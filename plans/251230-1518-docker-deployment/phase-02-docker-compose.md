# Phase 02: Docker Compose Setup

## Context Links
- [Main Plan](./plan.md)
- [Phase 01: Dockerfile](./phase-01-dockerfile-creation.md)

## Overview
- **Priority**: P2
- **Status**: Pending
- **Effort**: 30m

Create docker-compose.yml for simplified local development and testing with environment variable management.

## Key Insights

### Docker Compose Benefits
- Single command to start all services
- Environment variable management via .env file
- Volume mounting for development
- Easy port mapping
- Network isolation
- Consistent across team members

### Current App Needs
- Single service (no database/redis dependencies)
- Environment variables for PayPal credentials
- Port 8000 exposed
- No persistent storage needed (stateless API)

## Requirements

### Functional
- Define paypal-api service
- Load environment variables from .env
- Map port 8000
- Auto-restart on failure
- Health check integration

### Non-Functional
- Easy to use for developers
- Clear service naming
- Proper network isolation
- Development-friendly configuration

## Architecture

### Service Structure
```yaml
services:
  paypal-api:
    - Build from Dockerfile
    - Load .env variables
    - Map ports
    - Health check
    - Restart policy
```

### Environment Management
- .env file for local secrets
- .env.example for template
- Docker Compose reads .env automatically

## Related Code Files

### Files to Create
- `docker-compose.yml` (root directory)
- `.env.example` (root directory, if doesn't exist)

### Files Referenced
- `Dockerfile` (built by compose)
- `.env` (loaded by compose, user-created)

## Implementation Steps

### 1. Create docker-compose.yml

Create file at project root: `docker-compose.yml`

```yaml
version: '3.8'

services:
  paypal-api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: paypal-api
    ports:
      - "${PORT:-8000}:8000"
    environment:
      - PAYPAL_CLIENT_ID=${PAYPAL_CLIENT_ID}
      - PAYPAL_CLIENT_SECRET=${PAYPAL_CLIENT_SECRET}
      - PAYPAL_MODE=${PAYPAL_MODE:-sandbox}
      - PORT=${PORT:-8000}
      - RATE_LIMIT_PER_MINUTE=${RATE_LIMIT_PER_MINUTE:-60}
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import httpx; httpx.get('http://localhost:8000/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 5s
    networks:
      - paypal-network

networks:
  paypal-network:
    driver: bridge
```

### 2. Create/Update .env.example

```bash
# PayPal API Configuration
PAYPAL_CLIENT_ID=your_client_id_here
PAYPAL_CLIENT_SECRET=your_client_secret_here
PAYPAL_MODE=sandbox

# Server Configuration
PORT=8000
RATE_LIMIT_PER_MINUTE=60
```

### 3. Test Docker Compose

```bash
# Create .env from example
cp .env.example .env
# Edit .env with your PayPal credentials

# Start services
docker-compose up -d

# View logs
docker-compose logs -f paypal-api

# Check health
docker-compose ps

# Test API
curl http://localhost:8000/health
curl http://localhost:8000/docs

# Stop services
docker-compose down
```

### 4. Verify Setup
- Service starts successfully
- Environment variables loaded correctly
- Port accessible on localhost:8000
- Health check passes
- Logs visible via docker-compose logs

## Todo List

- [ ] Create docker-compose.yml in project root
- [ ] Define paypal-api service
- [ ] Configure build context and Dockerfile
- [ ] Set container name to paypal-api
- [ ] Map ports with variable substitution
- [ ] Add environment variables from .env
- [ ] Set restart policy to unless-stopped
- [ ] Configure health check
- [ ] Create custom network (paypal-network)
- [ ] Create/update .env.example file
- [ ] Test: docker-compose up -d
- [ ] Test: View logs with docker-compose logs
- [ ] Test: Check health with docker-compose ps
- [ ] Test: Access API endpoints
- [ ] Test: docker-compose down cleanup

## Success Criteria

- docker-compose.yml builds and starts successfully
- Service accessible on http://localhost:8000
- Environment variables loaded from .env
- Health check shows healthy status
- Logs visible via docker-compose logs
- Clean shutdown with docker-compose down
- .env.example provides clear template

## Risk Assessment

### Potential Issues
1. **Missing .env file**: Users forget to create it
   - Mitigation: Clear docs, .env.example template
2. **Port conflicts**: 8000 already in use
   - Mitigation: Configurable PORT in .env
3. **Environment variable typos**: Break API calls
   - Mitigation: Validate on startup, clear error messages
4. **Health check failures**: Delay service readiness
   - Mitigation: Proper start_period configuration

### Mitigation Strategies
- Document .env setup clearly in README
- Use ${VAR:-default} for sensible defaults
- Add validation in app startup
- Test locally before documenting

## Security Considerations

### Environment Variables
- Never commit .env to git
- Add .env to .gitignore
- Provide .env.example as template
- Document required vs optional variables

### Network Security
- Use custom bridge network for isolation
- No exposed secrets in docker-compose.yml
- Restrict port access in production

## Next Steps

After docker-compose setup:
1. Create .dockerignore to optimize build
2. Update README with docker-compose instructions
3. Test full development workflow
4. Document common docker-compose commands

## Unresolved Questions

1. Should we add development volume mounting for hot reload?
   - Decision: No, keep simple. Developers can rebuild if needed
   - Alternative: Could add optional dev override file
2. Do we need separate prod/dev compose files?
   - Decision: No, single file sufficient for now
   - Future: Can add docker-compose.override.yml for dev
