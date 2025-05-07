import os
import pickle
import queue
import threading
from typing import Any, Dict, Optional

from services.interfaces import QueueServiceInterface


class FileProcessingQueueService(QueueServiceInterface):
    def __init__(self, queue_file_path: str):
        """Initialize the queue service

        Args:
            queue_file_path: Path to save the queue state
        """
        self.queue = queue.Queue()
        self.queue_file_path = queue_file_path
        self.lock = threading.Lock()
        self.status = {"total": 0, "processed": 0, "failed": 0}

        # Try to load the existing queue if the file exists
        if os.path.exists(queue_file_path):
            try:
                with open(queue_file_path, "rb") as f:
                    pending_items = pickle.load(f)
                    for item in pending_items:
                        self.queue.put(item)
            except Exception as e:
                print(f"Error loading queue: {e}")

    def add_task(self, task: Any, task_id: str) -> None:
        """Add a task to the queue

        Args:
            task: Task to add (typically a file)
            task_id: Unique identifier for the task
        """
        with self.lock:
            self.queue.put((task, task_id))
            self.status["total"] += 1
            self.save_queue()

    def get_queue_size(self) -> int:
        """Return the size of the queue"""
        return self.queue.qsize()

    def save_queue(self) -> None:
        """Save the queue state to disk"""
        try:
            with self.lock:
                pending_items = list(self.queue.queue)
                os.makedirs(os.path.dirname(self.queue_file_path), exist_ok=True)
                with open(self.queue_file_path, "wb") as f:
                    pickle.dump(pending_items, f)
        except Exception as e:
            print(f"Error saving queue: {e}")

    def get_queue_status(self) -> Dict[str, int]:
        """Return the queue statistics"""
        with self.lock:
            return self.status.copy()

    def update_queue_status(self, status_key: str, increment: int = 1) -> None:
        """Update queue statistics

        Args:
            status_key: Key to update (e.g., "processed", "failed")
            increment: Value to add to the status counter
        """
        with self.lock:
            if status_key in self.status:
                self.status[status_key] += increment

    def get_task(self, block: bool = True, timeout: float = None) -> Optional[tuple]:
        """Get a task from the queue

        Args:
            block: Whether to block until a task is available
            timeout: Timeout for blocking

        Returns:
            Tuple of (task, task_id) or None if queue is empty
        """
        try:
            return self.queue.get(block=block, timeout=timeout)
        except queue.Empty:
            return None

    def task_done(self) -> None:
        """Mark a task as complete"""
        self.queue.task_done()
