"""Constants for the KleverKey integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "kleverkey"

MANUFACTURER: Final = "KleverKey"

CONF_ORGANIZATION_IDS: Final = "organization_ids"

DEFAULT_SCAN_INTERVAL: Final = timedelta(seconds=60)

API_BASE_URL: Final = "https://api.kleverkey.com"
API_TIMEOUT: Final = 30

# The API caps ``PageSize`` at 100'000 items, which is far more than any
# realistic organization holds, so a single request is always enough.
API_PAGE_SIZE: Final = 1000
