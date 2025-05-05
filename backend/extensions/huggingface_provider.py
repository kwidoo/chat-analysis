"""
HuggingFace Model Provider

This module provides an implementation of the BaseModelProvider for HuggingFace models,
supporting the Open/Closed Principle by allowing new models without modifying existing code.
"""
import logging
from typing import Dict, List, Any, Optional

from interfaces.embedding import IEmbeddingService
from extensions.model_provider import BaseModelProvider, ModelProviderRegistry


class HuggingFaceEmbeddingService(IEmbeddingService):
    """Implementation of the embedding service interface using HuggingFace models"""

    # Predefined model dimensions
    MODEL_DIMENSIONS = {
        'sentence-transformers/all-mpnet-base-v2': 768,
        'sentence-transformers/all-MiniLM-L6-v2': 384,
        'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2': 384,
        'sentence-transformers/paraphrase-albert-small-v2': 768,
    }

    def __init__(self, model_name: str, distributed_client: Optional[Any] = None):
        """Initialize the HuggingFace embedding service

        Args:
            model_name: The name of the HuggingFace model
            distributed_client: Optional client for distributed processing
        """
        self.model_name = model_name
        self.distributed_client = distributed_client
        self.logger = logging.getLogger(__name__)

        # Load the model
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
            self.logger.info(f"Loaded HuggingFace model: {model_name}")
        except Exception as e:
            self.logger.error(f"Failed to load HuggingFace model {model_name}: {e}")
            raise

    def embed_document(self, text: str) -> List[float]:
        """Generate an embedding for a document

        Args:
            text: The text to embed

        Returns:
            The embedding vector
        """
        # Generate the embedding
        try:
            embedding = self.model.encode(text)
            return embedding.tolist()
        except Exception as e:
            self.logger.error(f"Error generating embedding with {self.model_name}: {e}")
            raise

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of documents

        Args:
            texts: List of text documents to embed

        Returns:
            List of embedding vectors
        """
        try:
            # Use distributed client if available
            if self.distributed_client and hasattr(self.distributed_client, 'submit'):
                self.logger.info(f"Using distributed client for batch embedding of {len(texts)} documents")

                # Split the batch into smaller chunks
                chunk_size = 10  # Adjust based on memory constraints
                chunks = [texts[i:i + chunk_size] for i in range(0, len(texts), chunk_size)]

                # Submit each chunk as a task
                futures = []
                for chunk in chunks:
                    future = self.distributed_client.submit(self._embed_chunk, chunk)
                    futures.append(future)

                # Gather results
                results = []
                for future in futures:
                    chunk_results = future.result()
                    results.extend(chunk_results)

                return results
            else:
                # Generate embeddings locally
                embeddings = self.model.encode(texts)
                return embeddings.tolist()
        except Exception as e:
            self.logger.error(f"Error generating batch embeddings with {self.model_name}: {e}")
            raise

    def _embed_chunk(self, texts: List[str]) -> List[List[float]]:
        """Helper method for distributed embedding of chunks

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
        # Return from predefined dimensions if available
        if self.model_name in self.MODEL_DIMENSIONS:
            return self.MODEL_DIMENSIONS[self.model_name]

        # Or query the model
        try:
            return self.model.get_sentence_embedding_dimension()
        except:
            # Generate a sample embedding to determine dimension
            sample_embedding = self.embed_document("Sample text for dimension detection")
            return len(sample_embedding)

    def get_model_name(self) -> str:
        """Get the name of the embedding model

        Returns:
            The name of the embedding model
        """
        return self.model_name


class HuggingFaceProvider(BaseModelProvider):
    """HuggingFace implementation of the model provider interface"""

    # Available models
    AVAILABLE_MODELS = {
        'mpnet-base': 'sentence-transformers/all-mpnet-base-v2',
        'minilm-l6': 'sentence-transformers/all-MiniLM-L6-v2',
        'multilingual-minilm': 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
        'albert-small': 'sentence-transformers/paraphrase-albert-small-v2',
    }

    @classmethod
    def get_provider_name(cls) -> str:
        """Get the name of this model provider

        Returns:
            The provider name
        """
        return "huggingface"

    def get_embedding_service(self, model_name: str,
                             distributed_client: Optional[Any] = None) -> IEmbeddingService:
        """Get an embedding service for a model

        Args:
            model_name: The name of the model
            distributed_client: Optional client for distributed processing

        Returns:
            An embedding service for the model
        """
        # Translate friendly model names to actual HuggingFace model names
        hf_model_name = self.AVAILABLE_MODELS.get(model_name, model_name)

        # Create and return the embedding service
        return HuggingFaceEmbeddingService(hf_model_name, distributed_client)

    def get_available_models(self) -> List[str]:
        """Get the list of available models from this provider

        Returns:
            List of model names
        """
        return list(self.AVAILABLE_MODELS.keys())


# Register the provider with the registry
ModelProviderRegistry.register_provider(HuggingFaceProvider)
