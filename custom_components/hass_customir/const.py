"""Constants for the Custom IR integration."""

from __future__ import annotations

from pathlib import Path
from typing import Final

DOMAIN: Final = "hass_customir"

CONF_INFRARED_ENTITY_ID: Final = "infrared_entity_id"
CONF_DEVICE_KEY: Final = "device_key"
CONF_MANUFACTURER: Final = "manufacturer"
CONF_LEGACY_TIMINGS: Final = "legacy_timings"
DEFAULT_LEGACY_TIMINGS: Final = False

# Synthetic "manufacturer" sentinel for devices that have none set.
MANUFACTURER_OTHER: Final = "__other__"

# Bundled catalog is committed alongside the integration source.
BUNDLED_CATALOG_DIR: Final = Path(__file__).parent / "catalog"
BUNDLED_CATALOG_INDEX: Final = BUNDLED_CATALOG_DIR / "index.json"
BUNDLED_DEVICES_DIR: Final = BUNDLED_CATALOG_DIR / "devices"

# Users can drop YAML/JSON device files here; they overlay the bundled catalog.
USER_DEVICES_SUBDIR: Final = "customir_devices"

# Sane modulation bounds used by validate_catalog and the runtime loader.
MIN_MODULATION_HZ: Final = 30_000
MAX_MODULATION_HZ: Final = 60_000
