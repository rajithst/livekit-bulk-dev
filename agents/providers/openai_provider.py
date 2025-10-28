"""
OpenAI provider factories that return LiveKit plugin instances.
"""

from livekit.plugins import openai as lk_openai
from .base import STTConfig, LLMConfig, TTSConfig


class OpenAIProviderFactory:
    """Factory class for creating OpenAI plugin instances."""
    
    @staticmethod
    def create_stt(config: STTConfig):
        """Create OpenAI STT plugin instance for LiveKit."""
        return lk_openai.STT(
            model=config.model or "whisper-1",
            language=config.language,
            api_key=config.metadata.get("api_key")
        )
    
    @staticmethod
    def create_llm(config: LLMConfig):
        """Create OpenAI LLM plugin instance for LiveKit."""
        return lk_openai.LLM(
            model=config.model,
            temperature=config.temperature,
            api_key=config.metadata.get("api_key")
        )
    
    @staticmethod
    def create_tts(config: TTSConfig):
        """Create OpenAI TTS plugin instance for LiveKit."""
        return lk_openai.TTS(
            model=config.model or "tts-1",
            voice=config.voice,
            api_key=config.metadata.get("api_key")
        )


# Convenience functions for backward compatibility
def create_openai_stt(config: STTConfig):
    """Create OpenAI STT plugin instance for LiveKit."""
    return OpenAIProviderFactory.create_stt(config)


def create_openai_llm(config: LLMConfig):
    """Create OpenAI LLM plugin instance for LiveKit."""
    return OpenAIProviderFactory.create_llm(config)


def create_openai_tts(config: TTSConfig):
    """Create OpenAI TTS plugin instance for LiveKit."""
    return OpenAIProviderFactory.create_tts(config)
