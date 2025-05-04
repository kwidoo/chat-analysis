import os
import json
import logging
import threading
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
import traceback

from services.message_broker import MessageBrokerInterface
from services.embedding_service import EmbeddingServiceInterface
from services.index_service import IndexServiceInterface
from services.file_processor_producer import TASK_TRACKING_QUEUE, FILE_PROCESSING_QUEUE

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Circuit breaker pattern implementation for error handling"""

    def __init__(self, failure_threshold: int = 5, reset_timeout: int = 60):
        """Initialize the circuit breaker

        Args:
            failure_threshold: Number of failures before opening the circuit
            reset_timeout: Time in seconds before attempting to close the circuit
        """
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.state = "CLOSED"
        self.last_failure_time = None
        self._lock = threading.RLock()

    def execute(self, func: Callable, *args, **kwargs):
        """Execute a function with circuit breaker protection

        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Result of the function or raises an exception

        Raises:
            CircuitBreakerOpenError: If the circuit is open
            Exception: Any exception raised by the function
        """
        with self._lock:
            if self.state == "OPEN":
                # Check if reset timeout has elapsed
                if self.last_failure_time and time.time() - self.last_failure_time >= self.reset_timeout:
                    logger.info("Circuit breaker reset timeout elapsed, moving to half-open state")
                    self.state = "HALF-OPEN"
                else:
                    raise CircuitBreakerOpenError("Circuit breaker is open")

            try:
                result = func(*args, **kwargs)

                # If successful and in half-open state, close the circuit
                if self.state == "HALF-OPEN":
                    logger.info("Circuit breaker operation successful, closing circuit")
                    self.state = "CLOSED"
                    self.failure_count = 0

                return result

            except Exception as e:
                self.last_failure_time = time.time()
                self.failure_count += 1

                if self.failure_count >= self.failure_threshold:
                    logger.warning(f"Circuit breaker threshold reached ({self.failure_count} failures), opening circuit")
                    self.state = "OPEN"

                raise e


class CircuitBreakerOpenError(Exception):
    """Exception raised when the circuit breaker is open"""
    pass


class RetryPolicy:
    """Retry policy for handling transient failures"""

    def __init__(self, max_retries: int = 3, retry_delay: int = 5,
                 backoff_factor: float = 1.5, max_delay: int = 60):
        """Initialize the retry policy

        Args:
            max_retries: Maximum number of retries
            retry_delay: Initial delay between retries in seconds
            backoff_factor: Factor to increase delay by after each retry
            max_delay: Maximum delay between retries in seconds
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.backoff_factor = backoff_factor
        self.max_delay = max_delay

    def execute(self, func: Callable, *args, **kwargs):
        """Execute a function with retry policy

        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Result of the function or raises an exception

        Raises:
            Exception: After max retries or non-retryable exception
        """
        retries = 0
        delay = self.retry_delay

        while True:
            try:
                return func(*args, **kwargs)
            except CircuitBreakerOpenError:
                # Don't retry if circuit breaker is open
                raise
            except Exception as e:
                retries += 1

                # Check if we should retry
                if retries > self.max_retries:
                    logger.error(f"Max retries ({self.max_retries}) exceeded: {e}")
                    raise

                logger.warning(f"Retry {retries}/{self.max_retries} after error: {e}. Waiting {delay}s")
                time.sleep(delay)

                # Increase delay for next retry
                delay = min(delay * self.backoff_factor, self.max_delay)


class FileProcessorConsumer:
    """Consumer service for file processing tasks

    This service consumes file processing tasks from the queue and processes them.
    """

    def __init__(self, broker: MessageBrokerInterface,
                 embedding_service: EmbeddingServiceInterface,
                 index_service: IndexServiceInterface,
                 task_store_dir: str,
                 prefetch: int = 1):
        """Initialize the file processor consumer

        Args:
            broker: Message broker for queue operations
            embedding_service: Service for generating embeddings
            index_service: Service for storing embeddings
            task_store_dir: Directory to store task status
            prefetch: Number of messages to prefetch
        """
        self.broker = broker
        self.embedding_service = embedding_service
        self.index_service = index_service
        self.task_store_dir = task_store_dir
        self.prefetch = prefetch
        self.circuit_breaker = CircuitBreaker()
        self.retry_policy = RetryPolicy()
        self.running = False
        self.thread = None

        os.makedirs(task_store_dir, exist_ok=True)

    def start(self) -> None:
        """Start the consumer thread"""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._consume_tasks)
        self.thread.daemon = True
        self.thread.start()
        logger.info("File processor consumer started")

    def stop(self) -> None:
        """Stop the consumer thread"""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5.0)
        logger.info("File processor consumer stopped")

    def _consume_tasks(self) -> None:
        """Start consuming tasks from the queue"""
        try:
            self.broker.consume(FILE_PROCESSING_QUEUE, self._process_task, self.prefetch)
        except Exception as e:
            logger.error(f"Error in consumer: {e}")
            self.running = False

    def _process_task(self, message: Dict[str, Any]) -> None:
        """Process a task from the queue

        Args:
            message: Task message from the queue
        """
        task_id = message.get("task_id")
        if not task_id:
            logger.error("Received task without task_id")
            return

        # Update task status to processing
        self._update_task_status(task_id, "processing")

        try:
            # Extract data from message
            file_path = message.get("file_path")
            file_content = message.get("file_content")
            metadata = message.get("metadata", {})

            if not file_path or not file_content:
                raise ValueError("Missing file path or content in message")

            # Process the file with circuit breaker and retry protection
            self.retry_policy.execute(
                self.circuit_breaker.execute,
                self._extract_and_index_embeddings,
                file_path, file_content, metadata
            )

            # Update task status to completed
            self._update_task_status(task_id, "completed", {
                "processing_time": datetime.now().isoformat(),
                "success": True
            })

        except Exception as e:
            logger.error(f"Error processing task {task_id}: {e}\n{traceback.format_exc()}")

            # Update task status to failed
            self._update_task_status(task_id, "failed", {
                "error": str(e),
                "traceback": traceback.format_exc()
            })

    def _extract_and_index_embeddings(self, file_path: str, file_content: str, metadata: Dict[str, Any]) -> None:
        """Extract and index embeddings from a file

        Args:
            file_path: Path to the file
            file_content: Content of the file
            metadata: Additional metadata about the file
        """
        # Parse content based on file type
        file_ext = os.path.splitext(file_path)[1].lower()

        messages = []
        try:
            if file_ext == '.json':
                # Parse JSON file
                data = json.loads(file_content)

                # Extract messages from JSON
                if "messages" in data:
                    messages = [msg.get('content', '') for msg in data["messages"] if 'content' in msg]
                elif "text" in data:
                    messages = [data["text"]]
            else:
                # Treat as plain text
                messages = [file_content]
        except json.JSONDecodeError:
            # If JSON parsing fails, treat as plain text
            messages = [file_content]

        if not messages:
            raise ValueError(f"No messages found in file: {file_path}")

        # Generate embeddings
        embeddings = self.embedding_service.encode(messages)

        # Add to index
        self.index_service.add_embeddings(embeddings)

    def _update_task_status(self, task_id: str, status: str, metadata: Dict[str, Any] = None) -> None:
        """Update task status

        Args:
            task_id: ID of the task
            status: New status of the task
            metadata: Additional metadata to include
        """
        try:
            # Get current task status
            task_file = os.path.join(self.task_store_dir, f"{task_id}.json")
            current_status = {}

            if os.path.exists(task_file):
                with open(task_file, 'r') as f:
                    current_status = json.load(f)
            else:
                current_status = {
                    "task_id": task_id,
                    "created_at": datetime.now().isoformat()
                }

            # Update status and metadata
            current_status["status"] = status
            current_status["updated_at"] = datetime.now().isoformat()

            if metadata:
                if "metadata" not in current_status:
                    current_status["metadata"] = {}
                current_status["metadata"].update(metadata)

            # Save updated status
            with open(task_file, 'w') as f:
                json.dump(current_status, f, indent=2)

            # Publish status update to tracking queue
            self.broker.publish(TASK_TRACKING_QUEUE, {
                "task_id": task_id,
                "status": status,
                "updated_at": current_status["updated_at"],
                "metadata": metadata or {}
            })

        except Exception as e:
            logger.error(f"Error updating task status for {task_id}: {e}")


class SupervisorProcess:
    """Supervisor process for managing consumer workers"""

    def __init__(self, broker: MessageBrokerInterface,
                 embedding_service: EmbeddingServiceInterface,
                 index_service: IndexServiceInterface,
                 task_store_dir: str,
                 worker_count: int = 3):
        """Initialize the supervisor process

        Args:
            broker: Message broker for queue operations
            embedding_service: Service for generating embeddings
            index_service: Service for storing embeddings
            task_store_dir: Directory to store task status
            worker_count: Number of worker processes to run
        """
        self.broker = broker
        self.embedding_service = embedding_service
        self.index_service = index_service
        self.task_store_dir = task_store_dir
        self.worker_count = worker_count
        self.workers = []
        self.running = False
        self.monitor_thread = None

    def start(self) -> None:
        """Start the supervisor and worker processes"""
        if self.running:
            return

        self.running = True

        # Start worker processes
        for i in range(self.worker_count):
            worker = FileProcessorConsumer(
                self.broker,
                self.embedding_service,
                self.index_service,
                self.task_store_dir
            )
            worker.start()
            self.workers.append(worker)

        # Start monitor thread
        self.monitor_thread = threading.Thread(target=self._monitor_workers)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

        logger.info(f"Supervisor started with {self.worker_count} workers")

    def stop(self) -> None:
        """Stop the supervisor and worker processes"""
        self.running = False

        # Stop all workers
        for worker in self.workers:
            worker.stop()

        # Wait for monitor thread
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5.0)

        logger.info("Supervisor stopped")

    def _monitor_workers(self) -> None:
        """Monitor worker processes and restart any that have failed"""
        while self.running:
            for i, worker in enumerate(self.workers):
                if worker.thread is None or not worker.thread.is_alive():
                    logger.warning(f"Worker {i} is not running, restarting")

                    # Create a new worker
                    new_worker = FileProcessorConsumer(
                        self.broker,
                        self.embedding_service,
                        self.index_service,
                        self.task_store_dir
                    )
                    new_worker.start()

                    # Replace the failed worker
                    self.workers[i] = new_worker

            # Sleep for a while before checking again
            time.sleep(30)
