"""Migrate probonopd/irdb CSV files into the Custom IR bundled catalog.

Usage::

    python tools/migrate_irdb.py --src <path/to/irdb_clone> [filters...]

One CSV file in irdb represents one remote (one device). Each row is a named
function plus its protocol/device/subdevice/function values. We translate
every supported row into raw timings and emit a single device JSON per CSV.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

# Make sibling package importable when running as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from encoders import encode_by_protocol  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
DEVICES_DIR = REPO_ROOT / "custom_components" / "hass_customir" / "catalog" / "devices"
INDEX_PATH = REPO_ROOT / "custom_components" / "hass_customir" / "catalog" / "index.json"

_LOGGER = logging.getLogger("migrate_irdb")


@dataclass
class _Row:
    function_name: str
    protocol: str
    device: int
    subdevice: int
    function: int


def _slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value


def _parse_csv(path: Path) -> list[_Row]:
    rows: list[_Row] = []
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for raw in reader:
            try:
                rows.append(
                    _Row(
                        function_name=raw["functionname"],
                        protocol=raw["protocol"],
                        device=int(raw["device"]),
                        subdevice=int(raw["subdevice"]),
                        function=int(raw["function"]),
                    )
                )
            except (KeyError, ValueError) as err:
                _LOGGER.warning("Skipping malformed row in %s: %s", path, err)
    return rows


def _device_from_csv(
    path: Path, manufacturer: str, device_type: str
) -> dict | None:
    rows = _parse_csv(path)
    if not rows:
        return None

    # Path looks like: codes/<manufacturer>/<device_type>/<device,subdevice>.csv
    addr = path.stem  # e.g. "4,-1"
    key_base = _slugify(f"{manufacturer}_{device_type}_{addr}")
    commands: dict[str, dict] = {}
    used_names: set[str] = set()

    for row in rows:
        try:
            timings, modulation = encode_by_protocol(
                row.protocol,
                device=row.device,
                subdevice=row.subdevice,
                function=row.function,
            )
        except NotImplementedError as err:
            _LOGGER.debug("Skipping %s::%s: %s", path, row.function_name, err)
            continue
        except ValueError as err:
            _LOGGER.warning(
                "Skipping %s::%s: %s", path, row.function_name, err
            )
            continue

        name = _slugify(row.function_name)
        if not name:
            continue
        if name in used_names:
            # Collisions happen when irdb has duplicate function names with
            # different params; keep the first.
            continue
        used_names.add(name)
        commands[name] = {
            "modulation": modulation,
            "repeat_count": 0,
            "timings": timings,
        }

    if not commands:
        _LOGGER.info("No supported commands in %s — skipping device", path)
        return None

    return {
        "key": key_base,
        "manufacturer": manufacturer,
        "model": addr,
        "type": _slugify(device_type),
        "source": {
            "db": "probonopd/irdb",
            "path": str(path.relative_to(path.parents[3]) if len(path.parents) >= 4 else path),
        },
        "commands": commands,
    }


def _walk(src: Path, manufacturer_filter: str | None, type_filter: str | None) -> list[Path]:
    codes_root = src / "codes" if (src / "codes").is_dir() else src
    out: list[Path] = []
    for path in codes_root.rglob("*.csv"):
        try:
            rel = path.relative_to(codes_root)
        except ValueError:
            continue
        # rel = <Manufacturer>/<DeviceType>/<addr>.csv
        if len(rel.parts) < 3:
            continue
        manufacturer, device_type = rel.parts[0], rel.parts[1]
        if manufacturer_filter and manufacturer.lower() != manufacturer_filter.lower():
            continue
        if type_filter and device_type.lower() != type_filter.lower():
            continue
        out.append(path)
    return out


def _rebuild_index() -> None:
    entries: list[dict] = []
    for path in sorted(DEVICES_DIR.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        entries.append(
            {
                "key": payload["key"],
                "manufacturer": payload.get("manufacturer"),
                "model": payload.get("model"),
                "type": payload.get("type"),
                "commands": sorted(payload["commands"].keys()),
            }
        )
    INDEX_PATH.write_text(
        json.dumps(entries, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    _LOGGER.info("Wrote %s with %d device(s)", INDEX_PATH, len(entries))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--src", required=True, type=Path, help="Path to a probonopd/irdb checkout")
    parser.add_argument("--manufacturer", help="Filter to a single manufacturer (e.g. 'LG')")
    parser.add_argument("--device-type", help="Filter to a single device type (e.g. 'TV')")
    parser.add_argument("--limit", type=int, default=0, help="Max devices to emit (0 = unlimited)")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    if not args.src.is_dir():
        parser.error(f"--src not a directory: {args.src}")
    DEVICES_DIR.mkdir(parents=True, exist_ok=True)

    csv_paths = _walk(args.src, args.manufacturer, args.device_type)
    _LOGGER.info("Discovered %d CSV file(s) to process", len(csv_paths))

    written = 0
    for path in csv_paths:
        manufacturer = path.parents[1].name
        device_type = path.parents[0].name
        device = _device_from_csv(path, manufacturer, device_type)
        if device is None:
            continue
        out_path = DEVICES_DIR / f"{device['key']}.json"
        out_path.write_text(
            json.dumps(_compact_device(device), indent=2) + "\n",
            encoding="utf-8",
        )
        written += 1
        if args.limit and written >= args.limit:
            _LOGGER.info("Hit --limit=%d, stopping", args.limit)
            break

    _LOGGER.info("Wrote %d device file(s) to %s", written, DEVICES_DIR)
    _rebuild_index()
    return 0


def _compact_device(device: dict) -> dict:
    """Stable ordering for diff-friendly catalog files."""
    return {
        "key": device["key"],
        "manufacturer": device.get("manufacturer"),
        "model": device.get("model"),
        "type": device.get("type"),
        "source": device.get("source", {}),
        "commands": dict(sorted(device["commands"].items())),
    }


if __name__ == "__main__":
    raise SystemExit(main())
