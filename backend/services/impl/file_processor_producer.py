"""
File Processor Producer Implementation

This module provides an implementation of the IFileProcessorProducer interface
for submitting files to a queue for processing.
"""
import os
import json
import uuid
import logging
from typing import Dict, Any, Optional

from interfaces.queue import IFileProcessorProducer
from interfaces.message_broker import IMessageBroker


class FileProcessorProducerImpl(IFileProcessorProducer):
    """Implementation of the file processor producer interface"""

    def __init__(self, message_broker: IMessageBroker, task_store_dir: str):
        """Initialize the file processor producer

        Args:
            message_broker: The message broker for sending messages
            task_store_dir: Directory to store task information
        """
        self.message_broker = message_broker
        self.task_store_dir = task_store_dir
        self.logger = logging.getLogger(__name__)

        # Ensure the task store directory exists
        os.makedirs(self.task_store_dir, exist_ok=True)

        # Queue name for file processing tasks
        self.queue_name = 'file_processing'

        # Ensure the queue exists
        try:
            self.message_broker.declare_queue(
                queue_name=self.queue_name,
                durable=True
            )
        except Exception as e:
            self.logger.error(f"Failed to declare queue {self.queue_name}: {e}")

    def submit_file(self, file_path: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Submit a file for processing

        Args:
            file_path: The path to the file
            metadata: Optional metadata about the file

        Returns:
            The task ID
        """
        try:
            # Generate a unique task ID
            task_id = str(uuid.uuid4())

            # Create task data
            task_data = {
                'task_id': task_id,
                'file_path': file_path,
                'status': 'queued',
                'metadata': metadata or {}
            }

            # Save task data to disk for persistence
            self._save_task_data(task_id, task_data)

            # Send message to queue
            message = {
                'task_id': task_id,
                'file_path': file_path,
                'metadata': metadata or {}
            }

            success = self.message_broker.publish_message(
                exchange='',  # Default exchange
                routing_key=self.queue_name,
                message=message,
                properties={
                    'delivery_mode': 2  # Make message persistent
                }
            )

            if not success:
                self.logger.error(f"Failed to publish message for task {task_id}")
                # Update task status
                task_data['status'] = 'failed'
                task_data['error'] = 'Failed to publish message to queue'
                self._save_task_data(task_id, task_data)

            self.logger.info(f"Submitted file {file_path} for processing as task {task_id}")
            return task_id

        except Exception as e:
            self.logger.error(f"Error submitting file {file_path}: {e}")
            raise

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get the status of a task

        Args:
            task_id: The ID of the task

        Returns:
            Task status information
        """
        try:
            # Load task data from disk
            task_data = self._load_task_data(task_id)
            if not task_data:
                return {
                    'task_id': task_id,
                    'status': 'not_found'
                }

            return task_data

        except Exception as e:
            self.logger.error(f"Error getting status for task {task_id}: {e}")
            return {
                'task_id': task_id,
                'status': 'error',
                'error': str(e)
            }

    def _save_task_data(self, task_id: str, task_data: Dict[str, Any]) -> None:
        """Save task data to disk

        Args:
            task_id: The ID of the task
            task_data: The task data to save
        """
        try:
            task_file = os.path.join(self.task_store_dir, f"{task_id}.json")
            with open(task_file, 'w') as f:
                json.dump(task_data, f)
        except Exception as e:
            self.logger.error(f"Error saving task data for {task_id}: {e}")

    def _load_task_data(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Load task data from disk

        Args:
            task_id: The ID of the task

        Returns:
            The task data or None if not found
        """
        try:
            task_file = os.path.join(self.task_store_dir, f"{task_id}.json")
            if not os.path.exists(task_file):
                return None

            with open(task_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading task data for {task_id}: {e}")
            return None
