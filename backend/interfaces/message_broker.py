"""
Message Broker Interface

This module defines interfaces for message broker operations,
implementing the Interface Segregation Principle (I in SOLID).
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, Dict


class IMessageBroker(ABC):
    """Interface for message broker operations"""

    @abstractmethod
    def get_connection(self) -> Any:
        """Get a connection to the message broker

        Returns:
            A connection object
        """
        pass

    @abstractmethod
    def close_all(self) -> None:
        """Close all connections to the message broker"""
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Check if the message broker is healthy

        Returns:
            True if the message broker is healthy, False otherwise
        """
        pass

    @abstractmethod
    def publish_message(
        self,
        exchange: str,
        routing_key: str,
        message: Dict[str, Any],
        properties: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Publish a message to an exchange

        Args:
            exchange: The exchange to publish to
            routing_key: The routing key for the message
            message: The message to publish
            properties: Optional properties for the message

        Returns:
            True if the message was published successfully, False otherwise
        """
        pass

    @abstractmethod
    def declare_queue(
        self,
        queue_name: str,
        durable: bool = True,
        exclusive: bool = False,
        auto_delete: bool = False,
    ) -> Any:
        """Declare a queue

        Args:
            queue_name: The name of the queue
            durable: Whether the queue should survive broker restarts
            exclusive: Whether the queue can only be used by the current connection
            auto_delete: Whether the queue should be deleted when no consumers are connected

        Returns:
            Queue declaration result
        """
        pass

    @abstractmethod
    def consume(self, queue_name: str, callback: Any) -> Any:
        """Consume messages from a queue

        Args:
            queue_name: The name of the queue
            callback: The callback to call when a message is received

        Returns:
            Consumer tag
        """
        pass
