"""
Application Factory

This module provides a factory function for creating the Flask application,
implementing the Factory Method pattern for better control over application initialization.
"""

import importlib
import logging
import os
import pkgutil

import config
import extensions
from core.di_container import DIContainer
from db.session import DatabaseSessionManager  # Import the DatabaseSessionManager
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
    # ✅ Dynamically load all *_provider modules from the extensions package
    for _, module_name, _ in pkgutil.iter_modules(extensions.__path__):
        if module_name.endswith("_provider"):
            importlib.import_module(f"extensions.{module_name}")

    # Configure CORS
    CORS(app, supports_credentials=True)

    # Configure session
    app.config["SESSION_TYPE"] = "filesystem"
    app.config["SESSION_PERMANENT"] = False
    app.config["SESSION_USE_SIGNER"] = True
    app.config["SESSION_FILE_DIR"] = os.path.join(
        os.path.dirname(app.instance_path), "flask_sessions"
    )

    # Initialize the database session manager
    db_manager = DatabaseSessionManager()
    # db_manager.init_app(app)
    app.db_manager = db_manager  # Attach the manager to the app for later use

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
    from api.blueprints.auth.routes import auth_bp  # noqa: E402
    from api.blueprints.files.routes import files_bp  # noqa: E402
    from api.blueprints.models.routes import models_bp  # noqa: E402

    # from api.blueprints.queue import queue_bp  # noqa: E402
    from api.blueprints.search.routes import search_bp  # noqa: E402

    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(files_bp, url_prefix="/api/files")
    app.register_blueprint(search_bp, url_prefix="/api/search")
    app.register_blueprint(models_bp, url_prefix="/api/models")
    # app.register_blueprint(queue_bp, url_prefix="/api/queue")


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
