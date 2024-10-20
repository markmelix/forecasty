import requests
import json
import os

from .cache import cached
from enum import Enum
from pydantic import BaseModel


class Geo(BaseModel):
    id: str
    name: str
    longitude: float
    latitude: float

    def __hash__(self):
        return hash((self.id, self.name, self.longitude, self.latitude))


# Variable format: name_time_measure
class WeatherConditions(BaseModel):
    temperature_average_day_c: float
    temperature_average_night_c: float
    wind_speed_day_ms: float
    wind_speed_night_ms: float
    precipitation_probability_day_percent: float
    precipitation_probability_night_percent: float
    humidity_average_day_percent: float
    humidity_average_night_percent: float


class Weather(BaseModel):
    geo: Geo
    date: str  # string in iso format
    conditions: WeatherConditions


class ForecastDelta(str, Enum):
    day = "day"
    hour = "hour"


class Forecast(BaseModel):
    units: list[Weather]
    delta: ForecastDelta

    @property
    def geo(self) -> Geo | None:
        if len(self.units) == 0:
            return
        return self.units[-1].geo

    @property
    def longs(self) -> int:
        return len(self.units)


def celsius_to_fahrenheit(celsius: float) -> float:
    return (celsius - 32) * 5 / 9


def mih_to_ms(mih: float) -> float:
    return mih / 2.237


class Provider:
    def get_geo(
        self,
        name: str | None = None,
        longitude: float | None = None,
        latitude: float | None = None,
    ) -> Geo | None: ...

    def get_forecast(
        self, geo: Geo, delta: ForecastDelta, longs: int
    ) -> Forecast | None: ...

    def __hash__(self):
        return hash(self.__class__.__name__)


class AccuWeather(Provider):
    def __init__(self):
        self._locale = "ru-ru"
        self._api_key = os.getenv("API_KEY")
        self._domain = "http://dataservice.accuweather.com"

    @cached
    def _get_geo(
        self,
        search_string: str | None = None,
        longitude: float | None = None,
        latitude: float | None = None,
    ):
        if search_string is None and longitude is None and latitude is None:
            return

        if search_string is None:
            baseurl = f"{self._domain}/locations/v1/cities/geoposition/search"
            query = f"{longitude},{latitude}"
        else:
            baseurl = f"{self._domain}/locations/v1/cities/search"
            query = search_string

        response = requests.get(
            baseurl,
            params={
                "apikey": self._api_key,
                "q": query,
                "language": self._locale,
            },
        )
        return json.loads(response.text)

    def get_geo(
        self,
        search_string: str | None = None,
        longitude: float | None = None,
        latitude: float | None = None,
    ) -> Geo | None:
        data = self._get_geo(search_string, longitude, latitude)
        if data is None or isinstance(data, list) and len(data) == 0:
            return
        data = data if search_string is None else data[0]
        return Geo(
            id=data["Key"],
            name=data["LocalizedName"],
            longitude=data["GeoPosition"]["Longitude"],
            latitude=data["GeoPosition"]["Latitude"],
        )

    @cached
    def _get_forecast(self, geo: Geo, delta: ForecastDelta, longs: int):
        raw_delta = {
            ForecastDelta.day: ("daily", "day"),
            ForecastDelta.hour: ("hourly", "hour"),
        }[delta]
        baseurl = (
            f"{self._domain}/forecasts/v1/{raw_delta[0]}/{longs}{raw_delta[1]}/{geo.id}"
        )
        response = requests.get(
            baseurl, params={"apikey": self._api_key, "details": "true"}
        )
        return json.loads(response.text)

    def _parse_dayily_forecast(self, data: dict, geo: Geo) -> Forecast:
        units = []
        for forecast in data["DailyForecasts"]:
            units.append(
                Weather(
                    geo=geo,
                    date=forecast["Date"],
                    conditions=WeatherConditions(
                        temperature_average_day_c=celsius_to_fahrenheit(
                            forecast["Day"]["WetBulbTemperature"]["Average"]["Value"]
                        ),
                        temperature_average_night_c=celsius_to_fahrenheit(
                            forecast["Night"]["WetBulbTemperature"]["Average"]["Value"]
                        ),
                        wind_speed_day_ms=forecast["Day"]["Wind"]["Speed"]["Value"],
                        wind_speed_night_ms=forecast["Night"]["Wind"]["Speed"]["Value"],
                        precipitation_probability_day_percent=forecast["Day"][
                            "PrecipitationProbability"
                        ],
                        precipitation_probability_night_percent=forecast["Night"][
                            "PrecipitationProbability"
                        ],
                        humidity_average_day_percent=forecast["Day"][
                            "RelativeHumidity"
                        ]["Average"],
                        humidity_average_night_percent=forecast["Night"][
                            "RelativeHumidity"
                        ]["Average"],
                    ),
                )
            )
        return Forecast(units=units, delta=ForecastDelta.hour)

    def _parse_hourly_forecast(self, data: dict, geo: Geo) -> Forecast:
        units = []
        for forecast in data:
            units.append(
                Weather(
                    geo=geo,
                    date=forecast["DateTime"],
                    conditions=WeatherConditions(
                        temperature_average_day_c=celsius_to_fahrenheit(
                            forecast["WetBulbTemperature"]["Value"]
                        ),
                        temperature_average_night_c=celsius_to_fahrenheit(
                            forecast["WetBulbTemperature"]["Value"]
                        ),
                        wind_speed_day_ms=forecast["Wind"]["Speed"]["Value"],
                        wind_speed_night_ms=forecast["Wind"]["Speed"]["Value"],
                        precipitation_probability_day_percent=forecast[
                            "PrecipitationProbability"
                        ],
                        precipitation_probability_night_percent=forecast[
                            "PrecipitationProbability"
                        ],
                        humidity_average_day_percent=forecast["RelativeHumidity"],
                        humidity_average_night_percent=forecast["RelativeHumidity"],
                    ),
                )
            )
        return Forecast(units=units, delta=ForecastDelta.hour)

    def get_forecast(
        self, geo: Geo, delta: ForecastDelta, longs: int
    ) -> Forecast | None:
        data = self._get_forecast(geo, delta, longs)
        if data is None:
            return
        match delta:
            case ForecastDelta.day:
                return self._parse_dayily_forecast(data, geo)
            case ForecastDelta.hour:
                return self._parse_hourly_forecast(data, geo)
