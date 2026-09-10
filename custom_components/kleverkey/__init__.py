"""The KleverKey integration."""

from __future__ import annotations

from homeassistant.const import CONF_API_KEY, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceEntry

from .api import KleverKeyClient
from .const import CONF_ORGANIZATION_IDS, DOMAIN
from .coordinator import KleverKeyConfigEntry, KleverKeyDataUpdateCoordinator

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.SENSOR,
]


def _organization_ids(entry: KleverKeyConfigEntry) -> list[int]:
    """Return the organizations the entry is configured for."""
    raw = entry.options.get(
        CONF_ORGANIZATION_IDS, entry.data.get(CONF_ORGANIZATION_IDS, [])
    )
    return [int(organization_id) for organization_id in raw]


async def async_setup_entry(hass: HomeAssistant, entry: KleverKeyConfigEntry) -> bool:
    """Set up KleverKey from a config entry."""
    organization_ids = _organization_ids(entry)
    if not organization_ids:
        raise ConfigEntryNotReady("No organizations selected for this entry")

    client = KleverKeyClient(entry.data[CONF_API_KEY], async_get_clientsession(hass))
    coordinator = KleverKeyDataUpdateCoordinator(hass, entry, client, organization_ids)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: KleverKeyConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(hass: HomeAssistant, entry: KleverKeyConfigEntry) -> None:
    """Reload the entry when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: KleverKeyConfigEntry, device: DeviceEntry
) -> bool:
    """Allow removing devices that are no longer reported by the API."""
    if (coordinator := getattr(entry, "runtime_data", None)) is None:
        return True
    known = {
        *(f"lock_{lock_id}" for lock_id in coordinator.data.locks),
        *(f"gateway_{gateway_id}" for gateway_id in coordinator.data.gateways),
    }
    return not any(
        identifier in known
        for domain, identifier in device.identifiers
        if domain == DOMAIN
    )
