"""Config flow for Custom IR."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components.infrared import (
    DOMAIN as INFRARED_DOMAIN,
    async_get_emitters,
)
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .catalog import async_load_catalog
from .const import CONF_DEVICE_KEY, CONF_INFRARED_ENTITY_ID, DOMAIN


class HassCustomIrConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow for Custom IR."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        emitter_ids = async_get_emitters(self.hass)
        if not emitter_ids:
            return self.async_abort(reason="no_emitters")

        catalog = await async_load_catalog(self.hass)
        if not catalog:
            return self.async_abort(reason="no_devices")

        if user_input is not None:
            device_key = user_input[CONF_DEVICE_KEY]
            entity_id = user_input[CONF_INFRARED_ENTITY_ID]

            if device_key not in catalog:
                return self.async_abort(reason="unknown_device")

            await self.async_set_unique_id(f"{device_key}_{entity_id}")
            self._abort_if_unique_id_configured()

            ent_reg = er.async_get(self.hass)
            entry = ent_reg.async_get(entity_id)
            emitter_label = (
                entry.name or entry.original_name or entity_id if entry else entity_id
            )
            title = f"{catalog[device_key].name} via {emitter_label}"

            return self.async_create_entry(title=title, data=user_input)

        device_options = [
            SelectOptionDict(value=key, label=device.name)
            for key, device in sorted(catalog.items(), key=lambda kv: kv[1].name.lower())
        ]

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DEVICE_KEY): SelectSelector(
                        SelectSelectorConfig(
                            options=device_options,
                            mode=SelectSelectorMode.DROPDOWN,
                            sort=False,
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
        )
