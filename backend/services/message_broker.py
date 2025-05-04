import pika
import json
import time
import threading
import logging
from typing import Dict, List, Any, Callable, Optional
from abc import ABC, abstractmethod


logger = logging.getLogger(__name__)


class MessageBrokerInterface(ABC):
    """Interface for message broker implementations"""

    @abstractmethod
    def publish(self, queue_name: str, message: Dict[str, Any], persistent: bool = True) -> None:
        """Publish a message to a queue

        Args:
            queue_name: Name of the queue to publish to
            message: Message to publish (will be serialized to JSON)
            persistent: Whether the message should persist through broker restarts
        """
        pass

    @abstractmethod
    def consume(self, queue_name: str, callback: Callable[[Dict[str, Any]], None], prefetch: int = 1) -> None:
        """Start consuming messages from a queue

        Args:
            queue_name: Name of the queue to consume from
            callback: Function to call for each message
            prefetch: Number of messages to prefetch
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """Close the connection to the message broker"""
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Check if the connection to the message broker is healthy

        Returns:
            True if the connection is healthy, False otherwise
        """
        pass

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if there is an active connection to the message broker

        Returns:
            True if connected, False otherwise
        """
        pass


class RabbitMQBroker(MessageBrokerInterface):
    """Implementation of MessageBrokerInterface using RabbitMQ"""

    def __init__(self, host: str = 'localhost', port: int = 5672,
                 user: str = 'guest', password: str = 'guest',
                 virtual_host: str = '/', connection_attempts: int = 5,
                 retry_delay: int = 5):
        """Initialize RabbitMQ connection

        Args:
            host: RabbitMQ host
            port: RabbitMQ port
            user: RabbitMQ username
            password: RabbitMQ password
            virtual_host: RabbitMQ virtual host
            connection_attempts: Number of connection attempts
            retry_delay: Delay between connection attempts in seconds
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.virtual_host = virtual_host
        self.connection_attempts = connection_attempts
        self.retry_delay = retry_delay

        self._connection = None
        self._channel = None
        self._consuming = False
        self._connection_lock = threading.Lock()
        self._connect()

    def _connect(self) -> bool:
        """Establish a connection to RabbitMQ

        Returns:
            True if connection successful, False otherwise
        """
        with self._connection_lock:
            if self._connection and self._connection.is_open:
                return True

            # Close existing connection if it exists
            self._close_connection()

            # Connection parameters
            credentials = pika.PlainCredentials(self.user, self.password)
            parameters = pika.ConnectionParameters(
                host=self.host,
                port=self.port,
                virtual_host=self.virtual_host,
                credentials=credentials,
                connection_attempts=self.connection_attempts,
                retry_delay=self.retry_delay
            )

            try:
                self._connection = pika.BlockingConnection(parameters)
                self._channel = self._connection.channel()
                return True
            except Exception as e:
                logger.error(f"Failed to connect to RabbitMQ: {e}")
                self._connection = None
                self._channel = None
                return False

    def _ensure_connection(self) -> bool:
        """Ensure that there is an active connection to RabbitMQ

        Returns:
            True if connection is active, False otherwise
        """
        if self.is_connected:
            return True
        return self._connect()

    def _close_connection(self) -> None:
        """Close the RabbitMQ connection"""
        if self._connection and self._connection.is_open:
            try:
                self._connection.close()
            except:
                pass
        self._connection = None
        self._channel = None

    def publish(self, queue_name: str, message: Dict[str, Any], persistent: bool = True) -> None:
        """Publish a message to a queue

        Args:
            queue_name: Name of the queue to publish to
            message: Message to publish (will be serialized to JSON)
            persistent: Whether the message should persist through broker restarts
        """
        if not self._ensure_connection():
            raise ConnectionError("Could not connect to RabbitMQ")

        # Ensure queue exists
        self._channel.queue_declare(queue=queue_name, durable=True)

        # Set message properties
        properties = pika.BasicProperties(
            delivery_mode=2 if persistent else 1,  # Make message persistent
            content_type='application/json'
        )

        # Publish message
        self._channel.basic_publish(
            exchange='',
            routing_key=queue_name,
            body=json.dumps(message),
            properties=properties
        )

    def consume(self, queue_name: str, callback: Callable[[Dict[str, Any]], None], prefetch: int = 1) -> None:
        """Start consuming messages from a queue

        Args:
            queue_name: Name of the queue to consume from
            callback: Function to call for each message
            prefetch: Number of messages to prefetch
        """
        if not self._ensure_connection():
            raise ConnectionError("Could not connect to RabbitMQ")

        # Ensure queue exists
        self._channel.queue_declare(queue=queue_name, durable=True)

        # Set prefetch count
        self._channel.basic_qos(prefetch_count=prefetch)

        # Create a wrapper for the callback to handle JSON parsing
        def on_message_callback(ch, method, properties, body):
            try:
                message = json.loads(body)
                callback(message)
                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                # Reject the message and requeue it
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

        # Start consuming
        self._channel.basic_consume(
            queue=queue_name,
            on_message_callback=on_message_callback,
            auto_ack=False
        )

        self._consuming = True

        # Start blocking consumer
        try:
            self._channel.start_consuming()
        except Exception as e:
            logger.error(f"Error in consumer: {e}")
            self._consuming = False
            raise

    def close(self) -> None:
        """Close the connection to RabbitMQ"""
        if self._consuming:
            try:
                self._channel.stop_consuming()
            except:
                pass
            self._consuming = False

        self._close_connection()

    def health_check(self) -> bool:
        """Check if the connection to RabbitMQ is healthy

        Returns:
            True if the connection is healthy, False otherwise
        """
        return self.is_connected

    @property
    def is_connected(self) -> bool:
        """Check if there is an active connection to RabbitMQ

        Returns:
            True if connected, False otherwise
        """
        return (self._connection is not None and
                self._connection.is_open and
                self._channel is not None and
                self._channel.is_open)


class RabbitMQConnectionPool:
    """Connection pool for RabbitMQ connections"""

    def __init__(self, max_connections: int = 10, **connection_params):
        """Initialize the connection pool

        Args:
            max_connections: Maximum number of connections in the pool
            connection_params: Parameters to pass to RabbitMQBroker
        """
        self.max_connections = max_connections
        self.connection_params = connection_params
        self.pool = []
        self.lock = threading.Lock()

    def get_connection(self) -> RabbitMQBroker:
        """Get a connection from the pool or create a new one

        Returns:
            A RabbitMQBroker instance
        """
        with self.lock:
            # Try to find an available connection
            for connection in self.pool:
                if connection.is_connected:
                    return connection

            # If we have reached the maximum number of connections, close the oldest one
            if len(self.pool) >= self.max_connections:
                old_connection = self.pool.pop(0)
                old_connection.close()

            # Create a new connection
            new_connection = RabbitMQBroker(**self.connection_params)
            self.pool.append(new_connection)
            return new_connection

    def close_all(self) -> None:
        """Close all connections in the pool"""
        with self.lock:
            for connection in self.pool:
                connection.close()
            self.pool = []

    def health_check(self) -> Dict[str, Any]:
        """Check the health of all connections in the pool

        Returns:
            A dictionary with health statistics
        """
        with self.lock:
            total = len(self.pool)
            active = sum(1 for conn in self.pool if conn.is_connected)

            return {
                "total_connections": total,
                "active_connections": active,
                "connection_pool_utilization": active / max(1, self.max_connections)
            }
