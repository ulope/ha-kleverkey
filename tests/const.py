"""Shared test data for the KleverKey integration."""

from __future__ import annotations

from typing import Any

API_KEY = "test-api-key"

USER: dict[str, Any] = {
    "id": 42,
    "email": "user@example.com",
    "displayName": "Test User",
    "organizationId": 1,
    "organizationIds": [1, 2],
}

ORGANIZATIONS: dict[int, dict[str, Any]] = {
    1: {"id": 1, "name": "Acme Corp"},
    2: {"id": 2, "name": "Beta Ltd"},
}

LOCK: dict[str, Any] = {
    "id": 100,
    "organizationId": 1,
    "lockHexId": "AABBCCDD",
    "gatewayId": 200,
    "name": "Front Door",
    "displayName": "Front Door",
    "type": 1,
    "physicalState": 3,
    "state": 1,
    "firmwareVersion": 67329,
    "isFirmwareUpdateAvailable": True,
    "isConnected": True,
    "batteryChangeRecommended": False,
    "powerSource": 100,
    "bleRssi": -67,
    "dieTemperature": 21,
    "weeklyOpeningCount": 12.5,
    "dateBatteryChanged": "2026-01-02T03:04:05Z",
    "dateConnected": "2026-02-03T04:05:06Z",
    "dateDisconnected": None,
    "dateLastActivity": "2026-02-03T05:06:07Z",
    "timezone": "Europe/Zurich",
}

GATEWAY: dict[str, Any] = {
    "id": 200,
    "organizationId": 1,
    "gatewayHexId": "11223344",
    "name": "Hallway Gateway",
    "displayName": "Hallway Gateway",
    "type": 1,
    "firmwareVersion": 66049,
    "isFirmwareUpdateAvailable": False,
    "isConnected": True,
    "wifiRssi": -55,
    "dateConnected": "2026-02-01T00:00:00Z",
    "dateDisconnected": None,
    "dateLastActivity": "2026-02-03T05:00:00Z",
}
