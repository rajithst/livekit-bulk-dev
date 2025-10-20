# LiveKit Native State Management

## Overview

LiveKit Agents SDK provides **built-in state management** through the `JobContext` and room objects. This eliminates the need for custom state managers in most cases.

## LiveKit's Native State Features

### 1. Room State (ctx.room)

LiveKit automatically manages room state:

```python
async def entrypoint(ctx: JobContext):
    # Room information
    room_name = ctx.room.name
    room_sid = ctx.room.sid
    room_metadata = ctx.room.metadata
    
    # Participant information
    local_participant = ctx.room.local_participant
    remote_participants = ctx.room.remote_participants
    
    # Track information
    for participant in ctx.room.remote_participants.values():
        print(f"Participant: {participant.identity}")
        for track_pub in participant.track_publications.values():
            print(f"  Track: {track_pub.sid}")
```

### 2. Participant State

Each participant maintains its own state:

```python
# Participant metadata (custom data)
participant.metadata  # JSON string

# Participant identity
participant.identity
participant.sid
participant.name

# Track state
participant.track_publications  # Dict of track publications
```

### 3. Room Metadata

Store custom data at room level:

```python
# Set room metadata (from backend/server)
# Room metadata can be set when creating room or updated later
await livekit_api.update_room_metadata(
    room="room-name",
    metadata=json.dumps({
        "conversation_id": "uuid",
        "user_context": {...}
    })
)

# Access in agent
ctx.room.metadata  # Returns JSON string
data = json.loads(ctx.room.metadata)
```

### 4. Participant Attributes (User Data)

Store custom attributes per participant:

```python
# Set participant attributes (from backend)
await livekit_api.update_participant(
    room="room-name",
    identity="participant-id",
    metadata=json.dumps({
        "user_id": "123",
        "preferences": {...}
    })
)

# Access in agent
for participant in ctx.room.remote_participants.values():
    user_data = json.loads(participant.metadata)
```

### 5. Data Messages (Room Data)

Send/receive arbitrary data:

```python
# Send data to specific participant
await ctx.room.local_participant.publish_data(
    payload=json.dumps({"type": "notification", "message": "Hello"}),
    destination_identities=["user-123"]
)

# Send data to all participants
await ctx.room.local_participant.publish_data(
    payload=data,
    reliable=True
)

# Receive data (event handler)
ctx.room.on("data_received", handle_data)
```

## When to Use LiveKit Native State

### ✅ Use LiveKit Native State For:

1. **Room-level data**
   - Room metadata
   - Active participants list
   - Room configuration

2. **Participant data**
   - User identity
   - User preferences
   - Participant metadata

3. **Session data**
   - Current tracks
   - Connection quality
   - Active speakers

4. **Real-time data**
   - Data messages between participants
   - Temporary session state

### ❌ Use External State (Redis/Database) For:

1. **Persistent data**
   - Conversation history (across sessions)
   - User profiles (across rooms)
   - Analytics data

2. **Cross-room data**
   - User data shared across multiple rooms
   - Global rate limiting
   - Cross-session context

3. **Large datasets**
   - Full conversation transcripts
   - File references
   - Historical data

4. **Backend integration**
   - Data that needs to be accessed by other services
   - Data that outlives the room

## Updated Architecture Approach

### Option 1: LiveKit-First (Recommended for Simple Cases)

Use LiveKit's native state for everything in-session:

```python
class VoiceAssistantAgent:
    def __init__(self, ctx: JobContext):
        self.ctx = ctx
        self.room = ctx.room
        # No custom state manager needed!
        
    async def _on_participant_connected(self, participant):
        # Store in room metadata
        metadata = json.loads(self.room.metadata or "{}")
        metadata["participants"] = metadata.get("participants", [])
        metadata["participants"].append({
            "identity": participant.identity,
            "joined_at": datetime.utcnow().isoformat()
        })
        
        # Update via backend API
        await self.backend_client.update_room_metadata(
            self.room.name,
            json.dumps(metadata)
        )
    
    async def save_message(self, role, content):
        # Store in room metadata (for current session)
        metadata = json.loads(self.room.metadata or "{}")
        metadata["messages"] = metadata.get("messages", [])
        metadata["messages"].append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Persist to backend (for history)
        await self.backend_client.save_message(...)
```

### Option 2: Hybrid Approach (Recommended for Production)

Use LiveKit for session state, external storage for persistence:

```python
class VoiceAssistantAgent:
    def __init__(self, ctx: JobContext, backend_client: BackendClient):
        self.ctx = ctx
        self.room = ctx.room
        self.backend_client = backend_client
        
        # Conversation history in memory (for this session)
        self.conversation_history = []
        
        # Load context from backend if needed
        self.user_context = None
    
    async def initialize(self):
        # Load user context from backend
        if self.room.metadata:
            metadata = json.loads(self.room.metadata)
            user_id = metadata.get("user_id")
            if user_id:
                self.user_context = await self.backend_client.get_user_context(user_id)
        
        # Load recent conversation history from backend
        recent_messages = await self.backend_client.get_recent_messages(
            self.room.name,
            limit=10
        )
        self.conversation_history.extend(recent_messages)
    
    async def save_turn(self, user_message, assistant_message):
        # Add to in-memory history (for this session)
        self.conversation_history.append(
            LLMMessage(role="user", content=user_message)
        )
        self.conversation_history.append(
            LLMMessage(role="assistant", content=assistant_message)
        )
        
        # Persist to backend asynchronously (for long-term storage)
        asyncio.create_task(
            self.backend_client.save_conversation_turn(
                room_name=self.room.name,
                user_message=user_message,
                assistant_message=assistant_message
            )
        )
```

### Option 3: Redis for Multi-Agent Coordination

Use Redis only when multiple agents need to share state:

```python
# Only needed if you have multiple agents working together
# or need to maintain state across agent restarts

class DistributedStateManager:
    """Use only for multi-agent coordination"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def acquire_lock(self, resource: str):
        """Distributed lock for multi-agent scenarios"""
        pass
    
    async def share_context(self, room_name: str, context: dict):
        """Share context between multiple agents"""
        pass
```

## Comparison: LiveKit vs Custom State

| Aspect | LiveKit Native | Custom Redis State |
|--------|---------------|-------------------|
| **Setup** | No setup needed | Requires Redis |
| **Scope** | Per-room, per-session | Global, persistent |
| **Persistence** | Session lifetime | Configurable TTL |
| **Access** | Room participants only | Any service |
| **Performance** | Direct access | Network roundtrip |
| **Use Case** | Session data | Cross-session data |

## Updated Recommendation

### For Most Use Cases (Simple → Medium Complexity):

```python
async def entrypoint(ctx: JobContext):
    """Simplified - no custom state manager needed"""
    
    # 1. Load settings
    settings = Settings()
    
    # 2. Create backend client (for persistence)
    backend_client = BackendClient(settings)
    
    # 3. Create agent (uses LiveKit native state)
    agent = VoiceAssistantAgent(
        ctx=ctx,
        stt_config=stt_config,
        llm_config=llm_config,
        tts_config=tts_config,
        backend_client=backend_client
    )
    
    await agent.initialize()
    
    # 4. Connect (LiveKit manages room state)
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    
    # 5. Wait for disconnection
    await ctx.wait_for_disconnection()
    
    # 6. Save to backend and cleanup
    await agent.save_final_state()
    await agent.cleanup()
```

### For Complex Multi-Agent Scenarios:

Only add Redis when you need:
- Multiple agents coordinating in the same room
- State that outlives the room session
- Global rate limiting across rooms
- Cross-room data sharing

## Migration Path

### Current Architecture (with custom StateManager):
```python
# agents/state/manager.py - can be simplified or removed
```

### Recommended Simplified Architecture:
```python
# Use LiveKit native state for session data
# Use BackendClient for persistence
# Add Redis only if needed for multi-agent coordination
```

## Best Practices

1. ✅ **Use LiveKit room.metadata** for session configuration
2. ✅ **Use participant.metadata** for user context
3. ✅ **Use in-memory lists** for conversation history (current session)
4. ✅ **Use backend API** for persistent storage
5. ⚠️ **Add Redis** only when you need distributed coordination
6. ❌ **Don't duplicate** what LiveKit already provides

## Example: Simplified Agent (No Custom State Manager)

```python
class VoiceAssistantAgent:
    """Simplified agent using LiveKit native state"""
    
    def __init__(
        self,
        ctx: JobContext,
        stt_provider,
        llm_provider,
        tts_provider,
        backend_client: BackendClient
    ):
        self.ctx = ctx
        self.room = ctx.room
        self.backend_client = backend_client
        
        self.stt_provider = stt_provider
        self.llm_provider = llm_provider
        self.tts_provider = tts_provider
        
        # Simple in-memory state (for this session only)
        self.conversation_history: List[LLMMessage] = []
        self.session_start = datetime.utcnow()
    
    async def initialize(self):
        """Initialize providers and load context"""
        await self.stt_provider.initialize()
        await self.llm_provider.initialize()
        await self.tts_provider.initialize()
        
        # Load context from room metadata (set by backend)
        if self.room.metadata:
            room_data = json.loads(self.room.metadata)
            conversation_id = room_data.get("conversation_id")
            
            # Load recent history from backend
            if conversation_id:
                recent = await self.backend_client.get_recent_messages(
                    conversation_id,
                    limit=10
                )
                self.conversation_history.extend(recent)
        
        self._setup_event_handlers()
    
    async def save_final_state(self):
        """Save session data before cleanup"""
        session_data = {
            "room_name": self.room.name,
            "messages": [
                {"role": msg.role, "content": msg.content}
                for msg in self.conversation_history
            ],
            "duration": (datetime.utcnow() - self.session_start).seconds,
            "participant_count": len(self.room.remote_participants)
        }
        
        await self.backend_client.save_session(session_data)
```

## Summary

**LiveKit provides built-in state management** - you don't need a custom StateManager for most use cases!

✅ Use **LiveKit native state** for:
- Room data, participants, tracks
- Session state
- Real-time data

✅ Use **Backend API** for:
- Persistent storage
- Cross-session data
- Analytics

⚠️ Use **Redis** only when:
- Multiple agents need coordination
- Need distributed locks
- Global rate limiting

The architecture can be **significantly simplified** by leveraging LiveKit's native capabilities! 🎯
