"""
Azure OpenAI provider factory for initializing TTS, STT, and LLM services.
"""

import logging
from typing import Dict, Optional, Type, Union
from agents.providers.azure.tts import AzureTTSProvider
from agents.providers.azure.stt import AzureSTTProvider
from agents.providers.azure.llm import AzureLLMProvider

logger = logging.getLogger(__name__)

class AzureProviderFactory:
    """Factory for creating and managing Azure OpenAI service providers."""

    PROVIDER_TYPES = {
        "tts": AzureTTSProvider,
        "stt": AzureSTTProvider,
        "llm": AzureLLMProvider
    }

    @classmethod
    async def create_provider(
        cls,
        provider_type: str,
        config: Dict
    ) -> Union[AzureTTSProvider, AzureSTTProvider, AzureLLMProvider]:
        """
        Create and initialize an Azure provider instance.
        
        Args:
            provider_type: Type of provider ("tts", "stt", or "llm")
            config: Provider configuration dictionary
            
        Returns:
            Initialized provider instance
        
        Raises:
            ValueError: If provider type is invalid
            RuntimeError: If provider initialization fails
        """
        if provider_type not in cls.PROVIDER_TYPES:
            raise ValueError(f"Invalid provider type: {provider_type}")
            
        try:
            provider_class = cls.PROVIDER_TYPES[provider_type]
            provider = provider_class(config)
            await provider.initialize()
            return provider
            
        except Exception as e:
            logger.error(
                f"Failed to initialize {provider_type} provider: {str(e)}",
                exc_info=True
            )
            raise RuntimeError(f"Provider initialization failed: {str(e)}")

    @classmethod
    async def cleanup_provider(cls, provider: Union[AzureTTSProvider, AzureSTTProvider, AzureLLMProvider]) -> None:
        """
        Clean up provider resources.
        
        Args:
            provider: Provider instance to clean up
        """
        try:
            await provider.cleanup()
        except Exception as e:
            logger.error(f"Provider cleanup failed: {str(e)}", exc_info=True)