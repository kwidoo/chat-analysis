import logging
import os

from flask import Flask, g
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

# Setup logging
logger = logging.getLogger(__name__)

# Create base class for SQLAlchemy models
Base = declarative_base()

# SQLAlchemy ORM instance
db = SQLAlchemy()


class DatabaseSessionManager:
    """
    Database session manager for SQLAlchemy.
    Handles database connection configuration and session management.
    """

    def __init__(self):
        self.engine = None
        self.Session = None
        self.connection_url = None

    def init_app(self, app: Flask):
        """
        Initialize the database with Flask app configuration.

        Args:
            app: Flask application instance
        """
        db_type = app.config.get("DB_TYPE", "sqlite")

        if db_type == "mysql":
            # MySQL configuration
            self.connection_url = self._build_mysql_connection_url(app)
            pool_size = app.config.get("DB_POOL_SIZE", 10)
            max_overflow = app.config.get("DB_MAX_OVERFLOW", 20)
            pool_recycle = app.config.get(
                "DB_POOL_RECYCLE", 3600
            )  # Recycle connections after 1 hour

            self.engine = create_engine(
                self.connection_url,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_recycle=pool_recycle,
                pool_pre_ping=True,  # Verify connections before use
            )
        else:
            # SQLite configuration (default)
            db_path = app.config.get("DB_PATH", os.path.join(app.root_path, "auth.db"))
            self.connection_url = f"sqlite:///{db_path}"
            # SQLite engine settings - check_same_thread False allows multithreaded access
            self.engine = create_engine(
                self.connection_url, connect_args={"check_same_thread": False}
            )

        # Initialize SQLAlchemy with Flask app
        app.config["SQLALCHEMY_DATABASE_URI"] = self.connection_url
        app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
        db.init_app(app)

        # Create session factory
        self.Session = scoped_session(
            sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        )

        # Register teardown function to close session
        @app.teardown_appcontext
        def cleanup_session(exception=None):
            session = g.pop("db_session", None)
            if session is not None:
                session.close()

        # Create all tables if they don't exist yet
        with app.app_context():
            db.create_all()

        logger.info(f"Database initialized with {db_type} at {self.connection_url}")

    def get_session(self):
        """
        Get a database session for the current application context.

        Returns:
            SQLAlchemy session
        """
        if "db_session" not in g:
            g.db_session = self.Session()
        return g.db_session

    def _build_mysql_connection_url(self, app: Flask) -> str:
        """
        Build MySQL connection URL from app config.

        Args:
            app: Flask application instance with config

        Returns:
            MySQL connection URL string
        """
        username = app.config.get("DB_USERNAME", "root")
        password = app.config.get("DB_PASSWORD", "")
        host = app.config.get("DB_HOST", "localhost")
        port = app.config.get("DB_PORT", 3306)
        database = app.config.get("DB_DATABASE", "auth")

        return f"mysql+mysqlconnector://{username}:{password}@{host}:{port}/{database}"
