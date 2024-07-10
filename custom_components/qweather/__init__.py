from dataclasses import dataclass
from datetime import timedelta
import logging

from aiohttp import ClientTimeout

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_LATITUDE, CONF_LONGITUDE, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    TimestampDataUpdateCoordinator,
)

from .api import QWeatherClient
from .const import CONF_GIRD

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.WEATHER,
]

type QWeatherConfigEntry = ConfigEntry[Coordinators]


async def async_setup_entry(hass: HomeAssistant, entry: QWeatherConfigEntry) -> bool:
    entry.async_on_unload(entry.add_update_listener(entry_update_listener))

    api_key: str = entry.data[CONF_API_KEY]
    longitude: float = round(entry.data[CONF_LONGITUDE], 2)
    latitude: float = round(entry.data[CONF_LATITUDE], 2)
    gird_weather: bool = entry.options.get(CONF_GIRD, True)

    session = async_create_clientsession(hass, timeout=ClientTimeout(total=20))
    client = QWeatherClient(session, api_key, f"{longitude},{latitude}", gird_weather)
    entry.runtime_data = coordinators = Coordinators(hass, client)

    for coordinator in coordinators.__dict__.values():
        await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: QWeatherConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def entry_update_listener(
    hass: HomeAssistant, entry: QWeatherConfigEntry
) -> None:
    # https://developers.home-assistant.io/docs/config_entries_options_flow_handler/#signal-updates
    _LOGGER.debug("[%s] Options updated: %s", entry.unique_id, entry.options)
    await hass.config_entries.async_reload(entry.entry_id)


@dataclass
class Coordinators:
    observation: TimestampDataUpdateCoordinator
    daily_forecast: TimestampDataUpdateCoordinator
    hourly_forecast: TimestampDataUpdateCoordinator
    air_now: DataUpdateCoordinator
    minutely_precipitation: DataUpdateCoordinator
    warning_now: DataUpdateCoordinator
    # indices_1d: DataUpdateCoordinator

    def __init__(self, hass: HomeAssistant, client: QWeatherClient):
        self.observation = TimestampDataUpdateCoordinator(
            hass,
            _LOGGER,
            name="实时天气",
            update_method=client.update_observation,
            update_interval=timedelta(minutes=10),
        )
        self.daily_forecast = TimestampDataUpdateCoordinator(
            hass,
            _LOGGER,
            name="每日天气预报",
            update_method=client.update_daily_forecast,
            update_interval=timedelta(hours=1),
        )
        self.hourly_forecast = TimestampDataUpdateCoordinator(
            hass,
            _LOGGER,
            name="逐小时天气预报",
            update_method=client.update_hourly_forecast,
            update_interval=timedelta(minutes=30),
        )
        self.air_now = DataUpdateCoordinator(
            hass,
            _LOGGER,
            name="实时空气质量",
            update_method=client.update_air_now,
            update_interval=timedelta(minutes=30),
        )
        self.minutely_precipitation = DataUpdateCoordinator(
            hass,
            _LOGGER,
            name="分钟级降水",
            update_method=client.update_minutely_precipitation,
            update_interval=timedelta(minutes=10),
        )
        self.warning_now = DataUpdateCoordinator(
            hass,
            _LOGGER,
            name="天气灾害预警",
            update_method=client.update_warning_now,
            update_interval=timedelta(minutes=20),
        )
        # indices_1d=DataUpdateCoordinator(
        #     hass,
        #     _LOGGER,
        #     name="天气指数预报",
        #     update_method=client.update_indices_1d,
        #     update_interval=timedelta(hours=12),
        # )
