# Deployment Guide

## Docker Deployment (Phase 01 - Complete)

### Overview

Production-ready Docker image with multi-stage build, security hardening, and health checks. Image footprint: ~220MB.

### Build Configuration

**File:** `Dockerfile`

#### Multi-Stage Build Strategy

**Stage 1: Builder**
- Base: `python:3.11-slim`
- Installs build dependencies (gcc) for compiled packages
- Installs Python dependencies
- Layer optimized: requirements copied first for cache efficiency

**Stage 2: Runtime**
- Base: `python:3.11-slim`
- Copies only built packages from Stage 1
- Reduces final image size by ~100MB
- No build tools in final image (reduced attack surface)

#### Security Features

- **Non-root user:** `appuser` (UID 1000)
- **File permissions:** All app files owned by appuser
- **Minimal base image:** python:3.11-slim (no unnecessary tools)
- **No extra dependencies in runtime:** Build deps removed

#### Environment Variables

| Variable | Default | Description | Override Method |
|----------|---------|-------------|-----------------|
| `PORT` | `8000` | Server port | Docker -e flag or docker-compose |
| `WORKERS` | `1` | Uvicorn worker count | Docker -e flag or docker-compose |
| `PYTHONUNBUFFERED` | `1` | Direct stdout/stderr to logs | Set in Dockerfile |
| `PYTHONDONTWRITEBYTECODE` | `1` | No .pyc files | Set in Dockerfile |

#### Health Check

- **Command:** Python http.client (no extra dependencies)
- **Interval:** 30 seconds
- **Timeout:** 10 seconds
- **Start grace period:** 5 seconds
- **Failure threshold:** 3 retries
- **Endpoint:** GET `/health`

### Building & Running

#### Build Image

```bash
# Build with default tag
docker build -t paypal-api:latest .

# Build with version tag
docker build -t paypal-api:1.0.0 .
```

#### Run Container

```bash
# Basic run (development)
docker run -d \
  --name paypal-api \
  -p 8000:8000 \
  -e PAYPAL_CLIENT_ID=your_client_id \
  -e PAYPAL_CLIENT_SECRET=your_client_secret \
  -e PAYPAL_MODE=sandbox \
  paypal-api:latest

# Production with custom workers & port
docker run -d \
  --name paypal-api-prod \
  -p 80:8080 \
  --restart unless-stopped \
  -e PORT=8080 \
  -e WORKERS=4 \
  -e PAYPAL_CLIENT_ID=your_client_id \
  -e PAYPAL_CLIENT_SECRET=your_client_secret \
  -e PAYPAL_MODE=live \
  paypal-api:latest

# With env file
docker run -d \
  --name paypal-api \
  -p 8000:8000 \
  --env-file .env.docker \
  paypal-api:latest
```

#### Docker Compose

```yaml
version: '3.9'

services:
  paypal-api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: paypal-api
    ports:
      - "8000:8000"
    environment:
      PORT: 8000
      WORKERS: 1
      PAYPAL_CLIENT_ID: ${PAYPAL_CLIENT_ID}
      PAYPAL_CLIENT_SECRET: ${PAYPAL_CLIENT_SECRET}
      PAYPAL_MODE: sandbox
    env_file:
      - .env
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import http.client; c=http.client.HTTPConnection('localhost:8000', timeout=5); c.request('GET', '/health'); r=c.getresponse(); exit(0 if r.status==200 else 1)"]
      interval: 30s
      timeout: 10s
      start_period: 5s
      retries: 3
```

**Start with compose:**
```bash
docker-compose up -d
```

### Image Specifications

| Aspect | Details |
|--------|---------|
| **Base Image** | python:3.11-slim |
| **Final Size** | ~220MB |
| **Exposed Port** | 8000 (configurable via PORT env var) |
| **Runtime User** | appuser (UID 1000, non-root) |
| **Python Version** | 3.11 |
| **Included** | FastAPI, uvicorn, requests, other dependencies from requirements.txt |
| **Excluded** | Build tools (gcc), development files, tests, documentation |

### Environment Setup

#### .env.docker File

```env
PAYPAL_CLIENT_ID=your_actual_client_id
PAYPAL_CLIENT_SECRET=your_actual_client_secret
PAYPAL_MODE=sandbox
PORT=8000
WORKERS=1
RATE_LIMIT_PER_MINUTE=60
```

#### Secrets Management (Production)

For production deployments, use Docker secrets or orchestration platform secrets:

**Docker Swarm:**
```bash
echo "your_secret" | docker secret create paypal_client_id -
docker service create \
  --secret paypal_client_id \
  -e PAYPAL_CLIENT_ID_FILE=/run/secrets/paypal_client_id \
  paypal-api:latest
```

**Kubernetes:**
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: paypal-credentials
type: Opaque
stringData:
  client-id: your_client_id
  client-secret: your_client_secret
---
apiVersion: v1
kind: Pod
metadata:
  name: paypal-api
spec:
  containers:
  - name: paypal-api
    image: paypal-api:latest
    env:
    - name: PAYPAL_CLIENT_ID
      valueFrom:
        secretKeyRef:
          name: paypal-credentials
          key: client-id
```

### Logs & Monitoring

#### View Container Logs

```bash
# Real-time logs
docker logs -f paypal-api

# Last 100 lines
docker logs --tail 100 paypal-api

# Logs with timestamps
docker logs --timestamps paypal-api
```

#### Health Status

```bash
# Check container health
docker ps | grep paypal-api

# Detailed health info
docker inspect --format='{{.State.Health}}' paypal-api
```

### Performance Tuning

#### Worker Configuration

Default: 1 worker (suitable for development and light load)

**Calculate optimal workers:**
- Formula: (CPU cores × 2) + 1
- Example: 4-core server → 9 workers
- Min: 1 (single core/development)
- Max: 32 (diminishing returns on most servers)

```bash
docker run -e WORKERS=4 paypal-api:latest
```

#### Port Customization

Default: 8000 (remapped as needed)

```bash
# Run on port 9000
docker run -p 9000:8000 -e PORT=8000 paypal-api:latest

# Run on port 80 (requires root or privileged mode)
docker run -p 80:8000 paypal-api:latest
```

### Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Container exits immediately | Missing env vars | Add PAYPAL_CLIENT_ID & SECRET |
| Health check failing | Port mismatch | Ensure PORT env var matches EXPOSE & mapped port |
| Slow startup | First build | Subsequent runs use cached layers |
| High memory usage | Too many workers | Reduce WORKERS env var |
| Connection refused | Port not exposed | Check docker run -p mapping |

### Next Phases

- **Phase 02:** Kubernetes manifests (Deployment, Service, HPA)
- **Phase 03:** Container registry integration (Docker Hub/ECR/GCR)
- **Phase 04:** CI/CD pipeline with automated builds & pushes
- **Phase 05:** Multi-environment configs (dev/staging/prod)

