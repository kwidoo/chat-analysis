"""
Queue Service Interfaces

This module defines interfaces for queue-related services,
implementing the Interface Segregation Principle (I in SOLID).
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional


class IQueueService(ABC):
    """Interface for file processing queue operations"""

    @abstractmethod
    def add_task(self, file_path: str, task_id: str) -> bool:
        """Add a file processing task to the queue

        Args:
            file_path: The path to the file
            task_id: The ID of the task

        Returns:
            True if the task was added successfully, False otherwise
        """
        pass

    @abstractmethod
    def get_next_task(self) -> Optional[Dict[str, Any]]:
        """Get the next task from the queue

        Returns:
            Task information or None if the queue is empty
        """
        pass

    @abstractmethod
    def mark_complete(self, task_id: str, file_path: str, success: bool = True) -> None:
        """Mark a task as complete

        Args:
            task_id: The ID of the task
            file_path: The path to the file
            success: Whether the processing was successful
        """
        pass

    @abstractmethod
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get the status of a task

        Args:
            task_id: The ID of the task

        Returns:
            Task status information
        """
        pass

    @abstractmethod
    def get_all_tasks(self, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all tasks in the queue

        Args:
            status_filter: Optional filter for task status (pending, completed, failed)

        Returns:
            List of task information dictionaries
        """
        pass

    @abstractmethod
    def save_queue(self) -> None:
        """Save the queue to persistent storage"""
        pass

    @abstractmethod
    def get_queue_size(self) -> int:
        """Get the number of pending tasks in the queue

        Returns:
            The number of pending tasks
        """
        pass


class IFileProcessorProducer(ABC):
    """Interface for file processor producer operations"""

    @abstractmethod
    def submit_file(self, file_path: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Submit a file for processing

        Args:
            file_path: The path to the file
            metadata: Optional metadata about the file

        Returns:
            The task ID
        """
        pass

    @abstractmethod
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get the status of a task

        Args:
            task_id: The ID of the task

        Returns:
            Task status information
        """
        pass


class IFileProcessorConsumer(ABC):
    """Interface for file processor consumer operations"""

    @abstractmethod
    def start(self) -> None:
        """Start processing files from the queue"""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop processing files from the queue"""
        pass

    @abstractmethod
    def process_file(self, file_path: str, task_id: str) -> bool:
        """Process a file

        Args:
            file_path: The path to the file
            task_id: The ID of the task

        Returns:
            True if processing was successful, False otherwise
        """
        pass
