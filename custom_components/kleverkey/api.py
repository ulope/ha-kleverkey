"""Thin async client for the parts of the KleverKey API used here.

Only the ``/organizations/{organizationId}/locks`` and
``/organizations/{organizationId}/gateways`` endpoints are used, plus the
handful of calls needed to discover which organizations an API key can see.
"""

from __future__ import annotations

import asyncio
from http import HTTPStatus
import logging
import socket
from typing import Any

import aiohttp
from yarl import URL

from .const import API_BASE_URL, API_PAGE_SIZE, API_TIMEOUT
from .models import Gateway, Lock, Organization

_LOGGER = logging.getLogger(__name__)


class KleverKeyError(Exception):
    """Base class for all KleverKey API errors."""


class KleverKeyConnectionError(KleverKeyError):
    """Raised when the API could not be reached."""


class KleverKeyAuthenticationError(KleverKeyError):
    """Raised when the API key is missing, invalid or lacks permissions."""


class KleverKeyResponseError(KleverKeyError):
    """Raised when the API returned an unexpected response."""


class KleverKeyClient:
    """Minimal client for the KleverKey REST API."""

    def __init__(
        self,
        api_key: str,
        session: aiohttp.ClientSession,
        base_url: str = API_BASE_URL,
    ) -> None:
        """Initialize the client."""
        self._api_key = api_key
        self._session = session
        self._base_url = str(URL(base_url)).rstrip("/")

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Perform a request against the API and return the decoded body."""
        url = URL(f"{self._base_url}{path}")
        headers = {
            "Authorization": f"ApiKey {self._api_key}",
            "Accept": "application/json",
        }

        try:
            async with (
                asyncio.timeout(API_TIMEOUT),
                self._session.request(
                    method, url, headers=headers, params=params
                ) as response,
            ):
                if response.status in (
                    HTTPStatus.UNAUTHORIZED,
                    HTTPStatus.FORBIDDEN,
                ):
                    raise KleverKeyAuthenticationError(
                        f"KleverKey rejected the API key ({response.status})"
                    )
                response.raise_for_status()
                if response.status == HTTPStatus.NO_CONTENT:
                    return None
                return await response.json(content_type=None)
        except TimeoutError as err:
            raise KleverKeyConnectionError(f"Timeout while talking to {url}") from err
        except aiohttp.ClientResponseError as err:
            raise KleverKeyResponseError(
                f"KleverKey returned HTTP {err.status} for {url}"
            ) from err
        except (aiohttp.ClientError, socket.gaierror) as err:
            raise KleverKeyConnectionError(f"Error talking to {url}: {err}") from err
        except ValueError as err:
            raise KleverKeyResponseError(
                f"KleverKey returned invalid JSON for {url}"
            ) from err

    async def _get_list(self, path: str, params: dict[str, Any]) -> list[Any]:
        """Fetch every page of a paged list endpoint and return its items."""
        items: list[Any] = []
        page = 1
        while True:
            payload = await self._request(
                "GET",
                path,
                params={**params, "Page": page, "PageSize": API_PAGE_SIZE},
            )
            if not isinstance(payload, dict):
                raise KleverKeyResponseError(f"Unexpected list response for {path}")
            page_items = payload.get("items") or []
            if not isinstance(page_items, list):
                raise KleverKeyResponseError(f"Unexpected items in response for {path}")
            items.extend(page_items)

            total_items = payload.get("totalItems")
            if (
                len(page_items) < API_PAGE_SIZE
                or not isinstance(total_items, int)
                or len(items) >= total_items
            ):
                return items
            page += 1

    async def async_get_current_user(self) -> dict[str, Any]:
        """Return the user the API key belongs to."""
        payload = await self._request("GET", "/api/v1/users/me")
        if not isinstance(payload, dict) or "id" not in payload:
            raise KleverKeyResponseError("Unexpected response for the current user")
        return payload

    async def async_get_organization(self, organization_id: int) -> Organization:
        """Return a single organization."""
        payload = await self._request("GET", f"/api/v1/organizations/{organization_id}")
        if not isinstance(payload, dict) or "id" not in payload:
            raise KleverKeyResponseError(
                f"Unexpected response for organization {organization_id}"
            )
        return Organization.from_api(payload)

    async def async_get_organizations(
        self, user: dict[str, Any] | None = None
    ) -> list[Organization]:
        """Return every organization the API key has access to.

        The API has no "list organizations" endpoint; the current user carries
        the IDs and each organization is then fetched by ID.  Pass ``user`` to
        reuse an already fetched current user.
        """
        if user is None:
            user = await self.async_get_current_user()
        organization_ids = user.get("organizationIds") or []
        if not organization_ids and (fallback := user.get("organizationId")):
            organization_ids = [fallback]

        results = await asyncio.gather(
            *(
                self.async_get_organization(int(organization_id))
                for organization_id in organization_ids
            ),
            return_exceptions=True,
        )

        organizations: list[Organization] = []
        for organization_id, result in zip(organization_ids, results, strict=True):
            if isinstance(result, Organization):
                organizations.append(result)
            elif isinstance(result, KleverKeyAuthenticationError):
                # The key may be scoped to a subset of the user's organizations.
                _LOGGER.debug("No access to organization %s", organization_id)
            elif isinstance(result, BaseException):
                raise result
        return sorted(organizations, key=lambda organization: organization.name)

    async def async_get_locks(self, organization_id: int) -> list[Lock]:
        """Return the locks of an organization."""
        items = await self._get_list(
            f"/api/v1/organizations/{organization_id}/locks",
            {"IncludeFirmwareUpdateInformation": "true"},
        )
        return [Lock.from_api(item) for item in items]

    async def async_get_gateways(self, organization_id: int) -> list[Gateway]:
        """Return the gateways of an organization."""
        items = await self._get_list(
            f"/api/v1/organizations/{organization_id}/gateways",
            {"IncludeFirmwareUpdateInformation": "true"},
        )
        return [Gateway.from_api(item) for item in items]

    async def async_restart_lock(self, organization_id: int, lock_id: int) -> None:
        """Restart a lock."""
        await self._request(
            "PUT",
            f"/api/v1/organizations/{organization_id}/locks/{lock_id}/restart",
        )

    async def async_restart_gateway(
        self, organization_id: int, gateway_id: int
    ) -> None:
        """Restart a gateway."""
        await self._request(
            "PUT",
            f"/api/v1/organizations/{organization_id}/gateways/{gateway_id}/restart",
        )
