import os
import shutil
import tempfile
import threading
from datetime import datetime, timedelta
from pathlib import Path

import faiss
import git
import numpy as np
import pytest
from services.distributed_indexer import DaskDistributedIndexer
from services.index_health_monitor import IndexHealthMonitor
from services.index_version_manager import GitIndexVersionManager


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


class TestGitIndexVersionManager:
    """Tests for the GitIndexVersionManager class"""

    @pytest.fixture
    def version_manager(self, temp_dir):
        """Create a version manager for testing"""
        config = {
            "FAISS_DIR": os.path.join(temp_dir, "faiss"),
            "MODELS_DIR": os.path.join(temp_dir, "models"),
            "ACTIVE_MODEL": "v1",
        }
        manager = GitIndexVersionManager(config)

        # Create a dummy index for testing
        index_dir = Path(config["FAISS_DIR"]) / "indexes" / "v1"
        index_dir.mkdir(parents=True, exist_ok=True)
        index_path = index_dir / "index.index"

        # Create a simple index with one vector
        index = faiss.IndexFlatL2(128)
        vec = np.random.random(128).astype("float32").reshape(1, -1)
        index.add(vec)
        faiss.write_index(index, str(index_path))

        return manager

    def test_init_creates_git_repo(self, version_manager):
        """Test that the init method creates a Git repository"""
        assert os.path.exists(os.path.join(version_manager.git_repo_dir, ".git"))
        assert os.path.exists(os.path.join(version_manager.git_repo_dir, "README.md"))

    def test_commit_version(self, version_manager):
        """Test committing a version"""
        # Commit the version
        version_id = version_manager.commit_version("Initial commit")

        # Check that the commit was created
        assert len(version_id) > 0

        # Check that the index was copied to the repository
        assert os.path.exists(
            os.path.join(version_manager.git_repo_dir, "indexes", "v1", "index.index")
        )

    def test_list_versions(self, version_manager):
        """Test listing versions"""
        # Commit a version
        version_id1 = version_manager.commit_version("First commit")

        # Modify the index and commit again
        index_path = version_manager.index_dir / "v1" / "index.index"
        index = faiss.read_index(str(index_path))
        vec = np.random.random(128).astype("float32").reshape(1, -1)
        index.add(vec)
        faiss.write_index(index, str(index_path))

        version_manager.commit_version("Second commit")

        # List versions
        versions = version_manager.list_versions()

        # Check that we have at least the commits we created (plus initial repo setup)
        assert len(versions) >= 2
        assert version_id1 in [v["id"] for v in versions]

    def test_tag_version(self, version_manager):
        """Test tagging a version"""
        # Commit a version
        version_id = version_manager.commit_version("Version to tag")

        # Tag it
        tag_name = "v1.0.0"
        version_manager.tag_version(version_id, tag_name)

        # Check that the tag exists
        versions = version_manager.list_versions()
        tagged_version = next(v for v in versions if v["id"] == version_id)
        assert tag_name in tagged_version["tags"]

    def test_rollback(self, version_manager):
        """Test rolling back to a previous version"""
        # Initial commit
        initial_path = version_manager.index_dir / "v1" / "index.index"
        initial_index = faiss.read_index(str(initial_path))
        initial_count = initial_index.ntotal

        version_id1 = version_manager.commit_version("Initial version")

        # Modify the index and commit again
        index_path = version_manager.index_dir / "v1" / "index.index"
        index = faiss.read_index(str(index_path))
        vec = np.random.random(128).astype("float32").reshape(1, -1)
        index.add(vec)
        faiss.write_index(index, str(index_path))

        modified_index = faiss.read_index(str(index_path))
        modified_count = modified_index.ntotal

        # Check that the counts are different
        assert initial_count != modified_count

        # Roll back to the first version
        result = version_manager.rollback(version_id1)
        assert result is True

        # Check that the index is back to the initial state
        current_index = faiss.read_index(str(index_path))
        assert current_index.ntotal == initial_count


class TestIndexHealthMonitor:
    """Tests for the IndexHealthMonitor class"""

    @pytest.fixture
    def health_monitor(self, temp_dir):
        """Create a health monitor for testing"""
        config = {
            "FAISS_DIR": os.path.join(temp_dir, "faiss"),
            "ACTIVE_MODEL": "v1",
            "HEALTH_CHECK_INTERVAL": 1,  # 1 second for faster tests
            "VACUUM_THRESHOLD": 20,
            "VACUUM_INTERVAL": 0.01,  # 0.01 hours (36 seconds) for faster tests
        }

        # Create a dummy index for testing
        index_dir = Path(config["FAISS_DIR"]) / "indexes" / "v1"
        index_dir.mkdir(parents=True, exist_ok=True)
        index_path = index_dir / "index.index"

        # Create a simple index with one vector
        index = faiss.IndexFlatL2(128)
        vec = np.random.random(128).astype("float32").reshape(1, -1)
        index.add(vec)
        faiss.write_index(index, str(index_path))

        monitor = IndexHealthMonitor(config)
        return monitor

    def test_check_index_health(self, health_monitor):
        """Test checking index health"""
        metrics = health_monitor.check_index_health()

        # Check that we have basic metrics
        assert metrics["status"] == "healthy"
        assert "ntotal" in metrics
        assert metrics["ntotal"] == 1
        assert "dimension" in metrics
        assert metrics["dimension"] == 128
        assert "check_time_ms" in metrics

    def test_detect_corruption(self, health_monitor):
        """Test corruption detection"""
        result = health_monitor.detect_corruption()

        # Check that the index is healthy
        assert result["status"] == "healthy"
        assert result["header_check"] == "passed"
        assert result["structure_check"] == "passed"

        # Check that detection is fast
        assert result["check_time_ms"] < 1000  # Should be < 1s

    def test_vacuum_index(self, health_monitor):
        """Test vacuuming the index"""
        result = health_monitor.vacuum_index()

        # Check that the vacuum completed
        assert result["status"] == "completed"
        assert result["original_count"] == 1
        assert result["new_count"] == 1
        assert "backup_created" in result


@pytest.mark.skipif(
    os.environ.get("CI") == "true",
    reason="Dask tests need a real distributed environment",
)
class TestDaskDistributedIndexer:
    """Tests for the DaskDistributedIndexer class"""

    @pytest.fixture
    def distributed_indexer(self, temp_dir):
        """Create a distributed indexer for testing"""
        config = {
            "FAISS_DIR": os.path.join(temp_dir, "faiss"),
            "ACTIVE_MODEL": "v1",
            "DASK_SCHEDULER_ADDRESS": "tcp://localhost:8786",  # Use local Dask scheduler
            "CHUNK_SIZE": 100,
            "MAX_WORKERS": 2,
            "INDEX_TYPE": "flat",
            "IVF_NLIST": 10,
        }

        # Skip test if no Dask scheduler available
        pytest.importorskip("dask.distributed")

        try:
            from dask.distributed import Client

            client = Client(config["DASK_SCHEDULER_ADDRESS"])
            client.close()
        except Exception:
            pytest.skip("No Dask scheduler available at localhost:8786")

        indexer = DaskDistributedIndexer(config)
        return indexer

    def test_build_index(self, distributed_indexer):
        """Test building an index with Dask"""
        # Create test embeddings
        num_vectors = 500
        dimension = 128
        embeddings = np.random.random((num_vectors, dimension)).astype("float32")

        # Build index
        index_path = distributed_indexer.build_index(embeddings, dimension)

        # Check that the index was created
        assert os.path.exists(index_path)

        # Check that the index has the right number of vectors
        index = faiss.read_index(index_path)
        assert index.ntotal == num_vectors

    def test_build_index_with_batches(self, distributed_indexer):
        """Test building an index from batches"""
        dimension = 128
        batches = []

        # Create 5 batches of 100 vectors each
        for i in range(5):
            batch = np.random.random((100, dimension)).astype("float32")
            batches.append(batch)

        # Create batch generator
        def batch_generator():
            for batch in batches:
                yield batch, len(batch)

        # Build index
        index_path = distributed_indexer.index_from_batches(lambda: batch_generator(), dimension)

        # Check that the index was created
        assert os.path.exists(index_path)

        # Check that the index has the right number of vectors
        index = faiss.read_index(index_path)
        assert index.ntotal == 500  # 5 batches * 100 vectors
