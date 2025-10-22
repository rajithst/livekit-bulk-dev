"""
Azure OpenAI Text-to-Speech provider implementation.
"""

import logging
from typing import AsyncIterable, AsyncIterator, Optional
from livekit import rtc
from livekit.plugins import openai as lk_openai
from ..base import BaseTTSProvider, TTSConfig, TTSResult

logger = logging.getLogger(__name__)

class AzureTTSProvider(BaseTTSProvider):
    """
    Azure OpenAI TTS provider using LiveKit's plugin system.
    """

    def __init__(self, config: TTSConfig):
        super().__init__(config)
        self.tts = None

    async def initialize(self) -> None:
        """Initialize the TTS provider."""
        try:
            # Use LiveKit's built-in Azure OpenAI plugin
            self.tts = lk_openai.TTS.with_azure(
                api_version=self.config.metadata.get("api_version", "2023-05-15"),
                azure_endpoint=self.config.metadata["azure_endpoint"],
                azure_deployment=self.config.metadata["azure_deployment"],
                api_key=self.config.metadata["api_key"]
            )
            logger.info("Azure TTS provider initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Azure TTS: {str(e)}", exc_info=True)
            raise

    async def synthesize(self, text: str) -> TTSResult:
        """Synthesize speech from text."""
        if not text.strip():
            raise ValueError("Text cannot be empty")

        try:
            audio_data = []
            duration_ms = 0
            
            async for frame in self.tts.synthesize(
                text,
                voice=self.config.voice,
                model=self.config.model
            ):
                audio_data.append(frame.audio_data)
                duration_ms += frame.duration_ms
                
            return TTSResult(
                audio_data=b''.join(audio_data),
                sample_rate=self.config.sample_rate,
                duration_ms=duration_ms
            )
        except Exception as e:
            logger.error(f"TTS synthesis failed: {str(e)}", exc_info=True)
            raise

    async def synthesize_stream(self, text: str) -> AsyncIterator[bytes]:
        """Synthesize speech with streaming output."""
        if not text.strip():
            raise ValueError("Text cannot be empty")

        try:
            async for frame in self.tts.synthesize(
                text,
                voice=self.config.voice,
                model=self.config.model
            ):
                yield frame.audio_data
        except Exception as e:
            logger.error(f"TTS synthesis failed: {str(e)}", exc_info=True)
            raise

    async def cleanup(self) -> None:
        """Clean up any resources."""
        if self.tts:
            await self.tts.aclose()