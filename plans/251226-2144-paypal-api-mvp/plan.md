---
title: "PayPal API MVP - FastAPI Read-Only Reporting Service"
description: "Python 3.11 + FastAPI service exposing PayPal balances & transactions with OAuth2, rate limiting, & caching"
status: pending
priority: P1
effort: 6h
branch: main
tags: [fastapi, paypal, oauth2, rate-limiting, python-311]
created: 2025-12-26
---

## Implementation Plan: PayPal API MVP

### Overview
Build minimal FastAPI service (2 endpoints) wrapping PayPal Reporting APIs with OAuth2 client credentials, in-memory token caching, rate limiting (60 req/min), retry logic, & sandbox/live mode switching.

**Total Effort**: ~6 hours
**Principles**: YAGNI, KISS, DRY - No repositories, no complex abstractions

---

## Phase 1: Project Setup (30 min)

### 1.1 Create Project Structure

**Create directories:**
```bash
mkdir -p app/api/v1 app/services app/models tests
touch app/__init__.py app/api/__init__.py app/api/v1/__init__.py app/services/__init__.py app/models/__init__.py tests/__init__.py
```

**Dependencies** - Create `requirements.txt`:
```
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
httpx>=0.28.0
pydantic>=2.10.0
pydantic-settings>=2.6.0
slowapi>=0.1.9
python-dotenv>=1.0.0
pytest>=8.0.0
pytest-asyncio>=0.24.0
pytest-cov>=4.0.0
```

**Create `pyproject.toml`**:
```toml
[project]
name = "paypal-api"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "httpx>=0.28.0",
    "pydantic>=2.10.0",
    "pydantic-settings>=2.6.0",
    "slowapi>=0.1.9",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=4.0.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

**Create `.env.example`**:
```env
PAYPAL_CLIENT_ID=your_client_id
PAYPAL_CLIENT_SECRET=your_client_secret
PAYPAL_MODE=sandbox
PORT=8000
RATE_LIMIT_PER_MINUTE=60
```

---

## Phase 2: Configuration Layer (45 min)

### 2.1 Create `app/config.py`

**Purpose**: Centralized env var management with Pydantic Settings

**Full implementation**:
```python
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    paypal_client_id: str = Field(..., description="PayPal OAuth2 client ID")
    paypal_client_secret: str = Field(..., description="PayPal OAuth2 client secret")
    paypal_mode: str = Field("sandbox", description="PayPal environment: sandbox or live")

    port: int = Field(8000, description="Application port")
    rate_limit_per_minute: int = Field(60, description="Rate limit per IP per minute")

    # PayPal API base URLs
    @property
    def paypal_base_url(self) -> str:
        if self.paypal_mode == "live":
            return "https://api-m.paypal.com"
        return "https://api-m.sandbox.paypal.com"

    @field_validator("paypal_mode")
    @classmethod
    def validate_paypal_mode(cls, v: str) -> str:
        if v not in ("sandbox", "live"):
            raise ValueError('PAYPAL_MODE must be "sandbox" or "live"')
        return v


settings = Settings()
```

**Dependencies**: None
**Tests**:
- Valid mode (sandbox/live) loads correctly
- Invalid mode raises ValueError
- Properties return correct base URLs

---

## Phase 3: PayPal Client Service (2h)

### 3.1 Create `app/services/paypal_client.py`

**Purpose**: httpx wrapper for PayPal API with OAuth2 flow, token caching, auto-refresh, retry logic

**Full implementation**:
```python
import time
from typing import Any

import httpx
from app.config import settings


class PayPalClient:
    """PayPal API client with OAuth2 and in-memory token caching."""

    def __init__(self) -> None:
        self._token_cache: dict[str, dict[str, Any]] = {}
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(5.0),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )

    async def close(self) -> None:
        await self._client.aclose()

    def _get_cache_key(self) -> str:
        return settings.paypal_mode

    async def _get_access_token(self) -> str:
        cache_key = self._get_cache_key()
        cached = self._token_cache.get(cache_key)

        now = int(time.time())
        if cached and cached["expires_at"] > now:
            return cached["token"]

        auth = httpx.BasicAuth(
            username=settings.paypal_client_id,
            password=settings.paypal_client_secret,
        )

        response = await self._client.post(
            f"{settings.paypal_base_url}/v1/oauth2/token",
            auth=auth,
            data={"grant_type": "client_credentials"},
        )
        response.raise_for_status()

        data = response.json()
        token = data["access_token"]
        expires_in = data.get("expires_in", 32400)

        # 60s buffer to refresh before expiry
        self._token_cache[cache_key] = {
            "token": token,
            "expires_at": now + expires_in - 60,
        }

        return token

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        max_retries = 3
        base_delay = 0.5

        for attempt in range(max_retries):
            try:
                token = await self._get_access_token()
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                }

                response = await self._client.request(
                    method=method,
                    url=f"{settings.paypal_base_url}{path}",
                    headers=headers,
                    params=params,
                )

                if response.status_code == 401 and attempt == 0:
                    # Clear cache and retry once
                    cache_key = self._get_cache_key()
                    self._token_cache.pop(cache_key, None)
                    continue

                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401 and attempt == 0:
                    continue
                raise
            except httpx.RequestError as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(base_delay * (2**attempt))
                    continue
                raise

        raise RuntimeError("Max retries exceeded")

    async def get_balances(self) -> dict[str, Any]:
        return await self._request("GET", "/v1/reporting/balances")

    async def get_transactions(
        self,
        start_date: str,
        end_date: str,
        page: int = 1,
        page_size: int = 20,
        transaction_status: str | None = None,
    ) -> dict[str, Any]:
        params = {
            "start_date": start_date,
            "end_date": end_date,
            "page": page,
            "page_size": page_size,
        }
        if transaction_status:
            params["transaction_status"] = transaction_status

        return await self._request("GET", "/v1/reporting/transactions", params=params)


# Singleton instance
paypal_client = PayPalClient()
```

**Note**: Add `import asyncio` at top

**Dependencies**: `app.config.settings`
**Tests**:
- Token cache stores and retrieves tokens
- Token refreshes before expiry (60s buffer)
- 401 clears cache and retries
- Retry logic on network errors (exponential backoff)
- get_balances() calls correct endpoint
- get_transactions() passes query params correctly

---

## Phase 4: Rate Limiter Service (30 min)

### 4.1 Create `app/services/rate_limiter.py`

**Purpose**: slowapi middleware for 60 req/min per IP

**Full implementation**:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
```

**Dependencies**: `slowapi`
**Tests**: Integration only (tested via API endpoints)

---

## Phase 5: Response Models (30 min)

### 5.1 Create `app/models/responses.py`

**Purpose**: Minimal Pydantic schemas for type safety

**Full implementation**:
```python
from pydantic import BaseModel


class BalanceResponse(BaseModel):
    """PayPal balance response (minimal wrapper)."""

    pass  # Let raw PayPal dict pass through


class TransactionResponse(BaseModel):
    """PayPal transaction response (minimal wrapper)."""

    pass  # Let raw PayPal dict pass through


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str
    message: str
```

**Note**: Using raw dict passthrough (YAGNI - no need for full schemas)

**Dependencies**: None
**Tests**: Basic schema validation

---

## Phase 6: API Routes (1h)

### 6.1 Create `app/api/v1/paypal.py`

**Purpose**: FastAPI route handlers for balance & transactions

**Full implementation**:
```python
import re
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from slowapi import _rate_limit_exceeded_handler

from app.services.paypal_client import paypal_client
from app.services.rate_limiter import limiter

router = APIRouter(prefix="/api/v1/paypal", tags=["paypal"])


def to_snake_case(data: dict[str, Any] | list[Any]) -> dict[str, Any] | list[Any]:
    """Convert camelCase keys to snake_case recursively."""
    if isinstance(data, list):
        return [to_snake_case(item) for item in data]
    if isinstance(data, dict):
        return {
            re.sub(r"(?<!^)(?=[A-Z])", "_", k).lower(): to_snake_case(v)
            for k, v in data.items()
        }
    return data


@router.get("/balance")
@limiter.limit("60/minute")
async def get_balance():
    """Get PayPal account balance."""
    try:
        response = await paypal_client.get_balances()
        return to_snake_case(response)
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=e.response.json(),
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "service_unavailable", "message": str(e)},
        )


@router.get("/transactions")
@limiter.limit("60/minute")
async def get_transactions(
    start_date: str = Query(..., description="Start date (ISO 8601)"),
    end_date: str = Query(..., description="End date (ISO 8601)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    transaction_status: str | None = Query(None, description="Filter by status"),
):
    """Get PayPal transactions with pagination."""
    try:
        response = await paypal_client.get_transactions(
            start_date=start_date,
            end_date=end_date,
            page=page,
            page_size=page_size,
            transaction_status=transaction_status,
        )
        return to_snake_case(response)
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=e.response.json(),
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "service_unavailable", "message": str(e)},
        )
```

**Note**: Add `import httpx` at top

**Dependencies**: `app.services.paypal_client`, `app.services.rate_limiter`
**Tests**:
- GET /balance returns snake_case response
- GET /transactions forwards query params correctly
- Rate limit 429 response after 60 req/min
- PayPal errors pass through correctly
- Network errors return 503

---

## Phase 7: FastAPI App Setup (30 min)

### 7.1 Create `app/main.py`

**Purpose**: FastAPI app initialization with CORS & middleware

**Full implementation**:
```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded

from app.api.v1.paypal import router as paypal_router
from app.services.paypal_client import paypal_client
from app.services.rate_limiter import limiter


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await paypal_client.close()


app = FastAPI(
    title="PayPal API",
    description="Read-only PayPal Reporting API wrapper",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS - Same origin only
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:*", "http://127.0.0.1:*"],
    allow_methods=["GET"],
    allow_headers=["*"],
    allow_credentials=True,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, limiter._rate_limit_exceeded_handler)

# Routes
app.include_router(paypal_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
```

**Dependencies**: All modules
**Tests**:
- Health endpoint returns 200
- CORS blocks non-origin requests
- Lifespan closes httpx client

---

## Phase 8: Test Suite (1h)

### 8.1 Create `tests/conftest.py`

**Full implementation**:
```python
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
```

### 8.2 Create `tests/test_api.py`

**Full implementation**:
```python
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status


@pytest.mark.asyncio
async def test_health_endpoint(async_client):
    response = await async_client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
@patch("app.api.v1.paypal.paypal_client.get_balances")
async def test_get_balance_success(mock_get_balances, async_client):
    mock_get_balances.return_value = {
        "balances": [{"currency": "USD", "available_amount": "100.00"}]
    }

    response = await async_client.get("/api/v1/paypal/balance")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "balances" in data


@pytest.mark.asyncio
@patch("app.api.v1.paypal.paypal_client.get_transactions")
async def test_get_transactions_success(mock_get_transactions, async_client):
    mock_get_transactions.return_value = {
        "transaction_details": [],
        "total_items": 0,
        "total_pages": 0,
    }

    response = await async_client.get(
        "/api/v1/paypal/transactions",
        params={
            "start_date": "2024-01-01T00:00:00Z",
            "end_date": "2024-01-31T23:59:59Z",
            "page": 1,
            "page_size": 20,
        },
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "transaction_details" in data


@pytest.mark.asyncio
async def test_rate_limiting(async_client):
    # Make 61 requests (exceeds 60/min)
    responses = []
    for _ in range(61):
        responses.append(await async_client.get("/health"))

    # At least one should be rate limited
    rate_limited = [r for r in responses if r.status_code == status.HTTP_429_TOO_MANY_REQUESTS]
    assert len(rate_limited) > 0
```

### 8.3 Create `tests/test_paypal_client.py`

**Full implementation**:
```python
from unittest.mock import AsyncMock, patch

import pytest
import httpx


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_token_caching(mock_post):
    from app.services.paypal_client import PayPalClient

    mock_post.return_value = AsyncMock(
        json=lambda: {"access_token": "test-token", "expires_in": 3600},
        raise_for_status=lambda: None,
    )

    client = PayPalClient()
    token1 = await client._get_access_token()
    token2 = await client._get_access_token()

    assert token1 == token2
    assert mock_post.call_count == 1  # Second call uses cache

    await client.close()


@pytest.mark.asyncio
@patch("httpx.AsyncClient.request")
async def test_retry_on_401(mock_request):
    from app.services.paypal_client import PayPalClient

    # First call returns 401, second succeeds
    mock_request.side_effect = [
        httpx.HTTPStatusError(
            "Unauthorized",
            request=AsyncMock(),
            response=AsyncMock(status_code=401),
        ),
        AsyncMock(
            json=lambda: {"balances": []},
            raise_for_status=lambda: None,
        ),
    ]

    client = PayPalClient()
    response = await client._request("GET", "/v1/reporting/balances")

    assert "balances" in response
    await client.close()
```

---

## Phase 9: Documentation (15 min)

### 9.1 Create `README.md`

```markdown
# PayPal API Service

FastAPI wrapper for PayPal Reporting APIs (read-only).

## Setup

```bash
# Install deps
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your PayPal credentials

# Run
uvicorn app.main:app --reload --port $PORT
```

## Endpoints

- `GET /api/v1/paypal/balance` - Account balance
- `GET /api/v1/paypal/transactions` - Transactions (paginated)

## Env Vars

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| PAYPAL_CLIENT_ID | Yes | - | PayPal OAuth2 client ID |
| PAYPAL_CLIENT_SECRET | Yes | - | PayPal OAuth2 client secret |
| PAYPAL_MODE | No | sandbox | sandbox or live |
| PORT | No | 8000 | Server port |
| RATE_LIMIT_PER_MINUTE | No | 60 | Rate limit per IP |

## Rate Limiting

60 requests per minute per IP (configurable).

## Running Tests

```bash
pytest --cov=app tests/
```
```

---

## Phase 10: Validation Checklist (15 min)

### Manual Testing

1. **Startup**:
   - [ ] Server starts on PORT=8000
   - [ ] Health check returns 200
   - [ ] Invalid PAYPAL_MODE raises error on startup

2. **OAuth2 Flow**:
   - [ ] Token cached correctly
   - [ ] Token refreshes before expiry
   - [ ] 401 clears cache and retries

3. **Endpoints**:
   - [ ] GET /balance returns PayPal data
   - [ ] GET /transactions with query params works
   - [ ] Pagination params forwarded correctly

4. **Rate Limiting**:
   - [ ] 61st request returns 429
   - [ ] X-RateLimit headers present

5. **Error Handling**:
   - [ ] PayPal errors pass through with original status
   - [ ] Network errors return 503

6. **Tests**:
   - [ ] All tests pass: `pytest --cov=app`
   - [ ] Coverage > 80%

7. **CORS**:
   - [ ] Same-origin requests allowed
   - [ ] Cross-origin requests blocked

---

## Implementation Order

**Sequential (no parallelization needed)**:

1. Project structure + requirements (30 min)
2. config.py (45 min)
3. paypal_client.py (2h)
4. rate_limiter.py (30 min)
5. responses.py (30 min)
6. paypal.py routes (1h)
7. main.py app setup (30 min)
8. Test suite (1h)
9. README (15 min)
10. Validation (15 min)

**Total**: ~6 hours

---

## Unresolved Questions

- Q1: Should we add structured logging (e.g., loguru) or skip for MVP?
- Q2: Do we need database persistence for token cache (horizontal scaling)?
- Q3: Should we add request signing validation (webhook security)?
- Q4: Do we need OpenAPI spec export separate from FastAPI auto-docs?
- Q5: Should we implement circuit breaker pattern for PayPal outages?

**Recommendation**: Skip all for MVP (YAGNI). Add only if production demands.
