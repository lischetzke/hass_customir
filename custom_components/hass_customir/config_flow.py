"""Config + options flow for Custom IR.

Two-step config flow:

1. ``async_step_user`` — pick the **manufacturer** (devices in the catalog
   are grouped by manufacturer) and the **IR proxy emitter** entity.
2. ``async_step_device`` — pick the specific **model** for that manufacturer.

Both steps use ``SelectSelector(mode=DROPDOWN)`` which supports type-ahead
search in the Home Assistant frontend, so even long lists stay usable.

The options flow exposes a single *Legacy timing pairs* boolean — see
``commands.LegacyRawCommand`` for the rationale.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components.infrared import (
    DOMAIN as INFRARED_DOMAIN,
    async_get_emitters,
)
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.selector import (
    BooleanSelector,
    EntitySelector,
    EntitySelectorConfig,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .catalog import DeviceDef, async_load_catalog
from .const import (
    CONF_DEVICE_KEY,
    CONF_INFRARED_ENTITY_ID,
    CONF_LEGACY_TIMINGS,
    CONF_MANUFACTURER,
    DEFAULT_LEGACY_TIMINGS,
    DOMAIN,
    MANUFACTURER_OTHER,
)


def _manufacturer_label(value: str | None) -> str:
    """Display label for a manufacturer; ``None`` is shown as 'Other'."""
    return value if value else "Other"


def _group_by_manufacturer(
    catalog: dict[str, DeviceDef],
) -> dict[str, list[DeviceDef]]:
    """Group devices by manufacturer; ``MANUFACTURER_OTHER`` for unset values."""
    groups: dict[str, list[DeviceDef]] = {}
    for device in catalog.values():
        key = device.manufacturer or MANUFACTURER_OTHER
        groups.setdefault(key, []).append(device)
    for devices in groups.values():
        devices.sort(key=lambda d: (d.model or d.key).lower())
    return groups


class HassCustomIrConfigFlow(ConfigFlow, domain=DOMAIN):
    """Two-step config flow for Custom IR."""

    VERSION = 1

    def __init__(self) -> None:
        super().__init__()
        self._catalog: dict[str, DeviceDef] = {}
        self._groups: dict[str, list[DeviceDef]] = {}
        self._emitter_entity_id: str | None = None
        self._manufacturer: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 1 — pick manufacturer + IR proxy emitter."""
        emitter_ids = async_get_emitters(self.hass)
        if not emitter_ids:
            return self.async_abort(reason="no_emitters")

        self._catalog = await async_load_catalog(self.hass)
        if not self._catalog:
            return self.async_abort(reason="no_devices")

        self._groups = _group_by_manufacturer(self._catalog)

        if user_input is not None:
            self._manufacturer = user_input[CONF_MANUFACTURER]
            self._emitter_entity_id = user_input[CONF_INFRARED_ENTITY_ID]
            return await self.async_step_device()

        manuf_options = [
            SelectOptionDict(
                value=key,
                label=f"{_manufacturer_label(None if key == MANUFACTURER_OTHER else key)}"
                f"  ({len(devices)})",
            )
            for key, devices in sorted(
                self._groups.items(), key=lambda kv: _manufacturer_label(
                    None if kv[0] == MANUFACTURER_OTHER else kv[0]
                ).lower()
            )
        ]

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_MANUFACTURER): SelectSelector(
                        SelectSelectorConfig(
                            options=manuf_options,
                            mode=SelectSelectorMode.DROPDOWN,
                            sort=False,
                            custom_value=False,
                        )
                    ),
                    vol.Required(CONF_INFRARED_ENTITY_ID): EntitySelector(
                        EntitySelectorConfig(
                            domain=INFRARED_DOMAIN,
                            include_entities=emitter_ids,
                        )
                    ),
                }
            ),
            description_placeholders={
                "device_count": str(len(self._catalog)),
                "manufacturer_count": str(len(self._groups)),
            },
        )

    async def async_step_device(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 2 — pick the model from the chosen manufacturer."""
        assert self._manufacturer is not None
        assert self._emitter_entity_id is not None

        devices = self._groups.get(self._manufacturer, [])
        if not devices:
            return self.async_abort(reason="no_devices_for_manufacturer")

        if user_input is not None:
            device_key = user_input[CONF_DEVICE_KEY]
            if device_key not in self._catalog:
                return self.async_abort(reason="unknown_device")

            await self.async_set_unique_id(
                f"{device_key}_{self._emitter_entity_id}"
            )
            self._abort_if_unique_id_configured()

            ent_reg = er.async_get(self.hass)
            entry = ent_reg.async_get(self._emitter_entity_id)
            emitter_label = (
                entry.name
                or entry.original_name
                or self._emitter_entity_id
                if entry
                else self._emitter_entity_id
            )
            title = f"{self._catalog[device_key].name} via {emitter_label}"

            return self.async_create_entry(
                title=title,
                data={
                    CONF_DEVICE_KEY: device_key,
                    CONF_INFRARED_ENTITY_ID: self._emitter_entity_id,
                },
            )

        device_options = [
            SelectOptionDict(
                value=device.key,
                label=f"{device.model or device.key}"
                f"  ({len(device.commands)} cmds)",
            )
            for device in devices
        ]

        return self.async_show_form(
            step_id="device",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DEVICE_KEY): SelectSelector(
                        SelectSelectorConfig(
                            options=device_options,
                            mode=SelectSelectorMode.DROPDOWN,
                            sort=False,
                            custom_value=False,
                        )
                    ),
                }
            ),
            description_placeholders={
                "manufacturer": _manufacturer_label(
                    None if self._manufacturer == MANUFACTURER_OTHER else self._manufacturer
                ),
                "device_count": str(len(devices)),
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> OptionsFlow:
        """Return the options flow."""
        return HassCustomIrOptionsFlow()


class HassCustomIrOptionsFlow(OptionsFlow):
    """Options flow — exposes the legacy-Timing compatibility toggle."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self.config_entry.options.get(
            CONF_LEGACY_TIMINGS, DEFAULT_LEGACY_TIMINGS
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_LEGACY_TIMINGS, default=current
                    ): BooleanSelector(),
                }
            ),
        )
