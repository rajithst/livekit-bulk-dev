"""
In-memory state backend for development/testing.
"""

import logging
from typing import Optional, Dict, Set, List


logger = logging.getLogger(__name__)


class MemoryStateBackend:
    """In-memory implementation of state backend (for development)."""

    def __init__(self):
        self.store: Dict[str, str] = {}
        self.sets: Dict[str, Set[str]] = {}

    async def initialize(self):
        """Initialize (no-op for memory backend)."""
        logger.info("In-memory state backend initialized")

    async def get(self, key: str) -> Optional[str]:
        """Get value by key."""
        return self.store.get(key)

    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> None:
        """Set value (TTL ignored in memory backend)."""
        self.store[key] = value

    async def delete(self, key: str) -> None:
        """Delete key."""
        self.store.pop(key, None)

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        return key in self.store

    async def sadd(self, key: str, *values: str) -> None:
        """Add to set."""
        if key not in self.sets:
            self.sets[key] = set()
        self.sets[key].update(values)

    async def srem(self, key: str, *values: str) -> None:
        """Remove from set."""
        if key in self.sets:
            self.sets[key].difference_update(values)

    async def smembers(self, key: str) -> List[str]:
        """Get all set members."""
        return list(self.sets.get(key, set()))

    async def cleanup(self):
        """Clean up (no-op for memory backend)."""
        self.store.clear()
        self.sets.clear()
        logger.info("In-memory state cleared")
