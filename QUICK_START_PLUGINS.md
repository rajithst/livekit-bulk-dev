# Quick Start: Using LiveKit Plugins with Decoupled Providers

## TL;DR

```python
# 1. Configure provider
stt_config = STTConfig(
    provider=ProviderType.OPENAI,  # or AZURE
    model="whisper-1",
    metadata={"api_key": "sk-..."}
)

# 2. Create plugin via factory (vendor-agnostic)
stt_plugin = ProviderFactory.create_stt(stt_config)

# 3. Pass to AgentSession - LiveKit handles everything
session = AgentSession(stt=stt_plugin, llm=llm_plugin, tts=tts_plugin)
await session.start(room=ctx.room, agent=agent)
```

**That's it!** No manual audio buffering, streaming, or chunk management.

## Why This Approach?

### ✅ Pros
- **Vendor Decoupling**: Switch providers by changing config
- **LiveKit Native**: Full access to LiveKit features (VAD, noise cancellation)
- **Zero Boilerplate**: No manual audio processing code
- **Battle-Tested**: LiveKit's production-ready implementations

### ❌ What We DON'T Do
- ❌ Manual audio chunk buffering
- ❌ Manual stream feeding to STT APIs
- ❌ Custom audio frame processing
- ❌ Implementing base provider classes

### ✅ What LiveKit Does For Us
- ✅ Audio buffering and streaming
- ✅ VAD (Voice Activity Detection)
- ✅ Noise/echo cancellation
- ✅ Audio resampling
- ✅ Packet loss recovery
- ✅ Jitter buffering

## Provider Factory Pattern

### Factory (Vendor-Agnostic)
```python
# agents/providers/base.py
class ProviderFactory:
    _stt_registry = {}  # Maps ProviderType → factory_func
    
    @classmethod
    def create_stt(cls, config: STTConfig):
        factory_func = cls._stt_registry[config.provider]
        return factory_func(config)  # Returns LiveKit plugin
```

### Factory Functions (Vendor-Specific)
```python
# agents/providers/openai_provider.py
def create_openai_stt(config: STTConfig):
    return lk_openai.STT(
        model=config.model,
        api_key=config.metadata["api_key"]
    )

# agents/providers/azure_provider.py
def create_azure_stt(config: STTConfig):
    return lk_openai.STT.with_azure(
        azure_endpoint=config.metadata["azure_endpoint"],
        api_key=config.metadata["api_key"]
    )
```

### Registration (Auto on Import)
```python
# agents/providers/__init__.py
ProviderFactory.register_stt_provider(ProviderType.OPENAI, create_openai_stt)
ProviderFactory.register_stt_provider(ProviderType.AZURE, create_azure_stt)
```

## Usage Examples

### Example 1: OpenAI
```python
config = STTConfig(
    provider=ProviderType.OPENAI,
    model="whisper-1",
    language="en-US",
    metadata={"api_key": os.getenv("OPENAI_API_KEY")}
)

stt = ProviderFactory.create_stt(config)  # Returns lk_openai.STT
```

### Example 2: Azure OpenAI
```python
config = STTConfig(
    provider=ProviderType.AZURE,
    model="whisper",
    metadata={
        "azure_endpoint": "https://my-resource.openai.azure.com",
        "azure_deployment": "whisper-deployment",
        "api_key": os.getenv("AZURE_API_KEY")
    }
)

stt = ProviderFactory.create_stt(config)  # Returns lk_openai.STT.with_azure
```

### Example 3: Full Agent Setup
```python
async def entrypoint(ctx: JobContext):
    settings = Settings()
    
    # Create configs
    stt_config = STTConfig(
        provider=ProviderType.OPENAI,
        model=settings.stt_model,
        metadata={"api_key": settings.openai_api_key}
    )
    
    llm_config = LLMConfig(
        provider=ProviderType.OPENAI,
        model=settings.llm_model,
        temperature=0.7,
        metadata={"api_key": settings.openai_api_key}
    )
    
    tts_config = TTSConfig(
        provider=ProviderType.OPENAI,
        voice="alloy",
        model="tts-1",
        metadata={"api_key": settings.openai_api_key}
    )
    
    # Create plugins via factory
    stt_plugin = ProviderFactory.create_stt(stt_config)
    llm_plugin = ProviderFactory.create_llm(llm_config)
    tts_plugin = ProviderFactory.create_tts(tts_config)
    
    # Create agent
    agent = VoiceAssistantAgent(...)
    
    # Connect to room
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    
    # Start session with plugins
    session = AgentSession(stt=stt_plugin, llm=llm_plugin, tts=tts_plugin)
    await session.start(room=ctx.room, agent=agent)
    
    # LiveKit handles everything from here!
    await ctx.wait_for_disconnection()
```

## Adding New Providers

### Step-by-Step: Add Deepgram

**1. Create factory function**
```python
# agents/providers/deepgram_provider.py
from livekit.plugins import deepgram

def create_deepgram_stt(config: STTConfig):
    return deepgram.STT(
        model=config.model or "nova-2",
        language=config.language,
        api_key=config.metadata["api_key"]
    )

def create_deepgram_llm(config: LLMConfig):
    # If Deepgram had LLM
    return deepgram.LLM(...)
```

**2. Register**
```python
# agents/providers/__init__.py
from .deepgram_provider import create_deepgram_stt

ProviderFactory.register_stt_provider(
    ProviderType.DEEPGRAM,
    create_deepgram_stt
)
```

**3. Add to enum**
```python
# agents/providers/base.py
class ProviderType(Enum):
    OPENAI = "openai"
    AZURE = "azure"
    DEEPGRAM = "deepgram"  # Add this
```

**4. Use it**
```python
config = STTConfig(
    provider=ProviderType.DEEPGRAM,
    model="nova-2",
    metadata={"api_key": "..."}
)

stt = ProviderFactory.create_stt(config)
```

**That's all!** No base classes, no streaming logic.

## Configuration via Environment

```bash
# .env
STT_PROVIDER=openai  # or azure, deepgram, etc.
STT_MODEL=whisper-1
STT_LANGUAGE=en-US

OPENAI_API_KEY=sk-...

# For Azure
AZURE_OPENAI_ENDPOINT=https://...
AZURE_STT_DEPLOYMENT=whisper
AZURE_API_KEY=...
```

```python
# agents/config/settings.py
class Settings:
    stt_provider: str = os.getenv("STT_PROVIDER", "openai")
    stt_model: str = os.getenv("STT_MODEL", "whisper-1")
    openai_api_key: str = os.getenv("OPENAI_API_KEY")
    
    def get_stt_config(self) -> STTConfig:
        provider_type = ProviderType(self.stt_provider)
        
        if provider_type == ProviderType.AZURE:
            metadata = {
                "azure_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
                "azure_deployment": os.getenv("AZURE_STT_DEPLOYMENT"),
                "api_key": os.getenv("AZURE_API_KEY")
            }
        else:
            metadata = {"api_key": self.openai_api_key}
        
        return STTConfig(
            provider=provider_type,
            model=self.stt_model,
            metadata=metadata
        )
```

## Deployment

```bash
# Development
python agents/core/agent.py

# Docker
docker build -f docker/Dockerfile.agent -t agent .
docker run -e OPENAI_API_KEY=sk-... agent

# Kubernetes
kubectl apply -f k8s/agents/deployment.yaml

# Change provider
docker run -e STT_PROVIDER=azure -e AZURE_API_KEY=... agent
```

## Key Files

```
agents/
├── providers/
│   ├── __init__.py              # Auto-registration
│   ├── base.py                   # ProviderFactory + configs
│   ├── openai_provider.py        # create_openai_stt/llm/tts
│   └── azure_provider.py         # create_azure_stt/llm/tts
└── core/
    └── agent.py                  # Uses plugins via factory
```

## Common Patterns

### Pattern 1: Runtime Provider Selection
```python
def create_stt_from_env():
    provider = os.getenv("STT_PROVIDER", "openai")
    config = STTConfig(
        provider=ProviderType(provider),
        model=os.getenv("STT_MODEL"),
        metadata={...}
    )
    return ProviderFactory.create_stt(config)
```

### Pattern 2: Multi-Vendor Setup
```python
# Use OpenAI for STT, Azure for LLM, ElevenLabs for TTS
stt_plugin = ProviderFactory.create_stt(
    STTConfig(provider=ProviderType.OPENAI, ...)
)
llm_plugin = ProviderFactory.create_llm(
    LLMConfig(provider=ProviderType.AZURE, ...)
)
tts_plugin = ProviderFactory.create_tts(
    TTSConfig(provider=ProviderType.ELEVENLABS, ...)
)
```

### Pattern 3: Fallback Providers
```python
try:
    stt = ProviderFactory.create_stt(primary_config)
except Exception as e:
    logger.warning(f"Primary STT failed: {e}, using fallback")
    stt = ProviderFactory.create_stt(fallback_config)
```

## Debugging

```python
# Check registered providers
print(ProviderFactory._stt_registry.keys())
# dict_keys([<ProviderType.OPENAI>, <ProviderType.AZURE>])

# Verify plugin instance
plugin = ProviderFactory.create_stt(config)
print(type(plugin))
# <class 'livekit.plugins.openai.stt.STT'>

# Test plugin creation
try:
    plugin = ProviderFactory.create_stt(config)
    print("✅ Plugin created successfully")
except Exception as e:
    print(f"❌ Error: {e}")
```

## Summary

**Three Core Principles:**

1. **Factory Pattern** = Vendor decoupling
   ```python
   ProviderFactory.create_stt(config)  # Vendor-agnostic
   ```

2. **Simple Factory Functions** = Easy to add providers
   ```python
   def create_xxx_stt(config):
       return xxx_plugin.STT(...)
   ```

3. **LiveKit Plugin Instances** = Zero boilerplate
   ```python
   # Just pass to AgentSession - done!
   AgentSession(stt=plugin, ...)
   ```

**Result**: Clean, maintainable, vendor-agnostic agent with full LiveKit power! 🚀
