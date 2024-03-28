import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_API_KEY,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    Platform,
)
from homeassistant.core import HomeAssistant

from .const import (
    CONF_GIRD,
    DOMAIN,
    ROOT_PATH,
    VERSION,
)
from .core.q_client import QWeatherClient

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.WEATHER,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})

    entry.async_on_unload(entry.add_update_listener(entry_update_listener))

    # name = entry.data.get(CONF_NAME)
    api_key = entry.data[CONF_API_KEY]
    longitude = round(entry.data[CONF_LONGITUDE], 2)
    latitude = round(entry.data[CONF_LATITUDE], 2)
    gird_weather = entry.options.get(CONF_GIRD, False)

    client = QWeatherClient(
        hass,
        api_key,
        longitude,
        latitude,
        gird_weather,
    )
    hass.data[DOMAIN][entry.entry_id] = client
    # entry.async_on_unload(hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, client.unload))
    await client.load_init_data()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # api: QWeatherClient = hass.data[DOMAIN][entry.entry_id]
    # if api is not None:
    #     await api.unload()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def entry_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    # https://developers.home-assistant.io/docs/config_entries_options_flow_handler/#signal-updates
    _LOGGER.debug("[%s] Options updated: %s", entry.unique_id, entry.options)
    await hass.config_entries.async_reload(entry.entry_id)
