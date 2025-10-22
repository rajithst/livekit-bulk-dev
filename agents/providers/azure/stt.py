"""
Azure OpenAI STT provider implementation.
"""

import logging
from typing import AsyncIterable, AsyncIterator, Optional
from livekit import rtc
from livekit.plugins import openai as lk_openai
from livekit.agents import stt
from ..base import BaseSTTProvider, STTConfig, STTResult

logger = logging.getLogger(__name__)

class AzureSTTProvider(BaseSTTProvider):
    """
    Azure OpenAI STT provider using LiveKit's plugin system.
    """

    def __init__(self, config: STTConfig):
        super().__init__(config)
        self.stt = None

    async def initialize(self) -> None:
        """Initialize the STT provider."""
        try:
            # Use LiveKit's built-in Azure OpenAI plugin
            self.stt = lk_openai.STT.with_azure(
                api_version=self.config.metadata.get("api_version", "2023-05-15"),
                azure_endpoint=self.config.metadata["azure_endpoint"],
                azure_deployment=self.config.metadata["azure_deployment"],
                api_key=self.config.metadata["api_key"]
            )
            logger.info("Azure STT provider initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Azure STT: {str(e)}", exc_info=True)
            raise

    async def transcribe_file(self, audio_file_path: str) -> STTResult:
        """Transcribe an audio file."""
        try:
            with open(audio_file_path, 'rb') as audio_file:
                audio_data = audio_file.read()
                
            result = await self.stt.transcribe_file(
                audio_data,
                language=self.config.language,
                model=self.config.model
            )
            
            return STTResult(
                text=result.text,
                confidence=result.confidence,
                is_final=True,
                language=result.language
            )
            
        except Exception as e:
            logger.error(f"File transcription failed: {str(e)}", exc_info=True)
            raise

    async def transcribe_stream(
        self,
        audio_stream: AsyncIterator[bytes]
    ) -> AsyncIterator[STTResult]:
        """Transcribe audio stream in real-time."""
        try:
            async for event in self.stt.transcribe(
                audio_stream,
                language=self.config.language,
                model=self.config.model
            ):
                yield STTResult(
                    text=event.text,
                    confidence=event.confidence,
                    is_final=event.is_final,
                    language=event.language
                )
        except Exception as e:
            logger.error(f"STT transcription failed: {str(e)}", exc_info=True)
            raise

    async def cleanup(self) -> None:
        """Clean up any resources."""
        if self.stt:
            await self.stt.aclose()