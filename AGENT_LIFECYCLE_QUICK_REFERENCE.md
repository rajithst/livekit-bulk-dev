# LiveKit Agent Process Lifecycle - Quick Reference

## The Golden Rule
```
🏠 ONE ROOM = ONE AGENT PROCESS
```

## Visual Summary is
 
### What It Is ✅ 
```
┌─────────────────────────────────┐
│  Room: "customer-support-123"   │
│                                 │
│  👤 Alice (User)                │
│  👤 Bob (User)                  │  ──┐
│  👤 Sarah (Support Agent)       │    │
│                                 │    ├──► ONE Agent Process
│  💬 20 messages exchanged       │    │   (PID: 12345)
│  ⏱️  Duration: 30 minutes        │    │   Lives for entire session
│                                 │  ──┘
└─────────────────────────────────┘

Memory for this ONE process:
- Base: ~110 MB
- History: ~50 KB (20 messages)
- Total: ~110 MB
```

### What It's NOT ❌
```
❌ NOT one process per participant:
   Alice  → Process A  (WRONG!)
   Bob    → Process B  (WRONG!)
   Sarah  → Process C  (WRONG!)

❌ NOT one process per message:
   Msg 1 → Process A  (WRONG!)
   Msg 2 → Process B  (WRONG!)
   Msg 3 → Process C  (WRONG!)

❌ NOT one process per interaction:
   Question  → Process A  (WRONG!)
   Response  → Process B  (WRONG!)
```

## Timeline Example

```
09:00:00 AM - Alice creates room "support-123"
              ↓
              🚀 Agent Process STARTS (PID: 12345)
              ↓
09:00:05 AM - Alice: "I need help"
              ↓
              ⚡ SAME process handles message
              ↓
09:02:00 AM - Bob joins room "support-123"
              ↓
              ⚡ SAME process handles Bob
              ↓
09:03:00 AM - Bob: "Me too"
              ↓
              ⚡ SAME process handles message
              ↓
09:05:00 AM - Agent: "I can help both of you"
              ↓
              ⚡ SAME process generates response
              ↓
... 25 more minutes of conversation ...
              ↓
              ⚡ ALL handled by SAME process
              ↓
09:30:00 AM - All participants leave
              ↓
              🛑 Agent Process TERMINATES
              ↓
              Memory freed (110 MB released)
```

## Concurrent Rooms

```
Time: 10:00 AM - Three active rooms

Room "sales-1"          Room "sales-2"          Room "sales-3"
- Alice, Bob           - Charlie               - Diana, Eve, Frank
- 10 messages          - 5 messages            - 15 messages
    ↓                      ↓                       ↓
Process 12345          Process 12346           Process 12347
(110 MB)              (110 MB)                (115 MB)

Total Processes: 3
Total Memory: 335 MB
NOT 6 processes (if per participant)
NOT 30 processes (if per message)
```

## Memory Calculation

### Per Agent Process
```
Component               Memory
─────────────────────────────────
Python Runtime          50 MB
LiveKit SDK            30 MB
AI Provider SDKs       20 MB
Audio Buffers          10 MB
Base Total            110 MB

+ Conversation History:
  - 10 messages        ~10 KB
  - 50 messages        ~50 KB
  - 100 messages      ~100 KB

Typical Total        ~110-120 MB
```

### Scaling Math
```
Number of Rooms = Number of Processes

10 rooms   = 10 processes  = ~1.1 GB RAM
50 rooms   = 50 processes  = ~5.5 GB RAM
100 rooms  = 100 processes = ~11 GB RAM

Formula: processes × 110 MB = RAM needed
```

## Common Patterns

### Pattern 1: Simple Support (1-on-1)
```
Room "ticket-001"
├── Customer (1 person)
└── Agent Process (1 process)
    Memory: ~110 MB
```

### Pattern 2: Group Support (Multi-participant)
```
Room "ticket-002"
├── Customer 1
├── Customer 2
├── Support Rep
└── Agent Process (STILL 1 process)
    Memory: ~115 MB (slight increase for more audio tracks)
```

### Pattern 3: Webinar (Many participants)
```
Room "webinar-live"
├── Host
├── 50 Attendees
└── Agent Process (STILL 1 process!)
    Memory: ~150 MB (more audio tracks, but manageable)
```

## Code Lifecycle

```python
# This runs ONCE per room
async def entrypoint(ctx: JobContext):
    """
    Entry point for agent job.
    Called when room is created.
    Creates ONE agent that lives until room closes.
    """
    
    # Create agent instance (once)
    agent = VoiceAssistantAgent(...)
    
    # Initialize (once)
    await agent.on_enter()
    logger.info("Agent started for room")
    
    # Handle events (loop until room closes)
    # This handles ALL participants and ALL messages
    await session.start(room=ctx.room, agent=agent)
    
    # Clean up (once)
    await agent.on_exit()
    logger.info("Agent terminated")
    
# When room closes, this entrypoint() function exits
# Process terminates, memory freed
```

## Scaling Decision Tree

```
How many concurrent conversations do you expect?

< 10 conversations
    └─► Single server, in-memory state, no Redis needed
        Cost: ~$50/month

10-100 conversations
    └─► Single server + Redis, hybrid state
        Cost: ~$150/month

100-1000 conversations
    └─► 3-5 servers + Redis cluster, distributed state
        Cost: ~$500/month

> 1000 conversations
    └─► Kubernetes cluster + Redis cluster + Auto-scaling
        Cost: ~$2000+/month
```

## Key Metrics to Monitor

```
Metric                      Why It Matters
────────────────────────────────────────────────────────────
active_agent_processes      = number of concurrent rooms
memory_per_process          should be ~110-150 MB
process_lifetime_seconds    how long rooms stay open
process_crash_rate          stability indicator
messages_per_process        conversation activity
redis_hit_rate             cache efficiency (if using Redis)
```

## Quick Troubleshooting

### Problem: High memory usage
```
Check: How many agent processes are running?
Fix: Each room = one process. If 100 processes, that's normal!
Consider: Add more servers or implement process limits
```

### Problem: Lost conversation history
```
Check: Using only in-memory state?
Fix: Implement Redis or database persistence
Pattern: In-memory → Redis → PostgreSQL
```

### Problem: Slow response times
```
Check: Process count vs CPU cores
Fix: Scale horizontally (add more servers)
Optimize: Use Redis to reduce DB queries
```

## Best Practices

✅ **DO**
- Use one agent process per room
- Implement Redis for production
- Set memory limits per process
- Monitor process count and memory
- Persist to database for long-term storage

❌ **DON'T**
- Create processes per participant
- Create processes per message
- Load entire history into memory
- Ignore memory limits
- Rely only on in-memory state for production

## Summary

**Remember**: 
- 🏠 Room = Process (1:1 relationship)
- 👥 All participants share the process
- 💬 All messages handled by same process
- ⏱️ Process lives from room open → room close
- 💾 Use Redis for scalability beyond prototype

This design makes LiveKit agents:
- ✅ Stable (isolated processes)
- ✅ Scalable (add more servers)
- ✅ Simple (one process per conversation)
- ✅ Efficient (no process spawning per message)
