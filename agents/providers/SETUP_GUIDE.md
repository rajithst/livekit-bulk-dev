# Setup Guide for Custom STT Integration

## Prerequisites

- Python 3.9 or higher
- pip or conda package manager

## Installation Steps

### 1. Install Dependencies

Navigate to the agents directory and install all required packages:

```bash
cd agents
pip install -r requirements.txt
```

This will install:
- `livekit` - LiveKit SDK
- `livekit-agents` - LiveKit Agents Framework
- `aiohttp` - Async HTTP client for custom adapters
- `openai` - OpenAI SDK (for native plugins)
- `azure-cognitiveservices-speech` - Azure Speech SDK (optional)
- Other dependencies for state management, logging, etc.

### 2. Verify Installation

Check that the packages are installed correctly:

```bash
python -c "import livekit; print(f'LiveKit: {livekit.__version__}')"
python -c "import livekit.agents; print('LiveKit Agents: OK')"
python -c "import aiohttp; print(f'aiohttp: {aiohttp.__version__}')"
```

Expected output:
```
LiveKit: 0.11.0
LiveKit Agents: OK
aiohttp: 3.9.x
```

### 3. Configure Python Environment in VS Code

If using VS Code, configure the Python interpreter:

1. Open Command Palette (Cmd+Shift+P)
2. Select "Python: Select Interpreter"
3. Choose the Python environment where you installed the packages

Alternatively, use the Python extension's environment configuration:
```bash
# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate  # On Windows

# Install dependencies in the virtual environment
pip install -r requirements.txt
```

### 4. Test the Implementation

Create a test file to verify the custom adapters work:

```python
# test_custom_stt.py
import asyncio
from agents.providers.adapters import CustomHTTPSTTAdapter, CustomWebSocketSTTAdapter
from livekit.agents.stt import AudioBuffer

async def test_http_adapter():
    adapter = CustomHTTPSTTAdapter(
        endpoint_url="https://api.example.com/stt",
        api_key="test-key",
        language="en-US"
    )
    
    print(f"✓ HTTP adapter created")
    print(f"  Sample rate: {adapter.sample_rate}")
    print(f"  Model: {adapter.model}")
    print(f"  Provider: {adapter.provider}")

async def test_websocket_adapter():
    adapter = CustomWebSocketSTTAdapter(
        ws_url="wss://api.example.com/stream",
        api_key="test-key",
        language="en-US"
    )
    
    print(f"✓ WebSocket adapter created")
    print(f"  Sample rate: {adapter.sample_rate}")
    print(f"  Model: {adapter.model}")
    print(f"  Provider: {adapter.provider}")

if __name__ == "__main__":
    asyncio.run(test_http_adapter())
    asyncio.run(test_websocket_adapter())
```

Run the test:
```bash
python test_custom_stt.py
```

Expected output:
```
✓ HTTP adapter created
  Sample rate: 16000
  Model: custom-http
  Provider: custom
✓ WebSocket adapter created
  Sample rate: 16000
  Model: custom-websocket
  Provider: custom
```

## Common Issues and Solutions

### Issue: "Import 'aiohttp' could not be resolved"

**Solution:**
```bash
pip install aiohttp>=3.9.0
```

Verify installation:
```bash
python -c "import aiohttp; print(aiohttp.__version__)"
```

### Issue: "Import 'livekit.agents' could not be resolved"

**Solution:**
```bash
pip install livekit-agents>=0.8.0
```

Verify installation:
```bash
python -c "import livekit.agents; print('OK')"
```

### Issue: VS Code shows import errors but code runs fine

**Solution:**
1. Ensure VS Code is using the correct Python interpreter
2. Reload VS Code window (Cmd+Shift+P → "Developer: Reload Window")
3. Install Python extension if not already installed
4. Configure the Python path in `.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": "./venv/bin/python",
  "python.analysis.extraPaths": [
    "${workspaceFolder}/agents"
  ]
}
```

### Issue: ModuleNotFoundError at runtime

**Solution:**
Ensure you're running Python from the agents directory or add it to PYTHONPATH:

```bash
export PYTHONPATH="${PYTHONPATH}:${PWD}/agents"
python your_script.py
```

Or run from the project root:
```bash
cd /Users/rajith/Documents/Projects/livekit-starter
python -m agents.core.agent
```

## Development Workflow

### 1. Working with Custom Adapters

When developing custom adapters:

1. Create your adapter in `agents/providers/adapters.py` or a separate file
2. Test it independently before integrating with AgentSession
3. Add factory method in `agents/providers/custom_provider.py`
4. Register in `agents/providers/__init__.py` if needed

### 2. Testing with Mock Endpoints

For testing without real API endpoints:

```python
from unittest.mock import AsyncMock, patch

async def test_custom_stt_with_mock():
    adapter = CustomHTTPSTTAdapter(
        endpoint_url="https://mock.api.com/stt",
        api_key="test-key"
    )
    
    with patch.object(adapter, '_send_audio_chunk', new_callable=AsyncMock) as mock:
        mock.return_value = "Hello, world!"
        
        buffer = AudioBuffer(data=b'\x00' * 1600, sample_rate=16000)
        event = await adapter._recognize_impl(buffer, language="en-US", conn_options=None)
        
        assert event.alternatives[0].text == "Hello, world!"
```

### 3. Integration with AgentSession

Complete example:

```python
from livekit.agents import AgentSession, JobContext
from agents.providers import ProviderFactory, ProviderType
from agents.providers.base import STTConfig, LLMConfig, TTSConfig

async def entrypoint(ctx: JobContext):
    # Configure providers
    stt = ProviderFactory.create_stt(STTConfig(
        provider=ProviderType.CUSTOM_WS,
        language="en-US",
        metadata={"ws_url": "wss://api.deepgram.com/v1/listen", "api_key": "key"}
    ))
    
    llm = ProviderFactory.create_llm(LLMConfig(
        provider=ProviderType.OPENAI,
        model="gpt-4",
        api_key="openai-key"
    ))
    
    tts = ProviderFactory.create_tts(TTSConfig(
        provider=ProviderType.OPENAI,
        voice="alloy",
        api_key="openai-key"
    ))
    
    # Create and run session
    session = AgentSession(stt=stt, llm=llm, tts=tts)
    await session.run()
```

## Package Versions

Ensure you're using compatible versions:

```
livekit==0.11.0
livekit-agents==0.8.0
aiohttp>=3.9.0
openai>=1.12.0
```

Check installed versions:
```bash
pip list | grep -E "livekit|aiohttp|openai"
```

## Next Steps

1. ✅ Install all dependencies
2. ✅ Verify imports work
3. ✅ Test custom adapters
4. ✅ Integrate with your AgentSession
5. ✅ Configure your specific STT vendor (Deepgram, AssemblyAI, etc.)

## Support

If you encounter issues:
1. Check the error messages carefully
2. Verify package versions match requirements.txt
3. Ensure Python 3.9+ is being used
4. Check that virtual environment is activated (if using one)
5. Review the documentation in `CUSTOM_STT_USAGE.md`

## References

- [LiveKit Agents Documentation](https://docs.livekit.io/agents/)
- [aiohttp Documentation](https://docs.aiohttp.org/)
- Custom STT Usage Guide: `agents/providers/CUSTOM_STT_USAGE.md`
- Implementation Summary: `agents/providers/IMPLEMENTATION_SUMMARY.md`
