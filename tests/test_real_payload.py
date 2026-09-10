"""Parsing tests against a payload captured from the live KleverKey API."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from aioresponses import aioresponses
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kleverkey.api import KleverKeyClient
from custom_components.kleverkey.const import DOMAIN
from custom_components.kleverkey.models import (
    LockPhysicalState,
    LockState,
    LockType,
)

from .conftest import mock_api_responses, setup_integration
from .const import API_KEY

# Trimmed from a real GET /organizations/{id}/locks response. Kept verbatim
# where it matters: displayName carries the hex ID, timestamps use one, two or
# three fractional digits, weeklyOpeningCount is an int for some locks and a
# float for others, wirelessModes is a bitmask value not in the documented
# enum, and physicalState 0 (unknown) really does occur.
REAL_LOCKS: list[dict[str, Any]] = [
    {
        "id": 4050,
        "lockHexId": "C0E78B3011ED0000",
        "organizationId": 1,
        "gatewayId": 2057,
        "name": "B38 Toilette",
        "type": 18,
        "physicalState": 2,
        "properties": 0,
        "wirelessModes": 3,
        "state": 4,
        "firmwareVersion": 67329,
        "manufacturerFirmwareVersion": 132871,
        "firmwareUpdateState": 0,
        "displayName": "B38 Toilette (C0E78B3011ED0000)",
        "timezone": "W. Europe Standard Time",
        "powerSource": 100,
        "flashUsage": 15,
        "dieTemperature": 18,
        "bleRssi": -67,
        "isConnected": True,
        "dateBatteryChanged": "2026-04-13T19:35:11.437Z",
        "dateConnected": "2026-08-23T10:22:00.41Z",
        "dateDisconnected": "2026-08-23T09:30:00.117Z",
        "dateLastActivity": "2026-09-10T13:40:20.2Z",
        "weeklyOpeningCount": 26.1,
        "batteryChangeRecommended": False,
    },
    {
        "id": 4768,
        "lockHexId": "B56926C38CC20000",
        "organizationId": 1,
        "gatewayId": 2014,
        "name": "B38 Töpfern",
        "type": 18,
        "physicalState": 0,
        "wirelessModes": 3,
        "state": 4,
        "firmwareVersion": 67329,
        "displayName": "B38 Töpfern (B56926C38CC20000)",
        "dieTemperature": 22,
        "bleRssi": -81,
        "isConnected": True,
        "dateLastActivity": "2026-09-10T13:37:55.95Z",
        "weeklyOpeningCount": 57,
        "batteryChangeRecommended": False,
    },
    {
        "id": 4051,
        "lockHexId": "4CE88B7E1BE80000",
        "organizationId": 1,
        "gatewayId": 2049,
        "name": "B42 Rolltor",
        "type": 18,
        "physicalState": 1,
        "wirelessModes": 3,
        "state": 8,
        "firmwareVersion": 67329,
        "displayName": "B42 Rolltor (4CE88B7E1BE80000)",
        "dieTemperature": 14,
        "bleRssi": -84,
        "isConnected": True,
        "dateLastActivity": "2026-09-10T13:37:36.26Z",
        "weeklyOpeningCount": 16.7,
        "batteryChangeRecommended": False,
    },
]


async def test_parses_real_locks(hass: HomeAssistant) -> None:
    """The live payload parses into the expected models."""
    with aioresponses() as mocked:
        mock_api_responses(mocked, locks=REAL_LOCKS)
        locks = await KleverKeyClient(
            API_KEY, async_get_clientsession(hass)
        ).async_get_locks(1)

    by_id = {lock.id: lock for lock in locks}
    assert len(by_id) == 3

    toilette = by_id[4050]
    # The device name must not carry the hex ID that displayName appends.
    assert toilette.name == "B38 Toilette"
    assert toilette.hex_id == "C0E78B3011ED0000"
    assert toilette.type is LockType.UZMTK
    assert toilette.model == "UZMTK"
    assert toilette.physical_state is LockPhysicalState.CLOSED
    assert toilette.state is LockState.CLOSED
    assert toilette.die_temperature == 18
    assert toilette.battery_level == 100
    # 67329 == 0x10701, packed as major << 16 | minor << 8 | patch.
    assert toilette.firmware_version_string == "1.7.1"
    assert toilette.weekly_opening_count == 26.1
    assert toilette.date_last_activity == datetime(
        2026, 9, 10, 13, 40, 20, 200000, tzinfo=UTC
    )
    assert toilette.date_connected == datetime(
        2026, 8, 23, 10, 22, 0, 410000, tzinfo=UTC
    )

    # Non-ASCII names and an integer opening count survive parsing.
    toepfern = by_id[4768]
    assert toepfern.name == "B38 Töpfern"
    assert toepfern.weekly_opening_count == 57
    # physicalState 0 means the lock does not know, not "unlocked".
    assert toepfern.physical_state is LockPhysicalState.UNKNOWN

    rolltor = by_id[4051]
    assert rolltor.physical_state is LockPhysicalState.OPEN
    assert rolltor.state is LockState.OPEN


@pytest.mark.parametrize(
    ("lock_id", "entity_id", "expected"),
    [
        (4050, "binary_sensor.b38_toilette_lock", "on"),
        (4050, "binary_sensor.b38_toilette_door", "off"),
        (4050, "sensor.b38_toilette_controller_temperature", "18"),
        (4768, "sensor.b38_topfern_physical_state", "unknown"),
        (4051, "sensor.b42_rolltor_physical_state", "open"),
    ],
)
async def test_entities_from_real_locks(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    lock_id: int,
    entity_id: str,
    expected: str,
) -> None:
    """Entity IDs and states derive from the plain lock names."""
    with aioresponses() as mocked:
        mock_api_responses(mocked, locks=REAL_LOCKS)
        await setup_integration(hass, mock_config_entry)

    state = hass.states.get(entity_id)
    assert state is not None, entity_id
    assert state.state == expected


async def test_devices_from_real_locks(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Devices are named without the hex ID suffix."""
    with aioresponses() as mocked:
        mock_api_responses(mocked, locks=REAL_LOCKS)
        await setup_integration(hass, mock_config_entry)

    device_registry = dr.async_get(hass)
    device = device_registry.async_get_device({(DOMAIN, "lock_4050")})
    assert device is not None
    assert device.name == "B38 Toilette"
    assert device.serial_number == "C0E78B3011ED0000"
