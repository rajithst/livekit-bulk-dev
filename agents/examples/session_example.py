"""
Example of how to create and start a LiveKit agent session
"""

from livekit.agents import AgentSession, RoomInputOptions
from livekit.plugins import silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

from .core.agent import VoiceAssistantAgent
from .config.settings import Settings
from .services.backend_client import BackendClient

async def create_agent_session(
    ctx,
    settings: Settings,
    backend_client: BackendClient
) -> AgentSession:
    """
    Create and configure a LiveKit agent session with our custom VoiceAssistantAgent.
    """
    # Create our custom agent
    agent = VoiceAssistantAgent(
        settings=settings,
        backend_client=backend_client,
        instructions="You are a helpful voice AI assistant"
    )
    
    # Create the agent session with default providers
    session = AgentSession(
        stt="assemblyai/universal-streaming:en",  # or your configured STT
        llm="openai/gpt-4",  # or your configured LLM
        tts="openai/tts-1",  # or your configured TTS
        vad=silero.VAD.load(),
        turn_detection=MultilingualModel(),
    )
    
    # Start the session
    await session.start(
        room=ctx.room,
        agent=agent,
        room_input_options=RoomInputOptions(
            noise_cancellation=True
        )
    )
    
    return session