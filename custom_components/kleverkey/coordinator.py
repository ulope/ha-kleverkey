"""Data update coordinator for the KleverKey integration."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    KleverKeyAuthenticationError,
    KleverKeyClient,
    KleverKeyError,
)
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .models import Gateway, Lock

_LOGGER = logging.getLogger(__name__)

type KleverKeyConfigEntry = ConfigEntry[KleverKeyDataUpdateCoordinator]


@dataclass(slots=True)
class KleverKeyData:
    """Locks and gateways of all configured organizations."""

    locks: dict[int, Lock] = field(default_factory=dict)
    gateways: dict[int, Gateway] = field(default_factory=dict)


class KleverKeyDataUpdateCoordinator(DataUpdateCoordinator[KleverKeyData]):
    """Fetch locks and gateways for the selected organizations."""

    config_entry: KleverKeyConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: KleverKeyConfigEntry,
        client: KleverKeyClient,
        organization_ids: list[int],
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.client = client
        self.organization_ids = organization_ids

    async def _async_update_data(self) -> KleverKeyData:
        """Fetch the current locks and gateways."""
        try:
            results = await asyncio.gather(
                *(
                    self.client.async_get_locks(organization_id)
                    for organization_id in self.organization_ids
                ),
                *(
                    self.client.async_get_gateways(organization_id)
                    for organization_id in self.organization_ids
                ),
            )
        except KleverKeyAuthenticationError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except KleverKeyError as err:
            raise UpdateFailed(str(err)) from err

        split = len(self.organization_ids)
        data = KleverKeyData()
        for locks in results[:split]:
            for lock in locks:
                data.locks[lock.id] = lock
        for gateways in results[split:]:
            for gateway in gateways:
                data.gateways[gateway.id] = gateway
        return data
