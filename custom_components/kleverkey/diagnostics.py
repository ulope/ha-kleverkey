"""Diagnostics support for the KleverKey integration."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant

from .const import CONF_ORGANIZATION_IDS
from .coordinator import KleverKeyConfigEntry

TO_REDACT = {CONF_API_KEY, "hex_id", "serial_number"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: KleverKeyConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    return {
        "entry": {
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": {
                CONF_ORGANIZATION_IDS: entry.options.get(CONF_ORGANIZATION_IDS, [])
            },
        },
        "locks": [
            async_redact_data(asdict(lock), TO_REDACT)
            for lock in coordinator.data.locks.values()
        ],
        "gateways": [
            async_redact_data(asdict(gateway), TO_REDACT)
            for gateway in coordinator.data.gateways.values()
        ],
    }
