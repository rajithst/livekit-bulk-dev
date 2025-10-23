# LiveKit Agent Scaling Architecture

## Process Isolation Model

### How LiveKit Agents Work

**Critical Understanding**: One agent process = One room session

🎯 **This is the DEFAULT behavior** - No configuration needed!  
✅ LiveKit automatically spawns one process per room  
✅ Handled by `cli.run_app()` framework  
✅ Your `entrypoint()` function is called once per room

```
┌─────────────────────────────────────────────────────────┐
│              LiveKit Server (Central Hub)               │
│  - Routes rooms to available agents                     │
│  - Manages WebRTC connections                           │
│  - Broadcasts media tracks                              │
└────────────────┬────────────────────────────────────────┘
                 │
        ┌────────┼────────┐
        │        │        │
    ┌───▼─────────────┐┌──▼─────────────┐┌───▼─────────────┐
    │ Room: "sales-1" ││ Room: "sales-2"││ Room: "sales-3" │
    │ Participants:   ││ Participants:  ││ Participants:   │
    │ - Alice         ││ - Charlie      ││ - Eve           │
    │ - Bob           ││ - Diana        ││ - Frank         │
    │                 ││                ││ - Grace         │
    └───┬─────────────┘└──┬─────────────┘└───┬─────────────┘
        │                 │                   │
    ┌───▼─────────────┐┌──▼─────────────┐┌───▼─────────────┐
    │ Agent Process 1 ││ Agent Process 2││ Agent Process 3 │
    │ PID: 12345      ││ PID: 12346     ││ PID: 12347      │
    │                 ││                ││                 │
    │ Handles BOTH    ││ Handles BOTH   ││ Handles ALL 3   │
    │ Alice & Bob     ││ Charlie & Diana││ participants    │
    │                 ││                ││                 │
    │ Memory: ~120MB  ││ Memory: ~120MB ││ Memory: ~130MB  │
    └─────────────────┘└────────────────┘└─────────────────┘
    
    Each agent process:
    ✓ Handles ONE room (not one participant)
    ✓ Serves ALL participants in that room
    ✓ Processes ALL messages in that conversation
    ✓ Lives for the duration of the room session
    ✓ Has own memory space (isolated)
    ✓ Has own Python interpreter
    ✓ Has own event loop
    ✗ CANNOT share in-memory data with other rooms
```

### Lifecycle Timeline

```
Time: 10:00 AM
┌──────────────────────────────────────────────────────┐
│ User Alice joins Room "sales-1"                      │
│ → LiveKit creates Room                               │
│ → Agent Process spawned (PID: 12345)                 │
│ → Agent.on_enter() called                            │
│ → Agent greets Alice: "Hello, how can I help?"       │
└──────────────────────────────────────────────────────┘

Time: 10:02 AM
┌──────────────────────────────────────────────────────┐
│ User Bob joins SAME Room "sales-1"                   │
│ → NO new agent process!                              │
│ → SAME Agent Process (PID: 12345) handles Bob        │
│ → Agent sees both Alice and Bob                      │
│ → conversation_history has messages from BOTH        │
└──────────────────────────────────────────────────────┘

Time: 10:05 AM
┌──────────────────────────────────────────────────────┐
│ Alice sends: "I need help with billing"              │
│ Bob sends: "Yes, billing issue"                      │
│ → SAME process handles BOTH messages                 │
│ → conversation_history: [alice_msg, bob_msg]         │
│ → Agent responds to conversation (not individuals)   │
└──────────────────────────────────────────────────────┘

Time: 10:30 AM
┌──────────────────────────────────────────────────────┐
│ Alice and Bob leave Room "sales-1"                   │
│ → Room closes                                        │
│ → Agent.on_exit() called                             │
│ → Agent Process (PID: 12345) terminates              │
│ → Memory freed                                       │
└──────────────────────────────────────────────────────┘

Time: 10:31 AM
┌──────────────────────────────────────────────────────┐
│ User Charlie joins NEW Room "sales-2"                │
│ → NEW Agent Process spawned (PID: 12346)             │
│ → Fresh conversation_history (empty)                 │
│ → Different memory space                             │
│ → Completely isolated from "sales-1"                 │
└──────────────────────────────────────────────────────┘
```

### Common Misconceptions

❌ **WRONG**: One process per message
```
Message 1 → Spawn Process A → Handle → Terminate
Message 2 → Spawn Process B → Handle → Terminate
Message 3 → Spawn Process C → Handle → Terminate
(This would be incredibly inefficient!)
```

❌ **WRONG**: One process per participant
```
Alice → Agent Process A
Bob   → Agent Process B
(They can't collaborate in the same conversation!)
```

✅ **CORRECT**: One process per room/conversation
```
Room "sales-1" → Agent Process 1
  ├── Handles Alice's messages
  ├── Handles Bob's messages
  ├── Maintains conversation context
  └── Lives until room closes

Room "sales-2" → Agent Process 2
  ├── Handles Charlie's messages
  └── Lives until room closes
```

### Real-World Example: Customer Support

```
Scenario: 3 customer support conversations happening simultaneously

╔══════════════════════════════════════════════════════════╗
║ Room: "support-ticket-001"                               ║
║ Agent Process: PID 5001 (Memory: 115 MB)                 ║
║ Started: 09:00 AM, Running for: 25 minutes               ║
╠══════════════════════════════════════════════════════════╣
║ Participants:                                            ║
║   • Customer Alice (joined 09:00 AM)                     ║
║   • Support Agent Sarah (joined 09:02 AM)                ║
║                                                          ║
║ Conversation History (in THIS process):                  ║
║   [09:00] Alice: "My payment failed"                     ║
║   [09:01] Agent: "Let me check your account"            ║
║   [09:02] Sarah: "I can help with that"                  ║
║   [09:05] Alice: "Transaction ID: ABC123"                ║
║   [09:10] Agent: "Found the issue, processing refund"   ║
║   ... (continues in same process)                        ║
╚══════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════╗
║ Room: "support-ticket-002"                               ║
║ Agent Process: PID 5002 (Memory: 118 MB)                 ║
║ Started: 09:15 AM, Running for: 10 minutes               ║
╠══════════════════════════════════════════════════════════╣
║ Participants:                                            ║
║   • Customer Bob (joined 09:15 AM)                       ║
║                                                          ║
║ Conversation History (DIFFERENT process):                ║
║   [09:15] Bob: "Can't login to my account"               ║
║   [09:16] Agent: "Let me help you reset password"       ║
║   [09:18] Bob: "Email is bob@example.com"                ║
║   ... (separate conversation, separate memory)           ║
╚══════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════╗
║ Room: "support-ticket-003"                               ║
║ Agent Process: PID 5003 (Memory: 125 MB)                 ║
║ Started: 09:20 AM, Running for: 5 minutes                ║
╠══════════════════════════════════════════════════════════╣
║ Participants:                                            ║
║   • Customer Charlie (joined 09:20 AM)                   ║
║   • Customer Diana (joined 09:22 AM) ← SAME room!        ║
║                                                          ║
║ Conversation History (BOTH participants in SAME process):║
║   [09:20] Charlie: "Question about pricing"              ║
║   [09:21] Agent: "Our plans start at $9/month"          ║
║   [09:22] Diana: "I have the same question"              ║
║   [09:23] Agent: "Happy to help both of you"            ║
║   ... (Charlie & Diana share this process)               ║
╚══════════════════════════════════════════════════════════╝

Key Insights:
1. Three separate rooms = Three separate processes
2. Multiple participants in one room = SAME process
3. Each process is completely independent
4. If PID 5001 crashes, only "support-ticket-001" is affected
5. Total memory: 115 + 118 + 125 = 358 MB for 3 conversations
```

### Process Creation and Termination

```python
# What happens in code (simplified)

# When room "support-ticket-001" is created:
async def entrypoint(ctx: JobContext):
    """
    This function is called ONCE per room.
    Creates ONE agent instance that lives for the room duration.
    """
    agent = VoiceAssistantAgent(...)
    
    # Agent starts
    await agent.on_enter()  # Called once when room opens
    
    # Agent handles ALL events in this room
    while room_is_active:
        # Alice sends message → agent handles it
        # Bob joins → agent handles it
        # Alice sends another message → SAME agent handles it
        # Sarah joins → SAME agent handles it
        # ... ALL handled by THIS agent instance
        await handle_events()
    
    # Agent ends
    await agent.on_exit()  # Called once when room closes
    # Process terminates

# Different room? Different process!
# Room "support-ticket-002" → NEW entrypoint() call → NEW process
```

## The In-Memory Problem

### Without Redis (Current Basic Implementation)

```
Agent Process 1                Agent Process 2
┌──────────────────┐          ┌──────────────────┐
│ conversation_id: │          │ conversation_id: │
│   "conv_123"     │          │   "conv_456"     │
│                  │          │                  │
│ Memory:          │          │ Memory:          │
│ [msg1, msg2,     │          │ [msg1, msg2,     │
│  msg3, ...]      │          │  msg3, ...]      │
│                  │          │                  │
│ Size: ~50MB      │          │ Size: ~50MB      │
└──────────────────┘          └──────────────────┘

Problems:
❌ If Agent 1 crashes → conversation_history lost
❌ Cannot resume on Agent 2 (different process)
❌ 100 agents × 50MB = 5GB just for history
❌ No way to share context across processes
```

### With Redis (Recommended)

```
Agent Process 1        Agent Process 2        Agent Process 3
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│ Small cache  │      │ Small cache  │      │ Small cache  │
│ (last 10 msg)│      │ (last 10 msg)│      │ (last 10 msg)│
└──────┬───────┘      └──────┬───────┘      └──────┬───────┘
       │                     │                     │
       └─────────────────────┼─────────────────────┘
                             │
                    ┌────────▼────────┐
                    │  Redis Cluster  │
                    │  (Shared Cache) │
                    │                 │
                    │ conv_123: [...]│
                    │ conv_456: [...]│
                    │ conv_789: [...]│
                    │                 │
                    │ Total: ~500MB  │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   PostgreSQL    │
                    │ (Persistent DB) │
                    │                 │
                    │ All messages    │
                    │ Full history    │
                    └─────────────────┘

Benefits:
✅ Crash recovery → data in Redis
✅ Session resumption → any agent can pick up
✅ Shared state → all agents see same data
✅ Memory efficient → 100 agents share Redis
✅ TTL cleanup → old conversations auto-expire
```

## Scaling Patterns

### Pattern 1: Vertical Scaling (Single Server)
```
┌────────────────────────────────────┐
│   Single Server                    │
│   16 vCPU, 32 GB RAM              │
│                                    │
│   ┌──────────────────────────┐    │
│   │  Agent Pool              │    │
│   │  - 50-100 concurrent     │    │
│   │  - Process isolation     │    │
│   │  - Auto-restart          │    │
│   └──────────────────────────┘    │
│                                    │
│   ┌──────────────────────────┐    │
│   │  Redis (local)           │    │
│   │  - 2GB memory limit      │    │
│   └──────────────────────────┘    │
└────────────────────────────────────┘

Good for: 
- MVP/Prototype
- <100 concurrent users
- Single region
- Cost-effective start
```

### Pattern 2: Horizontal Scaling (Multi-Server)
```
                 ┌──────────────────┐
                 │  Load Balancer   │
                 └────────┬─────────┘
                          │
          ┌───────────────┼───────────────┐
          │               │               │
    ┌─────▼─────┐   ┌────▼──────┐  ┌────▼──────┐
    │ Server 1  │   │ Server 2  │  │ Server 3  │
    │ 30 agents │   │ 30 agents │  │ 30 agents │
    └─────┬─────┘   └────┬──────┘  └────┬──────┘
          │              │              │
          └──────────────┼──────────────┘
                         │
                 ┌───────▼────────┐
                 │ Redis Cluster  │
                 │  (Primary +    │
                 │   Replicas)    │
                 └───────┬────────┘
                         │
                 ┌───────▼────────┐
                 │  PostgreSQL    │
                 │  (Primary +    │
                 │   Read Replica)│
                 └────────────────┘

Good for:
- Production
- 100-1000+ concurrent users
- Multi-region
- High availability
```

### Pattern 3: Kubernetes Auto-Scaling
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: agent-scaler
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: livekit-agent
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Pods
    pods:
      metric:
        name: active_sessions
      target:
        type: AverageValue
        averageValue: "10"  # 10 sessions per pod
```

## Memory Usage Analysis

### Per-Agent Memory Breakdown
```
Component                    Memory Usage
──────────────────────────────────────────
Python Runtime               50 MB
LiveKit SDK                  30 MB
Provider SDKs (STT/LLM/TTS)  20 MB
Audio Buffers                10 MB
Conversation History         1 KB × N messages
──────────────────────────────────────────
Base per agent:              ~110 MB
+ History (50 messages):     ~50 KB
+ Total:                     ~110 MB per agent

With 100 concurrent agents:
100 × 110 MB = 11 GB (just agents)
+ System overhead = ~4 GB
+ Redis = ~2 GB
────────────────────────────
Total needed: ~17 GB RAM
```

### Redis Memory Calculation
```
Per message:
- role: 10 bytes
- content: ~500 bytes (avg)
- metadata: ~50 bytes
─────────────────
Total: ~560 bytes

Per conversation (50 messages):
560 bytes × 50 = ~28 KB

1000 active conversations:
28 KB × 1000 = ~28 MB

10,000 conversations (with TTL):
28 KB × 10,000 = ~280 MB

Recommendation: 2-4 GB Redis for safety
```

## Monitoring & Observability

### Key Metrics to Track
```python
# Agent-level metrics
agent_memory_usage_mb       # Per process
agent_session_count         # Active sessions per agent
agent_crash_count           # Process restarts

# Redis metrics
redis_memory_used_mb        # Total Redis memory
redis_key_count             # Number of conversations
redis_evicted_keys          # Keys removed by TTL
redis_hit_rate              # Cache efficiency

# System metrics
total_memory_available_gb   # Server capacity
cpu_utilization_percent     # Processing load
network_bandwidth_mbps      # Media streaming
```

### Health Checks
```python
# agents/health.py
async def check_agent_health():
    return {
        "memory_mb": get_process_memory(),
        "active_sessions": len(active_sessions),
        "redis_connected": await redis.ping(),
        "backend_connected": await backend.health_check(),
        "uptime_seconds": time.time() - start_time
    }
```

## Best Practices

### ✅ DO
1. **Use Redis for production** (>10 concurrent users)
2. **Set memory limits** per agent process
3. **Implement graceful shutdown** (save state on exit)
4. **Monitor memory usage** proactively
5. **Set TTLs on Redis keys** (auto-cleanup)
6. **Trim in-memory history** periodically
7. **Use connection pooling** for Redis/DB
8. **Implement circuit breakers** for external services

### ❌ DON'T
1. **Don't rely on in-memory state alone** (production)
2. **Don't load entire conversation history** (limit to context window)
3. **Don't ignore memory limits** (OOM kills)
4. **Don't share state via files** (use Redis)
5. **Don't forget to persist to backend** (source of truth)
6. **Don't skip error handling** (Redis/DB failures)

## Cost Analysis

### Small Deployment (50 concurrent)
```
1 × Server (8 vCPU, 16 GB)     $100/month
1 × Redis (2 GB)               $20/month
1 × PostgreSQL (20 GB)         $30/month
──────────────────────────────────────────
Total:                         ~$150/month
Per user:                      $3/month
```

### Medium Deployment (500 concurrent)
```
3 × Servers (8 vCPU, 16 GB)    $300/month
1 × Redis Cluster (8 GB)       $80/month
1 × PostgreSQL (100 GB)        $100/month
Load Balancer                  $20/month
──────────────────────────────────────────
Total:                         ~$500/month
Per user:                      $1/month
```

### Large Deployment (5000 concurrent)
```
10 × Servers (16 vCPU, 32 GB)  $2000/month
3 × Redis Nodes (16 GB)        $480/month
PostgreSQL Cluster (500 GB)    $500/month
Load Balancer + CDN            $100/month
Monitoring & Logging           $200/month
──────────────────────────────────────────
Total:                         ~$3,280/month
Per user:                      $0.66/month
```

## Summary

**Key Takeaway**: Each LiveKit agent runs in its own process, which means:
- ✅ Better isolation and stability
- ✅ No shared memory bugs
- ✅ Easy horizontal scaling
- ⚠️ Need Redis for shared state
- ⚠️ Higher memory overhead per session

**Critical Understanding**:
- 🏠 **One room = One agent process** (not one per participant or message)
- 👥 Multiple participants in a room share the same agent process
- 💬 All messages in a conversation are handled by the same process
- ⏱️ Process lives from room creation to room closure
- 🔄 New room = New process (complete isolation)

## Frequently Asked Questions

### Q: Does each message from a user spawn a new agent process?
**A: NO!** The agent process stays alive for the entire room session. It handles all messages from all participants in that room.

### Q: If I have 100 participants in one room, do I need 100 agent processes?
**A: NO!** One room = one agent process, regardless of participant count. All 100 participants would share the same agent process.

### Q: What if a participant leaves and rejoins the same room?
**A: Same agent process!** As long as the room exists, the same agent process continues running. The participant reconnecting doesn't create a new process.

### Q: When does an agent process terminate?
**A: When the room closes.** This happens when:
- All participants leave
- Room is explicitly closed
- Timeout expires (configurable)
- Agent crashes (auto-restart may spawn new process)

### Q: How many agent processes can one server handle?
**A: Typically 50-150**, depending on:
- Server resources (CPU, RAM)
- Conversation complexity
- Audio processing load
- Provider API latency

### Q: Can I limit the number of messages stored in memory?
**A: YES!** Recommended approach:
```python
# Keep only last N messages in memory
if len(self.conversation_history) > 50:
    self.conversation_history = self.conversation_history[-20:]
    
# Or use Redis with automatic TTL
await redis_state.append_message(conversation_id, message)
# Old messages automatically expire
```

### Q: What happens to conversation history when agent crashes?
**A: Depends on your setup**:
- ❌ In-memory only: **Lost** (that's why you need persistence!)
- ✅ With Redis: **Preserved** (can be restored)
- ✅ With Backend DB: **Fully preserved** (source of truth)

### Q: Should I use in-memory state for production?
**A: Only as a cache!** Use this pattern:
```
In-Memory (fast, last 10-20 msgs) 
    ↓
Redis (shared, last 50-100 msgs)
    ↓
PostgreSQL (persistent, all messages)
```

**Recommended Setup**:
- **Development**: In-memory (simple, fast to test)
- **Production (<100 users)**: Redis single node
- **Production (>100 users)**: Redis cluster + horizontal scaling
- **Enterprise**: Redis cluster + K8s auto-scaling + multi-region

The investment in Redis pays off immediately once you go beyond prototype stage!
