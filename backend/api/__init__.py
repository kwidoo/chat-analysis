from flask import Flask
from api.blueprints.files import files_bp
from api.blueprints.models import models_bp
from api.blueprints.search import search_bp
from api.blueprints.auth import auth_bp


def register_blueprints(app: Flask) -> None:
    """Register all blueprints with the Flask application

    Args:
        app: Flask application instance
    """
    app.register_blueprint(files_bp)
    app.register_blueprint(models_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(auth_bp)
