"""
Custom provider factories for non-LiveKit STT/LLM/TTS endpoints.

Use these when integrating third-party services that don't have LiveKit plugins.
"""

from .adapters import CustomHTTPSTTAdapter, CustomWebSocketSTTAdapter
from .base import STTConfig


class CustomProviderFactory:
    """Factory for creating custom (non-LiveKit) provider adapters."""
    
    @staticmethod
    def create_http_stt(config: STTConfig):
        """
        Create HTTP-based custom STT adapter.
        
        Config metadata should include:
        - endpoint_url: The HTTP endpoint for STT
        - api_key: Optional API key
        - headers: Optional additional headers
        - request_timeout: Optional timeout in seconds
        
        Example:
            config = STTConfig(
                provider=ProviderType.CUSTOM_HTTP,
                language="en-US",
                metadata={
                    "endpoint_url": "https://api.vendor.com/v1/stt",
                    "api_key": "your-api-key",
                    "headers": {"X-Custom-Header": "value"},
                    "request_timeout": 30
                }
            )
        """
        return CustomHTTPSTTAdapter(
            endpoint_url=config.metadata["endpoint_url"],
            api_key=config.metadata.get("api_key"),
            language=config.language,
            headers=config.metadata.get("headers"),
            request_timeout=config.metadata.get("request_timeout", 30)
        )
    
    @staticmethod
    def create_websocket_stt(config: STTConfig):
        """
        Create WebSocket-based custom STT adapter.
        
        Config metadata should include:
        - ws_url: The WebSocket endpoint for STT
        - api_key: Optional API key
        - sample_rate: Optional sample rate (default 16000)
        
        Example:
            config = STTConfig(
                provider=ProviderType.CUSTOM_WS,
                language="en-US",
                metadata={
                    "ws_url": "wss://api.vendor.com/v1/stt/stream",
                    "api_key": "your-api-key",
                    "sample_rate": 16000
                }
            )
        """
        return CustomWebSocketSTTAdapter(
            ws_url=config.metadata["ws_url"],
            api_key=config.metadata.get("api_key"),
            language=config.language,
            sample_rate=config.metadata.get("sample_rate", 16000)
        )


# Example: Specific vendor implementations

class DeepgramProviderFactory:
    """Factory for Deepgram STT (example of a specific vendor)."""
    
    @staticmethod
    def create_stt(config: STTConfig):
        """
        Create Deepgram STT adapter.
        
        Deepgram uses WebSocket for streaming.
        """
        api_key = config.metadata.get("api_key")
        model = config.model or "nova-2"
        
        ws_url = f"wss://api.deepgram.com/v1/listen?model={model}&language={config.language}"
        
        return CustomWebSocketSTTAdapter(
            ws_url=ws_url,
            api_key=api_key,
            language=config.language,
            sample_rate=config.metadata.get("sample_rate", 16000)
        )


class AssemblyAIProviderFactory:
    """Factory for AssemblyAI STT (example of another vendor)."""
    
    @staticmethod
    def create_stt(config: STTConfig):
        """
        Create AssemblyAI STT adapter.
        
        AssemblyAI uses WebSocket for real-time transcription.
        """
        api_key = config.metadata.get("api_key")
        
        ws_url = "wss://api.assemblyai.com/v2/realtime/ws"
        
        return CustomWebSocketSTTAdapter(
            ws_url=ws_url,
            api_key=api_key,
            language=config.language,
            sample_rate=config.metadata.get("sample_rate", 16000)
        )


class GoogleCloudSTTProviderFactory:
    """Factory for Google Cloud STT (example)."""
    
    @staticmethod
    def create_stt(config: STTConfig):
        """
        Create Google Cloud STT adapter.
        
        Note: This is a simplified example. Real implementation would need
        proper Google Cloud authentication and API format.
        """
        endpoint_url = config.metadata.get(
            "endpoint_url",
            "https://speech.googleapis.com/v1/speech:recognize"
        )
        
        return CustomHTTPSTTAdapter(
            endpoint_url=endpoint_url,
            api_key=config.metadata.get("api_key"),
            language=config.language,
            headers=config.metadata.get("headers", {}),
            request_timeout=config.metadata.get("request_timeout", 30)
        )
