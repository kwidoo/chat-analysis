"""
Dependency Injection Container

This module implements the Dependency Inversion Principle (D in SOLID)
by providing a container that manages service dependencies and their lifecycles.
"""

import logging
import os
from typing import Type  # Only import what's needed

from interfaces.auth import IAuthService, IMFAService, ITokenService, IUserService
from interfaces.embedding import IEmbeddingService
from interfaces.index import IIndexService
from interfaces.message_broker import IMessageBroker
from interfaces.queue import IFileProcessorConsumer, IFileProcessorProducer, IQueueService
from services.default_auth_service import AuthServiceImpl
from services.default_embedding_service import ModelRegistry
from services.default_message_broker import RabbitMQConnectionPool
from services.default_mfa_service import TOTPMFAServiceImpl
from services.default_user_service import UserServiceImpl
from services.file_processor_consumer import SupervisorProcessImpl
from services.file_processor_producer import FileProcessorProducerImpl
from services.token_service import JWTTokenServiceImpl


class DIContainer:
    """Dependency Injection Container for service management"""

    def __init__(self, app=None):
        """Initialize the DI container

        Args:
            app: Optional Flask application instance
        """
        self.app = app
        self.logger = logging.getLogger(__name__)

        # Service registry for singletons
        self._services = {}

    def setup_services(self) -> None:
        """Initialize and configure all application services"""
        self.logger.info("Setting up application services")

        # Set up auth services
        self._setup_auth_services()

        # Set up message broker
        self._setup_message_broker()

        # Set up file processing services
        self._setup_file_processing_services()

        # Set up embedding service
        self._setup_embedding_service()

        # Set up index service
        self._setup_index_services()

        self.logger.info("All services have been set up")

    def _setup_auth_services(self) -> None:
        """Set up authentication-related services"""
        # Configuration
        secret_key = self.app.config.get("SECRET_KEY", "default-secret-key")
        token_expiry = self.app.config.get("ACCESS_TOKEN_EXPIRY", 3600)
        refresh_expiry = self.app.config.get("REFRESH_TOKEN_EXPIRY", 604800)

        # Create token service
        token_service = JWTTokenServiceImpl(
            secret_key=secret_key,
            token_expiry=token_expiry,
            refresh_expiry=refresh_expiry,
        )
        self._services[ITokenService] = token_service

        # Create MFA service
        mfa_service = TOTPMFAServiceImpl(
            issuer_name=self.app.config.get("APP_NAME", "AI3 Application")
        )
        self._services[IMFAService] = mfa_service

        # Create user service
        user_service = UserServiceImpl(token_service=token_service, mfa_service=mfa_service)
        self._services[IUserService] = user_service

        # Create composite auth service
        auth_service = AuthServiceImpl(
            user_service=user_service,
            token_service=token_service,
            mfa_service=mfa_service,
        )
        self._services[IAuthService] = auth_service

        self.logger.info("Auth services have been set up")

    def _setup_message_broker(self) -> None:
        """Set up message broker service"""
        # Configuration
        host = self.app.config.get("RABBITMQ_HOST", "localhost")
        port = self.app.config.get("RABBITMQ_PORT", 5672)
        user = self.app.config.get("RABBITMQ_USER", "guest")
        password = self.app.config.get("RABBITMQ_PASSWORD", "guest")

        # Create message broker
        message_broker = RabbitMQConnectionPool(host=host, port=port, user=user, password=password)
        self._services[IMessageBroker] = message_broker

        self.logger.info(f"Message broker set up with host: {host}")

    def _setup_file_processing_services(self) -> None:
        """Set up file processing services"""
        # Get dependencies
        message_broker = self.get_service(IMessageBroker)

        # Configuration
        task_store_dir = self.app.config.get(
            "TASK_STORE_DIR",
            os.path.join(os.path.dirname(self.app.instance_path), "queues/tasks"),
        )

        # Create file processor producer
        file_processor_producer = FileProcessorProducerImpl(
            message_broker=message_broker, task_store_dir=task_store_dir
        )
        self._services[IFileProcessorProducer] = file_processor_producer

        # Consumer will be created on demand when needed

        self.logger.info("File processing services have been set up")

    def _setup_embedding_service(self) -> None:
        """Set up embedding service"""
        # Get the default model version from config
        default_model = self.app.config.get("DEFAULT_MODEL", "v2")

        # Create embedding service
        embedding_service = ModelRegistry.get_embedding_service(default_model)
        self._services[IEmbeddingService] = embedding_service

        self.logger.info(f"Embedding service set up with model: {default_model}")

    def _setup_index_services(self) -> None:
        """Set up index services"""
        # These would be added as they're implemented
        # self._services[IIndexService] = ...
        # self._services[IIndexHealthMonitorService] = ...
        # self._services[IIndexVersionManager] = ...
        pass

    def get_service(self, service_type):
        """Get a service by its interface

        Args:
            service_type: The interface of the service to get

        Returns:
            The service instance if found, None otherwise
        """
        return self._services.get(service_type)

    # Convenience methods for common services

    def get_auth_service(self) -> IAuthService:
        """Get the auth service

        Returns:
            The auth service
        """
        return self.get_service(IAuthService)

    def get_embedding_service(self) -> IEmbeddingService:
        """Get the embedding service

        Returns:
            The embedding service
        """
        return self.get_service(IEmbeddingService)

    def get_index_service(self) -> IIndexService:
        """Get the index service

        Returns:
            The index service
        """
        return self.get_service(IIndexService)

    def get_queue_service(self) -> IQueueService:
        """Get the queue service

        Returns:
            The queue service
        """
        return self.get_service(IQueueService)

    def get_file_processor_producer(self) -> IFileProcessorProducer:
        """Get the file processor producer

        Returns:
            The file processor producer
        """
        return self.get_service(IFileProcessorProducer)

    def get_file_processor_consumer(self) -> IFileProcessorConsumer:
        """Get the file processor consumer

        Returns:
            The file processor consumer
        """
        consumer = self.get_service(IFileProcessorConsumer)

        # Create on demand if not available
        if not consumer:
            message_broker = self.get_service(IMessageBroker)
            embedding_service = self.get_service(IEmbeddingService)
            index_service = self.get_service(IIndexService)

            if message_broker and embedding_service and index_service:
                task_store_dir = self.app.config.get(
                    "TASK_STORE_DIR",
                    os.path.join(os.path.dirname(self.app.instance_path), "queues/tasks"),
                )

                consumer = SupervisorProcessImpl(
                    message_broker=message_broker,
                    embedding_service=embedding_service,
                    index_service=index_service,
                    task_store_dir=task_store_dir,
                )

                self._services[IFileProcessorConsumer] = consumer

        return consumer
