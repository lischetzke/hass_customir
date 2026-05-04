"""Validate every device JSON in the bundled catalog and rebuild the index.

Reuses the runtime catalog loader so the validation logic is exactly what HA
will apply at config-flow time.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CATALOG_DIR = REPO_ROOT / "custom_components" / "hass_customir" / "catalog"
DEVICES_DIR = CATALOG_DIR / "devices"
INDEX_PATH = CATALOG_DIR / "index.json"

# Make ``hass_customir`` importable without installing the package.
sys.path.insert(0, str(REPO_ROOT / "custom_components"))

# pylint: disable=wrong-import-position
from hass_customir.catalog import _parse_device  # noqa: E402

_LOGGER = logging.getLogger("validate_catalog")


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if not DEVICES_DIR.is_dir():
        _LOGGER.error("No devices directory at %s", DEVICES_DIR)
        return 1

    failures: list[str] = []
    keys_seen: set[str] = set()
    entries: list[dict] = []

    for path in sorted(DEVICES_DIR.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            device = _parse_device(payload, origin=str(path))
        except Exception as err:  # noqa: BLE001
            failures.append(f"{path}: {err}")
            continue

        if device.key in keys_seen:
            failures.append(f"{path}: duplicate key {device.key!r}")
            continue
        keys_seen.add(device.key)

        entries.append(
            {
                "key": device.key,
                "manufacturer": device.manufacturer,
                "model": device.model,
                "type": device.type,
                "commands": sorted(device.commands.keys()),
            }
        )

    if failures:
        for line in failures:
            _LOGGER.error(line)
        _LOGGER.error("%d device file(s) failed validation", len(failures))
        return 1

    INDEX_PATH.write_text(
        json.dumps(entries, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    _LOGGER.info("Validated %d device(s); wrote %s", len(entries), INDEX_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
