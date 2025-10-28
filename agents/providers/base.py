"""
Base classes for pluggable AI providers.

The provider factory creates LiveKit plugin instances directly.
"""

from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum


class ProviderType(Enum):
    """Supported AI provider types."""
    OPENAI = "openai"
    AZURE = "azure"
    CUSTOM_HTTP = "custom_http"  # For HTTP-based custom endpoints
    CUSTOM_WS = "custom_ws"      # For WebSocket-based custom endpoints
    UNKNOWN = "unknown"


@dataclass
class STTConfig:
    """Configuration for Speech-to-Text providers."""
    provider: ProviderType
    language: str = "en-US"
    model: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class LLMConfig:
    """Configuration for Large Language Model providers."""
    provider: ProviderType
    model: str
    temperature: float = 0.7
    max_tokens: int = 150
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class TTSConfig:
    """Configuration for Text-to-Speech providers."""
    provider: ProviderType
    voice: str
    model: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class LLMMessage:
    """Message format for LLM conversations."""
    role: str
    content: str
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ProviderFactory:
    """Factory for creating LiveKit plugin instances."""
    
    _stt_registry: Dict[ProviderType, Callable[[STTConfig], Any]] = {}
    _llm_registry: Dict[ProviderType, Callable[[LLMConfig], Any]] = {}
    _tts_registry: Dict[ProviderType, Callable[[TTSConfig], Any]] = {}

    @classmethod
    def register_stt_provider(cls, provider_type: ProviderType, factory_func: Callable[[STTConfig], Any]) -> None:
        cls._stt_registry[provider_type] = factory_func

    @classmethod
    def register_llm_provider(cls, provider_type: ProviderType, factory_func: Callable[[LLMConfig], Any]) -> None:
        cls._llm_registry[provider_type] = factory_func

    @classmethod
    def register_tts_provider(cls, provider_type: ProviderType, factory_func: Callable[[TTSConfig], Any]) -> None:
        cls._tts_registry[provider_type] = factory_func

    @classmethod
    def create_stt(cls, config: STTConfig) -> Any:
        factory_func = cls._stt_registry.get(config.provider)
        if not factory_func:
            raise ValueError(f"No STT provider registered for {config.provider}")
        return factory_func(config)

    @classmethod
    def create_llm(cls, config: LLMConfig) -> Any:
        factory_func = cls._llm_registry.get(config.provider)
        if not factory_func:
            raise ValueError(f"No LLM provider registered for {config.provider}")
        return factory_func(config)

    @classmethod
    def create_tts(cls, config: TTSConfig) -> Any:
        factory_func = cls._tts_registry.get(config.provider)
        if not factory_func:
            raise ValueError(f"No TTS provider registered for {config.provider}")
        return factory_func(config)
