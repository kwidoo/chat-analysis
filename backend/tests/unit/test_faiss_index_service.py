import os
import shutil
import tempfile
import threading

import numpy as np
import pytest
from services.index_service import FaissIndexService, IndexManager


class TestFaissIndexService:
    @pytest.fixture
    def temp_dir(self):
        """Fixture to create and clean up a temporary directory"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def index_path(self, temp_dir):
        """Fixture for a temporary index path"""
        return os.path.join(temp_dir, "test_index.index")

    def test_create_new_index(self, index_path):
        """Test creating a new index"""
        embedding_dimension = 128
        service = FaissIndexService(index_path, embedding_dimension)

        assert service.get_total() == 0
        assert not os.path.exists(index_path)  # Index is not saved until add_embeddings is called

    def test_add_embeddings(self, index_path):
        """Test adding embeddings to the index"""
        embedding_dimension = 128
        service = FaissIndexService(index_path, embedding_dimension)

        # Generate random embeddings
        embeddings = np.random.random((5, embedding_dimension)).astype("float32")

        # Add to index
        service.add_embeddings(embeddings)

        # Verify embeddings were added
        assert service.get_total() == 5
        assert os.path.exists(index_path)

    def test_search(self, index_path):
        """Test searching the index"""
        embedding_dimension = 128
        service = FaissIndexService(index_path, embedding_dimension)

        # Generate random embeddings
        embeddings = np.random.random((10, embedding_dimension)).astype("float32")

        # Add to index
        service.add_embeddings(embeddings)

        # Search for the first embedding (should be an exact match)
        query = embeddings[0]
        distances, indices = service.search(query, 3)

        assert indices[0][0] == 0  # First result should be the query itself
        assert len(indices[0]) == 3  # Should return 3 results

    def test_empty_index_search(self, index_path):
        """Test searching an empty index"""
        embedding_dimension = 128
        service = FaissIndexService(index_path, embedding_dimension)

        # Generate query embedding
        query = np.random.random(embedding_dimension).astype("float32")

        # Search empty index
        distances, indices = service.search(query, 3)

        assert distances.shape == (1, 3)
        assert indices.shape == (1, 3)
        # FAISS returns -1 for indices when no results are found
        assert (indices == -1).all()


class TestIndexManager:
    @pytest.fixture
    def temp_dir(self):
        """Fixture to create and clean up a temporary directory"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    def test_get_index_path(self, temp_dir):
        """Test that index paths are constructed correctly"""
        manager = IndexManager(temp_dir)

        path = manager.get_index_path("v1")
        expected_path = os.path.join(temp_dir, "indexes/v1/index.index")

        assert path == expected_path

    def test_get_index_service(self, temp_dir):
        """Test that index services are created correctly"""
        manager = IndexManager(temp_dir)

        # Create an index service
        embedding_dimension = 128
        service = manager.get_index_service("v1", embedding_dimension)

        assert isinstance(service, FaissIndexService)
        assert service.index_path == os.path.join(temp_dir, "indexes/v1/index.index")
