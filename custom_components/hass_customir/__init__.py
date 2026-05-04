"""The Custom IR integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant


def _platforms() -> list:
    # Lazy import keeps this package importable in non-HA contexts (e.g. when
    # the bundled catalog is validated by ``tools/validate_catalog.py``).
    from homeassistant.const import Platform

    return [Platform.BUTTON, Platform.REMOTE]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Custom IR from a config entry."""
    await hass.config_entries.async_forward_entry_setups(entry, _platforms())
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Custom IR config entry."""
    return await hass.config_entries.async_unload_platforms(entry, _platforms())
