"""Tests for the KleverKey binary sensors."""

from __future__ import annotations

from datetime import timedelta

from aioresponses import aioresponses
from freezegun.api import FrozenDateTimeFactory
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from .conftest import mock_api_responses, setup_integration
from .const import GATEWAY, LOCK


@pytest.mark.parametrize(
    ("entity_id", "expected"),
    [
        ("binary_sensor.lock_front_door_lock", STATE_OFF),
        ("binary_sensor.lock_front_door_door", STATE_OFF),
        ("binary_sensor.lock_front_door_connectivity", STATE_ON),
        ("binary_sensor.lock_front_door_battery", STATE_ON),
        ("binary_sensor.lock_front_door_emergency", STATE_OFF),
        ("binary_sensor.lock_front_door_update", STATE_ON),
        ("binary_sensor.gateway_hallway_connectivity", STATE_ON),
        ("binary_sensor.gateway_hallway_update", STATE_OFF),
    ],
)
async def test_states(
    hass: HomeAssistant,
    mock_api: aioresponses,
    mock_config_entry: MockConfigEntry,
    entity_id: str,
    expected: str,
) -> None:
    """Locks and gateways expose their status as binary sensors."""
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(entity_id)
    assert state is not None, entity_id
    assert state.state == expected


async def test_open_lock(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """An open lock reports as unlocked and its door as open."""
    with aioresponses() as mocked:
        mock_api_responses(mocked, locks=[{**LOCK, "physicalState": 1}])
        await setup_integration(hass, mock_config_entry)

    assert hass.states.get("binary_sensor.lock_front_door_lock").state == STATE_ON
    assert hass.states.get("binary_sensor.lock_front_door_door").state == STATE_ON


async def test_unknown_physical_state(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """An unknown physical state is reported as unknown, not as unlocked."""
    with aioresponses() as mocked:
        mock_api_responses(mocked, locks=[{**LOCK, "physicalState": 0}])
        await setup_integration(hass, mock_config_entry)

    assert hass.states.get("binary_sensor.lock_front_door_lock").state == STATE_UNKNOWN
    assert hass.states.get("binary_sensor.lock_front_door_door").state == STATE_UNKNOWN


async def test_removed_lock_becomes_unavailable(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """A lock that disappears from the API turns unavailable."""
    with aioresponses() as mocked:
        mock_api_responses(mocked)
        await setup_integration(hass, mock_config_entry)
        assert (
            hass.states.get("binary_sensor.lock_front_door_connectivity").state
            == STATE_ON
        )

    with aioresponses() as mocked:
        mock_api_responses(mocked, locks=[])
        freezer.tick(timedelta(minutes=5))
        async_fire_time_changed(hass)
        await hass.async_block_till_done(wait_background_tasks=True)

    assert (
        hass.states.get("binary_sensor.lock_front_door_connectivity").state
        == STATE_UNAVAILABLE
    )
    assert (
        hass.states.get("binary_sensor.gateway_hallway_connectivity").state == STATE_ON
    )


async def test_new_lock_is_added(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """A lock that appears later is added without reloading the entry."""
    with aioresponses() as mocked:
        mock_api_responses(mocked)
        await setup_integration(hass, mock_config_entry)
        assert hass.states.get("binary_sensor.lock_back_door_connectivity") is None

    new_lock = {**LOCK, "id": 101, "displayName": "Back Door", "name": "Back Door"}
    with aioresponses() as mocked:
        mock_api_responses(mocked, locks=[LOCK, new_lock], gateways=[GATEWAY])
        freezer.tick(timedelta(minutes=5))
        async_fire_time_changed(hass)
        await hass.async_block_till_done(wait_background_tasks=True)

    assert (
        hass.states.get("binary_sensor.lock_back_door_connectivity").state == STATE_ON
    )
