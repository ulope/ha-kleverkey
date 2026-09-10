"""Tests for the KleverKey API client."""

from __future__ import annotations

from datetime import UTC, datetime
import re

from aioresponses import aioresponses
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import pytest

from custom_components.kleverkey.api import (
    KleverKeyAuthenticationError,
    KleverKeyClient,
    KleverKeyConnectionError,
    KleverKeyResponseError,
)
from custom_components.kleverkey.const import API_BASE_URL
from custom_components.kleverkey.models import (
    GatewayType,
    LockPhysicalState,
    LockState,
    LockType,
)

from .conftest import mock_api_responses
from .const import API_KEY


def _client(hass: HomeAssistant) -> KleverKeyClient:
    return KleverKeyClient(API_KEY, async_get_clientsession(hass))


async def test_get_organizations(hass: HomeAssistant, mock_api: aioresponses) -> None:
    """Organizations are looked up from the current user's organization IDs."""
    organizations = await _client(hass).async_get_organizations()

    assert [(organization.id, organization.name) for organization in organizations] == [
        (1, "Acme Corp"),
        (2, "Beta Ltd"),
    ]


async def test_get_organizations_skips_inaccessible(
    hass: HomeAssistant, mock_api: aioresponses
) -> None:
    """Organizations the key cannot read are skipped instead of failing."""
    mock_api.clear()
    mock_api.get(
        f"{API_BASE_URL}/api/v1/users/me",
        payload={"id": 42, "organizationIds": [1, 2]},
    )
    mock_api.get(
        f"{API_BASE_URL}/api/v1/organizations/1",
        payload={"id": 1, "name": "Acme Corp"},
    )
    mock_api.get(f"{API_BASE_URL}/api/v1/organizations/2", status=403)

    organizations = await _client(hass).async_get_organizations()

    assert [organization.id for organization in organizations] == [1]


async def test_get_locks_parses_payload(
    hass: HomeAssistant, mock_api: aioresponses
) -> None:
    """Lock payloads are converted into typed models."""
    locks = await _client(hass).async_get_locks(1)

    assert len(locks) == 1
    lock = locks[0]
    assert lock.id == 100
    assert lock.name == "Front Door"
    assert lock.gateway_id == 200
    assert lock.type is LockType.LOCK_B1
    assert lock.model == "Lock B1"
    assert lock.physical_state is LockPhysicalState.LOCKED
    assert lock.state is LockState.BATTERY_LOW
    assert lock.ble_rssi == -67
    assert lock.battery_level == 100
    assert lock.firmware_version_string == "1.7.1"
    assert lock.weekly_opening_count == 12.5
    assert lock.date_last_activity == datetime(2026, 2, 3, 5, 6, 7, tzinfo=UTC)
    assert lock.date_disconnected is None


async def test_get_gateways_parses_payload(
    hass: HomeAssistant, mock_api: aioresponses
) -> None:
    """Gateway payloads are converted into typed models."""
    gateways = await _client(hass).async_get_gateways(1)

    assert len(gateways) == 1
    gateway = gateways[0]
    assert gateway.id == 200
    assert gateway.type is GatewayType.WIFI
    assert gateway.model == "Wi-Fi Gateway"
    assert gateway.wifi_rssi == -55
    assert gateway.firmware_version_string == "1.2.1"


async def test_unknown_enum_values_are_tolerated(hass: HomeAssistant) -> None:
    """Enum values the integration does not know about do not break parsing."""
    with aioresponses() as mocked:
        mock_api_responses(mocked, locks=[{"id": 1, "organizationId": 1, "type": 99}])
        locks = await _client(hass).async_get_locks(1)

    assert locks[0].type is None
    assert locks[0].model is None
    assert locks[0].name == "Lock 1"


@pytest.mark.parametrize("status", [401, 403])
async def test_authentication_error(hass: HomeAssistant, status: int) -> None:
    """4xx auth responses raise an authentication error."""
    with aioresponses() as mocked:
        mocked.get(f"{API_BASE_URL}/api/v1/users/me", status=status)
        with pytest.raises(KleverKeyAuthenticationError):
            await _client(hass).async_get_current_user()


async def test_server_error(hass: HomeAssistant) -> None:
    """Server errors raise a response error."""
    with aioresponses() as mocked:
        mocked.get(f"{API_BASE_URL}/api/v1/users/me", status=500)
        with pytest.raises(KleverKeyResponseError):
            await _client(hass).async_get_current_user()


async def test_connection_error(hass: HomeAssistant) -> None:
    """Connection problems raise a connection error."""
    with aioresponses() as mocked:
        mocked.get(f"{API_BASE_URL}/api/v1/users/me", exception=TimeoutError)
        with pytest.raises(KleverKeyConnectionError):
            await _client(hass).async_get_current_user()


async def test_unexpected_payload(hass: HomeAssistant) -> None:
    """An unexpected body shape raises a response error."""
    with aioresponses() as mocked:
        mocked.get(f"{API_BASE_URL}/api/v1/users/me", payload=["nope"])
        with pytest.raises(KleverKeyResponseError):
            await _client(hass).async_get_current_user()


async def test_restart_calls(hass: HomeAssistant) -> None:
    """Restart calls hit the organization scoped endpoints."""
    with aioresponses() as mocked:
        mocked.put(
            f"{API_BASE_URL}/api/v1/organizations/1/locks/100/restart", status=200
        )
        mocked.put(
            f"{API_BASE_URL}/api/v1/organizations/1/gateways/200/restart", status=200
        )
        client = _client(hass)
        await client.async_restart_lock(1, 100)
        await client.async_restart_gateway(1, 200)


async def test_pagination(hass: HomeAssistant) -> None:
    """All pages of a list endpoint are fetched."""
    page_size = 1000
    first_page = [
        {"id": index, "organizationId": 1} for index in range(1, page_size + 1)
    ]
    second_page = [{"id": page_size + 1, "organizationId": 1}]

    with aioresponses() as mocked:
        mocked.get(
            re.compile(
                rf"^{re.escape(API_BASE_URL)}/api/v1/organizations/1/locks\?.*Page=1&.*$"
            ),
            payload={"totalItems": page_size + 1, "items": first_page},
        )
        mocked.get(
            re.compile(
                rf"^{re.escape(API_BASE_URL)}/api/v1/organizations/1/locks\?.*Page=2&.*$"
            ),
            payload={"totalItems": page_size + 1, "items": second_page},
        )
        locks = await _client(hass).async_get_locks(1)

    assert len(locks) == page_size + 1
    assert locks[-1].id == page_size + 1
