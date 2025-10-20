"""
LiveKit Agent with pluggable AI providers using LiveKit's native lifecycle hooks and state management.
"""

import asyncio
import logging
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from livekit import rtc
from livekit.agents import (
    AutoSubscribe, 
    JobContext, 
    WorkerOptions, 
    cli,
    JobProcess,
    JobRequest
)
from livekit.plugins import openai, silero

from .providers import ProviderFactory
from .providers.base import (
    STTConfig, LLMConfig, TTSConfig,
    LLMMessage, ProviderType
)
from .config.settings import Settings
from .services.backend_client import BackendClient


logger = logging.getLogger(__name__)


class VoiceAssistantAgent:
    """
    Main voice assistant agent that orchestrates STT, LLM, and TTS providers.
    Uses LiveKit's native event system and state management.
    
    State is managed through:
    - LiveKit room.metadata for room-level state
    - LiveKit participant.metadata for user context
    - In-memory conversation history for current session
    - Backend API for persistent storage
    """

    def __init__(
        self,
        ctx: JobContext,
        stt_config: STTConfig,
        llm_config: LLMConfig,
        tts_config: TTSConfig,
        settings: Settings,
        backend_client: BackendClient
    ):
        self.ctx = ctx
        self.settings = settings
        self.backend_client = backend_client
        
        # Create providers
        self.stt_provider = ProviderFactory.create_stt_provider(stt_config)
        self.llm_provider = ProviderFactory.create_llm_provider(llm_config)
        self.tts_provider = ProviderFactory.create_tts_provider(tts_config)
        
        # LiveKit room (native state container)
        self.room: rtc.Room = ctx.room
        
        # Session state (in-memory for current session)
        self.conversation_history: List[LLMMessage] = []
        self._audio_source: Optional[rtc.AudioSource] = None
        self.session_start = datetime.utcnow()
        self.conversation_id: Optional[str] = None
        self.participant_states: Dict[str, Dict[str, Any]] = {}

    async def initialize(self):
        """Initialize all providers and load context from room metadata."""
        logger.info("Initializing voice assistant agent")
        
        await self.stt_provider.initialize()
        await self.llm_provider.initialize()
        await self.tts_provider.initialize()
        
        logger.info("All providers initialized successfully")
        
        # Load context from LiveKit room metadata (set by backend when creating room)
        await self._load_room_context()
        
        # Set up LiveKit native event handlers
        self._setup_event_handlers()
    
    async def _load_room_context(self):
        """Load conversation context from LiveKit room metadata."""
        if self.room.metadata:
            try:
                room_data = json.loads(self.room.metadata)
                self.conversation_id = room_data.get("conversation_id")
                
                logger.info(f"Loaded room context: conversation_id={self.conversation_id}")
                
                # Load recent conversation history from backend if available
                if self.conversation_id:
                    recent_messages = await self.backend_client.get_recent_messages(
                        conversation_id=self.conversation_id,
                        limit=10
                    )
                    if recent_messages:
                        self.conversation_history.extend(recent_messages)
                        logger.info(f"Loaded {len(recent_messages)} recent messages from backend")
            except json.JSONDecodeError:
                logger.warning(f"Could not parse room metadata: {self.room.metadata}")

    def _setup_event_handlers(self):
        """Set up LiveKit's native event handlers."""
        # Room events
        self.room.on("participant_connected", self._on_participant_connected)
        self.room.on("participant_disconnected", self._on_participant_disconnected)
        self.room.on("track_subscribed", self._on_track_subscribed)
        self.room.on("track_unsubscribed", self._on_track_unsubscribed)
        self.room.on("data_received", self._on_data_received)
        self.room.on("connection_quality_changed", self._on_connection_quality_changed)
        
        logger.info(f"Agent connected to room: {self.room.name}")

    async def _on_participant_connected(self, participant: rtc.RemoteParticipant):
        """Handle participant connection (LiveKit native event)."""
        logger.info(f"Participant connected: {participant.identity}")
        
        # Store participant state in memory
        participant_data = {
            "identity": participant.identity,
            "joined_at": datetime.utcnow().isoformat(),
            "metadata": participant.metadata
        }
        self.participant_states[participant.identity] = participant_data
        
        # Notify backend
        await self.backend_client.participant_connected(
            room_name=self.room.name,
            participant_identity=participant.identity,
            participant_metadata=participant.metadata
        )

    async def _on_participant_disconnected(self, participant: rtc.RemoteParticipant):
        """Handle participant disconnection (LiveKit native event)."""
        logger.info(f"Participant disconnected: {participant.identity}")
        
        # Update participant state
        if participant.identity in self.participant_states:
            self.participant_states[participant.identity]["left_at"] = datetime.utcnow().isoformat()
        
        # Notify backend
        await self.backend_client.participant_disconnected(
            room_name=self.room.name,
            participant_identity=participant.identity
        )

    async def _on_track_subscribed(
        self,
        track: rtc.Track,
        publication: rtc.TrackPublication,
        participant: rtc.RemoteParticipant
    ):
        """Handle new audio track subscription (LiveKit native event)."""
        if track.kind == rtc.TrackKind.KIND_AUDIO:
            logger.info(f"Subscribed to audio track from {participant.identity}")
            
            # Start processing audio stream
            asyncio.create_task(
                self._process_audio_stream(track, participant)
            )
    
    async def _on_track_unsubscribed(
        self,
        track: rtc.Track,
        publication: rtc.TrackPublication,
        participant: rtc.RemoteParticipant
    ):
        """Handle track unsubscription (LiveKit native event)."""
        logger.info(f"Unsubscribed from track {track.sid} from {participant.identity}")

    async def _on_data_received(self, data_packet: rtc.DataPacket):
        """Handle data messages (LiveKit native event) - e.g., file uploads, commands."""
        logger.info(f"Data received from {data_packet.participant.identity}, size: {len(data_packet.data)} bytes")
        
        # Send to backend for processing
        await self.backend_client.handle_file_upload(
            room_name=self.room.name,
            participant_identity=data_packet.participant.identity,
            data=data_packet.data
        )
    
    async def _on_connection_quality_changed(
        self,
        quality: rtc.ConnectionQuality,
        participant: rtc.Participant
    ):
        """Handle connection quality changes (LiveKit native event)."""
        logger.info(f"Connection quality for {participant.identity}: {quality}")

    async def _process_audio_stream(
        self,
        track: rtc.AudioTrack,
        participant: rtc.RemoteParticipant
    ):
        """Process audio stream through STT -> LLM -> TTS pipeline."""
        
        audio_stream = rtc.AudioStream(track)
        
        try:
            # Stream through STT
            async for stt_result in self.stt_provider.transcribe_stream(
                self._audio_stream_generator(audio_stream)
            ):
                if stt_result.is_final and stt_result.text.strip():
                    logger.info(f"User said: {stt_result.text}")
                    
                    # Add to in-memory conversation history
                    user_message = LLMMessage(
                        role="user",
                        content=stt_result.text
                    )
                    self.conversation_history.append(user_message)
                    
                    # Generate response using LLM
                    response_text = await self._generate_llm_response()
                    
                    # Add to conversation history
                    assistant_message = LLMMessage(
                        role="assistant",
                        content=response_text
                    )
                    self.conversation_history.append(assistant_message)
                    
                    logger.info(f"Assistant responds: {response_text}")
                    
                    # Convert to speech and stream back
                    await self._speak(response_text)
                    
                    # Save conversation turn to backend asynchronously (persistence layer)
                    asyncio.create_task(
                        self.backend_client.save_conversation_turn(
                            room_name=self.room.name,
                            participant_identity=participant.identity,
                            user_message=stt_result.text,
                            assistant_message=response_text,
                            metadata={
                                "stt_confidence": stt_result.confidence,
                                "stt_metadata": stt_result.metadata
                            }
                        )
                    )
                    
        except Exception as e:
            logger.error(f"Error processing audio stream: {e}", exc_info=True)

    async def _audio_stream_generator(self, audio_stream):
        """Generator to convert LiveKit audio stream to bytes."""
        async for frame in audio_stream:
            # Convert audio frame to bytes
            yield frame.data.tobytes()

    async def _generate_llm_response(self) -> str:
        """Generate response using LLM provider."""
        
        # Use streaming for real-time feel
        response_chunks = []
        
        async for chunk in self.llm_provider.generate_stream(
            self.conversation_history
        ):
            response_chunks.append(chunk)
        
        return "".join(response_chunks)

    async def _speak(self, text: str):
        """Convert text to speech and send to room."""
        
        if not self._audio_source:
            # Create audio source for TTS output
            self._audio_source = rtc.AudioSource(
                sample_rate=self.tts_provider.config.sample_rate,
                num_channels=1
            )
            
            # Publish audio track
            track = rtc.LocalAudioTrack.create_audio_track(
                "assistant_voice",
                self._audio_source
            )
            
            await self.room.local_participant.publish_track(
                track,
                rtc.TrackPublishOptions()
            )
        
        # Stream TTS audio
        async for audio_chunk in self.tts_provider.synthesize_stream(text):
            # Send audio to LiveKit room
            await self._audio_source.capture_frame(
                rtc.AudioFrame(
                    data=audio_chunk,
                    sample_rate=self.tts_provider.config.sample_rate,
                    num_channels=1,
                    samples_per_channel=len(audio_chunk) // 2  # 16-bit audio
                )
            )

    async def cleanup(self):
        """Clean up resources and save final session state."""
        logger.info("Cleaning up voice assistant agent")
        
        # Prepare session summary
        session_data = {
            "room_name": self.room.name,
            "conversation_id": self.conversation_id,
            "session_start": self.session_start.isoformat(),
            "session_end": datetime.utcnow().isoformat(),
            "duration_seconds": (datetime.utcnow() - self.session_start).total_seconds(),
            "message_count": len(self.conversation_history),
            "participant_count": len(self.participant_states),
            "participants": list(self.participant_states.values()),
            "messages": [
                {"role": msg.role, "content": msg.content}
                for msg in self.conversation_history
            ]
        }
        
        # Save session to backend asynchronously
        try:
            await self.backend_client.save_session(session_data)
            logger.info(f"Session saved: {len(self.conversation_history)} messages")
        except Exception as e:
            logger.error(f"Error saving session to backend: {e}", exc_info=True)
        
        # Clean up providers
        await self.stt_provider.cleanup()
        await self.llm_provider.cleanup()
        await self.tts_provider.cleanup()
        
        # Clean up backend client
        await self.backend_client.cleanup()
        
        logger.info("Cleanup complete")


async def entrypoint(ctx: JobContext):
    """
    Entry point for the LiveKit agent (using LiveKit's native lifecycle and state management).
    This function is called when a new job is assigned.
    
    State Management:
    - LiveKit manages room/participant state natively
    - Agent uses in-memory state for current session
    - Backend API used for persistent storage
    """
    logger.info(f"Starting agent for room: {ctx.room.name}")
    
    # Load settings
    settings = Settings()
    
    # Initialize backend client
    backend_client = BackendClient(settings)
    
    # Create provider configs from settings
    stt_config = STTConfig(
        provider=ProviderType(settings.stt_provider),
        model=settings.stt_model,
        language=settings.stt_language,
        metadata={"api_key": settings.openai_api_key}  # Adapt based on provider
    )
    
    llm_config = LLMConfig(
        provider=ProviderType(settings.llm_provider),
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        system_prompt=settings.llm_system_prompt,
        metadata={"api_key": settings.openai_api_key}
    )
    
    tts_config = TTSConfig(
        provider=ProviderType(settings.tts_provider),
        voice=settings.tts_voice,
        model=settings.tts_model,
        metadata={"api_key": settings.openai_api_key}
    )
    
    # Create and initialize agent
    agent = VoiceAssistantAgent(
        ctx=ctx,
        stt_config=stt_config,
        llm_config=llm_config,
        tts_config=tts_config,
        settings=settings,
        backend_client=backend_client
    )
    
    await agent.initialize()
    
    # Notify backend that agent joined (backend will create conversation record)
    agent.conversation_id = await backend_client.agent_joined(
        room_name=ctx.room.name,
        agent_metadata={
            "stt_provider": settings.stt_provider,
            "llm_provider": settings.llm_provider,
            "tts_provider": settings.tts_provider
        }
    )
    
    logger.info(f"Agent initialized with conversation_id: {agent.conversation_id}")
    
    # Connect to room (LiveKit handles the connection lifecycle)
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    
    logger.info(f"Agent connected to room {ctx.room.name}")
    
    # Keep agent running (LiveKit manages the lifecycle)
    await ctx.wait_for_disconnection()
    
    # Cleanup on disconnection
    logger.info(f"Agent disconnecting from room {ctx.room.name}")
    await agent.cleanup()


if __name__ == "__main__":
    # Run the agent
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
        )
    )
