"""Buttons for KleverKey locks and gateways."""

from __future__ import annotations

from homeassistant.components.button import (
    ButtonDeviceClass,
    ButtonEntity,
    ButtonEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import KleverKeyError
from .const import DOMAIN
from .coordinator import KleverKeyConfigEntry, KleverKeyDataUpdateCoordinator
from .entity import KleverKeyGatewayEntity, KleverKeyLockEntity

RESTART_DESCRIPTION = ButtonEntityDescription(
    key="restart",
    device_class=ButtonDeviceClass.RESTART,
    entity_category=EntityCategory.CONFIG,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KleverKeyConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the KleverKey buttons."""
    coordinator = entry.runtime_data
    known: set[str] = set()

    @callback
    def _async_add_entities() -> None:
        entities: list[ButtonEntity] = []
        for lock_id in coordinator.data.locks:
            if (unique := f"lock_{lock_id}") in known:
                continue
            known.add(unique)
            entities.append(KleverKeyLockRestartButton(coordinator, lock_id))
        for gateway_id in coordinator.data.gateways:
            if (unique := f"gateway_{gateway_id}") in known:
                continue
            known.add(unique)
            entities.append(KleverKeyGatewayRestartButton(coordinator, gateway_id))
        async_add_entities(entities)

    _async_add_entities()
    entry.async_on_unload(coordinator.async_add_listener(_async_add_entities))


class KleverKeyLockRestartButton(KleverKeyLockEntity, ButtonEntity):
    """Restart a lock."""

    entity_description = RESTART_DESCRIPTION

    def __init__(
        self, coordinator: KleverKeyDataUpdateCoordinator, lock_id: int
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator, lock_id, RESTART_DESCRIPTION.key)

    async def async_press(self) -> None:
        """Restart the lock."""
        lock = self.lock
        try:
            await self.coordinator.client.async_restart_lock(
                lock.organization_id, lock.id
            )
        except KleverKeyError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="restart_failed",
                translation_placeholders={"name": lock.name, "error": str(err)},
            ) from err


class KleverKeyGatewayRestartButton(KleverKeyGatewayEntity, ButtonEntity):
    """Restart a gateway."""

    entity_description = RESTART_DESCRIPTION

    def __init__(
        self, coordinator: KleverKeyDataUpdateCoordinator, gateway_id: int
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator, gateway_id, RESTART_DESCRIPTION.key)

    async def async_press(self) -> None:
        """Restart the gateway."""
        gateway = self.gateway
        try:
            await self.coordinator.client.async_restart_gateway(
                gateway.organization_id, gateway.id
            )
        except KleverKeyError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="restart_failed",
                translation_placeholders={"name": gateway.name, "error": str(err)},
            ) from err
