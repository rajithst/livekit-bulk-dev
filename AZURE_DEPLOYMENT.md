# Azure Deployment Architecture for Voice Assistant

## Overview

This document describes the Azure infrastructure for deploying the Voice Assistant system with self-hosted LiveKit server.

## Architecture Diagram

```
                                    ┌─────────────────────────────┐
                                    │   Azure Traffic Manager     │
                                    │   (Global Load Balancing)   │
                                    └──────────────┬──────────────┘
                                                   │
                        ┌──────────────────────────┼──────────────────────────┐
                        │                          │                          │
                   ┌────▼─────┐             ┌────▼─────┐             ┌─────▼────┐
                   │  Region  │             │  Region  │             │  Region  │
                   │  East US │             │ West EU  │             │ Asia SE  │
                   └────┬─────┘             └──────────┘             └──────────┘
                        │
           ┌────────────┴────────────┐
           │                         │
    ┌──────▼──────┐          ┌──────▼──────┐
    │ Application │          │   Traffic   │
    │   Gateway   │          │   Manager   │
    │   + WAF     │          │             │
    └──────┬──────┘          └─────────────┘
           │
    ┌──────▼──────────────────────────────────────┐
    │                                              │
    │     Azure Kubernetes Service (AKS)          │
    │                                              │
    │  ┌────────────────────────────────────┐     │
    │  │   Ingress Controller (NGINX)       │     │
    │  └────────┬────────────────────────┬──┘     │
    │           │                        │         │
    │  ┌────────▼────────┐    ┌─────────▼──────┐  │
    │  │  LiveKit Server  │    │  API Services  │  │
    │  │   (Node Pool)    │    │  (Node Pool)   │  │
    │  │  - 2-10 nodes    │    │  - 2-10 nodes  │  │
    │  │  - Auto-scale    │    │  - Auto-scale  │  │
    │  └─────────────────┘    └────────────────┘  │
    │                                              │
    │  ┌─────────────────────────────────────┐    │
    │  │     Agent Services (Node Pool)      │    │
    │  │     - 4-20 nodes, Auto-scale        │    │
    │  └─────────────────────────────────────┘    │
    │                                              │
    └──────────────────────────────────────────────┘
                        │
       ┌────────────────┼────────────────┐
       │                │                │
  ┌────▼────┐    ┌─────▼──────┐   ┌────▼─────┐
  │PostgreSQL│    │   Redis    │   │   Blob   │
  │ Flexible │    │  Premium   │   │ Storage  │
  │  Server  │    │  Cluster   │   │   GRS    │
  └──────────┘    └────────────┘   └──────────┘
       │
  ┌────▼─────────────────────────┐
  │     Monitoring & Logging     │
  │  - Azure Monitor             │
  │  - Application Insights      │
  │  - Log Analytics             │
  │  - Container Insights        │
  └──────────────────────────────┘
```

## Resource Groups

### Production Environment

**Resource Group:** `rg-voiceassistant-prod-eastus`

**Location:** East US (Primary)

## Core Services

### 1. Azure Kubernetes Service (AKS)

**Configuration:**
- **Cluster Name:** `aks-voiceassistant-prod`
- **Kubernetes Version:** 1.28+
- **Network Plugin:** Azure CNI
- **Network Policy:** Azure Network Policy
- **DNS:** Azure DNS
- **Authentication:** Azure AD Integration

**Node Pools:**

1. **System Pool** (system)
   - VM Size: Standard_D4s_v3
   - Min nodes: 2
   - Max nodes: 4
   - OS Disk: 128 GB

2. **LiveKit Pool** (livekit)
   - VM Size: Standard_D8s_v3 (8 vCPU, 32 GB RAM)
   - Min nodes: 2
   - Max nodes: 10
   - Auto-scale: Enabled
   - Taints: livekit=true:NoSchedule

3. **Agent Pool** (agents)
   - VM Size: Standard_D4s_v3 (4 vCPU, 16 GB RAM)
   - Min nodes: 4
   - Max nodes: 20
   - Auto-scale: Enabled
   - Taints: agents=true:NoSchedule

4. **API Pool** (api)
   - VM Size: Standard_D4s_v3
   - Min nodes: 2
   - Max nodes: 10
   - Auto-scale: Enabled

**Auto-scaling Configuration:**
```yaml
# Cluster Autoscaler
--scale-down-delay-after-add: 10m
--scale-down-unneeded-time: 10m
--scale-down-utilization-threshold: 0.5
```

### 2. Azure Database for PostgreSQL

**Configuration:**
- **Service:** Azure Database for PostgreSQL Flexible Server
- **Name:** `psql-voiceassistant-prod`
- **Version:** PostgreSQL 15
- **SKU:** General Purpose, 4 vCores, 16 GB RAM
- **Storage:** 256 GB, Auto-grow enabled
- **Backup:** 7 days retention, Geo-redundant
- **High Availability:** Zone-redundant

**Read Replicas:**
- 2 read replicas for scaling reads
- Located in same region

**Security:**
- Private endpoint (VNet integration)
- SSL/TLS enforced
- Azure AD authentication

### 3. Azure Cache for Redis

**Configuration:**
- **Service:** Azure Cache for Redis
- **Name:** `redis-voiceassistant-prod`
- **Tier:** Premium
- **Capacity:** P2 (6 GB)
- **Clustering:** Enabled (3 shards)
- **Redis Version:** 6.x
- **Persistence:** RDB enabled
- **Replication:** Zone-redundant

**Use Cases:**
- Session state
- Conversation context
- Rate limiting
- Caching

### 4. Azure Blob Storage

**Configuration:**
- **Account Name:** `stvoiceassistantprod`
- **Account Type:** StorageV2 (General Purpose v2)
- **Replication:** GRS (Geo-Redundant Storage)
- **Performance:** Standard
- **Access Tier:** Hot

**Containers:**
1. `conversations` - Conversation recordings
2. `uploads` - User file uploads
3. `recordings` - Full session recordings
4. `backups` - Database backups

**Lifecycle Management:**
- Move to Cool tier after 30 days
- Move to Archive tier after 90 days
- Delete after 365 days (configurable)

**Security:**
- Private endpoint
- RBAC for access control
- Encryption at rest (Microsoft-managed keys)
- Encryption in transit (TLS 1.2+)

### 5. Azure Virtual Network

**Configuration:**
- **VNet Name:** `vnet-voiceassistant-prod`
- **Address Space:** 10.0.0.0/16

**Subnets:**
```
aks-subnet:        10.0.0.0/20    (4096 IPs)
db-subnet:         10.1.0.0/24    (256 IPs)
cache-subnet:      10.2.0.0/24    (256 IPs)
gateway-subnet:    10.3.0.0/27    (32 IPs)
```

**Network Security Groups:**
- Restrict traffic between subnets
- Allow only necessary ports
- Block all inbound by default

### 6. Azure Application Gateway

**Configuration:**
- **Name:** `appgw-voiceassistant-prod`
- **SKU:** WAF_v2
- **Capacity:** Auto-scale (2-10 instances)
- **Public IP:** Static

**Features:**
- Web Application Firewall (WAF)
- SSL/TLS termination
- HTTP/2 support
- URL-based routing
- Health probes

**WAF Rules:**
- OWASP Core Rule Set 3.2
- Custom rules for DDoS protection
- Rate limiting at gateway level

### 7. Azure Load Balancer

**Configuration:**
- **Name:** `lb-livekit-prod`
- **SKU:** Standard
- **Type:** Public
- **Public IP:** Static

**Purpose:**
- Load balance LiveKit WebRTC traffic
- Support UDP/TCP for TURN/STUN

### 8. Azure Monitor & Application Insights

**Application Insights:**
- **Name:** `appi-voiceassistant-prod`
- Distributed tracing
- Request tracking
- Dependency tracking
- Custom metrics

**Log Analytics Workspace:**
- **Name:** `log-voiceassistant-prod`
- 30 days retention (default)
- 90 days retention for audit logs

**Container Insights:**
- Monitor AKS cluster health
- Node and pod metrics
- Container logs

**Alert Rules:**
1. High error rate (>5%)
2. High latency (p95 > 2s)
3. Pod restarts (>3 in 5 min)
4. Node CPU/Memory (>80%)
5. Database connections (>80%)
6. LiveKit room errors

### 9. Azure Key Vault

**Configuration:**
- **Name:** `kv-voiceassistant-prod`
- **SKU:** Standard
- **Soft Delete:** Enabled
- **Purge Protection:** Enabled

**Secrets:**
- Database credentials
- Redis connection strings
- API keys (OpenAI, Azure AI, etc.)
- LiveKit API key/secret
- JWT signing keys
- Azure Storage connection strings

**Access:**
- Managed Identity for AKS
- RBAC for developers (read-only)

### 10. Azure Container Registry

**Configuration:**
- **Name:** `acrvoiceassistantprod`
- **SKU:** Premium
- **Geo-replication:** Enabled (replicate to West EU)

**Images:**
- livekit-agent:latest
- fastapi-backend:latest
- Web client images

## Networking Architecture

### Public-facing Components

```
Internet → Application Gateway (WAF) → AKS Ingress → Services
        → Load Balancer → LiveKit Server (WebRTC)
```

### Private Components

- PostgreSQL (private endpoint)
- Redis (private endpoint)
- Blob Storage (private endpoint)
- Internal service-to-service communication

### DNS Configuration

**Azure DNS Zone:** `voiceassistant.example.com`

Records:
- `api.voiceassistant.example.com` → Application Gateway
- `livekit.voiceassistant.example.com` → Load Balancer
- `*.voiceassistant.example.com` → Application Gateway

### SSL/TLS Certificates

- Azure-managed certificates for *.voiceassistant.example.com
- Auto-renewal enabled
- Stored in Key Vault

## Security Architecture

### Identity & Access Management

1. **Azure AD Integration:**
   - User authentication via Azure AD
   - Service Principal for CI/CD
   - Managed Identities for services

2. **RBAC:**
   - Least privilege access
   - Separate roles for dev/ops/admin

3. **Network Security:**
   - NSGs on all subnets
   - Private endpoints for PaaS services
   - No public IPs on backend services

### Data Protection

1. **Encryption at Rest:**
   - PostgreSQL: Azure-managed keys
   - Redis: Enabled
   - Blob Storage: Enabled
   - AKS: Enabled for etcd

2. **Encryption in Transit:**
   - TLS 1.2+ for all connections
   - mTLS between services (optional)

3. **Secrets Management:**
   - Azure Key Vault for all secrets
   - Kubernetes secrets synced from Key Vault
   - No secrets in code or config files

### Compliance

- Data residency (regional deployment)
- GDPR compliance features
- Audit logging enabled
- Data retention policies

## Disaster Recovery

### Backup Strategy

1. **PostgreSQL:**
   - Automated daily backups (7 days)
   - Point-in-time restore (up to 35 days)
   - Geo-redundant backup storage

2. **Redis:**
   - RDB persistence enabled
   - Daily snapshots
   - Zone-redundant

3. **Blob Storage:**
   - GRS (Geo-Redundant Storage)
   - Soft delete (14 days)

4. **AKS Configuration:**
   - GitOps (ArgoCD)
   - All configs in Git
   - Helm charts versioned

### High Availability

**RTO:** < 1 hour  
**RPO:** < 5 minutes

**Strategy:**
- Multi-zone deployment
- Auto-healing for pods
- Database replicas
- Redis cluster mode
- Geo-replication for storage

### Failover Procedure

1. **Region Failure:**
   - Traffic Manager routes to secondary region
   - Manual database failover (if needed)
   - Restore from geo-redundant backups

2. **Service Failure:**
   - Kubernetes auto-restart
   - Health checks and probes
   - Circuit breakers in application

## Cost Optimization

### Reserved Instances

- 1-year or 3-year reservations for baseline capacity
- Savings: 30-50%

### Auto-scaling

- Scale down during off-peak hours
- Scale up based on demand
- Spot instances for non-critical workloads

### Storage Optimization

- Lifecycle policies for Blob Storage
- Archive old data
- Delete after retention period

### Monitoring

- Cost alerts (budget exceeded)
- Resource utilization reports
- Rightsize recommendations

### Estimated Monthly Cost (USD)

**Production Environment:**

| Service | Configuration | Monthly Cost |
|---------|--------------|--------------|
| AKS Cluster | 3-4 node pools, 8-44 nodes | $3,000 - $8,000 |
| PostgreSQL | General Purpose, 4 vCores + replicas | $400 - $600 |
| Redis Premium | P2 (6 GB) | $350 |
| Blob Storage | 1 TB, GRS | $50 - $100 |
| Application Gateway | WAF v2, 2-10 instances | $300 - $500 |
| Load Balancer | Standard | $20 - $50 |
| Azure Monitor | Standard tier | $200 - $400 |
| Bandwidth | Outbound data transfer | $100 - $500 |
| **Total** | | **$4,420 - $10,150** |

*Note: Costs vary based on actual usage, region, and scaling*

## Deployment Process

See `DEPLOYMENT.md` for detailed deployment instructions.

## Monitoring & Alerts

See `MONITORING.md` for monitoring setup and alert configurations.

## Scaling Strategy

See `SCALING.md` for auto-scaling configurations and capacity planning.
