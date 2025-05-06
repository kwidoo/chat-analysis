from flask import Blueprint

from . import (
    routes,
)  # noqa: F401  # Import the routes to register them with the blueprint

files_bp = Blueprint("files", __name__, url_prefix="/api/files")
