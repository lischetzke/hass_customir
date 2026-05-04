"""Remote platform for Custom IR.

Exposes one ``remote`` entity whose ``send_command`` service accepts the
named commands defined in the device's catalog entry.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
from typing import Any

from homeassistant.components.remote import (
    ATTR_DELAY_SECS,
    ATTR_NUM_REPEATS,
    DEFAULT_DELAY_SECS,
    DEFAULT_NUM_REPEATS,
    RemoteEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .catalog import DeviceDef, async_load_catalog
from .const import CONF_DEVICE_KEY, CONF_INFRARED_ENTITY_ID
from .entity import HassCustomIrEntity

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Custom IR remote entity."""
    catalog = await async_load_catalog(hass)
    device_key = entry.data[CONF_DEVICE_KEY]
    device = catalog.get(device_key)
    if device is None:
        raise ConfigEntryNotReady(f"Device '{device_key}' not in catalog")

    async_add_entities(
        [HassCustomIrRemote(entry, entry.data[CONF_INFRARED_ENTITY_ID], device)]
    )


class HassCustomIrRemote(HassCustomIrEntity, RemoteEntity):
    """A remote entity wrapping a Custom IR device's named commands."""

    _attr_assumed_state = True
    _attr_name = None

    def __init__(
        self,
        entry: ConfigEntry,
        infrared_entity_id: str,
        device: DeviceDef,
    ) -> None:
        """Initialize."""
        super().__init__(
            entry,
            infrared_entity_id,
            device,
            unique_id_suffix="remote",
        )
        self._attr_state = STATE_ON
        self._attr_is_on = True

    async def async_send_command(self, command: Iterable[str], **kwargs: Any) -> None:
        """Send a sequence of named IR commands.

        ``command`` is the list passed via ``remote.send_command``'s
        ``command:`` field. Standard ``num_repeats`` and ``delay_secs`` apply.
        """
        commands = list(command)
        if not commands:
            return

        unknown = [c for c in commands if c not in self._device.commands]
        if unknown:
            raise HomeAssistantError(
                f"Device '{self._device.key}' has no command(s) {unknown}. "
                f"Known: {sorted(self._device.commands)}"
            )

        repeats: int = int(kwargs.get(ATTR_NUM_REPEATS, DEFAULT_NUM_REPEATS))
        delay: float = float(kwargs.get(ATTR_DELAY_SECS, DEFAULT_DELAY_SECS))

        for _ in range(max(1, repeats)):
            for idx, name in enumerate(commands):
                if idx > 0 and delay > 0:
                    await asyncio.sleep(delay)
                await self._send(name)
