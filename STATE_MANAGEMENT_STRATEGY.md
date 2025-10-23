# State Management Strategy and Lifecycle Integration

## State Management Strategy
The LiveKit Agent uses a multi-layered state management approach to ensure robust, scalable, and context-aware operation:

- **Room-Level State:** Utilizes `room.metadata` to store and retrieve session-wide information, such as the current conversation ID. This enables persistent context across agent restarts and participant changes.
- **Participant-Level State:** Uses `participant.metadata` to maintain user-specific context, preferences, and session data. This allows personalized experiences and context retention for each user.
- **In-Memory State (Session Cache):** Maintains a local `conversation_history` list for the current session, enabling fast access to recent messages. **Note**: This is suitable for single-session access patterns but has limitations for scale (see Scalability Considerations below).
- **Backend State (Source of Truth):** Integrates with a backend API via the `BackendClient` to persist conversation history, user actions, and error logs. This is the **authoritative source** for all conversation data, ensuring long-term storage, analytics, and business logic execution beyond the agent's lifecycle.

## Agent Process Isolation
**Important**: LiveKit agents run in **separate processes** (not threads) for each session. This means:

- ✅ **Pros**: Complete isolation, no shared memory issues, crash in one session doesn't affect others
- ⚠️ **Cons**: Higher memory overhead, in-memory state is not shared across sessions
- 📊 **Implication**: Each agent process maintains its own conversation history copy

### Process Model: One Process Per Room
```
┌─────────────────┐
│ LiveKit Server  │
└────────┬────────┘
         │
    ┌────┴────────────────────────────┐
    │                                  │
    │  Room: "customer-123"            │──► Agent Process 1 (PID: 1234)
    │    Participants: [Alice, Bob]    │    - Handles ALL participants in this room
    │                                  │    - ONE process for the ENTIRE conversation
    │                                  │    - Lives for duration of room session
    │                                  │
    │  Room: "customer-456"            │──► Agent Process 2 (PID: 1235)
    │    Participants: [Charlie]       │    - Different room = different process
    │                                  │
    │  Room: "customer-789"            │──► Agent Process 3 (PID: 1236)
    │    Participants: [Diana, Eve]    │    - Multiple participants share same process
    └──────────────────────────────────┘

Key Points:
✓ One agent process per ROOM (not per participant)
✓ One agent process per CONVERSATION (not per message)
✓ Agent lives as long as the room session exists
✓ All participants in a room share the same agent process
✓ Process terminates when room closes or all participants leave
```

### Message Flow Within a Single Agent Process
```
Agent Process (PID: 1234) for Room "customer-123"
┌────────────────────────────────────────────────────┐
│  Lifecycle: Room opens → Agent starts → Room ends  │
│                                                     │
│  Participant: Alice                                 │
│    Message 1: "Hello" ──┐                          │
│    Message 2: "How are you?" ──┐                   │
│                                 │                   │
│  Participant: Bob               │                   │
│    Message 3: "Hi there" ──┐   │                   │
│                             │   │                   │
│  ┌──────────────────────────▼───▼───▼─────────┐   │
│  │     conversation_history (in memory)        │   │
│  │  [msg1, msg2, msg3, msg4, msg5, ...]       │   │
│  │  All messages in chronological order        │   │
│  └──────────────────────────────────────────────┘  │
│                                                     │
│  The SAME process handles ALL messages             │
│  from ALL participants in this room                │
└────────────────────────────────────────────────────┘

NOT like this: ❌
  Message 1 → Process A
  Message 2 → Process B  (WRONG!)
  Message 3 → Process C
```

## Lifecycle Hooks Utilization
The agent leverages LiveKit's event-driven lifecycle hooks to manage state transitions and trigger business logic:

- **on_enter:** Initializes providers, loads context from room metadata, greets the user, and fetches recent conversation history from the backend.
- **on_exit:** Saves the current conversation state to the backend and sends a farewell message to the user.
- **on_user_turn_completed:** Updates in-memory conversation history and augments user messages with additional backend context if available.
- **Event Handlers:**
  - `_handle_transcription`: Processes STT events, updates metrics, and stores transcriptions in the backend.
  - `_handle_conversation_item`: Updates conversation history, records metrics, and persists LLM responses.
  - `_handle_speech_created`: Tracks TTS events and stores metadata in the backend.
  - `_handle_error`: Logs errors, updates error metrics, and notifies the backend of unrecoverable issues.

## Backend Client Integration
The `BackendClient` acts as the bridge between the agent and external business logic:

- **Persistence:** Stores transcriptions, conversation history, and TTS metadata for analytics and compliance.
- **Context Enrichment:** Provides relevant context to the agent during user turns, enabling smarter and more personalized responses.
- **Error Handling:** Logs errors and stack traces for monitoring and debugging.
- **Lifecycle Coordination:** Ensures that state is saved and cleaned up at appropriate lifecycle stages, supporting graceful shutdowns and handovers.

## Benefits
- **Reliability:** Multi-layered state management ensures data integrity and session continuity.
- **Scalability:** Decouples transient and persistent state, allowing for distributed and cloud-native deployments.
- **Extensibility:** Lifecycle hooks and backend integration make it easy to add new business logic and features.
- **Observability:** Metrics and error logging provide deep insights into agent performance and user interactions.

## Scalability Considerations

### In-Memory State Limitations
The current in-memory conversation history approach has these characteristics:

**Pros**:
- ⚡ Fast access to recent messages (no DB query)
- 🎯 Simple implementation for prototyping
- 💾 Reduces backend load for frequently accessed data

**Cons**:
- ❌ Memory grows linearly with conversation length
- ❌ Lost if agent process crashes or restarts
- ❌ Not shared across multiple agent instances
- ❌ No persistence across session resumption
- ⚠️ Each agent process = isolated memory space

### Recommended Production Patterns

#### 1. **Hybrid Approach (Current Implementation)**
```python
# Load recent N messages on session start
on_enter():
    self.conversation_history = await backend.get_recent_messages(limit=20)
    
# Append new messages to memory + async persist
on_message():
    self.conversation_history.append(message)
    asyncio.create_task(backend.store_message(message))  # Fire and forget
    
# Trim history periodically
if len(self.conversation_history) > 50:
    self.conversation_history = self.conversation_history[-20:]  # Keep last 20
```

**Best for**: Most use cases with reasonable conversation lengths (<100 messages/session)

#### 2. **Redis Cache Layer** (Recommended for Scale)
```python
# Use Redis for shared, fast access
conversation_history = await redis.get(f"conversation:{conversation_id}")

# TTL ensures memory cleanup
await redis.setex(
    f"conversation:{conversation_id}", 
    ttl=3600,  # 1 hour
    value=json.dumps(messages)
)
```

**Best for**: 
- Multi-agent scenarios
- Session resumption
- High memory pressure
- Horizontal scaling

#### 3. **Streaming from Backend** (For Long Conversations)
```python
# Don't load all history, stream context as needed
async def get_llm_context(self, user_message):
    # Only fetch relevant context
    relevant_history = await backend.search_conversation(
        conversation_id=self.conversation_id,
        query=user_message,
        limit=10  # Just enough context
    )
    return relevant_history
```

**Best for**:
- Very long conversations (>1000 messages)
- RAG (Retrieval-Augmented Generation) patterns
- Memory-constrained environments

### Memory Usage Estimation

Per agent process:
```
Base overhead:        ~50-100 MB (Python + LiveKit SDK)
Provider instances:   ~20-50 MB (per provider)
Audio buffers:        ~10-20 MB
Conversation history: ~1 KB per message × N messages

Example:
- 100 concurrent sessions
- 50 messages per session average
- = 100 MB just for conversation history
- = ~20 GB total (with base overhead)
```

### Scaling Strategy

#### Vertical Scaling (Single Server)
```
Small:  4 vCPU, 8 GB RAM   → ~20-30 concurrent agents
Medium: 8 vCPU, 16 GB RAM  → ~50-80 concurrent agents
Large:  16 vCPU, 32 GB RAM → ~100-150 concurrent agents
```

#### Horizontal Scaling (Multiple Servers)
```yaml
# Kubernetes deployment
replicas: 5  # 5 servers
resources:
  limits:
    memory: "16Gi"
    cpu: "8"
  
# LoadBalancer routes new rooms to available agents
# Each agent process runs independently
```

**Key Point**: Since agents are isolated processes, horizontal scaling is straightforward - just add more servers!

### Recommended Architecture for Production

```
┌──────────────┐
│   Client     │
└──────┬───────┘
       │
┌──────▼───────┐
│  LiveKit     │
│  Server      │
└──────┬───────┘
       │
   ┌───┴───┐
   │       │
┌──▼──┐  ┌─▼───┐
│Agent│  │Agent│  ... (Auto-scaled)
│Pod 1│  │Pod 2│
└──┬──┘  └──┬──┘
   │        │
   └────┬───┘
        │
   ┌────▼─────┐
   │  Redis   │ ◄─── Shared cache for conversation state
   │  Cluster │
   └────┬─────┘
        │
   ┌────▼─────┐
   │ Backend  │ ◄─── Source of truth (PostgreSQL/MongoDB)
   │   API    │
   └──────────┘
```

### Migration Path

**Phase 1 (Current)**: In-memory with backend persistence
- Good for: MVP, low traffic (<100 concurrent)
- Simple, fast to implement

**Phase 2**: Add Redis caching layer
- Good for: Production (100-1000 concurrent)
- Better session resumption
- Shared state across restarts

**Phase 3**: Distributed state management
- Good for: Enterprise scale (1000+ concurrent)
- Service mesh (e.g., Istio)
- Distributed tracing
- Advanced load balancing

## Example Flow
1. Agent starts (`on_enter`): Loads context, initializes providers, greets user.
2. User interacts: State updated in-memory and persisted via backend client.
3. Agent processes events: Metrics recorded, business logic executed, state synchronized.
4. Agent exits (`on_exit`): Final state saved, resources cleaned up.

This strategy ensures the agent is both stateful and stateless where appropriate, balancing performance, reliability, and business requirements.
