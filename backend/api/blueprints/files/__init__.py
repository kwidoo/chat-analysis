from flask import Blueprint

files_bp = Blueprint('files', __name__, url_prefix='/api/files')

# Import the routes to register them with the blueprint
from . import routes
