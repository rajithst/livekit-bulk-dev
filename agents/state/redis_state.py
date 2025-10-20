"""
Redis-based state backend for distributed state management.
"""

import logging
from typing import Optional, List
import redis.asyncio as redis


logger = logging.getLogger(__name__)


class RedisStateBackend:
    """Redis implementation of state backend."""

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.client: Optional[redis.Redis] = None

    async def initialize(self):
        """Initialize Redis connection."""
        self.client = await redis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
        logger.info("Redis state backend initialized")

    async def get(self, key: str) -> Optional[str]:
        """Get value by key."""
        return await self.client.get(key)

    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> None:
        """Set value with optional TTL."""
        if ttl:
            await self.client.setex(key, ttl, value)
        else:
            await self.client.set(key, value)

    async def delete(self, key: str) -> None:
        """Delete key."""
        await self.client.delete(key)

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        return await self.client.exists(key)

    async def sadd(self, key: str, *values: str) -> None:
        """Add to set."""
        await self.client.sadd(key, *values)

    async def srem(self, key: str, *values: str) -> None:
        """Remove from set."""
        await self.client.srem(key, *values)

    async def smembers(self, key: str) -> List[str]:
        """Get all set members."""
        members = await self.client.smembers(key)
        return list(members)

    async def cleanup(self):
        """Close Redis connection."""
        if self.client:
            await self.client.close()
            logger.info("Redis connection closed")
