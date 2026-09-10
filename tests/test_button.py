"""Tests for the KleverKey restart buttons."""

from __future__ import annotations

from aioresponses import aioresponses
from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from yarl import URL

from custom_components.kleverkey.const import API_BASE_URL

from .conftest import setup_integration
from .const import API_KEY


@pytest.mark.parametrize(
    ("entity_id", "url"),
    [
        (
            "button.front_door_restart",
            f"{API_BASE_URL}/api/v1/organizations/1/locks/100/restart",
        ),
        (
            "button.hallway_gateway_restart",
            f"{API_BASE_URL}/api/v1/organizations/1/gateways/200/restart",
        ),
    ],
)
async def test_press(
    hass: HomeAssistant,
    mock_api: aioresponses,
    mock_config_entry: MockConfigEntry,
    entity_id: str,
    url: str,
) -> None:
    """Pressing the button calls the matching restart endpoint."""
    await setup_integration(hass, mock_config_entry)
    mock_api.put(url, status=200)

    await hass.services.async_call(
        BUTTON_DOMAIN,
        SERVICE_PRESS,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )

    calls = mock_api.requests[("PUT", URL(url))]
    assert len(calls) == 1
    assert calls[0].kwargs["headers"]["Authorization"] == f"ApiKey {API_KEY}"


async def test_press_error(
    hass: HomeAssistant, mock_api: aioresponses, mock_config_entry: MockConfigEntry
) -> None:
    """A failing restart is surfaced as a Home Assistant error."""
    await setup_integration(hass, mock_config_entry)
    mock_api.put(f"{API_BASE_URL}/api/v1/organizations/1/locks/100/restart", status=500)

    with pytest.raises(HomeAssistantError, match="Failed to restart Front Door"):
        await hass.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: "button.front_door_restart"},
            blocking=True,
        )


async def test_gateway_press_error(
    hass: HomeAssistant, mock_api: aioresponses, mock_config_entry: MockConfigEntry
) -> None:
    """A failing gateway restart is surfaced as a Home Assistant error."""
    await setup_integration(hass, mock_config_entry)
    mock_api.put(
        f"{API_BASE_URL}/api/v1/organizations/1/gateways/200/restart",
        exception=TimeoutError,
    )

    with pytest.raises(HomeAssistantError, match="Failed to restart Hallway Gateway"):
        await hass.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: "button.hallway_gateway_restart"},
            blocking=True,
        )
