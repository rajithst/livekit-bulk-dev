# FastAPI Backend: Stateless Design

## Overview

**Yes, the FastAPI backend is designed to be STATELESS!** This is critical for horizontal scaling and cloud-native deployment.

## Current State Architecture

### Backend State Management

```
┌──────────────────────────────────────────────────────┐
│  FastAPI Backend (Stateless)                         │
│  ┌────────────────────────────────────────────────┐  │
│  │  API Endpoints (No session state)              │  │
│  │  - POST /api/v1/rooms                          │  │
│  │  - POST /api/v1/conversations/save-turn        │  │
│  │  - GET /api/v1/conversations/{id}/messages     │  │
│  └────────────────────────────────────────────────┘  │
│                                                       │
│  ┌────────────────────────────────────────────────┐  │
│  │  Services (Business Logic - Stateless)         │  │
│  │  - ConversationService                         │  │
│  │  - RoomService                                 │  │
│  │  - UserService                                 │  │
│  └────────────────────────────────────────────────┘  │
│                                                       │
│  ┌────────────────────────────────────────────────┐  │
│  │  Repositories (Data Access - Stateless)        │  │
│  │  - ConversationRepo → PostgreSQL               │  │
│  │  - UserRepo → PostgreSQL                       │  │
│  └────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────────────────┐
│  External State Storage                              │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐    │
│  │ PostgreSQL │  │   Redis    │  │ Blob Store │    │
│  │(Persistent)│  │  (Cache)   │  │  (Files)   │    │
│  └────────────┘  └────────────┘  └────────────┘    │
└──────────────────────────────────────────────────────┘
```

## Stateless Design Principles

### ✅ Backend IS Stateless

**No in-memory session state:**
```python
# ❌ BAD: Stateful (storing in memory)
class ConversationService:
    def __init__(self):
        self.active_conversations = {}  # ❌ Don't do this!
        self.user_sessions = {}          # ❌ Bad for scaling!

# ✅ GOOD: Stateless (everything in database)
class ConversationService:
    def __init__(self, db: AsyncSession):
        self.db = db  # Database session only
    
    async def get_conversation(self, conversation_id: str):
        # Query database every time (stateless)
        return await self.db.query(Conversation).filter_by(
            id=conversation_id
        ).first()
```

### ✅ Every Request is Independent

```python
# Each request gets fresh context from database
@router.post("/api/v1/conversations/save-turn")
async def save_conversation_turn(
    request: SaveTurnRequest,
    db: AsyncSession = Depends(get_db)  # Fresh DB session
):
    # 1. No session state - everything from DB
    conversation = await ConversationRepo(db).get_by_id(
        request.conversation_id
    )
    
    # 2. Save to database (persistent state)
    message = Message(
        conversation_id=conversation.id,
        role="user",
        content=request.user_message
    )
    await db.add(message)
    await db.commit()
    
    # 3. Return response (no state kept in memory)
    return {"status": "saved"}
    # Database session closed automatically
```

## State Storage Layers

### Layer 1: PostgreSQL (Persistent State)

**What it stores:**
- User accounts
- Conversations (metadata)
- Messages (all conversation turns)
- Rooms (room details)
- Files metadata

**Example:**
```python
# backend/repositories/conversation_repo.py
class ConversationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db  # Stateless - just DB connection
    
    async def save_message(
        self,
        conversation_id: str,
        role: str,
        content: str
    ) -> Message:
        # All state in database
        message = Message(
            id=uuid.uuid4(),
            conversation_id=conversation_id,
            role=role,
            content=content,
            created_at=datetime.utcnow()
        )
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)
        return message
```

### Layer 2: Redis (Cache & Sessions)

**What it stores:**
- JWT token blacklist
- Rate limiting counters
- Temporary cache (query results)
- User session cache (optional)

**Why Redis is OK for stateless:**
- Cache can be rebuilt
- Not source of truth
- Can be cleared without data loss
- Used for performance, not state

**Example:**
```python
# backend/middleware/rate_limit.py
class RateLimitMiddleware:
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def check_rate_limit(self, user_id: str) -> bool:
        key = f"rate_limit:{user_id}"
        count = await self.redis.incr(key)
        
        if count == 1:
            await self.redis.expire(key, 60)  # 1 minute window
        
        return count <= 60  # Max 60 requests/minute
    
    # This is stateless because:
    # 1. Rate limit data can be lost (just resets counters)
    # 2. Not critical business data
    # 3. Helps prevent abuse, not store state
```

### Layer 3: Azure Blob Storage (File Storage)

**What it stores:**
- Uploaded files
- Audio recordings
- Conversation exports
- User uploads

**Stateless pattern:**
```python
# backend/services/file_service.py
class FileService:
    def __init__(self, blob_client: BlobServiceClient):
        self.blob_client = blob_client
    
    async def upload_file(
        self,
        file_data: bytes,
        filename: str,
        conversation_id: str
    ) -> str:
        # Upload to blob storage
        blob_name = f"{conversation_id}/{uuid.uuid4()}/{filename}"
        blob_client = self.blob_client.get_blob_client(
            container="uploads",
            blob=blob_name
        )
        await blob_client.upload_blob(file_data)
        
        # Save metadata to database (not memory!)
        file_record = File(
            id=uuid.uuid4(),
            conversation_id=conversation_id,
            blob_name=blob_name,
            filename=filename,
            uploaded_at=datetime.utcnow()
        )
        await self.db.add(file_record)
        await self.db.commit()
        
        return blob_name
```

## Achieving True Statelessness

### 1. JWT for Authentication (No Server Sessions)

**Stateless Auth:**
```python
# backend/core/security.py
def create_access_token(user_id: str) -> str:
    """Create JWT token (stateless)."""
    payload = {
        "sub": user_id,
        "exp": datetime.utcnow() + timedelta(minutes=30),
        "iat": datetime.utcnow()
    }
    # Token contains all info needed
    # No server-side session storage!
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def verify_token(token: str) -> dict:
    """Verify JWT token (stateless)."""
    try:
        # Decode token - no database lookup needed
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except JWTError:
        raise HTTPException(401, "Invalid token")

# Usage in endpoint
@router.get("/api/v1/profile")
async def get_profile(
    current_user: dict = Depends(get_current_user)  # From JWT
):
    # User info from token, not server session
    user_id = current_user["sub"]
    # Fetch from database (stateless)
    return await UserRepo(db).get_by_id(user_id)
```

### 2. Database Connection Pooling (Not Session State)

**Important: Connection pool ≠ State**
```python
# backend/db/session.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Connection pool is for performance, not state
engine = create_async_engine(
    DATABASE_URL,
    pool_size=10,        # Reuse connections
    max_overflow=20,     # Burst capacity
    pool_pre_ping=True   # Check connection health
)

AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db() -> AsyncSession:
    """Dependency: Get database session (per request)."""
    async with AsyncSessionLocal() as session:
        yield session
        # Session closed after request
        # No state persists between requests!
```

**Each request gets fresh session:**
```python
@router.post("/api/v1/conversations")
async def create_conversation(
    request: CreateConversationRequest,
    db: AsyncSession = Depends(get_db)  # Fresh session
):
    # Use database session
    conversation = await ConversationRepo(db).create(request)
    
    # Session automatically closed after request
    return conversation
```

### 3. No In-Memory Caches (Use Redis Instead)

**❌ Stateful (bad):**
```python
# DON'T DO THIS - Breaks statelessness!
class ConversationService:
    def __init__(self):
        self.cache = {}  # ❌ In-memory cache
    
    async def get_conversation(self, conv_id: str):
        if conv_id in self.cache:
            return self.cache[conv_id]
        
        conv = await db.query(Conversation).get(conv_id)
        self.cache[conv_id] = conv  # ❌ Stored in memory
        return conv
```

**✅ Stateless (good):**
```python
class ConversationService:
    def __init__(self, db: AsyncSession, redis: RedisClient):
        self.db = db
        self.redis = redis  # Shared cache
    
    async def get_conversation(self, conv_id: str):
        # Check Redis cache (shared across all instances)
        cached = await self.redis.get(f"conversation:{conv_id}")
        if cached:
            return json.loads(cached)
        
        # Query database
        conv = await self.db.query(Conversation).filter_by(
            id=conv_id
        ).first()
        
        # Cache in Redis (shared, not local memory)
        await self.redis.setex(
            f"conversation:{conv_id}",
            300,  # 5 minutes
            json.dumps(conv.to_dict())
        )
        
        return conv
```

## Horizontal Scaling Benefits

### Without Statelessness (Stateful)

```
Request 1 → Backend Pod 1 (has session A in memory)
Request 2 → Backend Pod 2 (doesn't have session A!) ❌
            ↓
         User needs to reconnect
         Sticky sessions required
         Can't scale freely
```

### With Statelessness (Current Design)

```
Request 1 → Backend Pod 1 → PostgreSQL (session A)
Request 2 → Backend Pod 2 → PostgreSQL (session A) ✅
Request 3 → Backend Pod 3 → PostgreSQL (session A) ✅
            ↓
         All pods can serve any request
         No sticky sessions needed
         Scales horizontally easily
```

## Load Balancing

**Stateless allows round-robin:**
```yaml
# k8s/api/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: backend-api
spec:
  type: LoadBalancer
  selector:
    app: backend-api
  ports:
    - port: 80
      targetPort: 8000
  # No session affinity needed - truly stateless!
  sessionAffinity: None
```

## When Redis is Used (Still Stateless!)

### Use Case 1: Rate Limiting

```python
# Temporary counters - can be lost
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host
    key = f"rate_limit:{client_ip}"
    
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, 60)
    
    if count > 100:
        raise HTTPException(429, "Too many requests")
    
    return await call_next(request)
```

### Use Case 2: JWT Blacklist

```python
# Token revocation - not session state
async def logout(token: str, redis: RedisClient):
    # Add token to blacklist
    await redis.setex(
        f"blacklist:{token}",
        3600,  # Token expiry time
        "1"
    )

async def verify_token(token: str, redis: RedisClient):
    # Check if token is blacklisted
    if await redis.exists(f"blacklist:{token}"):
        raise HTTPException(401, "Token revoked")
    
    # Verify JWT (stateless)
    return jwt.decode(token, SECRET_KEY)
```

### Use Case 3: Query Cache (Performance)

```python
# Cache for performance - can be cleared
async def get_user_conversations(user_id: str):
    cache_key = f"user_conversations:{user_id}"
    
    # Try cache first
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # Query database (source of truth)
    conversations = await db.query(Conversation).filter_by(
        user_id=user_id
    ).all()
    
    # Cache for 5 minutes
    await redis.setex(
        cache_key,
        300,
        json.dumps([c.to_dict() for c in conversations])
    )
    
    return conversations
```

**Why this is still stateless:**
- Redis is shared across all backend pods
- Cache can be cleared without data loss
- PostgreSQL is source of truth
- Any pod can rebuild cache from database

## Deployment: Multiple Backend Instances

### Docker Compose (Dev)

```yaml
# docker-compose.yml
services:
  # Stateless backend - can run multiple instances
  backend-api-1:
    image: backend:latest
    environment:
      - DATABASE_URL=postgresql://...
      - REDIS_URL=redis://redis:6379
    # No volumes for state - truly stateless!
  
  backend-api-2:
    image: backend:latest
    environment:
      - DATABASE_URL=postgresql://...  # Same database
      - REDIS_URL=redis://redis:6379    # Same Redis
    # Exact same config - interchangeable!
  
  # Load balancer distributes requests
  nginx:
    image: nginx:latest
    depends_on:
      - backend-api-1
      - backend-api-2
    # Round-robin load balancing works!
```

### Kubernetes (Production)

```yaml
# k8s/api/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend-api
spec:
  replicas: 5  # Can scale to any number!
  selector:
    matchLabels:
      app: backend-api
  template:
    metadata:
      labels:
        app: backend-api
    spec:
      containers:
      - name: backend
        image: backend:latest
        env:
          - name: DATABASE_URL
            valueFrom:
              secretKeyRef:
                name: db-secret
                key: url
          - name: REDIS_URL
            valueFrom:
              secretKeyRef:
                name: redis-secret
                key: url
        # No persistent volumes - stateless!
        
---
# Horizontal Pod Autoscaler - works because stateless!
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend-api
  minReplicas: 2
  maxReplicas: 20  # Can scale freely!
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

## Conversation Flow (Stateless)

### 1. Create Room
```python
# Any backend pod can handle this
@router.post("/api/v1/rooms")
async def create_room(
    request: CreateRoomRequest,
    db: AsyncSession = Depends(get_db),
    livekit_service: LiveKitService = Depends()
):
    # 1. Create in database (persistent state)
    room = Room(
        id=uuid.uuid4(),
        name=request.name,
        created_by=request.user_id,
        created_at=datetime.utcnow()
    )
    db.add(room)
    await db.commit()
    
    # 2. Create in LiveKit
    conversation_id = str(uuid.uuid4())
    await livekit_service.create_room(
        room.name,
        metadata={"conversation_id": conversation_id}
    )
    
    # 3. Return response (no state kept in pod)
    return {
        "room_id": room.id,
        "conversation_id": conversation_id
    }
    # Database session closed - pod is stateless again!
```

### 2. Save Conversation Turn
```python
# Different backend pod can handle this
@router.post("/api/v1/conversations/save-turn")
async def save_turn(
    request: SaveTurnRequest,
    db: AsyncSession = Depends(get_db)
):
    # Query database (no in-memory state needed)
    conversation = await db.query(Conversation).filter_by(
        id=request.conversation_id
    ).first()
    
    if not conversation:
        raise HTTPException(404, "Conversation not found")
    
    # Save messages to database
    user_msg = Message(
        id=uuid.uuid4(),
        conversation_id=conversation.id,
        role="user",
        content=request.user_message,
        created_at=datetime.utcnow()
    )
    assistant_msg = Message(
        id=uuid.uuid4(),
        conversation_id=conversation.id,
        role="assistant",
        content=request.assistant_message,
        created_at=datetime.utcnow()
    )
    
    db.add_all([user_msg, assistant_msg])
    await db.commit()
    
    # Invalidate cache (if using)
    await redis.delete(f"conversation:{conversation.id}:messages")
    
    return {"status": "saved"}
```

### 3. Get Conversation History
```python
# Yet another backend pod can serve this
@router.get("/api/v1/conversations/{conversation_id}/messages")
async def get_messages(
    conversation_id: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends()
):
    # Check Redis cache
    cache_key = f"conversation:{conversation_id}:messages"
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # Query database
    messages = await db.query(Message).filter_by(
        conversation_id=conversation_id
    ).order_by(Message.created_at.desc()).limit(limit).all()
    
    result = {
        "conversation_id": conversation_id,
        "messages": [m.to_dict() for m in messages]
    }
    
    # Cache for 5 minutes
    await redis.setex(cache_key, 300, json.dumps(result))
    
    return result
```

## Summary: Is Backend Stateless?

### ✅ YES - Backend is Fully Stateless!

**What makes it stateless:**
1. ✅ No in-memory session state
2. ✅ JWT authentication (no server sessions)
3. ✅ Database connection pool (not state storage)
4. ✅ Each request independent
5. ✅ Redis for cache only (can be cleared)
6. ✅ All state in PostgreSQL (persistent)
7. ✅ Can scale horizontally freely

**State storage:**
- ✅ PostgreSQL: Persistent data (source of truth)
- ✅ Redis: Cache & rate limiting (can be lost)
- ✅ Blob Storage: Files (persistent)

**Benefits:**
- ✅ Horizontal scaling (2-20+ pods)
- ✅ No sticky sessions needed
- ✅ Load balancer can use round-robin
- ✅ Pods are interchangeable
- ✅ Easy to deploy/rollback
- ✅ Auto-scaling works seamlessly

### Comparison: Agent vs Backend State

| Aspect | Agent (Session State) | Backend (Stateless) |
|--------|----------------------|---------------------|
| **Session State** | In-memory (current session) | No session state |
| **Persistence** | Async to backend | Direct to PostgreSQL |
| **Scaling** | One per room | Horizontal (unlimited) |
| **State Lifetime** | Until disconnect | Permanent (database) |
| **Cache** | In-memory only | Redis (shared) |
| **Auth** | N/A | JWT (stateless) |

**Key Insight:**
- **Agents** hold temporary session state (conversation history)
- **Backend** holds permanent persistent state (database)
- Both architectures support massive scale!

## Architectural Diagram

```
┌────────────────────────────────────────────────────────┐
│  Load Balancer (Round Robin)                          │
└────────┬───────────────────────────────────────────────┘
         │
         ├──────┬──────┬──────┬──────┬──────┐
         │      │      │      │      │      │
         ▼      ▼      ▼      ▼      ▼      ▼
      ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐
      │Pod1│ │Pod2│ │Pod3│ │Pod4│ │Pod5│ │Pod6│
      │API │ │API │ │API │ │API │ │API │ │API │
      └──┬─┘ └──┬─┘ └──┬─┘ └──┬─┘ └──┬─┘ └──┬─┘
         │      │      │      │      │      │
         │      └──────┴──────┴──────┴──────┘
         │                    │
         │                    │ All pods share
         ▼                    ▼ same storage
    ┌──────────────────────────────────────┐
    │  PostgreSQL (Source of Truth)        │
    │  - Users, Conversations, Messages    │
    └──────────────────────────────────────┘
                    │
                    ▼
    ┌──────────────────────────────────────┐
    │  Redis (Shared Cache)                │
    │  - Rate limits, JWT blacklist        │
    └──────────────────────────────────────┘
                    │
                    ▼
    ┌──────────────────────────────────────┐
    │  Azure Blob Storage (Files)          │
    │  - Uploads, recordings               │
    └──────────────────────────────────────┘

✅ Any pod can serve any request!
✅ Pods can be added/removed freely!
✅ Load balancer doesn't need session affinity!
```

🎯 **Conclusion:** The FastAPI backend is **fully stateless** and designed for cloud-native horizontal scaling!
