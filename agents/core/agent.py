"""
LiveKit Agent with pluggable AI providers using LiveKit's native event system.

This agent uses LiveKit's plugin system to handle all audio streaming, STT/LLM/TTS processing.
No manual audio buffering or chunk management is required - LiveKit handles it all automatically.
"""

import asyncio
import logging
import json
from datetime import datetime
from typing import Optional, Dict, Any, List

from livekit.agents import (
    Agent,
    AgentSession,
    AutoSubscribe, 
    JobContext, 
    WorkerOptions, 
    cli,
    RoomInputOptions,
    UserInputTranscribedEvent,
    ConversationItemAddedEvent,
    SpeechCreatedEvent,
    AgentStateChangedEvent,
    UserStateChangedEvent,
    ErrorEvent
)
from livekit.agents import llm

from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader
)
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.metrics.view import View
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes

from .providers import ProviderFactory
from .providers.base import (
    STTConfig, LLMConfig, TTSConfig,
    LLMMessage, ProviderType
)
from .config.settings import Settings
from .services.backend_client import BackendClient


logger = logging.getLogger(__name__)


class VoiceAssistantAgent(Agent):
    """
    Main voice assistant agent that orchestrates STT, LLM, and TTS providers.
    Uses LiveKit's native event system and state management.
    
    Inherits from LiveKit's Agent class to properly integrate with the LiveKit ecosystem.
    
    State is managed through:
    - LiveKit room.metadata for room-level state
    - LiveKit participant.metadata for user context
    - In-memory conversation history for current session
    - Backend API for persistent storage
    """

    def _setup_metrics(self):
        """Initialize OpenTelemetry metrics."""
        # Create resource for the agent
        resource = Resource.create({
            ResourceAttributes.SERVICE_NAME: "voice_assistant",
            ResourceAttributes.SERVICE_VERSION: "1.0",
            "agent.type": "voice_assistant",
        })

        # Set up metric readers
        prometheus_reader = PrometheusMetricReader()
        console_reader = PeriodicExportingMetricReader(
            ConsoleMetricExporter(),
            export_interval_millis=5000
        )

        # Create and set meter provider
        provider = MeterProvider(
            resource=resource,
            metric_readers=[prometheus_reader, console_reader],
            views=[
                # Custom views for specific metrics if needed
                View(
                    instrument_name="stt_latency",
                    aggregation=metrics.ExponentialHistogram()
                )
            ]
        )
        metrics.set_meter_provider(provider)

        # Create meter for our agent
        meter = metrics.get_meter("voice_assistant")

        # STT Metrics
        self.metrics.stt_latency = meter.create_histogram(
            name="stt_latency",
            description="Speech-to-text transcription latency",
            unit="s"
        )
        self.metrics.stt_confidence = meter.create_histogram(
            name="stt_confidence",
            description="Speech-to-text confidence scores",
            unit="1"
        )
        self.metrics.stt_interim_results = meter.create_counter(
            name="stt_interim_results",
            description="Number of interim STT results"
        )
        self.metrics.stt_final_results = meter.create_counter(
            name="stt_final_results",
            description="Number of final STT results"
        )

        # LLM Metrics
        self.metrics.llm_latency = meter.create_histogram(
            name="llm_latency",
            description="LLM response generation latency",
            unit="s"
        )
        self.metrics.llm_tokens = meter.create_up_down_counter(
            name="llm_tokens",
            description="Total tokens processed by LLM",
            unit="1"
        )
        self.metrics.llm_response_tokens = meter.create_histogram(
            name="llm_response_tokens",
            description="Number of tokens in LLM responses",
            unit="1"
        )

        # TTS Metrics
        self.metrics.tts_latency = meter.create_histogram(
            name="tts_latency",
            description="Text-to-speech synthesis latency",
            unit="s"
        )
        self.metrics.tts_audio_duration = meter.create_histogram(
            name="tts_audio_duration",
            description="Duration of synthesized audio",
            unit="s"
        )

        # Error Metrics with attributes
        self.metrics.errors = meter.create_counter(
            name="errors",
            description="Number of errors by type",
            unit="1"
        )

        # Session Metrics
        self.metrics.session_duration = meter.create_observable_gauge(
            name="session_duration",
            description="Current session duration",
            unit="s",
            callbacks=[self._get_session_duration]
        )

        # Performance Attributes
        self.metrics.attributes = {
            "provider.stt": getattr(self.stt_config, "provider", "unknown").value,
            "provider.llm": getattr(self.llm_config, "provider", "unknown").value,
            "provider.tts": getattr(self.tts_config, "provider", "unknown").value,
            "model.stt": getattr(self.stt_config, "model", "unknown"),
            "model.llm": getattr(self.llm_config, "model", "unknown"),
            "model.tts": getattr(self.tts_config, "model", "unknown")
        }

    def _get_session_duration(self, callback):
        """Callback for observable session duration metric."""
        duration = (datetime.utcnow() - self.session_start).total_seconds()
        callback.observe(duration, self.metrics.attributes)
        
    def __init__(
        self,
        settings: Settings,
        backend_client: BackendClient,
        stt_config: Optional[STTConfig] = None,
        llm_config: Optional[LLMConfig] = None,
        tts_config: Optional[TTSConfig] = None,
        instructions: str = "You are a helpful voice AI assistant"
    ):
        super().__init__(instructions=instructions)
        self.settings = settings
        self.backend_client = backend_client
        
        # Store configs for observability/metrics only
        # These are NOT used to create plugins - plugins are created in entrypoint()
        # and passed to AgentSession. We keep configs here to:
        # 1. Populate metrics attributes (provider/model info)
        # 2. Log metadata to backend (track what models were used)
        # 3. Enable debugging (know exact configuration for this session)
        self.stt_config = stt_config
        self.llm_config = llm_config
        self.tts_config = tts_config
        
        # Initialize metrics (uses config info for attributes)
        self._setup_metrics()
        
        # Session state
        self.conversation_history: List[LLMMessage] = []
        self.session_start = datetime.utcnow()
        self.conversation_id: Optional[str] = None
        self.participant_states: Dict[str, Dict[str, Any]] = {}
        
        # Performance tracking
        self.total_stt_latency = 0.0
        self.total_llm_latency = 0.0
        self.total_tts_latency = 0.0
        self.request_count = 0

    async def on_enter(self) -> None:
        """Called when the agent becomes active in a session."""
        logger.info("Agent becoming active in session")
        
        # Set up LiveKit event handlers in the session
        self.session.on("user_input_transcribed", self._handle_transcription)
        self.session.on("conversation_item_added", self._handle_conversation_item)
        self.session.on("speech_created", self._handle_speech_created)
        self.session.on("agent_state_changed", self._handle_agent_state)
        self.session.on("user_state_changed", self._handle_user_state)
        self.session.on("error", self._handle_error)
        
        # Load context from room metadata
        if self.session.room.metadata:
            try:
                room_data = json.loads(self.session.room.metadata)
                self.conversation_id = room_data.get("conversation_id")
            except json.JSONDecodeError:
                logger.error("Failed to parse room metadata")
        
        # Greet the user with a warm welcome
        await self.session.generate_reply(
            instructions="Greet the user with a warm welcome"
        )
        
        # Load recent conversation history from backend if available
        if self.conversation_id and self.backend_client:
            recent_messages = await self.backend_client.get_recent_messages(
                conversation_id=self.conversation_id,
                limit=10
            )
            if recent_messages:
                self.conversation_history.extend(recent_messages)
                logger.info(f"Loaded {len(recent_messages)} recent messages from backend")

    async def on_exit(self) -> None:
        """Called before the agent gives control to another agent."""
        # Say goodbye before exiting
        await self.session.generate_reply(
            instructions="Tell the user a friendly goodbye before you exit."
        )
        
        # Save conversation state if needed
        if self.backend_client and self.conversation_id:
            await self.backend_client.save_conversation_state(
                conversation_id=self.conversation_id,
                messages=self.conversation_history
            )

    async def on_user_turn_completed(
        self,
        turn_ctx: llm.ChatContext,
        new_message: llm.ChatMessage
    ) -> None:
        """
        Called when the user's turn has ended, before the agent's reply.
        This is where we can modify the user's message or add context before processing.
        """
        # Add the message to our conversation history
        self.conversation_history.append(
            LLMMessage(role="user", content=new_message.text_content)
        )
        
        # Optional: Modify message content if needed
        # Example: Filter out offensive content or add context

        # new_message.content = filter_offensive_content(new_message.content)
        
        # Add any relevant context from our backend
        if self.backend_client:
            context = await self.backend_client.get_relevant_context(
                new_message.text_content
            )
            if context:
                turn_ctx.add_message(
                    role="assistant",
                    content=f"Additional context: {context}"
                )
                
    async def _handle_transcription(self, event: "UserInputTranscribedEvent") -> None:
        """Handle STT transcription events."""
        if not event.is_final:
            # Update metrics with attributes
            attributes = {
                **self.metrics.attributes,
                "conversation_id": self.conversation_id,
                "language": event.language,
                "speaker_id": event.speaker_id,
                "is_final": str(event.is_final)
            }
            self.metrics.stt_interim_results.add(1, attributes)
            return

        if not self.conversation_id:
            return

        # Update metrics for final transcription
        self.metrics.stt_final_results.add(1, attributes)
        
        if hasattr(event, "latency"):
            self.metrics.stt_latency.record(event.latency, attributes)
            
        if hasattr(event, "confidence"):
            self.metrics.stt_confidence.record(event.confidence, attributes)

        # Store transcription in database
        asyncio.create_task(
            self.backend_client.store_transcription(
                conversation_id=self.conversation_id,
                text=event.transcript,
                metadata={
                    "language": event.language,
                    "speaker_id": event.speaker_id,
                    "is_final": event.is_final,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        )

    async def _handle_conversation_item(self, event: "ConversationItemAddedEvent") -> None:
        """Handle conversation updates for both user and agent messages."""
        if not self.conversation_id:
            return

        # Store message in conversation history
        self.conversation_history.append(
            LLMMessage(role=event.item.role, content=event.item.text_content)
        )

        # For LLM responses, store additional metadata and update metrics
        if event.item.role == "assistant":
            # Get token counts for metrics
            total_tokens = len(event.item.text_content.split())
            
            # Update metrics with attributes
            attributes = {
                **self.metrics.attributes,
                "conversation_id": self.conversation_id,
                "interrupted": str(event.item.interrupted)
            }
            
            self.metrics.llm_tokens.add(total_tokens, attributes)
            if hasattr(event.item, "latency"):
                self.metrics.llm_latency.record(event.item.latency, attributes)
            if hasattr(event.item, "prompt"):
                self.metrics.llm_response_tokens.record(
                    len(event.item.prompt.split()),
                    attributes
                )
            
            # Store in backend
            asyncio.create_task(
                self.backend_client.store_llm_response(
                    conversation_id=self.conversation_id,
                    prompt=event.item.prompt if hasattr(event.item, "prompt") else "",
                    response=event.item.text_content,
                    metadata={
                        "model": getattr(self.llm_config, "model", "unknown"),
                        "provider": getattr(self.llm_config, "provider", ProviderType.UNKNOWN).value,
                        "interrupted": event.item.interrupted,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
            )

    async def _handle_speech_created(self, event: "SpeechCreatedEvent") -> None:
        """Handle TTS speech generation events."""
        if not self.conversation_id:
            return

        # Update metrics with attributes
        text = event.speech_handle.text if hasattr(event.speech_handle, "text") else ""
        attributes = {
            **self.metrics.attributes,
            "conversation_id": self.conversation_id,
            "source": event.source,
            "user_initiated": str(event.user_initiated)
        }

        # Record TTS metrics
        self.metrics.tts_requests.add(1, attributes)
        self.metrics.tts_characters.add(len(text), attributes)
        
        if hasattr(event, "latency"):
            self.metrics.tts_latency.record(event.latency, attributes)
            
        if hasattr(event.speech_handle, "duration_ms"):
            self.metrics.tts_audio_duration.record(
                event.speech_handle.duration_ms / 1000.0,
                attributes
            )

        # Store TTS metadata
        asyncio.create_task(
            self.backend_client.store_tts_metadata(
                conversation_id=self.conversation_id,
                text=text,
                metadata={
                    "source": event.source,
                    "user_initiated": event.user_initiated,
                    "model": getattr(self.tts_config, "model", "unknown"),
                    "provider": getattr(self.tts_config, "provider", ProviderType.UNKNOWN).value,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        )

    async def _handle_agent_state(self, event: "AgentStateChangedEvent") -> None:
        """Handle agent state changes."""
        logger.info(f"Agent state changed: {event.old_state} -> {event.new_state}")
        
        # Update session duration metric
        session_duration = (datetime.utcnow() - self.session_start).total_seconds()
        self.metrics.session_duration.set(session_duration)

    async def _handle_user_state(self, event: "UserStateChangedEvent") -> None:
        """Handle user state changes."""
        logger.info(f"User state changed: {event.old_state} -> {event.new_state}")
        
        # Handle user going away
        if event.new_state == "away":
            await self.session.generate_reply(
                instructions="The user has been inactive. Ask if they're still there or need help."
            )

    async def _handle_error(self, event: "ErrorEvent") -> None:
        """Handle errors during the session."""
        logger.error(
            f"Error in {event.source}: {event.error}",
            extra={"recoverable": event.error.recoverable}
        )
        
        # Update error metrics with attributes
        attributes = {
            **self.metrics.attributes,
            "conversation_id": self.conversation_id,
            "source": str(event.source),
            "recoverable": str(event.error.recoverable),
            "error_type": event.error.__class__.__name__
        }
        self.metrics.errors.add(1, attributes)

        if not event.error.recoverable:
            # Inform user of the error
            await self.session.say(
                "I apologize, but I'm experiencing some technical difficulties. " 
                "Please try again in a moment."
            )
            
            # Log unrecoverable error to backend
            if self.backend_client and self.conversation_id:
                await self.backend_client.log_error(
                    room_name=self.session.room.name,
                    error_type=str(event.source),
                    error_message=str(event.error),
                    stack_trace=getattr(event.error, "stack_trace", None)
                )

    async def cleanup(self):
        """Clean up resources and save final session state."""
        logger.info("Cleaning up voice assistant agent")
        
        if self.conversation_id and self.backend_client:
            # Save final conversation state
            await self.backend_client.save_conversation_state(
                conversation_id=self.conversation_id,
                messages=self.conversation_history
            )
        
        # Clean up backend client
        if self.backend_client:
            await self.backend_client.cleanup()
        
        logger.info("Cleanup complete")


async def entrypoint(ctx: JobContext):
    """
    Entry point for the LiveKit agent job.
    Handles agent initialization, room connection, and lifecycle management.
    """
    # Set up logging context
    ctx.log_context_fields = {
        "worker_id": ctx.worker_id,
        "room_name": ctx.room.name,
        "job_id": ctx.job.id
    }
    
    logger.info("Initializing agent job", extra=ctx.log_context_fields)
    
    # Load settings and create backend client
    settings = Settings()
    backend_client = BackendClient(settings)
    
    # Load job metadata if provided
    if ctx.job.metadata:
        try:
            metadata = json.loads(ctx.job.metadata)
            logger.info(f"Job metadata loaded: {metadata}", extra=ctx.log_context_fields)
        except json.JSONDecodeError:
            logger.warning("Failed to parse job metadata", extra=ctx.log_context_fields)
            metadata = {}
    else:
        metadata = {}
    
    # Create provider configs
    def get_provider_type(provider_string: str) -> ProviderType:
        """Safely convert provider string to ProviderType enum."""
        try:
            return ProviderType[provider_string.upper()]
        except (KeyError, AttributeError):
            logger.warning(f"Invalid provider type: {provider_string}, falling back to OPENAI")
            return ProviderType.OPENAI

    stt_config = STTConfig(
        provider=get_provider_type(settings.stt_provider),
        model=settings.stt_model,
        language=settings.stt_language,
        metadata={"api_key": settings.openai_api_key}
    )
    
    llm_config = LLMConfig(
        provider=get_provider_type(settings.llm_provider),
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        system_prompt=settings.llm_system_prompt,
        metadata={"api_key": settings.openai_api_key}
    )
    
    tts_config = TTSConfig(
        provider=get_provider_type(settings.tts_provider),
        voice=settings.tts_voice,
        model=settings.tts_model,
        metadata={"api_key": settings.openai_api_key}
    )
    
    # Create agent instance
    agent = VoiceAssistantAgent(
        settings=settings,
        backend_client=backend_client,
        stt_config=stt_config,  # Passed for metrics/observability only
        llm_config=llm_config,  # Passed for metrics/observability only
        tts_config=tts_config   # Passed for metrics/observability only
    )
    
    # Create LiveKit plugin instances from configs
    # These are the actual plugins that AgentSession uses for STT/LLM/TTS processing
    # LiveKit handles all audio streaming, buffering, and processing automatically
    stt_plugin = ProviderFactory.create_stt(stt_config)
    llm_plugin = ProviderFactory.create_llm(llm_config)
    tts_plugin = ProviderFactory.create_tts(tts_config)
    
    # Register shutdown hook for cleanup
    async def cleanup_hook():
        logger.info("Running cleanup hook", extra=ctx.log_context_fields)
        await agent.cleanup()
        await backend_client.cleanup()
    
    ctx.add_shutdown_callback(cleanup_hook)
    
    # Connect to the room
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    logger.info("Connected to room", extra=ctx.log_context_fields)
    
    try:
        # Wait for first participant
        participant = await ctx.wait_for_participant()
        logger.info(
            f"First participant joined: {participant.identity}",
            extra=ctx.log_context_fields
        )
        
        # Create conversation record in backend
        agent.conversation_id = await backend_client.agent_joined(
            room_name=ctx.room.name,
            agent_metadata={
                "stt_provider": settings.stt_provider,
                "llm_provider": settings.llm_provider,
                "tts_provider": settings.tts_provider,
                "participant": participant.identity
            }
        )
        
        # Start agent session with LiveKit plugins
        # LiveKit handles all audio streaming, buffering, and processing
        session = AgentSession(
            stt=stt_plugin,
            llm=llm_plugin,
            tts=tts_plugin
        )
        
        await session.start(
            room=ctx.room,
            agent=agent,
            room_input_options=RoomInputOptions(
                noise_cancellation=True
            )
        )
        
        # Keep running until all participants leave or job is terminated
        await ctx.wait_for_disconnection()
        
    except Exception as e:
        logger.error(f"Error in agent job: {str(e)}", exc_info=True, extra=ctx.log_context_fields)
        # Ensure proper cleanup on error
        ctx.shutdown(reason=f"Error occurred: {str(e)}")
    finally:
        logger.info("Agent job completed", extra=ctx.log_context_fields)


if __name__ == "__main__":
    # Run the agent
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
        )
    )
