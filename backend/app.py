"""
Main application entry point for AI3

This module creates and configures the Flask application using the app factory.
"""

from core.app_factory import create_app

# Create a Flask application instance at the module level for Gunicorn
app = create_app()


if __name__ == "__main__":
    # Use the app instance that's already created
    app.run(host="0.0.0.0", port=5000, threaded=True)
