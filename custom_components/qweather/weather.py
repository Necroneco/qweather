import logging
from typing import Any

from homeassistant.components.weather import (
    ATTR_CONDITION_CLEAR_NIGHT,
    ATTR_CONDITION_CLOUDY,
    ATTR_CONDITION_EXCEPTIONAL,
    ATTR_CONDITION_FOG,
    ATTR_CONDITION_HAIL,
    ATTR_CONDITION_LIGHTNING_RAINY,
    ATTR_CONDITION_PARTLYCLOUDY,
    ATTR_CONDITION_POURING,
    ATTR_CONDITION_RAINY,
    ATTR_CONDITION_SNOWY,
    ATTR_CONDITION_SNOWY_RAINY,
    ATTR_CONDITION_SUNNY,
    CoordinatorWeatherEntity,
    Forecast,
    WeatherEntityFeature,
)
from homeassistant.const import (
    CONF_NAME,
    UnitOfLength,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
import homeassistant.util.dt as dt_util

from . import Coordinators, QWeatherConfigEntry
from .const import (
    ATTRIBUTION,
    DOMAIN,
    MANUFACTURER,
    AirNow,
    DailyForecast,
    HourlyForecast,
    RealtimeWeather,
)

_LOGGER = logging.getLogger(__name__)

DEFAULT_TIME = dt_util.now()


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: QWeatherConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities(
        [
            QWeatherEntity(
                config_entry.runtime_data,
                config_entry.data[CONF_NAME],
                config_entry.unique_id,
            )
        ]
    )


class QWeatherEntity(CoordinatorWeatherEntity):
    """Representation of a weather condition."""

    _attr_attribution: str | None = ATTRIBUTION
    _attr_has_entity_name: bool = True
    _attr_name: str | None = None
    _attr_supported_features: int | None = (
        WeatherEntityFeature.FORECAST_DAILY | WeatherEntityFeature.FORECAST_HOURLY
    )

    _attr_precision: float = 1
    _attr_native_pressure_unit: str | None = UnitOfPressure.HPA
    _attr_native_temperature_unit: str | None = UnitOfTemperature.CELSIUS
    _attr_native_visibility_unit: str | None = UnitOfLength.KILOMETERS
    _attr_native_precipitation_unit: str | None = UnitOfLength.MILLIMETERS
    _attr_native_wind_speed_unit: str | None = UnitOfSpeed.KILOMETERS_PER_HOUR

    def __init__(self, coordinators: Coordinators, name: str, unique_id: str):
        """Initialize the weather."""
        super().__init__(
            coordinators.observation,
            daily_coordinator=coordinators.daily_forecast,
            hourly_coordinator=coordinators.hourly_forecast,
        )
        self.coordinators = coordinators
        self._attr_unique_id = f"{unique_id}_weather"
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, unique_id)},
            manufacturer=MANUFACTURER,
            name=name,
        )

        self._forecast_daily: list[Forecast] | None = None
        self._forecast_hourly: list[Forecast] | None = None

        self._update_weather_now(coordinators.observation.data)
        self._update_weather_daily(coordinators.daily_forecast.data)
        self._update_weather_hourly(coordinators.hourly_forecast.data)

        self._update_air_now(coordinators.air_now.data)

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.coordinators.air_now.async_add_listener(
                self._handle_air_now_coordinator_update
            )
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        _LOGGER.debug("_handle_coordinator_update")
        self._update_weather_now(self.coordinators.observation.data)
        super()._handle_coordinator_update()

    def _update_weather_now(self, weather_now: RealtimeWeather | None):
        if not weather_now:
            return
        self._attr_condition = CONDITION_MAP.get(weather_now.get("icon"))
        self._attr_humidity = maybe_float(weather_now.get("humidity"))
        self._attr_cloud_coverage = maybe_int(weather_now.get("cloud"))
        self._attr_wind_bearing = maybe_float(weather_now.get("wind360"))
        self._attr_native_pressure = maybe_float(weather_now.get("pressure"))
        self._attr_native_apparent_temperature = maybe_float(
            weather_now.get("feelsLike")
        )
        self._attr_native_temperature = maybe_float(weather_now.get("temp"))
        self._attr_native_visibility = maybe_float(weather_now.get("vis"))
        # self._attr_native_wind_gust_speed
        self._attr_native_wind_speed = maybe_float(weather_now.get("windSpeed"))
        self._attr_native_dew_point = maybe_float(weather_now.get("dew"))

        self._update_extra_weather_now(weather_now)

    @callback
    def _handle_daily_forecast_coordinator_update(self) -> None:
        """Handle updated data from the daily forecast coordinator."""
        _LOGGER.debug("_handle_daily_forecast_coordinator_update")
        self._update_weather_daily(self.coordinators.daily_forecast.data)
        self.async_write_ha_state()

    def _update_weather_daily(self, weather_daily: list[DailyForecast]) -> None:
        self._forecast_daily = [
            Forecast(
                condition=CONDITION_MAP.get(daily.get("iconDay")),
                datetime=daily.get("fxDate"),
                humidity=maybe_float(daily.get("humidity")),
                # precipitation_probability=,
                cloud_coverage=maybe_float(daily.get("cloud")),
                native_precipitation=maybe_float(daily.get("precip")),
                native_pressure=maybe_float(daily.get("pressure")),
                native_temperature=maybe_float(daily.get("tempMax")),
                native_templow=maybe_float(daily.get("tempMin")),
                # native_apparent_temperature=,
                wind_bearing=maybe_float(daily.get("wind360Day")),
                # native_wind_gust_speed=,
                native_wind_speed=maybe_float(daily.get("windSpeedDay")),
                # native_dew_point=,
                uv_index=maybe_float(daily.get("uvIndex")),
                # is_daytime=,
            )
            for daily in weather_daily
        ]

        if weather_daily:
            self._attr_uv_index = maybe_float(weather_daily[0].get("uvIndex"))

    @callback
    def _handle_hourly_forecast_coordinator_update(self) -> None:
        """Handle updated data from the hourly forecast coordinator."""
        _LOGGER.debug("_handle_hourly_forecast_coordinator_update")
        self._update_weather_hourly(self.coordinators.hourly_forecast.data)
        self.async_write_ha_state()

    def _update_weather_hourly(self, weather_hourly: list[HourlyForecast]):
        self._forecast_hourly = [
            Forecast(
                condition=CONDITION_MAP.get(hourly.get("icon")),
                datetime=hourly.get("fxTime"),
                humidity=maybe_float(hourly.get("humidity")),
                precipitation_probability=maybe_int(hourly.get("pop")),
                cloud_coverage=maybe_float(hourly.get("cloud")),
                native_precipitation=maybe_float(hourly.get("precip")),
                native_pressure=maybe_float(hourly.get("pressure")),
                native_temperature=maybe_float(hourly.get("temp")),
                # native_templow=,
                # native_apparent_temperature=,
                wind_bearing=maybe_float(hourly.get("wind360")),
                # native_wind_gust_speed=,
                native_wind_speed=maybe_float(hourly.get("windSpeed")),
                native_dew_point=maybe_float(hourly.get("dew")),
                # uv_index=,
                # is_daytime=,
            )
            for hourly in weather_hourly
        ]

    @callback
    def _async_forecast_daily(self) -> list[Forecast] | None:
        """Return the daily forecast in native units."""
        return self._forecast_daily

    @callback
    def _async_forecast_hourly(self) -> list[Forecast] | None:
        """Return the hourly forecast in native units."""
        return self._forecast_hourly

    @callback
    def _handle_air_now_coordinator_update(self) -> None:
        """Handle updated data from the air now coordinator."""
        _LOGGER.debug("_handle_air_now_coordinator_update")
        self._update_air_now(self.coordinators.air_now.data)
        self.async_write_ha_state()

    @callback
    def _update_air_now(self, air_now: AirNow | None):
        self._attr_ozone = maybe_float(air_now.get("o3")) if air_now else None

    @callback
    def _update_extra_weather_now(self, weather_now: RealtimeWeather | None):
        if not weather_now:
            return
        self._attr_extra_state_attributes = {
            # "obs_time": weather_now.get("obsTime"),
            "winddir": weather_now.get("windDir"),
        }


# https://www.home-assistant.io/integrations/weather/
# https://dev.qweather.com/docs/resource/icons/
CONDITION_MAP = {
    "100": ATTR_CONDITION_SUNNY,  # 晴(白天)
    "101": ATTR_CONDITION_CLOUDY,  # 多云(白天)
    "102": ATTR_CONDITION_PARTLYCLOUDY,  # 少云(白天)
    "103": ATTR_CONDITION_PARTLYCLOUDY,  # 晴间多云(白天)
    "104": ATTR_CONDITION_CLOUDY,  # 阴(白天)
    "150": ATTR_CONDITION_CLEAR_NIGHT,  # 晴(夜间)
    "151": ATTR_CONDITION_CLOUDY,  # 多云(夜间)
    "152": ATTR_CONDITION_PARTLYCLOUDY,  # 少云(夜间)
    "153": ATTR_CONDITION_PARTLYCLOUDY,  # 夜间多云(夜间)
    "300": ATTR_CONDITION_RAINY,  # 阵雨(白天)
    "301": ATTR_CONDITION_POURING,  # 强阵雨(白天)
    "302": ATTR_CONDITION_LIGHTNING_RAINY,  # 雷阵雨
    "303": ATTR_CONDITION_LIGHTNING_RAINY,  # 强雷阵雨
    "304": ATTR_CONDITION_HAIL,  # 雷阵雨伴有冰雹
    "305": ATTR_CONDITION_RAINY,  # 小雨
    "306": ATTR_CONDITION_RAINY,  # 中雨
    "307": ATTR_CONDITION_POURING,  # 大雨
    "308": ATTR_CONDITION_POURING,  # 极端降雨
    "309": ATTR_CONDITION_RAINY,  # 毛毛雨/细雨
    "310": ATTR_CONDITION_POURING,  # 暴雨
    "311": ATTR_CONDITION_POURING,  # 大暴雨
    "312": ATTR_CONDITION_POURING,  # 特大暴雨
    "313": ATTR_CONDITION_RAINY,  # 冻雨
    "314": ATTR_CONDITION_RAINY,  # 小到中雨
    "315": ATTR_CONDITION_RAINY,  # 中到大雨
    "316": ATTR_CONDITION_POURING,  # 大到暴雨
    "317": ATTR_CONDITION_POURING,  # 暴雨到大暴雨
    "318": ATTR_CONDITION_POURING,  # 大暴雨到特大暴雨
    "350": ATTR_CONDITION_RAINY,  # 阵雨(夜间)
    "351": ATTR_CONDITION_POURING,  # 强阵雨(夜间)
    "399": ATTR_CONDITION_RAINY,  # 雨
    "400": ATTR_CONDITION_SNOWY,  # 小雪
    "401": ATTR_CONDITION_SNOWY,  # 中雪
    "402": ATTR_CONDITION_SNOWY,  # 大雪
    "403": ATTR_CONDITION_SNOWY,  # 暴雪
    "404": ATTR_CONDITION_SNOWY_RAINY,  # 雨夹雪
    "405": ATTR_CONDITION_SNOWY_RAINY,  # 雨雪天气
    "406": ATTR_CONDITION_SNOWY_RAINY,  # 阵雨夹雪(白天)
    "407": ATTR_CONDITION_SNOWY,  # 阵雪(白天)
    "408": ATTR_CONDITION_SNOWY,  # 小到中雪
    "409": ATTR_CONDITION_SNOWY,  # 中到大雪
    "410": ATTR_CONDITION_SNOWY,  # 大到暴雪
    "456": ATTR_CONDITION_SNOWY_RAINY,  # 阵雨夹雪(夜间)
    "457": ATTR_CONDITION_SNOWY,  # 阵雪(夜间)
    "499": ATTR_CONDITION_SNOWY,  # 雪
    "500": ATTR_CONDITION_FOG,  # 薄雾
    "501": ATTR_CONDITION_FOG,  # 雾
    "502": ATTR_CONDITION_FOG,  # 霾
    "503": ATTR_CONDITION_EXCEPTIONAL,  # 扬沙
    "504": ATTR_CONDITION_EXCEPTIONAL,  # 浮尘
    "507": ATTR_CONDITION_EXCEPTIONAL,  # 沙尘暴
    "508": ATTR_CONDITION_EXCEPTIONAL,  # 强沙尘暴
    "509": ATTR_CONDITION_FOG,  # 浓雾
    "510": ATTR_CONDITION_FOG,  # 强浓雾
    "511": ATTR_CONDITION_FOG,  # 中度霾
    "512": ATTR_CONDITION_FOG,  # 重度霾
    "513": ATTR_CONDITION_FOG,  # 严重霾
    "514": ATTR_CONDITION_FOG,  # 大雾
    "515": ATTR_CONDITION_FOG,  # 特强浓雾
    "900": ATTR_CONDITION_EXCEPTIONAL,  # 热
    "901": ATTR_CONDITION_EXCEPTIONAL,  # 冷
    "999": ATTR_CONDITION_EXCEPTIONAL,  # 未知
}


# region Utils


def maybe_int(s: int | None) -> int | None:
    return None if s is None else int(s)


def maybe_float(s: str | None) -> float | None:
    return None if s is None else float(s)


# endregion
