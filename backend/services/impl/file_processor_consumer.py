"""
File Processor Consumer Implementation

This module provides an implementation of the IFileProcessorConsumer interface
for consuming file processing tasks from a queue.
"""

import os
import json
import time
import logging
import threading
import traceback
from typing import Dict, Any, List

from interfaces.queue import IFileProcessorConsumer
from interfaces.embedding import IEmbeddingService
from interfaces.index import IIndexService
from interfaces.message_broker import IMessageBroker


class SupervisorProcessImpl(IFileProcessorConsumer):
    """Implementation of the file processor consumer interface"""

    def __init__(
        self,
        message_broker: IMessageBroker,
        embedding_service: IEmbeddingService,
        index_service: IIndexService,
        task_store_dir: str,
        worker_count: int = 3,
    ):
        """Initialize the file processor consumer

        Args:
            message_broker: The message broker for receiving messages
            embedding_service: The embedding service for generating embeddings
            index_service: The index service for storing embeddings
            task_store_dir: Directory to store task information
            worker_count: Number of worker threads to use
        """
        self.message_broker = message_broker
        self.embedding_service = embedding_service
        self.index_service = index_service
        self.task_store_dir = task_store_dir
        self.worker_count = worker_count
        self.logger = logging.getLogger(__name__)

        # Ensure the task store directory exists
        os.makedirs(self.task_store_dir, exist_ok=True)

        # Queue name for file processing tasks
        self.queue_name = "file_processing"

        # Worker threads
        self.workers = []
        self.running = False

    def start(self) -> None:
        """Start processing files from the queue"""
        if self.running:
            return

        self.running = True

        # Ensure the queue exists
        try:
            self.message_broker.declare_queue(queue_name=self.queue_name, durable=True)
        except Exception as e:
            self.logger.error(f"Failed to declare queue {self.queue_name}: {e}")
            return

        # Create and start worker threads
        for i in range(self.worker_count):
            worker = threading.Thread(target=self._worker_thread, name=f"FileProcessorWorker-{i}")
            worker.daemon = True  # Thread will exit when main thread exits
            worker.start()
            self.workers.append(worker)

        self.logger.info(f"Started {self.worker_count} file processor workers")

    def stop(self) -> None:
        """Stop processing files from the queue"""
        self.running = False

        # Wait for workers to finish (with timeout)
        for worker in self.workers:
            worker.join(timeout=2.0)

        self.workers = []
        self.logger.info("Stopped all file processor workers")

    def process_file(self, file_path: str, task_id: str) -> bool:
        """Process a file

        Args:
            file_path: The path to the file
            task_id: The ID of the task

        Returns:
            True if processing was successful, False otherwise
        """
        try:
            self.logger.info(f"Processing file {file_path} for task {task_id}")

            # Update task status
            task_data = self._load_task_data(task_id) or {
                "task_id": task_id,
                "file_path": file_path,
                "status": "processing",
            }
            task_data["status"] = "processing"
            self._save_task_data(task_id, task_data)

            # Read the file
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()

            # Generate embedding
            embedding = self.embedding_service.embed_document(text)

            # Store in index
            result = self.index_service.add(embedding, file_path)

            if result:
                # Update task status to complete
                task_data["status"] = "completed"
                task_data["processed_at"] = time.time()
                self._save_task_data(task_id, task_data)
                self.logger.info(f"Successfully processed file {file_path} for task {task_id}")
                return True
            else:
                # Update task status to failed
                task_data["status"] = "failed"
                task_data["error"] = "Failed to add embedding to index"
                self._save_task_data(task_id, task_data)
                self.logger.error(f"Failed to add embedding to index for file {file_path}")
                return False

        except Exception as e:
            # Update task status to failed
            task_data = self._load_task_data(task_id) or {
                "task_id": task_id,
                "file_path": file_path,
            }
            task_data["status"] = "failed"
            task_data["error"] = str(e)
            task_data["traceback"] = traceback.format_exc()
            self._save_task_data(task_id, task_data)

            self.logger.error(f"Error processing file {file_path} for task {task_id}: {e}")
            return False

    def _worker_thread(self) -> None:
        """Worker thread for processing files from the queue"""
        self.logger.info(f"Worker thread {threading.current_thread().name} started")

        while self.running:
            try:
                # Get a connection from the pool
                connection = self.message_broker.get_connection()

                # Create a channel
                channel = connection.channel()

                # Define the callback for handling messages
                def callback(ch, method, properties, body):
                    try:
                        # Parse message
                        message = json.loads(body)
                        task_id = message.get("task_id")
                        file_path = message.get("file_path")

                        if not task_id or not file_path:
                            self.logger.error("Invalid message format")
                            ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
                            return

                        # Process the file
                        success = self.process_file(file_path, task_id)

                        # Acknowledge the message
                        if success:
                            ch.basic_ack(delivery_tag=method.delivery_tag)
                        else:
                            # Reject the message and don't requeue
                            ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)

                    except Exception as e:
                        self.logger.error(f"Error in message callback: {e}")
                        # Reject the message and don't requeue
                        ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)

                # Set prefetch count to 1
                channel.basic_qos(prefetch_count=1)

                # Start consuming
                channel.basic_consume(
                    queue=self.queue_name, on_message_callback=callback, auto_ack=False
                )

                self.logger.info(f"Worker {threading.current_thread().name} waiting for messages")

                # Start consuming (this is a blocking call)
                # Will continue until the channel is closed
                channel.start_consuming()

            except Exception as e:
                self.logger.error(f"Error in worker thread: {e}")

                # Sleep before reconnecting
                time.sleep(5)

        self.logger.info(f"Worker thread {threading.current_thread().name} exiting")

    def _save_task_data(self, task_id: str, task_data: Dict[str, Any]) -> None:
        """Save task data to disk

        Args:
            task_id: The ID of the task
            task_data: The task data to save
        """
        try:
            task_file = os.path.join(self.task_store_dir, f"{task_id}.json")
            with open(task_file, "w") as f:
                json.dump(task_data, f)
        except Exception as e:
            self.logger.error(f"Error saving task data for {task_id}: {e}")

    def _load_task_data(self, task_id: str) -> Dict[str, Any]:
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

            with open(task_file, "r") as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading task data for {task_id}: {e}")
            return None
