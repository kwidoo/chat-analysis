from flask import Blueprint

# Create auth blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# Import routes to register them with the blueprint
from . import routes
