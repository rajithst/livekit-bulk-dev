# Scalable State Management Implementation Guide

## Problem Statement
The default in-memory conversation history doesn't scale well because:
1. Each LiveKit agent runs in a **separate process** (isolated memory)
2. Memory grows with conversation length
3. State lost on agent restart/crash
4. Cannot share context across agent instances

## Solution: Redis-Backed State Management

### Architecture
```
Agent Process 1 ──┐
Agent Process 2 ──┼──► Redis (Shared Cache) ──► PostgreSQL (Persistent)
Agent Process 3 ──┘
```

## Implementation

### 1. Install Dependencies
```bash
pip install redis aioredis
```

### 2. Redis State Manager (`agents/state/redis_state.py`)

```python
import json
import logging
from typing import List, Optional
from datetime import timedelta
import aioredis
from .base import LLMMessage

logger = logging.getLogger(__name__)


class RedisStateManager:
    """
    Redis-backed state manager for scalable conversation history.
    Provides fast access with automatic TTL and backend sync.
    """
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        ttl_seconds: int = 3600,  # 1 hour default
        max_history_size: int = 100
    ):
        self.redis_url = redis_url
        self.ttl = ttl_seconds
        self.max_history_size = max_history_size
        self.redis: Optional[aioredis.Redis] = None
        
    async def initialize(self):
        """Connect to Redis."""
        self.redis = await aioredis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
        logger.info("Redis state manager initialized")
        
    async def cleanup(self):
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()
            
    def _get_key(self, conversation_id: str) -> str:
        """Generate Redis key for conversation."""
        return f"conversation:{conversation_id}:history"
        
    async def get_history(
        self,
        conversation_id: str,
        limit: Optional[int] = None
    ) -> List[LLMMessage]:
        """
        Get conversation history from Redis.
        Falls back to empty list if not found.
        """
        if not self.redis:
            logger.warning("Redis not initialized, returning empty history")
            return []
            
        key = self._get_key(conversation_id)
        
        try:
            # Get all messages (stored as JSON strings in a list)
            messages_json = await self.redis.lrange(key, 0, -1)
            
            messages = [
                LLMMessage(**json.loads(msg))
                for msg in messages_json
            ]
            
            # Apply limit if specified
            if limit:
                messages = messages[-limit:]
                
            logger.info(
                f"Retrieved {len(messages)} messages from Redis",
                extra={"conversation_id": conversation_id}
            )
            return messages
            
        except Exception as e:
            logger.error(
                f"Failed to get history from Redis: {e}",
                extra={"conversation_id": conversation_id}
            )
            return []
            
    async def append_message(
        self,
        conversation_id: str,
        message: LLMMessage
    ) -> bool:
        """
        Append a message to conversation history in Redis.
        Automatically trims to max_history_size.
        """
        if not self.redis:
            logger.warning("Redis not initialized, cannot append message")
            return False
            
        key = self._get_key(conversation_id)
        
        try:
            # Serialize message to JSON
            message_json = json.dumps({
                "role": message.role,
                "content": message.content,
                "timestamp": message.timestamp if hasattr(message, "timestamp") else None
            })
            
            # Append to list
            await self.redis.rpush(key, message_json)
            
            # Trim to max size (keep most recent)
            await self.redis.ltrim(key, -self.max_history_size, -1)
            
            # Set TTL
            await self.redis.expire(key, self.ttl)
            
            logger.debug(
                f"Appended message to Redis",
                extra={"conversation_id": conversation_id, "role": message.role}
            )
            return True
            
        except Exception as e:
            logger.error(
                f"Failed to append message to Redis: {e}",
                extra={"conversation_id": conversation_id}
            )
            return False
            
    async def clear_history(self, conversation_id: str) -> bool:
        """Clear conversation history from Redis."""
        if not self.redis:
            return False
            
        key = self._get_key(conversation_id)
        
        try:
            await self.redis.delete(key)
            logger.info(
                f"Cleared history from Redis",
                extra={"conversation_id": conversation_id}
            )
            return True
            
        except Exception as e:
            logger.error(
                f"Failed to clear history from Redis: {e}",
                extra={"conversation_id": conversation_id}
            )
            return False
            
    async def get_history_size(self, conversation_id: str) -> int:
        """Get the number of messages in conversation history."""
        if not self.redis:
            return 0
            
        key = self._get_key(conversation_id)
        
        try:
            return await self.redis.llen(key)
        except Exception as e:
            logger.error(f"Failed to get history size: {e}")
            return 0
```

### 3. Update Agent to Use Redis (`agents/core/agent.py`)

```python
from .state.redis_state import RedisStateManager

class VoiceAssistantAgent(Agent):
    
    def __init__(
        self,
        settings: Settings,
        backend_client: BackendClient,
        use_redis: bool = True,  # Toggle Redis on/off
        **kwargs
    ):
        super().__init__(**kwargs)
        self.settings = settings
        self.backend_client = backend_client
        
        # Initialize Redis state manager if enabled
        self.use_redis = use_redis
        if use_redis:
            self.redis_state = RedisStateManager(
                redis_url=settings.redis_url,
                ttl_seconds=settings.redis_ttl,
                max_history_size=50  # Keep last 50 messages
            )
        else:
            self.redis_state = None
            
        # In-memory fallback/cache
        self.conversation_history: List[LLMMessage] = []
        
    async def on_enter(self) -> None:
        """Called when the agent becomes active in a session."""
        logger.info("Agent becoming active in session")
        
        # Initialize Redis if enabled
        if self.redis_state:
            await self.redis_state.initialize()
        
        # ... provider initialization ...
        
        # Load conversation history
        if self.conversation_id:
            if self.redis_state:
                # Try Redis first
                self.conversation_history = await self.redis_state.get_history(
                    self.conversation_id,
                    limit=20  # Last 20 messages for context
                )
                
                # If Redis is empty, load from backend and populate Redis
                if not self.conversation_history and self.backend_client:
                    self.conversation_history = await self.backend_client.get_recent_messages(
                        conversation_id=self.conversation_id,
                        limit=20
                    )
                    # Populate Redis cache
                    for msg in self.conversation_history:
                        await self.redis_state.append_message(
                            self.conversation_id,
                            msg
                        )
            else:
                # Fallback to direct backend load
                if self.backend_client:
                    self.conversation_history = await self.backend_client.get_recent_messages(
                        conversation_id=self.conversation_id,
                        limit=20
                    )
                    
        logger.info(f"Loaded {len(self.conversation_history)} messages from history")
        
    async def _handle_conversation_item(self, event: "ConversationItemAddedEvent") -> None:
        """Handle conversation updates for both user and agent messages."""
        if not self.conversation_id:
            return

        message = LLMMessage(
            role=event.item.role,
            content=event.item.text_content
        )
        
        # Update in-memory cache
        self.conversation_history.append(message)
        
        # Trim in-memory to prevent unlimited growth
        if len(self.conversation_history) > 50:
            self.conversation_history = self.conversation_history[-20:]
        
        # Persist to Redis (fast, async)
        if self.redis_state:
            await self.redis_state.append_message(
                self.conversation_id,
                message
            )
        
        # Persist to backend (slower, fire-and-forget)
        asyncio.create_task(
            self.backend_client.store_message(
                conversation_id=self.conversation_id,
                message=message
            )
        )
        
        # ... rest of the handler ...
        
    async def cleanup(self):
        """Clean up resources and save final session state."""
        logger.info("Cleaning up voice assistant agent")
        
        # Close Redis connection
        if self.redis_state:
            await self.redis_state.cleanup()
        
        # ... rest of cleanup ...
```

### 4. Configuration (`agents/config/settings.py`)

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # ... existing settings ...
    
    # Redis Configuration
    redis_url: str = "redis://localhost:6379"
    redis_ttl: int = 3600  # 1 hour
    use_redis_cache: bool = True
    
    class Config:
        env_file = ".env"
```

### 5. Docker Compose with Redis (`docker-compose.yml`)

```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  livekit:
    image: livekit/livekit-server:latest
    # ... existing config ...

  agent:
    build:
      context: .
      dockerfile: docker/Dockerfile.agent
    depends_on:
      - redis
      - livekit
    environment:
      - REDIS_URL=redis://redis:6379
      - USE_REDIS_CACHE=true
    # ... rest of config ...

volumes:
  redis_data:
```

## Benefits

### Performance
- ⚡ **Fast**: Redis in-memory access (~1ms latency)
- 🔄 **Shared**: All agent processes access same cache
- 📦 **Automatic cleanup**: TTL expires old conversations

### Scalability
- 📈 **Horizontal scaling**: Add more agent servers
- 💾 **Memory efficient**: Bounded history size
- 🔁 **Session resumption**: State survives agent restarts

### Reliability
- ✅ **Dual persistence**: Redis + Backend database
- 🛡️ **Graceful fallback**: Works without Redis
- 📊 **Monitoring**: Redis metrics available

## Monitoring

### Redis Metrics
```python
# Add to metrics collection
redis_hits = meter.create_counter(
    name="redis_cache_hits",
    description="Number of Redis cache hits"
)

redis_misses = meter.create_counter(
    name="redis_cache_misses",
    description="Number of Redis cache misses"
)
```

### Health Check
```python
async def check_redis_health(self) -> bool:
    """Check if Redis is healthy."""
    try:
        await self.redis.ping()
        return True
    except Exception:
        return False
```

## Testing

### Unit Tests
```python
import pytest
from agents.state.redis_state import RedisStateManager

@pytest.mark.asyncio
async def test_redis_state_manager():
    manager = RedisStateManager(redis_url="redis://localhost:6379")
    await manager.initialize()
    
    # Test append
    message = LLMMessage(role="user", content="Hello")
    success = await manager.append_message("conv_123", message)
    assert success
    
    # Test retrieve
    history = await manager.get_history("conv_123")
    assert len(history) == 1
    assert history[0].content == "Hello"
    
    await manager.cleanup()
```

## Migration Strategy

### Phase 1: Add Redis (no breaking changes)
```python
# Enable Redis but keep in-memory as fallback
use_redis: bool = True
```

### Phase 2: Monitor & Tune
- Watch Redis memory usage
- Adjust TTL and max_history_size
- Monitor cache hit rates

### Phase 3: Optimize
- Add Redis clustering for HA
- Implement read replicas
- Add compression for large conversations

This approach gives you the best of both worlds: fast in-memory access with Redis, persistent storage in your database, and graceful fallback if Redis is unavailable.
