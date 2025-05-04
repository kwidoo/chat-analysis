import pytest
import numpy as np
import os
from services.embedding_service import SentenceTransformerEmbeddingService, ModelRegistry


class TestEmbeddingService:
    def test_encode(self):
        """Test that encoding produces embeddings with correct dimensions"""
        # Use a small model for faster testing
        service = SentenceTransformerEmbeddingService('all-MiniLM-L6-v2')
        texts = ["This is a test sentence", "Another test sentence"]

        # Generate embeddings
        embeddings = service.encode(texts)

        # Check dimensions
        assert isinstance(embeddings, np.ndarray)
        assert embeddings.shape[0] == len(texts)
        assert embeddings.shape[1] == service.get_embedding_dimension()

    def test_empty_input(self):
        """Test that encoding empty input returns empty array"""
        service = SentenceTransformerEmbeddingService('all-MiniLM-L6-v2')
        embeddings = service.encode([])

        assert isinstance(embeddings, np.ndarray)
        assert embeddings.size == 0

    def test_get_embedding_dimension(self):
        """Test that embedding dimension is returned correctly"""
        service = SentenceTransformerEmbeddingService('all-MiniLM-L6-v2')

        # MiniLM model dimension should be 384
        assert service.get_embedding_dimension() == 384


class TestModelRegistry:
    def test_get_model_path(self):
        """Test that model paths are returned correctly"""
        # Check valid model versions
        assert ModelRegistry.get_model_path('v1') == 'all-MiniLM-L6-v2'
        assert ModelRegistry.get_model_path('v2') == 'sentence-transformers/all-mpnet-base-v2'

    def test_invalid_model_version(self):
        """Test that invalid model versions raise ValueError"""
        with pytest.raises(ValueError):
            ModelRegistry.get_model_path('non_existent')

    def test_get_available_models(self):
        """Test that available models are returned correctly"""
        models = ModelRegistry.get_available_models()

        assert isinstance(models, dict)
        assert 'v1' in models
        assert 'v2' in models

    def test_get_embedding_service(self):
        """Test factory method for creating embedding service"""
        service = ModelRegistry.get_embedding_service('v1')

        assert isinstance(service, SentenceTransformerEmbeddingService)
        assert service.model_name == 'all-MiniLM-L6-v2'
