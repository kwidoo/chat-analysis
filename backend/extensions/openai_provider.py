"""
OpenAI Model Provider

This module provides an implementation of the BaseModelProvider for OpenAI models,
supporting the Open/Closed Principle by allowing new models without modifying existing code.
"""
import logging
import os
import time
from typing import Dict, List, Any, Optional

from interfaces.embedding import IEmbeddingService
from extensions.model_provider import BaseModelProvider, ModelProviderRegistry


class OpenAIEmbeddingService(IEmbeddingService):
    """Implementation of the embedding service interface using OpenAI models"""

    # Predefined model dimensions
    MODEL_DIMENSIONS = {
        'text-embedding-ada-002': 1536,
        'text-embedding-3-small': 1536,
        'text-embedding-3-large': 3072
    }

    def __init__(self, model_name: str, distributed_client: Optional[Any] = None):
        """Initialize the OpenAI embedding service

        Args:
            model_name: The name of the OpenAI model
            distributed_client: Optional client for distributed processing
        """
        self.model_name = model_name
        self.distributed_client = distributed_client
        self.logger = logging.getLogger(__name__)

        # Check for OpenAI API key
        self.api_key = os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            self.logger.warning("OPENAI_API_KEY environment variable not set")

        # Import and initialize OpenAI client
        try:
            import openai
            self.client = openai.OpenAI(api_key=self.api_key)
            self.logger.info(f"Initialized OpenAI client for model: {model_name}")
        except Exception as e:
            self.logger.error(f"Failed to initialize OpenAI client: {e}")
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
            # Rate limiting: basic sleep to avoid hitting OpenAI rate limits
            time.sleep(0.1)

            response = self.client.embeddings.create(
                input=text,
                model=self.model_name
            )

            # Extract the embedding from the response
            embedding = response.data[0].embedding
            return embedding
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

                # Split the batch into smaller chunks to avoid rate limits
                chunk_size = 5  # Small batch size due to rate limits
                chunks = [texts[i:i + chunk_size] for i in range(0, len(texts), chunk_size)]

                # Submit each chunk as a task
                futures = []
                for chunk in chunks:
                    future = self.distributed_client.submit(self._embed_chunk, chunk)
                    futures.append(future)
                    # Sleep to avoid rate limits
                    time.sleep(1)

                # Gather results
                results = []
                for future in futures:
                    chunk_results = future.result()
                    results.extend(chunk_results)

                return results
            else:
                # Send a batch request to OpenAI
                # Note: Limited by OpenAI's rate limits and max tokens
                response = self.client.embeddings.create(
                    input=texts,
                    model=self.model_name
                )

                # Sort embeddings by index (OpenAI preserves order but just to be safe)
                sorted_embeddings = sorted(response.data, key=lambda x: x.index)
                return [item.embedding for item in sorted_embeddings]

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
        response = self.client.embeddings.create(
            input=texts,
            model=self.model_name
        )

        # Sort embeddings by index
        sorted_embeddings = sorted(response.data, key=lambda x: x.index)
        return [item.embedding for item in sorted_embeddings]

    def get_embedding_dimension(self) -> int:
        """Get the dimension of the embedding vectors

        Returns:
            The dimension of the embedding vectors
        """
        # Return from predefined dimensions if available
        if self.model_name in self.MODEL_DIMENSIONS:
            return self.MODEL_DIMENSIONS[self.model_name]

        # Generate a sample embedding to determine dimension
        sample_embedding = self.embed_document("Sample text for dimension detection")
        return len(sample_embedding)

    def get_model_name(self) -> str:
        """Get the name of the embedding model

        Returns:
            The name of the embedding model
        """
        return self.model_name


class OpenAIProvider(BaseModelProvider):
    """OpenAI implementation of the model provider interface"""

    # Available models
    AVAILABLE_MODELS = {
        'ada': 'text-embedding-ada-002',
        'embedding-3-small': 'text-embedding-3-small',
        'embedding-3-large': 'text-embedding-3-large'
    }

    @classmethod
    def get_provider_name(cls) -> str:
        """Get the name of this model provider

        Returns:
            The provider name
        """
        return "openai"

    def get_embedding_service(self, model_name: str,
                             distributed_client: Optional[Any] = None) -> IEmbeddingService:
        """Get an embedding service for a model

        Args:
            model_name: The name of the model
            distributed_client: Optional client for distributed processing

        Returns:
            An embedding service for the model
        """
        # Translate friendly model names to actual OpenAI model names
        openai_model_name = self.AVAILABLE_MODELS.get(model_name, model_name)

        # Create and return the embedding service
        return OpenAIEmbeddingService(openai_model_name, distributed_client)

    def get_available_models(self) -> List[str]:
        """Get the list of available models from this provider

        Returns:
            List of model names
        """
        return list(self.AVAILABLE_MODELS.keys())


# Register the provider with the registry
ModelProviderRegistry.register_provider(OpenAIProvider)
