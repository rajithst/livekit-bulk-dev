"""
Application settings and configuration management.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "Voice Assistant"
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    
    # LiveKit
    livekit_url: str = Field(..., env="LIVEKIT_URL")
    livekit_api_key: str = Field(..., env="LIVEKIT_API_KEY")
    livekit_api_secret: str = Field(..., env="LIVEKIT_API_SECRET")
    
    # STT Provider Configuration
    stt_provider: str = Field(default="openai", env="STT_PROVIDER")
    stt_model: Optional[str] = Field(default=None, env="STT_MODEL")
    stt_language: str = Field(default="en-US", env="STT_LANGUAGE")
    
    # LLM Provider Configuration
    llm_provider: str = Field(default="openai", env="LLM_PROVIDER")
    llm_model: str = Field(default="gpt-4", env="LLM_MODEL")
    llm_temperature: float = Field(default=0.7, env="LLM_TEMPERATURE")
    llm_max_tokens: int = Field(default=150, env="LLM_MAX_TOKENS")
    llm_system_prompt: str = Field(
        default="You are a helpful voice assistant. Keep responses concise and natural.",
        env="LLM_SYSTEM_PROMPT"
    )
    
    # TTS Provider Configuration
    tts_provider: str = Field(default="openai", env="TTS_PROVIDER")
    tts_model: Optional[str] = Field(default="tts-1", env="TTS_MODEL")
    tts_voice: str = Field(default="alloy", env="TTS_VOICE")
    
    # API Keys for AI Providers
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    azure_speech_key: Optional[str] = Field(default=None, env="AZURE_SPEECH_KEY")
    azure_speech_region: Optional[str] = Field(default=None, env="AZURE_SPEECH_REGION")
    azure_openai_key: Optional[str] = Field(default=None, env="AZURE_OPENAI_KEY")
    azure_openai_endpoint: Optional[str] = Field(default=None, env="AZURE_OPENAI_ENDPOINT")
    aws_access_key: Optional[str] = Field(default=None, env="AWS_ACCESS_KEY_ID")
    aws_secret_key: Optional[str] = Field(default=None, env="AWS_SECRET_ACCESS_KEY")
    aws_region: Optional[str] = Field(default="us-east-1", env="AWS_REGION")
    google_credentials_path: Optional[str] = Field(default=None, env="GOOGLE_CREDENTIALS_PATH")
    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    
    # Backend API
    backend_api_url: str = Field(..., env="BACKEND_API_URL")
    backend_api_key: str = Field(..., env="BACKEND_API_KEY")
    
    # Redis
    redis_url: Optional[str] = Field(default=None, env="REDIS_URL")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


def get_settings() -> Settings:
    """Get application settings singleton."""
    return Settings()
