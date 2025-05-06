import os
import shutil
import tempfile

import pytest
from services.queue_service import FileProcessingQueueService


class MockFile:
    """Mock file object for testing"""

    def __init__(self, filename):
        self.filename = filename


class TestQueueService:
    @pytest.fixture
    def temp_dir(self):
        """Fixture to create and clean up a temporary directory"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def queue_file_path(self, temp_dir):
        """Fixture for a temporary queue file path"""
        return os.path.join(temp_dir, "test_queue.pkl")

    def test_empty_queue_init(self, queue_file_path):
        """Test initializing an empty queue"""
        service = FileProcessingQueueService(queue_file_path)

        assert service.get_queue_size() == 0
        assert service.get_queue_status() == {"total": 0, "processed": 0, "failed": 0}

    def test_add_task(self, queue_file_path):
        """Test adding tasks to the queue"""
        service = FileProcessingQueueService(queue_file_path)

        # Add a task
        file = MockFile("test.json")
        task_id = "test_task_1"
        service.add_task(file, task_id)

        assert service.get_queue_size() == 1
        assert service.get_queue_status()["total"] == 1
        assert os.path.exists(queue_file_path)

    def test_get_task(self, queue_file_path):
        """Test getting tasks from the queue"""
        service = FileProcessingQueueService(queue_file_path)

        # Add a task
        file = MockFile("test.json")
        task_id = "test_task_1"
        service.add_task(file, task_id)

        # Get the task
        task = service.get_task(block=False)
        assert task is not None
        task_file, task_task_id = task

        assert task_file.filename == "test.json"
        assert task_task_id == "test_task_1"

        # Queue should now be empty
        assert service.get_queue_size() == 0

        # Status should not change until we call task_done
        assert service.get_queue_status()["total"] == 1
        assert service.get_queue_status()["processed"] == 0

    def test_update_queue_status(self, queue_file_path):
        """Test updating queue status"""
        service = FileProcessingQueueService(queue_file_path)

        # Update processed count
        service.update_queue_status("processed")
        assert service.get_queue_status()["processed"] == 1

        # Update failed count
        service.update_queue_status("failed", 2)
        assert service.get_queue_status()["failed"] == 2

    def test_empty_queue_get(self, queue_file_path):
        """Test getting tasks from an empty queue"""
        service = FileProcessingQueueService(queue_file_path)

        # Try to get a task without blocking
        task = service.get_task(block=False)
        assert task is None

    def test_task_done(self, queue_file_path):
        """Test marking tasks as done"""
        service = FileProcessingQueueService(queue_file_path)

        # Add a task
        file = MockFile("test.json")
        task_id = "test_task_1"
        service.add_task(file, task_id)

        # Get the task
        service.get_task(block=False)  # Changed: task variable was unused.

        # Mark as done
        service.task_done()

        # Add another task to make sure the queue still works
        file2 = MockFile("test2.json")
        service.add_task(file2, task_id)

        assert service.get_queue_size() == 1
