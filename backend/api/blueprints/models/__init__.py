from flask import Blueprint

from . import (
    routes,
)  # noqa: F401  # Import the routes to register them with the blueprint

models_bp = Blueprint("models", __name__, url_prefix="/api/models")
