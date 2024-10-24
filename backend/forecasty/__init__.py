from . import api
from flask import Flask
from flask_cors import CORS
from .routes import forecast_bp


def make_app():
    app = Flask(__name__)

    CORS(app)

    with app.app_context():
        app.register_blueprint(forecast_bp)

    print("Application was created successfully")

    return app
