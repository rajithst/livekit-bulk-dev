"""
Provider registry - automatically registers all available providers.

Each provider factory function returns a LiveKit plugin instance or adapter that can be
passed directly to AgentSession. LiveKit handles all audio streaming and buffering.

Supports both native LiveKit plugins and custom HTTP/WebSocket endpoints.
"""

from .base import ProviderFactory, ProviderType
from .openai_provider import OpenAIProviderFactory
from .azure_provider import AzureProviderFactory
from .custom_provider import CustomProviderFactory


def register_all_providers():
    """Register all available providers with the factory."""
    
    # Register OpenAI providers (using class methods)
    ProviderFactory.register_stt_provider(ProviderType.OPENAI, OpenAIProviderFactory.create_stt)
    ProviderFactory.register_llm_provider(ProviderType.OPENAI, OpenAIProviderFactory.create_llm)
    ProviderFactory.register_tts_provider(ProviderType.OPENAI, OpenAIProviderFactory.create_tts)
    
    # Register Azure OpenAI providers (using class methods)
    ProviderFactory.register_stt_provider(ProviderType.AZURE, AzureProviderFactory.create_stt)
    ProviderFactory.register_llm_provider(ProviderType.AZURE, AzureProviderFactory.create_llm)
    ProviderFactory.register_tts_provider(ProviderType.AZURE, AzureProviderFactory.create_tts)
    
    # Register custom HTTP/WebSocket providers
    ProviderFactory.register_stt_provider(ProviderType.CUSTOM_HTTP, CustomProviderFactory.create_http_stt)
    ProviderFactory.register_stt_provider(ProviderType.CUSTOM_WS, CustomProviderFactory.create_websocket_stt)


# Auto-register on import
register_all_providers()


__all__ = [
    'ProviderFactory',
    'ProviderType',
    'OpenAIProviderFactory',
    'AzureProviderFactory',
    'CustomProviderFactory',
    'register_all_providers'
]
