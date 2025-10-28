"""
Adapter interfaces for wrapping both LiveKit plugins and custom providers.

This allows seamless integration of third-party STT/LLM/TTS services that don't
have LiveKit plugins, by providing a unified interface.
"""

from typing import AsyncIterator, Optional, Any
import aiohttp
import asyncio
import logging

from livekit.agents import stt, llm, tts

logger = logging.getLogger(__name__)


class STTAdapter(stt.STT):
    """
    Abstract adapter for Speech-to-Text providers.
    
    Inherits from LiveKit's stt.STT to be compatible with AgentSession.
    Custom providers should implement _recognize_impl and stream methods.
    """
    
    def __init__(self, *, sample_rate: int = 16000, streaming: bool = True, interim_results: bool = True):
        """Initialize STT adapter with capabilities."""
        super().__init__(
            capabilities=stt.STTCapabilities(
                streaming=streaming,
                interim_results=interim_results
            )
        )
        self._sample_rate = sample_rate
    
    @property
    def sample_rate(self) -> int:
        """Audio sample rate expected by this STT."""
        return self._sample_rate


class LiveKitSTTAdapter(STTAdapter):
    """
    Adapter for LiveKit native STT plugins.
    
    NOTE: This is typically NOT needed when using AgentSession directly,
    as AgentSession expects native LiveKit plugin instances.
    
    This adapter is useful ONLY when you need to:
    1. Use a LiveKit plugin outside of AgentSession
    2. Provide a unified interface alongside custom HTTP/WebSocket providers
    3. Test or wrap plugin functionality with additional logic
    
    For normal use with AgentSession, pass the plugin directly without wrapping.
    """
    
    def __init__(self, plugin: Any):
        """
        Wrap a LiveKit STT plugin.
        
        Args:
            plugin: LiveKit STT plugin instance (e.g., lk_openai.STT)
        """
        self.plugin = plugin
    
    async def transcribe_stream(self, audio_stream: AsyncIterator[bytes]) -> AsyncIterator[str]:
        """Pass through to LiveKit plugin's streaming transcription."""
        async for text in self.plugin.transcribe_stream(audio_stream):
            yield text
    
    async def transcribe(self, audio_data: bytes) -> str:
        """Pass through to LiveKit plugin's transcription."""
        return await self.plugin.transcribe(audio_data)


class CustomHTTPSTTAdapter(STTAdapter):
    """Adapter for custom HTTP-based STT endpoints."""
    
    def __init__(
        self,
        endpoint_url: str,
        api_key: Optional[str] = None,
        language: str = "en-US",
        headers: Optional[dict] = None,
        request_timeout: int = 30,
        sample_rate: int = 16000
    ):
        """
        Initialize custom HTTP STT adapter.
        
        Args:
            endpoint_url: The STT service endpoint URL
            api_key: Optional API key for authentication
            language: Language code for transcription
            headers: Additional HTTP headers
            request_timeout: Request timeout in seconds
            sample_rate: Audio sample rate
        """
        super().__init__(sample_rate=sample_rate, streaming=False, interim_results=False)
        
        self.endpoint_url = endpoint_url
        self.api_key = api_key
        self.language = language
        self.request_timeout = request_timeout
        
        # Build headers
        self.headers = headers or {}
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"
        self.headers["Content-Type"] = "audio/wav"
    
    @property
    def model(self) -> str:
        """Model identifier."""
        return "custom-http"
    
    @property
    def provider(self) -> str:
        """Provider name."""
        return "custom"
    
    async def _recognize_impl(
        self,
        buffer: stt.AudioBuffer,
        *,
        language: str | None = None,
        conn_options: stt.APIConnectOptions,
    ) -> stt.SpeechEvent:
        """
        Implement LiveKit's STT interface for HTTP endpoint.
        
        Args:
            buffer: Audio buffer to transcribe
            language: Optional language override
            conn_options: Connection options
            
        Returns:
            SpeechEvent with transcription
        """
        try:
            # Convert AudioBuffer to bytes
            audio_data = buffer.data.tobytes()
            
            # Send to custom endpoint
            text = await self._send_audio_chunk(audio_data)
            
            # Return as SpeechEvent
            return stt.SpeechEvent(
                type=stt.SpeechEventType.FINAL_TRANSCRIPT,
                alternatives=[stt.SpeechData(text=text, language=language or self.language)]
            )
                    
        except asyncio.TimeoutError:
            logger.error(f"Timeout calling STT endpoint: {self.endpoint_url}")
            return stt.SpeechEvent(
                type=stt.SpeechEventType.FINAL_TRANSCRIPT,
                alternatives=[stt.SpeechData(text="", language=language or self.language)]
            )
        except Exception as e:
            logger.error(f"Error in STT transcription: {e}", exc_info=True)
            return stt.SpeechEvent(
                type=stt.SpeechEventType.FINAL_TRANSCRIPT,
                alternatives=[stt.SpeechData(text="", language=language or self.language)]
            )
    
    async def _send_audio_chunk(self, audio_data: bytes) -> str:
        """
        Send audio chunk to custom endpoint.
        
        Override this method to customize the request format for your specific endpoint.
        """
        try:
            async with aiohttp.ClientSession() as session:
                # Build request payload
                # Adjust this based on your endpoint's expected format
                data = {
                    "audio": audio_data,
                    "language": self.language,
                    "encoding": "LINEAR16",
                    "sample_rate": 16000
                }
                
                async with session.post(
                    self.endpoint_url,
                    json=data,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=self.request_timeout)
                ) as response:
                    response.raise_for_status()
                    result = await response.json()
                    
                    # Extract transcription from response
                    # Adjust this based on your endpoint's response format
                    return result.get("transcription", result.get("text", ""))
                    
        except asyncio.TimeoutError:
            logger.error(f"Timeout calling STT endpoint: {self.endpoint_url}")
            return ""
        except aiohttp.ClientError as e:
            logger.error(f"Error calling STT endpoint: {e}")
            return ""
        except Exception as e:
            logger.error(f"Unexpected error in STT transcription: {e}", exc_info=True)
            return ""


class CustomWebSocketSTTAdapter(STTAdapter):
    """
    Adapter for custom WebSocket-based STT endpoints.
    
    Use this for true real-time streaming STT services.
    """
    
    def __init__(
        self,
        ws_url: str,
        api_key: Optional[str] = None,
        language: str = "en-US",
        sample_rate: int = 16000
    ):
        """
        Initialize WebSocket STT adapter.
        
        Args:
            ws_url: WebSocket endpoint URL
            api_key: Optional API key
            language: Language code
            sample_rate: Audio sample rate
        """
        super().__init__(sample_rate=sample_rate, streaming=True, interim_results=True)
        
        self.ws_url = ws_url
        self.api_key = api_key
        self.language = language
    
    @property
    def model(self) -> str:
        """Model identifier."""
        return "custom-websocket"
    
    @property
    def provider(self) -> str:
        """Provider name."""
        return "custom"
    
    async def _recognize_impl(
        self,
        buffer: stt.AudioBuffer,
        *,
        language: str | None = None,
        conn_options: stt.APIConnectOptions,
    ) -> stt.SpeechEvent:
        """
        For WebSocket, use stream() method instead.
        This provides a fallback for non-streaming use.
        """
        # Convert to streaming
        audio_data = buffer.data.tobytes()
        
        result = []
        async for event in self._transcribe_stream(audio_data):
            if event.type == stt.SpeechEventType.FINAL_TRANSCRIPT:
                result.append(event.alternatives[0].text)
        
        final_text = " ".join(result)
        return stt.SpeechEvent(
            type=stt.SpeechEventType.FINAL_TRANSCRIPT,
            alternatives=[stt.SpeechData(text=final_text, language=language or self.language)]
        )
    
    def stream(
        self,
        *,
        language: str | None = None,
        conn_options: stt.APIConnectOptions = None,
    ) -> "WebSocketSpeechStream":
        """Create a streaming session."""
        return WebSocketSpeechStream(
            stt=self,
            language=language or self.language,
            conn_options=conn_options or stt.APIConnectOptions()
        )
    
    async def _transcribe_stream(self, audio_data: bytes) -> AsyncIterator[stt.SpeechEvent]:
        """Internal method for streaming transcription."""
        async with aiohttp.ClientSession() as session:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            try:
                async with session.ws_connect(self.ws_url, headers=headers) as ws:
                    # Send initial configuration
                    await ws.send_json({
                        "type": "config",
                        "language": self.language,
                        "sample_rate": self.sample_rate,
                        "encoding": "LINEAR16"
                    })
                    
                    # Send audio data
                    await ws.send_bytes(audio_data)
                    await ws.send_json({"type": "end_of_stream"})
                    
                    # Receive transcriptions
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = msg.json()
                            
                            if data.get("type") == "transcription":
                                text = data.get("text", "")
                                is_final = data.get("is_final", False)
                                
                                event_type = (
                                    stt.SpeechEventType.FINAL_TRANSCRIPT
                                    if is_final
                                    else stt.SpeechEventType.INTERIM_TRANSCRIPT
                                )
                                
                                yield stt.SpeechEvent(
                                    type=event_type,
                                    alternatives=[stt.SpeechData(text=text, language=self.language)]
                                )
                        
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            logger.error(f"WebSocket error: {ws.exception()}")
                            break
                            
            except Exception as e:
                logger.error(f"Error in WebSocket transcription: {e}", exc_info=True)


class WebSocketSpeechStream(stt.SpeechStream):
    """Speech stream for WebSocket-based STT."""
    
    def __init__(
        self,
        *,
        stt: CustomWebSocketSTTAdapter,
        language: str,
        conn_options: stt.APIConnectOptions
    ):
        super().__init__(
            stt=stt,
            conn_options=conn_options,
            sample_rate=stt.sample_rate
        )
        self._stt = stt
        self._language = language
        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _run(self) -> None:
        """Run the WebSocket streaming session."""
        self._session = aiohttp.ClientSession()
        
        headers = {}
        if self._stt.api_key:
            headers["Authorization"] = f"Bearer {self._stt.api_key}"
        
        try:
            async with self._session.ws_connect(self._stt.ws_url, headers=headers) as ws:
                self._ws = ws
                
                # Send configuration
                await ws.send_json({
                    "type": "config",
                    "language": self._language,
                    "sample_rate": self._stt.sample_rate,
                    "encoding": "LINEAR16"
                })
                
                # Handle incoming messages
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        data = msg.json()
                        
                        if data.get("type") == "transcription":
                            text = data.get("text", "")
                            is_final = data.get("is_final", False)
                            
                            event_type = (
                                stt.SpeechEventType.FINAL_TRANSCRIPT
                                if is_final
                                else stt.SpeechEventType.INTERIM_TRANSCRIPT
                            )
                            
                            event = stt.SpeechEvent(
                                type=event_type,
                                alternatives=[stt.SpeechData(text=text, language=self._language)]
                            )
                            self._event_ch.send_nowait(event)
                    
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        logger.error(f"WebSocket error: {ws.exception()}")
                        break
                        
        except Exception as e:
            logger.error(f"Error in WebSocket stream: {e}", exc_info=True)
        finally:
            if self._session:
                await self._session.close()
    
    async def _send_audio_frame(self, frame: stt.AudioFrame) -> None:
        """Send audio frame to WebSocket."""
        if self._ws:
            await self._ws.send_bytes(frame.data.tobytes())


# Placeholder adapters for LLM and TTS (can be implemented similarly)
class LLMAdapter(llm.LLM):
    """Abstract adapter for LLM providers."""
    pass


class TTSAdapter(tts.TTS):
    """Abstract adapter for TTS providers."""
    pass
