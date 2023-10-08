"""Adds config flow for Qweather."""
import json
import logging
from typing import Any

import homeassistant.helpers.config_validation as cv
import requests
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY, CONF_LATITUDE, CONF_LONGITUDE, CONF_NAME
from homeassistant.core import callback

from .const import CONF_GIRD, DOMAIN

_LOGGER = logging.getLogger(__name__)


@config_entries.HANDLERS.register(DOMAIN)
class QWeatherFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    def get_data(self, url):
        json_text = requests.get(url).content
        return json.loads(json_text)

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors = {}
        if user_input is not None:
            # Check if entered host is already in HomeAssistant
            existing = await self._check_existing(user_input[CONF_NAME])
            if existing:
                return self.async_abort(reason="already_configured")

            # If it is not, continue with communication test
            longitude = round(user_input["longitude"], 2)
            latitude = round(user_input["latitude"], 2)
            url = f'https://devapi.qweather.com/v7/weather/now?location={longitude},{latitude}&key={user_input["api_key"]}'
            ret_data = await self.hass.async_add_executor_job(self.get_data, url)
            _LOGGER.debug(ret_data)
            if ret_data["code"] == "200":
                await self.async_set_unique_id(f"{longitude}-{latitude}".replace(".", "_"))
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)
            else:
                errors["base"] = "communication"

        data_schema = {
            vol.Required(CONF_API_KEY): str,
            vol.Required(CONF_LONGITUDE, default=self.hass.config.longitude): cv.longitude,
            vol.Required(CONF_LATITUDE, default=self.hass.config.latitude): cv.latitude,
            vol.Optional(CONF_NAME, default=self.hass.config.location_name): str,
        }
        return self.async_show_form(step_id="user", data_schema=vol.Schema(data_schema), errors=errors)

    async def _check_existing(self, host):
        for entry in self._async_current_entries():
            if host == entry.data.get(CONF_NAME):
                return True

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return QWeatherOptionsFlow(config_entry)


class QWeatherOptionsFlow(config_entries.OptionsFlow):
    """Config flow options for Qweather."""

    def __init__(self, config_entry: config_entries.ConfigEntry):
        """Initialize Qweather options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Handle a flow initialized by the user."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_GIRD,
                        default=self.config_entry.options.get(CONF_GIRD, False),
                    ): bool,
                }
            ),
        )
