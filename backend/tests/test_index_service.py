import os
import shutil
import tempfile
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from services.index_service import FaissIndexService, IndexManager


@pytest.fixture
def temp_index_dir():
    """Create a temporary directory for index files"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Clean up after test
    shutil.rmtree(temp_dir)


@pytest.fixture
def index_manager(temp_index_dir):
    """Create an index manager for testing"""
    return IndexManager(temp_index_dir)


@pytest.fixture
def mock_faiss():
    """Mock FAISS library for testing"""
    with patch("services.index_service.faiss") as mock:
        # Simulate index behavior
        mock_index = MagicMock()
        mock_index.ntotal = 0

        # Set up behavior for index creation
        mock.IndexFlatL2.return_value = mock_index

        # Set up behavior for search
        mock_index.search.return_value = (
            np.array([[0.1, 0.2, 0.3]]),  # distances
            np.array([[1, 2, 3]]),  # indices
        )

        # Set up read_index behavior to return our mock index
        mock.read_index.return_value = mock_index

        yield mock


def test_index_creation(mock_faiss, temp_index_dir):
    """Test creating a new FAISS index"""
    index_path = os.path.join(temp_index_dir, "test_index.index")
    index_service = FaissIndexService(index_path, embedding_dimension=384)

    # Verify the index was created with the correct dimension
    mock_faiss.IndexFlatL2.assert_called_once_with(384)

    # Check total count is initially zero
    assert index_service.get_total() == 0


def test_adding_embeddings(mock_faiss, temp_index_dir):
    """Test adding embeddings to an index"""
    index_path = os.path.join(temp_index_dir, "test_index.index")
    index_service = FaissIndexService(index_path, embedding_dimension=384)

    # Create some test embeddings
    embeddings = np.random.rand(10, 384).astype("float32")

    # Add to index
    index_service.add_embeddings(embeddings)

    # Verify the add method was called with the correct embeddings
    mock_faiss.IndexFlatL2.return_value.add.assert_called_once()

    # Verify index was saved
    mock_faiss.write_index.assert_called_once()


def test_search_index(mock_faiss, temp_index_dir):
    """Test searching the index"""
    index_path = os.path.join(temp_index_dir, "test_index.index")
    index_service = FaissIndexService(index_path, embedding_dimension=384)

    # Create a test query embedding
    query = np.random.rand(384).astype("float32")

    # Search the index
    distances, indices = index_service.search(query, k=3)

    # Verify search was called
    mock_faiss.IndexFlatL2.return_value.search.assert_called_once()

    # Verify expected results
    assert distances.shape == (1, 3)
    assert indices.shape == (1, 3)
    np.testing.assert_array_equal(indices, np.array([[1, 2, 3]]))


def test_index_manager(mock_faiss, index_manager):
    """Test the index manager for creating and getting indexes"""
    # Get index service for a model version
    expected_path = os.path.join(index_manager.base_dir, "indexes/model-v1/index.index")
    assert (
        index_manager.get_index_service("model-v1", embedding_dimension=384).index_path
        == expected_path
    )

    # Verify index was created
    assert isinstance(
        index_manager.get_index_service("model-v1", embedding_dimension=384), FaissIndexService
    )


def test_loading_existing_index(mock_faiss, temp_index_dir):
    """Test loading an existing index"""
    index_path = os.path.join(temp_index_dir, "test_index.index")

    # Set up the index path to exist
    os.makedirs(os.path.dirname(index_path), exist_ok=True)
    with open(index_path, "w") as f:
        f.write("mock index file")

    # Verify read_index was called with correct path
    mock_faiss.read_index.assert_called_once_with(index_path)

    # Verify IndexFlatL2 wasn't called (since we're loading not creating)
    mock_faiss.IndexFlatL2.assert_not_called()


def test_index_versioning(index_manager):
    """Test creating indexes with different versions"""
    # Create two different version indexes
    index_v1 = index_manager.get_index_service("model-v1", embedding_dimension=384)
    index_v2 = index_manager.get_index_service("model-v2", embedding_dimension=512)

    # Verify they have different paths
    assert index_v1.index_path != index_v2.index_path

    # Check paths contain correct version identifiers
    assert "model-v1" in index_v1.index_path
    assert "model-v2" in index_v2.index_path
