"""
Application Factory

This module provides a factory function for creating the Flask application,
implementing the Factory Method pattern for better control over application initialization.
"""

import logging
import os

import config
from core.di_container import DIContainer
from flask import Flask
from flask_cors import CORS


def create_app(config_name=None) -> Flask:
    """Create and configure a Flask application instance

    Args:
        config_name: Configuration name to use (default: from environment variable)

    Returns:
        A Flask application instance
    """
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Create the Flask application
    app = Flask(__name__)

    # Load configuration
    if not config_name:
        config_name = os.environ.get("FLASK_ENV", "development")
    app.config.from_object(getattr(config, f"{config_name.capitalize()}Config"))

    # Configure the application
    _configure_app(app)

    return app


def _configure_app(app: Flask) -> None:
    """Configure the application

    Args:
        app: The Flask application instance to configure
    """
    # Configure CORS
    CORS(app, supports_credentials=True)

    # Configure session
    app.config["SESSION_TYPE"] = "filesystem"
    app.config["SESSION_PERMANENT"] = False
    app.config["SESSION_USE_SIGNER"] = True
    app.config["SESSION_FILE_DIR"] = os.path.join(
        os.path.dirname(app.instance_path), "flask_sessions"
    )

    # Set up the Dependency Injection Container
    di_container = DIContainer(app)
    app.di_container = di_container

    # Set up services
    _setup_services(app)

    # Register blueprints
    _register_blueprints(app)

    # Register error handlers
    _register_error_handlers(app)

    # Register CLI commands
    _register_commands(app)


def _setup_services(app: Flask) -> None:
    """Set up application services using the DI container

    Args:
        app: The Flask application instance
    """
    # Initialize all services through the DI container
    app.di_container.setup_services()

    # Make common services available through the app for backward compatibility
    app.auth_service = app.di_container.get_auth_service()
    app.embedding_service = app.di_container.get_embedding_service()
    app.index_service = app.di_container.get_index_service()
    app.queue_service = app.di_container.get_queue_service()


def _register_blueprints(app: Flask) -> None:
    """Register Flask blueprints

    Args:
        app: The Flask application instance
    """
    from api.blueprints.auth import auth_bp  # noqa: E402
    from api.blueprints.files import files_bp  # noqa: E402
    from api.blueprints.models import models_bp  # noqa: E402
    from api.blueprints.queue import queue_bp  # noqa: E402
    from api.blueprints.search import search_bp  # noqa: E402

    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(files_bp, url_prefix="/api/files")
    app.register_blueprint(search_bp, url_prefix="/api/search")
    app.register_blueprint(models_bp, url_prefix="/api/models")
    app.register_blueprint(queue_bp, url_prefix="/api/queue")


def _register_error_handlers(app: Flask) -> None:
    """Register error handlers

    Args:
        app: The Flask application instance
    """
    from api.error_handlers import register_error_handlers  # noqa: E402

    register_error_handlers(app)


def _register_commands(app: Flask) -> None:
    """Register CLI commands

    Args:
        app: The Flask application instance
    """
    # Import CLI commands here to avoid circular imports
    from cli import register_commands  # noqa: E402

    register_commands(app)
