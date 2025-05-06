"""
Main application entry point for AI3

This module creates and configures the Flask application using the app factory.
"""

import os
import sys

from cli import register_commands
from core.app_factory import create_app

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, "/app")
print("PYTHONPATH:", sys.path)

# Create a Flask application instance at the module level for Gunicorn
app = create_app()
register_commands(app)


if __name__ == "__main__":
    # Use the app instance that's already created
    app.run(host="0.0.0.0", port=5000, threaded=True)
