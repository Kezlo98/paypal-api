# Phase 01: Dockerfile Creation

## Context Links
- [Main Plan](./plan.md)
- [requirements.txt](/requirements.txt)
- [app/main.py](/app/main.py)

## Overview
- **Priority**: P1
- **Status**: Pending
- **Effort**: 1h

Create production-ready Dockerfile using Python 3.11+ base image with multi-stage build pattern, security best practices, and optimized layer caching.

## Key Insights

### Current App Structure
- FastAPI app entry: `app.main:app`
- Default port: 8000
- Dependencies: requirements.txt (fastapi, uvicorn, httpx, pydantic, etc.)
- Static files: `static/` directory for frontend
- No database, stateless API service

### Docker Best Practices
- Multi-stage build reduces image size
- Non-root user improves security
- Layer caching optimizes rebuild speed
- Health check ensures container readiness
- Minimal base image (python:3.11-slim)

## Requirements

### Functional
- Install Python dependencies from requirements.txt
- Copy application code to container
- Expose port 8000
- Run uvicorn server with proper workers
- Serve static files

### Non-Functional
- Image size < 500MB
- Build time < 2 minutes
- Security: non-root user
- Health check endpoint: /health
- Graceful shutdown handling

## Architecture

### Multi-Stage Build Pattern
```
Stage 1: Builder
- Install build dependencies
- Install Python packages
- Create virtual environment

Stage 2: Runtime
- Copy only necessary files from builder
- Run as non-root user
- Minimal attack surface
```

### Container Layers (bottom to top)
1. Base: python:3.11-slim
2. System packages (if needed)
3. Python dependencies
4. Application code
5. User & permissions
6. Entry point

## Related Code Files

### Files to Create
- `Dockerfile` (root directory)

### Files Referenced
- `requirements.txt` (read)
- `app/` (copy to container)
- `static/` (copy to container)

## Implementation Steps

### 1. Create Dockerfile
Create file at project root: `Dockerfile`

```dockerfile
# Multi-stage build for smaller final image
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install system dependencies (if needed)
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Final stage - runtime
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=appuser:appuser app/ ./app/
COPY --chown=appuser:appuser static/ ./static/

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health')" || exit 1

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

# Run application with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
```

### 2. Build & Test Locally

```bash
# Build image
docker build -t paypal-api:latest .

# Run container
docker run -p 8000:8000 \
  -e PAYPAL_CLIENT_ID=your_id \
  -e PAYPAL_CLIENT_SECRET=your_secret \
  -e PAYPAL_MODE=sandbox \
  paypal-api:latest

# Test health endpoint
curl http://localhost:8000/health

# Test API
curl http://localhost:8000/docs
```

### 3. Verify Build
- Image builds without errors
- Image size reasonable (< 500MB)
- Container starts successfully
- Health check passes
- API endpoints accessible

## Todo List

- [ ] Create Dockerfile in project root
- [ ] Use python:3.11-slim base image
- [ ] Implement multi-stage build pattern
- [ ] Add non-root user (appuser)
- [ ] Copy requirements.txt with layer caching
- [ ] Install dependencies in builder stage
- [ ] Copy app code to runtime stage
- [ ] Copy static files to runtime stage
- [ ] Configure health check on /health endpoint
- [ ] Set environment variables (PYTHONUNBUFFERED, PORT)
- [ ] Expose port 8000
- [ ] Set CMD to run uvicorn
- [ ] Build image locally
- [ ] Test container startup
- [ ] Verify health check works
- [ ] Test API endpoints in container

## Success Criteria

- Dockerfile builds successfully without errors
- Final image size under 500MB
- Container runs as non-root user (appuser)
- Health check endpoint returns 200 OK
- FastAPI /docs endpoint accessible
- Static files served correctly
- Container logs show uvicorn startup

## Risk Assessment

### Potential Issues
1. **Large image size**: Mitigated by multi-stage build
2. **Slow builds**: Mitigated by layer caching (requirements.txt first)
3. **Health check failures**: Ensure /health endpoint exists in app
4. **Permission errors**: Properly set ownership for appuser
5. **Missing static files**: Verify COPY paths match directory structure

### Mitigation Strategies
- Test build locally before pushing
- Verify all file paths in COPY commands
- Check app/main.py has /health endpoint
- Use --no-cache-dir to reduce image size
- Document environment variable requirements

## Security Considerations

### Container Security
- Run as non-root user (UID 1000)
- Minimal base image (slim variant)
- No unnecessary packages installed
- Remove apt cache after installs
- Set PYTHONDONTWRITEBYTECODE=1

### Secrets Management
- Never hardcode credentials in Dockerfile
- Use environment variables for secrets
- Document required env vars in README
- Use .env file for local development
- Use Docker secrets for production

## Next Steps

After Dockerfile creation:
1. Create .dockerignore to exclude unnecessary files
2. Create docker-compose.yml for easier local development
3. Update README with Docker instructions
4. Test full build and run cycle
5. Prepare for Docker Hub push

## Unresolved Questions

1. Should we use multiple workers for uvicorn? (Currently set to 1)
   - Decision: Start with 1, scale later if needed
2. Do we need any additional system packages in runtime stage?
   - Decision: No, Python 3.11-slim has all we need
3. Should health check use httpx or simpler method?
   - Current: Uses httpx (already in dependencies)
   - Alternative: Could use curl if we install it
