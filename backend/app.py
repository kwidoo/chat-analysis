"""
Main application entry point for AI3

This module creates and configures the Flask application using the app factory.
"""

import logging
import os
import sys

from cli import register_commands
from core.app_factory import create_app

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Add current directory to Python path to ensure all modules are importable
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
if "/app" not in sys.path:  # Avoid duplicate entries
    sys.path.insert(0, "/app")
logger.info("PYTHONPATH: %s", sys.path)

try:
    # Create a Flask application instance at the module level for Gunicorn
    app = create_app()
    register_commands(app)
    logger.info("Application initialized successfully")
except Exception as e:
    logger.error(f"Error initializing application: {str(e)}", exc_info=True)
    # Re-raise the error after logging to ensure Gunicorn knows initialization failed
    raise

if __name__ == "__main__":
    # Use the app instance that's already created
    app.run(host="0.0.0.0", port=5000, threaded=True)
