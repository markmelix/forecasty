import json
import os
from flask import Blueprint, request
from . import api

forecast_bp = Blueprint("forecast_bp", __name__)

coords = ("55.782547", "37.629834")


def location_parse(string, provider) -> api.Geo | None:
    if len(string_coords := string.split(",")) == 2:
        coords = [float(coord) for coord in string_coords]
        return provider.get_geo(longitude=coords[0], latitude=coords[1])
    return provider.get_geo(search_string=string)


@forecast_bp.route("/accu/forecast/5days")
def five_days_forecast():
    if (location := request.args.get("location")) is None:
        return {"status": "error", "message": "location query param must be provided"}

    provider = api.AccuWeather()

    if (geo := location_parse(location, provider)) is None:
        return {"status": "error", "message": "could not parse location query param"}

    forecast = provider.get_forecast(delta=api.ForecastDelta.day, geo=geo, longs=5)

    if forecast is None:
        return {"status": "error", "message": "could not get forecast"}

    return forecast.model_dump()


@forecast_bp.route("/accu/forecast/12hours")
def twelve_hours_forecast():
    if (location := request.args.get("location")) is None:
        return {"status": "error", "message": "location query param must be provided"}

    provider = api.AccuWeather()

    if (geo := location_parse(location, provider)) is None:
        return {"status": "error", "message": "could not parse location query param"}

    forecast = provider.get_forecast(delta=api.ForecastDelta.hour, geo=geo, longs=12)

    if forecast is None:
        return {"status": "error", "message": "could not get forecast"}

    return forecast.model_dump()
