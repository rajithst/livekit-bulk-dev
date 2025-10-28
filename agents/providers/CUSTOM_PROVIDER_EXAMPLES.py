"""
Examples of how to use custom STT providers.

This file demonstrates various ways to integrate third-party STT services
that don't have native LiveKit plugins.
"""

from agents.providers.base import STTConfig, ProviderType
from agents.providers import ProviderFactory


# Example 1: Generic HTTP-based STT endpoint
def example_generic_http_stt():
    """Use a generic HTTP STT endpoint."""
    config = STTConfig(
        provider=ProviderType.CUSTOM_HTTP,
        language="en-US",
        model="base",  # Optional, depends on vendor
        metadata={
            "endpoint_url": "https://your-stt-service.com/api/v1/transcribe",
            "api_key": "your-api-key-here",
            "headers": {
                "X-Custom-Header": "custom-value"
            },
            "request_timeout": 30
        }
    )
    
    # Create the adapter
    stt_adapter = ProviderFactory.create_stt(config)
    return stt_adapter


# Example 2: WebSocket-based STT (real-time streaming)
def example_websocket_stt():
    """Use a WebSocket STT endpoint for real-time transcription."""
    config = STTConfig(
        provider=ProviderType.CUSTOM_WS,
        language="en-US",
        metadata={
            "ws_url": "wss://your-stt-service.com/stream",
            "api_key": "your-api-key-here",
            "sample_rate": 16000
        }
    )
    
    stt_adapter = ProviderFactory.create_stt(config)
    return stt_adapter


# Example 3: Deepgram (specific vendor)
def example_deepgram_stt():
    """
    Use Deepgram's STT service.
    
    Deepgram provides excellent accuracy and real-time streaming.
    Sign up at: https://deepgram.com
    """
    from agents.providers.custom_provider import DeepgramProviderFactory
    
    config = STTConfig(
        provider=ProviderType.CUSTOM_WS,  # Deepgram uses WebSocket
        language="en-US",
        model="nova-2",  # Deepgram's latest model
        metadata={
            "api_key": "your-deepgram-api-key",
            "sample_rate": 16000
        }
    )
    
    stt_adapter = DeepgramProviderFactory.create_stt(config)
    return stt_adapter


# Example 4: AssemblyAI
def example_assemblyai_stt():
    """
    Use AssemblyAI's real-time STT service.
    
    AssemblyAI offers good accuracy with speaker diarization.
    Sign up at: https://www.assemblyai.com
    """
    from agents.providers.custom_provider import AssemblyAIProviderFactory
    
    config = STTConfig(
        provider=ProviderType.CUSTOM_WS,
        language="en",
        metadata={
            "api_key": "your-assemblyai-api-key",
            "sample_rate": 16000
        }
    )
    
    stt_adapter = AssemblyAIProviderFactory.create_stt(config)
    return stt_adapter


# Example 5: Mixed providers (different vendors for different services)
def example_mixed_providers():
    """
    Use different vendors for STT, LLM, and TTS.
    
    For example:
    - Deepgram for STT (better accuracy)
    - OpenAI for LLM (GPT-4)
    - Azure for TTS (neural voices)
    """
    from agents.providers.custom_provider import DeepgramProviderFactory
    from agents.providers.base import LLMConfig, TTSConfig
    
    # Custom STT (Deepgram)
    stt_config = STTConfig(
        provider=ProviderType.CUSTOM_WS,
        language="en-US",
        model="nova-2",
        metadata={
            "api_key": "deepgram-key",
            "sample_rate": 16000
        }
    )
    stt_plugin = DeepgramProviderFactory.create_stt(stt_config)
    
    # OpenAI LLM
    llm_config = LLMConfig(
        provider=ProviderType.OPENAI,
        model="gpt-4",
        temperature=0.7,
        metadata={"api_key": "openai-key"}
    )
    llm_plugin = ProviderFactory.create_llm(llm_config)
    
    # Azure TTS
    tts_config = TTSConfig(
        provider=ProviderType.AZURE,
        voice="en-US-JennyNeural",
        model="tts-1-hd",
        metadata={
            "api_key": "azure-key",
            "azure_endpoint": "https://your-resource.openai.azure.com/",
            "azure_deployment": "tts-deployment"
        }
    )
    tts_plugin = ProviderFactory.create_tts(tts_config)
    
    return stt_plugin, llm_plugin, tts_plugin


# Example 6: Create a custom adapter for your specific vendor
def example_custom_vendor_adapter():
    """
    If you need special handling, create a custom adapter class.
    
    This example shows how to extend CustomHTTPSTTAdapter for a specific vendor.
    """
    from agents.providers.adapters import CustomHTTPSTTAdapter
    
    class MyVendorSTTAdapter(CustomHTTPSTTAdapter):
        """Custom adapter for MyVendor's specific API format."""
        
        async def _send_audio_chunk(self, audio_data: bytes) -> str:
            """Override to match MyVendor's API format."""
            import aiohttp
            
            # MyVendor expects multipart form data
            form_data = aiohttp.FormData()
            form_data.add_field('audio', audio_data, content_type='audio/wav')
            form_data.add_field('language', self.language)
            form_data.add_field('model', 'my-vendor-model-v2')
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.endpoint_url,
                    data=form_data,
                    headers={'Authorization': f'Bearer {self.api_key}'}
                ) as response:
                    response.raise_for_status()
                    result = await response.json()
                    
                    # MyVendor returns: {"result": {"transcript": "..."}}
                    return result.get("result", {}).get("transcript", "")
    
    # Use the custom adapter
    config = STTConfig(
        provider=ProviderType.CUSTOM_HTTP,
        language="en-US",
        metadata={
            "endpoint_url": "https://api.myvendor.com/stt",
            "api_key": "my-vendor-key"
        }
    )
    
    return MyVendorSTTAdapter(
        endpoint_url=config.metadata["endpoint_url"],
        api_key=config.metadata["api_key"],
        language=config.language
    )


# Usage in agent.py entrypoint:
"""
In your agent.py entrypoint function, use custom providers like this:

async def entrypoint(ctx: JobContext):
    settings = Settings()
    
    # Option 1: Use environment variables to configure
    if settings.stt_provider == "deepgram":
        from agents.providers.custom_provider import DeepgramProviderFactory
        
        stt_config = STTConfig(
            provider=ProviderType.CUSTOM_WS,
            language=settings.stt_language,
            model="nova-2",
            metadata={
                "api_key": settings.deepgram_api_key,
                "sample_rate": 16000
            }
        )
        stt_plugin = DeepgramProviderFactory.create_stt(stt_config)
    
    elif settings.stt_provider == "custom_http":
        stt_config = STTConfig(
            provider=ProviderType.CUSTOM_HTTP,
            language=settings.stt_language,
            metadata={
                "endpoint_url": settings.custom_stt_endpoint,
                "api_key": settings.custom_stt_api_key
            }
        )
        stt_plugin = ProviderFactory.create_stt(stt_config)
    
    else:
        # Default to OpenAI or Azure
        stt_config = STTConfig(
            provider=ProviderType.OPENAI,
            ...
        )
        stt_plugin = ProviderFactory.create_stt(stt_config)
    
    # Use stt_plugin in AgentSession
    session = AgentSession(
        stt=stt_plugin,
        llm=llm_plugin,
        tts=tts_plugin
    )
    
    await session.start(room=ctx.room, agent=agent)
"""
