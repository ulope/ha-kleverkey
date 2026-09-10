"""Tests for the KleverKey sensors."""

from __future__ import annotations

from aioresponses import aioresponses
from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from .conftest import mock_api_responses, setup_integration
from .const import LOCK


@pytest.mark.parametrize(
    ("entity_id", "expected"),
    [
        ("sensor.front_door_physical_state", "locked"),
        ("sensor.front_door_weekly_openings", "12.5"),
        ("sensor.front_door_last_activity", "2026-02-03T05:06:07+00:00"),
        ("sensor.hallway_gateway_last_activity", "2026-02-03T05:00:00+00:00"),
    ],
)
async def test_states(
    hass: HomeAssistant,
    mock_api: aioresponses,
    mock_config_entry: MockConfigEntry,
    entity_id: str,
    expected: str,
) -> None:
    """Locks and gateways expose their readings as sensors."""
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(entity_id)
    assert state is not None, entity_id
    assert state.state == expected


async def test_diagnostic_sensors_are_disabled_by_default(
    hass: HomeAssistant, mock_api: aioresponses, mock_config_entry: MockConfigEntry
) -> None:
    """Noisy diagnostic sensors are registered but not enabled."""
    await setup_integration(hass, mock_config_entry)

    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get("sensor.front_door_signal_strength")
    assert entry is not None
    assert entry.disabled_by is er.RegistryEntryDisabler.INTEGRATION
    assert hass.states.get("sensor.front_door_signal_strength") is None


async def test_missing_values_are_unknown(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Values the API omits are reported as unknown."""
    lock = {key: value for key, value in LOCK.items() if key != "weeklyOpeningCount"}
    with aioresponses() as mocked:
        mock_api_responses(mocked, locks=[{**lock, "physicalState": 0}])
        await setup_integration(hass, mock_config_entry)

    assert hass.states.get("sensor.front_door_weekly_openings").state == STATE_UNKNOWN
    assert hass.states.get("sensor.front_door_physical_state").state == STATE_UNKNOWN


async def test_physical_state_options(
    hass: HomeAssistant, mock_api: aioresponses, mock_config_entry: MockConfigEntry
) -> None:
    """The physical state sensor advertises its possible values."""
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get("sensor.front_door_physical_state")
    assert state.attributes["options"] == ["open", "closed", "locked"]
