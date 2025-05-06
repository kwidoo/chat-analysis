import os
import numpy as np
import faiss
import threading
from typing import Dict, List, Tuple, Optional, Any
from services.interfaces import IndexServiceInterface


class FaissIndexService(IndexServiceInterface):
    def __init__(
        self,
        index_path: str,
        embedding_dimension: int = None,
        lock: threading.Lock = None,
    ):
        """Initialize the FAISS index service

        Args:
            index_path: Path to the FAISS index file
            embedding_dimension: Dimension of embeddings (only needed when creating a new index)
            lock: Optional threading lock for thread safety
        """
        self.index_path = index_path
        self.lock = lock or threading.Lock()

        # Load or create the index
        with self.lock:
            if os.path.exists(index_path):
                self.index = faiss.read_index(index_path)
            else:
                if embedding_dimension is None:
                    raise ValueError(
                        "embedding_dimension must be provided when creating a new index"
                    )
                os.makedirs(os.path.dirname(index_path), exist_ok=True)
                self.index = faiss.IndexFlatL2(embedding_dimension)

    def add_embeddings(self, embeddings: np.ndarray) -> None:
        """Add embeddings to the index

        Args:
            embeddings: Array of embeddings to add
        """
        if embeddings.size == 0:
            return

        with self.lock:
            self.index.add(np.array(embeddings, dtype="float32"))
            self.save_index()

    def search(self, query_embedding: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """Search for similar embeddings in the index

        Args:
            query_embedding: Query embedding
            k: Number of results to return

        Returns:
            Tuple of (distances, indices)
        """
        with self.lock:
            return self.index.search(np.array([query_embedding], dtype="float32"), k)

    def get_total(self) -> int:
        """Return the total number of embeddings in the index"""
        return self.index.ntotal

    def save_index(self) -> None:
        """Save the index to disk"""
        with self.lock:
            os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
            faiss.write_index(self.index, self.index_path)


class IndexManager:
    """Factory for FAISS index services"""

    def __init__(self, base_dir: str):
        """Initialize the index manager

        Args:
            base_dir: Base directory for index storage
        """
        self.base_dir = base_dir
        self.lock = threading.Lock()

    def get_index_path(self, model_version: str) -> str:
        """Get the path to the index file for a given model version

        Args:
            model_version: Model version identifier
        """
        return os.path.join(self.base_dir, f"indexes/{model_version}/index.index")

    def get_index_service(
        self, model_version: str, embedding_dimension: int = None
    ) -> IndexServiceInterface:
        """Get or create an index service for a given model version

        Args:
            model_version: Model version identifier
            embedding_dimension: Dimension of embeddings (only needed when creating a new index)
        """
        index_path = self.get_index_path(model_version)
        return FaissIndexService(index_path, embedding_dimension, self.lock)
