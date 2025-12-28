# PayPal API MVP - Brainstorm Report

**Date:** 2025-12-26
**Status:** Ready for Implementation Planning

---

## Problem Statement

Build a Python 3.11 + FastAPI service that exposes read-only PayPal Reporting APIs as a public API for website consumption.

### Core Requirements

| Area | Requirement |
|------|-------------|
| **Endpoints** | `GET /api/v1/paypal/balance`, `GET /api/v1/paypal/transactions` |
| **Auth** | OAuth2 Client Credentials with token caching + auto-refresh |
| **Mode** | Support sandbox & live via `PAYPAL_MODE` env var |
| **Timeout** | 5s, retry ≤ 3 |
| **Protection** | Rate limiting (public API) |
| **Response** | Minimal cleanup (snake_case, flatten) |
| **Errors** | Raw PayPal errors passthrough |
| **Pagination** | Forward to PayPal (cursor-based) |

### Tech Stack

- Python 3.11
- FastAPI
- httpx (async HTTP)
- pydantic

---

## Clarified Requirements

Based on discovery phase:

| Question | Answer | Implication |
|----------|--------|-------------|
| Deployment | Single instance | In-memory token cache sufficient |
| Consumers | Public website | Rate limiting required |
| Pagination | Forward to PayPal | Use PayPal's pagination params directly |
| Error handling | Raw PayPal errors | Simple passthrough, no wrapper |
| Normalization | Minimal cleanup | snake_case conversion, field flattening |
| Auth protection | Rate limiting only | No API keys/JWT for public endpoint |

---

## Architecture Approaches Evaluated

### Approach A: Simple Proxy (RECOMMENDED)

```
Client → FastAPI → httpx → PayPal API
         ↓
    Rate Limiter
```

**Pros:**
- KISS: minimal code, easy to understand
- YAGNI: no unnecessary abstraction layers
- Fast to build, easy to debug
- PayPal pagination works naturally

**Cons:**
- Less control over response format
- PayPal API changes affect consumers
- No caching layer (every hit calls PayPal)

**Verdict:** Best fit for MVP. Aligns with "minimal cleanup" requirement.

---

### Approach B: Aggregation Layer (OVER-ENGINEERED)

```
Client → FastAPI → Service Layer → Repository → httpx → PayPal
         ↓                                ↓
    Rate Limiter                    Response Cache
```

**Pros:**
- Clean separation of concerns
- Testable components
- Easy to add caching later

**Cons:**
- Violates YAGNI for 2 endpoints
- More files to maintain
- Indirection makes debugging harder

**Verdict:** Skip until you have >5 endpoints or business logic.

---

### Approach C: Full Transformation Layer (REJECTED)

```
Client → FastAPI → Normalizer → PayPal Client → PayPal
         ↓
    Custom Schemas
```

**Pros:**
- Maximum API stability
- Version can stay same while PayPal changes

**Cons:**
- Major maintenance burden
- You said "raw errors" - conflicts with this approach
- Need to map every PayPal field

**Verdict:** User explicitly chose "minimal cleanup," not this.

---

## Final Recommended Solution

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Public Website                      │
└────────────────────────────┬────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────┐
│  FastAPI Application                                    │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Rate Limiting Middleware (slower, slowpoke)    │   │
│  └─────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────┐   │
│  │  /api/v1/paypal/balance                          │   │
│  │  /api/v1/paypal/transactions                     │   │
│  └─────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────┐   │
│  │  PayPal Client (httpx)                          │   │
│  │  - OAuth2 token management                      │   │
│  │  - In-memory token cache                        │   │
│  │  - Auto-refresh on 401                          │   │
│  │  - Retry logic (≤3)                             │   │
│  │  - 5s timeout                                   │   │
│  └─────────────────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────┘
                             │
                             ▼
                    ┌────────────────┐
                    │  PayPal API     │
                    │  (Sandbox/Live) │
                    └────────────────┘
```

### Project Structure

```
paypal-api/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app setup
│   ├── config.py               # Env vars + settings
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       └── paypal.py       # Route handlers
│   ├── services/
│   │   ├── __init__.py
│   │   ├── paypal_client.py    # httpx wrapper + OAuth
│   │   └── rate_limiter.py     # Rate limiting
│   └── models/
│       ├── __init__.py
│       └── responses.py        # Pydantic schemas
├── tests/
│   ├── __init__.py
│   ├── test_api.py
│   └── test_paypal_client.py
├── .env.example
├── requirements.txt
├── pyproject.toml              # Poetry/pyproject
└── README.md
```

### Key Implementation Decisions

| Area | Decision | Rationale |
|------|----------|-----------|
| **Token Cache** | In-memory `dict` | Single instance, simplest |
| **Rate Limiting** | `slowapi` (Sliding Window) | Battle-tested, FastAPI-native |
| **HTTP Client** | `httpx.AsyncClient` | Async by design, connection pooling |
| **Retry Logic** | `httpx` + simple retry counter | No extra deps for 3 retries |
| **Normalization** | Response middleware | Apply snake_case globally |
| **Error Handling** | Raise `HTTPException` with PayPal body | Clean Swagger, raw errors |

### Environment Variables

```bash
# PayPal
PAYPAL_CLIENT_ID=your_client_id
PAYPAL_CLIENT_SECRET=your_client_secret
PAYPAL_MODE=sandbox  # or "live"

# Server
PORT=8000
WORKERS=1  # single instance = in-memory cache works

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
```

### Endpoint Specs

#### GET /api/v1/paypal/balance

```python
# Request: None
# Response (PayPal raw, minimal cleanup)
{
  "balances": [
    {
      "currency": "USD",
      "primary": true,
      "total_balance": {
        "currency_code": "USD",
        "value": "1234.56"
      }
    }
  ],
  "timestamp": "2025-12-26T21:14:00Z"
}
```

#### GET /api/v1/paypal/transactions

```python
# Query params (forwarded to PayPal)
start_date: str  # ISO 8601, required
end_date: str    # ISO 8601, required
page: int = 1
page_size: int = 20
transaction_status: str | None = None

# Response (PayPal raw, minimal cleanup)
{
  "transaction_details": [...],
  "total_items": 100,
  "total_pages": 5
}
```

### Rate Limiting Strategy

```
- 60 requests/minute per IP
- Sliding window for smooth distribution
- Response: 429 Too Many Requests
- Headers: X-RateLimit-Remaining, X-RateLimit-Reset
```

### Token Management Flow

```
1. Check in-memory cache for valid token
2. If expired/missing:
   - POST /v1/oauth2/token
   - Cache with expires_at = now + expires_in - 60s (buffer)
3. Make API call with Bearer token
4. If 401 Unauthorized:
   - Clear cache
   - Retry once with fresh token
5. If still 401 → raise HTTPException
```

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| PayPal API changes break consumers | High | Version your API (`/api/v1/`), document PayPal dependency |
| Rate limiting too aggressive | Medium | Make configurable via env, expose in docs |
| Token race condition (multiple requests) | Low | Lock-free: let multiple requests fetch token, last write wins |
| PayPal downtime | Medium | FastAPI timeout returns 504, frontend handles gracefully |
| Memory leak in token cache | Low | Simple dict with TTL, max 1 entry per mode |

---

## Success Criteria

- [ ] Both endpoints return PayPal data successfully
- [ ] Token auto-refreshes on expiry
- [ ] Rate limiting prevents abuse
- [ ] Swagger docs at `/docs` work
- [ ] Error responses include PayPal error body
- [ ] Sandbox and live modes work via env var
- [ ] Timeout + retry logic tested
- [ ] Response fields are snake_case

---

## Dependencies

```
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
httpx>=0.28.0
pydantic>=2.10.0
slowapi>=0.1.9
python-dotenv>=1.0.0
pytest>=8.0.0
pytest-asyncio>=0.24.0
```

---

## Open Questions

1. **Rate limit granularity** - Per-IP or per-API-key? (You said per-IP for public)
2. **CORS** - Which domains can call your API? (Need config)
3. **Monitoring** - Need logging/metrics for production? (Consider later)

---

## Next Steps

Do you want to create a detailed implementation plan?

If **Yes**: I'll run `/plan` to create step-by-step implementation tasks.
If **No**: You have everything needed to build this.

---

**Report End**
