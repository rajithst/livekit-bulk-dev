"""
Backend configuration settings.
"""

import os
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field, PostgresDsn


class Settings(BaseSettings):
    """Backend application settings."""

    # Application
    app_name: str = "Voice Assistant Backend"
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    
    # Server
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    
    # Security
    secret_key: str = Field(..., env="SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, env="REFRESH_TOKEN_EXPIRE_DAYS")
    
    # CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        env="CORS_ORIGINS"
    )
    
    # Database
    database_url: PostgresDsn = Field(..., env="DATABASE_URL")
    db_pool_size: int = Field(default=10, env="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=20, env="DB_MAX_OVERFLOW")
    
    # Redis
    redis_url: str = Field(..., env="REDIS_URL")
    redis_cache_ttl: int = Field(default=300, env="REDIS_CACHE_TTL")
    
    # LiveKit
    livekit_url: str = Field(..., env="LIVEKIT_URL")
    livekit_api_key: str = Field(..., env="LIVEKIT_API_KEY")
    livekit_api_secret: str = Field(..., env="LIVEKIT_API_SECRET")
    
    # Azure Blob Storage
    azure_storage_connection_string: str = Field(..., env="AZURE_STORAGE_CONNECTION_STRING")
    azure_storage_container_conversations: str = Field(
        default="conversations",
        env="AZURE_STORAGE_CONTAINER_CONVERSATIONS"
    )
    azure_storage_container_uploads: str = Field(
        default="uploads",
        env="AZURE_STORAGE_CONTAINER_UPLOADS"
    )
    
    # Rate Limiting
    rate_limit_per_minute: int = Field(default=60, env="RATE_LIMIT_PER_MINUTE")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Monitoring
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    sentry_dsn: str = Field(default=None, env="SENTRY_DSN")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()
