import json
import threading
import time
import queue
import os
from typing import Callable, Any

from services.interfaces import (
    QueueServiceInterface,
    EmbeddingServiceInterface,
    IndexServiceInterface,
)


class QueueProcessor:
    """Processor for the file processing queue"""

    def __init__(
        self,
        queue_service: QueueServiceInterface,
        embedding_service: EmbeddingServiceInterface,
        index_service: IndexServiceInterface,
    ):
        """Initialize the queue processor

        Args:
            queue_service: Queue service to process
            embedding_service: Embedding service to generate embeddings
            index_service: Index service to store embeddings
        """
        self.queue_service = queue_service
        self.embedding_service = embedding_service
        self.index_service = index_service
        self.thread = None
        self.running = False

    def start(self):
        """Start the queue processor thread"""
        if self.thread is not None and self.thread.is_alive():
            return

        self.running = True
        self.thread = threading.Thread(target=self._process_queue)
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        """Stop the queue processor thread"""
        self.running = False
        if self.thread is not None:
            self.thread.join(timeout=5.0)

    def _process_queue(self):
        """Main queue processing loop"""
        while self.running:
            try:
                # Get item from queue with 5-second timeout
                task = self.queue_service.get_task(block=True, timeout=5)
                if task is None:
                    time.sleep(1)
                    continue

                file, task_id = task

                try:
                    self._process_file(file)
                    # Update stats
                    self.queue_service.update_queue_status("processed")
                except Exception as e:
                    print(f"Error processing file {file.filename}: {e}")
                    self.queue_service.update_queue_status("failed")

                # Mark task as complete
                self.queue_service.task_done()

                # Update persisted queue
                self.queue_service.save_queue()
            except Exception as e:
                print(f"Queue processing error: {e}")
                time.sleep(1)

    def _process_file(self, file):
        """Process a single file

        Args:
            file: File to process
        """
        # Read file contents
        content = file.read()
        if isinstance(content, bytes):
            content = content.decode("utf-8")

        # Parse JSON if it's a JSON file
        data = json.loads(content) if file.filename.endswith(".json") else {"text": content}

        # Extract messages
        messages = []
        if "messages" in data:
            messages = [msg.get("content", "") for msg in data["messages"] if "content" in msg]
        elif "text" in data:
            messages = [data["text"]]

        if not messages:
            raise ValueError("No messages found in file")

        # Generate embeddings
        embeddings = self.embedding_service.encode(messages)

        # Add to index
        self.index_service.add_embeddings(embeddings)
