# Project Overview & PDR

## Project: PayPal API Service

**Status:** Active Development (Phase 01: Docker Complete)
**Last Updated:** 2025-12-30
**Version:** 1.0.0

### Executive Summary

FastAPI wrapper for PayPal Reporting APIs providing OAuth2 authentication, rate limiting, response normalization, and security-hardened containerization. Read-only access to PayPal transaction and balance data with automatic token refresh, retry logic, and configurable sandbox/live modes.

### Core Objectives

1. **Secure OAuth2 Access** - Automatic token management with 60-second refresh buffer
2. **Rate-Limited API** - 60 req/min per IP (configurable)
3. **Normalized Responses** - camelCase to snake_case conversion for consistency
4. **Production Ready** - Docker containerization with health checks and security hardening

### Functional Requirements

#### FR-001: OAuth2 Authentication
- Client credentials flow with PayPal OAuth endpoints
- In-memory token caching (configurable TTL)
- Automatic token refresh before expiry (60s buffer)
- Support sandbox & live modes via PAYPAL_MODE env var

#### FR-002: PayPal Integration Endpoints
- GET `/api/v1/paypal/balance` - Account balance data
- GET `/api/v1/paypal/transactions` - Transaction history with pagination
- GET `/health` - Health check endpoint

#### FR-003: Rate Limiting
- Per-IP request limiting (default: 60/minute)
- Response headers: `X-RateLimit-Remaining`, `X-RateLimit-Reset`
- 429 Too Many Requests when exceeded

#### FR-004: Response Normalization
- Convert PayPal camelCase keys to snake_case
- Consistent response structure across endpoints
- Error response pass-through with original status codes

#### FR-005: Retry & Resilience
- Exponential backoff retry logic (up to 3 attempts)
- Timeout handling for network failures
- 503 Service Unavailable for network errors

### Non-Functional Requirements

#### NFR-001: Security
- Non-root user execution (appuser, UID 1000)
- Minimal base image (python:3.11-slim)
- No build tools in production container
- Environment variable validation
- Secrets not logged

#### NFR-002: Performance
- Configurable worker count (default: 1)
- Response caching via token cache
- Layer optimization in Docker multi-stage build
- Async I/O with FastAPI

#### NFR-003: Reliability
- Health check endpoint (Python http.client)
- Container health monitoring (30s interval)
- Graceful signal handling (SIGTERM/SIGINT)
- Automatic token refresh before expiry

#### NFR-004: Scalability
- Horizontal scaling via Docker/Kubernetes
- Worker configuration per container
- Stateless design (no session affinity required)
- Rate limiting per IP (no global state)

#### NFR-005: Observability
- Structured JSON request/response logging (future)
- Health check endpoint
- Container logs accessible via docker logs
- Configurable log level

#### NFR-006: Maintainability
- Clear project structure (app/, tests/, static/)
- Comprehensive documentation in docs/
- Type hints throughout codebase
- Test coverage target: 80%+

### Technical Architecture

#### Stack

- **Framework:** FastAPI 0.104+
- **Server:** Uvicorn
- **Python:** 3.11+
- **Container:** Docker (multi-stage)
- **Auth:** OAuth2 (Client Credentials)
- **Rate Limit:** Custom in-memory implementation

#### Key Components

| Component | Purpose | Tech |
|-----------|---------|------|
| FastAPI App | HTTP server & routing | app/main.py |
| PayPal Client | API integration & auth | app/services/paypal_client.py |
| Rate Limiter | Per-IP request limiting | app/services/rate_limiter.py |
| Docker Image | Production packaging | Dockerfile |
| Health Check | Container liveness | /health endpoint |

#### Data Flow

```
Client Request
    ↓
Rate Limiter (429 if exceeded)
    ↓
Route Handler
    ↓
PayPal Client
    → Token Manager (auto-refresh if <60s to expiry)
    → Retry Logic (up to 3 attempts with backoff)
    → HTTP Request to PayPal API
    ↓
Response Normalizer (camelCase → snake_case)
    ↓
Client Response
```

### Environment Variables

| Variable | Required | Default | Env | Description |
|----------|----------|---------|-----|-------------|
| PAYPAL_CLIENT_ID | Yes | - | All | PayPal OAuth client ID |
| PAYPAL_CLIENT_SECRET | Yes | - | All | PayPal OAuth client secret |
| PAYPAL_MODE | No | sandbox | All | Mode: sandbox or live |
| PORT | No | 8000 | All | Server port |
| WORKERS | No | 1 | Docker | Uvicorn worker count |
| RATE_LIMIT_PER_MINUTE | No | 60 | All | Rate limit per IP/min |

### Project Structure

```
paypal-api/
├── app/
│   ├── main.py                    # FastAPI app setup & routes
│   ├── config.py                  # Config & env validation
│   ├── api/
│   │   └── v1/
│   │       └── paypal.py          # PayPal routes (balance, transactions)
│   ├── services/
│   │   ├── paypal_client.py       # PayPal API client & token mgmt
│   │   ├── rate_limiter.py        # Per-IP rate limiting
│   │   └── exchange_rate_service.py # Currency conversion (future)
│   └── models/
│       └── responses.py           # Pydantic response models
├── tests/                         # pytest test suite
├── static/                        # Frontend assets (HTML, JS, CSS)
├── docs/                          # Documentation
│   ├── deployment-guide.md        # Docker & deployment
│   ├── project-overview-pdr.md    # This file
│   ├── code-standards.md          # Code style & patterns
│   └── system-architecture.md     # Detailed architecture
├── Dockerfile                     # Multi-stage build (220MB final)
├── .dockerignore                  # Docker build exclusions
├── requirements.txt               # Python dependencies
├── .env.example                   # Environment template
└── README.md                      # Quick start guide
```

### Acceptance Criteria

#### Phase 01 (Docker Deployment) ✅ COMPLETE

- [x] Multi-stage Dockerfile with python:3.11-slim
- [x] Final image size ~220MB
- [x] Non-root user (appuser, UID 1000)
- [x] Health check with Python http.client
- [x] PORT & WORKERS env var configuration
- [x] Documentation updated (README + deployment-guide.md)

#### Phase 02 (Planned: Frontend Integration)

- [ ] Static landing page integration
- [ ] Transaction filtering UI
- [ ] Real-time balance display
- [ ] Date range selection

#### Phase 03 (Planned: Advanced Features)

- [ ] Transaction export (CSV/JSON)
- [ ] Webhook integration
- [ ] Multi-account support
- [ ] Audit logging

### Deployment Environments

#### Development

```bash
uvicorn app.main:app --reload --port 8000
```

#### Staging

```bash
docker run -e PAYPAL_MODE=sandbox \
  -e WORKERS=2 \
  -e PORT=8080 \
  paypal-api:latest
```

#### Production

```bash
docker run --restart unless-stopped \
  -e PAYPAL_MODE=live \
  -e WORKERS=4 \
  -e PORT=8000 \
  paypal-api:latest
```

### Success Metrics

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Image Size | <250MB | ~220MB | ✅ |
| Container Startup | <5s | ~2s | ✅ |
| Health Check Pass Rate | 99% | 100% | ✅ |
| Test Coverage | 80% | 75% | ⚠️ |
| Documentation | 100% | 95% | ✅ |

### Dependencies & Integrations

#### External APIs
- **PayPal Reporting API** - Transaction & balance data
- **PayPal OAuth Endpoint** - Token generation

#### Internal Services
- None (stateless, read-only)

#### Infrastructure
- Docker (containerization)
- Docker Compose (local orchestration)
- Kubernetes (future: scaling & orchestration)

### Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| PayPal API outage | High | Low | Retry logic + fallback responses |
| Auth token expiry | Medium | Low | 60s refresh buffer |
| Rate limit blocking | Medium | Medium | Configurable per-client limits |
| Secrets exposure | Critical | Low | Env vars only, no config files |
| Container security | High | Low | Non-root user + minimal image |

### Known Issues & Limitations

1. **Single Worker Default** - WORKERS=1 for development safety. Requires manual config for production.
2. **No Persistent Storage** - In-memory token cache. Lost on container restart (acceptable: 60s refresh buffer).
3. **No Database** - Read-only API. Plan DB integration for audit logging (Phase 03+).
4. **Static Frontend** - Basic HTML/JS. Plan React/Vue migration (Phase 02+).

### Roadmap

**Q1 2025 (Weeks 1-4)**
- Phase 01: Docker ✅ Complete
- Phase 02: Frontend integration (in progress)
- Phase 03: Date range filtering

**Q1 2025 (Weeks 5-8)**
- Currency conversion service
- Enhanced error logging
- Performance metrics

**Q2 2025**
- Kubernetes manifests
- Database integration
- Advanced analytics

### Support & Escalation

| Category | Contact | Response Time |
|----------|---------|----------------|
| Bug Fixes | Dev Team | 4-24h |
| Feature Requests | Product Owner | Weekly review |
| Security Issues | Security Lead | 1h max |

### Glossary

| Term | Definition |
|------|-----------|
| **OAuth2 (PKCE)** | Secure API authentication protocol |
| **Rate Limiting** | Request throttling per IP address |
| **Multi-stage Build** | Docker build with separate builder & runtime stages |
| **Token Cache** | In-memory storage of OAuth tokens until expiry |
| **Snake Case** | variable_name format (Python convention) |
| **Camel Case** | variableName format (JavaScript convention) |

