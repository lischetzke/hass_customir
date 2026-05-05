"""Common entity for the Custom IR integration."""

from __future__ import annotations

import logging

from homeassistant.components.infrared import async_send_command
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import Event, EventStateChangedData, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_track_state_change_event

from .catalog import DeviceDef
from .commands import LegacyRawCommand, RawCommand
from .const import CONF_LEGACY_TIMINGS, DEFAULT_LEGACY_TIMINGS, DOMAIN

_LOGGER = logging.getLogger(__name__)


class HassCustomIrEntity(Entity):
    """Base entity for Custom IR — tracks emitter availability."""

    _attr_has_entity_name = True

    def __init__(
        self,
        entry: ConfigEntry,
        infrared_entity_id: str,
        device: DeviceDef,
        unique_id_suffix: str,
    ) -> None:
        """Initialize."""
        self._entry = entry
        self._infrared_entity_id = infrared_entity_id
        self._device = device
        self._attr_unique_id = f"{entry.entry_id}_{unique_id_suffix}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            manufacturer=device.manufacturer or "Custom IR",
            model=device.model,
            name=device.name,
        )

    async def async_added_to_hass(self) -> None:
        """Subscribe to emitter state changes for availability tracking."""
        await super().async_added_to_hass()

        @callback
        def _emitter_state_changed(event: Event[EventStateChangedData]) -> None:
            new_state = event.data["new_state"]
            ir_available = (
                new_state is not None and new_state.state != STATE_UNAVAILABLE
            )
            if ir_available != self.available:
                _LOGGER.info(
                    "IR emitter %s used by %s is %s",
                    self._infrared_entity_id,
                    self.entity_id,
                    "available" if ir_available else "unavailable",
                )
                self._attr_available = ir_available
                self.async_write_ha_state()

        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [self._infrared_entity_id], _emitter_state_changed
            )
        )

        ir_state = self.hass.states.get(self._infrared_entity_id)
        self._attr_available = (
            ir_state is not None and ir_state.state != STATE_UNAVAILABLE
        )

    def _build_command(
        self, cmd_def, *, legacy: bool
    ) -> RawCommand | LegacyRawCommand:
        cmd_cls = LegacyRawCommand if legacy else RawCommand
        return cmd_cls(
            modulation=cmd_def.modulation,
            repeat_count=cmd_def.repeat_count,
            timings=list(cmd_def.timings),
        )

    async def _send(self, command_name: str) -> None:
        """Look up a command by name and send it through the IR proxy.

        If the user has explicitly enabled the legacy compatibility option
        we use it directly. Otherwise we send the modern ``list[int]`` shape
        and, only on the first :class:`AttributeError` complaining about
        ``high_us`` (i.e. an emitter still on the pre-2.0 ``infrared-
        protocols`` API), persist ``legacy_timings=True`` to the config entry
        so subsequent presses skip the failed attempt.
        """
        cmd_def = self._device.commands.get(command_name)
        if cmd_def is None:
            raise HomeAssistantError(
                f"Device '{self._device.key}' has no command '{command_name}'. "
                f"Known commands: {sorted(self._device.commands)}"
            )

        legacy = self._entry.options.get(CONF_LEGACY_TIMINGS, DEFAULT_LEGACY_TIMINGS)

        if not legacy:
            try:
                await async_send_command(
                    self.hass,
                    self._infrared_entity_id,
                    self._build_command(cmd_def, legacy=False),
                    context=self._context,
                )
                return
            except AttributeError as err:
                if "high_us" not in str(err) and "low_us" not in str(err):
                    raise
                _LOGGER.warning(
                    "Auto-enabling legacy timing-pair mode for %s — emitter "
                    "%s is on the pre-2.0 infrared-protocols API "
                    "(it accessed .high_us on a timing element). The proper "
                    "fix is to update Home Assistant / your emitter "
                    "integration; until then we'll keep using legacy timing "
                    "pairs.",
                    self.entity_id,
                    self._infrared_entity_id,
                )
                self.hass.config_entries.async_update_entry(
                    self._entry,
                    options={
                        **self._entry.options,
                        CONF_LEGACY_TIMINGS: True,
                    },
                )
                legacy = True

        await async_send_command(
            self.hass,
            self._infrared_entity_id,
            self._build_command(cmd_def, legacy=True),
            context=self._context,
        )
