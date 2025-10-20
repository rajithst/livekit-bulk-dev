"""
Base abstract classes for pluggable AI providers.
This module defines the interfaces that all provider implementations must follow.
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum


class ProviderType(Enum):
    """Supported AI provider types."""
    OPENAI = "openai"
    AZURE = "azure"
    AWS = "aws"
    GOOGLE = "google"
    ANTHROPIC = "anthropic"
    DEEPGRAM = "deepgram"
    ELEVENLABS = "elevenlabs"


@dataclass
class STTConfig:
    """Configuration for Speech-to-Text providers."""
    provider: ProviderType
    language: str = "en-US"
    model: Optional[str] = None
    sample_rate: int = 16000
    enable_interim_results: bool = True
    profanity_filter: bool = False
    custom_vocabulary: Optional[List[str]] = None
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
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    system_prompt: Optional[str] = None
    streaming: bool = True
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
    speed: float = 1.0
    pitch: float = 1.0
    sample_rate: int = 24000
    audio_encoding: str = "pcm"
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class STTResult:
    """Result from Speech-to-Text processing."""
    text: str
    confidence: float
    is_final: bool
    language: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class LLMMessage:
    """Message format for LLM conversations."""
    role: str  # system, user, assistant
    content: str
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class LLMResponse:
    """Response from LLM processing."""
    content: str
    finish_reason: Optional[str] = None
    tokens_used: Optional[int] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class TTSResult:
    """Result from Text-to-Speech processing."""
    audio_data: bytes
    sample_rate: int
    duration_ms: Optional[int] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BaseSTTProvider(ABC):
    """
    Abstract base class for Speech-to-Text providers.
    All STT implementations must inherit from this class.
    """

    def __init__(self, config: STTConfig):
        self.config = config
        self._initialized = False

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the provider (e.g., authenticate, load models)."""
        pass

    @abstractmethod
    async def transcribe_stream(
        self, audio_stream: AsyncIterator[bytes]
    ) -> AsyncIterator[STTResult]:
        """
        Transcribe audio stream in real-time.
        
        Args:
            audio_stream: Async iterator of audio bytes
            
        Yields:
            STTResult objects with transcription results
        """
        pass

    @abstractmethod
    async def transcribe_file(self, audio_file_path: str) -> STTResult:
        """
        Transcribe an audio file.
        
        Args:
            audio_file_path: Path to the audio file
            
        Returns:
            STTResult with final transcription
        """
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up resources."""
        pass

    async def health_check(self) -> bool:
        """Check if the provider is healthy and ready."""
        return self._initialized

    def get_supported_languages(self) -> List[str]:
        """Return list of supported language codes."""
        return ["en-US"]  # Override in implementations


class BaseLLMProvider(ABC):
    """
    Abstract base class for Large Language Model providers.
    All LLM implementations must inherit from this class.
    """

    def __init__(self, config: LLMConfig):
        self.config = config
        self._initialized = False

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the provider."""
        pass

    @abstractmethod
    async def generate(
        self,
        messages: List[LLMMessage],
        **kwargs
    ) -> LLMResponse:
        """
        Generate a response from the LLM.
        
        Args:
            messages: List of conversation messages
            **kwargs: Additional parameters for generation
            
        Returns:
            LLMResponse with generated content
        """
        pass

    @abstractmethod
    async def generate_stream(
        self,
        messages: List[LLMMessage],
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Generate a streaming response from the LLM.
        
        Args:
            messages: List of conversation messages
            **kwargs: Additional parameters for generation
            
        Yields:
            Chunks of generated text
        """
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up resources."""
        pass

    async def health_check(self) -> bool:
        """Check if the provider is healthy and ready."""
        return self._initialized

    def get_model_info(self) -> Dict[str, Any]:
        """Return information about the current model."""
        return {
            "provider": self.config.provider.value,
            "model": self.config.model
        }


class BaseTTSProvider(ABC):
    """
    Abstract base class for Text-to-Speech providers.
    All TTS implementations must inherit from this class.
    """

    def __init__(self, config: TTSConfig):
        self.config = config
        self._initialized = False

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the provider."""
        pass

    @abstractmethod
    async def synthesize(self, text: str) -> TTSResult:
        """
        Synthesize speech from text.
        
        Args:
            text: Text to synthesize
            
        Returns:
            TTSResult with audio data
        """
        pass

    @abstractmethod
    async def synthesize_stream(
        self, text: str
    ) -> AsyncIterator[bytes]:
        """
        Synthesize speech with streaming output.
        
        Args:
            text: Text to synthesize
            
        Yields:
            Chunks of audio data
        """
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up resources."""
        pass

    async def health_check(self) -> bool:
        """Check if the provider is healthy and ready."""
        return self._initialized

    def get_available_voices(self) -> List[str]:
        """Return list of available voice IDs."""
        return []  # Override in implementations


class ProviderFactory:
    """
    Factory for creating provider instances.
    Supports registration of custom providers at runtime.
    """

    _stt_providers: Dict[ProviderType, type] = {}
    _llm_providers: Dict[ProviderType, type] = {}
    _tts_providers: Dict[ProviderType, type] = {}

    @classmethod
    def register_stt_provider(
        cls,
        provider_type: ProviderType,
        provider_class: type
    ) -> None:
        """Register a custom STT provider."""
        if not issubclass(provider_class, BaseSTTProvider):
            raise TypeError(
                f"{provider_class} must inherit from BaseSTTProvider"
            )
        cls._stt_providers[provider_type] = provider_class

    @classmethod
    def register_llm_provider(
        cls,
        provider_type: ProviderType,
        provider_class: type
    ) -> None:
        """Register a custom LLM provider."""
        if not issubclass(provider_class, BaseLLMProvider):
            raise TypeError(
                f"{provider_class} must inherit from BaseLLMProvider"
            )
        cls._llm_providers[provider_type] = provider_class

    @classmethod
    def register_tts_provider(
        cls,
        provider_type: ProviderType,
        provider_class: type
    ) -> None:
        """Register a custom TTS provider."""
        if not issubclass(provider_class, BaseTTSProvider):
            raise TypeError(
                f"{provider_class} must inherit from BaseTTSProvider"
            )
        cls._tts_providers[provider_type] = provider_class

    @classmethod
    def create_stt_provider(cls, config: STTConfig) -> BaseSTTProvider:
        """Create an STT provider instance."""
        provider_class = cls._stt_providers.get(config.provider)
        if not provider_class:
            raise ValueError(
                f"STT provider {config.provider} not registered"
            )
        return provider_class(config)

    @classmethod
    def create_llm_provider(cls, config: LLMConfig) -> BaseLLMProvider:
        """Create an LLM provider instance."""
        provider_class = cls._llm_providers.get(config.provider)
        if not provider_class:
            raise ValueError(
                f"LLM provider {config.provider} not registered"
            )
        return provider_class(config)

    @classmethod
    def create_tts_provider(cls, config: TTSConfig) -> BaseTTSProvider:
        """Create a TTS provider instance."""
        provider_class = cls._tts_providers.get(config.provider)
        if not provider_class:
            raise ValueError(
                f"TTS provider {config.provider} not registered"
            )
        return provider_class(config)
