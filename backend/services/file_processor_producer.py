import json
import os
import hashlib
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from services.message_broker import MessageBrokerInterface, RabbitMQBroker

logger = logging.getLogger(__name__)

# Constants
FILE_PROCESSING_QUEUE = "file_processing"
TASK_TRACKING_QUEUE = "task_tracking"


class FileProcessorProducer:
    """Producer service for file processing tasks

    This service is responsible for submitting file processing tasks to the queue
    in an idempotent manner with task status tracking.
    """

    def __init__(self, broker: MessageBrokerInterface, task_store_dir: str):
        """Initialize the file processor producer

        Args:
            broker: Message broker for queue operations
            task_store_dir: Directory to store task status
        """
        self.broker = broker
        self.task_store_dir = task_store_dir
        os.makedirs(task_store_dir, exist_ok=True)

    def submit_file(self, file_path: str, file_content: bytes, metadata: Dict[str, Any] = None) -> str:
        """Submit a file for processing

        Args:
            file_path: Path to the file
            file_content: Content of the file
            metadata: Additional metadata about the file

        Returns:
            Task ID for tracking the task
        """
        # Generate a unique task ID based on file content and metadata
        task_id = self._generate_task_id(file_path, file_content, metadata)

        # Check if the task already exists
        if self._task_exists(task_id):
            logger.info(f"Task {task_id} already exists, returning existing task ID")
            return task_id

        # Create task message
        task = {
            "task_id": task_id,
            "file_path": file_path,
            "file_content_hash": self._hash_content(file_content),
            "file_size": len(file_content),
            "file_type": os.path.splitext(file_path)[1],
            "submitted_at": datetime.now().isoformat(),
            "status": "submitted",
            "metadata": metadata or {}
        }

        # Store initial task status
        self._store_task_status(task_id, task)

        # Submit task to processing queue
        try:
            self.broker.publish(FILE_PROCESSING_QUEUE, {
                "task_id": task_id,
                "file_path": file_path,
                "file_content": file_content.decode('utf-8') if isinstance(file_content, bytes) else file_content,
                "metadata": metadata or {}
            })

            # Update task status to queued
            task["status"] = "queued"
            self._store_task_status(task_id, task)

            # Publish task status update
            self.broker.publish(TASK_TRACKING_QUEUE, {
                "task_id": task_id,
                "status": "queued",
                "updated_at": datetime.now().isoformat()
            })

            logger.info(f"Task {task_id} submitted to queue")

        except Exception as e:
            # Update task status to failed
            task["status"] = "failed"
            task["error"] = str(e)
            self._store_task_status(task_id, task)

            logger.error(f"Failed to submit task {task_id}: {e}")

        return task_id

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get the current status of a task

        Args:
            task_id: ID of the task to check

        Returns:
            Task status data or None if task not found
        """
        task_file = os.path.join(self.task_store_dir, f"{task_id}.json")
        if not os.path.exists(task_file):
            return None

        try:
            with open(task_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading task status for {task_id}: {e}")
            return None

    def update_task_status(self, task_id: str, status: str, metadata: Dict[str, Any] = None) -> bool:
        """Update the status of a task

        Args:
            task_id: ID of the task to update
            status: New status of the task
            metadata: Additional metadata to add to the task

        Returns:
            True if the update was successful, False otherwise
        """
        current_status = self.get_task_status(task_id)
        if not current_status:
            logger.error(f"Cannot update non-existent task {task_id}")
            return False

        # Update the status and metadata
        current_status["status"] = status
        current_status["updated_at"] = datetime.now().isoformat()

        if metadata:
            if "metadata" not in current_status:
                current_status["metadata"] = {}
            current_status["metadata"].update(metadata)

        # Store updated status
        self._store_task_status(task_id, current_status)

        # Publish status update
        try:
            self.broker.publish(TASK_TRACKING_QUEUE, {
                "task_id": task_id,
                "status": status,
                "updated_at": current_status["updated_at"],
                "metadata": metadata or {}
            })
            return True
        except Exception as e:
            logger.error(f"Failed to publish status update for task {task_id}: {e}")
            return False

    def _generate_task_id(self, file_path: str, file_content: bytes, metadata: Dict[str, Any] = None) -> str:
        """Generate a unique task ID based on file content and metadata

        Args:
            file_path: Path to the file
            file_content: Content of the file
            metadata: Additional metadata about the file

        Returns:
            Unique task ID
        """
        content_hash = self._hash_content(file_content)
        metadata_str = json.dumps(metadata or {}, sort_keys=True)
        combined = f"{file_path}:{content_hash}:{metadata_str}"

        # Create a unique, but deterministic ID
        task_hash = hashlib.sha256(combined.encode()).hexdigest()[:16]
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

        return f"{timestamp}-{task_hash}"

    def _hash_content(self, content: bytes) -> str:
        """Create a hash of the file content

        Args:
            content: File content

        Returns:
            Content hash
        """
        if isinstance(content, str):
            content = content.encode('utf-8')
        return hashlib.sha256(content).hexdigest()

    def _task_exists(self, task_id: str) -> bool:
        """Check if a task already exists

        Args:
            task_id: ID of the task to check

        Returns:
            True if the task exists, False otherwise
        """
        task_file = os.path.join(self.task_store_dir, f"{task_id}.json")
        return os.path.exists(task_file)

    def _store_task_status(self, task_id: str, status: Dict[str, Any]) -> None:
        """Store task status to disk

        Args:
            task_id: ID of the task
            status: Task status data
        """
        task_file = os.path.join(self.task_store_dir, f"{task_id}.json")

        try:
            with open(task_file, 'w') as f:
                json.dump(status, f, indent=2)
        except Exception as e:
            logger.error(f"Error storing task status for {task_id}: {e}")

    def list_tasks(self, status: str = None, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """List tasks, optionally filtered by status

        Args:
            status: Filter tasks by status (optional)
            limit: Maximum number of tasks to return
            offset: Number of tasks to skip

        Returns:
            List of task data
        """
        tasks = []

        try:
            files = os.listdir(self.task_store_dir)
            task_files = [f for f in files if f.endswith('.json')]

            # Apply pagination
            paginated_files = task_files[offset:offset+limit]

            for file_name in paginated_files:
                task_id = file_name.replace('.json', '')
                task_data = self.get_task_status(task_id)

                if task_data and (status is None or task_data.get("status") == status):
                    tasks.append(task_data)

        except Exception as e:
            logger.error(f"Error listing tasks: {e}")

        return tasks
