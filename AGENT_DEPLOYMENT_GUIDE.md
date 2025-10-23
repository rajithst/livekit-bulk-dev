# Deploying LiveKit Agents - Complete Guide

## TL;DR - Deployment Methods

```bash
# Method 1: Direct Python (Development)
python agents/core/agent.py

# Method 2: Docker (Production)
docker build -f docker/Dockerfile.agent -t my-agent .
docker run my-agent

# Method 3: Kubernetes (Scale)
kubectl apply -f k8s/agents/deployment.yaml

# Method 4: Systemd (Linux Server)
systemctl start livekit-agent
```

**No web framework needed!** The agent is a standalone process.

## Understanding the Architecture

### What cli.run_app() Does

```python
if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
        )
    )
```

This:
1. ✅ Connects to LiveKit Server via WebSocket
2. ✅ Registers as an available agent worker
3. ✅ Waits for room assignments
4. ✅ Spawns processes for each room
5. ✅ Handles lifecycle and health checks

### Network Flow

```
Internet/Users
    ↓
┌────────────────┐
│ LiveKit Server │ (Port 7880 WebSocket, 443/80 HTTPS)
│  (Central Hub) │
└────┬───────────┘
     │
     │ WebSocket Connection
     │ ws://livekit-server:7880
     │
┌────▼───────────┐
│  Agent Worker  │ (Your Python process)
│  (Background)  │ NO HTTP SERVER!
│                │ Just connects to LiveKit
└────────────────┘

Agents connect TO LiveKit (outbound)
LiveKit doesn't connect to agents (no inbound ports needed)
```

## Deployment Options

### 1. Development - Direct Python

```bash
# Set environment variables
export LIVEKIT_URL=ws://localhost:7880
export LIVEKIT_API_KEY=your_api_key
export LIVEKIT_API_SECRET=your_api_secret
export OPENAI_API_KEY=sk-...

# Run the agent
cd agents
python core/agent.py

# You'll see:
# INFO: Agent worker started
# INFO: Connected to LiveKit server
# INFO: Waiting for room assignments...
```

**When to use**: Local development, testing

### 2. Production - Docker Container

#### Create Dockerfile (`docker/Dockerfile.agent`)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY agents/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent code
COPY agents/ ./agents/
COPY backend/ ./backend/

# Run the agent
CMD ["python", "agents/core/agent.py"]
```

#### Build and Run

```bash
# Build
docker build -f docker/Dockerfile.agent -t livekit-agent:latest .

# Run
docker run -d \
  --name livekit-agent \
  --restart unless-stopped \
  -e LIVEKIT_URL=ws://livekit-server:7880 \
  -e LIVEKIT_API_KEY=your_api_key \
  -e LIVEKIT_API_SECRET=your_api_secret \
  -e OPENAI_API_KEY=sk-... \
  -e REDIS_URL=redis://redis:6379 \
  livekit-agent:latest

# Check logs
docker logs -f livekit-agent
```

#### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  livekit:
    image: livekit/livekit-server:latest
    ports:
      - "7880:7880"
      - "7881:7881"
    # ... livekit config ...

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  agent:
    build:
      context: .
      dockerfile: docker/Dockerfile.agent
    depends_on:
      - livekit
      - redis
    environment:
      - LIVEKIT_URL=ws://livekit:7880
      - LIVEKIT_API_KEY=${LIVEKIT_API_KEY}
      - LIVEKIT_API_SECRET=${LIVEKIT_API_SECRET}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - REDIS_URL=redis://redis:6379
    restart: unless-stopped
    # Scale agents
    deploy:
      replicas: 3  # Run 3 agent workers
```

```bash
# Deploy
docker-compose up -d

# Scale up/down
docker-compose up -d --scale agent=5  # 5 workers
```

**When to use**: Production single server, quick setup

### 3. Kubernetes - Full Scale

#### Deployment (`k8s/agents/deployment.yaml`)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: livekit-agent
  labels:
    app: livekit-agent
spec:
  replicas: 3  # Start with 3 workers
  selector:
    matchLabels:
      app: livekit-agent
  template:
    metadata:
      labels:
        app: livekit-agent
    spec:
      containers:
      - name: agent
        image: your-registry/livekit-agent:latest
        env:
        - name: LIVEKIT_URL
          value: "ws://livekit-server:7880"
        - name: LIVEKIT_API_KEY
          valueFrom:
            secretKeyRef:
              name: livekit-secrets
              key: api-key
        - name: LIVEKIT_API_SECRET
          valueFrom:
            secretKeyRef:
              name: livekit-secrets
              key: api-secret
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: ai-secrets
              key: openai-key
        - name: REDIS_URL
          value: "redis://redis:6379"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          exec:
            command:
            - python
            - -c
            - "import sys; sys.exit(0)"
          initialDelaySeconds: 30
          periodSeconds: 10
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: livekit-agent-hpa
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
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

```bash
# Create secrets
kubectl create secret generic livekit-secrets \
  --from-literal=api-key=your_api_key \
  --from-literal=api-secret=your_api_secret

kubectl create secret generic ai-secrets \
  --from-literal=openai-key=sk-...

# Deploy
kubectl apply -f k8s/agents/deployment.yaml

# Watch
kubectl get pods -l app=livekit-agent -w

# Scale manually
kubectl scale deployment livekit-agent --replicas=10

# Logs
kubectl logs -f deployment/livekit-agent
```

**When to use**: Production at scale, auto-scaling needed

### 4. Systemd Service (Linux Server)

#### Create Service File (`/etc/systemd/system/livekit-agent.service`)

```ini
[Unit]
Description=LiveKit Agent Worker
After=network.target

[Service]
Type=simple
User=livekit
WorkingDirectory=/opt/livekit-agent
Environment="LIVEKIT_URL=ws://localhost:7880"
Environment="LIVEKIT_API_KEY=your_api_key"
Environment="LIVEKIT_API_SECRET=your_api_secret"
Environment="OPENAI_API_KEY=sk-..."
Environment="REDIS_URL=redis://localhost:6379"
ExecStart=/usr/bin/python3 agents/core/agent.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable livekit-agent
sudo systemctl start livekit-agent

# Check status
sudo systemctl status livekit-agent

# Logs
sudo journalctl -u livekit-agent -f
```

**When to use**: VPS, dedicated server, traditional hosting

### 5. Process Manager (PM2 - Node.js ecosystem)

```bash
# Install PM2
npm install -g pm2

# Create ecosystem file
cat > ecosystem.config.js << EOF
module.exports = {
  apps: [{
    name: 'livekit-agent',
    script: 'python',
    args: 'agents/core/agent.py',
    instances: 3,  // 3 worker processes
    exec_mode: 'fork',
    autorestart: true,
    watch: false,
    max_memory_restart: '1G',
    env: {
      LIVEKIT_URL: 'ws://localhost:7880',
      LIVEKIT_API_KEY: 'your_api_key',
      LIVEKIT_API_SECRET: 'your_api_secret',
      OPENAI_API_KEY: 'sk-...'
    }
  }]
};
EOF

# Start
pm2 start ecosystem.config.js

# Monitor
pm2 monit

# Logs
pm2 logs livekit-agent

# Auto-start on boot
pm2 startup
pm2 save
```

**When to use**: Familiar with PM2, quick deployment

## Environment Configuration

### Required Environment Variables

```bash
# LiveKit Connection
LIVEKIT_URL=ws://your-livekit-server:7880
LIVEKIT_API_KEY=your_api_key
LIVEKIT_API_SECRET=your_api_secret

# AI Providers
OPENAI_API_KEY=sk-...
AZURE_OPENAI_KEY=...
AZURE_OPENAI_ENDPOINT=https://....openai.azure.com/

# Backend
BACKEND_URL=http://backend:8000
REDIS_URL=redis://redis:6379

# Optional
LOG_LEVEL=INFO
METRICS_PORT=9090  # Prometheus metrics
```

### Using .env File

```bash
# agents/.env
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret
OPENAI_API_KEY=sk-...

# Load and run
export $(cat .env | xargs)
python agents/core/agent.py
```

## Monitoring & Health Checks

### Add Health Check Endpoint (Optional)

```python
# agents/core/agent.py
from aiohttp import web

async def health_check(request):
    """Simple health check for monitoring."""
    return web.Response(text="OK", status=200)

async def start_health_server():
    """Start health check HTTP server."""
    app = web.Application()
    app.router.add_get('/health', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()

# In entrypoint or main:
asyncio.create_task(start_health_server())
```

### Kubernetes Probes

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 5
```

### Prometheus Metrics

```python
# Already included via OpenTelemetry!
# Metrics exposed on port configured in PrometheusMetricReader
# Default: http://localhost:9090/metrics

# Add to prometheus.yml:
scrape_configs:
  - job_name: 'livekit-agents'
    static_configs:
      - targets: ['agent-1:9090', 'agent-2:9090']
```

## Scaling Strategies

### Vertical Scaling (Single Instance)

```yaml
# Give more resources to one agent
resources:
  limits:
    memory: "4Gi"
    cpu: "2000m"
```

**Handles**: ~50-100 concurrent rooms

### Horizontal Scaling (Multiple Instances)

```yaml
# Run multiple agent workers
replicas: 10
```

**Handles**: ~500-1000 concurrent rooms (10 workers × ~50-100 rooms each)

### Auto-Scaling

```yaml
# Kubernetes HPA
minReplicas: 3
maxReplicas: 50
targetCPUUtilizationPercentage: 70
```

**Handles**: Scales automatically based on load

## Deployment Checklist

### Pre-Deployment
- [ ] Test agent locally
- [ ] Configure environment variables
- [ ] Set up Redis (if using)
- [ ] Set up backend API (if using)
- [ ] Configure AI provider keys
- [ ] Build Docker image (if using containers)

### Deployment
- [ ] Deploy LiveKit Server first
- [ ] Deploy Redis/database
- [ ] Deploy backend API
- [ ] Deploy agent workers
- [ ] Configure load balancing (if needed)

### Post-Deployment
- [ ] Verify agent connection to LiveKit
- [ ] Check logs for errors
- [ ] Test room creation and agent assignment
- [ ] Monitor metrics (CPU, memory, latency)
- [ ] Set up alerts
- [ ] Configure auto-scaling

## Common Issues & Solutions

### Issue: Agent won't connect to LiveKit

```bash
# Check connectivity
telnet livekit-server 7880

# Check credentials
echo $LIVEKIT_API_KEY
echo $LIVEKIT_API_SECRET

# Check logs
docker logs livekit-agent
```

### Issue: High memory usage

```python
# Trim conversation history
if len(self.conversation_history) > 50:
    self.conversation_history = self.conversation_history[-20:]

# Use Redis instead of in-memory
```

### Issue: Agent process crashes

```yaml
# Add restart policy
restart: unless-stopped  # Docker
restartPolicy: Always    # Kubernetes
Restart=always          # Systemd
```

## Production Best Practices

1. **Use Docker/K8s** - Consistent deployment
2. **Enable Redis** - Scalable state management
3. **Set Resource Limits** - Prevent OOM kills
4. **Monitor Metrics** - Prometheus + Grafana
5. **Log Aggregation** - ELK/Loki stack
6. **Auto-Scaling** - Handle traffic spikes
7. **Health Checks** - Detect failures early
8. **Secrets Management** - Use K8s secrets or Vault
9. **CI/CD Pipeline** - Automated deployments
10. **Backup Strategy** - Database backups

## Example: Complete AWS Deployment

```bash
# 1. Build and push image
docker build -f docker/Dockerfile.agent -t my-agent:v1 .
docker tag my-agent:v1 123456789.dkr.ecr.us-east-1.amazonaws.com/my-agent:v1
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/my-agent:v1

# 2. Deploy to ECS
aws ecs create-service \
  --cluster livekit-cluster \
  --service-name agent-service \
  --task-definition agent-task:1 \
  --desired-count 5 \
  --launch-type FARGATE

# 3. Configure auto-scaling
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --scalable-dimension ecs:service:DesiredCount \
  --resource-id service/livekit-cluster/agent-service \
  --min-capacity 3 \
  --max-capacity 20
```

## Summary

**Key Points**:
- ✅ **No web framework needed** - agents are standalone processes
- ✅ **Agents connect TO LiveKit** - outbound WebSocket connection
- ✅ **Multiple deployment options** - Docker, K8s, Systemd, PM2
- ✅ **Scales horizontally** - add more worker instances
- ✅ **Production-ready** - health checks, metrics, auto-scaling

**Simplest Deployment**:
```bash
python agents/core/agent.py  # That's it!
```

**Production Deployment**:
```bash
docker-compose up -d --scale agent=5  # 5 workers
```

The agent is designed to be simple to deploy while being production-ready! 🚀
