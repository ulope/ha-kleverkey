"""Sensors for KleverKey locks and gateways."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType

from .coordinator import KleverKeyConfigEntry, KleverKeyDataUpdateCoordinator
from .entity import KleverKeyGatewayEntity, KleverKeyLockEntity
from .models import Gateway, Lock, LockPhysicalState

PHYSICAL_STATE_OPTIONS = ["open", "closed", "locked"]


@dataclass(frozen=True, kw_only=True)
class KleverKeyLockSensorDescription(SensorEntityDescription):
    """Describes a KleverKey lock sensor."""

    value_fn: Callable[[Lock], StateType | datetime]


@dataclass(frozen=True, kw_only=True)
class KleverKeyGatewaySensorDescription(SensorEntityDescription):
    """Describes a KleverKey gateway sensor."""

    value_fn: Callable[[Gateway], StateType | datetime]


def _physical_state(lock: Lock) -> str | None:
    """Return the physical state as one of the enum options."""
    if lock.physical_state is None or lock.physical_state is LockPhysicalState.UNKNOWN:
        return None
    return lock.physical_state.name.lower()


LOCK_DESCRIPTIONS: tuple[KleverKeyLockSensorDescription, ...] = (
    KleverKeyLockSensorDescription(
        key="physical_state",
        translation_key="physical_state",
        device_class=SensorDeviceClass.ENUM,
        options=PHYSICAL_STATE_OPTIONS,
        value_fn=_physical_state,
    ),
    KleverKeyLockSensorDescription(
        key="signal_strength",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda lock: lock.ble_rssi,
    ),
    KleverKeyLockSensorDescription(
        key="temperature",
        translation_key="controller_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        # The API reports the controller die temperature as whole degrees.
        suggested_display_precision=0,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda lock: lock.die_temperature,
    ),
    KleverKeyLockSensorDescription(
        key="weekly_opening_count",
        translation_key="weekly_opening_count",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda lock: lock.weekly_opening_count,
    ),
    KleverKeyLockSensorDescription(
        key="last_activity",
        translation_key="last_activity",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda lock: lock.date_last_activity,
    ),
    KleverKeyLockSensorDescription(
        key="connected_since",
        translation_key="connected_since",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda lock: lock.date_connected,
    ),
    KleverKeyLockSensorDescription(
        key="disconnected_since",
        translation_key="disconnected_since",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda lock: lock.date_disconnected,
    ),
    KleverKeyLockSensorDescription(
        key="battery_changed",
        translation_key="battery_changed",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda lock: lock.date_battery_changed,
    ),
)

GATEWAY_DESCRIPTIONS: tuple[KleverKeyGatewaySensorDescription, ...] = (
    KleverKeyGatewaySensorDescription(
        key="signal_strength",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda gateway: gateway.wifi_rssi,
    ),
    KleverKeyGatewaySensorDescription(
        key="last_activity",
        translation_key="last_activity",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda gateway: gateway.date_last_activity,
    ),
    KleverKeyGatewaySensorDescription(
        key="connected_since",
        translation_key="connected_since",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda gateway: gateway.date_connected,
    ),
    KleverKeyGatewaySensorDescription(
        key="disconnected_since",
        translation_key="disconnected_since",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda gateway: gateway.date_disconnected,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KleverKeyConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the KleverKey sensors."""
    coordinator = entry.runtime_data
    known: set[str] = set()

    @callback
    def _async_add_entities() -> None:
        entities: list[SensorEntity] = []
        for lock_id in coordinator.data.locks:
            for description in LOCK_DESCRIPTIONS:
                if (unique := f"lock_{lock_id}_{description.key}") in known:
                    continue
                known.add(unique)
                entities.append(KleverKeyLockSensor(coordinator, lock_id, description))
        for gateway_id in coordinator.data.gateways:
            for gateway_description in GATEWAY_DESCRIPTIONS:
                if (
                    unique := f"gateway_{gateway_id}_{gateway_description.key}"
                ) in known:
                    continue
                known.add(unique)
                entities.append(
                    KleverKeyGatewaySensor(coordinator, gateway_id, gateway_description)
                )
        async_add_entities(entities)

    _async_add_entities()
    entry.async_on_unload(coordinator.async_add_listener(_async_add_entities))


class KleverKeyLockSensor(KleverKeyLockEntity, SensorEntity):
    """A sensor for a KleverKey lock."""

    entity_description: KleverKeyLockSensorDescription

    def __init__(
        self,
        coordinator: KleverKeyDataUpdateCoordinator,
        lock_id: int,
        description: KleverKeyLockSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, lock_id, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> StateType | datetime:
        """Return the state of the sensor."""
        return self.entity_description.value_fn(self.lock)


class KleverKeyGatewaySensor(KleverKeyGatewayEntity, SensorEntity):
    """A sensor for a KleverKey gateway."""

    entity_description: KleverKeyGatewaySensorDescription

    def __init__(
        self,
        coordinator: KleverKeyDataUpdateCoordinator,
        gateway_id: int,
        description: KleverKeyGatewaySensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, gateway_id, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> StateType | datetime:
        """Return the state of the sensor."""
        return self.entity_description.value_fn(self.gateway)
