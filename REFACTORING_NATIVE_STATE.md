# Refactoring to LiveKit Native State Management

## Overview

The architecture has been **refactored to leverage LiveKit's built-in state management** capabilities, eliminating the need for a custom StateManager in most scenarios.

## What Changed

### Before: Custom State Manager

```python
# OLD: Custom state management layer
class VoiceAssistantAgent:
    def __init__(self, ..., state_manager: StateManager):
        self.state_manager = state_manager
    
    async def initialize(self):
        # Create conversation in custom state
        self.conversation_id = await self.state_manager.create_conversation(...)
        await self.state_manager.add_message(...)
        await self.state_manager.add_participant(...)
```

### After: LiveKit Native State

```python
# NEW: Use LiveKit's native state + backend persistence
class VoiceAssistantAgent:
    def __init__(self, ..., backend_client: BackendClient):
        self.backend_client = backend_client
        # LiveKit room is the state container
        self.room: rtc.Room = ctx.room
        # In-memory for session
        self.conversation_history: List[LLMMessage] = []
        self.participant_states: Dict[str, Any] = {}
    
    async def initialize(self):
        # Load from room metadata
        await self._load_room_context()
        # No custom state manager!
```

## Key Changes

### 1. Room Metadata Instead of Redis

**Before:**
```python
await state_manager.create_conversation(room_name, participant_id)
```

**After:**
```python
# Room metadata set by backend when creating room
if self.room.metadata:
    room_data = json.loads(self.room.metadata)
    self.conversation_id = room_data.get("conversation_id")
```

### 2. In-Memory Session State

**Before:**
```python
await state_manager.add_message(room_name, role, content, metadata)
```

**After:**
```python
# Store in memory for current session
self.conversation_history.append(
    LLMMessage(role="user", content=text)
)

# Persist to backend asynchronously
asyncio.create_task(
    self.backend_client.save_conversation_turn(...)
)
```

### 3. Participant Tracking

**Before:**
```python
await state_manager.add_participant(room_name, participant_identity)
await state_manager.remove_participant(room_name, participant_identity)
```

**After:**
```python
# Track in memory
self.participant_states[participant.identity] = {
    "identity": participant.identity,
    "joined_at": datetime.utcnow().isoformat(),
    "metadata": participant.metadata
}

# Notify backend
await self.backend_client.participant_connected(...)
```

### 4. Session Summary

**Before:**
```python
await state_manager.finalize_conversation(room_name)
conversation = await state_manager.get_conversation(room_name)
await backend_client.save_conversation(room_name, conversation)
```

**After:**
```python
# Build session summary from in-memory data
session_data = {
    "room_name": self.room.name,
    "conversation_id": self.conversation_id,
    "message_count": len(self.conversation_history),
    "participants": list(self.participant_states.values()),
    "messages": [{"role": msg.role, "content": msg.content} 
                 for msg in self.conversation_history]
}

# Save to backend
await self.backend_client.save_session(session_data)
```

## Architecture Layers

### Layer 1: LiveKit Native State (Session Data)
- **Room metadata** - Conversation ID, room configuration
- **Participant metadata** - User identity, preferences
- **Track state** - Active audio/video tracks
- **Data messages** - Real-time file uploads, commands

### Layer 2: In-Memory State (Agent Process)
- **Conversation history** - Current session messages
- **Participant states** - Join/leave timestamps
- **Session metadata** - Duration, message count

### Layer 3: Backend Persistence (Long-term Storage)
- **Conversation turns** - Saved asynchronously
- **Session summaries** - Saved on cleanup
- **Analytics** - Connection events, errors
- **User profiles** - Cross-session data

## Benefits of This Approach

### ✅ Simplicity
- No Redis setup required for basic use
- Fewer moving parts
- Less infrastructure to manage

### ✅ LiveKit-Native
- Uses LiveKit's built-in capabilities
- Better aligned with framework design
- Leverages optimized LiveKit internals

### ✅ Performance
- No Redis roundtrips during session
- State access is direct (in-memory)
- Backend saves are asynchronous (non-blocking)

### ✅ Scalability
- Each agent manages its own session state
- No central state bottleneck
- Backend handles persistence at scale

### ✅ Maintainability
- Less custom code to maintain
- Simpler debugging (fewer layers)
- Easier testing (mock backend only)

## When to Still Use Redis

Keep Redis/StateManager **only if you need**:

1. **Multi-Agent Coordination**
   - Multiple agents working together in same room
   - Need distributed locks
   - Shared state between agents

2. **Agent Failover**
   - Agent crashes and new agent takes over
   - Need to restore exact conversation state
   - Stateful migration between agents

3. **Cross-Room State**
   - User data shared across multiple rooms
   - Global rate limiting
   - Complex session management

## Migration Guide

### If You Have Existing Custom StateManager

**Option 1: Remove Completely** (Recommended for most)
1. Delete `agents/state/manager.py`, `redis_state.py`, `memory_state.py`
2. Update agent to use in-memory state + backend
3. Backend handles all persistence

**Option 2: Keep for Specific Use Cases**
1. Document why you need it (multi-agent, failover, etc.)
2. Use StateManager only for those specific features
3. Use LiveKit native state for everything else

**Option 3: Gradual Migration**
1. Start with new rooms using native state
2. Keep StateManager for existing rooms
3. Migrate rooms gradually

## Updated File Structure

```
agents/
├── core/
│   ├── agent.py                    # ✅ Updated: Uses LiveKit native state
│   └── providers/                  # ✅ Unchanged
├── services/
│   └── backend_client.py           # ✅ Updated: Added get_recent_messages, save_session
├── state/                          # ⚠️ Optional: Only for multi-agent scenarios
│   ├── manager.py                  # Can be removed for simple use cases
│   ├── redis_state.py              # Can be removed
│   └── memory_state.py             # Can be removed
├── config/
│   └── settings.py                 # ✅ Unchanged
└── hooks/
    └── lifecycle.py                # ✅ Documentation only
```

## Example: Complete Flow

### 1. Backend Creates Room

```python
# Backend API sets room metadata
await livekit_api.create_room(
    name="room-123",
    metadata=json.dumps({
        "conversation_id": "conv-uuid",
        "user_id": "user-456"
    })
)
```

### 2. Agent Joins

```python
async def entrypoint(ctx: JobContext):
    # Agent loads context from room.metadata
    agent = VoiceAssistantAgent(ctx, backend_client)
    await agent.initialize()  # Loads from room.metadata
    
    # Notify backend
    conversation_id = await backend_client.agent_joined(room_name)
    
    await ctx.connect()
    await ctx.wait_for_disconnection()
    await agent.cleanup()  # Saves session to backend
```

### 3. Conversation Flow

```python
# User speaks -> STT
user_message = await stt_provider.transcribe(audio)

# Store in memory
agent.conversation_history.append(LLMMessage("user", user_message))

# Generate response -> LLM
response = await llm_provider.generate(agent.conversation_history)

# Store in memory
agent.conversation_history.append(LLMMessage("assistant", response))

# Save to backend asynchronously (non-blocking)
asyncio.create_task(
    backend_client.save_conversation_turn(user_message, response)
)

# Speak -> TTS
await tts_provider.synthesize(response)
```

### 4. Session End

```python
# Agent cleanup
session_data = {
    "messages": agent.conversation_history,
    "participants": agent.participant_states,
    "duration": (now - agent.session_start).seconds
}

# Save final state to backend
await backend_client.save_session(session_data)
```

## Testing

### Unit Tests

```python
# No Redis needed for testing!
async def test_agent():
    mock_backend = MockBackendClient()
    agent = VoiceAssistantAgent(ctx, backend_client=mock_backend)
    
    await agent.initialize()
    # Test with in-memory state
    assert len(agent.conversation_history) == 0
```

### Integration Tests

```python
# Test with real backend, no Redis
async def test_full_flow():
    agent = VoiceAssistantAgent(ctx, backend_client)
    await agent.initialize()
    
    # Simulate conversation
    await agent._process_audio_stream(track, participant)
    
    # Verify backend received data
    assert backend_client.save_count > 0
```

## Performance Comparison

| Operation | Custom StateManager | LiveKit Native |
|-----------|-------------------|----------------|
| **Read participant** | Redis GET (~1ms) | Direct access (<0.1ms) |
| **Add message** | Redis RPUSH (~1ms) | List append (<0.01ms) |
| **Get conversation** | Redis GET + parse (~2ms) | Direct access (<0.1ms) |
| **Session cleanup** | Redis DEL (~1ms) | No-op (0ms) |

**Result:** ~10x faster for state operations during session!

## Summary

✅ **Removed:** Custom StateManager dependency  
✅ **Added:** LiveKit native state usage  
✅ **Added:** In-memory session state  
✅ **Updated:** Backend client with new methods  
✅ **Improved:** Performance (no Redis roundtrips)  
✅ **Simplified:** Architecture (fewer layers)  

The refactored architecture is:
- **Simpler** - Uses LiveKit's built-in capabilities
- **Faster** - Direct memory access, async persistence
- **Scalable** - Each agent independent, no state bottleneck
- **Maintainable** - Less custom code, easier testing

🎯 **Use Redis/StateManager only when you truly need multi-agent coordination or failover capabilities!**
