# System Architecture

## High-Level Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Application                        │
│                 (Browser / Frontend / Mobile App)                │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP/REST
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Docker Container (220MB)                      │
│                  ┌───────────────────────┐                      │
│                  │  FastAPI Application  │                      │
│                  │  (Python 3.11-slim)   │                      │
│                  └──────────┬────────────┘                      │
│                             │                                   │
│      ┌──────────────────────┼──────────────────────┐            │
│      ▼                      ▼                      ▼            │
│  ┌────────┐         ┌────────────┐        ┌──────────┐         │
│  │ Routes │         │Rate Limiter│        │ Health   │         │
│  │ Handler│         │ (Per IP)   │        │ Check    │         │
│  └────┬───┘         └────────────┘        └──────────┘         │
│       │                                                          │
│       ▼                                                          │
│  ┌──────────────────────────────────┐                          │
│  │   PayPal API Client Service      │                          │
│  │  ┌──────────────┐ ┌──────────┐  │                          │
│  │  │OAuth2 Client │ │ Token    │  │                          │
│  │  │ (PKCE Flow)  │ │ Manager  │  │                          │
│  │  └──────────────┘ └──────────┘  │                          │
│  │        ├─ Auto Refresh (60s buf) │                          │
│  │        └─ In-Memory Cache        │                          │
│  │  ┌──────────────┐ ┌──────────┐  │                          │
│  │  │ Retry Logic  │ │Response  │  │                          │
│  │  │(Exponential) │ │Normalizer│  │                          │
│  │  └──────────────┘ └──────────┘  │                          │
│  └──────────────────────────────────┘                          │
│                  │                                              │
│                  │ (HTTPS)                                      │
│                  ▼                                              │
│        ┌──────────────────────┐                                │
│        │ PayPal API Endpoints │                                │
│        │ - /v1/reporting/...  │                                │
│        │ - OAuth2 Token EP    │                                │
│        └──────────────────────┘                                │
│                                                                 │
│  Non-root user: appuser (UID 1000)                            │
│  Exposed port: 8000 (configurable via PORT env var)           │
│  Workers: 1 (configurable via WORKERS env var)                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Component Architecture

### 1. FastAPI Application Layer

**File:** `app/main.py`

Responsibilities:
- HTTP server initialization
- Route registration
- Middleware setup (logging, error handling)
- Health check endpoint
- CORS configuration (if needed)

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import paypal

app = FastAPI(
    title="PayPal API Service",
    version="1.0.0",
    docs_url="/docs"
)

# CORS middleware (restrict origins in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure per environment
    allow_methods=["GET"],
    allow_headers=["*"]
)

# Routes
app.include_router(paypal.router)

@app.get("/health")
async def health():
    return {"status": "ok"}
```

### 2. API Routes Layer

**File:** `app/api/v1/paypal.py`

Responsibilities:
- HTTP endpoint definitions
- Query parameter validation
- Request/response transformation
- Error status code mapping
- Rate limiting enforcement

**Endpoints:**

| Method | Path | Description | Status |
|--------|------|-------------|--------|
| GET | `/health` | Health check | 200 |
| GET | `/api/v1/paypal/balance` | Account balance | 200/401/503/429 |
| GET | `/api/v1/paypal/transactions` | Transaction history | 200/401/503/429 |

**Query Parameters:**

```
GET /api/v1/paypal/transactions
  ?start_date=2025-12-01
  &end_date=2025-12-31
  &page=1
  &page_size=20
  &transaction_status=S
```

### 3. Services Layer

#### 3.1 PayPal Client Service

**File:** `app/services/paypal_client.py`

Responsibilities:
- OAuth2 token acquisition & refresh
- PayPal API HTTP requests
- Retry logic with exponential backoff
- Response normalization (camelCase → snake_case)
- Error handling & categorization

**Key Methods:**

```python
class PayPalClient:
    async def get_balance() -> Dict[str, str]
    async def get_transactions(
        start_date: str,
        end_date: str,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]

    async def _get_token() -> str  # Private: Token management
    async def _request(method, url, **kwargs) -> dict  # Private: HTTP wrapper
    async def _normalize_response(data: dict) -> dict  # Private: Key conversion
```

**Token Management Flow:**

```
Request to PayPal API
    ↓
Check cached token
    ├─ Valid & not expiring soon → Use it
    └─ Missing or expiring in <60s → Refresh
         ↓
     OAuth2 Client Credentials Flow
         ├─ POST /oauth2/token
         ├─ Returns: {access_token, expires_in}
         └─ Cache: Token + expiry time
    ↓
Use token in Authorization header
    ↓
Process response
```

**Retry Logic:**

```
Attempt 1 (immediate)
    │ Failure (network/transient)
    ├─ Wait: 1s (2^0)
    ▼
Attempt 2
    │ Failure
    ├─ Wait: 2s (2^1)
    ▼
Attempt 3 (last)
    │ Failure
    └─ Raise Exception
```

#### 3.2 Rate Limiter Service

**File:** `app/services/rate_limiter.py`

Responsibilities:
- Per-IP request counting
- Rate limit enforcement (60 req/min default)
- Reset tracking
- Header calculation (X-RateLimit-*)

**Algorithm:**

```
Request from IP: 192.168.1.100
    ↓
Lookup: ip_requests["192.168.1.100"]
    ├─ Not found → Create: count=1, reset_time=now+60s
    ├─ Found & reset_time passed → Reset: count=1, reset_time=now+60s
    ├─ Found & count < 60 → Increment: count++
    └─ Found & count >= 60 → Reject: 429 Too Many Requests
    ↓
Response Headers:
  X-RateLimit-Limit: 60
  X-RateLimit-Remaining: <count>
  X-RateLimit-Reset: <unix_timestamp>
```

**Cleanup:**

- Expired buckets removed periodically
- Memory efficient: O(n) where n = unique IPs

#### 3.3 Exchange Rate Service (Future)

**File:** `app/services/exchange_rate_service.py`

Placeholder for currency conversion logic (Phase 03+).

### 4. Models Layer

**File:** `app/models/responses.py`

Pydantic models for:
- Response validation
- OpenAPI schema generation
- Type safety

```python
class BalanceResponse(BaseModel):
    currency_code: str
    total_balance: str
    available_balance: str
    updated_at: datetime

class TransactionResponse(BaseModel):
    transaction_id: str
    amount: str
    currency: str
    status: str
    transaction_date: datetime

class PaginatedTransactions(BaseModel):
    transactions: List[TransactionResponse]
    page: int
    page_size: int
    total_count: int
    total_pages: int
```

### 5. Configuration Layer

**File:** `app/config.py`

Responsibilities:
- Environment variable loading
- Type validation
- Sensible defaults
- Runtime validation

```python
class Settings(BaseSettings):
    # PayPal credentials
    paypal_client_id: str  # Required
    paypal_client_secret: str  # Required
    paypal_mode: Literal["sandbox", "live"] = "sandbox"

    # Server
    port: int = 8000
    workers: int = 1

    # Features
    rate_limit_per_minute: int = 60
    token_refresh_buffer: int = 60
    request_timeout: int = 30
    max_retries: int = 3

    # Validation
    @validator('paypal_mode')
    def validate_mode(cls, v):
        if v not in ["sandbox", "live"]:
            raise ValueError("Must be 'sandbox' or 'live'")
        return v
```

## Data Flow Diagrams

### Flow 1: Get Account Balance

```
GET /api/v1/paypal/balance
    ↓
FastAPI route handler
    ├─ Check rate limit (IP)
    │   └─ Exceeded? → 429
    ├─ Call PayPalClient.get_balance()
    │   ├─ Get or refresh token
    │   │   └─ POST /oauth2/token (if needed)
    │   ├─ GET /reporting/transactions (search)
    │   │   └─ Retry up to 3x with backoff
    │   ├─ Aggregate balance from transactions
    │   └─ Normalize response (camelCase → snake_case)
    ├─ Return JSON response
    └─ Update rate limit headers

Response:
{
    "currency_code": "USD",
    "total_balance": "1000.00",
    "available_balance": "950.00",
    "updated_at": "2025-12-30T10:00:00Z"
}
```

### Flow 2: List Transactions

```
GET /api/v1/paypal/transactions?start_date=2025-12-01&end_date=2025-12-31
    ↓
Route validation:
    ├─ Parse dates (ISO 8601)
    ├─ Validate page & page_size
    └─ Check rate limit
    ↓
PayPalClient.get_transactions()
    ├─ Ensure token fresh (60s buffer)
    ├─ Split large date range if needed (PayPal limits)
    │   └─ Make multiple requests
    ├─ Aggregate results
    ├─ Normalize keys
    └─ Paginate response
    ↓
Return:
{
    "transactions": [
        {
            "transaction_id": "123",
            "amount": "50.00",
            "currency": "USD",
            "status": "S",
            "transaction_date": "2025-12-30T10:00:00Z"
        }
    ],
    "page": 1,
    "page_size": 20,
    "total_count": 45,
    "total_pages": 3
}
```

### Flow 3: OAuth2 Token Refresh

```
Token check on request
    ↓
Is token cached?
    ├─ No → Get new token
    ├─ Yes & expiry > now + 60s → Use cached
    └─ Yes & expiry ≤ now + 60s → Refresh
    ↓
POST /oauth2/token
    ├─ Client ID: <paypal_client_id>
    ├─ Client Secret: <paypal_client_secret>
    ├─ Grant Type: client_credentials
    └─ Scope: https://api.paypal.com/v1/reporting.transactions
    ↓
Response:
{
    "access_token": "A21ABc...",
    "token_type": "Bearer",
    "expires_in": 3600
}
    ↓
Cache token:
    ├─ Token value
    ├─ Received at: now
    ├─ Expiry: now + 3600s
    └─ TTL: 3600s
```

## Deployment Architecture

### Development Environment

```
Developer Machine
    ├─ Source: /Users/nam/galaxy/sonbip/paypal-api/
    ├─ Python venv: .venv/
    ├─ Server: uvicorn --reload (hot reload on file changes)
    ├─ Port: 8000
    └─ Database: None (stateless)
```

### Docker Container

```
Docker Container
    ├─ Image: paypal-api:latest (220MB)
    ├─ Base: python:3.11-slim
    ├─ User: appuser (UID 1000, non-root)
    ├─ Port: 8000 (configurable via PORT env var)
    ├─ Workers: 1 (configurable via WORKERS env var)
    ├─ Entrypoint: sh -c "uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers ${WORKERS}"
    ├─ Health check: /health endpoint
    │   ├─ Interval: 30s
    │   ├─ Timeout: 10s
    │   ├─ Grace period: 5s
    │   └─ Retries: 3
    ├─ Volumes: None (stateless)
    └─ Environment:
        ├─ PAYPAL_CLIENT_ID
        ├─ PAYPAL_CLIENT_SECRET
        ├─ PAYPAL_MODE (sandbox|live)
        ├─ PORT (8000)
        ├─ WORKERS (1)
        ├─ PYTHONUNBUFFERED (1)
        └─ PYTHONDONTWRITEBYTECODE (1)
```

### Scaling Strategy

#### Horizontal Scaling (Multiple Containers)

```
Load Balancer (nginx/HAProxy/Cloud Load Balancer)
    ├─ Container 1: Port 8000
    ├─ Container 2: Port 8001
    ├─ Container 3: Port 8002
    └─ Container N: Port 800N

Health Check: GET /health (30s interval)
Algorithm: Round-robin or least-connections
```

#### Vertical Scaling (Single Container)

```
Docker Container
    ├─ Workers: 4 (increased from default 1)
    ├─ Memory: 512MB+ (depends on workers)
    └─ CPU: 1+ cores
```

**Formula for optimal workers:**
```
WORKERS = (CPU_CORES × 2) + 1
Example: 4 cores = 9 workers
```

## Security Architecture

### Authentication & Authorization

```
Client Request
    ├─ No authentication required for API endpoints
    │  (Read-only access, credentials in backend only)
    ├─ Internal PayPal auth:
    │   └─ OAuth2 Client Credentials (server-to-server)
    └─ Optional: API key auth for future phases
```

### Secrets Management

```
Production Deployment
    ├─ Secrets stored in:
    │   ├─ Docker Secrets (Swarm)
    │   ├─ Kubernetes Secrets
    │   └─ Cloud KMS (AWS/GCP/Azure)
    ├─ Never in:
    │   ├─ Docker images
    │   ├─ Docker logs
    │   ├─ Code repository
    │   └─ Application logs
    └─ Injected via environment variables at runtime
```

### Network Security

```
Container Network
    ├─ Exposed: Port 8000 (configurable)
    ├─ Ingress: HTTPS only (configured at load balancer)
    ├─ Egress: HTTPS to PayPal API
    └─ User: appuser (UID 1000, no root access)
```

## Dependency Architecture

### External Dependencies

```
PayPal API (OAuth2 + Reporting)
    ├─ Endpoint: api.paypal.com (sandbox) or live
    ├─ Protocol: HTTPS
    ├─ Auth: OAuth2 Client Credentials
    ├─ Retry: 3 attempts with exponential backoff
    └─ Timeout: 30 seconds per request
```

### Internal Dependencies

```
Python Dependencies:
    ├─ fastapi (0.104+) - Web framework
    ├─ uvicorn - ASGI server
    ├─ pydantic (2.0+) - Data validation
    ├─ httpx - Async HTTP client
    ├─ python-multipart - Form parsing
    └─ pydantic-settings - Environment config

Development Dependencies:
    ├─ pytest - Testing framework
    ├─ pytest-asyncio - Async test support
    ├─ pytest-cov - Coverage reporting
    ├─ pytest-mock - Mocking utilities
    └─ black - Code formatter
```

## Error Handling Architecture

```
Error Hierarchy:
    ├─ PayPalError (base)
    │   ├─ InvalidCredentialsError (401 Unauthorized)
    │   ├─ RateLimitError (429 Too Many Requests)
    │   ├─ PayPalAPIError (4xx/5xx from PayPal)
    │   └─ NetworkError (connection issues)
    └─ FastAPI HTTPException
         ├─ 400 Bad Request (invalid params)
         ├─ 401 Unauthorized (auth failed)
         ├─ 429 Too Many Requests (rate limit)
         ├─ 500 Internal Server Error
         └─ 503 Service Unavailable (PayPal down)
```

## Caching Architecture

```
Token Cache (In-Memory)
    ├─ Data: OAuth2 access_token
    ├─ Key: Composite (client_id + mode)
    ├─ TTL: token.expires_in - 60s (refresh buffer)
    ├─ Eviction: Automatic on expiry
    └─ Limitation: Lost on container restart (acceptable)

Response Cache:
    ├─ Status: Not implemented
    ├─ Reason: Read-only API, data should be fresh
    └─ Future: Implement for high-volume scenarios
```

## Performance Characteristics

### Request Latency

| Operation | Latency | Notes |
|-----------|---------|-------|
| Health check | <10ms | Local endpoint |
| Get balance | 500-2000ms | 1x PayPal API call |
| List transactions | 500-2000ms | 1-N PayPal API calls (date range split) |
| Token refresh | 200-500ms | PayPal OAuth endpoint |

### Resource Usage

| Resource | Default | Config | Notes |
|----------|---------|--------|-------|
| Memory | 150-300MB | Workers × 50MB | Depends on workers |
| CPU | <10% idle | Workers × 25% | Per core |
| Disk | 220MB | N/A | Docker image size |
| Connections | 1-4 | Workers | HTTP connections to PayPal |

## Monitoring & Observability

```
Observability Stack:
    ├─ Logs: STDOUT/STDERR (JSON format, future)
    ├─ Health: GET /health endpoint
    ├─ Metrics: None built-in (Prometheus, future)
    ├─ Traces: None built-in (Jaeger, future)
    └─ Alerts: Orchestrator-level (Kubernetes, etc.)
```

## Future Architecture Phases

### Phase 02: Frontend Integration
- Static files served from /static
- HTML template rendering
- Transaction filtering UI

### Phase 03: Database Integration
- PostgreSQL for audit logs
- Transaction caching (opt-in)
- User sessions (if needed)

### Phase 04: Advanced Services
- Webhook support
- Event streaming
- Analytics & reporting

### Phase 05: Kubernetes Ready
- Helm charts
- Network policies
- Multi-zone deployment

