from flask import Blueprint
from . import api

forecast_bp = Blueprint("forecast_bp", __name__)

coords = ("55.782547", "37.629834")


@forecast_bp.route("/")
def root():
    return api.get_forecast(*coords)
