"""Fixtures for the KleverKey tests."""

from __future__ import annotations

from collections.abc import Generator
import re
from typing import Any

from aioresponses import aioresponses
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kleverkey.const import (
    API_BASE_URL,
    CONF_ORGANIZATION_IDS,
    DOMAIN,
)

from .const import API_KEY, GATEWAY, LOCK, ORGANIZATIONS, USER

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: None,
) -> None:
    """Enable loading of the custom integration in every test."""


@pytest.fixture
def mock_api() -> Generator[aioresponses]:
    """Mock the KleverKey API with a working default set of responses."""
    # Let requests to the in-process test HTTP server (used by ``hass_client``)
    # through, so only the KleverKey API is mocked.
    with aioresponses(passthrough=["http://127.0.0.1", "http://localhost"]) as mocked:
        mock_api_responses(mocked)
        yield mocked


def mock_api_responses(
    mocked: aioresponses,
    *,
    locks: list[dict[str, Any]] | None = None,
    gateways: list[dict[str, Any]] | None = None,
    repeat: bool = True,
) -> None:
    """Register the default set of API responses."""
    mocked.get(f"{API_BASE_URL}/api/v1/users/me", payload=USER, repeat=repeat)
    for organization_id, organization in ORGANIZATIONS.items():
        mocked.get(
            f"{API_BASE_URL}/api/v1/organizations/{organization_id}",
            payload=organization,
            repeat=repeat,
        )
    locks = [LOCK] if locks is None else locks
    gateways = [GATEWAY] if gateways is None else gateways
    mocked.get(
        re.compile(rf"^{re.escape(API_BASE_URL)}/api/v1/organizations/1/locks\?.*$"),
        payload={"totalItems": len(locks), "items": locks},
        repeat=repeat,
    )
    mocked.get(
        re.compile(rf"^{re.escape(API_BASE_URL)}/api/v1/organizations/1/gateways\?.*$"),
        payload={"totalItems": len(gateways), "items": gateways},
        repeat=repeat,
    )


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a configured KleverKey config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Acme Corp",
        unique_id=str(USER["id"]),
        data={CONF_API_KEY: API_KEY},
        options={CONF_ORGANIZATION_IDS: [1]},
    )


async def setup_integration(
    hass: HomeAssistant, entry: MockConfigEntry
) -> MockConfigEntry:
    """Add and set up a config entry."""
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry
