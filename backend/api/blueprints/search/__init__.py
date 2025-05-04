from flask import Blueprint

search_bp = Blueprint('search', __name__, url_prefix='/api/search')

# Import the routes to register them with the blueprint
from . import routes
