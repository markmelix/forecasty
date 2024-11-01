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
    temperature_c: float
    wind_speed_ms: float
    humidity_percent: float
    precipitation_probability_percent: float

    def is_favorable(self) -> bool:
        return (
            (-15 <= self.temperature_c <= 30)
            and (self.precipitation_probability_percent < 50)
            and (self.wind_speed_ms < 19)
        )


class Weather(BaseModel):
    geo: Geo
    date: str  # string in iso format
    conditions: WeatherConditions
    favorable: bool
    description: str


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


def fahrenheit_to_celsius(fahrenheit):
    return (fahrenheit - 32) * 5 / 9


def mih_to_ms(mih: float) -> float:
    return mih / 2.237


class Provider:
    def get_geo(
        self,
        name: str | None = None,
        longitude: float | None = None,
        latitude: float | None = None,
    ) -> Geo | None: ...

    def get_conditions(self, geo: Geo) -> Weather: ...

    def get_forecast(
        self, geo: Geo, delta: ForecastDelta, longs: int
    ) -> Forecast | None: ...

    def __hash__(self):
        return hash(self.__class__.__name__)


class ApiException(Exception):
    pass


class ApiKeyExpiredError(ApiException):
    pass


class AccuWeather(Provider):
    def __init__(self):
        self._locale = "ru-ru"
        self._api_key = os.getenv("API_KEY")
        self._domain = "http://dataservice.accuweather.com"

    def _check_api_key_expiration(self, response):
        if (
            "The allowed number of requests has been exceeded".lower()
            in response.text.lower()
        ):
            raise ApiKeyExpiredError("Обновите AccuWeather API ключ в .env файле")

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
        self._check_api_key_expiration(response)
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

    def _get_conditions(self, geo: Geo):
        baseurl = f"{self._domain}/currentconditions/v1/{geo.id}"
        response = requests.get(
            baseurl,
            params={
                "apikey": self._api_key,
                "details": "true",
                "language": self._locale,
            },
        )
        self._check_api_key_expiration(response)
        return json.loads(response.text)

    def get_conditions(self, geo: Geo) -> Weather:
        data = self._get_conditions(geo)[0]
        conds = WeatherConditions(
            temperature_c=fahrenheit_to_celsius(
                data["Temperature"]["Imperial"]["Value"]
            ),
            wind_speed_ms=mih_to_ms(data["Wind"]["Speed"]["Imperial"]["Value"]),
            humidity_percent=data["RelativeHumidity"],
            precipitation_probability_percent=int(data["HasPrecipitation"]) * 100,
        )
        return Weather(
            geo=geo,
            date=data["LocalObservationDateTime"],
            conditions=conds,
            favorable=conds.is_favorable(),
            description=data["WeatherText"],
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
            baseurl,
            params={
                "apikey": self._api_key,
                "details": "true",
                "language": self._locale,
            },
        )
        self._check_api_key_expiration(response)
        return json.loads(response.text)

    def _parse_dayily_forecast(self, data: dict, geo: Geo) -> Forecast:
        units = []
        for forecast in data["DailyForecasts"]:
            conds = WeatherConditions(
                temperature_c=fahrenheit_to_celsius(
                    forecast["Day"]["WetBulbTemperature"]["Average"]["Value"]
                ),
                wind_speed_ms=forecast["Day"]["Wind"]["Speed"]["Value"],
                precipitation_probability_percent=forecast["Day"][
                    "PrecipitationProbability"
                ],
                humidity_percent=forecast["Day"]["RelativeHumidity"]["Average"],
            )
            units.append(
                Weather(
                    geo=geo,
                    date=forecast["Date"],
                    conditions=conds,
                    favorable=conds.is_favorable(),
                    description=forecast["Day"]["LongPhrase"],
                )
            )
        return Forecast(units=units, delta=ForecastDelta.hour)

    def _parse_hourly_forecast(self, data: dict, geo: Geo) -> Forecast:
        units = []
        for forecast in data:
            conds = WeatherConditions(
                temperature_c=fahrenheit_to_celsius(
                    forecast["WetBulbTemperature"]["Value"]
                ),
                wind_speed_ms=forecast["Wind"]["Speed"]["Value"],
                precipitation_probability_percent=forecast["PrecipitationProbability"],
                humidity_percent=forecast["RelativeHumidity"],
            )
            units.append(
                Weather(
                    geo=geo,
                    date=forecast["DateTime"],
                    conditions=conds,
                    favorable=conds.is_favorable(),
                    description=forecast["IconPhrase"],
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
