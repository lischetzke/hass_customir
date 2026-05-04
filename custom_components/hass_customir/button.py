"""Button platform for Custom IR — one button per command."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .catalog import DeviceDef, async_load_catalog
from .const import CONF_DEVICE_KEY, CONF_INFRARED_ENTITY_ID
from .entity import HassCustomIrEntity

PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class HassCustomIrButtonDescription(ButtonEntityDescription):
    """Describes a Custom IR button entity."""

    command_name: str


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Custom IR buttons from a config entry."""
    catalog = await async_load_catalog(hass)
    device_key = entry.data[CONF_DEVICE_KEY]
    device = catalog.get(device_key)
    if device is None:
        raise ConfigEntryNotReady(f"Device '{device_key}' not in catalog")

    infrared_entity_id = entry.data[CONF_INFRARED_ENTITY_ID]

    descriptions = tuple(
        HassCustomIrButtonDescription(
            key=name,
            translation_key=name,
            name=name.replace("_", " ").title(),
            command_name=name,
        )
        for name in sorted(device.commands)
    )

    async_add_entities(
        HassCustomIrButton(entry, infrared_entity_id, device, description)
        for description in descriptions
    )


class HassCustomIrButton(HassCustomIrEntity, ButtonEntity):
    """A single Custom IR button."""

    entity_description: HassCustomIrButtonDescription

    def __init__(
        self,
        entry: ConfigEntry,
        infrared_entity_id: str,
        device: DeviceDef,
        description: HassCustomIrButtonDescription,
    ) -> None:
        """Initialize."""
        super().__init__(
            entry,
            infrared_entity_id,
            device,
            unique_id_suffix=f"button_{description.key}",
        )
        self.entity_description = description

    async def async_press(self) -> None:
        """Send the IR command."""
        await self._send(self.entity_description.command_name)
