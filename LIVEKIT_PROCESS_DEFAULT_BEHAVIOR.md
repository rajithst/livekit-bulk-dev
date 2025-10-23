# LiveKit Agent Process Model - Default Behavior

## TL;DR
✅ **Yes, LiveKit automatically uses one process per room BY DEFAULT**  
✅ **No configuration needed** - it's the built-in behavior  
✅ **Works out of the box** when you use the standard entrypoint pattern  

## How It Works

### The Magic Happens in `cli.run_app()`

```python
# Your agent code (agents/core/agent.py)
if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,  # ← This function runs once per room
        )
    )
```

**What happens behind the scenes:**

1. LiveKit Server detects a new room needs an agent
2. LiveKit Agent framework **spawns a new Python process**
3. Calls your `entrypoint()` function in that new process
4. One room → One `entrypoint()` call → One process
5. Process stays alive until room closes

### The Entrypoint Function

```python
async def entrypoint(ctx: JobContext):
    """
    This function is called ONCE per room.
    The entire function runs in a single process.
    """
    
    # Setup (runs once when room is created)
    logger.info("Agent starting for room", extra={
        "room_name": ctx.room.name,
        "job_id": ctx.job.id
    })
    
    agent = VoiceAssistantAgent(...)
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    
    # Wait for participants (same process)
    participant = await ctx.wait_for_participant()
    
    # Start agent session (same process)
    session = AgentSession(...)
    await session.start(room=ctx.room, agent=agent)
    
    # Keep running (same process handles ALL events)
    # - All participants joining/leaving
    # - All messages from all participants
    # - All STT/LLM/TTS events
    await ctx.wait_for_disconnection()
    
    # Cleanup (runs once when room closes)
    logger.info("Agent completed")
    # Process terminates here
```

## Visual Flow

```
┌────────────────────────────────────────────────────────┐
│            LiveKit Server (Central Coordinator)        │
└────────────────────┬───────────────────────────────────┘
                     │
         New room "meeting-1" needs an agent
                     │
                     ↓
         ┌───────────────────────────┐
         │  Agent Worker Process     │
         │  (Your Python script)     │
         └───────────┬───────────────┘
                     │
              Spawns new process
                     │
                     ↓
         ┌───────────────────────────┐
         │  Process 1 (PID: 12345)   │
         │  ───────────────────────  │
         │  Calls: entrypoint(ctx)   │
         │  Room: "meeting-1"        │
         │  ───────────────────────  │
         │  Handles all events       │
         │  for this room only       │
         └───────────────────────────┘

         New room "meeting-2" needs an agent
                     │
                     ↓
         ┌───────────────────────────┐
         │  Process 2 (PID: 12346)   │
         │  ───────────────────────  │
         │  Calls: entrypoint(ctx)   │
         │  Room: "meeting-2"        │
         │  ───────────────────────  │
         │  Completely separate      │
         │  from Process 1           │
         └───────────────────────────┘
```

## Configuration Options

While one-process-per-room is the default, you CAN configure some behaviors:

### 1. Worker Options (Optional)
```python
from livekit.agents import cli, WorkerOptions

cli.run_app(
    WorkerOptions(
        entrypoint_fnc=entrypoint,
        
        # Optional configurations:
        num_idle_processes=3,        # Pre-spawn processes for faster startup
        max_retry=3,                  # Retry failed jobs
        shutdown_process_timeout=60,  # Graceful shutdown timeout
        initialize_process_fnc=init,  # Custom initialization per process
    )
)
```

### 2. Process Pool (Advanced)
```python
# You can configure a process pool for faster room assignment
WorkerOptions(
    entrypoint_fnc=entrypoint,
    num_idle_processes=5,  # Keep 5 idle processes ready
)

# Benefits:
# - Faster room assignment (no spawn delay)
# - Still one process per room
# - Processes are recycled after use
```

### 3. Custom Process Limits (System-level)
```bash
# Limit total processes (OS level)
ulimit -u 500  # Max 500 processes

# Or in Docker/K8s
resources:
  limits:
    memory: "16Gi"  # Indirect limit via memory
```

## What You Don't Need to Configure

❌ **Don't need to configure**:
- Process spawning (automatic)
- Room-to-process mapping (automatic)
- Process lifecycle (automatic)
- Inter-process communication (not needed - isolated)

✅ **Already handled by LiveKit**:
- Process creation when room is created
- Process termination when room closes
- Resource cleanup
- Crash recovery (optional restart)

## Verification - Check It Yourself

### Method 1: Check Running Processes
```bash
# Start your agent
python agents/core/agent.py

# In another terminal, check processes
ps aux | grep python | grep agent

# You'll see:
# - One main worker process (waits for jobs)
# - One process per active room
```

### Method 2: Add Logging
```python
import os

async def entrypoint(ctx: JobContext):
    logger.info(f"Agent started - PID: {os.getpid()}, Room: {ctx.room.name}")
    # ... rest of code
    
# Output will show different PIDs for different rooms:
# Agent started - PID: 12345, Room: meeting-1
# Agent started - PID: 12346, Room: meeting-2
```

### Method 3: Monitor with Docker Stats
```bash
# If running in Docker
docker stats

# Watch CPU/Memory per container
# Each active room will use resources in its process
```

## Common Misconceptions

### ❌ Myth: "I need to configure process pooling"
**Reality**: No! One-process-per-room works by default. Process pooling is just an optimization for faster startup.

### ❌ Myth: "I need to manage process creation"
**Reality**: No! LiveKit handles all process management automatically.

### ❌ Myth: "Multiple rooms will share a process"
**Reality**: No! Each room gets its own isolated process automatically.

### ❌ Myth: "I need IPC (Inter-Process Communication)"
**Reality**: No! Processes are isolated. Use Redis/DB for shared state if needed.

## When Would You Configure Something?

### Use Case 1: Faster Startup
```python
# Pre-spawn processes to avoid cold start
WorkerOptions(
    entrypoint_fnc=entrypoint,
    num_idle_processes=3,  # Keep 3 ready
)
```

### Use Case 2: Resource Limits
```python
# In Kubernetes deployment
resources:
  limits:
    memory: "512Mi"  # Per pod (process)
    cpu: "500m"
  requests:
    memory: "256Mi"
    cpu: "250m"
```

### Use Case 3: Custom Initialization
```python
# Run setup once per process (before room assignment)
async def initialize_process():
    """Called once when process starts, before handling rooms."""
    await load_models()  # Load AI models once
    await connect_to_services()  # Setup connections

WorkerOptions(
    entrypoint_fnc=entrypoint,
    initialize_process_fnc=initialize_process,
)
```

### Use Case 4: Horizontal Scaling
```yaml
# Scale number of worker instances (not processes per room)
# kubernetes/agents/deployment.yaml
replicas: 5  # 5 worker instances

# Each worker can handle multiple rooms (one process each)
# Total capacity: 5 workers × ~20 rooms/worker = 100 rooms
```

## Summary

**Default Behavior** (no configuration needed):
```
1 Room created → 1 entrypoint() call → 1 Process spawned
```

**What LiveKit Automatically Does**:
- ✅ Spawns process when room needs agent
- ✅ Routes room to process
- ✅ Maintains process for room duration
- ✅ Cleans up when room closes
- ✅ Isolates processes from each other

**What You Control**:
- Your `entrypoint()` function logic
- Agent behavior and providers
- State management (in-memory vs Redis)
- Horizontal scaling (number of workers)

**Bottom Line**: Just write your `entrypoint()` function and LiveKit handles all the process management! 🎉

## Quick Start Example

```python
# This is all you need! No process configuration required.

from livekit.agents import cli, WorkerOptions, JobContext

async def entrypoint(ctx: JobContext):
    """Runs once per room - that's it!"""
    agent = VoiceAssistantAgent(...)
    await ctx.connect()
    await agent.on_enter()
    # Handle room events...
    await ctx.wait_for_disconnection()
    await agent.on_exit()

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
    # ↑ This is all the "configuration" you need!
```

That's it! LiveKit takes care of creating one process per room automatically.
