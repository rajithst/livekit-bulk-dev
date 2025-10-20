"""
Backend API client for LiveKit agents to communicate with FastAPI backend.
"""

import logging
from typing import Any, Dict, Optional
import aiohttp

from ..config.settings import Settings


logger = logging.getLogger(__name__)


class BackendClient:
    """
    Client for communicating with the FastAPI backend.
    Handles all HTTP requests from agents to the backend service.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.backend_url = settings.backend_api_url
        self.api_key = settings.backend_api_key
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if not self.session:
            self.session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
            )
        return self.session

    async def agent_joined(
        self,
        room_name: str,
        agent_metadata: Dict[str, Any] = None
    ) -> str:
        """
        Notify backend that agent joined a room.
        Returns conversation_id for tracking.
        """
        try:
            session = await self._get_session()
            async with session.post(
                f"{self.backend_url}/api/v1/rooms/{room_name}/agent-joined",
                json={
                    "agent_metadata": agent_metadata or {},
                    "timestamp": self._get_timestamp()
                }
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    conversation_id = result.get("conversation_id")
                    logger.info(f"Agent joined room {room_name}, conversation_id: {conversation_id}")
                    return conversation_id
                else:
                    logger.error(f"Failed to notify agent joined: {response.status}")
                    # Generate fallback conversation ID
                    import uuid
                    return str(uuid.uuid4())
        except Exception as e:
            logger.error(f"Error notifying agent joined: {e}", exc_info=True)
            # Generate fallback conversation ID
            import uuid
            return str(uuid.uuid4())

    async def participant_connected(
        self,
        room_name: str,
        participant_identity: str,
        participant_metadata: str = None
    ) -> None:
        """
        Notify backend that a participant connected.
        """
        try:
            session = await self._get_session()
            async with session.post(
                f"{self.backend_url}/api/v1/analytics/participant-connected",
                json={
                    "room_name": room_name,
                    "participant_identity": participant_identity,
                    "metadata": participant_metadata,
                    "timestamp": self._get_timestamp()
                }
            ) as response:
                if response.status != 200:
                    logger.warning(f"Failed to log participant connected: {response.status}")
        except Exception as e:
            logger.error(f"Error logging participant connected: {e}", exc_info=True)

    async def participant_disconnected(
        self,
        room_name: str,
        participant_identity: str
    ) -> None:
        """
        Notify backend that a participant disconnected.
        """
        try:
            session = await self._get_session()
            async with session.post(
                f"{self.backend_url}/api/v1/analytics/participant-disconnected",
                json={
                    "room_name": room_name,
                    "participant_identity": participant_identity,
                    "timestamp": self._get_timestamp()
                }
            ) as response:
                if response.status != 200:
                    logger.warning(f"Failed to log participant disconnected: {response.status}")
        except Exception as e:
            logger.error(f"Error logging participant disconnected: {e}", exc_info=True)

    async def save_conversation_turn(
        self,
        room_name: str,
        participant_identity: str,
        user_message: str,
        assistant_message: str,
        metadata: Dict[str, Any] = None
    ) -> None:
        """
        Save a conversation turn (user message + assistant response).
        """
        try:
            session = await self._get_session()
            async with session.post(
                f"{self.backend_url}/api/v1/conversations/save-turn",
                json={
                    "room_name": room_name,
                    "participant_identity": participant_identity,
                    "user_message": user_message,
                    "assistant_message": assistant_message,
                    "metadata": metadata or {},
                    "timestamp": self._get_timestamp()
                }
            ) as response:
                if response.status != 200:
                    logger.error(f"Failed to save conversation turn: {response.status}")
                else:
                    logger.debug("Conversation turn saved successfully")
        except Exception as e:
            logger.error(f"Error saving conversation turn: {e}", exc_info=True)

    async def handle_file_upload(
        self,
        room_name: str,
        participant_identity: str,
        data: bytes
    ) -> Optional[Dict[str, Any]]:
        """
        Upload a file to the backend.
        """
        try:
            session = await self._get_session()
            
            form_data = aiohttp.FormData()
            form_data.add_field('file', data, filename='upload.bin')
            form_data.add_field('room_name', room_name)
            form_data.add_field('participant_identity', participant_identity)
            
            async with session.post(
                f"{self.backend_url}/api/v1/files/upload",
                data=form_data
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"File uploaded successfully: {result.get('file_id')}")
                    return result
                else:
                    logger.error(f"File upload failed: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error uploading file: {e}", exc_info=True)
            return None

    async def save_conversation(
        self,
        room_name: str,
        conversation_data: Dict[str, Any]
    ) -> None:
        """
        Save final conversation data to backend.
        """
        try:
            session = await self._get_session()
            async with session.post(
                f"{self.backend_url}/api/v1/conversations/finalize",
                json={
                    "room_name": room_name,
                    "conversation_data": conversation_data,
                    "timestamp": self._get_timestamp()
                }
            ) as response:
                if response.status != 200:
                    logger.error(f"Failed to save conversation: {response.status}")
                else:
                    logger.info(f"Conversation saved for room {room_name}")
        except Exception as e:
            logger.error(f"Error saving conversation: {e}", exc_info=True)

    async def get_user_context(
        self,
        participant_identity: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve user context from backend (e.g., preferences, history).
        """
        try:
            session = await self._get_session()
            async with session.get(
                f"{self.backend_url}/api/v1/users/{participant_identity}/context"
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.warning(f"Failed to get user context: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error getting user context: {e}", exc_info=True)
            return None

    async def log_error(
        self,
        room_name: str,
        error_type: str,
        error_message: str,
        stack_trace: str = None
    ) -> None:
        """
        Log an error to the backend for monitoring.
        """
        try:
            session = await self._get_session()
            async with session.post(
                f"{self.backend_url}/api/v1/analytics/log-error",
                json={
                    "room_name": room_name,
                    "error_type": error_type,
                    "error_message": error_message,
                    "stack_trace": stack_trace,
                    "timestamp": self._get_timestamp()
                }
            ) as response:
                pass  # Fire and forget
        except Exception as e:
            logger.error(f"Error logging error to backend: {e}")

    async def get_recent_messages(
        self,
        conversation_id: str,
        limit: int = 10
    ) -> list:
        """
        Get recent conversation messages from backend.
        Returns list of LLMMessage objects.
        """
        try:
            session = await self._get_session()
            async with session.get(
                f"{self.backend_url}/api/v1/conversations/{conversation_id}/messages",
                params={"limit": limit}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    # Convert to LLMMessage objects
                    from ..providers.base import LLMMessage
                    messages = [
                        LLMMessage(role=msg["role"], content=msg["content"])
                        for msg in data.get("messages", [])
                    ]
                    logger.info(f"Loaded {len(messages)} recent messages")
                    return messages
                else:
                    logger.warning(f"Failed to get recent messages: {response.status}")
                    return []
        except Exception as e:
            logger.error(f"Error getting recent messages: {e}", exc_info=True)
            return []

    async def save_session(
        self,
        session_data: Dict[str, Any]
    ) -> None:
        """
        Save session summary to backend.
        """
        try:
            session = await self._get_session()
            async with session.post(
                f"{self.backend_url}/api/v1/sessions/save",
                json=session_data
            ) as response:
                if response.status == 200:
                    logger.info(f"Session saved: {session_data.get('room_name')}")
                else:
                    logger.error(f"Failed to save session: {response.status}")
        except Exception as e:
            logger.error(f"Error saving session: {e}", exc_info=True)

    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime
        return datetime.utcnow().isoformat()

    async def cleanup(self):
        """Close HTTP session."""
        if self.session:
            await self.session.close()
            logger.info("Backend client session closed")
