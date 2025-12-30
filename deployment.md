# Deployment Guide

Quick reference for deploying the PayPal API Service.

> **📖 Full Documentation:** See [docs/deployment-guide.md](./docs/deployment-guide.md) for comprehensive deployment instructions, troubleshooting, and production best practices.

---

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+ (optional)
- PayPal API credentials (Client ID & Secret)

---

## Quick Start

### Option 1: Docker (Recommended)

```bash
# Build image
docker build -t paypal-api:latest .

# Run container
docker run -d \
  --name paypal-api \
  -p 8000:8000 \
  -e PAYPAL_CLIENT_ID=your_client_id \
  -e PAYPAL_CLIENT_SECRET=your_client_secret \
  -e PAYPAL_MODE=sandbox \
  paypal-api:latest

# Check health
curl http://localhost:8000/health

# View logs
docker logs -f paypal-api
```

### Option 2: Docker Compose

```bash
# Create .env file
cp .env.example .env
# Edit .env with your credentials

# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Option 3: Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Run server
uvicorn app.main:app --reload --port 8000
```

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PAYPAL_CLIENT_ID` | ✅ Yes | - | PayPal OAuth2 client ID |
| `PAYPAL_CLIENT_SECRET` | ✅ Yes | - | PayPal OAuth2 client secret |
| `PAYPAL_MODE` | No | `sandbox` | Environment: `sandbox` or `live` |
| `PORT` | No | `8000` | Server port (Docker only) |
| `WORKERS` | No | `1` | Uvicorn worker count (Docker only) |
| `RATE_LIMIT_PER_MINUTE` | No | `60` | Rate limit per IP address |

---

## Production Deployment

### Recommended Configuration

```bash
docker run -d \
  --name paypal-api-prod \
  --restart unless-stopped \
  -p 80:8000 \
  -e PORT=8000 \
  -e WORKERS=4 \
  -e PAYPAL_CLIENT_ID=${PAYPAL_CLIENT_ID} \
  -e PAYPAL_CLIENT_SECRET=${PAYPAL_CLIENT_SECRET} \
  -e PAYPAL_MODE=live \
  paypal-api:latest
```

### Worker Calculation

**Formula:** `WORKERS = (CPU_CORES × 2) + 1`

Examples:
- 1 CPU core → 3 workers
- 2 CPU cores → 5 workers
- 4 CPU cores → 9 workers

---

## Docker Hub Deployment

### 1. Build & Tag

```bash
# Build image
docker build -t paypal-api:latest .

# Tag for Docker Hub
docker tag paypal-api:latest yourusername/paypal-api:latest
docker tag paypal-api:latest yourusername/paypal-api:1.0.0
```

### 2. Push to Docker Hub

```bash
# Login
docker login

# Push images
docker push yourusername/paypal-api:latest
docker push yourusername/paypal-api:1.0.0
```

### 3. Pull & Run from Docker Hub

```bash
# Pull image
docker pull yourusername/paypal-api:latest

# Run container
docker run -d \
  --name paypal-api \
  -p 8000:8000 \
  --env-file .env \
  yourusername/paypal-api:latest
```

---

## Health Checks

### Container Health

```bash
# Check container status
docker ps | grep paypal-api

# View health status
docker inspect --format='{{.State.Health.Status}}' paypal-api

# Manual health check
curl http://localhost:8000/health
```

**Expected Response:**
```json
{
  "status": "ok"
}
```

---

## Monitoring

### View Logs

```bash
# Real-time logs
docker logs -f paypal-api

# Last 100 lines
docker logs --tail 100 paypal-api

# With timestamps
docker logs --timestamps paypal-api
```

### Access API Documentation

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

---

## Troubleshooting

### Container Won't Start

```bash
# Check logs for errors
docker logs paypal-api

# Common issues:
# - Missing PAYPAL_CLIENT_ID or PAYPAL_CLIENT_SECRET
# - Port 8000 already in use (change with -p 9000:8000)
# - Invalid PayPal credentials
```

### Health Check Failing

```bash
# Verify container is running
docker ps -a | grep paypal-api

# Check if app is listening
docker exec paypal-api netstat -tlnp | grep 8000

# Test health endpoint from inside container
docker exec paypal-api curl http://localhost:8000/health
```

### Can't Access API

```bash
# Verify port mapping
docker port paypal-api

# Check firewall rules
sudo ufw status

# Test from host
curl http://localhost:8000/health
```

---

## Scaling

### Horizontal Scaling (Multiple Containers)

```bash
# Container 1
docker run -d --name paypal-api-1 -p 8001:8000 -e WORKERS=2 paypal-api:latest

# Container 2
docker run -d --name paypal-api-2 -p 8002:8000 -e WORKERS=2 paypal-api:latest

# Container 3
docker run -d --name paypal-api-3 -p 8003:8000 -e WORKERS=2 paypal-api:latest

# Configure load balancer (nginx, HAProxy, etc.)
```

### Vertical Scaling (Increase Workers)

```bash
# Single container with more workers
docker run -d \
  --name paypal-api \
  -p 8000:8000 \
  -e WORKERS=8 \
  paypal-api:latest
```

---

## Security Best Practices

### 🔒 Production Checklist

- ✅ Use `PAYPAL_MODE=live` for production
- ✅ Store secrets in environment variables (never in code)
- ✅ Use Docker secrets or Kubernetes secrets in orchestration
- ✅ Run behind HTTPS/TLS termination (load balancer)
- ✅ Enable firewall rules (allow only necessary ports)
- ✅ Set `--restart unless-stopped` for automatic recovery
- ✅ Monitor container health checks
- ✅ Implement log aggregation (ELK, CloudWatch, etc.)
- ✅ Regular security updates (rebuild images monthly)

### 🚫 Never Do

- ❌ Hardcode credentials in Dockerfile
- ❌ Commit .env files to git
- ❌ Run containers as root (already handled: appuser)
- ❌ Expose container port directly to internet (use reverse proxy)
- ❌ Use default/weak credentials
- ❌ Skip health checks
- ❌ Run without restart policy

---

## Docker Image Details

| Aspect | Details |
|--------|---------|
| **Base Image** | python:3.11-slim |
| **Final Size** | ~220MB |
| **User** | appuser (UID 1000, non-root) |
| **Exposed Port** | 8000 (configurable) |
| **Health Check** | GET /health (30s interval) |
| **Startup Time** | ~2 seconds |
| **Build Type** | Multi-stage (builder + runtime) |

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Build and Push to Docker Hub

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Login to Docker Hub
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: |
            ${{ secrets.DOCKERHUB_USERNAME }}/paypal-api:latest
            ${{ secrets.DOCKERHUB_USERNAME }}/paypal-api:${{ github.sha }}
```

---

## Support & Documentation

- **Quick Start:** [README.md](./README.md)
- **Full Deployment Guide:** [docs/deployment-guide.md](./docs/deployment-guide.md)
- **System Architecture:** [docs/system-architecture.md](./docs/system-architecture.md)
- **Code Standards:** [docs/code-standards.md](./docs/code-standards.md)
- **Project Overview:** [docs/project-overview-pdr.md](./docs/project-overview-pdr.md)
- **Codebase Summary:** [docs/codebase-summary.md](./docs/codebase-summary.md)

---

## License

MIT
