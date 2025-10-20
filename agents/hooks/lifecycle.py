"""
LiveKit Native Lifecycle Events - Documentation and Reference

LiveKit Agents SDK provides built-in lifecycle events through the Room and Participant objects.
This file documents these native events and how to use them.

## NATIVE LIVEKIT EVENTS

### Room Events (ctx.room.on(...))

1. **participant_connected** - Fired when a participant joins the room
   Args: participant (rtc.RemoteParticipant)
   
2. **participant_disconnected** - Fired when a participant leaves the room
   Args: participant (rtc.RemoteParticipant)
   
3. **track_published** - Fired when a participant publishes a track
   Args: publication (rtc.RemoteTrackPublication), participant (rtc.RemoteParticipant)
   
4. **track_unpublished** - Fired when a participant unpublishes a track
   Args: publication (rtc.RemoteTrackPublication), participant (rtc.RemoteParticipant)
   
5. **track_subscribed** - Fired when the agent subscribes to a track
   Args: track (rtc.Track), publication (rtc.TrackPublication), participant (rtc.RemoteParticipant)
   
6. **track_unsubscribed** - Fired when the agent unsubscribes from a track
   Args: track (rtc.Track), publication (rtc.TrackPublication), participant (rtc.RemoteParticipant)
   
7. **data_received** - Fired when a data packet is received
   Args: data_packet (rtc.DataPacket)
   
8. **connection_quality_changed** - Fired when connection quality changes
   Args: quality (rtc.ConnectionQuality), participant (rtc.Participant)
   
9. **room_metadata_changed** - Fired when room metadata changes
   Args: metadata (str)
   
10. **active_speakers_changed** - Fired when active speakers change
    Args: speakers (List[rtc.Participant])

### Participant Events (participant.on(...))

1. **track_muted** - Fired when a participant mutes a track
   Args: publication (rtc.TrackPublication)
   
2. **track_unmuted** - Fired when a participant unmutes a track
   Args: publication (rtc.TrackPublication)
   
3. **metadata_changed** - Fired when participant metadata changes
   Args: metadata (str)

## IMPLEMENTATION EXAMPLE

See agents/core/agent.py for the actual implementation:

```python
class VoiceAssistantAgent:
    def _setup_event_handlers(self):
        \"\"\"Set up LiveKit's native event handlers.\"\"\"
        self.room.on("participant_connected", self._on_participant_connected)
        self.room.on("participant_disconnected", self._on_participant_disconnected)
        self.room.on("track_subscribed", self._on_track_subscribed)
        self.room.on("track_unsubscribed", self._on_track_unsubscribed)
        self.room.on("data_received", self._on_data_received)
        self.room.on("connection_quality_changed", self._on_connection_quality_changed)

    async def _on_participant_connected(self, participant: rtc.RemoteParticipant):
        \"\"\"Handle participant connection (LiveKit native event).\"\"\"
        logger.info(f"Participant connected: {participant.identity}")
        
        # Your business logic here:
        # - Notify backend via BackendClient
        # - Update state via StateManager
        # - Send welcome message
        # - Load user context
        
    async def _on_data_received(self, data_packet: rtc.DataPacket):
        \"\"\"Handle data messages (file uploads, commands).\"\"\"
        # Your business logic here:
        # - Process file upload
        # - Handle commands
        # - Update conversation state
```

## BUSINESS LOGIC INTEGRATION

For custom business logic, use:

1. **BackendClient** (agents/services/backend_client.py)
   - Communicate with FastAPI backend
   - Save conversations, analytics, files
   - Retrieve user context
   
2. **StateManager** (agents/state/manager.py)
   - Manage conversation state
   - Track participants
   - Store temporary data in Redis

## JOB LIFECYCLE

LiveKit Agents also provides job-level lifecycle through the entrypoint function:

```python
async def entrypoint(ctx: JobContext):
    # Called when agent is assigned to a room
    
    # 1. Initialize (setup providers, state, etc.)
    await agent.initialize()
    
    # 2. Connect to room
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    
    # 3. Wait for disconnection (LiveKit manages this)
    await ctx.wait_for_disconnection()
    
    # 4. Cleanup
    await agent.cleanup()
```

## WEBHOOK INTEGRATION

For events that happen outside the agent (room created, recording started, etc.),
use LiveKit webhooks configured in the LiveKit server:

```yaml
# config/livekit.yaml
webhook:
  api_key: livekit-webhook-key
  urls:
    - http://backend:8000/api/v1/webhooks/livekit
```

Backend handles these webhooks in:
- backend/api/v1/endpoints/webhooks.py

## BEST PRACTICES

1. **Use Native Events** - Don't create custom lifecycle managers when LiveKit provides events
2. **Keep Handlers Async** - All event handlers should be async functions
3. **Handle Errors** - Wrap business logic in try-except blocks
4. **Log Everything** - Use structured logging for debugging
5. **Separate Concerns** - Use BackendClient for API calls, StateManager for state
6. **Non-blocking** - Don't block event handlers with long-running operations

## MIGRATION NOTE

If you previously used a custom LifecycleManager, migrate to:
- Native LiveKit events for real-time events
- BackendClient for API integration
- LiveKit webhooks for server-side events

"""

import logging

logger = logging.getLogger(__name__)

# This file is documentation only
# Actual event handling is in agents/core/agent.py
# Backend integration is in agents/services/backend_client.py
