import numpy as np
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
from services.interfaces import EmbeddingServiceInterface
from dask.distributed import Client
import os


class SentenceTransformerEmbeddingService(EmbeddingServiceInterface):
    def __init__(self, model_name: str, client: Client = None):
        """Initialize the embedding service with a specific model

        Args:
            model_name: The name or path of the Sentence Transformer model
            client: Optional Dask client for distributed processing
        """
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        self.client = client

    def encode(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings using Sentence Transformers

        Use Dask for distributed processing if client is provided

        Args:
            texts: List of text strings to encode

        Returns:
            Array of embeddings
        """
        if not texts:
            return np.array([])

        if self.client:
            # Use Dask for distributed processing
            future = self.client.submit(self.model.encode, texts)
            return future.result()
        else:
            # Process locally
            return self.model.encode(texts)

    def get_embedding_dimension(self) -> int:
        """Return the dimension of the embeddings"""
        return self.model.get_sentence_embedding_dimension()


class ModelRegistry:
    """Registry of available embedding models"""

    MODELS = {
        'v1': 'all-MiniLM-L6-v2',
        'v2': 'sentence-transformers/all-mpnet-base-v2'
    }

    @classmethod
    def get_model_path(cls, version: str) -> str:
        """Get the model path for a given version"""
        if version not in cls.MODELS:
            raise ValueError(f"Model version {version} not found")
        return cls.MODELS[version]

    @classmethod
    def get_available_models(cls) -> Dict[str, str]:
        """Get all available models"""
        return cls.MODELS.copy()

    @classmethod
    def get_embedding_service(cls, version: str, client: Client = None) -> EmbeddingServiceInterface:
        """Create an embedding service for a given model version"""
        model_path = cls.get_model_path(version)
        return SentenceTransformerEmbeddingService(model_path, client)
