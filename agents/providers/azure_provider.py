"""
Azure OpenAI provider factories that return LiveKit plugin instances.
"""

from livekit.plugins import openai as lk_openai
from .base import STTConfig, LLMConfig, TTSConfig


class AzureProviderFactory:
    """Factory class for creating Azure OpenAI plugin instances."""
    
    @staticmethod
    def create_stt(config: STTConfig):
        """Create Azure OpenAI STT plugin instance for LiveKit."""
        return lk_openai.STT.with_azure(
            model=config.model or "whisper-1",
            azure_endpoint=config.metadata["azure_endpoint"],
            azure_deployment=config.metadata["azure_deployment"],
            api_version=config.metadata.get("api_version", "2024-02-15-preview"),
            api_key=config.metadata["api_key"]
        )
    
    @staticmethod
    def create_llm(config: LLMConfig):
        """Create Azure OpenAI LLM plugin instance for LiveKit."""
        return lk_openai.LLM.with_azure(
            model=config.model,
            azure_endpoint=config.metadata["azure_endpoint"],
            azure_deployment=config.metadata["azure_deployment"],
            api_version=config.metadata.get("api_version", "2024-02-15-preview"),
            api_key=config.metadata["api_key"],
            temperature=config.temperature
        )
    
    @staticmethod
    def create_tts(config: TTSConfig):
        """Create Azure OpenAI TTS plugin instance for LiveKit."""
        return lk_openai.TTS.with_azure(
            model=config.model or "tts-1",
            voice=config.voice,
            azure_endpoint=config.metadata["azure_endpoint"],
            azure_deployment=config.metadata["azure_deployment"],
            api_version=config.metadata.get("api_version", "2024-02-15-preview"),
            api_key=config.metadata["api_key"]
        )


# Convenience functions for backward compatibility
def create_azure_stt(config: STTConfig):
    """Create Azure OpenAI STT plugin instance for LiveKit."""
    return AzureProviderFactory.create_stt(config)


def create_azure_llm(config: LLMConfig):
    """Create Azure OpenAI LLM plugin instance for LiveKit."""
    return AzureProviderFactory.create_llm(config)


def create_azure_tts(config: TTSConfig):
    """Create Azure OpenAI TTS plugin instance for LiveKit."""
    return AzureProviderFactory.create_tts(config)
