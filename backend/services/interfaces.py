from abc import ABC, abstractmethod
import numpy as np
from typing import List, Dict, Any, Tuple, Union, Optional


class EmbeddingServiceInterface(ABC):
    @abstractmethod
    def encode(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for a list of texts"""
        pass

    @abstractmethod
    def get_embedding_dimension(self) -> int:
        """Return the dimension of the embeddings"""
        pass


class IndexServiceInterface(ABC):
    @abstractmethod
    def add_embeddings(self, embeddings: np.ndarray) -> None:
        """Add embeddings to the index"""
        pass

    @abstractmethod
    def search(self, query_embedding: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """Search for similar embeddings in the index"""
        pass

    @abstractmethod
    def get_total(self) -> int:
        """Return the total number of embeddings in the index"""
        pass

    @abstractmethod
    def save_index(self) -> None:
        """Save the index to disk"""
        pass


class IndexVersionManagerInterface(ABC):
    @abstractmethod
    def commit_version(self, message: str) -> str:
        """Commit current index state to the version history

        Args:
            message: Commit message describing the changes

        Returns:
            str: Version identifier
        """
        pass

    @abstractmethod
    def tag_version(self, version_id: str, tag: str) -> None:
        """Tag a specific version for easy reference

        Args:
            version_id: The version identifier to tag
            tag: The tag name
        """
        pass

    @abstractmethod
    def rollback(self, version_id: str) -> bool:
        """Roll back to a previous version

        Args:
            version_id: Version identifier to roll back to

        Returns:
            bool: Whether the rollback was successful
        """
        pass

    @abstractmethod
    def list_versions(self) -> List[Dict[str, Any]]:
        """List all available versions

        Returns:
            List of version details including id, date, message, tags
        """
        pass

    @abstractmethod
    def get_version_info(self, version_id: str) -> Dict[str, Any]:
        """Get details about a specific version

        Args:
            version_id: Version identifier

        Returns:
            Dict with version details
        """
        pass

    @abstractmethod
    def run_migration(self, source_version: str, target_version: str) -> bool:
        """Run migration script between two versions

        Args:
            source_version: Source version identifier
            target_version: Target version identifier

        Returns:
            bool: Whether the migration was successful
        """
        pass

    @abstractmethod
    def check_health(self, version_id: Optional[str] = None) -> Dict[str, Any]:
        """Check health of a specific version or the current index

        Args:
            version_id: Optional version identifier, if None uses current

        Returns:
            Dict with health metrics
        """
        pass


class QueueServiceInterface(ABC):
    @abstractmethod
    def add_task(self, task: Any, task_id: str) -> None:
        """Add a task to the queue"""
        pass

    @abstractmethod
    def get_queue_size(self) -> int:
        """Return the size of the queue"""
        pass

    @abstractmethod
    def save_queue(self) -> None:
        """Save the queue state to disk"""
        pass

    @abstractmethod
    def get_queue_status(self) -> Dict[str, int]:
        """Return queue statistics"""
        pass

    @abstractmethod
    def update_queue_status(self, status_key: str, increment: int = 1) -> None:
        """Update queue statistics"""
        pass
