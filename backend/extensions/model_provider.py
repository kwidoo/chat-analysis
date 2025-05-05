"""
Model Provider Extension

This module defines the BaseModelProvider interface and registerable provider classes,
implementing the Open/Closed Principle (O in SOLID).
"""
import logging
from typing import Dict, List, Any, Optional, Type

from interfaces.embedding import IModelProvider, IEmbeddingService


class ModelProviderRegistry:
    """Registry for model providers that allows dynamic registration"""

    _providers: Dict[str, Type['BaseModelProvider']] = {}
    _logger = logging.getLogger(__name__)

    @classmethod
    def register_provider(cls, provider_class: Type['BaseModelProvider']) -> None:
        """Register a model provider

        Args:
            provider_class: The model provider class to register
        """
        provider_name = provider_class.get_provider_name()
        cls._providers[provider_name] = provider_class
        cls._logger.info(f"Registered model provider: {provider_name}")

    @classmethod
    def get_provider(cls, provider_name: str) -> Optional['BaseModelProvider']:
        """Get a model provider by name

        Args:
            provider_name: The name of the provider

        Returns:
            The model provider instance or None if not found
        """
        provider_class = cls._providers.get(provider_name)
        if not provider_class:
            cls._logger.warning(f"Model provider not found: {provider_name}")
            return None

        return provider_class()

    @classmethod
    def get_available_providers(cls) -> List[str]:
        """Get a list of available model providers

        Returns:
            List of provider names
        """
        return list(cls._providers.keys())


class BaseModelProvider(IModelProvider):
    """Base class for model providers"""

    @classmethod
    def get_provider_name(cls) -> str:
        """Get the name of this model provider

        Returns:
            The provider name
        """
        # Default implementation returns the class name without "Provider"
        name = cls.__name__.replace("Provider", "")
        return name.lower()

    def get_embedding_service(self, model_name: str,
                             distributed_client: Optional[Any] = None) -> IEmbeddingService:
        """Get an embedding service for a model

        This method should be implemented by subclasses.

        Args:
            model_name: The name of the model
            distributed_client: Optional client for distributed processing

        Returns:
            An embedding service for the model

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement get_embedding_service")

    def get_available_models(self) -> List[str]:
        """Get the list of available models from this provider

        This method should be implemented by subclasses.

        Returns:
            List of model names

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement get_available_models")
