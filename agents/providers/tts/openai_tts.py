"""
OpenAI TTS provider implementation.
"""

from typing import AsyncIterator
import io
from openai import AsyncOpenAI

from ..base import (
    BaseTTSProvider,
    TTSConfig,
    TTSResult,
    ProviderType
)


class OpenAITTSProvider(BaseTTSProvider):
    """OpenAI TTS implementation."""

    def __init__(self, config: TTSConfig):
        super().__init__(config)
        self.client: AsyncOpenAI = None
        self._model = config.model or "tts-1"  # tts-1 or tts-1-hd

    async def initialize(self) -> None:
        """Initialize OpenAI client."""
        api_key = self.config.metadata.get("api_key")
        if not api_key:
            raise ValueError("OpenAI API key is required")
        
        self.client = AsyncOpenAI(api_key=api_key)
        self._initialized = True

    async def synthesize(self, text: str) -> TTSResult:
        """Synthesize speech from text."""
        response = await self.client.audio.speech.create(
            model=self._model,
            voice=self.config.voice,
            input=text,
            speed=self.config.speed,
            response_format="pcm" if self.config.audio_encoding == "pcm" else "mp3"
        )
        
        # Read all audio data
        audio_data = b""
        async for chunk in response.iter_bytes():
            audio_data += chunk
        
        return TTSResult(
            audio_data=audio_data,
            sample_rate=self.config.sample_rate,
            metadata={
                "model": self._model,
                "voice": self.config.voice,
                "text_length": len(text)
            }
        )

    async def synthesize_stream(
        self, text: str
    ) -> AsyncIterator[bytes]:
        """Synthesize speech with streaming output."""
        response = await self.client.audio.speech.create(
            model=self._model,
            voice=self.config.voice,
            input=text,
            speed=self.config.speed,
            response_format="pcm" if self.config.audio_encoding == "pcm" else "mp3"
        )
        
        async for chunk in response.iter_bytes():
            yield chunk

    async def cleanup(self) -> None:
        """Clean up resources."""
        if self.client:
            await self.client.close()
        self._initialized = False

    def get_available_voices(self):
        """Return list of OpenAI TTS voices."""
        return ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
