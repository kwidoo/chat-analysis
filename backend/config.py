# File: backend/config.py
import os
import secrets
import urllib.parse
from pydantic import BaseModel, validator
from typing import Dict, Any, Optional, List


class AppConfig(BaseModel):
    """Configuration settings for the application with validation"""
    DATA_DIR: str
    UPLOAD_DIR: str
    DASK_SCHEDULER_ADDRESS: str
    FAISS_LOCK_FILE: str
    FAISS_DIR: str
    MODELS_DIR: str
    QUEUES_DIR: str
    ACTIVE_MODEL: str
    MEMORY_LIMIT: str = "4GB"
    GC_INTERVAL: int = 300  # seconds
    QUEUE_STATUS: Dict[str, int] = {"total": 0, "processed": 0, "failed": 0}

    # RabbitMQ Configuration
    RABBITMQ_HOST: str
    RABBITMQ_PORT: int
    RABBITMQ_USER: str
    RABBITMQ_PASSWORD: str
    RABBITMQ_VHOST: str
    RABBITMQ_CONNECTION_ATTEMPTS: int
    RABBITMQ_RETRY_DELAY: int
    RABBITMQ_MAX_CONNECTIONS: int

    # Database Configuration
    DB_TYPE: str = "sqlite"  # sqlite or mysql
    DB_PATH: Optional[str] = None  # Path for SQLite database
    DB_HOST: Optional[str] = None  # Host for MySQL
    DB_PORT: Optional[int] = None  # Port for MySQL
    DB_USERNAME: Optional[str] = None  # Username for MySQL
    DB_PASSWORD: Optional[str] = None  # Password for MySQL
    DB_DATABASE: Optional[str] = None  # Database name for MySQL
    DB_POOL_SIZE: int = 10  # Connection pool size
    DB_MAX_OVERFLOW: int = 20  # Max overflow connections
    DB_POOL_RECYCLE: int = 3600  # Connection recycle time in seconds

    # Authentication System Configuration
    SECRET_KEY: Optional[str] = None
    JWT_ACCESS_TOKEN_EXPIRES: int = 3600  # 1 hour
    JWT_REFRESH_TOKEN_EXPIRES: int = 604800  # 7 days
    OAUTH_ENABLED: bool = False
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GITHUB_CLIENT_ID: Optional[str] = None
    GITHUB_CLIENT_SECRET: Optional[str] = None
    SESSION_TYPE: str = "filesystem"
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin"
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]

    @validator('ACTIVE_MODEL')
    def validate_active_model(cls, v):
        if v not in ('v1', 'v2'):
            raise ValueError(f"Invalid model version: {v}")
        return v

    @validator('DB_TYPE')
    def validate_db_type(cls, v):
        if v not in ('sqlite', 'mysql'):
            raise ValueError(f"Invalid database type: {v}")
        return v


class Config:
    """Base configuration class - defines defaults and structure"""
    APP_DIR = os.path.dirname(__file__)
    DATA_DIR = os.path.join(APP_DIR, 'faiss')
    UPLOAD_DIR = os.path.join(APP_DIR, 'uploads')
    DASK_SCHEDULER_ADDRESS = 'tcp://dask-scheduler:8786' # Default for containers
    FAISS_DIR = os.path.join(APP_DIR, 'faiss')
    FAISS_LOCK_FILE = os.path.join(FAISS_DIR, 'index.lock')
    MODELS_DIR = os.path.join(APP_DIR, 'models')
    QUEUES_DIR = os.path.join(APP_DIR, 'queues')
    ACTIVE_MODEL = 'v1' # Default

    # Memory management
    MEMORY_LIMIT = "4GB"
    GC_INTERVAL = 300

    # Queue monitoring
    QUEUE_STATUS = {"total": 0, "processed": 0, "failed": 0}

    # Default RabbitMQ settings (will be overridden by get_config_object logic)
    RABBITMQ_HOST = "localhost"
    RABBITMQ_PORT = 5672
    RABBITMQ_USER = "guest"
    RABBITMQ_PASSWORD = "guest"
    RABBITMQ_VHOST = "/"
    RABBITMQ_CONNECTION_ATTEMPTS = 5
    RABBITMQ_RETRY_DELAY = 5
    RABBITMQ_MAX_CONNECTIONS = 10

    # Database Configuration Defaults
    DB_TYPE = "sqlite"
    DB_PATH = os.path.join(APP_DIR, 'auth.db')
    DB_HOST = "localhost"
    DB_PORT = 3306
    DB_USERNAME = "root"
    DB_PASSWORD = ""
    DB_DATABASE = "ai3_auth"
    DB_POOL_SIZE = 10
    DB_MAX_OVERFLOW = 20
    DB_POOL_RECYCLE = 3600

    # Authentication System Configuration Defaults
    SECRET_KEY = None
    JWT_ACCESS_TOKEN_EXPIRES = 3600
    JWT_REFRESH_TOKEN_EXPIRES = 604800
    OAUTH_ENABLED = False
    GOOGLE_CLIENT_ID = None
    GOOGLE_CLIENT_SECRET = None
    GITHUB_CLIENT_ID = None
    GITHUB_CLIENT_SECRET = None
    SESSION_TYPE = "filesystem"
    ADMIN_USERNAME = "admin"
    ADMIN_PASSWORD = "admin"
    CORS_ORIGINS = ["http://localhost:3000", "http://localhost:8080"]

    @staticmethod
    def init_app(app):
        """Initialize application directories and files"""
        # Create necessary directories using app.config values
        os.makedirs(app.config['DATA_DIR'], exist_ok=True)
        os.makedirs(app.config['UPLOAD_DIR'], exist_ok=True)
        os.makedirs(app.config['MODELS_DIR'], exist_ok=True)
        os.makedirs(app.config['QUEUES_DIR'], exist_ok=True)
        os.makedirs(os.path.join(app.config['FAISS_DIR'], 'indexes'), exist_ok=True)

        # Create active_model.txt if it doesn't exist
        active_model_path = os.path.join(app.config['MODELS_DIR'], 'active_model.txt')
        if not os.path.exists(active_model_path):
            with open(active_model_path, 'w') as f:
                f.write(app.config['ACTIVE_MODEL'])

        # Create directory for Flask sessions if using filesystem session type
        if app.config.get('SESSION_TYPE') == 'filesystem':
            flask_session_dir = os.path.join(app.config['APP_DIR'], 'flask_sessions')
            os.makedirs(flask_session_dir, exist_ok=True)
            app.config['SESSION_FILE_DIR'] = flask_session_dir


class DevelopmentConfig(Config):
    """Development specific settings"""
    DEBUG = True
    TESTING = False
    MEMORY_LIMIT = "2GB"
    SECRET_KEY = "dev-secret-key" # Override default
    OAUTH_ENABLED = True # Override default
    DB_TYPE = "sqlite"  # Use SQLite for development
    DB_PATH = os.path.join(Config.APP_DIR, 'dev_auth.db')


class TestingConfig(Config):
    """Testing specific settings"""
    DEBUG = False
    TESTING = True
    DASK_SCHEDULER_ADDRESS = 'tcp://localhost:8786' # Override for local testing
    # Use temporary directories for testing
    DATA_DIR = '/tmp/faiss_test'
    UPLOAD_DIR = '/tmp/uploads_test'
    FAISS_DIR = '/tmp/faiss_test'
    MODELS_DIR = '/tmp/models_test'
    QUEUES_DIR = '/tmp/queues_test'
    SECRET_KEY = "test-secret-key" # Override default
    JWT_ACCESS_TOKEN_EXPIRES = 60
    JWT_REFRESH_TOKEN_EXPIRES = 300
    DB_TYPE = "sqlite"  # Use SQLite for testing
    DB_PATH = "/tmp/test_auth.db"  # Use temp path for testing


class ProductionConfig(Config):
    """Production specific settings"""
    DEBUG = False
    TESTING = False
    MEMORY_LIMIT = "8GB" # Override default
    SESSION_TYPE = "redis" # Override default
    DB_TYPE = "mysql"  # Use MySQL for production
    # DB credentials should be set via environment variables


# Configuration mapping
config_by_name: Dict[str, type[Config]] = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}


def get_config_object(config_name: Optional[str] = None) -> Config:
    """
    Get configuration object based on environment name, applying environment variables.
    Returns an *instance* of the config class with final values.
    """
    if not config_name:
        config_name = os.environ.get('FLASK_ENV', 'default')

    # Get the appropriate config class
    ConfigClass = config_by_name.get(config_name, config_by_name['default'])

    # Create an instance to hold the config values
    config_instance = ConfigClass()

    # --- Apply Environment Variables ---

    # Core settings
    config_instance.ACTIVE_MODEL = os.environ.get('ACTIVE_MODEL', config_instance.ACTIVE_MODEL)
    config_instance.MEMORY_LIMIT = os.environ.get('MEMORY_LIMIT', config_instance.MEMORY_LIMIT)
    config_instance.DASK_SCHEDULER_ADDRESS = os.environ.get('DASK_SCHEDULER_ADDRESS', config_instance.DASK_SCHEDULER_ADDRESS)

    # Database configuration
    config_instance.DB_TYPE = os.environ.get("DB_TYPE", config_instance.DB_TYPE)
    config_instance.DB_PATH = os.environ.get("DB_PATH", config_instance.DB_PATH)
    config_instance.DB_HOST = os.environ.get("DB_HOST", config_instance.DB_HOST)
    config_instance.DB_PORT = int(os.environ.get("DB_PORT", config_instance.DB_PORT))
    config_instance.DB_USERNAME = os.environ.get("DB_USERNAME", config_instance.DB_USERNAME)
    config_instance.DB_PASSWORD = os.environ.get("DB_PASSWORD", config_instance.DB_PASSWORD)
    config_instance.DB_DATABASE = os.environ.get("DB_DATABASE", config_instance.DB_DATABASE)
    config_instance.DB_POOL_SIZE = int(os.environ.get("DB_POOL_SIZE", config_instance.DB_POOL_SIZE))
    config_instance.DB_MAX_OVERFLOW = int(os.environ.get("DB_MAX_OVERFLOW", config_instance.DB_MAX_OVERFLOW))
    config_instance.DB_POOL_RECYCLE = int(os.environ.get("DB_POOL_RECYCLE", config_instance.DB_POOL_RECYCLE))

    # RabbitMQ - Prioritize URL, then individual vars, then class defaults
    rabbitmq_url = os.environ.get("RABBITMQ_URL")
    if rabbitmq_url:
        try:
            parsed_url = urllib.parse.urlparse(rabbitmq_url)
            config_instance.RABBITMQ_HOST = parsed_url.hostname or config_instance.RABBITMQ_HOST
            config_instance.RABBITMQ_PORT = parsed_url.port or config_instance.RABBITMQ_PORT
            config_instance.RABBITMQ_USER = parsed_url.username or config_instance.RABBITMQ_USER
            config_instance.RABBITMQ_PASSWORD = parsed_url.password or config_instance.RABBITMQ_PASSWORD
            config_instance.RABBITMQ_VHOST = parsed_url.path.lstrip('/') or config_instance.RABBITMQ_VHOST
        except Exception as e:
            print(f"Warning: Could not parse RABBITMQ_URL: {e}. Falling back to defaults/other env vars.")
            # Fallback to individual env vars if URL parsing fails
            config_instance.RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST", config_instance.RABBITMQ_HOST)
            config_instance.RABBITMQ_PORT = int(os.environ.get("RABBITMQ_PORT", config_instance.RABBITMQ_PORT))
            config_instance.RABBITMQ_USER = os.environ.get("RABBITMQ_USER", config_instance.RABBITMQ_USER)
            config_instance.RABBITMQ_PASSWORD = os.environ.get("RABBITMQ_PASSWORD", config_instance.RABBITMQ_PASSWORD)
            config_instance.RABBITMQ_VHOST = os.environ.get("RABBITMQ_VHOST", config_instance.RABBITMQ_VHOST)
    else:
        # If no URL, use individual env vars or defaults
        config_instance.RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST", config_instance.RABBITMQ_HOST)
        config_instance.RABBITMQ_PORT = int(os.environ.get("RABBITMQ_PORT", config_instance.RABBITMQ_PORT))
        config_instance.RABBITMQ_USER = os.environ.get("RABBITMQ_USER", config_instance.RABBITMQ_USER)
        config_instance.RABBITMQ_PASSWORD = os.environ.get("RABBITMQ_PASSWORD", config_instance.RABBITMQ_PASSWORD)
        config_instance.RABBITMQ_VHOST = os.environ.get("RABBITMQ_VHOST", config_instance.RABBITMQ_VHOST)

    config_instance.RABBITMQ_CONNECTION_ATTEMPTS = int(os.environ.get("RABBITMQ_CONNECTION_ATTEMPTS", config_instance.RABBITMQ_CONNECTION_ATTEMPTS))
    config_instance.RABBITMQ_RETRY_DELAY = int(os.environ.get("RABBITMQ_RETRY_DELAY", config_instance.RABBITMQ_RETRY_DELAY))
    config_instance.RABBITMQ_MAX_CONNECTIONS = int(os.environ.get("RABBITMQ_MAX_CONNECTIONS", config_instance.RABBITMQ_MAX_CONNECTIONS))

    # Authentication
    # Use secrets.token_hex only if SECRET_KEY is not set by env var *and* not overridden by subclass
    default_secret = secrets.token_hex(32) if config_name == 'production' and ConfigClass.SECRET_KEY is None else ConfigClass.SECRET_KEY
    config_instance.SECRET_KEY = os.environ.get("SECRET_KEY", default_secret)

    config_instance.JWT_ACCESS_TOKEN_EXPIRES = int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRES", config_instance.JWT_ACCESS_TOKEN_EXPIRES))
    config_instance.JWT_REFRESH_TOKEN_EXPIRES = int(os.environ.get("JWT_REFRESH_TOKEN_EXPIRES", config_instance.JWT_REFRESH_TOKEN_EXPIRES))
    # Handle boolean conversion carefully for OAUTH_ENABLED
    oauth_env = os.environ.get("OAUTH_ENABLED")
    if oauth_env is not None:
         config_instance.OAUTH_ENABLED = oauth_env.lower() in ("true", "1", "t")
    # else: it keeps the value from the ConfigClass instance

    config_instance.GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", config_instance.GOOGLE_CLIENT_ID)
    config_instance.GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", config_instance.GOOGLE_CLIENT_SECRET)
    config_instance.GITHUB_CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID", config_instance.GITHUB_CLIENT_ID)
    config_instance.GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET", config_instance.GITHUB_CLIENT_SECRET)
    config_instance.SESSION_TYPE = os.environ.get("SESSION_TYPE", config_instance.SESSION_TYPE)
    config_instance.ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", config_instance.ADMIN_USERNAME)
    config_instance.ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", config_instance.ADMIN_PASSWORD)
    config_instance.CORS_ORIGINS = os.environ.get("CORS_ORIGINS", ",".join(config_instance.CORS_ORIGINS)).split(",")


    # --- Validate Config ---
    # Convert instance attributes to dict for Pydantic validation
    config_dict = {key: getattr(config_instance, key)
                   for key in AppConfig.model_fields
                   if hasattr(config_instance, key)}

    try:
        AppConfig(**config_dict) # Validate against AppConfig model
        print(f"Configuration loaded successfully for '{config_name}':")
        # print(f"  RABBITMQ_HOST: {config_instance.RABBITMQ_HOST}") # Debug print
        # print(f"  RABBITMQ_PORT: {config_instance.RABBITMQ_PORT}") # Debug print
    except Exception as e:
        print(f"Configuration validation failed for {config_name} ({ConfigClass.__name__})")
        print(f"Config dictionary provided for validation: {config_dict}")
        raise e # Re-raise the validation error

    return config_instance # Return the populated instance


# Keep the old get_config function signature for compatibility if needed elsewhere,
# but make it use the new logic. Flask expects from_object to work with classes or objects.
# Returning the instance is generally safer for applying env vars correctly.
def get_config(config_name=None):
     """
     Legacy wrapper for compatibility. Returns the config *class* after ensuring
     an instance created with get_config_object validates correctly.
     Flask's from_object can handle classes, but this ensures validation runs.
     """
     # Run validation by creating an instance
     validated_instance = get_config_object(config_name)
     # Return the class that was used to create the instance
     return validated_instance.__class__
