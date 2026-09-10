"""Base entities for the KleverKey integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import KleverKeyDataUpdateCoordinator
from .models import Gateway, Lock


class KleverKeyLockEntity(CoordinatorEntity[KleverKeyDataUpdateCoordinator]):
    """Base entity for a lock."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: KleverKeyDataUpdateCoordinator,
        lock_id: int,
        key: str,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._lock_id = lock_id
        self._attr_unique_id = f"lock_{lock_id}_{key}"

        lock = self.lock
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"lock_{lock_id}")},
            manufacturer=MANUFACTURER,
            model=lock.model,
            name=lock.name,
            serial_number=lock.hex_id,
            sw_version=str(lock.firmware_version)
            if lock.firmware_version is not None
            else None,
        )
        if lock.gateway_id is not None:
            self._attr_device_info["via_device"] = (
                DOMAIN,
                f"gateway_{lock.gateway_id}",
            )

    @property
    def lock(self) -> Lock:
        """Return the lock this entity belongs to."""
        return self.coordinator.data.locks[self._lock_id]

    @property
    def available(self) -> bool:
        """Return whether the lock is still reported by the API."""
        return super().available and self._lock_id in self.coordinator.data.locks


class KleverKeyGatewayEntity(CoordinatorEntity[KleverKeyDataUpdateCoordinator]):
    """Base entity for a gateway."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: KleverKeyDataUpdateCoordinator,
        gateway_id: int,
        key: str,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._gateway_id = gateway_id
        self._attr_unique_id = f"gateway_{gateway_id}_{key}"

        gateway = self.gateway
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"gateway_{gateway_id}")},
            manufacturer=MANUFACTURER,
            model=gateway.model,
            name=gateway.name,
            serial_number=gateway.hex_id,
            sw_version=str(gateway.firmware_version)
            if gateway.firmware_version is not None
            else None,
        )

    @property
    def gateway(self) -> Gateway:
        """Return the gateway this entity belongs to."""
        return self.coordinator.data.gateways[self._gateway_id]

    @property
    def available(self) -> bool:
        """Return whether the gateway is still reported by the API."""
        return super().available and self._gateway_id in self.coordinator.data.gateways
