import os
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pytest
from services.index_service import FaissIndexService

# Add the backend directory to the path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))


@pytest.fixture
def temp_index_path():
    """Create a temporary directory for test index"""
    temp_dir = tempfile.mkdtemp()
    yield os.path.join(temp_dir, "test_index.index")
    # Cleanup not needed as we're using tmpdir


@pytest.fixture
def populated_index(temp_index_path):
    """Create and populate a test index with sample data"""
    # Define parameters
    num_vectors = 100000  # 100k vectors for stress test
    dimension = 384  # Common embedding dimension

    # Create index service
    index_service = FaissIndexService(temp_index_path, embedding_dimension=dimension)

    # Generate random embeddings
    embeddings = np.random.rand(num_vectors, dimension).astype("float32")

    # Add embeddings in batches to avoid memory issues
    batch_size = 10000
    for i in range(0, num_vectors, batch_size):
        batch_end = min(i + batch_size, num_vectors)
        index_service.add_embeddings(embeddings[i:batch_end])

    return index_service


def test_index_creation_performance():
    """Test the performance of index creation"""
    # Parameters
    num_vectors = 50000
    dimension = 384

    # Create temporary file
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        index_path = tmp.name

    try:
        # Measure time to create index
        start_time = time.time()

        index_service = FaissIndexService(index_path, embedding_dimension=dimension)

        # Generate random embeddings
        embeddings = np.random.rand(num_vectors, dimension).astype("float32")

        # Add all embeddings
        index_service.add_embeddings(embeddings)

        creation_time = time.time() - start_time

        # Assertions to ensure performance is acceptable
        assert creation_time < 30.0, f"Index creation took too long: {creation_time:.2f} seconds"
        print(f"Created index with {num_vectors} vectors in {creation_time:.2f} seconds")

    finally:
        # Clean up
        if os.path.exists(index_path):
            os.unlink(index_path)


def test_search_performance(populated_index):
    """Test search performance with a single query"""
    # Generate a random query vector
    query = np.random.rand(384).astype("float32")

    # Measure search time
    start_time = time.time()

    # Perform search
    distances, indices = populated_index.search(query, k=10)

    search_time = time.time() - start_time

    # Assertions
    assert distances.shape == (1, 10), "Expected 10 results"
    assert indices.shape == (1, 10), "Expected 10 results"
    assert search_time < 0.1, f"Search took too long: {search_time:.4f} seconds"
    print(f"Single search completed in {search_time:.4f} seconds")


def test_concurrent_search_performance(populated_index):
    """Test performance under concurrent search load"""
    # Parameters
    num_threads = 20
    num_queries_per_thread = 50
    dimension = 384

    # Function to be executed by each thread
    def run_searches(thread_id):
        times = []
        for i in range(num_queries_per_thread):
            # Generate a random query vector
            query = np.random.rand(dimension).astype("float32")

            # Measure search time
            start_time = time.time()
            populated_index.search(query, k=10)
            times.append(time.time() - start_time)

        return times

    # Execute searches concurrently
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        results = list(executor.map(run_searches, range(num_threads)))

    total_time = time.time() - start_time

    # Flatten results
    all_times = [time for thread_times in results for time in thread_times]

    # Calculate statistics
    avg_time = sum(all_times) / len(all_times)
    max_time = max(all_times)
    min_time = min(all_times)

    # Assertions
    assert avg_time < 0.2, f"Average search time is too high: {avg_time:.4f} seconds"
    assert max_time < 0.5, f"Max search time is too high: {max_time:.4f} seconds"

    total_searches = num_threads * num_queries_per_thread
    print(f"Completed {total_searches} concurrent searches in {total_time:.2f} seconds")
    print(f"Average: {avg_time:.4f}s, Min: {min_time:.4f}s, Max: {max_time:.4f}s")


def test_large_batch_search(populated_index):
    """Test searching with large batch of query vectors"""
    # Parameters
    batch_size = 100
    dimension = 384

    # Generate batch of query vectors
    query_batch = np.random.rand(batch_size, dimension).astype("float32")

    # Measure batch search time
    start_time = time.time()

    # Perform individual searches to simulate batch
    results = []
    for i in range(batch_size):
        distances, indices = populated_index.search(query_batch[i], k=10)
        results.append((distances, indices))

    batch_time = time.time() - start_time

    # Assertions
    assert len(results) == batch_size
    assert batch_time < 10.0, f"Batch search took too long: {batch_time:.2f} seconds"
    print(f"Completed batch of {batch_size} searches in {batch_time:.2f} seconds")


if __name__ == "__main__":
    # Run the tests directly when executing the script
    pytest.main(["-xvs", __file__])
