from . import api
from flask import Flask
from .routes import forecast_bp


def make_app():
    app = Flask(__name__)

    with app.app_context():
        app.register_blueprint(forecast_bp)

    print("Application was created successfully")

    return app
