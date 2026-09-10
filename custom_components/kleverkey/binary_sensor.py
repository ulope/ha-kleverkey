"""Binary sensors for KleverKey locks and gateways."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import KleverKeyConfigEntry, KleverKeyDataUpdateCoordinator
from .entity import KleverKeyGatewayEntity, KleverKeyLockEntity
from .models import Gateway, Lock, LockPhysicalState, LockState


@dataclass(frozen=True, kw_only=True)
class KleverKeyLockBinarySensorDescription(BinarySensorEntityDescription):
    """Describes a KleverKey lock binary sensor."""

    value_fn: Callable[[Lock], bool | None]


@dataclass(frozen=True, kw_only=True)
class KleverKeyGatewayBinarySensorDescription(BinarySensorEntityDescription):
    """Describes a KleverKey gateway binary sensor."""

    value_fn: Callable[[Gateway], bool | None]


def _lock_locked(lock: Lock) -> bool | None:
    """Return whether the lock is unlocked (``True``) or locked (``False``)."""
    if lock.physical_state is None or lock.physical_state is LockPhysicalState.UNKNOWN:
        return None
    return lock.physical_state is not LockPhysicalState.LOCKED


LOCK_DESCRIPTIONS: tuple[KleverKeyLockBinarySensorDescription, ...] = (
    KleverKeyLockBinarySensorDescription(
        key="lock",
        device_class=BinarySensorDeviceClass.LOCK,
        value_fn=_lock_locked,
    ),
    KleverKeyLockBinarySensorDescription(
        key="door",
        device_class=BinarySensorDeviceClass.DOOR,
        value_fn=lambda lock: (
            None
            if lock.physical_state is None
            or lock.physical_state is LockPhysicalState.UNKNOWN
            else lock.physical_state is LockPhysicalState.OPEN
        ),
    ),
    KleverKeyLockBinarySensorDescription(
        key="connectivity",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda lock: lock.is_connected,
    ),
    KleverKeyLockBinarySensorDescription(
        key="battery",
        device_class=BinarySensorDeviceClass.BATTERY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda lock: (
            bool(lock.state & LockState.BATTERY_LOW) or lock.battery_change_recommended
        ),
    ),
    KleverKeyLockBinarySensorDescription(
        key="emergency",
        translation_key="emergency",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda lock: bool(lock.state & LockState.EMERGENCY),
    ),
    KleverKeyLockBinarySensorDescription(
        key="firmware_update",
        device_class=BinarySensorDeviceClass.UPDATE,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda lock: lock.firmware_update_available,
    ),
)

GATEWAY_DESCRIPTIONS: tuple[KleverKeyGatewayBinarySensorDescription, ...] = (
    KleverKeyGatewayBinarySensorDescription(
        key="connectivity",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda gateway: gateway.is_connected,
    ),
    KleverKeyGatewayBinarySensorDescription(
        key="firmware_update",
        device_class=BinarySensorDeviceClass.UPDATE,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda gateway: gateway.firmware_update_available,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KleverKeyConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the KleverKey binary sensors."""
    coordinator = entry.runtime_data
    known: set[str] = set()

    @callback
    def _async_add_entities() -> None:
        entities: list[BinarySensorEntity] = []
        for lock_id in coordinator.data.locks:
            for description in LOCK_DESCRIPTIONS:
                if (unique := f"lock_{lock_id}_{description.key}") in known:
                    continue
                known.add(unique)
                entities.append(
                    KleverKeyLockBinarySensor(coordinator, lock_id, description)
                )
        for gateway_id in coordinator.data.gateways:
            for gateway_description in GATEWAY_DESCRIPTIONS:
                if (
                    unique := f"gateway_{gateway_id}_{gateway_description.key}"
                ) in known:
                    continue
                known.add(unique)
                entities.append(
                    KleverKeyGatewayBinarySensor(
                        coordinator, gateway_id, gateway_description
                    )
                )
        async_add_entities(entities)

    _async_add_entities()
    entry.async_on_unload(coordinator.async_add_listener(_async_add_entities))


class KleverKeyLockBinarySensor(KleverKeyLockEntity, BinarySensorEntity):
    """A binary sensor for a KleverKey lock."""

    entity_description: KleverKeyLockBinarySensorDescription

    def __init__(
        self,
        coordinator: KleverKeyDataUpdateCoordinator,
        lock_id: int,
        description: KleverKeyLockBinarySensorDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, lock_id, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return the state of the binary sensor."""
        return self.entity_description.value_fn(self.lock)


class KleverKeyGatewayBinarySensor(KleverKeyGatewayEntity, BinarySensorEntity):
    """A binary sensor for a KleverKey gateway."""

    entity_description: KleverKeyGatewayBinarySensorDescription

    def __init__(
        self,
        coordinator: KleverKeyDataUpdateCoordinator,
        gateway_id: int,
        description: KleverKeyGatewayBinarySensorDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, gateway_id, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return the state of the binary sensor."""
        return self.entity_description.value_fn(self.gateway)
