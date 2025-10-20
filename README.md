# AI Voice Assistant System

A scalable, production-ready AI voice assistant system built with LiveKit, FastAPI, and pluggable AI providers (OpenAI, Azure, AWS, Google).

## Features

✅ **Real-time Voice Conversations** - WebRTC-based low-latency voice communication  
✅ **Pluggable AI Providers** - Easy swap between OpenAI, Azure, AWS, Google for STT/LLM/TTS  
✅ **Scalable Architecture** - Kubernetes-based deployment supporting thousands of concurrent users  
✅ **Self-hosted LiveKit** - Full control over your voice infrastructure  
✅ **Business Logic Integration** - Lifecycle hooks for conversation saving, file uploads, analytics  
✅ **Production-ready** - Comprehensive monitoring, logging, and error handling  
✅ **Azure Deployment** - Complete infrastructure-as-code for Azure cloud

## Architecture

```
Client (Web/Mobile) 
    ↓ WebRTC
LiveKit Server (Self-hosted)
    ↓ gRPC
LiveKit Agents (Pluggable AI)
    ↓ REST
FastAPI Backend
    ↓
PostgreSQL + Redis + Azure Blob Storage
```

See [ARCHITECTURE.md](./ARCHITECTURE.md) for detailed system architecture.

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Node.js 18+ (for client)
- OpenAI API Key (or other AI provider keys)

### Local Development

1. **Clone the repository**
```bash
git clone <repository-url>
cd livekit-starter
```

2. **Create environment file**
```bash
cp .env.example .env
# Edit .env with your API keys
```

3. **Start services with Docker Compose**
```bash
docker-compose up -d
```

4. **Access the services**
- LiveKit Server: http://localhost:7880
- FastAPI Backend: http://localhost:8000
- API Docs: http://localhost:8000/api/docs

### Environment Variables

```env
# LiveKit
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=devsecret

# Database
DATABASE_URL=postgresql+asyncpg://voiceassistant:dev_password@localhost:5432/voiceassistant

# Redis
REDIS_URL=redis://localhost:6379

# AI Providers
OPENAI_API_KEY=your-openai-api-key
STT_PROVIDER=openai
LLM_PROVIDER=openai
TTS_PROVIDER=openai
LLM_MODEL=gpt-4
TTS_VOICE=alloy

# Backend
SECRET_KEY=your-secret-key
BACKEND_API_URL=http://localhost:8000
BACKEND_API_KEY=dev-backend-key

# Azure (Production)
AZURE_STORAGE_CONNECTION_STRING=your-connection-string
```

## Project Structure

```
livekit-starter/
├── agents/                      # LiveKit Agent Service
│   ├── core/                    # Core agent logic
│   │   └── agent.py             # Main agent orchestrator
│   ├── providers/               # Pluggable AI providers
│   │   ├── base.py              # Abstract base classes
│   │   ├── stt/                 # Speech-to-Text providers
│   │   │   ├── openai_stt.py
│   │   │   ├── azure_stt.py
│   │   │   ├── aws_stt.py
│   │   │   └── google_stt.py
│   │   ├── llm/                 # LLM providers
│   │   │   ├── openai_llm.py
│   │   │   ├── azure_llm.py
│   │   │   └── anthropic_llm.py
│   │   └── tts/                 # Text-to-Speech providers
│   │       ├── openai_tts.py
│   │       ├── azure_tts.py
│   │       └── aws_tts.py
│   ├── hooks/                   # Lifecycle hooks
│   │   └── lifecycle.py         # Room/conversation hooks
│   ├── state/                   # State management
│   │   ├── manager.py           # State manager
│   │   ├── redis_state.py       # Redis backend
│   │   └── memory_state.py      # In-memory backend
│   └── config/
│       └── settings.py          # Configuration
│
├── backend/                     # FastAPI Backend Service
│   ├── api/                     # API endpoints
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   ├── auth.py
│   │       │   ├── conversations.py
│   │       │   ├── rooms.py
│   │       │   ├── users.py
│   │       │   └── files.py
│   │       └── router.py
│   ├── core/                    # Core functionality
│   │   ├── config.py
│   │   ├── security.py
│   │   └── logging.py
│   ├── services/                # Business logic
│   │   ├── conversation_service.py
│   │   ├── user_service.py
│   │   ├── room_service.py
│   │   └── livekit_service.py
│   ├── repositories/            # Data access
│   │   ├── conversation_repo.py
│   │   └── user_repo.py
│   ├── models/                  # Data models
│   │   ├── database/            # SQLAlchemy models
│   │   └── schemas/             # Pydantic schemas
│   └── middleware/              # HTTP middleware
│
├── k8s/                         # Kubernetes manifests
│   ├── livekit/
│   │   └── deployment.yaml
│   ├── agents/
│   │   └── deployment.yaml
│   └── api/
│       └── deployment.yaml
│
├── terraform/                   # Infrastructure as Code
│   └── main.tf                  # Azure resources
│
├── docker/                      # Dockerfiles
│   ├── Dockerfile.agent
│   └── Dockerfile.backend
│
├── config/
│   └── livekit.yaml             # LiveKit configuration
│
├── docker-compose.yml           # Local development
├── ARCHITECTURE.md              # System architecture
├── AZURE_DEPLOYMENT.md          # Azure deployment guide
└── README.md                    # This file
```

## AI Provider Configuration

### Using OpenAI (Default)

```env
STT_PROVIDER=openai
LLM_PROVIDER=openai
TTS_PROVIDER=openai
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-4
TTS_VOICE=alloy
```

### Using Azure Cognitive Services

```env
STT_PROVIDER=azure
LLM_PROVIDER=azure
TTS_PROVIDER=azure
AZURE_SPEECH_KEY=your-key
AZURE_SPEECH_REGION=eastus
AZURE_OPENAI_KEY=your-key
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
```

### Using AWS

```env
STT_PROVIDER=aws
TTS_PROVIDER=aws
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=us-east-1
```

### Using Multiple Providers

```env
# Mix and match providers
STT_PROVIDER=deepgram     # Best for real-time transcription
LLM_PROVIDER=anthropic    # Claude for conversations
TTS_PROVIDER=elevenlabs   # High-quality voice synthesis
```

## Lifecycle Events (LiveKit Native)

The system uses **LiveKit's native event system** for real-time event handling:

```python
# agents/core/agent.py - LiveKit Native Events

class VoiceAssistantAgent:
    def _setup_event_handlers(self):
        """Register LiveKit's native event handlers"""
        # Room events
        self.room.on("participant_connected", self._on_participant_connected)
        self.room.on("participant_disconnected", self._on_participant_disconnected)
        self.room.on("track_subscribed", self._on_track_subscribed)
        self.room.on("data_received", self._on_data_received)
        self.room.on("connection_quality_changed", self._on_connection_quality_changed)
    
    async def _on_participant_connected(self, participant):
        """LiveKit native event - participant joined"""
        # Update state, notify backend, load user context
        await self.backend_client.participant_connected(...)
        
    async def _on_track_subscribed(self, track, publication, participant):
        """LiveKit native event - new audio/video track"""
        # Start processing audio stream
        await self._process_audio_stream(track, participant)
        
    async def _on_data_received(self, data_packet):
        """LiveKit native event - file upload or command"""
        # Handle file uploads, process commands
        await self.backend_client.handle_file_upload(...)
```

**Available Events:**
- `participant_connected` / `participant_disconnected`
- `track_subscribed` / `track_unsubscribed`
- `data_received` (for files, commands)
- `connection_quality_changed`
- `room_metadata_changed`
- `active_speakers_changed`

See `agents/hooks/lifecycle.py` for complete documentation.

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login user
- `POST /api/v1/auth/refresh` - Refresh token

### Rooms
- `POST /api/v1/rooms` - Create room
- `GET /api/v1/rooms/{room_id}` - Get room details
- `POST /api/v1/rooms/{room_id}/token` - Get LiveKit access token

### Conversations
- `GET /api/v1/conversations` - List conversations
- `GET /api/v1/conversations/{id}` - Get conversation details
- `GET /api/v1/conversations/{id}/messages` - Get messages

### Files
- `POST /api/v1/files/upload` - Upload file
- `GET /api/v1/files/{id}` - Download file

See API documentation at `http://localhost:8000/api/docs`

## Production Deployment

### Azure Kubernetes Service

1. **Provision infrastructure**
```bash
cd terraform
terraform init
terraform plan
terraform apply
```

2. **Configure kubectl**
```bash
az aks get-credentials \
  --resource-group rg-voiceassistant-prod-eastus \
  --name aks-voiceassistant-prod
```

3. **Create secrets**
```bash
kubectl create secret generic livekit-secrets \
  --from-literal=api-key=your-key \
  --from-literal=api-secret=your-secret

kubectl create secret generic ai-provider-secrets \
  --from-literal=openai-api-key=sk-...
```

4. **Deploy services**
```bash
kubectl apply -f k8s/livekit/
kubectl apply -f k8s/agents/
kubectl apply -f k8s/api/
```

5. **Verify deployment**
```bash
kubectl get pods --all-namespaces
kubectl get services --all-namespaces
```

See [AZURE_DEPLOYMENT.md](./AZURE_DEPLOYMENT.md) for detailed deployment guide.

## Scaling

### Horizontal Pod Autoscaler

The system automatically scales based on load:

- **LiveKit Server**: 2-10 pods (CPU 70%)
- **Agents**: 4-20 pods (CPU 70%, Memory 75%)
- **API**: 2-10 pods (CPU 70%)

### Manual Scaling

```bash
# Scale agents
kubectl scale deployment livekit-agent -n agents --replicas=10

# Scale API
kubectl scale deployment fastapi-backend -n api --replicas=5
```

## Monitoring

### Prometheus Metrics

- Room count, participant count
- Request rate, error rate
- Response times
- Provider latency (STT/LLM/TTS)

### Application Insights

- Distributed tracing
- Custom events
- Performance monitoring

### Logs

```bash
# Agent logs
kubectl logs -f deployment/livekit-agent -n agents

# API logs
kubectl logs -f deployment/fastapi-backend -n api

# LiveKit logs
kubectl logs -f deployment/livekit-server -n livekit-system
```

## Testing

### Unit Tests

```bash
# Agent tests
cd agents
pytest tests/

# Backend tests
cd backend
pytest tests/
```

### Integration Tests

```bash
# Full stack integration
pytest tests/integration/
```

### Load Testing

```bash
# Simulate 1000 concurrent users
locust -f tests/load/locustfile.py --users 1000
```

## Cost Estimation

### Development (Local)
- **Cost**: Free (local Docker)

### Staging (Azure)
- **AKS**: ~$500/month
- **Database**: ~$200/month
- **Redis**: ~$150/month
- **Total**: ~$850/month

### Production (Azure)
- **AKS**: $3,000 - $8,000/month
- **Database**: $400 - $600/month
- **Redis**: $350/month
- **Storage**: $50 - $100/month
- **Monitoring**: $200 - $400/month
- **Total**: $4,000 - $10,000/month

See [AZURE_DEPLOYMENT.md](./AZURE_DEPLOYMENT.md) for detailed cost breakdown.

## Security

- **Authentication**: JWT tokens with refresh tokens
- **Authorization**: Role-based access control (RBAC)
- **Network**: Private subnets, NSGs, WAF
- **Secrets**: Azure Key Vault integration
- **Encryption**: TLS 1.2+, at-rest encryption
- **Compliance**: GDPR-ready, audit logging

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see LICENSE file

## Support

- **Documentation**: See [ARCHITECTURE.md](./ARCHITECTURE.md)
- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions

## Roadmap

- [ ] Multi-modal support (vision, documents)
- [ ] Real-time translation
- [ ] Advanced analytics dashboard
- [ ] A/B testing framework
- [ ] Custom wake words
- [ ] Sentiment analysis
- [ ] Multi-language support

---

Built with ❤️ using LiveKit, FastAPI, and Azure
