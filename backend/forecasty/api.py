import requests
import json
import os

from .cache import cached
from datetime import datetime, timedelta
from pydantic import BaseModel


class Geo(BaseModel):
    _id: str
    name: str
    longitude: float
    latitude: float


class WeatherVariables(BaseModel):
    temperature: int
    wind_speed_ms: int
    precipitation_probability: int


class Weather(BaseModel):
    geo: Geo
    time: datetime
    variables: WeatherVariables


class Forecast(BaseModel):
    units: list[Weather]

    @property
    def delta(self) -> timedelta:
        if len(self.units) < 2:
            return timedelta()
        return self.units[-1].time - self.units[-2].time

    @property
    def geo(self) -> Geo | None:
        if len(self.units) == 0:
            return
        return self.units[-1].geo

    @property
    def longs(self) -> int:
        return len(self.units)


class Provider:
    def get_geo(
        self,
        name: str | None = None,
        longitude: float | None = None,
        latitude: float | None = None,
    ) -> Geo | None: ...

    def get_weather(self, geo: Geo, time: datetime) -> Weather | None: ...

    def get_forecast(
        self, geo: Geo, delta: timedelta, longs: int
    ) -> Forecast | None: ...


class AccuWeather(Provider):
    def __init__(self):
        self._locale = "ru-ru"
        self._api_key = os.getenv("API_KEY")

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
            baseurl = "http://dataservice.accuweather.com/locations/v1/cities/geoposition/search"
            query = f"{longitude},{latitude}"
        else:
            baseurl = "http://dataservice.accuweather.com/locations/v1/cities/search"
            query = search_string

        return json.loads(
            requests.get(
                baseurl,
                params={
                    "apikey": self._api_key,
                    "q": query,
                    "language": self._locale,
                },
            )
        )

    def get_geo(
        self,
        search_string: str | None = None,
        longitude: float | None = None,
        latitude: float | None = None,
    ) -> Geo | None:
        location = self._get_geo(search_string, longitude, latitude)
        if location is None:
            return
        return Geo(
            _id=location["Details"]["Key"],
            name=location["LocalizedName"],
            longitude=location["GeoPosition"]["Longitude"],
            latitude=location["GeoPosition"]["Latitude"],
        )

    @cached
    def _get_forecast(self, geo: Geo, delta: timedelta, longs: int):
        location_key = geo._id
        baseurl = (
            f"http://dataservice.accuweather.com/forecasts/v1/daily/1day/{location_key}"
        )
        response = requests.get(
            baseurl,
            params={"apikey": self._api_key, "details": "true"},
        )
        return json.loads(response.text)

    @cached
    def get_forecast(
        self, geo: Geo, delta: timedelta, longs: int
    ) -> Forecast | None: ...


@cached
def get_location_key(longitude, latitude):
    baseurl = (
        "http://dataservice.accuweather.com/locations/v1/cities/geoposition/search"
    )
    response = requests.get(
        baseurl,
        params={
            "apikey": API_KEY,
            "q": f"{longitude},{latitude}",
        },
    )
    return json.loads(response.content)["Key"]


@cached
def get_forecast(longitude, latitude):
    location_key = get_location_key(longitude, latitude)
    baseurl = (
        f"http://dataservice.accuweather.com/forecasts/v1/daily/1day/{location_key}"
    )
    response = requests.get(
        baseurl,
        params={"apikey": API_KEY, "details": "true"},
    )
    return json.loads(response.text)
