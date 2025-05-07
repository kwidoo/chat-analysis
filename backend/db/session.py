# db/session.py

import logging
import os

from flask import Flask, g
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

logger = logging.getLogger(__name__)
Base = declarative_base()

# Не инициализируем db здесь, оно будет в db_manager
# db = SQLAlchemy()


class DatabaseSessionManager:
    def __init__(self):
        self.engine = None
        self.Session = None
        self.connection_url = None
        self.db = SQLAlchemy()  # 👈 Переносим сюда
        self.initialized = False

    def init_app(self, app: Flask):
        if self.initialized:
            return
        self.initialized = True

        db_type = app.config.get("DB_TYPE", "mariadb")

        if db_type == "mariadb":
            self.connection_url = self._build_mysql_connection_url(app)
            if "?" not in self.connection_url:
                self.connection_url += "?charset=utf8mb4"
            elif "charset=" not in self.connection_url:
                self.connection_url += "&charset=utf8mb4"

            if not self.connection_url.startswith("mysql+pymysql://"):
                self.connection_url = self.connection_url.replace("mysql://", "mysql+pymysql://")

            self.engine = create_engine(
                self.connection_url,
                pool_size=app.config.get("DB_POOL_SIZE", 10),
                max_overflow=app.config.get("DB_MAX_OVERFLOW", 20),
                pool_recycle=app.config.get("DB_POOL_RECYCLE", 3600),
                pool_pre_ping=True,
                connect_args={"connect_timeout": 60},
            )
        else:
            db_path = app.config.get("DB_PATH", os.path.join(app.root_path, "auth.db"))
            self.connection_url = f"sqlite:///{db_path}"
            self.engine = create_engine(
                self.connection_url, connect_args={"check_same_thread": False}
            )

        app.config["SQLALCHEMY_DATABASE_URI"] = self.connection_url
        app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
        self.db.init_app(app)

        self.Session = scoped_session(
            sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        )

        @app.teardown_appcontext
        def cleanup_session(exception=None):
            session = g.pop("db_session", None)
            if session is not None:
                session.close()

        with app.app_context():
            try:
                self.db.create_all()
                logger.info("Database tables created or verified successfully")
            except Exception as e:
                logger.error(f"Error creating database tables: {str(e)}")
                raise

        logger.info(f"Database initialized with {db_type} at {self.connection_url}")

    def get_session(self):
        if "db_session" not in g:
            g.db_session = self.Session()
        return g.db_session

    def _build_mysql_connection_url(self, app: Flask) -> str:
        username = app.config.get("DB_USERNAME", "root")
        password = app.config.get("DB_PASSWORD", "")
        host = app.config.get("DB_HOST", "localhost")
        port = app.config.get("DB_PORT", 3306)
        database = app.config.get("DB_DATABASE", "auth")
        return f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}"


# 👇 Это и нужно было добавить
db_manager = DatabaseSessionManager()
db = db_manager.db
