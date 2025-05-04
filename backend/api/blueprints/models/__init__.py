from flask import Blueprint

models_bp = Blueprint('models', __name__, url_prefix='/api/models')

# Import the routes to register them with the blueprint
from . import routes
