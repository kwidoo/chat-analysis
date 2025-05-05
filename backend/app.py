import os
import logging
from flask import Flask
import time
import secrets
from flask_session import Session
import urllib.parse

from config import get_config, get_config_object, Config
from api import register_blueprints
from api.error_handlers import register_error_handlers
from services.embedding_service import ModelRegistry
from services.index_service import IndexManager
from services.queue_service import FileProcessingQueueService
from services.queue_processor import QueueProcessor
from services.message_broker import RabbitMQConnectionPool
from services.file_processor_producer import FileProcessorProducer
from services.file_processor_consumer import SupervisorProcess
from services.index_version_manager import GitIndexVersionManager
from services.index_health_monitor import IndexHealthMonitor
from services.distributed_indexer import DaskDistributedIndexer
from services.auth_service import AuthService
from services.permission_middleware import PermissionMiddleware
from services.oauth_integration import OAuthIntegration, create_google_provider
from dask.distributed import Client


def setup_dask_client(app):
    """Initialize Dask client for distributed processing

    Args:
        app: Flask application instance
    """
    logger = logging.getLogger(__name__)

    try:
        app.dask_client = Client(address=app.config['DASK_SCHEDULER_ADDRESS'])
        logger.info(f"Connected to Dask scheduler at {app.config['DASK_SCHEDULER_ADDRESS']}")

        # Register clean-up
        @app.teardown_appcontext
        def close_dask_client(exception=None):
            if hasattr(app, 'dask_client'):
                app.dask_client.close()
                logger.info("Closed Dask client connection")

    except Exception as e:
        logger.warning(f"Failed to connect to Dask scheduler: {e}. Some distributed features may be unavailable.")
        app.dask_client = None


def setup_rabbitmq_pool(app):
    """Initialize RabbitMQ connection pool

    Args:
        app: Flask application instance
    """
    logger = logging.getLogger(__name__)

    # Log the config values being used for RabbitMQ connection
    rmq_host = app.config.get('RABBITMQ_HOST')
    rmq_port = app.config.get('RABBITMQ_PORT')
    rmq_user = app.config.get('RABBITMQ_USER')
    rmq_vhost = app.config.get('RABBITMQ_VHOST')
    logger.info(f"Attempting to setup RabbitMQ pool with Host: {rmq_host}, Port: {rmq_port}, User: {rmq_user}, VHost: {rmq_vhost}")

    try:
        app.rabbitmq_pool = RabbitMQConnectionPool(
            host=rmq_host, # Use the retrieved variable
            port=rmq_port, # Use the retrieved variable
            user=rmq_user, # Use the retrieved variable
            password=app.config['RABBITMQ_PASSWORD'], # Password might be sensitive, get directly
            virtual_host=rmq_vhost, # Use the retrieved variable
            connection_attempts=app.config['RABBITMQ_CONNECTION_ATTEMPTS'],
            retry_delay=app.config['RABBITMQ_RETRY_DELAY'],
            max_connections=app.config['RABBITMQ_MAX_CONNECTIONS']
        )
        logger.info(f"Initialized RabbitMQ connection pool for {app.config['RABBITMQ_HOST']}:{app.config['RABBITMQ_PORT']}")
    except Exception as e:
        logger.warning(f"Failed to initialize RabbitMQ connection pool: {e}. Message queue features will be unavailable.")
        app.rabbitmq_pool = None


def setup_auth_system(app):
    """Initialize Authentication System

    Args:
        app: Flask application instance
    """
    logger = logging.getLogger(__name__)

    try:
        # Setup AuthService with JWT
        secret_key = app.config.get('SECRET_KEY') or secrets.token_hex(32)
        app.config['SECRET_KEY'] = secret_key  # Set it if it wasn't provided

        token_expiry = app.config.get('JWT_ACCESS_TOKEN_EXPIRES', 3600)  # 1 hour default
        refresh_expiry = app.config.get('JWT_REFRESH_TOKEN_EXPIRES', 86400 * 7)  # 7 days default

        # Create auth service
        app.auth_service = AuthService(
            secret_key=secret_key,
            token_expiry=token_expiry,
            refresh_expiry=refresh_expiry
        )

        # Setup permission middleware
        app.permission_middleware = PermissionMiddleware(app.auth_service)
        app.permission_middleware.init_app(app)

        # Add default admin user in development mode
        if app.config.get('ENV') == 'development':
            try:
                admin_username = app.config.get('ADMIN_USERNAME', 'admin')
                admin_password = app.config.get('ADMIN_PASSWORD', 'admin')
                app.auth_service.create_user(
                    username=admin_username,
                    password=admin_password,
                    roles=["admin"]
                )
                logger.info(f"Created default admin user: {admin_username}")
            except ValueError:
                logger.info(f"Admin user {app.config.get('ADMIN_USERNAME', 'admin')} already exists")

        # Setup OAuth integration if configured
        if app.config.get('OAUTH_ENABLED', False):
            app.session = Session()
            app.session.init_app(app)

            app.oauth_integration = OAuthIntegration(app.auth_service)

            # Register Google provider if configured
            if app.config.get('GOOGLE_CLIENT_ID') and app.config.get('GOOGLE_CLIENT_SECRET'):
                google_provider = create_google_provider(
                    app.config.get('GOOGLE_CLIENT_ID'),
                    app.config.get('GOOGLE_CLIENT_SECRET')
                )
                app.oauth_integration.register_provider(google_provider)
                logger.info("Registered Google OAuth provider")

            # Register GitHub provider if configured
            if app.config.get('GITHUB_CLIENT_ID') and app.config.get('GITHUB_CLIENT_SECRET'):
                from services.oauth_integration import create_github_provider
                github_provider = create_github_provider(
                    app.config.get('GITHUB_CLIENT_ID'),
                    app.config.get('GITHUB_CLIENT_SECRET')
                )
                app.oauth_integration.register_provider(github_provider)
                logger.info("Registered GitHub OAuth provider")

            app.oauth_integration.init_app(app)
            logger.info("OAuth integration initialized")

        logger.info("Authentication system initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize Authentication System: {e}")
        raise


def setup_logging(app):
    """Configure logging

    Args:
        app: Flask application instance
    """
    log_level = app.config.get('LOG_LEVEL', 'INFO')
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def setup_route_aliases(app):
    """Set up route aliases for the application

    Args:
        app: Flask application instance
    """
    from flask import redirect, request

    @app.route('/api/upload', methods=['POST'])
    def upload_alias():
        # Forward the request to the files upload endpoint
        return app.view_functions['files.upload_files']()


def create_app(config_name=None):
    """Create and configure the Flask application

    Args:
        config_name: Configuration name to use (development, production, testing)

    Returns:
        Flask application instance
    """
    app = Flask(__name__)

    # Load configuration using the instance from get_config_object
    app_config_instance = get_config_object(config_name)  # New way using instance
    app.config.from_object(app_config_instance)  # Load from the instance

    # --- Explicitly apply RabbitMQ URL from environment AFTER loading config object ---
    rabbitmq_url_env = os.environ.get("RABBITMQ_URL")
    if rabbitmq_url_env:
        try:
            parsed_url = urllib.parse.urlparse(rabbitmq_url_env)
            if parsed_url.hostname:
                app.config['RABBITMQ_HOST'] = parsed_url.hostname
            if parsed_url.port:
                app.config['RABBITMQ_PORT'] = parsed_url.port
            if parsed_url.username:
                app.config['RABBITMQ_USER'] = parsed_url.username
            if parsed_url.password:
                app.config['RABBITMQ_PASSWORD'] = parsed_url.password
            vhost = parsed_url.path.lstrip('/')
            if vhost: # Only update if vhost is not empty in URL
                app.config['RABBITMQ_VHOST'] = vhost
            # Note: Connection attempts, retry delay, max connections still come from config object/defaults
        except Exception as e:
            # Log if parsing fails, but proceed with potentially default/other env var values
            logging.getLogger(__name__).warning(f"Could not parse RABBITMQ_URL in create_app: {e}")
    # --- End of explicit RabbitMQ URL override ---

    # Set up logging
    setup_logging(app)
    logger = logging.getLogger(__name__)
    # Use the actual config name used
    actual_config_name = os.environ.get('FLASK_ENV', 'default') if config_name is None else config_name
    logger.info(f"Starting application with {actual_config_name} configuration")

    # Initialize application directories and files using the base Config class method
    # Note: init_app uses app.config which is now correctly populated
    Config.init_app(app)

    # Set up Authentication System
    setup_auth_system(app)

    # Set up Dask client for distributed processing
    setup_dask_client(app)

    # Set up RabbitMQ connection pool
    # This will now use the correct values from app.config
    setup_rabbitmq_pool(app)

    # Register error handlers
    register_error_handlers(app)

    # Initialize services
    setup_services(app)

    # Register blueprints
    register_blueprints(app)

    # Add route alias for upload endpoint
    setup_route_aliases(app)

    @app.route('/api/health')
    @app.route('/health')
    def health_check():
        # Check RabbitMQ connection pool health
        rabbitmq_health = app.rabbitmq_pool.health_check() if app.rabbitmq_pool else False

        # Check index health
        index_health = app.index_health_monitor.detect_corruption() if hasattr(app, 'index_health_monitor') else {"status": "unknown"}

        return {
            "status": "healthy",
            "model": app.config['ACTIVE_MODEL'],
            "model_name": ModelRegistry.MODELS[app.config['ACTIVE_MODEL']],
            "index_size": app.index_service.get_total(),
            "index_health": index_health["status"],
            "queue_length": app.queue_service.get_queue_size(),
            "rabbitmq": rabbitmq_health,
            "auth_system": "active" if hasattr(app, 'auth_service') else "inactive"
        }

    @app.teardown_appcontext
    def shutdown_app(exception=None):
        if hasattr(app, 'rabbitmq_pool'):
            app.rabbitmq_pool.close_all()

        if hasattr(app, 'file_processor_supervisor'):
            app.file_processor_supervisor.stop()

        if hasattr(app, 'index_health_monitor'):
            app.index_health_monitor.stop_monitoring()

        # Clean up expired tokens periodically
        if hasattr(app, 'auth_service'):
            app.auth_service.clean_expired_tokens()

    return app


def setup_services(app):
    """Initialize application services

    Args:
        app: Flask application instance
    """
    # Create embedding service
    app.embedding_service = ModelRegistry.get_embedding_service(
        app.config['ACTIVE_MODEL'],
        app.dask_client
    )

    # Create index service
    index_manager = IndexManager(app.config['FAISS_DIR'])
    app.index_service = index_manager.get_index_service(
        app.config['ACTIVE_MODEL'],
        app.embedding_service.get_embedding_dimension()
    )

    # Create index version manager
    app.index_version_manager = GitIndexVersionManager(app.config)

    # Create index health monitor
    app.index_health_monitor = IndexHealthMonitor(app.config)
    app.index_health_monitor.start_monitoring()

    # Create distributed indexer
    app.distributed_indexer = DaskDistributedIndexer(app.config)

    # Create queue service (legacy)
    queue_file_path = os.path.join(app.config['QUEUES_DIR'], 'processing_queue.pkl')
    app.queue_service = FileProcessingQueueService(queue_file_path)

    # Set up legacy queue processor
    if not hasattr(app, 'queue_processor') or app.queue_processor is None:
        app.queue_processor = QueueProcessor(
            app.queue_service,
            app.embedding_service,
            app.index_service
        )
        app.queue_processor.start()

    # Set up file processor services using RabbitMQ
    if app.rabbitmq_pool:
        # Create task directory if needed
        task_store_dir = os.path.join(app.config['QUEUES_DIR'], 'tasks')
        os.makedirs(task_store_dir, exist_ok=True)

        # Get a RabbitMQ connection from the pool
        broker = app.rabbitmq_pool.get_connection()

        # Create file processor producer
        app.file_processor_producer = FileProcessorProducer(
            broker,
            task_store_dir
        )

        # Create file processor supervisor
        if not hasattr(app, 'file_processor_supervisor') or app.file_processor_supervisor is None:
            app.file_processor_supervisor = SupervisorProcess(
                broker,
                app.embedding_service,
                app.index_service,
                task_store_dir,
                worker_count=3
            )
            app.file_processor_supervisor.start()


# Create a Flask application instance at the module level for Gunicorn
app = create_app()


if __name__ == '__main__':
    # Use the app instance that's already created
    app.run(host='0.0.0.0', port=5000, threaded=True)
