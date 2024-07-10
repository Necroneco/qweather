from typing import Literal, TypedDict

DOMAIN = "qweather"

ATTRIBUTION = "Data provided by Qweather"
MANUFACTURER = "Qweather, Inc."

CONF_GIRD = "grid_weather"


class RealtimeWeather(TypedDict):
    """https://dev.qweather.com/en/docs/api/weather/weather-now/"""

    obsTime: str  # "2020-06-30T21:40+08:00",
    temp: str  # "24",
    feelsLike: str | None  # "26",
    icon: str  # "101",
    text: str  # "多云",
    wind360: str  # "123",
    windDir: str  # "东南风",
    windScale: str  # "1",
    windSpeed: str  # "3",
    humidity: str  # "72",
    precip: str  # "0.0",
    pressure: str  # "1003",
    vis: str | None  # "16",
    cloud: str | None  # "10",
    dew: str | None  # "21"


class DailyForecast(TypedDict):
    """https://dev.qweather.com/en/docs/api/weather/weather-daily-forecast/"""

    fxDate: str  # "2021-11-15",
    sunrise: str | None  # "06:58",
    sunset: str | None  # "16:59",
    moonrise: str | None  # "15:16",
    moonset: str | None  # "03:40",
    moonPhase: str | None  # "盈凸月",
    moonPhaseIcon: str | None  # "803",
    tempMax: str  # "12",
    tempMin: str  # "-1",
    iconDay: str  # "101",
    textDay: str  # "多云",
    iconNight: str  # "150",
    textNight: str  # "晴",
    wind360Day: str  # "45",
    windDirDay: str  # "东北风",
    windScaleDay: str  # "1-2",
    windSpeedDay: str  # "3",
    wind360Night: str  # "0",
    windDirNight: str  # "北风",
    windScaleNight: str  # "1-2",
    windSpeedNight: str  # "3",
    humidity: str  # "65",
    precip: str  # "0.0",
    pressure: str  # "1020",
    vis: str | None  # "25",
    cloud: str | None  # "4",
    uvIndex: str | None  # "3"


class HourlyForecast(TypedDict):
    """https://dev.qweather.com/en/docs/api/weather/weather-hourly-forecast/"""

    fxTime: str  # "2021-02-16T15:00+08:00",
    temp: str  # "2",
    icon: str  # "100",
    text: str  # "晴",
    wind360: str  # "335",
    windDir: str  # "西北风",
    windScale: str  # "3-4",
    windSpeed: str  # "20",
    humidity: str  # "11",
    pop: str | None  # "0",
    precip: str  # "0.0",
    pressure: str  # "1025",
    cloud: str | None  # "0",
    dew: str | None  # "-25"


class AirNow(TypedDict):
    """https://dev.qweather.com/docs/api/air/air-now/"""

    pubTime: str  # "2021-02-16T14:00+08:00",
    aqi: str  # "28",
    level: str  # "1",
    category: str  # "优",
    primary: str  # "NA",
    pm10: str  # "28",
    pm2p5: str  # "5",
    no2: str  # "3",
    so2: str  # "2",
    co: str  # "0.2",
    o3: str  # "76"


class MinutelyPrecipitationItem(TypedDict):
    fxTime: str
    precip: str
    type: Literal["rain", "snow"]


class MinutelyPrecipitation(TypedDict):
    """https://dev.qweather.com/en/docs/api/minutely/minutely-precipitation/"""

    summary: str
    minutely: list[MinutelyPrecipitationItem]


class WeatherWarning(TypedDict):
    """https://dev.qweather.com/docs/api/warning/weather-warning/"""

    id: str  # "10102010020230403103000500681616",
    sender: str | None  # "上海中心气象台",
    pubTime: str  # "2023-04-03T10:30+08:00",
    title: str  # "上海中心气象台发布大风蓝色预警[Ⅳ级/一般]",
    startTime: str | None  # "2023-04-03T10:30+08:00",
    endTime: str | None  # "2023-04-04T10:30+08:00",
    status: str  # "active",
    severity: str  # "Minor",
    severityColor: str | None  # "Blue",
    type: str  # "1006",
    typeName: str  # "大风",
    urgency: str | None  # "",
    certainty: str | None  # "",
    text: str  # "上海中心气象台2023年04月03日10时30分发布大风蓝色预警[Ⅳ级/一般]：受江淮气旋影响，预计明天傍晚以前本市大部地区将出现6级阵风7-8级的东南大风，沿江沿海地区7级阵风8-9级，请注意防范大风对高空作业、交通出行、设施农业等的不利影响。",
    related: str | None  # ""


class IndicesDailyItem(TypedDict):
    """https://dev.qweather.com/docs/api/indices/indices-forecast/"""

    date: str  # "2021-12-16"
    type: str  # "1"
    name: str  # "运动指数"
    level: str  # "3"
    category: str  # "较不宜"
    text: (
        str | None
    )  # "天气较好，但考虑天气寒冷，风力较强，推荐您进行室内运动，若户外运动请注意保暖并做好准备活动。
