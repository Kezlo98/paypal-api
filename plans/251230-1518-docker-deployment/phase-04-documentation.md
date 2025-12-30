# Phase 04: Docker Hub Documentation

## Context Links
- [Main Plan](./plan.md)
- [Phase 01: Dockerfile](./phase-01-dockerfile-creation.md)
- [Phase 02: Docker Compose](./phase-02-docker-compose.md)
- [README.md](/README.md)

## Overview
- **Priority**: P1
- **Status**: Pending
- **Effort**: 45m

Update README.md with comprehensive Docker deployment instructions including Docker Hub publishing, image usage, and troubleshooting.

## Key Insights

### Documentation Needs
- Clear Docker installation requirements
- Step-by-step Docker build instructions
- Docker Hub push/pull workflow
- Environment variable configuration
- Common troubleshooting scenarios
- Quick start with docker-compose

### Target Audience
- Developers (local development)
- DevOps (deployment)
- Users (running pre-built images)

## Requirements

### Functional
- Docker installation prerequisites
- Local build instructions
- Docker Hub deployment workflow
- Pull and run pre-built image
- Environment variable setup
- docker-compose quick start
- Troubleshooting section

### Non-Functional
- Clear and concise
- Copy-paste ready commands
- Well-organized sections
- Beginner-friendly

## Architecture

### README Structure Addition
```markdown
## Docker Deployment

### Prerequisites
- Docker Engine 20.10+
- Docker Compose 2.0+ (optional)

### Quick Start (Docker Compose)
- One-command startup
- Environment configuration

### Building from Source
- Build image locally
- Tag conventions

### Docker Hub Deployment
- Login to Docker Hub
- Tag for Docker Hub
- Push to registry

### Running Pre-built Image
- Pull from Docker Hub
- Run container
- Configuration

### Troubleshooting
- Common issues
- Solutions
```

## Related Code Files

### Files to Modify
- `README.md` (add Docker deployment section)

### Files Referenced
- `Dockerfile` (referenced in docs)
- `docker-compose.yml` (referenced in docs)
- `.env.example` (referenced in docs)

## Implementation Steps

### 1. Add Docker Deployment Section to README

Add new section after "Quick Start" or before "API Endpoints":

```markdown
## Docker Deployment

### Prerequisites

- Docker Engine 20.10+ ([Install Docker](https://docs.docker.com/get-docker/))
- Docker Compose 2.0+ (optional, included with Docker Desktop)
- Docker Hub account (for publishing)

### Quick Start with Docker Compose

```bash
# 1. Clone repository
git clone https://github.com/yourusername/paypal-api.git
cd paypal-api

# 2. Configure environment
cp .env.example .env
# Edit .env with your PayPal credentials

# 3. Start with docker-compose
docker-compose up -d

# 4. View logs
docker-compose logs -f paypal-api

# 5. Access API
open http://localhost:8000/docs

# 6. Stop services
docker-compose down
```

### Building Docker Image Locally

```bash
# Build image
docker build -t paypal-api:latest .

# Run container
docker run -d \
  --name paypal-api \
  -p 8000:8000 \
  -e PAYPAL_CLIENT_ID=your_client_id \
  -e PAYPAL_CLIENT_SECRET=your_secret \
  -e PAYPAL_MODE=sandbox \
  paypal-api:latest

# View logs
docker logs -f paypal-api

# Stop container
docker stop paypal-api
docker rm paypal-api
```

### Publishing to Docker Hub

```bash
# 1. Login to Docker Hub
docker login

# 2. Tag image with your Docker Hub username
docker tag paypal-api:latest yourusername/paypal-api:latest
docker tag paypal-api:latest yourusername/paypal-api:v1.0.0

# 3. Push to Docker Hub
docker push yourusername/paypal-api:latest
docker push yourusername/paypal-api:v1.0.0

# 4. Verify on Docker Hub
# Visit: https://hub.docker.com/r/yourusername/paypal-api
```

### Running Pre-built Image from Docker Hub

```bash
# Pull image from Docker Hub
docker pull yourusername/paypal-api:latest

# Run container
docker run -d \
  --name paypal-api \
  -p 8000:8000 \
  -e PAYPAL_CLIENT_ID=your_client_id \
  -e PAYPAL_CLIENT_SECRET=your_secret \
  -e PAYPAL_MODE=sandbox \
  yourusername/paypal-api:latest

# Health check
curl http://localhost:8000/health

# Access Swagger docs
open http://localhost:8000/docs
```

### Environment Variables for Docker

When running containers, provide these environment variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PAYPAL_CLIENT_ID` | Yes | - | PayPal OAuth2 client ID |
| `PAYPAL_CLIENT_SECRET` | Yes | - | PayPal OAuth2 client secret |
| `PAYPAL_MODE` | No | `sandbox` | PayPal environment: `sandbox` or `live` |
| `PORT` | No | `8000` | Server port (internal container port) |
| `RATE_LIMIT_PER_MINUTE` | No | `60` | Rate limit per IP per minute |

### Docker Image Details

- **Base Image**: python:3.11-slim
- **Image Size**: ~450MB
- **Exposed Port**: 8000
- **Health Check**: `/health` endpoint
- **User**: Non-root (appuser, UID 1000)
- **Working Directory**: `/app`

### Troubleshooting

#### Container won't start
```bash
# Check logs
docker logs paypal-api

# Common issues:
# - Missing environment variables
# - Port 8000 already in use
# - Invalid PayPal credentials
```

#### Health check failing
```bash
# Check health status
docker inspect paypal-api | grep -A 10 Health

# Manual health check
curl http://localhost:8000/health

# Verify app is listening
docker exec paypal-api netstat -tlnp
```

#### Can't access API
```bash
# Verify port mapping
docker ps | grep paypal-api

# Check if port is exposed
docker port paypal-api

# Test from inside container
docker exec paypal-api curl http://localhost:8000/health
```

#### Build fails
```bash
# Clear Docker cache
docker builder prune

# Rebuild without cache
docker build --no-cache -t paypal-api:latest .

# Check Docker disk space
docker system df
```

### Docker Commands Reference

```bash
# Build
docker build -t paypal-api .

# Run (detached)
docker run -d --name paypal-api -p 8000:8000 paypal-api

# Run (with env file)
docker run -d --name paypal-api -p 8000:8000 --env-file .env paypal-api

# View logs
docker logs -f paypal-api

# Execute command in container
docker exec -it paypal-api bash

# Stop
docker stop paypal-api

# Remove
docker rm paypal-api

# Remove image
docker rmi paypal-api
```

## Docker Compose Commands

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Restart service
docker-compose restart paypal-api

# Stop services
docker-compose down

# Rebuild and restart
docker-compose up -d --build

# Remove volumes
docker-compose down -v
```
```

### 2. Update Project Structure Section

Add Docker files to project structure:

```markdown
## Project Structure

```
paypal-api/
├── app/
│   ├── main.py              # FastAPI app
│   ├── config.py            # Configuration
│   ├── api/v1/paypal.py     # Routes
│   ├── services/
│   │   ├── paypal_client.py # PayPal API client
│   │   └── rate_limiter.py  # Rate limiting
│   └── models/
│       └── responses.py     # Response models
├── static/                  # Static frontend files
├── tests/                   # pytest tests
├── Dockerfile               # Docker image definition
├── docker-compose.yml       # Docker Compose configuration
├── .dockerignore            # Docker build exclusions
├── requirements.txt
├── .env.example
└── README.md
```
```

### 3. Add Quick Start Docker Option

Update Quick Start section to include Docker:

```markdown
## Quick Start

### Option 1: Docker (Recommended)

```bash
# Using docker-compose
docker-compose up -d

# Using Docker directly
docker pull yourusername/paypal-api:latest
docker run -d -p 8000:8000 --env-file .env yourusername/paypal-api:latest
```

### Option 2: Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your PayPal credentials

# Run development server
uvicorn app.main:app --reload --port 8000
```
```

## Todo List

- [ ] Read current README.md structure
- [ ] Add "Docker Deployment" section after Quick Start
- [ ] Add Prerequisites subsection
- [ ] Add Quick Start with Docker Compose
- [ ] Add Building Docker Image Locally section
- [ ] Add Publishing to Docker Hub section
- [ ] Add Running Pre-built Image section
- [ ] Add Environment Variables for Docker table
- [ ] Add Docker Image Details section
- [ ] Add Troubleshooting section with common issues
- [ ] Add Docker Commands Reference
- [ ] Add Docker Compose Commands Reference
- [ ] Update Project Structure to include Docker files
- [ ] Update Quick Start to include Docker option
- [ ] Test all documented commands
- [ ] Verify all links work
- [ ] Proofread for clarity and accuracy

## Success Criteria

- README includes comprehensive Docker section
- All Docker commands copy-paste ready
- Docker Hub workflow clearly documented
- Troubleshooting covers common scenarios
- Environment variables table complete
- Quick start includes Docker option
- Project structure shows Docker files
- Documentation tested and verified accurate
- No broken links or formatting issues

## Risk Assessment

### Potential Issues
1. **Outdated commands**: Docker commands change over time
   - Mitigation: Use stable Docker features, note version requirements
2. **Username placeholders**: Readers forget to replace
   - Mitigation: Clear callouts, use obvious placeholders
3. **Environment setup confusion**: Multiple configuration methods
   - Mitigation: Provide clear examples for each method
4. **Port conflicts**: Users have 8000 in use
   - Mitigation: Document port configuration options

### Mitigation Strategies
- Test all commands before documenting
- Use consistent placeholder format (yourusername, your_client_id)
- Add notes for common pitfalls
- Provide alternative approaches where applicable

## Security Considerations

### Documentation Security
- Never include actual credentials in examples
- Use obvious placeholders (your_client_id, your_secret)
- Warn against committing .env files
- Document proper secrets management

### Credential Warnings
Add warnings in documentation:
```markdown
**⚠️ Security Warning**: Never commit your `.env` file or hardcode credentials in Docker commands. Always use environment variables or Docker secrets in production.
```

## Next Steps

After documentation:
1. Review documentation with fresh eyes
2. Test all commands on clean system
3. Gather feedback from team
4. Optional: Create GitHub Actions workflow (Phase 05)

## Unresolved Questions

1. Should we document multi-stage deployment strategies?
   - Decision: No, keep simple for now. Advanced users can adapt
2. Include production deployment best practices (Kubernetes, etc.)?
   - Decision: No, focus on Docker Hub. K8s is out of scope
3. Document docker-compose for production use?
   - Decision: Yes, but note it's primarily for development
