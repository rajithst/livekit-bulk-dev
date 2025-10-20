# AI Voice Assistant System Architecture

## System Overview

A scalable AI voice assistant system built with LiveKit for real-time voice communication, FastAPI for business logic, and pluggable AI providers (LLM/TTS/STT).

## Architecture Principles

- **Modularity**: Pluggable AI providers, clear separation of concerns
- **Scalability**: Horizontal scaling for all components
- **Maintainability**: Clean architecture, dependency injection, SOLID principles
- **Testability**: Unit tests, integration tests, mocking capabilities
- **Observability**: Logging, metrics, tracing
- **Resilience**: Circuit breakers, retries, graceful degradation

---

## System Architecture

### High-Level Components

```
┌─────────────────┐
│  Web/Mobile     │
│  Client         │
└────────┬────────┘
         │
         │ WebRTC/WSS
         │
┌────────▼────────────────────────────────────────┐
│           LiveKit Server (Self-Hosted)          │
│  - SFU (Selective Forwarding Unit)              │
│  - Room Management                              │
│  - WebRTC Signaling                             │
└────────┬────────────────────────────────────────┘
         │
         │ gRPC/WebSocket
         │
┌────────▼────────────────────────────────────────┐
│         LiveKit Agent Service (Python)          │
│  ┌──────────────────────────────────────────┐   │
│  │  Pluggable AI Provider Layer             │   │
│  │  ┌────────┐ ┌────────┐ ┌────────┐       │   │
│  │  │  STT   │ │  LLM   │ │  TTS   │       │   │
│  │  │Provider│ │Provider│ │Provider│       │   │
│  │  └────────┘ └────────┘ └────────┘       │   │
│  │  - OpenAI   - OpenAI    - OpenAI        │   │
│  │  - Azure    - Azure     - Azure         │   │
│  │  - AWS      - Anthropic - AWS           │   │
│  │  - Google   - Google    - Google        │   │
│  └──────────────────────────────────────────┘   │
│                                                  │
│  ┌──────────────────────────────────────────┐   │
│  │  Lifecycle Hooks                         │   │
│  │  - on_room_joined                        │   │
│  │  - on_participant_connected              │   │
│  │  - on_message_received                   │   │
│  │  - on_conversation_turn                  │   │
│  │  - on_room_left                          │   │
│  └──────────────────────────────────────────┘   │
└────────┬─────────────────────────────────────────┘
         │
         │ REST/gRPC
         │
┌────────▼────────────────────────────────────────┐
│         FastAPI Backend Service                 │
│  ┌──────────────────────────────────────────┐   │
│  │  API Layer (REST/GraphQL)                │   │
│  └──────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────┐   │
│  │  Business Logic Layer                    │   │
│  │  - Conversation Service                  │   │
│  │  - User Management Service               │   │
│  │  - Room Management Service               │   │
│  │  - File Upload Service                   │   │
│  │  - Analytics Service                     │   │
│  └──────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────┐   │
│  │  Repository Layer (Data Access)          │   │
│  └──────────────────────────────────────────┘   │
└────────┬─────────────────────────────────────────┘
         │
         │
    ┌────┴─────┬──────────┬───────────┬─────────┐
    │          │          │           │         │
┌───▼───┐ ┌───▼───┐ ┌────▼─────┐ ┌───▼───┐ ┌──▼──┐
│PostgreSQL│ │ Redis │ │  Azure   │ │Message│ │ S3  │
│          │ │ Cache │ │  Blob    │ │ Queue │ │Store│
│          │ │/State │ │ Storage  │ │(RabbitMQ│     │
│          │ │       │ │          │ │or Azure)│     │
└──────────┘ └───────┘ └──────────┘ └────────┘ └─────┘
```

---

## Component Details

### 1. Client Layer

**Technologies**: React/Vue.js for Web, React Native/Flutter for Mobile

**Responsibilities**:
- Establish WebRTC connection with LiveKit
- Capture and stream audio
- Display conversation UI
- Handle user authentication
- Manage local state

**Key Features**:
- LiveKit client SDK integration
- Audio visualization
- Connection state management
- Reconnection logic
- Error handling and user feedback

---

### 2. LiveKit Server (Self-Hosted)

**Technologies**: LiveKit Server (Go-based)

**Deployment**: Kubernetes on Azure

**Responsibilities**:
- WebRTC SFU (Selective Forwarding Unit)
- Room and participant management
- Audio/Video track routing
- Recording capabilities

**Configuration**:
- Horizontal scaling with Redis for state
- Turn/Stun server configuration
- API keys and authentication

---

### 3. LiveKit Agent Service

**Technologies**: Python, LiveKit Agents SDK

**Architecture**:

```python
# Layer Structure
agents/
├── core/
│   ├── agent.py              # Main agent orchestrator
│   ├── lifecycle.py          # Lifecycle hook definitions
│   └── pipeline.py           # STT -> LLM -> TTS pipeline
├── providers/
│   ├── base.py               # Abstract base classes
│   ├── stt/
│   │   ├── base_stt.py
│   │   ├── openai_stt.py
│   │   ├── azure_stt.py
│   │   ├── aws_stt.py
│   │   └── google_stt.py
│   ├── llm/
│   │   ├── base_llm.py
│   │   ├── openai_llm.py
│   │   ├── azure_llm.py
│   │   ├── anthropic_llm.py
│   │   └── google_llm.py
│   └── tts/
│       ├── base_tts.py
│       ├── openai_tts.py
│       ├── azure_tts.py
│       ├── aws_tts.py
│       └── google_tts.py
├── hooks/
│   ├── conversation_hooks.py  # Save conversations
│   ├── file_hooks.py          # Handle file uploads
│   ├── analytics_hooks.py     # Track metrics
│   └── room_hooks.py          # Room lifecycle
├── state/
│   ├── manager.py             # State management
│   ├── redis_state.py         # Redis state backend
│   └── memory_state.py        # In-memory for dev
└── config/
    └── settings.py            # Configuration management
```

**Key Responsibilities**:
- Connect to LiveKit rooms as an agent participant
- Process audio streams (STT)
- Generate responses (LLM)
- Synthesize speech (TTS)
- Execute lifecycle hooks
- Maintain conversation context
- Handle errors and fallbacks

**State Management**:
- Redis for distributed state
- Conversation context per session
- User preferences and history
- Rate limiting and quota tracking

---

### 4. FastAPI Backend Service

**Technologies**: FastAPI, SQLAlchemy, Pydantic, Redis

**Architecture** (Clean Architecture):

```python
backend/
├── api/
│   ├── v1/
│   │   ├── endpoints/
│   │   │   ├── auth.py
│   │   │   ├── conversations.py
│   │   │   ├── rooms.py
│   │   │   ├── users.py
│   │   │   ├── files.py
│   │   │   └── analytics.py
│   │   └── router.py
│   └── dependencies.py
├── core/
│   ├── config.py
│   ├── security.py
│   ├── logging.py
│   └── exceptions.py
├── services/
│   ├── conversation_service.py
│   ├── user_service.py
│   ├── room_service.py
│   ├── file_service.py
│   ├── analytics_service.py
│   └── livekit_service.py     # LiveKit API integration
├── repositories/
│   ├── base.py
│   ├── conversation_repo.py
│   ├── user_repo.py
│   ├── room_repo.py
│   └── file_repo.py
├── models/
│   ├── database/
│   │   ├── user.py
│   │   ├── conversation.py
│   │   ├── message.py
│   │   ├── room.py
│   │   └── file.py
│   └── schemas/
│       ├── user.py
│       ├── conversation.py
│       ├── room.py
│       └── file.py
├── db/
│   ├── session.py
│   ├── base.py
│   └── migrations/
└── middleware/
    ├── auth.py
    ├── rate_limit.py
    ├── logging.py
    └── error_handler.py
```

**Key Responsibilities**:
- User authentication and authorization (JWT)
- Conversation persistence and retrieval
- Room management and access control
- File upload/download management
- Analytics and reporting
- LiveKit token generation
- Business logic orchestration

**Database Schema**:
```sql
-- Users
users (
  id UUID PRIMARY KEY,
  email VARCHAR UNIQUE,
  name VARCHAR,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
)

-- Rooms
rooms (
  id UUID PRIMARY KEY,
  livekit_room_id VARCHAR UNIQUE,
  name VARCHAR,
  created_by UUID REFERENCES users(id),
  status VARCHAR,
  created_at TIMESTAMP,
  metadata JSONB
)

-- Conversations
conversations (
  id UUID PRIMARY KEY,
  room_id UUID REFERENCES rooms(id),
  user_id UUID REFERENCES users(id),
  started_at TIMESTAMP,
  ended_at TIMESTAMP,
  metadata JSONB
)

-- Messages
messages (
  id UUID PRIMARY KEY,
  conversation_id UUID REFERENCES conversations(id),
  role VARCHAR,  -- user, assistant, system
  content TEXT,
  timestamp TIMESTAMP,
  metadata JSONB  -- STT confidence, tokens used, etc.
)

-- Files
files (
  id UUID PRIMARY KEY,
  conversation_id UUID REFERENCES conversations(id),
  filename VARCHAR,
  blob_url VARCHAR,
  size BIGINT,
  mime_type VARCHAR,
  uploaded_at TIMESTAMP
)
```

---

## Scalability Strategy

### Horizontal Scaling

1. **LiveKit Server**:
   - Multiple instances behind load balancer
   - Redis for shared state
   - Session affinity for WebRTC connections

2. **LiveKit Agents**:
   - Stateless agent workers
   - Queue-based job distribution
   - Auto-scaling based on room count

3. **FastAPI Backend**:
   - Stateless API servers
   - Connection pooling for database
   - Redis for session/cache

### State Management

1. **Session State** (Redis):
   - User sessions
   - Conversation context
   - Rate limiting counters
   - Cache for frequently accessed data

2. **Persistent State** (PostgreSQL):
   - User profiles
   - Conversation history
   - Analytics data
   - Configuration

3. **Blob Storage** (Azure Blob):
   - File uploads
   - Recording storage
   - Backups

### Performance Optimization

- **Caching Strategy**: Redis for hot data, TTL-based invalidation
- **Database**: Connection pooling, read replicas, indexing
- **CDN**: Static assets and recorded files
- **Message Queue**: Async processing for non-critical tasks

---

## Deployment Architecture (Azure)

### Azure Resources

```
Azure Cloud
├── Resource Group: rg-voiceassistant-prod
│
├── Virtual Network (VNet)
│   ├── Subnet: aks-subnet (10.0.0.0/16)
│   ├── Subnet: db-subnet (10.1.0.0/16)
│   └── Subnet: cache-subnet (10.2.0.0/16)
│
├── Azure Kubernetes Service (AKS)
│   ├── Node Pool: system (2-4 nodes)
│   ├── Node Pool: livekit (2-10 nodes, auto-scale)
│   ├── Node Pool: agents (4-20 nodes, auto-scale)
│   └── Node Pool: api (2-10 nodes, auto-scale)
│
├── Azure Database for PostgreSQL
│   ├── Primary: General Purpose, 4 vCores
│   └── Read Replicas: 2 replicas
│
├── Azure Cache for Redis
│   ├── Premium tier (clustering enabled)
│   └── 6GB+ memory
│
├── Azure Blob Storage
│   ├── Container: conversations
│   ├── Container: uploads
│   └── Container: recordings
│
├── Azure Load Balancer
│   ├── Public IP for LiveKit
│   └── Public IP for API
│
├── Azure Application Gateway (optional)
│   └── WAF enabled
│
├── Azure Service Bus (or RabbitMQ on AKS)
│   └── Queues for async processing
│
├── Azure Monitor
│   ├── Application Insights
│   ├── Log Analytics
│   └── Container Insights
│
├── Azure Key Vault
│   ├── API Keys (OpenAI, Azure AI)
│   ├── Database credentials
│   └── LiveKit secrets
│
└── Azure CDN (optional)
    └── Static assets and recordings
```

### Kubernetes Architecture

```yaml
AKS Cluster
├── Namespace: livekit-system
│   ├── Deployment: livekit-server (2-10 replicas)
│   ├── Service: livekit-server (LoadBalancer)
│   └── ConfigMap/Secrets
│
├── Namespace: agents
│   ├── Deployment: livekit-agents (4-20 replicas)
│   ├── HPA: Auto-scaling based on CPU/Memory
│   └── ConfigMap/Secrets
│
├── Namespace: api
│   ├── Deployment: fastapi-backend (2-10 replicas)
│   ├── Service: fastapi-service
│   ├── HPA: Auto-scaling
│   └── ConfigMap/Secrets
│
├── Namespace: monitoring
│   ├── Prometheus
│   ├── Grafana
│   └── Loki
│
└── Ingress Controller (NGINX)
    ├── TLS termination
    └── Path-based routing
```

### Network Architecture

```
Internet
    │
    ├─── Azure Traffic Manager (Global)
    │
    ├─── Azure Front Door / Application Gateway
    │    ├── WAF Rules
    │    └── SSL/TLS Termination
    │
    ├─── Azure Load Balancer
    │
    ├─── AKS Cluster (Private IPs)
    │    ├── Ingress Controller
    │    ├── LiveKit Server (UDP/TCP ports)
    │    ├── Agent Services
    │    └── API Services
    │
    └─── Private Endpoints
         ├── PostgreSQL (private subnet)
         ├── Redis (private subnet)
         └── Blob Storage (private endpoint)
```

### Auto-Scaling Configuration

1. **AKS Cluster Auto-scaler**:
   - Min nodes: 2 per pool
   - Max nodes: 20 per pool
   - Scale based on resource requests

2. **Horizontal Pod Auto-scaler (HPA)**:
   - **LiveKit Agents**: Scale on room count (1 pod per 5 rooms)
   - **API Pods**: Scale on CPU (target 70%)
   - **LiveKit Server**: Scale on WebRTC connections

3. **Metrics**:
   - CPU utilization
   - Memory usage
   - Custom metrics (active rooms, queue depth)

---

## Deployment Strategy

### CI/CD Pipeline (Azure DevOps / GitHub Actions)

```yaml
Pipeline Stages:
1. Build:
   - Build Docker images
   - Run unit tests
   - Security scanning
   - Push to Azure Container Registry

2. Test:
   - Integration tests
   - Load tests
   - API tests

3. Deploy to Staging:
   - Deploy to AKS staging namespace
   - Run smoke tests
   - Performance validation

4. Deploy to Production:
   - Blue-Green or Canary deployment
   - Health checks
   - Rollback capability
   - Monitoring alerts
```

### Infrastructure as Code

- **Terraform** for Azure resources
- **Helm Charts** for Kubernetes deployments
- **ArgoCD** for GitOps (optional)

---

## Security Architecture

### Authentication & Authorization

1. **Client → API**:
   - JWT tokens with refresh tokens
   - OAuth2 / OIDC (Azure AD integration)

2. **Client → LiveKit**:
   - Short-lived LiveKit tokens generated by API
   - Token grants specific to rooms

3. **Agent → LiveKit**:
   - API key authentication
   - Scoped permissions

4. **Agent → Backend**:
   - Service-to-service authentication (mTLS or API keys)

### Network Security

- Private subnets for databases
- Network Security Groups (NSGs)
- Azure Private Link for services
- VPN/ExpressRoute for on-prem integration
- WAF for DDoS protection

### Data Security

- Encryption at rest (Azure Storage encryption)
- Encryption in transit (TLS 1.3)
- Key rotation (Azure Key Vault)
- Data retention policies
- GDPR compliance features

---

## Monitoring & Observability

### Metrics (Prometheus + Grafana)

- **LiveKit Metrics**: Room count, participant count, bandwidth
- **Agent Metrics**: Processing time, error rates, provider latency
- **API Metrics**: Request rate, response time, error rate
- **Infrastructure**: CPU, memory, disk, network

### Logging (ELK or Azure Monitor)

- Structured logging (JSON)
- Correlation IDs across services
- Log levels: DEBUG, INFO, WARN, ERROR
- Retention policies

### Tracing (Jaeger or Application Insights)

- Distributed tracing across services
- Request flow visualization
- Performance bottleneck identification

### Alerting

- PagerDuty / OpsGenie integration
- Slack notifications
- Alert rules:
  - High error rates
  - Service unavailability
  - Resource saturation
  - Cost anomalies

---

## Disaster Recovery

### Backup Strategy

- **Database**: Daily automated backups, 30-day retention
- **Blob Storage**: Geo-redundant storage (GRS)
- **Configuration**: GitOps, version controlled

### High Availability

- Multi-zone deployment in AKS
- Database replicas
- Redis cluster mode
- Health checks and auto-recovery

### Recovery Time Objectives

- **RTO**: < 1 hour for critical services
- **RPO**: < 5 minutes for database

---

## Cost Optimization

1. **Reserved Instances** for baseline compute
2. **Spot Instances** for burst capacity
3. **Auto-scaling** to match demand
4. **Blob Storage Lifecycle** policies (cool/archive tiers)
5. **Monitoring** cost anomalies
6. **Right-sizing** resources based on usage

---

## Testing Strategy

### Unit Tests
- Provider implementations
- Business logic services
- Repository layer

### Integration Tests
- API endpoints
- Database operations
- Redis operations

### E2E Tests
- Client → LiveKit → Agent → Backend flow
- Conversation scenarios

### Load Tests
- Simulate thousands of concurrent users
- Stress test individual components
- Identify bottlenecks

---

## Development Workflow

### Local Development

```bash
# Docker Compose for local development
docker-compose.dev.yml:
  - PostgreSQL
  - Redis
  - LiveKit Server
  - FastAPI Backend
  - Agent Service (with mock providers)
```

### Environment Strategy

- **Development**: Local Docker Compose
- **Staging**: AKS cluster (smaller instance)
- **Production**: AKS cluster (full scale)

---

## Migration & Rollout Plan

### Phase 1: MVP (Weeks 1-4)
- Basic LiveKit + OpenAI integration
- Simple FastAPI backend
- User authentication
- Single room conversations

### Phase 2: Multi-Provider (Weeks 5-8)
- Pluggable provider architecture
- Azure, AWS, Google implementations
- Provider selection logic
- Configuration management

### Phase 3: Scale (Weeks 9-12)
- Kubernetes deployment
- Auto-scaling setup
- Monitoring and alerting
- Load testing

### Phase 4: Production (Weeks 13-16)
- Azure deployment
- Security hardening
- Performance optimization
- Documentation

---

## Future Enhancements

- Multi-modal support (vision, documents)
- Advanced analytics and insights
- A/B testing framework
- Multi-language support
- Voice activity detection improvements
- Custom wake words
- Sentiment analysis
- Real-time translation

