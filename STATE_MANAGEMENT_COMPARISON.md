# State Management: LiveKit Native vs Custom

## Quick Comparison

| Aspect | Custom StateManager (OLD) | LiveKit Native (NEW) |
|--------|--------------------------|----------------------|
| **Redis Required** | ✅ Yes | ❌ No (optional) |
| **Setup Complexity** | High | Low |
| **State Access** | Network call (~1ms) | Direct (<0.1ms) |
| **Session State** | Redis | In-memory + room.metadata |
| **Persistence** | Redis + Backend | Backend only |
| **Scalability** | Central bottleneck | Distributed (per agent) |
| **Use Case** | Multi-agent coordination | Single agent per room |

## Current Architecture (After Refactoring)

### State Storage Layers

```
┌─────────────────────────────────────────────┐
│  LiveKit Room (Native State Container)      │
│  - room.metadata: {"conversation_id": ...}  │
│  - participant.metadata: User context       │
│  - Tracks, participants (auto-managed)      │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  Agent (In-Memory Session State)            │
│  - conversation_history: [...]              │
│  - participant_states: {...}                │
│  - session_start, message_count, etc.       │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  Backend API (Persistent Storage)           │
│  - PostgreSQL: Conversations, messages      │
│  - Blob Storage: Files, recordings          │
│  - Async writes (non-blocking)              │
└─────────────────────────────────────────────┘
```

## Code Changes

### Agent Initialization

**Before:**
```python
async def entrypoint(ctx: JobContext):
    state_manager = StateManager(settings)
    await state_manager.initialize()
    
    agent = VoiceAssistantAgent(
        ctx, 
        state_manager=state_manager,  # ❌ Removed
        backend_client=backend_client
    )
```

**After:**
```python
async def entrypoint(ctx: JobContext):
    # No state manager needed!
    agent = VoiceAssistantAgent(
        ctx,
        backend_client=backend_client  # ✅ Only backend client
    )
```

### Storing Messages

**Before:**
```python
# Write to Redis
await self.state_manager.add_message(
    room_name, role, content, metadata
)
```

**After:**
```python
# Store in memory
self.conversation_history.append(
    LLMMessage(role="user", content=text)
)

# Persist asynchronously (non-blocking)
asyncio.create_task(
    self.backend_client.save_conversation_turn(...)
)
```

### Cleanup

**Before:**
```python
# Finalize in Redis, then save to backend
await state_manager.finalize_conversation(room_name)
conversation = await state_manager.get_conversation(room_name)
await backend_client.save_conversation(room_name, conversation)
```

**After:**
```python
# Build session summary from in-memory data
session_data = {
    "messages": self.conversation_history,
    "participants": self.participant_states,
    "duration": (now - self.session_start).seconds
}
await backend_client.save_session(session_data)
```

## When to Use Redis/StateManager

### ✅ Keep Custom StateManager If You Need:

1. **Multi-Agent Coordination**
   - Multiple agents in the same room
   - Shared state between agents
   - Distributed locks

2. **Agent Failover**
   - Agent crashes, new agent resumes
   - Need to restore exact state
   - High availability requirements

3. **Cross-Room State**
   - Global rate limiting
   - User state across multiple rooms
   - Complex session management

### ❌ You Don't Need It For:

1. **Single agent per room** (most common)
2. **Session-only state**
3. **Stateless agents**
4. **Simple conversation tracking**

## Files Changed

### Modified Files

1. **agents/core/agent.py**
   - ❌ Removed: `state_manager` parameter
   - ✅ Added: In-memory `conversation_history`, `participant_states`
   - ✅ Added: `_load_room_context()` to read from room.metadata
   - ✅ Updated: All event handlers to use in-memory state

2. **agents/services/backend_client.py**
   - ✅ Added: `get_recent_messages()` - Load history from backend
   - ✅ Added: `save_session()` - Save session summary
   - ✅ Updated: `agent_joined()` - Returns conversation_id

### Optional Files (Can Be Removed)

3. **agents/state/manager.py** - Only needed for multi-agent
4. **agents/state/redis_state.py** - Only needed for multi-agent
5. **agents/state/memory_state.py** - Only needed for multi-agent

## Performance Impact

### Before (with Redis)
```
User speaks → STT (50ms)
           → Redis write (1ms)
           → LLM (500ms)
           → Redis write (1ms)
           → Backend save (5ms)
           → TTS (200ms)
Total: ~757ms
```

### After (Native State)
```
User speaks → STT (50ms)
           → Memory write (<0.1ms)
           → LLM (500ms)
           → Memory write (<0.1ms)
           → Backend save (async, non-blocking)
           → TTS (200ms)
Total: ~750ms (7ms faster)
```

**Bonus:** Backend saves happen asynchronously, don't block the conversation flow!

## Migration Steps

### Step 1: Update Agent Code
```bash
# Already done! agent.py refactored
```

### Step 2: Update Backend Client
```bash
# Already done! Added get_recent_messages, save_session
```

### Step 3: Deploy
```bash
# No Redis needed in docker-compose.yml (for simple use)
docker-compose up -d
```

### Step 4: Test
```bash
# Test conversation flow
curl -X POST http://localhost:8000/api/v1/rooms \
  -H "Content-Type: application/json" \
  -d '{"name": "test-room"}'
```

## Summary

✅ **Simpler:** No Redis for basic use  
✅ **Faster:** Direct memory access  
✅ **Scalable:** Each agent independent  
✅ **Maintainable:** Less infrastructure  
✅ **LiveKit-native:** Uses built-in features  

🎯 **Result:** Same functionality, simpler architecture, better performance!

## Documentation

- [LIVEKIT_STATE_MANAGEMENT.md](./LIVEKIT_STATE_MANAGEMENT.md) - Detailed guide
- [REFACTORING_NATIVE_STATE.md](./REFACTORING_NATIVE_STATE.md) - Complete refactoring details
- [LIFECYCLE_EVENTS.md](./LIFECYCLE_EVENTS.md) - LiveKit events reference

