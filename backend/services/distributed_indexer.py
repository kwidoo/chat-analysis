import logging
import os
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple, Union

import dask.array as da
import faiss
import fasteners
import numpy as np
from dask.distributed import Client, get_client, wait

logger = logging.getLogger(__name__)


class DaskDistributedIndexer:
    """Efficient distributed FAISS index builder using Dask

    This class implements parallel indexing using Dask to efficiently
    process large embedding datasets and build optimized FAISS indices.
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize the distributed indexer

        Args:
            config: Configuration dictionary with keys:
                - FAISS_DIR: Base directory for FAISS indexes
                - ACTIVE_MODEL: Current active model name
                - DASK_SCHEDULER_ADDRESS: Dask scheduler address
                - CHUNK_SIZE: Size of chunks for processing (default: 10000)
                - MAX_WORKERS: Maximum worker processes (default: 4)
                - INDEX_TYPE: Type of index to build (default: 'flat')
                - IVF_NLIST: Number of centroids for IVF indices (default: 100)
        """
        self.faiss_dir = Path(config.get("FAISS_DIR", "./faiss"))
        self.active_model = config.get("ACTIVE_MODEL", "v1")
        self.dask_scheduler = config.get("DASK_SCHEDULER_ADDRESS", "tcp://dask-scheduler:8786")

        # Indexing settings
        self.chunk_size = config.get("CHUNK_SIZE", 10000)
        self.max_workers = config.get("MAX_WORKERS", 4)
        self.index_type = config.get("INDEX_TYPE", "flat").lower()
        self.ivf_nlist = config.get("IVF_NLIST", 100)

        # Paths
        self.index_dir = self.faiss_dir / "indexes" / self.active_model
        self.index_path = self.index_dir / "index.index"
        self.index_dir.mkdir(parents=True, exist_ok=True)

        # Lock for thread safety
        self._lock = threading.Lock()
        self._file_lock = fasteners.InterProcessLock(str(self.faiss_dir / "index.lock"))

        # Dask client
        self._client = None

    def get_client(self) -> Client:
        """Get or create Dask client

        Returns:
            dask.distributed.Client: Dask client
        """
        if self._client is None:
            try:
                # Try to get existing client
                self._client = get_client()
                logger.info("Using existing Dask client")
            except ValueError:
                # Create new client
                logger.info(f"Connecting to Dask scheduler at {self.dask_scheduler}")
                self._client = Client(self.dask_scheduler)
                logger.info(f"Dask {len(self._client.scheduler_info()['workers'])} workers")

        return self._client

    def build_index(
        self, embeddings: Union[np.ndarray, da.Array], dimension: Optional[int] = None
    ) -> str:
        """Build a FAISS index from embeddings using distributed processing

        Args:
            embeddings: NumPy or Dask array of embeddings
            dimension: Dimension of embeddings (if not provided, inferred from data)

        Returns:
            str: Path to the built index
        """
        start_time = time.time()

        # Get embeddings info
        if dimension is None:
            if isinstance(embeddings, np.ndarray):
                dimension = embeddings.shape[1]
            else:
                # For Dask Array
                dimension = embeddings.shape[1]

        total_vectors = len(embeddings)
        logger.info(f"Building index with {total_vectors} vectors of dimension {dimension}")

        # Convert to Dask array if not already
        if isinstance(embeddings, np.ndarray):
            # Create Dask array with chunks of appropriate size
            dask_embeddings = da.from_array(embeddings, chunks=(self.chunk_size, dimension))
        else:
            dask_embeddings = embeddings

        # Get Dask client
        self.get_client()  # Changed: client variable was unused.

        # Choose index building strategy based on index type and size
        if self.index_type == "flat":
            index_path = self._build_flat_index(dask_embeddings, dimension)
        elif self.index_type == "ivf":
            index_path = self._build_ivf_index(dask_embeddings, dimension)
        elif self.index_type == "hnsw":
            index_path = self._build_hnsw_index(dask_embeddings, dimension)
        else:
            raise ValueError(f"Unsupported index type: {self.index_type}")

        elapsed_time = time.time() - start_time
        logger.info(
            f"Built index with {total_vectors} vectors in {elapsed_time:.2f}s "
            f"({total_vectors / elapsed_time:.2f} vectors/second)"
        )

        return index_path

    def _build_flat_index(self, embeddings: da.Array, dimension: int) -> str:
        """Build a flat index using parallel processing

        Args:
            embeddings: Dask array of embeddings
            dimension: Embedding dimension

        Returns:
            str: Path to the built index
        """
        # Create empty flat index
        index = faiss.IndexFlatL2(dimension)

        # Process in chunks for better memory management
        return self._build_chunked_index(embeddings, index)

    def _build_ivf_index(self, embeddings: da.Array, dimension: int) -> str:
        """Build an IVF index using parallel processing

        Args:
            embeddings: Dask array of embeddings
            dimension: Embedding dimension

        Returns:
            str: Path to the built index
        """
        # Create quantizer and index
        quantizer = faiss.IndexFlatL2(dimension)
        index = faiss.IndexIVFFlat(quantizer, dimension, self.ivf_nlist)

        # IVF indices need training
        # Sample data for training
        train_size = min(256 * self.ivf_nlist, len(embeddings))
        logger.info(f"Sampling {train_size} vectors for IVF training")

        # Get training vectors - sample from the dataset
        # We'll use Dask to compute a random sample
        train_indices = np.random.choice(len(embeddings), train_size, replace=False)
        train_vectors = embeddings[train_indices].compute()

        # Train the index
        logger.info("Training IVF index...")
        index.train(train_vectors.astype("float32"))

        # Now build the index with trained centroids
        return self._build_chunked_index(embeddings, index)

    def _build_hnsw_index(self, embeddings: da.Array, dimension: int) -> str:
        """Build an HNSW index using parallel processing

        Args:
            embeddings: Dask array of embeddings
            dimension: Embedding dimension

        Returns:
            str: Path to the built index
        """
        # Create HNSW index
        # HNSW parameters: M (connections per node) and efConstruction (search depth)
        M = 16  # Default connections per node
        ef_construction = 40  # Default search depth during construction

        index = faiss.IndexHNSWFlat(dimension, M)
        index.hnsw.efConstruction = ef_construction

        # HNSW doesn't need training, but adding vectors is not thread-safe
        # So we use a slightly different approach
        futures = []
        client = self.get_client()

        # Split into chunks for parallel processing
        chunks = []
        for i in range(0, len(embeddings), self.chunk_size):
            end = min(i + self.chunk_size, len(embeddings))
            chunks.append(embeddings[i:end])

        # Process chunks in parallel
        for i, chunk in enumerate(chunks):
            # Each worker builds a temporary index
            future = client.submit(
                self._build_partial_hnsw, chunk, dimension, M, ef_construction, i
            )
            futures.append(future)

        # Wait for all tasks to complete
        temp_paths = client.gather(futures)

        # Merge the temporary indices
        merged_index_path = self._merge_hnsw_indices(temp_paths, dimension)

        # Clean up temporary files
        for path in temp_paths:
            try:
                os.remove(path)
            except Exception as e:
                logger.warning(f"Failed to remove temporary file {path}: {e}")

        return merged_index_path

    def _build_partial_hnsw(self, chunk, dimension, M, ef_construction, i):
        """Build a partial HNSW index (runs on worker)"""
        # Convert Dask array chunk to numpy
        vectors = chunk.compute()

        # Create HNSW index
        index = faiss.IndexHNSWFlat(dimension, M)
        index.hnsw.efConstruction = ef_construction

        # Add vectors
        index.add(vectors.astype("float32"))

        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_chunk_{i}.index") as tmp:
            temp_path = tmp.name

        faiss.write_index(index, temp_path)
        return temp_path

    def _merge_hnsw_indices(self, index_paths, dimension):
        """Merge multiple HNSW indices (not efficient, but works for demonstration)"""
        # For a real implementation, merging HNSW indices efficiently is complex
        # This is a simplified approach that creates a new index and adds all vectors

        # Create target index
        merged_index = faiss.IndexHNSWFlat(dimension, 16)

        # Add vectors from all indices
        for path in index_paths:
            # Load index
            index = faiss.read_index(path)

            # Extract vectors (this is inefficient but works for demonstration)
            for i in range(index.ntotal):
                vector = index.reconstruct(i)
                merged_index.add(vector.reshape(1, -1))

        # Save merged index
        faiss.write_index(merged_index, str(self.index_path))

        return str(self.index_path)

    def _build_chunked_index(self, embeddings: da.Array, index: faiss.Index) -> str:
        """Build an index by processing chunks in parallel

        Args:
            embeddings: Dask array of embeddings
            index: FAISS index to populate

        Returns:
            str: Path to the built index
        """
        # Get the client for parallel processing
        client = self.get_client()

        # Process chunks in parallel using Dask
        # Create temporary directory for partial indices
        temp_dir = tempfile.mkdtemp(prefix="faiss_temp_")
        futures = []

        # Split data into chunks and process
        for i in range(0, len(embeddings), self.chunk_size):
            chunk_end = min(i + self.chunk_size, len(embeddings))
            chunk = embeddings[i:chunk_end]

            # Process each chunk in a worker
            chunk_path = os.path.join(temp_dir, f"chunk_{i}.npy")
            future = client.submit(self._process_chunk, chunk, chunk_path)
            futures.append(future)

        # Wait for all chunks to complete
        logger.info(f"Waiting for {len(futures)} chunk processing tasks to complete...")
        wait(futures)
        chunk_paths = client.gather(futures)

        # Add all chunks to the main index
        logger.info("Merging chunks into main index...")
        with self._file_lock:
            for chunk_path in chunk_paths:
                try:
                    # Load chunk
                    chunk_data = np.load(chunk_path)

                    # Add to index
                    index.add(chunk_data.astype("float32"))

                    # Remove temporary file
                    os.remove(chunk_path)
                except Exception as e:
                    logger.error(f"Error processing chunk {chunk_path}: {e}")

        # Remove temporary directory
        try:
            os.rmdir(temp_dir)
        except Exception as e:
            logger.warning(f"Failed to remove temporary directory {temp_dir}: {e}")

        # Save the complete index
        logger.info(f"Saving index with {index.ntotal} vectors to {self.index_path}")

        # Ensure directory exists
        self.index_dir.mkdir(parents=True, exist_ok=True)

        # Write index with lock to avoid concurrent access
        with self._file_lock:
            faiss.write_index(index, str(self.index_path))

        return str(self.index_path)

    @staticmethod
    def _process_chunk(chunk, output_path):
        """Process a chunk of embeddings (runs on worker)"""
        # Compute the chunk (convert from Dask array to NumPy)
        vectors = chunk.compute()

        # Save to temporary file
        np.save(output_path, vectors)

        return output_path

    def index_from_batches(
        self, data_generator: Callable[[], Tuple[np.ndarray, int]], dimension: int
    ) -> str:
        """Build an index from batches of data using a generator

        Args:
            data_generator: Function that yields (batch, total_size) tuples
            dimension: Embedding dimension

        Returns:
            str: Path to the built index
        """
        start_time = time.time()

        # Create appropriate index based on type
        if self.index_type == "flat":
            index = faiss.IndexFlatL2(dimension)
        elif self.index_type == "ivf":
            quantizer = faiss.IndexFlatL2(dimension)
            index = faiss.IndexIVFFlat(quantizer, dimension, self.ivf_nlist)
            # For IVF, we need training data
            # First batch will be used for training
            first_batch, _ = next(data_generator())
            if len(first_batch) > 0:
                logger.info(f"Training IVF index with {len(first_batch)} vectors")
                index.train(first_batch.astype("float32"))
        elif self.index_type == "hnsw":
            index = faiss.IndexHNSWFlat(dimension, 16)  # M=16 connections per node
        else:
            raise ValueError(f"Unsupported index type: {self.index_type}")

        # Process batches
        total_vectors = 0
        for batch, batch_size in data_generator():
            if batch.size == 0:
                continue

            # Add batch to index
            with self._file_lock:
                index.add(batch.astype("float32"))

            total_vectors += batch_size
            logger.info(f"Indexed batch of {batch_size} vectors, total: {total_vectors}")

        # Save the complete index
        logger.info(f"Saving index with {index.ntotal} vectors to {self.index_path}")

        # Ensure directory exists
        self.index_dir.mkdir(parents=True, exist_ok=True)

        # Write index with lock to avoid concurrent access
        with self._file_lock:
            faiss.write_index(index, str(self.index_path))

        elapsed_time = time.time() - start_time
        logger.info(
            f"Built index with {total_vectors} vectors in {elapsed_time:.2f}s "
            f"({total_vectors / elapsed_time:.2f} vectors/second)"
        )

        return str(self.index_path)

    def optimize_index_for_search(
        self, source_path: Optional[str] = None, target_path: Optional[str] = None
    ) -> str:
        """Optimize an existing index for faster search performance

        Args:
            source_path: Path to source index (default: current index)
            target_path: Path to save optimized index (default: replace current)

        Returns:
            str: Path to the optimized index
        """
        if source_path is None:
            source_path = str(self.index_path)

        if target_path is None:
            target_path = str(self.index_path)

        logger.info(f"Optimizing index {source_path} for search performance")

        try:
            # Load source index
            index = faiss.read_index(source_path)

            # Optimize based on index type
            if isinstance(index, faiss.IndexFlat):
                # For flat indices, not much optimization is possible
                optimized = index

            elif isinstance(index, faiss.IndexIVF):
                # For IVF indices, we can set search parameters
                # Increase nprobe for better recall at the cost of speed
                default_nprobe = min(10, index.nlist)
                index.nprobe = default_nprobe
                optimized = index

            elif isinstance(index, faiss.IndexHNSW) or hasattr(index, "hnsw"):
                # For HNSW indices, set efSearch parameter
                if hasattr(index, "hnsw"):
                    index.hnsw.efSearch = 64  # Increase for better recall
                optimized = index

            else:
                # General optimization: try to create an optimized version
                optimized = faiss.index_factory(index.d, "OPQ16_64,IVF256,PQ16")

                # Train on vectors from the original index
                sample_size = min(100000, index.ntotal)
                if index.ntotal > 0:
                    # Extract random vectors for training
                    indices = np.random.choice(index.ntotal, sample_size, replace=False)
                    vectors = np.stack([index.reconstruct(int(i)) for i in indices])

                    # Train the optimized index
                    optimized.train(vectors)

                    # Add all vectors
                    for i in range(0, index.ntotal, 10000):
                        batch_size = min(10000, index.ntotal - i)
                        batch_indices = np.arange(i, i + batch_size)
                        batch_vectors = np.stack([index.reconstruct(int(j)) for j in batch_indices])
                        optimized.add(batch_vectors)

            # Save optimized index
            faiss.write_index(optimized, target_path)
            logger.info(f"Saved optimized index to {target_path}")

            return target_path

        except Exception as e:
            logger.error(f"Error optimizing index: {e}")
            raise
