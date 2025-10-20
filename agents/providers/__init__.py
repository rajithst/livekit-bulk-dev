"""
Provider registry - automatically registers all available providers.
"""

from .base import ProviderFactory, ProviderType

# Import all provider implementations
from .stt.openai_stt import OpenAISTTProvider
from .stt.azure_stt import AzureSTTProvider
from .llm.openai_llm import OpenAILLMProvider
from .tts.openai_tts import OpenAITTSProvider


def register_all_providers():
    """Register all available providers with the factory."""
    
    # Register STT providers
    ProviderFactory.register_stt_provider(
        ProviderType.OPENAI,
        OpenAISTTProvider
    )
    ProviderFactory.register_stt_provider(
        ProviderType.AZURE,
        AzureSTTProvider
    )
    
    # Register LLM providers
    ProviderFactory.register_llm_provider(
        ProviderType.OPENAI,
        OpenAILLMProvider
    )
    
    # Register TTS providers
    ProviderFactory.register_tts_provider(
        ProviderType.OPENAI,
        OpenAITTSProvider
    )


# Auto-register on import
register_all_providers()


__all__ = [
    'ProviderFactory',
    'ProviderType',
    'register_all_providers'
]
