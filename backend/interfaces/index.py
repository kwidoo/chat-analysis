"""
Index Service Interfaces

This module defines interfaces for index-related services,
implementing the Interface Segregation Principle (I in SOLID).
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple


class IIndexService(ABC):
    """Interface for vector index operations"""

    @abstractmethod
    def add(self, embedding: List[float], document_id: str) -> bool:
        """Add an embedding to the index

        Args:
            embedding: The embedding vector
            document_id: The ID of the document

        Returns:
            True if the embedding was added successfully, False otherwise
        """
        pass

    @abstractmethod
    def add_batch(self, embeddings: List[List[float]], document_ids: List[str]) -> bool:
        """Add multiple embeddings to the index

        Args:
            embeddings: List of embedding vectors
            document_ids: List of document IDs

        Returns:
            True if all embeddings were added successfully, False otherwise
        """
        pass

    @abstractmethod
    def search(self, query_embedding: List[float], top_k: int = 10) -> Tuple[Any, Any]:
        """Search the index for similar embeddings

        Args:
            query_embedding: The query embedding vector
            top_k: Number of results to return

        Returns:
            Tuple of (indices, distances)
        """
        pass

    @abstractmethod
    def get_total(self) -> int:
        """Get the total number of embeddings in the index

        Returns:
            The number of embeddings in the index
        """
        pass

    @abstractmethod
    def save(self) -> bool:
        """Save the index to disk

        Returns:
            True if the index was saved successfully, False otherwise
        """
        pass

    @abstractmethod
    def load(self) -> bool:
        """Load the index from disk

        Returns:
            True if the index was loaded successfully, False otherwise
        """
        pass


class IIndexHealthMonitorService(ABC):
    """Interface for index health monitoring operations"""

    @abstractmethod
    def start_monitoring(self) -> None:
        """Start monitoring the index health"""
        pass

    @abstractmethod
    def stop_monitoring(self) -> None:
        """Stop monitoring the index health"""
        pass

    @abstractmethod
    def detect_corruption(self) -> Dict[str, str]:
        """Check for index corruption

        Returns:
            Dictionary with status information
        """
        pass


class IIndexVersionManager(ABC):
    """Interface for index version management operations"""

    @abstractmethod
    def get_current_version(self) -> str:
        """Get the current index version

        Returns:
            The current index version
        """
        pass

    @abstractmethod
    def create_version(self, version_name: str) -> bool:
        """Create a new index version

        Args:
            version_name: The name of the new version

        Returns:
            True if the version was created successfully, False otherwise
        """
        pass

    @abstractmethod
    def switch_version(self, version_name: str) -> bool:
        """Switch to a different index version

        Args:
            version_name: The name of the version to switch to

        Returns:
            True if the switch was successful, False otherwise
        """
        pass

    @abstractmethod
    def list_versions(self) -> List[Dict[str, Any]]:
        """List all available index versions

        Returns:
            List of version information dictionaries
        """
        pass
