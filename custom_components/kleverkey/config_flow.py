"""Config flow for the KleverKey integration."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_API_KEY
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
import voluptuous as vol

from .api import (
    KleverKeyAuthenticationError,
    KleverKeyClient,
    KleverKeyConnectionError,
    KleverKeyError,
)
from .const import CONF_ORGANIZATION_IDS, DOMAIN
from .coordinator import KleverKeyConfigEntry
from .models import Organization

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        )
    }
)


def _organizations_schema(
    organizations: list[Organization], selected: list[int]
) -> vol.Schema:
    """Return the schema for picking one or more organizations."""
    return vol.Schema(
        {
            vol.Required(
                CONF_ORGANIZATION_IDS,
                default=[
                    str(organization_id)
                    for organization_id in selected
                    if any(
                        organization.id == organization_id
                        for organization in organizations
                    )
                ],
            ): SelectSelector(
                SelectSelectorConfig(
                    options=[
                        SelectOptionDict(
                            value=str(organization.id), label=organization.name
                        )
                        for organization in organizations
                    ],
                    multiple=True,
                    mode=SelectSelectorMode.LIST,
                )
            )
        }
    )


class KleverKeyConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for KleverKey."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the flow."""
        self._api_key: str = ""
        self._organizations: list[Organization] = []

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: KleverKeyConfigEntry,
    ) -> KleverKeyOptionsFlow:
        """Return the options flow."""
        return KleverKeyOptionsFlow()

    async def _async_load_organizations(self, api_key: str) -> tuple[str | None, Any]:
        """Validate the API key and load the organizations it can see."""
        client = KleverKeyClient(api_key, async_get_clientsession(self.hass))
        try:
            user = await client.async_get_current_user()
            organizations = await client.async_get_organizations(user)
        except KleverKeyAuthenticationError:
            return "invalid_auth", None
        except KleverKeyConnectionError:
            return "cannot_connect", None
        except KleverKeyError:
            _LOGGER.exception("Unexpected error talking to the KleverKey API")
            return "unknown", None
        if not organizations:
            return "no_organizations", None
        self._organizations = organizations
        return None, user

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the API key."""
        errors: dict[str, str] = {}
        if user_input is not None:
            api_key = user_input[CONF_API_KEY]
            error, user = await self._async_load_organizations(api_key)
            if error is None:
                await self.async_set_unique_id(str(user["id"]))
                self._abort_if_unique_id_configured()
                self._api_key = api_key
                return await self.async_step_organizations()
            errors["base"] = error

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )

    async def async_step_organizations(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user pick one or more organizations."""
        errors: dict[str, str] = {}
        if user_input is not None:
            organization_ids = [
                int(organization_id)
                for organization_id in user_input[CONF_ORGANIZATION_IDS]
            ]
            if organization_ids:
                names = {
                    organization.id: organization.name
                    for organization in self._organizations
                }
                title = ", ".join(
                    names[organization_id] for organization_id in organization_ids
                )
                return self.async_create_entry(
                    title=title,
                    data={CONF_API_KEY: self._api_key},
                    options={CONF_ORGANIZATION_IDS: organization_ids},
                )
            errors[CONF_ORGANIZATION_IDS] = "no_organizations_selected"

        return self.async_show_form(
            step_id="organizations",
            data_schema=_organizations_schema(self._organizations, []),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle a re-authentication request."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for a new API key."""
        errors: dict[str, str] = {}
        if user_input is not None:
            api_key = user_input[CONF_API_KEY]
            error, user = await self._async_load_organizations(api_key)
            if error is None:
                await self.async_set_unique_id(str(user["id"]))
                self._abort_if_unique_id_mismatch(reason="wrong_account")
                return self.async_update_reload_and_abort(
                    self._get_reauth_entry(), data_updates={CONF_API_KEY: api_key}
                )
            errors["base"] = error

        return self.async_show_form(
            step_id="reauth_confirm", data_schema=STEP_USER_SCHEMA, errors=errors
        )


class KleverKeyOptionsFlow(OptionsFlow):
    """Handle changing the selected organizations."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user change the selected organizations."""
        entry = self.config_entry
        client = KleverKeyClient(
            entry.data[CONF_API_KEY], async_get_clientsession(self.hass)
        )

        errors: dict[str, str] = {}
        if user_input is not None:
            organization_ids = [
                int(organization_id)
                for organization_id in user_input[CONF_ORGANIZATION_IDS]
            ]
            if organization_ids:
                return self.async_create_entry(
                    data={CONF_ORGANIZATION_IDS: organization_ids}
                )
            errors[CONF_ORGANIZATION_IDS] = "no_organizations_selected"

        try:
            organizations = await client.async_get_organizations()
        except KleverKeyAuthenticationError:
            return self.async_abort(reason="invalid_auth")
        except KleverKeyError:
            return self.async_abort(reason="cannot_connect")
        if not organizations:
            return self.async_abort(reason="no_organizations")

        current = [
            int(organization_id)
            for organization_id in entry.options.get(CONF_ORGANIZATION_IDS, [])
        ]
        return self.async_show_form(
            step_id="init",
            data_schema=_organizations_schema(organizations, current),
            errors=errors,
        )
