import logging
from datetime import datetime

import homeassistant.util.dt as dt_util
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
    ATTR_FORECAST_CONDITION,
    ATTR_FORECAST_NATIVE_PRECIPITATION,
    ATTR_FORECAST_NATIVE_PRESSURE,
    ATTR_FORECAST_NATIVE_TEMP,
    ATTR_FORECAST_NATIVE_TEMP_LOW,
    ATTR_FORECAST_NATIVE_WIND_SPEED,
    ATTR_FORECAST_PRECIPITATION,
    ATTR_FORECAST_PRESSURE,
    ATTR_FORECAST_TEMP,
    ATTR_FORECAST_TIME,
    ATTR_FORECAST_WIND_BEARING,
    ATTR_FORECAST_WIND_SPEED,
    ATTR_WEATHER_HUMIDITY,
)
from homeassistant.components.weather import (
    CoordinatorWeatherEntity,
    Forecast,
    WeatherEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
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

from .const import (
    ATTRIBUTION,
    ATTR_AQI,
    ATTR_CONDITION_CN,
    ATTR_DAILY_FORECAST,
    ATTR_FORECAST_PROBABLE_PRECIPITATION,
    ATTR_HOURLY_FORECAST,
    ATTR_MINUTELY_FORECAST,
    ATTR_SUGGESTION,
    ATTR_UPDATE_TIME,
    AirNow,
    DOMAIN,
    DailyForecast,
    HourlyForecast,
    IndicesDailyItem,
    MANUFACTURER,
    MinutelyPrecipitation,
    RealtimeWeather,
    SUGGESTIONTPYE2NAME,
    WeatherWarning,
)
from .q_client import QWeatherClient
from .utils import float_or_none, int_or_none

_LOGGER = logging.getLogger(__name__)

DEFAULT_TIME = dt_util.now()


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    name = config_entry.data.get(CONF_NAME)
    unique_id = config_entry.unique_id
    client = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([QWeatherEntity(client, name, unique_id)])


class QWeatherEntity(CoordinatorWeatherEntity):
    """Representation of a weather condition."""

    _attr_attribution: str | None = ATTRIBUTION
    _attr_has_entity_name: bool = True
    _attr_name: str | None = None

    _attr_supported_features: int | None = WeatherEntityFeature.FORECAST_DAILY | WeatherEntityFeature.FORECAST_HOURLY

    _attr_precision: float = 1
    _attr_native_pressure_unit: str | None = UnitOfPressure.HPA
    _attr_native_temperature_unit: str | None = UnitOfTemperature.CELSIUS
    _attr_native_visibility_unit: str | None = UnitOfLength.KILOMETERS
    _attr_native_precipitation_unit: str | None = UnitOfLength.MILLIMETERS
    _attr_native_wind_speed_unit: str | None = UnitOfSpeed.KILOMETERS_PER_HOUR

    def __init__(self, client: QWeatherClient, name: str, unique_id: str):
        """Initialize the weather."""
        super().__init__(
            client.observation_coordinator,
            daily_coordinator=client.daily_forecast_coordinator,
            hourly_coordinator=client.hourly_forecast_coordinator,
        )
        self.client = client
        self._attr_unique_id = f"{unique_id}_weather"
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, unique_id)},
            manufacturer=MANUFACTURER,
            name=name,
        )

        self._forecast_daily: list[Forecast] | None = None
        self._forecast_hourly: list[Forecast] | None = None
        self._attr_extra_state_attributes = {
            "city": self.client.city,
        }

        self._update_weather_now(self.client.observation_coordinator.data)
        self._update_weather_daily(self.client.daily_forecast_coordinator.data)
        self._update_weather_hourly(self.client.hourly_forecast_coordinator.data)

        self._update_air_now(self.client.air_now_coordinator.data)
        self._update_extra_minutely_precipitation(self.client.minutely_precipitation_coordinator.data)
        self._update_extra_warning_now(self.client.warning_now_coordinator.data)
        self._update_extra_indices_1d(self.client.indices_1d_coordinator.data)

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.client.air_now_coordinator.async_add_listener(self._handle_air_now_coordinator_update)
        )
        self.async_on_remove(
            self.client.minutely_precipitation_coordinator.async_add_listener(
                self._handle_minutely_precipitation_coordinator_update
            )
        )
        self.async_on_remove(
            self.client.warning_now_coordinator.async_add_listener(self._handle_warning_now_coordinator_update)
        )
        self.async_on_remove(
            self.client.indices_1d_coordinator.async_add_listener(self._handle_indices_1d_coordinator_update)
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        _LOGGER.debug("_handle_coordinator_update")
        self._update_weather_now(self.client.observation_coordinator.data)
        super()._handle_coordinator_update()

    def _update_weather_now(self, weather_now: RealtimeWeather | None):
        if not weather_now:
            return
        self._attr_condition = CONDITION_MAP.get(weather_now.get("icon"))
        self._attr_humidity = float_or_none(weather_now.get("humidity"))
        self._attr_cloud_coverage = int_or_none(weather_now.get("cloud"))
        self._attr_wind_bearing = float_or_none(weather_now.get("wind360"))
        self._attr_native_pressure = float_or_none(weather_now.get("pressure"))
        self._attr_native_apparent_temperature = float_or_none(weather_now.get("feelsLike"))
        self._attr_native_temperature = float_or_none(weather_now.get("temp"))
        self._attr_native_visibility = float_or_none(weather_now.get("vis"))
        # self._attr_native_wind_gust_speed
        self._attr_native_wind_speed = float_or_none(weather_now.get("windSpeed"))
        self._attr_native_dew_point = float_or_none(weather_now.get("dew"))

        self._update_extra_weather_now(weather_now)

    @callback
    def _handle_daily_forecast_coordinator_update(self) -> None:
        """Handle updated data from the daily forecast coordinator."""
        _LOGGER.debug("_handle_daily_forecast_coordinator_update")
        self._update_weather_daily(self.client.daily_forecast_coordinator.data)
        self.async_write_ha_state()

    def _update_weather_daily(self, weather_daily: list[DailyForecast]) -> None:
        self._forecast_daily = [
            Forecast(
                condition=CONDITION_MAP.get(daily.get("iconDay")),
                datetime=daily.get("fxDate"),
                humidity=float_or_none(daily.get("humidity")),
                # precipitation_probability=,
                cloud_coverage=float_or_none(daily.get("cloud")),
                native_precipitation=float_or_none(daily.get("precip")),
                native_pressure=float_or_none(daily.get("pressure")),
                native_temperature=float_or_none(daily.get("tempMax")),
                native_templow=float_or_none(daily.get("tempMin")),
                # native_apparent_temperature=,
                wind_bearing=float_or_none(daily.get("wind360Day")),
                # native_wind_gust_speed=,
                native_wind_speed=float_or_none(daily.get("windSpeedDay")),
                # native_dew_point=,
                uv_index=float_or_none(daily.get("uvIndex")),
                # is_daytime=,
            )
            for daily in weather_daily
        ]

        if weather_daily:
            self._attr_uv_index = float_or_none(weather_daily[0].get("uvIndex"))

        self._update_extra_weather_daily(weather_daily)

    @callback
    def _handle_hourly_forecast_coordinator_update(self) -> None:
        """Handle updated data from the hourly forecast coordinator."""
        _LOGGER.debug("_handle_hourly_forecast_coordinator_update")
        self._update_weather_hourly(self.client.hourly_forecast_coordinator.data)
        self.async_write_ha_state()

    def _update_weather_hourly(self, weather_hourly: list[HourlyForecast]):
        self._forecast_hourly = [
            Forecast(
                condition=CONDITION_MAP.get(hourly.get("icon")),
                datetime=hourly.get("fxTime"),
                humidity=float_or_none(hourly.get("humidity")),
                precipitation_probability=int_or_none(hourly.get("pop")),
                cloud_coverage=float_or_none(hourly.get("cloud")),
                native_precipitation=float_or_none(hourly.get("precip")),
                native_pressure=float_or_none(hourly.get("pressure")),
                native_temperature=float_or_none(hourly.get("temp")),
                # native_templow=,
                # native_apparent_temperature=,
                wind_bearing=float_or_none(hourly.get("wind360")),
                # native_wind_gust_speed=,
                native_wind_speed=float_or_none(hourly.get("windSpeed")),
                native_dew_point=float_or_none(hourly.get("dew")),
                # uv_index=,
                # is_daytime=,
            )
            for hourly in weather_hourly
        ]

        self._update_extra_weather_hourly(weather_hourly)

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
        self._update_air_now(self.client.air_now_coordinator.data)
        self.async_write_ha_state()

    def _update_air_now(self, air_now: AirNow | None):
        self._attr_ozone = float_or_none(air_now.get("o3")) if air_now else None

        self._update_extra_air_now(air_now)

    @callback
    def _update_extra_weather_now(self, weather_now: RealtimeWeather | None):
        if not weather_now:
            return
        obs_time = dt_util.as_local(datetime.fromisoformat(weather_now.get("obsTime")))
        self._attr_extra_state_attributes.update(
            {
                "qweather_icon": weather_now.get("icon"),
                ATTR_UPDATE_TIME: obs_time.strftime("%Y-%m-%d %H:%M:%S"),
                ATTR_CONDITION_CN: weather_now.get("text"),
                "winddir": weather_now.get("windDir"),
                "windscale": weather_now.get("windScale"),
            }
        )
        self._update_extra_sun()

    @callback
    def _update_extra_weather_daily(self, weather_daily: list[DailyForecast]):
        self._attr_extra_state_attributes.update(
            {
                ATTR_DAILY_FORECAST: [
                    {
                        ATTR_FORECAST_TIME: daily["fxDate"],
                        ATTR_FORECAST_NATIVE_TEMP: float(daily["tempMax"]),
                        ATTR_FORECAST_NATIVE_TEMP_LOW: float(daily["tempMin"]),
                        ATTR_FORECAST_CONDITION: CONDITION_MAP.get(daily["iconDay"]),
                        "text": daily["textDay"],
                        "icon": daily["iconDay"],
                        "textnight": daily["textNight"],
                        "winddirday": daily["windDirDay"],
                        "winddirnight": daily["windDirNight"],
                        "windscaleday": daily["windScaleDay"],
                        "windscalenight": daily["windScaleNight"],
                        "iconnight": daily["iconNight"],
                        ATTR_FORECAST_WIND_BEARING: float(daily["wind360Day"]),
                        ATTR_FORECAST_NATIVE_WIND_SPEED: float(daily["windSpeedDay"]),
                        ATTR_FORECAST_NATIVE_PRECIPITATION: float(daily["precip"]),
                        "humidity": float(daily["humidity"]),
                        ATTR_FORECAST_NATIVE_PRESSURE: float(daily["pressure"]),
                    }
                    for daily in weather_daily
                ]
            }
        )
        self._update_extra_sun()

    @callback
    def _update_extra_weather_hourly(self, weather_hourly: list[HourlyForecast]):
        hourly_forecast = []
        summarystr = ""
        summarymaxprecipstr = ""
        summaryendstr = ""
        summarystart = 0
        summaryend = 0
        summaryprecip = 0
        for hourly in weather_hourly:
            date_obj = datetime.fromisoformat(hourly["fxTime"].replace("Z", "+00:00"))
            date_obj = dt_util.as_local(date_obj)
            formatted_date = datetime.strftime(date_obj, "%Y-%m-%d %H:%M")

            hourly_forecast.append(
                {
                    "datetime": formatted_date,
                    ATTR_CONDITION_CLOUDY: hourly["cloud"],
                    ATTR_FORECAST_TEMP: float(hourly["temp"]),
                    ATTR_FORECAST_CONDITION: CONDITION_MAP.get(hourly["icon"]),
                    "text": hourly["text"],
                    "icon": hourly["icon"],
                    ATTR_FORECAST_WIND_BEARING: float(hourly["wind360"]),
                    ATTR_FORECAST_WIND_SPEED: float(hourly["windSpeed"]),
                    ATTR_FORECAST_PRECIPITATION: float(hourly["precip"]),
                    ATTR_WEATHER_HUMIDITY: float(hourly["humidity"]),
                    ATTR_FORECAST_PROBABLE_PRECIPITATION: int(hourly["pop"])
                    if hourly.get("pop")
                    else 0,  # 降雨概率，城市天气才有，格点天气不存在。
                    ATTR_FORECAST_PRESSURE: float(hourly["pressure"]),
                }
            )

            if float(hourly["precip"]) > 0.1 and summarystart > 0:
                if summarystart < 4:
                    summarystr = str(summarystart) + "小时后转" + hourly["text"] + "。"
                else:
                    if int(datetime.strftime(date_obj, "%H")) > int(datetime.now().strftime("%H")):
                        summaryday = "今天"
                    else:
                        summaryday = "明天"
                    summarystr = f"{summaryday}{str(int(datetime.strftime(date_obj, '%H')))}点后转{hourly['text']}。"
                summarystart = -1000
                summaryprecip = float(hourly["precip"])
            if float(hourly["precip"]) > 0.1 and float(hourly["precip"]) > summaryprecip:
                if int(datetime.strftime(date_obj, "%H")) > int(datetime.now().strftime("%H")):
                    summaryday = "今天"
                else:
                    summaryday = "明天"
                summarymaxprecipstr = f"{summaryday}{str(int(datetime.strftime(date_obj, '%H')))}点为{hourly['text']}！"
                summaryprecip = float(hourly["precip"])
                summaryend = 0
                summaryendstr = ""
            if float(hourly["precip"]) == 0 and summaryprecip > 0 and summaryend == 0:
                summaryday = (
                    "今天" if int(datetime.strftime(date_obj, "%H")) > int(datetime.now().strftime("%H")) else "明天"
                )
                summaryendstr = f"{summaryday}{str(int(datetime.strftime(date_obj, '%H')))}点后转{hourly['text']}。"
                summaryend += 1
            summarystart += 1
        if summarystr:
            hourly_summary = summarystr + summarymaxprecipstr + summaryendstr
        else:
            hourly_summary = "未来24小时内无降水"

        self._attr_extra_state_attributes.update(
            {
                ATTR_HOURLY_FORECAST: hourly_forecast,
                "forecast_hourly": hourly_summary,
            }
        )
        self._update_extra_sun()

    @callback
    def _update_extra_air_now(self, air_now: AirNow | None):
        if not air_now:
            return
        self._attr_extra_state_attributes.update(
            {
                ATTR_AQI: air_now,
            }
        )
        self._update_extra_sun()

    @callback
    def _handle_minutely_precipitation_coordinator_update(self) -> None:
        """Handle updated data from the minutely precipitation coordinator."""
        _LOGGER.debug("_handle_minutely_precipitation_coordinator_update")
        self._update_extra_minutely_precipitation(self.client.minutely_precipitation_coordinator.data)
        self.async_write_ha_state()

    @callback
    def _update_extra_minutely_precipitation(self, minutely_precipitation: MinutelyPrecipitation | None):
        minutely_data = minutely_precipitation.get("minutely", []) if minutely_precipitation else []
        minutely_forecast = [
            {
                "time": item["fxTime"][11:16],
                "type": item["type"],
                ATTR_FORECAST_PRECIPITATION: float(item["precip"]),
            }
            for item in minutely_data
        ]
        minutely_summary = minutely_precipitation.get("summary") if minutely_precipitation else None
        self._attr_extra_state_attributes.update(
            {
                ATTR_MINUTELY_FORECAST: minutely_forecast,
                "forecast_minutely": minutely_summary,
            }
        )
        self._update_extra_sun()

    @callback
    def _handle_warning_now_coordinator_update(self) -> None:
        """Handle updated data from the warning now coordinator."""
        _LOGGER.debug("_handle_warning_now_coordinator_update")
        self._update_extra_warning_now(self.client.warning_now_coordinator.data)
        self.async_write_ha_state()

    @callback
    def _update_extra_warning_now(self, warning_now: list[WeatherWarning]):
        self._attr_extra_state_attributes.update(
            {
                "warning": warning_now,
            }
        )
        self._update_extra_sun()

    @callback
    def _handle_indices_1d_coordinator_update(self) -> None:
        """Handle updated data from the indices 1d coordinator."""
        _LOGGER.debug("_handle_indices_1d_coordinator_update")
        self._update_extra_indices_1d(self.client.indices_1d_coordinator.data)
        self.async_write_ha_state()

    @callback
    def _update_extra_indices_1d(self, indices_1d: list[IndicesDailyItem]):
        self._attr_extra_state_attributes.update(
            {
                ATTR_SUGGESTION: [
                    {
                        "title": SUGGESTIONTPYE2NAME[v.get("type")],
                        "title_cn": v.get("name"),
                        "brf": v.get("category"),
                        # "txt": v.get("text"),
                    }
                    for v in indices_1d
                ]
            }
        )
        self._update_extra_sun()

    @callback
    def _update_extra_sun(self):
        sun_next_rising = self.hass.states.get("sensor.sun_next_rising") if self.hass else None
        sun_next_setting = self.hass.states.get("sensor.sun_next_setting") if self.hass else None
        self._attr_extra_state_attributes.update(
            {
                "sunrise": sun_next_rising.state if sun_next_rising else None,
                "sunset": sun_next_setting.state if sun_next_setting else None,
            }
        )


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
