import requests
import json
import os

longitude = "55.782547"
latitude = "37.629834"

API_KEY = os.getenv("API_KEY")


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
