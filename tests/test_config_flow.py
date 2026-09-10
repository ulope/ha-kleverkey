"""Tests for the KleverKey config flow."""

from __future__ import annotations

from aioresponses import aioresponses
from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kleverkey.const import (
    API_BASE_URL,
    CONF_ORGANIZATION_IDS,
    DOMAIN,
)

from .conftest import mock_api_responses, setup_integration
from .const import API_KEY, USER


async def test_full_flow(hass: HomeAssistant, mock_api: aioresponses) -> None:
    """The user picks an API key and then one or more organizations."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_KEY: API_KEY}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "organizations"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_ORGANIZATION_IDS: ["1", "2"]}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Acme Corp, Beta Ltd"
    assert result["data"] == {CONF_API_KEY: API_KEY}
    assert result["options"] == {CONF_ORGANIZATION_IDS: [1, 2]}
    assert result["result"].unique_id == str(USER["id"])


async def test_flow_offers_every_organization(
    hass: HomeAssistant, mock_api: aioresponses
) -> None:
    """The organization step lists all organizations the key can see."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_KEY: API_KEY}
    )

    selector = result["data_schema"].schema[CONF_ORGANIZATION_IDS]
    config = selector.config
    assert config["multiple"] is True
    assert [option["label"] for option in config["options"]] == [
        "Acme Corp",
        "Beta Ltd",
    ]


@pytest.mark.parametrize(
    ("status", "error"),
    [(401, "invalid_auth"), (403, "invalid_auth"), (500, "unknown")],
)
async def test_user_step_errors(hass: HomeAssistant, status: int, error: str) -> None:
    """API errors are surfaced on the API key step and can be retried."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with aioresponses() as mocked:
        mocked.get(f"{API_BASE_URL}/api/v1/users/me", status=status)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_API_KEY: "bad"}
        )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}

    with aioresponses() as mocked:
        mock_api_responses(mocked)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_API_KEY: API_KEY}
        )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "organizations"


async def test_user_step_cannot_connect(hass: HomeAssistant) -> None:
    """Connection problems are reported as cannot_connect."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    with aioresponses() as mocked:
        mocked.get(f"{API_BASE_URL}/api/v1/users/me", exception=TimeoutError)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_API_KEY: API_KEY}
        )
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_step_without_organizations(hass: HomeAssistant) -> None:
    """A key without any organization cannot be set up."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    with aioresponses() as mocked:
        mocked.get(
            f"{API_BASE_URL}/api/v1/users/me",
            payload={"id": 42, "organizationIds": []},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_API_KEY: API_KEY}
        )
    assert result["errors"] == {"base": "no_organizations"}


async def test_already_configured(
    hass: HomeAssistant, mock_api: aioresponses, mock_config_entry: MockConfigEntry
) -> None:
    """The same KleverKey account can only be configured once."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_KEY: API_KEY}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reauth(
    hass: HomeAssistant, mock_api: aioresponses, mock_config_entry: MockConfigEntry
) -> None:
    """Re-authentication replaces the stored API key."""
    mock_config_entry.add_to_hass(hass)

    result = await mock_config_entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_KEY: "new-key"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert mock_config_entry.data[CONF_API_KEY] == "new-key"


async def test_reauth_wrong_account(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """A key for a different account is rejected during re-authentication."""
    mock_config_entry.add_to_hass(hass)
    result = await mock_config_entry.start_reauth_flow(hass)

    with aioresponses() as mocked:
        mocked.get(
            f"{API_BASE_URL}/api/v1/users/me",
            payload={"id": 99, "organizationIds": [1]},
        )
        mocked.get(
            f"{API_BASE_URL}/api/v1/organizations/1",
            payload={"id": 1, "name": "Other"},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_API_KEY: "other-account"}
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "wrong_account"


async def test_options_flow(
    hass: HomeAssistant, mock_api: aioresponses, mock_config_entry: MockConfigEntry
) -> None:
    """The selected organizations can be changed afterwards."""
    await setup_integration(hass, mock_config_entry)

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["data_schema"].schema[CONF_ORGANIZATION_IDS] is not None

    mock_api_responses(mock_api)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_ORGANIZATION_IDS: ["1", "2"]}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert mock_config_entry.options == {CONF_ORGANIZATION_IDS: [1, 2]}


async def test_options_flow_invalid_auth(
    hass: HomeAssistant, mock_api: aioresponses, mock_config_entry: MockConfigEntry
) -> None:
    """An invalid API key aborts the options flow."""
    await setup_integration(hass, mock_config_entry)

    mock_api.clear()
    mock_api.get(f"{API_BASE_URL}/api/v1/users/me", status=401, repeat=True)
    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "invalid_auth"


async def test_no_organization_selected(
    hass: HomeAssistant, mock_api: aioresponses
) -> None:
    """Submitting the organization step without a selection shows an error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_KEY: API_KEY}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_ORGANIZATION_IDS: []}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_ORGANIZATION_IDS: "no_organizations_selected"}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_ORGANIZATION_IDS: ["1"]}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_reauth_error_can_be_retried(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """A rejected key during re-authentication can be corrected."""
    mock_config_entry.add_to_hass(hass)
    result = await mock_config_entry.start_reauth_flow(hass)

    with aioresponses() as mocked:
        # The first attempt is rejected, the retry then uses the default mocks.
        mocked.get(f"{API_BASE_URL}/api/v1/users/me", status=401)
        mock_api_responses(mocked)

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_API_KEY: "bad"}
        )
        assert result["errors"] == {"base": "invalid_auth"}

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_API_KEY: "good"}
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert mock_config_entry.data[CONF_API_KEY] == "good"


async def test_options_flow_without_selection(
    hass: HomeAssistant, mock_api: aioresponses, mock_config_entry: MockConfigEntry
) -> None:
    """Clearing the organization selection is rejected."""
    await setup_integration(hass, mock_config_entry)

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_ORGANIZATION_IDS: []}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_ORGANIZATION_IDS: "no_organizations_selected"}


async def test_options_flow_cannot_connect(
    hass: HomeAssistant, mock_api: aioresponses, mock_config_entry: MockConfigEntry
) -> None:
    """A connection problem aborts the options flow."""
    await setup_integration(hass, mock_config_entry)

    mock_api.clear()
    mock_api.get(f"{API_BASE_URL}/api/v1/users/me", exception=TimeoutError, repeat=True)
    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "cannot_connect"


async def test_options_flow_without_organizations(
    hass: HomeAssistant, mock_api: aioresponses, mock_config_entry: MockConfigEntry
) -> None:
    """A key that lost access to every organization aborts the options flow."""
    await setup_integration(hass, mock_config_entry)

    mock_api.clear()
    mock_api.get(
        f"{API_BASE_URL}/api/v1/users/me",
        payload={"id": 42, "organizationIds": []},
        repeat=True,
    )
    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_organizations"
