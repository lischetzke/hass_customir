"""Migrate Flipper-IRDB ``.ir`` files into the Custom IR bundled catalog.

Usage::

    python tools/migrate_flipper.py --src <path/to/Flipper-IRDB[/sub]> [--manufacturer LG]

A Flipper ``.ir`` file represents one remote: it has a header
(``Filetype: IR signals file`` / ``Version: 1``) followed by repeating
``# name: <button>`` blocks. Each block is either:

* ``type: parsed`` with ``protocol: NEC|NECext|SIRC|RC5|RC6|Samsung32`` plus
  hex ``address:`` and ``command:`` fields (LSB-first byte tuples), or
* ``type: raw`` with ``frequency:``, ``duty_cycle:`` and ``data:`` (a list of
  unsigned microsecond durations alternating pulse/space starting with pulse).
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from encoders import (  # noqa: E402
    encode_nec1,
    encode_necext,
    encode_rc5,
    encode_rc6,
    encode_samsung32,
    encode_sirc,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
DEVICES_DIR = REPO_ROOT / "custom_components" / "hass_customir" / "catalog" / "devices"
INDEX_PATH = REPO_ROOT / "custom_components" / "hass_customir" / "catalog" / "index.json"

_LOGGER = logging.getLogger("migrate_flipper")


@dataclass
class _Block:
    name: str
    fields: dict[str, str]


def _slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value


def _hex_lsb(value: str) -> int:
    """Flipper hex fields are space-separated LSB-first bytes."""
    bytes_lsb = [int(b, 16) for b in value.split() if b]
    out = 0
    for i, byte in enumerate(bytes_lsb):
        out |= (byte & 0xFF) << (8 * i)
    return out


def _parse_blocks(text: str) -> list[_Block]:
    blocks: list[_Block] = []
    current: _Block | None = None
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if line.startswith("#"):
            stripped = line[1:].strip()
            if stripped.lower().startswith("name:"):
                if current is not None:
                    blocks.append(current)
                current = _Block(name=stripped.split(":", 1)[1].strip(), fields={})
            continue
        if not line or current is None:
            continue
        if ":" in line:
            key, _, value = line.partition(":")
            current.fields[key.strip().lower()] = value.strip()
    if current is not None:
        blocks.append(current)
    return blocks


def _encode_block(block: _Block) -> tuple[list[int], int] | None:
    btype = block.fields.get("type", "").lower()
    if btype == "raw":
        try:
            freq = int(block.fields["frequency"])
            data = [int(t) for t in block.fields["data"].split()]
        except (KeyError, ValueError) as err:
            _LOGGER.warning("Bad raw block %r: %s", block.name, err)
            return None
        if not data:
            return None
        # Flipper raw is unsigned alternating starting with pulse-on.
        timings = [v if i % 2 == 0 else -v for i, v in enumerate(data)]
        return timings, freq

    if btype != "parsed":
        return None

    protocol = block.fields.get("protocol", "").lower()
    try:
        address = _hex_lsb(block.fields["address"])
        command = _hex_lsb(block.fields["command"])
    except (KeyError, ValueError) as err:
        _LOGGER.warning("Bad parsed block %r: %s", block.name, err)
        return None

    try:
        if protocol == "nec":
            return encode_nec1(address=address & 0xFF, command=command & 0xFF), 38000
        if protocol in ("necext", "nec42", "nec42ext"):
            return encode_necext(address=address & 0xFFFF, command=command & 0xFF), 38000
        if protocol == "samsung32":
            return encode_samsung32(address=address & 0xFF, command=command & 0xFF), 38000
        if protocol == "rc5":
            return encode_rc5(address=address & 0x1F, command=command & 0x7F), 36000
        if protocol == "rc6":
            return encode_rc6(address=address & 0xFF, command=command & 0xFF), 36000
        if protocol in ("sirc", "sirc12"):
            return encode_sirc(address=address & 0x1F, command=command & 0x7F, bits=12), 40000
        if protocol == "sirc15":
            return encode_sirc(address=address & 0xFF, command=command & 0x7F, bits=15), 40000
        if protocol == "sirc20":
            return (
                encode_sirc(
                    address=address & 0x1F,
                    command=command & 0x7F,
                    bits=20,
                    extended=(address >> 5) & 0xFF,
                ),
                40000,
            )
    except ValueError as err:
        _LOGGER.warning("Encode failed for %r: %s", block.name, err)
        return None

    _LOGGER.debug("Unsupported parsed protocol %r in block %r", protocol, block.name)
    return None


def _device_from_ir(path: Path, manufacturer: str | None) -> dict | None:
    text = path.read_text(encoding="utf-8", errors="replace")
    blocks = _parse_blocks(text)
    if not blocks:
        return None

    # Manufacturer/model heuristic: <Category>/<Manufacturer>/<Model>.ir
    rel_parts = path.parts
    inferred_manuf = manufacturer
    if not inferred_manuf and len(rel_parts) >= 3:
        inferred_manuf = rel_parts[-3]
    model = path.stem

    commands: dict[str, dict] = {}
    used: set[str] = set()
    for block in blocks:
        encoded = _encode_block(block)
        if encoded is None:
            continue
        timings, modulation = encoded
        name = _slugify(block.name) or "btn"
        if name in used:
            continue
        used.add(name)
        commands[name] = {
            "modulation": modulation,
            "repeat_count": 0,
            "timings": timings,
        }
    if not commands:
        return None

    key = _slugify(f"{inferred_manuf}_{model}") if inferred_manuf else _slugify(model)
    return {
        "key": key,
        "manufacturer": inferred_manuf,
        "model": model,
        "type": _slugify(rel_parts[-4]) if len(rel_parts) >= 4 else None,
        "source": {"db": "Lucaslhm/Flipper-IRDB", "path": str(path)},
        "commands": dict(sorted(commands.items())),
    }


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
    parser.add_argument("--src", required=True, type=Path, help="Path to a Flipper-IRDB checkout (or sub-folder)")
    parser.add_argument("--manufacturer", help="Override the inferred manufacturer")
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

    written = 0
    for path in sorted(args.src.rglob("*.ir")):
        device = _device_from_ir(path, args.manufacturer)
        if device is None:
            continue
        out_path = DEVICES_DIR / f"{device['key']}.json"
        out_path.write_text(
            json.dumps(device, indent=2) + "\n",
            encoding="utf-8",
        )
        written += 1
        if args.limit and written >= args.limit:
            _LOGGER.info("Hit --limit=%d, stopping", args.limit)
            break

    _LOGGER.info("Wrote %d device file(s) to %s", written, DEVICES_DIR)
    _rebuild_index()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
