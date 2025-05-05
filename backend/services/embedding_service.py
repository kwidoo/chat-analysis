"""
Embedding Service for document embeddings

This module provides embedding services for various models, now refactored to use
the model provider registry for better extensibility (Open/Closed Principle).
"""
import os
import logging
from typing import Dict, List, Any, Optional

from interfaces.embedding import IEmbeddingService
from extensions.model_provider import ModelProviderRegistry


class ModelRegistry:
    """Registry of available embedding models

    This registry now uses the model provider registry for extensibility.
    """

    # Legacy model mapping - deprecated in favor of providers but kept for backward compatibility
    MODELS = {
        "v1": "Sentence Transformer MPNet Base",
        "v2": "Sentence Transformer MiniLM L6"
    }

    # Default model to use if none specified
    DEFAULT_MODEL = "v1"

    # Default provider to use if none specified
    DEFAULT_PROVIDER = "huggingface"

    # Provider model mapping
    PROVIDER_MODELS = {
        "v1": ("huggingface", "mpnet-base"),
        "v2": ("huggingface", "minilm-l6"),
        "v3": ("openai", "ada")
    }

    @classmethod
    def get_embedding_service(cls, model_version: str, distributed_client: Optional[Any] = None) -> IEmbeddingService:
        """Get an embedding service for a model version

        Args:
            model_version: Version of the model to use (e.g., "v1", "v2")
            distributed_client: Optional client for distributed processing

        Returns:
            An embedding service for the specified model
        """
        logger = logging.getLogger(__name__)

        # Use default model if none specified
        if not model_version:
            model_version = cls.DEFAULT_MODEL
            logger.info(f"No model version specified, using default: {model_version}")

        # Check if we have a provider mapping for this model
        if model_version in cls.PROVIDER_MODELS:
            provider_name, model_name = cls.PROVIDER_MODELS[model_version]

            # Get the provider from the registry
            provider = ModelProviderRegistry.get_provider(provider_name)
            if not provider:
                logger.warning(f"Provider {provider_name} not found for model {model_version}, trying default provider")
                provider = ModelProviderRegistry.get_provider(cls.DEFAULT_PROVIDER)
                if not provider:
                    raise ValueError(f"Default provider {cls.DEFAULT_PROVIDER} not found")

            # Get the embedding service from the provider
            return provider.get_embedding_service(model_name, distributed_client)

        # Legacy fallback for backward compatibility
        logger.warning(f"Using legacy model initialization for {model_version}")
        if model_version == "v1":
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")
            return LegacySentenceTransformerService(model, model_version)
        elif model_version == "v2":
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
            return LegacySentenceTransformerService(model, model_version)
        else:
            raise ValueError(f"Unknown model version: {model_version}")

    @classmethod
    def get_available_models(cls) -> Dict[str, str]:
        """Get a dictionary of available models

        Returns:
            Dictionary of model versions and names
        """
        models = {}

        # Add models from all providers
        for provider_name in ModelProviderRegistry.get_available_providers():
            provider = ModelProviderRegistry.get_provider(provider_name)
            if provider:
                for model_name in provider.get_available_models():
                    # Find the version key for this provider/model
                    version_key = None
                    for key, (p_name, m_name) in cls.PROVIDER_MODELS.items():
                        if p_name == provider_name and m_name == model_name:
                            version_key = key
                            break

                    if not version_key:
                        # Create a new version key if not found
                        version_key = f"{provider_name}-{model_name}"

                    # Add to the dictionary
                    models[version_key] = f"{provider_name.capitalize()}: {model_name}"

        # Add legacy models for backward compatibility
        for version, name in cls.MODELS.items():
            if version not in models:  # Don't overwrite provider models
                models[version] = name

        return models


class LegacySentenceTransformerService(IEmbeddingService):
    """Legacy adapter for Sentence Transformer models"""

    def __init__(self, model, model_version: str):
        """Initialize the service

        Args:
            model: The Sentence Transformer model
            model_version: The version of the model
        """
        self.model = model
        self.model_version = model_version

    def embed_document(self, text: str) -> List[float]:
        """Generate an embedding for a document

        Args:
            text: The text to embed

        Returns:
            The embedding vector
        """
        embedding = self.model.encode(text)
        return embedding.tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of documents

        Args:
            texts: List of text documents to embed

        Returns:
            List of embedding vectors
        """
        embeddings = self.model.encode(texts)
        return embeddings.tolist()

    def get_embedding_dimension(self) -> int:
        """Get the dimension of the embedding vectors

        Returns:
            The dimension of the embedding vectors
        """
        return self.model.get_sentence_embedding_dimension()

    def get_model_name(self) -> str:
        """Get the name of the embedding model

        Returns:
            The name of the embedding model
        """
        return ModelRegistry.MODELS.get(self.model_version, "Unknown Model")
