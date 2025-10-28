# Custom STT Provider Usage Guide

This guide explains how to integrate custom Speech-to-Text (STT) services with LiveKit AgentSession.

## Architecture Overview

The custom STT adapters inherit from LiveKit's `stt.STT` base class, making them fully compatible with `AgentSession`. You can seamlessly mix LiveKit native plugins (OpenAI, Azure) with custom HTTP/WebSocket endpoints.

### Key Compatibility Insight

```python
# From LiveKit's source code:
class AgentSession:
    def __init__(
        self,
        *,
        stt: NotGivenOr[stt.STT | STTModels | str] = NOT_GIVEN,
        # ...
    ):
```

**Any class inheriting from `stt.STT` is compatible with `AgentSession`.**

## Available Adapter Types

### 1. CustomHTTPSTTAdapter
For simple request/response STT APIs (non-streaming).

**Use cases:**
- RESTful STT services
- Batch transcription APIs
- Services without real-time streaming support

**Example:**
```python
from agents.providers.adapters import CustomHTTPSTTAdapter

# Basic usage
stt_adapter = CustomHTTPSTTAdapter(
    endpoint_url="https://api.example.com/v1/transcribe",
    api_key="your-api-key",
    language="en-US",
    request_timeout=30
)

# Use with AgentSession
session = AgentSession(
    stt=stt_adapter,  # ✅ Works because CustomHTTPSTTAdapter inherits from stt.STT
    llm=openai_llm,
    tts=openai_tts
)
```

**Customizing the HTTP request:**

If your endpoint expects a different format, subclass and override `_send_audio_chunk`:

```python
class MyCustomSTTAdapter(CustomHTTPSTTAdapter):
    async def _send_audio_chunk(self, audio_data: bytes) -> str:
        async with aiohttp.ClientSession() as session:
            # Custom request format for your specific API
            form_data = aiohttp.FormData()
            form_data.add_field('audio', audio_data, filename='audio.wav')
            form_data.add_field('language', self.language)
            
            async with session.post(
                self.endpoint_url,
                data=form_data,
                headers={"Authorization": f"Bearer {self.api_key}"}
            ) as response:
                result = await response.json()
                return result['transcript']['text']
```

### 2. CustomWebSocketSTTAdapter
For real-time streaming STT services.

**Use cases:**
- Real-time voice assistants
- Live transcription
- Low-latency applications
- WebSocket-based STT APIs (Deepgram, AssemblyAI, etc.)

**Example:**
```python
from agents.providers.adapters import CustomWebSocketSTTAdapter

# Basic usage
stt_adapter = CustomWebSocketSTTAdapter(
    ws_url="wss://api.example.com/v1/stream",
    api_key="your-api-key",
    language="en-US",
    sample_rate=16000
)

# Use with AgentSession
session = AgentSession(
    stt=stt_adapter,  # ✅ Supports streaming and interim results
    llm=openai_llm,
    tts=openai_tts
)
```

**How it works:**
1. Establishes WebSocket connection on first audio frame
2. Sends configuration message with language and sample rate
3. Streams audio frames as they arrive
4. Receives interim and final transcripts
5. Emits `SpeechEvent` objects compatible with LiveKit

## Using the Factory Pattern

The recommended way to create custom adapters is through the factory system:

```python
from agents.providers import ProviderFactory, ProviderType
from agents.providers.base import STTConfig

# HTTP-based STT
http_stt_config = STTConfig(
    provider=ProviderType.CUSTOM_HTTP,
    endpoint_url="https://api.deepgram.com/v1/listen",
    api_key="your-deepgram-key",
    language="en-US"
)
stt = ProviderFactory.create_stt(http_stt_config)

# WebSocket-based STT
ws_stt_config = STTConfig(
    provider=ProviderType.CUSTOM_WS,
    ws_url="wss://api.assemblyai.com/v2/realtime/ws",
    api_key="your-assemblyai-key",
    language="en-US"
)
stt = ProviderFactory.create_stt(ws_stt_config)

# Use in AgentSession
session = AgentSession(stt=stt, llm=llm, tts=tts)
```

## Vendor-Specific Factories

Pre-configured factories for popular services:

```python
from agents.providers.custom_provider import (
    create_deepgram_stt,
    create_assemblyai_stt,
    create_google_cloud_stt
)

# Deepgram (WebSocket)
deepgram_stt = create_deepgram_stt(
    api_key="your-key",
    language="en-US",
    model="nova-2"
)

# AssemblyAI (WebSocket)
assemblyai_stt = create_assemblyai_stt(
    api_key="your-key",
    language="en-US"
)

# Google Cloud (HTTP)
google_stt = create_google_cloud_stt(
    api_key="your-key",
    language="en-US",
    project_id="my-project"
)
```

## Complete Example

```python
from livekit.agents import AgentSession, JobContext
from agents.providers import ProviderFactory, ProviderType
from agents.providers.base import STTConfig, LLMConfig, TTSConfig

async def entrypoint(ctx: JobContext):
    # Mix custom STT with native OpenAI LLM/TTS
    stt_config = STTConfig(
        provider=ProviderType.CUSTOM_WS,
        ws_url="wss://api.deepgram.com/v1/listen",
        api_key="deepgram-key",
        language="en-US"
    )
    
    llm_config = LLMConfig(
        provider=ProviderType.OPENAI,
        model="gpt-4",
        api_key="openai-key"
    )
    
    tts_config = TTSConfig(
        provider=ProviderType.OPENAI,
        voice="alloy",
        api_key="openai-key"
    )
    
    # Create providers
    stt = ProviderFactory.create_stt(stt_config)
    llm = ProviderFactory.create_llm(llm_config)
    tts = ProviderFactory.create_tts(tts_config)
    
    # All work together seamlessly
    session = AgentSession(
        stt=stt,  # Custom Deepgram WebSocket
        llm=llm,  # Native OpenAI plugin
        tts=tts   # Native OpenAI plugin
    )
    
    await session.run()
```

## Error Handling

Both adapters include robust error handling:

```python
# Handles timeouts
try:
    event = await stt._recognize_impl(audio_buffer, ...)
except asyncio.TimeoutError:
    # Returns empty SpeechEvent instead of crashing
    pass

# Handles network errors
try:
    text = await adapter._send_audio_chunk(audio_data)
except aiohttp.ClientError as e:
    logger.error(f"Network error: {e}")
    # Returns empty string instead of crashing
```

## Testing Custom Adapters

```python
import pytest
from agents.providers.adapters import CustomHTTPSTTAdapter
from livekit.agents.stt import AudioBuffer

@pytest.mark.asyncio
async def test_custom_stt():
    adapter = CustomHTTPSTTAdapter(
        endpoint_url="https://mock-api.example.com/transcribe",
        api_key="test-key"
    )
    
    # Create test audio buffer
    audio_data = b'\x00' * 1600  # 100ms of silence at 16kHz
    buffer = AudioBuffer(data=audio_data, sample_rate=16000)
    
    # Test recognition
    event = await adapter._recognize_impl(
        buffer,
        language="en-US",
        conn_options=None
    )
    
    assert event.type == SpeechEventType.FINAL_TRANSCRIPT
    assert len(event.alternatives) > 0
```

## When to Use Which Adapter

### Use CustomHTTPSTTAdapter when:
- ✅ You have a REST API endpoint
- ✅ Latency requirements are relaxed (>500ms acceptable)
- ✅ Batch processing is acceptable
- ✅ Service doesn't support WebSocket streaming

### Use CustomWebSocketSTTAdapter when:
- ✅ You need real-time streaming (<200ms latency)
- ✅ You want interim transcription results
- ✅ Service supports WebSocket protocol
- ✅ Building interactive voice assistants

### Use Native LiveKit Plugins when:
- ✅ Provider has official LiveKit plugin (OpenAI, Azure, Deepgram, etc.)
- ✅ You want zero-config integration
- ✅ Provider is well-supported by LiveKit ecosystem

## Advanced: Implementing Custom Protocols

If your STT service uses a unique protocol, subclass `STTAdapter`:

```python
from agents.providers.adapters import STTAdapter
from livekit.agents import stt

class MyCustomProtocolSTTAdapter(STTAdapter):
    def __init__(self, custom_config):
        super().__init__(sample_rate=16000, streaming=True)
        self.config = custom_config
    
    async def _recognize_impl(
        self,
        buffer: stt.AudioBuffer,
        *,
        language: str | None = None,
        conn_options: stt.APIConnectOptions,
    ) -> stt.SpeechEvent:
        # Implement your custom protocol here
        text = await self._custom_transcribe(buffer.data.tobytes())
        
        return stt.SpeechEvent(
            type=stt.SpeechEventType.FINAL_TRANSCRIPT,
            alternatives=[stt.SpeechData(text=text, language=language)]
        )
    
    async def _custom_transcribe(self, audio_data: bytes) -> str:
        # Your custom implementation
        pass
```

## Troubleshooting

### "Import livekit.agents could not be resolved"
Install dependencies:
```bash
pip install -r agents/requirements.txt
```

### "Custom adapter not working with AgentSession"
Ensure your adapter inherits from `stt.STT`:
```python
class MyAdapter(stt.STT):  # ✅ Correct
    pass

class MyAdapter(ABC):  # ❌ Wrong - not compatible with AgentSession
    pass
```

### "WebSocket connection fails"
Check authentication and URL:
```python
adapter = CustomWebSocketSTTAdapter(
    ws_url="wss://api.example.com/v1/stream",  # Must start with wss://
    api_key="your-key",  # Check if key is valid
    language="en-US"
)
```

## Summary

- ✅ Custom adapters inherit from `stt.STT` for LiveKit compatibility
- ✅ Use `CustomHTTPSTTAdapter` for REST APIs
- ✅ Use `CustomWebSocketSTTAdapter` for real-time streaming
- ✅ Factory pattern handles provider creation
- ✅ Mix custom and native providers in same `AgentSession`
- ✅ Robust error handling prevents crashes
- ✅ Easy to extend for custom protocols
