"""
Message Broker Implementation

This module provides an implementation of the IMessageBroker interface
using RabbitMQ for message queuing, supporting the Dependency Inversion Principle.
"""
import logging
import json
import pika
from typing import Dict, Any, List, Optional, Callable
from pika.adapters.blocking_connection import BlockingChannel

from interfaces.message_broker import IMessageBroker


class RabbitMQConnectionPool(IMessageBroker):
    """RabbitMQ implementation of the message broker interface using a connection pool"""

    def __init__(self,
                 host: str = 'localhost',
                 port: int = 5672,
                 user: str = 'guest',
                 password: str = 'guest',
                 virtual_host: str = '/',
                 connection_attempts: int = 3,
                 retry_delay: int = 5,
                 max_connections: int = 10):
        """Initialize the RabbitMQ connection pool

        Args:
            host: RabbitMQ host
            port: RabbitMQ port
            user: RabbitMQ username
            password: RabbitMQ password
            virtual_host: RabbitMQ virtual host
            connection_attempts: Number of connection attempts
            retry_delay: Delay between connection attempts (in seconds)
            max_connections: Maximum number of connections in the pool
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.virtual_host = virtual_host
        self.connection_attempts = connection_attempts
        self.retry_delay = retry_delay
        self.max_connections = max_connections

        self.logger = logging.getLogger(__name__)

        # Connection pool
        self._connections = []
        self._connection_params = pika.ConnectionParameters(
            host=self.host,
            port=self.port,
            virtual_host=self.virtual_host,
            credentials=pika.PlainCredentials(self.user, self.password),
            connection_attempts=self.connection_attempts,
            retry_delay=self.retry_delay
        )

    def get_connection(self) -> Any:
        """Get a connection from the pool or create a new one

        Returns:
            A pika connection
        """
        # Check if there's an available connection in the pool
        if self._connections:
            # Try to get a connection from the pool
            try:
                connection = self._connections.pop()

                # Check if connection is still open
                if connection.is_open:
                    return RabbitMQConnection(connection, self)

                # Close connection if it's broken
                self.logger.warning("Found closed connection in pool, creating new one")
                try:
                    if connection.is_closed:
                        connection.close()
                except:
                    pass
            except Exception as e:
                self.logger.warning(f"Error reusing connection from pool: {e}")

        # Create a new connection if the pool is empty or all connections are broken
        try:
            connection = pika.BlockingConnection(self._connection_params)
            self.logger.debug(f"Created new RabbitMQ connection to {self.host}:{self.port}")
            return RabbitMQConnection(connection, self)
        except Exception as e:
            self.logger.error(f"Failed to create RabbitMQ connection: {e}")
            raise

    def return_connection(self, connection):
        """Return a connection to the pool

        Args:
            connection: The connection to return
        """
        # Only return open connections to the pool
        if len(self._connections) < self.max_connections and connection.is_open:
            self._connections.append(connection)
        else:
            # Close the connection if the pool is full or connection is closed
            try:
                if not connection.is_closed:
                    connection.close()
            except:
                pass

    def close_all(self) -> None:
        """Close all connections in the pool"""
        for connection in self._connections:
            try:
                if not connection.is_closed:
                    connection.close()
            except Exception as e:
                self.logger.warning(f"Error closing connection: {e}")

        self._connections = []
        self.logger.info("Closed all RabbitMQ connections in pool")

    def health_check(self) -> bool:
        """Check if RabbitMQ is healthy

        Returns:
            True if RabbitMQ is healthy, False otherwise
        """
        try:
            # Try to create a connection
            connection = self.get_connection()
            # If successful, return it to the pool and return True
            if isinstance(connection, RabbitMQConnection):
                connection.close()
                return True
            return False
        except Exception as e:
            self.logger.warning(f"Health check failed: {e}")
            return False

    def publish_message(self, exchange: str, routing_key: str, message: Dict[str, Any],
                       properties: Optional[Dict[str, Any]] = None) -> bool:
        """Publish a message to RabbitMQ

        Args:
            exchange: The exchange to publish to
            routing_key: The routing key for the message
            message: The message to publish (will be JSON serialized)
            properties: Optional properties for the message

        Returns:
            True if the message was published successfully, False otherwise
        """
        connection = None
        try:
            # Get a connection from the pool
            connection = self.get_connection()

            # Create a channel
            channel = connection.channel()

            # Convert dict to JSON
            message_body = json.dumps(message)

            # Set up properties if provided
            if properties:
                props = pika.BasicProperties(**properties)
            else:
                props = None

            # Publish the message
            channel.basic_publish(
                exchange=exchange,
                routing_key=routing_key,
                body=message_body,
                properties=props
            )

            return True
        except Exception as e:
            self.logger.error(f"Error publishing message: {e}")
            return False
        finally:
            if connection:
                connection.close()

    def declare_queue(self, queue_name: str, durable: bool = True,
                     exclusive: bool = False, auto_delete: bool = False) -> Any:
        """Declare a queue in RabbitMQ

        Args:
            queue_name: The name of the queue
            durable: Whether the queue should survive broker restarts
            exclusive: Whether the queue can only be used by the current connection
            auto_delete: Whether the queue should be deleted when no consumers are connected

        Returns:
            Queue declaration result
        """
        connection = None
        try:
            # Get a connection from the pool
            connection = self.get_connection()

            # Create a channel
            channel = connection.channel()

            # Declare the queue
            result = channel.queue_declare(
                queue=queue_name,
                durable=durable,
                exclusive=exclusive,
                auto_delete=auto_delete
            )

            return result
        except Exception as e:
            self.logger.error(f"Error declaring queue: {e}")
            raise
        finally:
            if connection:
                connection.close()

    def consume(self, queue_name: str, callback: Callable) -> Any:
        """Consume messages from a queue

        Args:
            queue_name: The name of the queue
            callback: The callback to call when a message is received

        Returns:
            Consumer tag
        """
        # This is a simplified implementation - in production, you would want to
        # handle reconnections, channel closures, etc.
        connection = None
        try:
            # Get a connection from the pool
            connection = self.get_connection()

            # Create a channel
            channel = connection.channel()

            # Start consuming
            result = channel.basic_consume(
                queue=queue_name,
                on_message_callback=callback,
                auto_ack=False
            )

            # Start consuming (this is a blocking call)
            channel.start_consuming()

            return result
        except Exception as e:
            self.logger.error(f"Error consuming messages: {e}")
            raise
        finally:
            if connection:
                connection.close()


class RabbitMQConnection:
    """Wrapper around a RabbitMQ connection to handle returning it to the pool"""

    def __init__(self, connection, pool):
        """Initialize the connection wrapper

        Args:
            connection: The pika connection
            pool: The connection pool
        """
        self.connection = connection
        self.pool = pool
        self._channels = []

    def channel(self) -> BlockingChannel:
        """Create a new channel on the connection

        Returns:
            A new channel
        """
        channel = self.connection.channel()
        self._channels.append(channel)
        return channel

    def close(self):
        """Return the connection to the pool"""
        # Close all channels
        for channel in self._channels:
            try:
                if channel.is_open:
                    channel.close()
            except:
                pass

        self._channels = []

        # Return the connection to the pool
        self.pool.return_connection(self.connection)

    @property
    def is_open(self) -> bool:
        """Check if the connection is open

        Returns:
            True if the connection is open, False otherwise
        """
        return self.connection.is_open

    @property
    def is_closed(self) -> bool:
        """Check if the connection is closed

        Returns:
            True if the connection is closed, False otherwise
        """
        return self.connection.is_closed
