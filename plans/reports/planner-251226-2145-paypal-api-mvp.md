# PayPal API MVP - Implementation Plan Summary

## Deliverable
Comprehensive implementation plan for FastAPI service exposing PayPal Reporting APIs.

**Location**: `/Users/nam/galaxy/sonbip/paypal-api/plans/251226-2144-paypal-api-mvp/plan.md`

## Plan Overview

### Scope
- **2 Endpoints**: GET /balance, GET /transactions
- **Tech Stack**: Python 3.11 + FastAPI + httpx + slowapi
- **Features**: OAuth2 client credentials, in-memory token cache, rate limiting (60/min), retry logic, sandbox/live modes

### Effort & Timeline
- **Total**: ~6 hours
- **10 Phases**: Sequential execution (no parallel deps)

### Key Implementation Files

| File | Purpose | Lines |
|------|---------|-------|
| `app/config.py` | Pydantic Settings env vars | ~40 |
| `app/services/paypal_client.py` | httpx wrapper + OAuth2 + cache | ~120 |
| `app/services/rate_limiter.py` | slowapi middleware | ~5 |
| `app/models/responses.py` | Pydantic schemas (minimal) | ~15 |
| `app/api/v1/paypal.py` | Route handlers + snake_case conv | ~80 |
| `app/main.py` | FastAPI app + CORS + lifespan | ~45 |
| `tests/*.py` | pytest test suite | ~150 |

### Core Features Specified

**OAuth2 Token Cache**:
```python
# In-memory dict: {"sandbox": {"token": "...", "expires_at": 1699999999}}
# 60s refresh buffer, auto-clear on 401
```

**Retry Logic**:
- Max 3 attempts, exponential backoff (0.5s * 2^attempt)
- 401: clear cache, retry once
- Network errors: retry with backoff

**Rate Limiting**:
- slowapi: 60 req/min per IP
- Returns 429 with X-RateLimit headers

**Response Normalization**:
- camelCase → snake_case via regex conversion
- Raw PayPal errors pass-through

### Implementation Phases

1. Project Setup (30 min)
2. Config Layer (45 min)
3. PayPal Client Service (2h)
4. Rate Limiter (30 min)
5. Response Models (30 min)
6. API Routes (1h)
7. FastAPI App Setup (30 min)
8. Test Suite (1h)
9. Documentation (15 min)
10. Validation (15 min)

### Test Coverage

- Unit: Token caching, retry logic, snake_case conversion
- Integration: Rate limiting, CORS, error handling
- E2E: Balance & transactions endpoints

### Unresolved Questions

1. Structured logging (loguru) - Skip for MVP
2. Token cache persistence - Skip (single-instance)
3. Request signing - Skip (read-only APIs)
4. Circuit breaker - Skip (retry sufficient)
5. OpenAPI export - Use FastAPI auto-docs

## Next Steps

**To implement**: Run plan phases sequentially, or request agent to begin Phase 1.

**To review**: Open plan file for detailed specs, code snippets, method signatures.

**To validate**: Use checklist in Phase 10 for manual testing & smoke tests.

---

**Plan Status**: Ready for implementation
**Principles**: YAGNI ✓, KISS ✓, DRY ✓
