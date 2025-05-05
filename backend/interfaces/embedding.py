"""
Embedding Service Interfaces

This module defines interfaces for embedding-related services,
implementing the Interface Segregation Principle (I in SOLID).
"""
from abc import ABC, abstractmethod
from typing import List, Any, Optional


class IEmbeddingService(ABC):
    """Interface for embedding generation services"""

    @abstractmethod
    def embed_document(self, text: str) -> List[float]:
        """Generate an embedding for a document

        Args:
            text: The text to embed

        Returns:
            The embedding vector
        """
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of documents

        Args:
            texts: List of text documents to embed

        Returns:
            List of embedding vectors
        """
        pass

    @abstractmethod
    def get_embedding_dimension(self) -> int:
        """Get the dimension of the embedding vectors

        Returns:
            The dimension of the embedding vectors
        """
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Get the name of the embedding model

        Returns:
            The name of the embedding model
        """
        pass


class IModelProvider(ABC):
    """Interface for model providers (e.g., OpenAI, Hugging Face)

    This supports the Open/Closed Principle by allowing new model providers
    to be added without modifying existing code.
    """

    @abstractmethod
    def get_embedding_service(self, model_name: str,
                              distributed_client: Optional[Any] = None) -> IEmbeddingService:
        """Get an embedding service for a model

        Args:
            model_name: The name of the model
            distributed_client: Optional client for distributed processing

        Returns:
            An embedding service for the model
        """
        pass

    @abstractmethod
    def get_available_models(self) -> List[str]:
        """Get the list of available models from this provider

        Returns:
            List of model names
        """
        pass
