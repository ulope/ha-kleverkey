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
        ("sensor.front_door_controller_temperature", "21"),
        ("sensor.front_door_battery", "100"),
        ("sensor.front_door_signal_strength", "-67"),
        ("sensor.front_door_last_activity", "2026-02-03T05:06:07+00:00"),
        ("sensor.front_door_connected_since", "2026-02-03T04:05:06+00:00"),
        ("sensor.front_door_disconnected_since", STATE_UNKNOWN),
        ("sensor.hallway_gateway_signal_strength", "-55"),
        ("sensor.hallway_gateway_last_activity", "2026-02-03T05:00:00+00:00"),
        ("sensor.hallway_gateway_connected_since", "2026-02-01T00:00:00+00:00"),
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


async def test_battery_changed_is_disabled_by_default(
    hass: HomeAssistant, mock_api: aioresponses, mock_config_entry: MockConfigEntry
) -> None:
    """The battery-changed timestamp is registered but not enabled."""
    await setup_integration(hass, mock_config_entry)

    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get("sensor.front_door_battery_changed")
    assert entry is not None
    assert entry.disabled_by is er.RegistryEntryDisabler.INTEGRATION
    assert hass.states.get("sensor.front_door_battery_changed") is None


async def test_diagnostic_sensors_are_enabled(
    hass: HomeAssistant, mock_api: aioresponses, mock_config_entry: MockConfigEntry
) -> None:
    """Signal strength, temperature and connect timestamps are on by default."""
    await setup_integration(hass, mock_config_entry)

    entity_registry = er.async_get(hass)
    for entity_id in (
        "sensor.front_door_signal_strength",
        "sensor.front_door_controller_temperature",
        "sensor.front_door_connected_since",
        "sensor.front_door_disconnected_since",
        "sensor.hallway_gateway_signal_strength",
        "sensor.hallway_gateway_connected_since",
        "sensor.hallway_gateway_disconnected_since",
    ):
        entry = entity_registry.async_get(entity_id)
        assert entry is not None, entity_id
        assert entry.disabled_by is None, entity_id


async def test_controller_temperature(
    hass: HomeAssistant, mock_api: aioresponses, mock_config_entry: MockConfigEntry
) -> None:
    """The controller temperature is whole degrees Celsius."""
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get("sensor.front_door_controller_temperature")
    assert state.state == "21"
    assert state.attributes["unit_of_measurement"] == "°C"
    assert state.attributes["device_class"] == "temperature"
    assert state.name == "Front Door Controller temperature"


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


async def test_battery_level(
    hass: HomeAssistant, mock_api: aioresponses, mock_config_entry: MockConfigEntry
) -> None:
    """The powerSource field is exposed as a battery percentage."""
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get("sensor.front_door_battery")
    assert state.state == "100"
    assert state.attributes["device_class"] == "battery"
    assert state.attributes["unit_of_measurement"] == "%"


async def test_battery_level_absent(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """A lock that reports no powerSource has an unknown battery level."""
    lock = {key: value for key, value in LOCK.items() if key != "powerSource"}
    with aioresponses() as mocked:
        mock_api_responses(mocked, locks=[lock])
        await setup_integration(hass, mock_config_entry)

    assert hass.states.get("sensor.front_door_battery").state == STATE_UNKNOWN
