"""
State manager for maintaining conversation and session state.
Supports both Redis (production) and in-memory (development) backends.
"""

import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
import uuid

from ..config.settings import Settings


logger = logging.getLogger(__name__)


class StateManager:
    """
    Manages application state across agent instances.
    Uses Redis for distributed state in production.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.backend = None
        self._use_redis = settings.redis_url is not None

    async def initialize(self):
        """Initialize state backend."""
        if self._use_redis:
            from .redis_state import RedisStateBackend
            self.backend = RedisStateBackend(self.settings.redis_url)
        else:
            from .memory_state import MemoryStateBackend
            self.backend = MemoryStateBackend()
            logger.warning("Using in-memory state backend - not suitable for production")
        
        await self.backend.initialize()

    async def create_conversation(
        self,
        room_name: str,
        participant_identity: str
    ) -> str:
        """Create a new conversation session."""
        conversation_id = str(uuid.uuid4())
        
        conversation_data = {
            "id": conversation_id,
            "room_name": room_name,
            "participant_identity": participant_identity,
            "started_at": datetime.utcnow().isoformat(),
            "messages": [],
            "metadata": {}
        }
        
        await self.backend.set(
            f"conversation:{room_name}",
            json.dumps(conversation_data),
            ttl=86400  # 24 hours
        )
        
        return conversation_id

    async def get_conversation(self, room_name: str) -> Optional[Dict[str, Any]]:
        """Get conversation data."""
        data = await self.backend.get(f"conversation:{room_name}")
        if data:
            return json.loads(data)
        return None

    async def add_message(
        self,
        room_name: str,
        role: str,
        content: str,
        metadata: Dict[str, Any]
    ) -> None:
        """Add a message to the conversation."""
        conversation = await self.get_conversation(room_name)
        if not conversation:
            logger.error(f"Conversation not found for room: {room_name}")
            return
        
        message = {
            "id": str(uuid.uuid4()),
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata
        }
        
        conversation["messages"].append(message)
        
        await self.backend.set(
            f"conversation:{room_name}",
            json.dumps(conversation),
            ttl=86400
        )

    async def add_participant(
        self,
        room_name: str,
        participant_identity: str
    ) -> None:
        """Track participant in room."""
        await self.backend.sadd(
            f"room:{room_name}:participants",
            participant_identity
        )

    async def remove_participant(
        self,
        room_name: str,
        participant_identity: str
    ) -> None:
        """Remove participant from room tracking."""
        await self.backend.srem(
            f"room:{room_name}:participants",
            participant_identity
        )

    async def get_participants(self, room_name: str) -> List[str]:
        """Get all participants in a room."""
        return await self.backend.smembers(f"room:{room_name}:participants")

    async def finalize_conversation(self, room_name: str) -> None:
        """Mark conversation as complete."""
        conversation = await self.get_conversation(room_name)
        if conversation:
            conversation["ended_at"] = datetime.utcnow().isoformat()
            await self.backend.set(
                f"conversation:{room_name}",
                json.dumps(conversation),
                ttl=604800  # Keep for 7 days
            )

    async def set_user_context(
        self,
        room_name: str,
        context_key: str,
        context_value: Any
    ) -> None:
        """Set custom context for a conversation."""
        conversation = await self.get_conversation(room_name)
        if conversation:
            conversation["metadata"][context_key] = context_value
            await self.backend.set(
                f"conversation:{room_name}",
                json.dumps(conversation),
                ttl=86400
            )

    async def get_user_context(
        self,
        room_name: str,
        context_key: str
    ) -> Optional[Any]:
        """Get custom context from conversation."""
        conversation = await self.get_conversation(room_name)
        if conversation:
            return conversation.get("metadata", {}).get(context_key)
        return None

    async def cleanup(self):
        """Clean up resources."""
        if self.backend:
            await self.backend.cleanup()
