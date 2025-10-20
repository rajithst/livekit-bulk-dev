# Architecture Update: LiveKit Native Lifecycle Events

## Summary

The architecture now uses **LiveKit's built-in lifecycle event system** instead of creating a custom lifecycle manager. This is the recommended approach and leverages LiveKit's native capabilities.

## Key Changes

### ✅ What Changed

1. **Removed Custom LifecycleManager** 
   - Previously: Custom `LifecycleManager` class with custom hooks
   - Now: LiveKit's native event system (`room.on(...)`)

2. **Created BackendClient**
   - New service for communicating with FastAPI backend
   - Handles all HTTP requests from agents to backend
   - Located in `agents/services/backend_client.py`

3. **Updated Agent Implementation**
   - Uses LiveKit's `JobContext` directly
   - Registers native event handlers in `_setup_event_handlers()`
   - Cleaner separation of concerns

### 📁 File Structure

```
agents/
├── core/
│   └── agent.py                    # Uses LiveKit native events ✅
├── hooks/
│   └── lifecycle.py                # Documentation only ✅
├── services/
│   └── backend_client.py           # New - Backend API client ✅
└── state/
    └── manager.py                  # State management (unchanged)
```

## LiveKit Native Events

### Room Events (`ctx.room.on(...)`)

```python
# agents/core/agent.py

def _setup_event_handlers(self):
    """Register LiveKit's native event handlers"""
    self.room.on("participant_connected", self._on_participant_connected)
    self.room.on("participant_disconnected", self._on_participant_disconnected)
    self.room.on("track_subscribed", self._on_track_subscribed)
    self.room.on("track_unsubscribed", self._on_track_unsubscribed)
    self.room.on("data_received", self._on_data_received)
    self.room.on("connection_quality_changed", self._on_connection_quality_changed)
```

### Event Handler Example

```python
async def _on_participant_connected(self, participant: rtc.RemoteParticipant):
    """Handle participant connection (LiveKit native event)."""
    logger.info(f"Participant connected: {participant.identity}")
    
    # Notify backend
    await self.backend_client.participant_connected(
        room_name=self.room.name,
        participant_identity=participant.identity,
        participant_metadata=participant.metadata
    )
    
    # Update state
    await self.state_manager.add_participant(
        room_name=self.room.name,
        participant_identity=participant.identity
    )
```

## Business Logic Integration

### BackendClient (New)

Centralized client for all backend API calls:

```python
# agents/services/backend_client.py

class BackendClient:
    """Client for communicating with FastAPI backend"""
    
    async def agent_joined(room_name, conversation_id):
        """Notify backend that agent joined"""
        
    async def participant_connected(room_name, participant_identity):
        """Log participant connection"""
        
    async def save_conversation_turn(room_name, user_msg, assistant_msg):
        """Save conversation to database"""
        
    async def handle_file_upload(room_name, participant, data):
        """Upload file to backend"""
        
    async def save_conversation(room_name, conversation_data):
        """Save final conversation state"""
```

### Job Lifecycle

```python
async def entrypoint(ctx: JobContext):
    """LiveKit agent entrypoint (called when job starts)"""
    
    # 1. Initialize
    agent = VoiceAssistantAgent(ctx, ...)
    await agent.initialize()
    
    # 2. Create conversation in state
    conversation_id = await state_manager.create_conversation(...)
    
    # 3. Notify backend
    await backend_client.agent_joined(...)
    
    # 4. Connect to room (LiveKit manages lifecycle)
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    
    # 5. Wait for disconnection (LiveKit manages this)
    await ctx.wait_for_disconnection()
    
    # 6. Cleanup
    await agent.cleanup()
```

## Benefits of Native Events

### ✅ Advantages

1. **Native Integration** - Uses LiveKit's built-in event system
2. **Better Performance** - No custom abstraction layer
3. **More Events** - Access to all LiveKit events out of the box
4. **Easier Debugging** - Standard LiveKit patterns
5. **Future-proof** - Automatically get new LiveKit features
6. **Cleaner Code** - Less custom infrastructure

### 📊 Comparison

| Aspect | Custom Manager | Native Events |
|--------|---------------|---------------|
| Event Registration | Custom wrapper | `room.on("event", handler)` |
| Event Types | Limited | Full LiveKit suite |
| Maintenance | Custom code to maintain | Maintained by LiveKit |
| Documentation | Custom docs | Official LiveKit docs |
| Learning Curve | Learn custom API | Learn LiveKit API |

## Available LiveKit Events

### Room Events
- ✅ `participant_connected` - Participant joined
- ✅ `participant_disconnected` - Participant left
- ✅ `track_published` - Track published
- ✅ `track_unpublished` - Track unpublished
- ✅ `track_subscribed` - Agent subscribed to track
- ✅ `track_unsubscribed` - Agent unsubscribed
- ✅ `data_received` - Data packet received
- ✅ `connection_quality_changed` - Connection quality changed
- ✅ `room_metadata_changed` - Room metadata updated
- ✅ `active_speakers_changed` - Active speakers changed

### Participant Events
- ✅ `track_muted` - Track muted
- ✅ `track_unmuted` - Track unmuted
- ✅ `metadata_changed` - Participant metadata changed

## Migration Guide

If you were using the custom LifecycleManager:

### Before (Custom Manager)
```python
# Old approach - custom lifecycle manager
lifecycle_manager = LifecycleManager(settings, state_manager)
await lifecycle_manager.on_room_joined(room_name, identity)
```

### After (Native Events)
```python
# New approach - LiveKit native events
def _setup_event_handlers(self):
    self.room.on("participant_connected", self._on_participant_connected)

async def _on_participant_connected(self, participant):
    await self.backend_client.participant_connected(...)
```

## Integration Points

### 1. Real-time Events → LiveKit Native
Use `room.on(...)` for events during the session

### 2. Business Logic → BackendClient
Use `BackendClient` for API calls to FastAPI backend

### 3. State → StateManager
Use `StateManager` for conversation state in Redis

### 4. Server Events → Webhooks
Use LiveKit webhooks for events outside agent (room created, recording started)

```yaml
# config/livekit.yaml
webhook:
  urls:
    - http://backend:8000/api/v1/webhooks/livekit
```

## Documentation

- **LiveKit Events**: `agents/hooks/lifecycle.py` (reference doc)
- **Agent Implementation**: `agents/core/agent.py`
- **Backend Client**: `agents/services/backend_client.py`
- **Official Docs**: https://docs.livekit.io/agents/

## Best Practices

1. ✅ **Use Native Events** - Don't wrap LiveKit's event system
2. ✅ **Keep Handlers Async** - All event handlers must be async
3. ✅ **Separate Concerns** - BackendClient for API, StateManager for state
4. ✅ **Handle Errors** - Wrap business logic in try-except
5. ✅ **Non-blocking** - Don't block event handlers
6. ✅ **Log Everything** - Use structured logging

## Example Flow

```
User speaks → WebRTC audio
    ↓
LiveKit Server receives audio
    ↓
track_subscribed event fires
    ↓
Agent processes audio (STT → LLM → TTS)
    ↓
BackendClient.save_conversation_turn()
    ↓
FastAPI saves to PostgreSQL
    ↓
Agent speaks response via TTS
```

## Summary

The updated architecture:
- ✅ Uses LiveKit's native event system (best practice)
- ✅ Introduces BackendClient for clean API integration
- ✅ Maintains StateManager for distributed state
- ✅ Provides full event documentation in lifecycle.py
- ✅ Follows LiveKit's recommended patterns
- ✅ Easier to maintain and extend

This is the **recommended approach** for LiveKit Agents development! 🎉
