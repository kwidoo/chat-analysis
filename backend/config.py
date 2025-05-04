# File: backend/config.py
import os
import secrets
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
    RABBITMQ_HOST: str = "localhost"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"
    RABBITMQ_VHOST: str = "/"
    RABBITMQ_CONNECTION_ATTEMPTS: int = 5
    RABBITMQ_RETRY_DELAY: int = 5
    RABBITMQ_MAX_CONNECTIONS: int = 10

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


class Config:
    """Base configuration class"""
    APP_DIR = os.path.dirname(__file__)
    DATA_DIR = os.path.join(APP_DIR, 'faiss')
    UPLOAD_DIR = os.path.join(APP_DIR, 'uploads')
    DASK_SCHEDULER_ADDRESS = 'tcp://dask-scheduler:8786'
    FAISS_DIR = os.path.join(APP_DIR, 'faiss')
    FAISS_LOCK_FILE = os.path.join(FAISS_DIR, 'index.lock')
    MODELS_DIR = os.path.join(APP_DIR, 'models')
    QUEUES_DIR = os.path.join(APP_DIR, 'queues')
    ACTIVE_MODEL = os.environ.get('ACTIVE_MODEL', 'v1')

    # Memory management
    MEMORY_LIMIT = "4GB"
    GC_INTERVAL = 300  # seconds

    # Queue monitoring
    QUEUE_STATUS = {
        "total": 0,
        "processed": 0,
        "failed": 0
    }

    # RabbitMQ Configuration
    RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST", "localhost")
    RABBITMQ_PORT = int(os.environ.get("RABBITMQ_PORT", 5672))
    RABBITMQ_USER = os.environ.get("RABBITMQ_USER", "guest")
    RABBITMQ_PASSWORD = os.environ.get("RABBITMQ_PASSWORD", "guest")
    RABBITMQ_VHOST = os.environ.get("RABBITMQ_VHOST", "/")
    RABBITMQ_CONNECTION_ATTEMPTS = int(os.environ.get("RABBITMQ_CONNECTION_ATTEMPTS", 5))
    RABBITMQ_RETRY_DELAY = int(os.environ.get("RABBITMQ_RETRY_DELAY", 5))
    RABBITMQ_MAX_CONNECTIONS = int(os.environ.get("RABBITMQ_MAX_CONNECTIONS", 10))

    # Authentication System Configuration
    SECRET_KEY = os.environ.get("SECRET_KEY")
    JWT_ACCESS_TOKEN_EXPIRES = int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRES", 3600))  # 1 hour
    JWT_REFRESH_TOKEN_EXPIRES = int(os.environ.get("JWT_REFRESH_TOKEN_EXPIRES", 604800))  # 7 days
    OAUTH_ENABLED = os.environ.get("OAUTH_ENABLED", "False").lower() in ("true", "1", "t")
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
    GITHUB_CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID")
    GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET")
    SESSION_TYPE = os.environ.get("SESSION_TYPE", "filesystem")
    ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin")
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:3000,http://localhost:8080").split(",")

    @classmethod
    def get_config_dict(cls):
        """Convert config to dictionary for validation"""
        return {
            key: value for key, value in vars(cls).items()
            if not key.startswith('__') and not callable(value)
        }

    @staticmethod
    def validate_config(config_dict):
        """Validate config using pydantic"""
        return AppConfig(**config_dict)

    @staticmethod
    def init_app(app):
        """Initialize application directories and files"""
        # Create necessary directories
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
            os.makedirs(os.path.join(app.config['APP_DIR'], 'flask_sessions'), exist_ok=True)


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False
    MEMORY_LIMIT = "2GB"  # Lower memory limit for development
    RABBITMQ_HOST = "localhost"

    # Development auth settings
    SECRET_KEY = "dev-secret-key"  # Only for development!
    OAUTH_ENABLED = True  # Enable OAuth in development for testing


class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = False
    TESTING = True
    DASK_SCHEDULER_ADDRESS = 'tcp://localhost:8786'
    # Use in-memory or temporary file storage for testing
    DATA_DIR = '/tmp/faiss_test'
    UPLOAD_DIR = '/tmp/uploads_test'
    FAISS_DIR = '/tmp/faiss_test'
    MODELS_DIR = '/tmp/models_test'
    QUEUES_DIR = '/tmp/queues_test'
    # Use local RabbitMQ for testing
    RABBITMQ_HOST = "localhost"

    # Testing auth settings
    SECRET_KEY = "test-secret-key"  # Only for testing!
    JWT_ACCESS_TOKEN_EXPIRES = 60  # Short expiry for testing
    JWT_REFRESH_TOKEN_EXPIRES = 300  # Short refresh expiry for testing
    SESSION_TYPE = "filesystem"


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    # In production, consider using environment variables for sensitive settings
    DASK_SCHEDULER_ADDRESS = os.environ.get('DASK_SCHEDULER_ADDRESS', 'tcp://dask-scheduler:8786')
    MEMORY_LIMIT = os.environ.get('MEMORY_LIMIT', "8GB")
    # RabbitMQ settings from environment variables (already handled in base class)

    # Production auth settings
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    OAUTH_ENABLED = os.environ.get("OAUTH_ENABLED", "False").lower() in ("true", "1", "t")
    SESSION_TYPE = os.environ.get("SESSION_TYPE", "redis")  # Use Redis for production


# Configuration mapping
config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}


def get_config(config_name=None):
    """Get configuration based on environment name"""
    if not config_name:
        config_name = os.environ.get('FLASK_ENV', 'default')

    config_class = config_by_name.get(config_name, config_by_name['default'])
    config_dict = config_class.get_config_dict()

    # Validate config
    validated_config = Config.validate_config(config_dict)

    return config_class
