"""Data models for the KleverKey API.

The KleverKey API returns enum members as plain integers.  The enums below
mirror the descriptions from the official OpenAPI document so that the rest of
the integration can work with readable names.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum, IntFlag
from typing import Any

from homeassistant.util import dt as dt_util


class LockPhysicalState(IntEnum):
    """Physical state reported by a lock."""

    UNKNOWN = 0
    OPEN = 1
    CLOSED = 2
    LOCKED = 3


class LockState(IntFlag):
    """Status flags reported by a lock."""

    NONE = 0
    BATTERY_LOW = 1
    EMERGENCY = 2
    CLOSED = 4
    OPEN = 8
    RTC_UPDATE_REQUIRED = 16
    EVENT_AVAILABLE = 32


class LockType(IntEnum):
    """Hardware type of a lock."""

    LOCK_B1 = 1
    UZEDH = 17
    UZMTK = 18
    UZRDR = 19
    AUTEC_READER = 20
    DEVELOPMENT = 255


class GatewayType(IntEnum):
    """Hardware type of a gateway."""

    WIFI = 1


LOCK_TYPE_NAMES: dict[LockType, str] = {
    LockType.LOCK_B1: "Lock B1",
    LockType.UZEDH: "UZEDH",
    LockType.UZMTK: "UZMTK",
    LockType.UZRDR: "UZRDR",
    LockType.AUTEC_READER: "Autec Reader",
    LockType.DEVELOPMENT: "Development",
}

GATEWAY_TYPE_NAMES: dict[GatewayType, str] = {
    GatewayType.WIFI: "Wi-Fi Gateway",
}


def _parse_datetime(value: Any) -> datetime | None:
    """Parse an ISO 8601 timestamp returned by the API."""
    if not isinstance(value, str):
        return None
    return dt_util.parse_datetime(value)


def _parse_int(value: Any) -> int | None:
    """Return ``value`` as an int, or ``None`` if it is not a number."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return int(value)


def _parse_float(value: Any) -> float | None:
    """Return ``value`` as a float, or ``None`` if it is not a number."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _parse_enum[EnumT: IntEnum](enum: type[EnumT], value: Any) -> EnumT | None:
    """Return ``value`` as an enum member, tolerating unknown values."""
    if (parsed := _parse_int(value)) is None:
        return None
    try:
        return enum(parsed)
    except ValueError:
        return None


@dataclass(frozen=True, slots=True)
class Organization:
    """A KleverKey organization."""

    id: int
    name: str

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Organization:
        """Build an organization from an API payload."""
        organization_id = int(data["id"])
        return cls(
            id=organization_id,
            name=data.get("name") or f"Organization {organization_id}",
        )


@dataclass(frozen=True, slots=True)
class Lock:
    """A lock belonging to an organization."""

    id: int
    organization_id: int
    name: str
    hex_id: str | None
    gateway_id: int | None
    type: LockType | None
    physical_state: LockPhysicalState | None
    state: LockState
    firmware_version: int | None
    firmware_update_available: bool | None
    is_connected: bool
    battery_change_recommended: bool
    ble_rssi: int | None
    die_temperature: int | None
    weekly_opening_count: float | None
    date_battery_changed: datetime | None
    date_connected: datetime | None
    date_disconnected: datetime | None
    date_last_activity: datetime | None
    timezone: str | None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Lock:
        """Build a lock from an API payload."""
        lock_id = int(data["id"])
        return cls(
            id=lock_id,
            organization_id=int(data["organizationId"]),
            # ``displayName`` appends the hex ID, e.g. "Front Door (C0E7…)",
            # so the plain name makes the better device name.
            name=data.get("name") or data.get("displayName") or f"Lock {lock_id}",
            hex_id=data.get("lockHexId"),
            gateway_id=_parse_int(data.get("gatewayId")),
            type=_parse_enum(LockType, data.get("type")),
            physical_state=_parse_enum(LockPhysicalState, data.get("physicalState")),
            state=LockState(_parse_int(data.get("state")) or 0),
            firmware_version=_parse_int(data.get("firmwareVersion")),
            firmware_update_available=data.get("isFirmwareUpdateAvailable"),
            is_connected=bool(data.get("isConnected")),
            battery_change_recommended=bool(data.get("batteryChangeRecommended")),
            ble_rssi=_parse_int(data.get("bleRssi")),
            die_temperature=_parse_int(data.get("dieTemperature")),
            weekly_opening_count=_parse_float(data.get("weeklyOpeningCount")),
            date_battery_changed=_parse_datetime(data.get("dateBatteryChanged")),
            date_connected=_parse_datetime(data.get("dateConnected")),
            date_disconnected=_parse_datetime(data.get("dateDisconnected")),
            date_last_activity=_parse_datetime(data.get("dateLastActivity")),
            timezone=data.get("timezone"),
        )

    @property
    def model(self) -> str | None:
        """Return a human readable hardware model."""
        if self.type is None:
            return None
        return LOCK_TYPE_NAMES.get(self.type, self.type.name)


@dataclass(frozen=True, slots=True)
class Gateway:
    """A gateway belonging to an organization."""

    id: int
    organization_id: int
    name: str
    hex_id: str | None
    type: GatewayType | None
    firmware_version: int | None
    firmware_update_available: bool | None
    is_connected: bool
    wifi_rssi: int | None
    date_connected: datetime | None
    date_disconnected: datetime | None
    date_last_activity: datetime | None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Gateway:
        """Build a gateway from an API payload."""
        gateway_id = int(data["id"])
        return cls(
            id=gateway_id,
            organization_id=int(data["organizationId"]),
            name=data.get("name") or data.get("displayName") or f"Gateway {gateway_id}",
            hex_id=data.get("gatewayHexId"),
            type=_parse_enum(GatewayType, data.get("type")),
            firmware_version=_parse_int(data.get("firmwareVersion")),
            firmware_update_available=data.get("isFirmwareUpdateAvailable"),
            is_connected=bool(data.get("isConnected")),
            wifi_rssi=_parse_int(data.get("wifiRssi")),
            date_connected=_parse_datetime(data.get("dateConnected")),
            date_disconnected=_parse_datetime(data.get("dateDisconnected")),
            date_last_activity=_parse_datetime(data.get("dateLastActivity")),
        )

    @property
    def model(self) -> str | None:
        """Return a human readable hardware model."""
        if self.type is None:
            return None
        return GATEWAY_TYPE_NAMES.get(self.type, self.type.name)
