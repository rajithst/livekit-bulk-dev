"""
OpenAI Whisper Speech-to-Text provider implementation.
"""

import asyncio
import io
from typing import AsyncIterator
import openai
from openai import AsyncOpenAI

from ..base import (
    BaseSTTProvider,
    STTConfig,
    STTResult,
    ProviderType
)


class OpenAISTTProvider(BaseSTTProvider):
    """OpenAI Whisper STT implementation."""

    def __init__(self, config: STTConfig):
        super().__init__(config)
        self.client: AsyncOpenAI = None
        self._model = config.model or "whisper-1"

    async def initialize(self) -> None:
        """Initialize OpenAI client."""
        api_key = self.config.metadata.get("api_key")
        if not api_key:
            raise ValueError("OpenAI API key is required")
        
        self.client = AsyncOpenAI(api_key=api_key)
        self._initialized = True

    async def transcribe_stream(
        self, audio_stream: AsyncIterator[bytes]
    ) -> AsyncIterator[STTResult]:
        """
        Transcribe audio stream using Whisper.
        Note: Whisper doesn't support true streaming, so we buffer chunks.
        """
        buffer = io.BytesIO()
        chunk_duration_ms = 2000  # Process every 2 seconds
        
        async for audio_chunk in audio_stream:
            buffer.write(audio_chunk)
            
            # Process when we have enough data
            if buffer.tell() > self.config.sample_rate * 2 * 2:  # ~2 seconds
                buffer.seek(0)
                
                try:
                    # Whisper API expects file-like object
                    buffer.name = "audio.wav"
                    
                    response = await self.client.audio.transcriptions.create(
                        model=self._model,
                        file=buffer,
                        language=self.config.language.split("-")[0],  # "en" from "en-US"
                        response_format="verbose_json"
                    )
                    
                    yield STTResult(
                        text=response.text,
                        confidence=1.0,  # Whisper doesn't provide confidence
                        is_final=False,  # Interim result
                        language=response.language,
                        metadata={
                            "duration": response.duration if hasattr(response, 'duration') else None
                        }
                    )
                    
                except Exception as e:
                    # Log error but continue processing
                    print(f"Error transcribing chunk: {e}")
                
                # Reset buffer
                buffer = io.BytesIO()
        
        # Process remaining data
        if buffer.tell() > 0:
            buffer.seek(0)
            buffer.name = "audio.wav"
            
            try:
                response = await self.client.audio.transcriptions.create(
                    model=self._model,
                    file=buffer,
                    language=self.config.language.split("-")[0],
                    response_format="verbose_json"
                )
                
                yield STTResult(
                    text=response.text,
                    confidence=1.0,
                    is_final=True,
                    language=response.language,
                    metadata={
                        "duration": response.duration if hasattr(response, 'duration') else None
                    }
                )
            except Exception as e:
                print(f"Error transcribing final chunk: {e}")

    async def transcribe_file(self, audio_file_path: str) -> STTResult:
        """Transcribe an audio file."""
        with open(audio_file_path, "rb") as audio_file:
            response = await self.client.audio.transcriptions.create(
                model=self._model,
                file=audio_file,
                language=self.config.language.split("-")[0],
                response_format="verbose_json"
            )
        
        return STTResult(
            text=response.text,
            confidence=1.0,
            is_final=True,
            language=response.language,
            metadata={
                "duration": response.duration if hasattr(response, 'duration') else None
            }
        )

    async def cleanup(self) -> None:
        """Clean up resources."""
        if self.client:
            await self.client.close()
        self._initialized = False

    def get_supported_languages(self):
        """Whisper supports 50+ languages."""
        return [
            "en", "es", "fr", "de", "it", "pt", "nl", "pl", "ru", "ja",
            "ko", "zh", "ar", "hi", "tr", "vi", "th", "id", "ms", "fil"
        ]
