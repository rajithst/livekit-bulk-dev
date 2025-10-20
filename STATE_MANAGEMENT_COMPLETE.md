# Complete State Management Overview

## Quick Answer

### Is the Backend Stateless?

**YES! ✅ The FastAPI backend is 100% stateless.**

### How Do Agents Manage State?

**Hybrid approach:**
- ✅ LiveKit native state (room.metadata, participant.metadata)
- ✅ In-memory session state (conversation history)
- ✅ Backend API for persistence (PostgreSQL)
- ⚠️ Redis optional (only for multi-agent coordination)

---

## Complete Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                    CLIENT LAYER                              │
│  Web Browser / Mobile App / Desktop App                      │
│  - LiveKit Client SDK                                        │
│  - WebRTC for real-time audio/video                         │
└────────────────────┬─────────────────────────────────────────┘
                     │ WebRTC
                     ▼
┌──────────────────────────────────────────────────────────────┐
│                 LIVEKIT SERVER (Self-Hosted)                 │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  NATIVE STATE MANAGEMENT (Built-in)                    │  │
│  │  - room.metadata: {"conversation_id": "..."}           │  │
│  │  - participant.metadata: {"user_id": "..."}            │  │
│  │  - Active participants (auto-tracked)                  │  │
│  │  - Track state (audio/video)                           │  │
│  │  - Data messages (real-time events)                    │  │
│  └────────────────────────────────────────────────────────┘  │
└────────────────────┬─────────────────────────────────────────┘
                     │ gRPC
                     ▼
┌──────────────────────────────────────────────────────────────┐
│                   LIVEKIT AGENTS (Python)                    │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  SESSION STATE (In-Memory, Per Room)                   │  │
│  │  - conversation_history: List[Message]                 │  │
│  │  - participant_states: Dict[identity, state]           │  │
│  │  - session_start: datetime                             │  │
│  │  - conversation_id: str (from room.metadata)           │  │
│  └────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  AI PROVIDERS (Pluggable)                              │  │
│  │  - STT: OpenAI Whisper / Azure / AWS                   │  │
│  │  - LLM: GPT-4 / Claude / Gemini                        │  │
│  │  - TTS: OpenAI TTS / Azure / AWS                       │  │
│  └────────────────────────────────────────────────────────┘  │
└────────────────────┬─────────────────────────────────────────┘
                     │ REST API (async)
                     ▼
┌──────────────────────────────────────────────────────────────┐
│              FASTAPI BACKEND (Stateless!)                    │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  NO IN-MEMORY STATE                                    │  │
│  │  - JWT authentication (stateless tokens)               │  │
│  │  - Database connection pool (not state)                │  │
│  │  - Each request is independent                         │  │
│  │  - Can scale horizontally (2-20+ pods)                 │  │
│  └────────────────────────────────────────────────────────┘  │
└────────────────────┬─────────────────────────────────────────┘
                     │
        ┌────────────┼────────────┬──────────────┐
        │            │            │              │
        ▼            ▼            ▼              ▼
┌──────────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│ PostgreSQL   │ │  Redis   │ │   Blob   │ │ LiveKit  │
│ (Persistent) │ │ (Cache)  │ │ Storage  │ │   API    │
│              │ │          │ │          │ │          │
│ - Users      │ │ - Rate   │ │ - Files  │ │ - Create │
│ - Rooms      │ │   limits │ │ - Audio  │ │   rooms  │
│ - Convos     │ │ - JWT    │ │ - Videos │ │ - Tokens │
│ - Messages   │ │   black- │ │ - Docs   │ │          │
│              │ │   list   │ │          │ │          │
└──────────────┘ └──────────┘ └──────────┘ └──────────┘
  Source of       Performance   File          Room
  Truth           Only          Storage       Management
```

---

## State Comparison Table

| Layer | State Type | Storage | Lifetime | Scalability | Use Case |
|-------|-----------|---------|----------|-------------|----------|
| **LiveKit Server** | Room/Participant | Native | Session | High | WebRTC state |
| **Agent** | Conversation | In-Memory | Session | Per-room | Active conversation |
| **Backend** | None! | N/A | N/A | Unlimited | Stateless API |
| **PostgreSQL** | Persistent | Disk | Permanent | High | Source of truth |
| **Redis** | Cache | Memory | Temporary | High | Performance |
| **Blob Storage** | Files | Disk | Permanent | Unlimited | File storage |

---

## Data Flow: Complete Conversation

### 1. User Joins Room

```
User → LiveKit Server
         ↓
      LiveKit creates room
      room.metadata = {"conversation_id": "uuid"}
         ↓
      Agent spawned (gRPC)
         ↓
      Agent.initialize()
        - Reads room.metadata (LiveKit native)
        - conversation_id = metadata["conversation_id"]
        - Loads recent messages from backend API
        - conversation_history = [last 10 messages]
         ↓
      Backend notified (REST)
        POST /api/v1/rooms/{id}/agent-joined
        → Saved to PostgreSQL
```

### 2. User Speaks

```
User speaks → WebRTC audio
         ↓
      LiveKit Server routes to Agent
         ↓
      Agent receives audio track
         ↓
      STT: transcribe audio
      user_message = "Hello"
         ↓
      Agent stores in memory (instant!)
      conversation_history.append(
        LLMMessage("user", "Hello")
      )
         ↓
      LLM: generate response
      assistant_message = "Hi there!"
         ↓
      Agent stores in memory
      conversation_history.append(
        LLMMessage("assistant", "Hi there!")
      )
         ↓
      TTS: speak response
         ↓
      Async persist to backend (non-blocking!)
      asyncio.create_task(
        backend.save_turn(...)
      )
         ↓
      Backend saves to PostgreSQL
      (Any backend pod can handle this)
```

### 3. User Disconnects

```
User disconnects → LiveKit event
         ↓
      Agent cleanup()
         ↓
      Build session summary:
      session_data = {
        "messages": conversation_history,
        "participants": participant_states,
        "duration": 325 seconds
      }
         ↓
      Save to backend
      POST /api/v1/sessions/save
         ↓
      Backend saves to PostgreSQL
      (Permanent storage)
         ↓
      Agent terminates
      (All in-memory state cleared)
```

---

## Scaling Characteristics

### LiveKit Server
- **Scale:** 100-1000s rooms per server
- **Method:** Add more LiveKit servers
- **State:** Native (room/participant)

### Agents
- **Scale:** One agent per room
- **Method:** Auto-spawn new agents
- **State:** In-memory (per session)

### Backend API
- **Scale:** Unlimited (stateless!)
- **Method:** Horizontal pod scaling (2-20+)
- **State:** None (truly stateless)

### PostgreSQL
- **Scale:** Millions of records
- **Method:** Read replicas, sharding
- **State:** All persistent data

### Redis
- **Scale:** Millions of keys
- **Method:** Redis cluster
- **State:** Cache only (can be cleared)

---

## Request Distribution

### Backend (Stateless)
```
Request 1 → Pod 1 → PostgreSQL → Response
Request 2 → Pod 3 → PostgreSQL → Response
Request 3 → Pod 2 → PostgreSQL → Response
Request 4 → Pod 1 → PostgreSQL → Response

✅ Any pod can serve any request!
✅ Load balancer uses round-robin
✅ No sticky sessions needed
```

### Agents (Stateful per Room)
```
Room A → Agent 1 (holds Room A state)
Room B → Agent 2 (holds Room B state)
Room C → Agent 3 (holds Room C state)

✅ Each agent independent
✅ Scales by number of rooms
✅ No shared state between agents
```

---

## When to Use Redis

### ✅ Use Redis For:

1. **Backend: Performance Cache**
   ```python
   # Cache query results
   cached = await redis.get(f"user:{user_id}:profile")
   if cached:
       return cached
   # Query database and cache
   ```

2. **Backend: Rate Limiting**
   ```python
   # Temporary counters
   count = await redis.incr(f"rate:{user_id}")
   if count > 100:
       raise TooManyRequests()
   ```

3. **Backend: JWT Blacklist**
   ```python
   # Token revocation
   await redis.setex(f"blacklist:{token}", 3600, "1")
   ```

4. **Agents: Multi-Agent Coordination** (Advanced)
   ```python
   # Only if multiple agents in same room
   lock = await redis.lock(f"room:{room_id}:lock")
   ```

### ❌ DON'T Use Redis For:

1. ❌ Backend session state (use JWT)
2. ❌ Agent conversation history (use in-memory)
3. ❌ Persistent data (use PostgreSQL)
4. ❌ File storage (use Blob Storage)

---

## Summary: State Management Strategy

### LiveKit Server
**Native state for WebRTC:**
- Room metadata
- Participant metadata
- Track state
- Data messages

### Agents
**Hybrid approach:**
- LiveKit native (room context)
- In-memory (session state)
- Backend API (persistence)
- No Redis needed (most cases)

### Backend
**Fully stateless:**
- JWT auth (no sessions)
- Database queries (per request)
- Redis cache (performance only)
- Scales horizontally

### Storage
**Three layers:**
1. PostgreSQL: Persistent truth
2. Redis: Cache & counters
3. Blob: Files & media

---

## Architecture Benefits

| Benefit | How Achieved |
|---------|-------------|
| **Scalability** | Backend stateless → unlimited pods |
| **Performance** | Agent in-memory → <0.1ms access |
| **Reliability** | PostgreSQL → ACID guarantees |
| **Simplicity** | LiveKit native → no custom state |
| **Cost** | No Redis needed → save $100-500/mo |
| **Flexibility** | Pluggable AI → swap providers easily |

---

## Quick Reference

### Agent State
```python
# In-memory (fast, session-only)
self.conversation_history.append(message)

# Backend persistence (async)
asyncio.create_task(backend.save_turn(...))
```

### Backend State
```python
# Stateless request handler
@router.post("/api/v1/conversations")
async def create(request: Request, db: Session):
    # Query database (no in-memory state)
    conversation = await db.query(...).first()
    return conversation
    # Session closed - pod is stateless again
```

### When to Use What

| Need | Solution |
|------|----------|
| Current conversation | Agent in-memory |
| Room context | LiveKit metadata |
| Persistent data | PostgreSQL |
| Performance cache | Redis |
| File storage | Blob Storage |
| Authentication | JWT (stateless) |
| Multi-agent sync | Redis locks (advanced) |

---

## Deployment: Scaling Numbers

### Small (100 concurrent users)
- LiveKit: 1 server
- Agents: ~10 pods
- Backend: 2 pods
- PostgreSQL: 1 instance
- Redis: Optional

### Medium (1,000 concurrent users)
- LiveKit: 2-3 servers
- Agents: ~100 pods
- Backend: 5 pods
- PostgreSQL: Primary + 2 replicas
- Redis: 1 cluster

### Large (10,000 concurrent users)
- LiveKit: 10+ servers
- Agents: ~1,000 pods
- Backend: 20 pods
- PostgreSQL: Primary + 5 replicas
- Redis: 3-node cluster

**All because:**
- ✅ Backend is stateless (scales easily)
- ✅ Agents are independent (one per room)
- ✅ LiveKit handles WebRTC efficiently

---

## Documentation

For deep dives, see:
- **[LIVEKIT_STATE_MANAGEMENT.md](./LIVEKIT_STATE_MANAGEMENT.md)** - Agent state
- **[BACKEND_STATELESS_DESIGN.md](./BACKEND_STATELESS_DESIGN.md)** - Backend architecture
- **[STATE_BEFORE_AFTER_VISUAL.md](./STATE_BEFORE_AFTER_VISUAL.md)** - Visual diagrams

🎯 **Result:** A truly cloud-native, horizontally scalable AI voice assistant system!
