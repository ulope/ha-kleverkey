"""Tests for setting up and unloading the KleverKey integration."""

from __future__ import annotations

import re

from aioresponses import aioresponses
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kleverkey.const import (
    API_BASE_URL,
    CONF_ORGANIZATION_IDS,
    DOMAIN,
)

from .conftest import setup_integration


async def test_setup_and_unload(
    hass: HomeAssistant, mock_api: aioresponses, mock_config_entry: MockConfigEntry
) -> None:
    """The entry loads and unloads cleanly."""
    await setup_integration(hass, mock_config_entry)
    assert mock_config_entry.state is ConfigEntryState.LOADED

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED


async def test_setup_without_organizations(
    hass: HomeAssistant, mock_api: aioresponses
) -> None:
    """An entry without organizations is retried instead of loading empty."""
    entry = MockConfigEntry(
        domain=DOMAIN, data={"api_key": "x"}, options={CONF_ORGANIZATION_IDS: []}
    )
    await setup_integration(hass, entry)
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_setup_starts_reauth_on_invalid_key(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """A rejected API key puts the entry into the re-authentication state."""
    with aioresponses() as mocked:
        mocked.get(
            re.compile(rf"^{re.escape(API_BASE_URL)}/api/v1/organizations/1/.*$"),
            status=401,
            repeat=True,
        )
        await setup_integration(hass, mock_config_entry)

    assert mock_config_entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert [flow["context"]["source"] for flow in flows] == ["reauth"]


async def test_devices(
    hass: HomeAssistant, mock_api: aioresponses, mock_config_entry: MockConfigEntry
) -> None:
    """A device is created per lock and gateway, with the lock behind its gateway."""
    await setup_integration(hass, mock_config_entry)

    device_registry = dr.async_get(hass)
    gateway = device_registry.async_get_device({(DOMAIN, "gateway_200")})
    lock = device_registry.async_get_device({(DOMAIN, "lock_100")})

    assert gateway is not None
    assert gateway.name == "Hallway Gateway"
    assert gateway.model == "Wi-Fi Gateway"
    assert gateway.sw_version == "1.2.1"

    assert lock is not None
    assert lock.name == "Front Door"
    assert lock.model == "Lock B1"
    assert lock.sw_version == "1.7.1"
    assert lock.via_device_id == gateway.id


async def test_device_removal(
    hass: HomeAssistant,
    hass_ws_client,
    mock_api: aioresponses,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Stale devices can be removed, current ones cannot."""
    from custom_components.kleverkey import async_remove_config_entry_device

    await setup_integration(hass, mock_config_entry)
    device_registry = dr.async_get(hass)

    current = device_registry.async_get_device({(DOMAIN, "lock_100")})
    assert not await async_remove_config_entry_device(hass, mock_config_entry, current)

    stale = device_registry.async_get_or_create(
        config_entry_id=mock_config_entry.entry_id,
        identifiers={(DOMAIN, "lock_999")},
    )
    assert await async_remove_config_entry_device(hass, mock_config_entry, stale)
