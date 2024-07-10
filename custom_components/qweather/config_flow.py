from http import HTTPStatus
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_API_KEY, CONF_LATITUDE, CONF_LONGITUDE, CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv

from .const import CONF_GIRD, DOMAIN

_LOGGER = logging.getLogger(__name__)


class QWeatherFlowHandler(ConfigFlow, domain=DOMAIN):
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors = {}
        if user_input is not None:
            longitude = round(user_input[CONF_LONGITUDE], 2)
            latitude = round(user_input[CONF_LATITUDE], 2)
            use_grid = user_input.get(CONF_GIRD, True)

            await self.async_set_unique_id(f"{longitude}_{latitude}".replace(".", "_"))
            self._abort_if_unique_id_configured()

            grid_weather = "grid-weather" if use_grid else "weather"
            url = f"https://devapi.qweather.com/v7/{grid_weather}/now"
            params = {
                "location": f"{longitude},{latitude}",
                "key": user_input[CONF_API_KEY],
            }
            session = async_get_clientsession(self.hass)
            resp = await session.get(url, params=params)
            if resp.status == HTTPStatus.OK:
                data = await resp.json()
                _LOGGER.debug(data)
                if data["code"] == "200":
                    return self.async_create_entry(
                        title=user_input[CONF_NAME],
                        data={
                            CONF_NAME: user_input[CONF_NAME],
                            CONF_API_KEY: user_input[CONF_API_KEY],
                            CONF_LONGITUDE: user_input[CONF_LONGITUDE],
                            CONF_LATITUDE: user_input[CONF_LATITUDE],
                        },
                        options={
                            CONF_GIRD: use_grid,
                        },
                    )

            _LOGGER.warning("Failed to communicate with QWeather: %s", resp.status)
            errors["base"] = "communication"

        my = self.hass.config
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_KEY): str,
                    vol.Required(CONF_LONGITUDE, default=my.longitude): cv.longitude,
                    vol.Required(CONF_LATITUDE, default=my.latitude): cv.latitude,
                    vol.Required(CONF_NAME, default=my.location_name): str,
                    vol.Optional(CONF_GIRD, default=True): bool,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow for this handler."""
        return QWeatherOptionsFlow(config_entry)


class QWeatherOptionsFlow(OptionsFlow):
    """Config options flow for Qweather."""

    def __init__(self, config_entry: ConfigEntry):
        """Initialize Qweather options flow."""
        self.use_grid = config_entry.options.get(CONF_GIRD, False)

    async def async_step_init(self, user_input=None) -> ConfigFlowResult:
        """Handle a flow initialized by the user."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_GIRD, default=self.use_grid): bool,
                }
            ),
        )
