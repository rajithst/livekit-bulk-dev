"""
Azure Cognitive Services Speech-to-Text provider implementation.
"""

from typing import AsyncIterator, List
import asyncio
import azure.cognitiveservices.speech as speechsdk

from ..base import (
    BaseSTTProvider,
    STTConfig,
    STTResult,
    ProviderType
)


class AzureSTTProvider(BaseSTTProvider):
    """Azure Cognitive Services STT implementation."""

    def __init__(self, config: STTConfig):
        super().__init__(config)
        self.speech_config = None
        self._model = config.model or "default"

    async def initialize(self) -> None:
        """Initialize Azure Speech SDK."""
        subscription_key = self.config.metadata.get("subscription_key")
        region = self.config.metadata.get("region", "eastus")
        
        if not subscription_key:
            raise ValueError("Azure subscription key is required")
        
        self.speech_config = speechsdk.SpeechConfig(
            subscription=subscription_key,
            region=region
        )
        self.speech_config.speech_recognition_language = self.config.language
        
        # Enable interim results if configured
        if self.config.enable_interim_results:
            self.speech_config.set_property(
                speechsdk.PropertyId.SpeechServiceResponse_PostProcessingOption,
                "TrueText"
            )
        
        self._initialized = True

    async def transcribe_stream(
        self, audio_stream: AsyncIterator[bytes]
    ) -> AsyncIterator[STTResult]:
        """Transcribe audio stream using Azure Speech SDK."""
        
        # Create push stream
        stream = speechsdk.audio.PushAudioInputStream()
        audio_config = speechsdk.audio.AudioConfig(stream=stream)
        
        recognizer = speechsdk.SpeechRecognizer(
            speech_config=self.speech_config,
            audio_config=audio_config
        )
        
        results_queue = asyncio.Queue()
        done = asyncio.Event()
        
        def recognizing_cb(evt):
            """Callback for interim results."""
            if self.config.enable_interim_results:
                asyncio.create_task(
                    results_queue.put(
                        STTResult(
                            text=evt.result.text,
                            confidence=0.0,  # Interim doesn't have confidence
                            is_final=False,
                            language=self.config.language
                        )
                    )
                )
        
        def recognized_cb(evt):
            """Callback for final results."""
            if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
                # Azure doesn't provide confidence in real-time API
                asyncio.create_task(
                    results_queue.put(
                        STTResult(
                            text=evt.result.text,
                            confidence=1.0,
                            is_final=True,
                            language=self.config.language,
                            metadata={
                                "duration_ms": evt.result.duration
                            }
                        )
                    )
                )
        
        def canceled_cb(evt):
            """Callback for errors."""
            print(f"Speech recognition canceled: {evt}")
            done.set()
        
        def stopped_cb(evt):
            """Callback for stream end."""
            done.set()
        
        # Connect callbacks
        recognizer.recognizing.connect(recognizing_cb)
        recognizer.recognized.connect(recognized_cb)
        recognizer.canceled.connect(canceled_cb)
        recognizer.session_stopped.connect(stopped_cb)
        
        # Start continuous recognition
        recognizer.start_continuous_recognition()
        
        # Feed audio stream
        async def feed_audio():
            try:
                async for audio_chunk in audio_stream:
                    stream.write(audio_chunk)
            finally:
                stream.close()
        
        # Start feeding audio in background
        feed_task = asyncio.create_task(feed_audio())
        
        # Yield results as they arrive
        try:
            while not done.is_set():
                try:
                    result = await asyncio.wait_for(
                        results_queue.get(), 
                        timeout=0.1
                    )
                    yield result
                except asyncio.TimeoutError:
                    continue
        finally:
            recognizer.stop_continuous_recognition()
            await feed_task

    async def transcribe_file(self, audio_file_path: str) -> STTResult:
        """Transcribe an audio file."""
        audio_config = speechsdk.audio.AudioConfig(filename=audio_file_path)
        recognizer = speechsdk.SpeechRecognizer(
            speech_config=self.speech_config,
            audio_config=audio_config
        )
        
        result = recognizer.recognize_once()
        
        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            return STTResult(
                text=result.text,
                confidence=1.0,
                is_final=True,
                language=self.config.language,
                metadata={
                    "duration_ms": result.duration
                }
            )
        else:
            raise Exception(f"Recognition failed: {result.reason}")

    async def cleanup(self) -> None:
        """Clean up resources."""
        self.speech_config = None
        self._initialized = False

    def get_supported_languages(self) -> List[str]:
        """Azure supports 100+ languages."""
        return [
            "en-US", "en-GB", "es-ES", "es-MX", "fr-FR", "de-DE", 
            "it-IT", "pt-BR", "pt-PT", "ja-JP", "ko-KR", "zh-CN",
            "ar-SA", "hi-IN", "tr-TR", "vi-VN", "th-TH", "id-ID"
        ]
