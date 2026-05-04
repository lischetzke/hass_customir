"""Catalog loader for Custom IR.

Loads device definitions from two places, in order:

1. ``custom_components/hass_customir/catalog/devices/*.json`` — bundled catalog.
2. ``<config>/customir_devices/*.{json,yaml,yml}`` — user overlay. User files
   with a key already in the bundled catalog override the bundled entry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .const import (
    BUNDLED_DEVICES_DIR,
    MAX_MODULATION_HZ,
    MIN_MODULATION_HZ,
    USER_DEVICES_SUBDIR,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class CatalogError(Exception):
    """Raised when a catalog file is malformed."""


@dataclass(frozen=True, slots=True)
class CommandDef:
    """One IR command — pre-encoded raw timings."""

    modulation: int
    repeat_count: int
    timings: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class DeviceDef:
    """One device — a named bundle of commands."""

    key: str
    manufacturer: str | None
    model: str | None
    type: str | None
    commands: dict[str, CommandDef]
    source: dict[str, Any] = field(default_factory=dict)

    @property
    def name(self) -> str:
        """Human label used in dropdowns and device registry."""
        parts = [p for p in (self.manufacturer, self.model) if p]
        return " ".join(parts) if parts else self.key


def _parse_device(payload: dict[str, Any], *, origin: str) -> DeviceDef:
    """Validate and convert a parsed JSON/YAML payload into a DeviceDef."""
    try:
        key = payload["key"]
        commands_raw = payload["commands"]
    except KeyError as err:
        raise CatalogError(f"{origin}: missing required field {err.args[0]!r}") from err

    if not isinstance(key, str) or not key:
        raise CatalogError(f"{origin}: 'key' must be a non-empty string")
    if not isinstance(commands_raw, dict) or not commands_raw:
        raise CatalogError(f"{origin}: 'commands' must be a non-empty mapping")

    commands: dict[str, CommandDef] = {}
    for name, raw in commands_raw.items():
        if not isinstance(name, str) or not name or any(c.isspace() for c in name):
            raise CatalogError(
                f"{origin}: command name {name!r} is empty or contains whitespace"
            )
        if not isinstance(raw, dict):
            raise CatalogError(f"{origin}: command {name!r} must be a mapping")

        modulation = int(raw.get("modulation", 38000))
        if not MIN_MODULATION_HZ <= modulation <= MAX_MODULATION_HZ:
            raise CatalogError(
                f"{origin}: command {name!r} modulation {modulation} out of range "
                f"[{MIN_MODULATION_HZ}, {MAX_MODULATION_HZ}]"
            )

        repeat_count = int(raw.get("repeat_count", 0))
        if repeat_count < 0:
            raise CatalogError(
                f"{origin}: command {name!r} repeat_count must be >= 0"
            )

        timings_raw = raw.get("timings")
        if not isinstance(timings_raw, list) or not timings_raw:
            raise CatalogError(f"{origin}: command {name!r} 'timings' must be a non-empty list")
        timings: list[int] = []
        for value in timings_raw:
            if not isinstance(value, int) or isinstance(value, bool) or value == 0:
                raise CatalogError(
                    f"{origin}: command {name!r} timings must be non-zero ints"
                )
            timings.append(value)

        # Pulse/space alternation: positive then negative then positive ...
        for idx, value in enumerate(timings):
            expected_positive = idx % 2 == 0
            if expected_positive and value <= 0:
                raise CatalogError(
                    f"{origin}: command {name!r} expected pulse (>0) at index {idx}, got {value}"
                )
            if not expected_positive and value >= 0:
                raise CatalogError(
                    f"{origin}: command {name!r} expected space (<0) at index {idx}, got {value}"
                )

        commands[name] = CommandDef(
            modulation=modulation,
            repeat_count=repeat_count,
            timings=tuple(timings),
        )

    return DeviceDef(
        key=str(key),
        manufacturer=payload.get("manufacturer"),
        model=payload.get("model"),
        type=payload.get("type"),
        commands=commands,
        source=dict(payload.get("source") or {}),
    )


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_yaml(path: Path) -> dict[str, Any]:
    # Local import: PyYAML ships with Home Assistant, but keep load lazy so
    # this module can be imported in non-HA contexts (e.g. unit tests).
    import yaml

    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _load_dir(directory: Path) -> dict[str, DeviceDef]:
    """Load every device file in a directory; ignore unrelated files."""
    out: dict[str, DeviceDef] = {}
    if not directory.is_dir():
        return out
    for path in sorted(directory.iterdir()):
        if path.suffix.lower() == ".json":
            payload = _read_json(path)
        elif path.suffix.lower() in (".yaml", ".yml"):
            payload = _read_yaml(path)
        else:
            continue
        try:
            device = _parse_device(payload, origin=str(path))
        except CatalogError as err:
            _LOGGER.warning("Skipping malformed device file: %s", err)
            continue
        if device.key in out:
            _LOGGER.warning(
                "Duplicate device key %r in %s — keeping first occurrence",
                device.key,
                directory,
            )
            continue
        out[device.key] = device
    return out


def load_catalog_sync(hass: HomeAssistant) -> dict[str, DeviceDef]:
    """Synchronous catalog load — call via ``async_add_executor_job``."""
    catalog: dict[str, DeviceDef] = {}
    catalog.update(_load_dir(BUNDLED_DEVICES_DIR))

    user_dir = Path(hass.config.path(USER_DEVICES_SUBDIR))
    user_devices = _load_dir(user_dir)
    if user_devices:
        _LOGGER.info(
            "Loaded %d user device(s) from %s (overlaying bundled catalog)",
            len(user_devices),
            user_dir,
        )
        catalog.update(user_devices)

    return catalog


async def async_load_catalog(hass: HomeAssistant) -> dict[str, DeviceDef]:
    """Load the catalog off the event loop."""
    return await hass.async_add_executor_job(load_catalog_sync, hass)
