import logging
import math
from collections.abc import Mapping
from datetime import datetime, timedelta

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, TimestampDataUpdateCoordinator

from ..const import (
    AirNow,
    DailyForecast,
    HourlyForecast,
    IndicesDailyItem,
    MinutelyPrecipitation,
    RealtimeWeather,
    WeatherWarning,
)

_LOGGER = logging.getLogger(__name__)


class QWeatherClient:
    dev_api_v7 = "https://devapi.qweather.com/v7"

    _wait_until: float = 0

    def __init__(
        self,
        hass: HomeAssistant,
        api_key: str,
        longitude: int,
        latitude: int,
        gird_weather: bool,
    ):
        super().__init__()
        # self.api_key = api_key
        # self.location = f"{longitude},{latitude}"
        self.params = {"location": f"{longitude},{latitude}", "key": api_key}
        self.weather_type = "grid-weather" if gird_weather else "weather"

        self.http = async_create_clientsession(hass, timeout=aiohttp.ClientTimeout(total=20))

        self.observation_coordinator = TimestampDataUpdateCoordinator(
            hass,
            _LOGGER,
            name="实时天气",
            update_method=self.update_observation,
            update_interval=timedelta(minutes=10),
        )
        self.daily_forecast_coordinator = TimestampDataUpdateCoordinator(
            hass,
            _LOGGER,
            name="每日天气预报",
            update_method=self.update_daily_forecast,
            update_interval=timedelta(hours=1),
        )
        self.hourly_forecast_coordinator = TimestampDataUpdateCoordinator(
            hass,
            _LOGGER,
            name="逐小时天气预报",
            update_method=self.update_hourly_forecast,
            update_interval=timedelta(minutes=30),
        )
        self.air_now_coordinator = DataUpdateCoordinator(
            hass,
            _LOGGER,
            name="实时空气质量",
            update_method=self.update_air_now,
            update_interval=timedelta(minutes=30),
        )
        self.minutely_precipitation_coordinator = DataUpdateCoordinator(
            hass,
            _LOGGER,
            name="分钟级降水",
            update_method=self.update_minutely_precipitation,
            update_interval=timedelta(minutes=10),
        )
        self.warning_now_coordinator = DataUpdateCoordinator(
            hass,
            _LOGGER,
            name="天气灾害预警",
            update_method=self.update_warning_now,
            update_interval=timedelta(minutes=20),
        )
        self.indices_1d_coordinator = DataUpdateCoordinator(
            hass,
            _LOGGER,
            name="天气指数预报",
            update_method=self.update_indices_1d,
            update_interval=timedelta(hours=12),
        )

        self.city = "未知"

    async def load_init_data(self):
        await self.observation_coordinator.async_config_entry_first_refresh()
        await self.daily_forecast_coordinator.async_config_entry_first_refresh()
        await self.hourly_forecast_coordinator.async_config_entry_first_refresh()
        await self.air_now_coordinator.async_config_entry_first_refresh()
        await self.minutely_precipitation_coordinator.async_config_entry_first_refresh()
        await self.warning_now_coordinator.async_config_entry_first_refresh()
        await self.indices_1d_coordinator.async_config_entry_first_refresh()

        geo_url = f"https://geoapi.qweather.com/v2/city/lookup"
        if json_data := await self.url_get(geo_url, self.params):
            if locations := json_data.get("location"):
                self.city = locations[0].get("name", "未知")

    async def update_observation(self) -> RealtimeWeather | None:
        """城市天气/格点天气 - 实时天气"""
        json_data = await self.api_get(f"{self.weather_type}/now")
        return json_data.get("now") if json_data else None

    async def update_daily_forecast(self) -> list[DailyForecast]:
        """城市天气/格点天气 - 每日天气预报"""
        json_data = await self.api_get(f"{self.weather_type}/7d")
        return json_data.get("daily", []) if json_data else []

    async def update_hourly_forecast(self) -> list[HourlyForecast]:
        """城市天气/格点天气 - 逐小时天气预报"""
        json_data = await self.api_get(f"{self.weather_type}/24h")
        return json_data.get("hourly") if json_data else []

    async def update_air_now(self) -> AirNow | None:
        """空气质量-实时空气质量"""
        json_data = await self.api_get("air/now")
        return json_data.get("now") if json_data else None

    async def update_minutely_precipitation(self) -> MinutelyPrecipitation:
        """分钟预报-分钟级降水"""
        json_data = await self.api_get("minutely/5m")
        return (
            {
                "summary": json_data.get("summary", ""),
                "minutely": json_data.get("minutely", []),
            }
            if json_data
            else {"summary": "", "minutely": []}
        )

    async def update_warning_now(self) -> list[WeatherWarning]:
        """预警-天气灾害预警"""
        json_data = await self.api_get("warning/now")
        return json_data.get("warning", []) if json_data else []

    async def update_indices_1d(self) -> list[IndicesDailyItem]:
        """天气指数-天气指数预报"""
        json_data = await self.api_get("indices/1d", {"type": "0"})
        return json_data.get("daily") if json_data else []

    async def api_get(self, api: str, extra_params: Mapping[str, str] | None = None) -> dict | None:
        return await self.url_get(f"{self.dev_api_v7}/{api}", extra_params)

    async def url_get(self, url: str, extra_params: Mapping[str, str] | None = None) -> dict | None:
        if self._wait_until > datetime.now().timestamp():
            return

        params = self.params if extra_params is None else {**self.params, **extra_params}
        response = await self.http.get(url, params=params)
        json_data = await response.json()
        if not json_data:
            _LOGGER.warning("Empty response from: %s", url)
            return
        code = json_data.get("code")
        match code:
            case "200":
                return json_data
            case "204":
                _LOGGER.error("请求成功，但你查询的地区暂时没有你需要的数据。")
                self._wait_until = math.inf
                return
            case "400":
                _LOGGER.error("请求错误，可能包含错误的请求参数或缺少必选的请求参数。")
                self._wait_until = math.inf
                return
            case "401":
                _LOGGER.error(
                    "认证失败，可能使用了错误的KEY、数字签名错误、KEY的类型错误（如使用SDK的KEY去访问Web API）。"
                )
                self._wait_until = math.inf
                return
            case "402":
                _LOGGER.warning("超过访问次数或余额不足以支持继续访问服务，你可以充值、升级访问量或等待访问量重置。")
                tomorrow_zero = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
                self._wait_until = tomorrow_zero.timestamp()
                return
            case "403":
                _LOGGER.error(
                    "无访问权限，可能是绑定的PackageName、BundleID、域名IP地址不一致，或者是需要额外付费的数据。"
                )
                self._wait_until = math.inf
                return
            case "404":
                _LOGGER.error("查询的数据或地区不存在。")
                self._wait_until = math.inf
                return
            case "429":
                _LOGGER.warning("超过限定的QPM（每分钟访问次数）")
                self._wait_until = datetime.now().timestamp() + 60
                return
            case "500":
                _LOGGER.warning("无响应或超时，接口服务异常")
                self._wait_until = datetime.now().timestamp() + 60
                return
            case _:
                _LOGGER.warning("%s 未知错误 (%s)", code, url)
                self._wait_until = datetime.now().timestamp() + 600
                return
