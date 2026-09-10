"""Tests for the KleverKey diagnostics."""

from __future__ import annotations

from aioresponses import aioresponses
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.components.diagnostics import (
    get_diagnostics_for_config_entry,
)
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

from .conftest import setup_integration


async def test_diagnostics(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    mock_api: aioresponses,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Diagnostics contain the polled data with secrets redacted."""
    await setup_integration(hass, mock_config_entry)

    diagnostics = await get_diagnostics_for_config_entry(
        hass, hass_client, mock_config_entry
    )

    assert diagnostics["entry"]["data"]["api_key"] == "**REDACTED**"
    assert diagnostics["entry"]["options"] == {"organization_ids": [1]}
    assert len(diagnostics["locks"]) == 1
    assert diagnostics["locks"][0]["id"] == 100
    assert diagnostics["locks"][0]["hex_id"] == "**REDACTED**"
    assert len(diagnostics["gateways"]) == 1
