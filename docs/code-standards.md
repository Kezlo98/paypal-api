# Code Standards & Architecture

## Overview

This document defines coding standards, architectural patterns, and best practices for the PayPal API Service project.

## 1. Code Style & Formatting

### Python Standards

- **PEP 8 Compliance:** Follow Python Enhancement Proposal 8 style guide
- **Line Length:** Max 100 characters
- **Indentation:** 4 spaces (no tabs)
- **Imports:** Group in order (stdlib, third-party, local), separated by blank lines
- **Type Hints:** Required for all function parameters and return types
- **Docstrings:** Google-style docstrings for all public functions/classes

### Import Organization

```python
# Standard library
import json
from typing import Optional, Dict

# Third-party
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Local
from app.services.paypal_client import PayPalClient
from app.config import settings
```

### Type Hints Example

```python
def get_transactions(
    start_date: str,
    end_date: str,
    page: int = 1,
    page_size: int = 20
) -> Dict[str, Any]:
    """
    Fetch transactions from PayPal API.

    Args:
        start_date: ISO 8601 formatted start date
        end_date: ISO 8601 formatted end date
        page: Page number (1-indexed)
        page_size: Items per page (max 100)

    Returns:
        Dictionary with transaction data and pagination info

    Raises:
        ValueError: If date format is invalid
        HTTPException: If PayPal API returns error
    """
    pass
```

## 2. Naming Conventions

### Variables & Functions

- **snake_case** for variables, functions, and module names
- **UPPER_SNAKE_CASE** for constants
- **PascalCase** for classes and exceptions

```python
# Variables & functions
client_id = "abc123"
def get_account_balance():
    pass

# Constants
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30

# Classes
class PayPalClient:
    pass

class InvalidCredentialsError(Exception):
    pass
```

### API Response Keys

- **snake_case** in API responses (Python convention)
- PayPal API uses camelCase; normalize via `normalize_response()` utility

```python
# PayPal API response (camelCase)
{
    "accountNumber": "123456",
    "accountCurrency": "USD"
}

# Normalized response (snake_case)
{
    "account_number": "123456",
    "account_currency": "USD"
}
```

### File & Folder Structure

- **Module files:** snake_case (e.g., paypal_client.py, rate_limiter.py)
- **Folders:** snake_case (e.g., app/api/v1/, app/services/)
- **Tests:** test_*.py or *_test.py pattern

## 3. Project Structure

```
app/
├── main.py                          # FastAPI app initialization
├── config.py                        # Settings & validation
├── api/
│   └── v1/
│       └── paypal.py               # Route handlers
├── services/
│   ├── paypal_client.py            # PayPal API integration
│   ├── rate_limiter.py             # Rate limiting
│   └── exchange_rate_service.py    # Currency conversion
└── models/
    └── responses.py                 # Pydantic models

tests/
├── conftest.py                      # Pytest fixtures
├── test_main.py                     # FastAPI app tests
├── test_paypal_client.py            # PayPal client tests
└── test_rate_limiter.py             # Rate limiter tests

docs/                                # Documentation
static/                              # Frontend assets
```

### Module Responsibilities

| Module | Responsibility | Key Files |
|--------|---|---|
| **app.main** | FastAPI app setup, middleware, error handling | main.py |
| **app.config** | Environment validation, settings | config.py |
| **app.api.v1.paypal** | Route handlers for PayPal endpoints | api/v1/paypal.py |
| **app.services.paypal_client** | PayPal API client, OAuth, token management | services/paypal_client.py |
| **app.services.rate_limiter** | Per-IP request rate limiting | services/rate_limiter.py |
| **app.models.responses** | Pydantic response schemas | models/responses.py |

## 4. FastAPI Patterns

### Route Organization

```python
# app/api/v1/paypal.py
from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from app.services.paypal_client import PayPalClient
from app.models.responses import TransactionResponse

router = APIRouter(prefix="/api/v1/paypal", tags=["paypal"])
client = PayPalClient()

@router.get("/balance")
async def get_balance():
    """Get account balance."""
    try:
        balance = await client.get_balance()
        return balance
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/transactions")
async def list_transactions(
    start_date: str = Query(..., description="ISO 8601 start date"),
    end_date: str = Query(..., description="ISO 8601 end date"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """List PayPal transactions with pagination."""
    # Implementation
    pass
```

### Error Handling

```python
# Define custom exceptions
class PayPalError(Exception):
    """Base exception for PayPal API errors."""
    pass

class InvalidCredentialsError(PayPalError):
    """Raised when auth fails."""
    pass

class RateLimitError(PayPalError):
    """Raised when rate limit exceeded."""
    pass

# Use in route handlers
@router.get("/balance")
async def get_balance():
    try:
        return await client.get_balance()
    except InvalidCredentialsError:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    except RateLimitError:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    except PayPalError as e:
        raise HTTPException(status_code=503, detail=f"PayPal API error: {str(e)}")
```

### Response Models

```python
# app/models/responses.py
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class BalanceResponse(BaseModel):
    currency_code: str = Field(..., description="ISO 4217 currency code")
    total_balance: str = Field(..., description="Total account balance")
    available_balance: str = Field(..., description="Available balance")
    updated_at: datetime = Field(..., description="Last updated timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "currency_code": "USD",
                "total_balance": "1000.00",
                "available_balance": "950.00",
                "updated_at": "2025-12-30T10:00:00Z"
            }
        }

class TransactionResponse(BaseModel):
    transaction_id: str
    amount: str
    currency: str
    status: str
    transaction_date: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "transaction_id": "TXN123",
                "amount": "100.00",
                "currency": "USD",
                "status": "S",
                "transaction_date": "2025-12-30T10:00:00Z"
            }
        }
```

## 5. Async/Await Patterns

Use async patterns for I/O operations:

```python
# ✅ Good: Async HTTP client
import httpx

async def fetch_from_paypal(url: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=30.0)
        response.raise_for_status()
        return response.json()

# ✅ Good: Async route handler
@app.get("/transactions")
async def list_transactions():
    data = await fetch_from_paypal("https://api.paypal.com/...")
    return data

# ❌ Bad: Blocking I/O in async context
import requests
@app.get("/transactions")
async def list_transactions():
    data = requests.get("https://api.paypal.com/...")  # Blocks event loop!
    return data
```

## 6. Testing Standards

### Test Organization

```
tests/
├── conftest.py                 # Shared fixtures
├── test_main.py               # FastAPI app tests
├── test_paypal_client.py      # PayPal client tests
└── test_rate_limiter.py       # Rate limiter tests
```

### Test Template

```python
# tests/test_paypal_client.py
import pytest
from app.services.paypal_client import PayPalClient
from app.config import settings

class TestPayPalClient:
    @pytest.fixture
    def client(self):
        """Create client with test credentials."""
        return PayPalClient(
            client_id="test_id",
            client_secret="test_secret",
            mode="sandbox"
        )

    def test_get_balance_success(self, client, mocker):
        """Test successful balance retrieval."""
        mock_response = {"balance": "1000.00", "currency": "USD"}
        mocker.patch.object(client, '_request', return_value=mock_response)

        result = client.get_balance()

        assert result["balance"] == "1000.00"

    def test_get_balance_invalid_credentials(self, client, mocker):
        """Test error handling for invalid credentials."""
        mocker.patch.object(client, '_request', side_effect=InvalidCredentialsError())

        with pytest.raises(InvalidCredentialsError):
            client.get_balance()

    @pytest.mark.asyncio
    async def test_token_refresh(self, client):
        """Test automatic token refresh."""
        # Async test example
        pass
```

### Coverage Requirements

- **Minimum:** 80% overall coverage
- **Critical paths:** 100% (auth, payment processing)
- **Integration tests:** Required for PayPal API calls
- **Run tests:** `pytest --cov=app tests/`

## 7. Security Patterns

### Environment Variables

```python
# ✅ Good: Load from environment
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    paypal_client_id: str
    paypal_client_secret: str
    paypal_mode: str = "sandbox"

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()

# ❌ Bad: Hardcoded secrets
CLIENT_ID = "abc123"
CLIENT_SECRET = "xyz789"
```

### Never Log Secrets

```python
# ✅ Good: Mask sensitive data
import logging

logger = logging.getLogger(__name__)

def authenticate(client_id: str, client_secret: str):
    logger.info(f"Authenticating client {client_id[:4]}****")
    # Process auth

# ❌ Bad: Logs full credentials
logger.info(f"Using credentials: {client_id}:{client_secret}")
```

### Input Validation

```python
from pydantic import BaseModel, Field, validator
from datetime import datetime

class TransactionQuery(BaseModel):
    start_date: str = Field(..., regex=r"^\d{4}-\d{2}-\d{2}$")
    end_date: str = Field(..., regex=r"^\d{4}-\d{2}-\d{2}$")

    @validator('start_date', 'end_date')
    def validate_dates(cls, v):
        try:
            datetime.fromisoformat(v)
        except ValueError:
            raise ValueError("Must be ISO 8601 format")
        return v
```

## 8. Error Handling

### Exception Hierarchy

```python
class PayPalError(Exception):
    """Base exception."""
    pass

class InvalidCredentialsError(PayPalError):
    """Auth failure."""
    pass

class RateLimitError(PayPalError):
    """Rate limit exceeded."""
    pass

class PayPalAPIError(PayPalError):
    """PayPal API returned error."""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"PayPal API error ({status_code}): {message}")
```

### Retry Logic

```python
import asyncio
from typing import Callable, TypeVar, Any

T = TypeVar('T')

async def retry_with_backoff(
    func: Callable[..., T],
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    **kwargs
) -> T:
    """Retry function with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return await func(**kwargs)
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            wait_time = backoff_factor ** attempt
            await asyncio.sleep(wait_time)
```

## 9. Configuration Management

### Environment-Specific Config

```python
# app/config.py
from pydantic_settings import BaseSettings
from typing import Literal

class Settings(BaseSettings):
    # Core
    app_name: str = "PayPal API Service"
    app_version: str = "1.0.0"
    debug: bool = False

    # PayPal
    paypal_client_id: str
    paypal_client_secret: str
    paypal_mode: Literal["sandbox", "live"] = "sandbox"

    # Server
    port: int = 8000
    workers: int = 1

    # Features
    rate_limit_per_minute: int = 60
    token_refresh_buffer: int = 60  # seconds
    request_timeout: int = 30
    max_retries: int = 3

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
```

## 10. Logging Standards

### Structured Logging

```python
import logging
import json
from datetime import datetime

class JsonFormatter(logging.Formatter):
    """JSON log formatter."""
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data)

# Setup
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logger.addHandler(handler)
```

### Log Levels

| Level | Use Case |
|-------|----------|
| **DEBUG** | Variable states, flow tracing |
| **INFO** | Request starts, API responses |
| **WARNING** | Retries, degraded service |
| **ERROR** | Exceptions, failures |
| **CRITICAL** | Auth failures, security issues |

## 11. Docker Standards

### Image Best Practices

- Multi-stage build (builder + runtime stages)
- Non-root user execution
- Health checks included
- Minimal base images (python:3.11-slim)
- .dockerignore properly configured

### Dockerfile Requirements

```dockerfile
# ✅ Must have:
FROM python:3.11-slim          # Minimal base
RUN useradd -m appuser          # Non-root user
USER appuser                     # Switch user
HEALTHCHECK --interval=30s ...   # Health check
ENV PYTHONUNBUFFERED=1          # Direct logs
```

## 12. Documentation Standards

### Docstring Format (Google Style)

```python
def calculate_balance(transactions: List[dict]) -> float:
    """Calculate total balance from transactions.

    Args:
        transactions: List of transaction dictionaries with 'amount' key

    Returns:
        Total balance as float

    Raises:
        ValueError: If transaction amount is invalid
        TypeError: If transactions is not a list

    Example:
        >>> calculate_balance([{"amount": 100}, {"amount": 50}])
        150.0
    """
    pass
```

### README Structure

- Project description
- Quick start (dev & docker)
- Environment variables
- API endpoints
- Project structure
- Testing instructions
- Troubleshooting

## 13. Git Workflow & Commits

### Commit Message Format

```
[TYPE] Brief description (50 chars max)

Longer explanation if needed (72 char wrap).

Fixes #123
```

**Types:** feat, fix, docs, refactor, test, chore, security

### Branch Naming

- Feature: `feature/description`
- Fix: `fix/description`
- Docs: `docs/description`
- Example: `feature/oauth2-token-caching`

## 14. Performance Guidelines

### Caching Strategy

- **Token cache:** In-memory with TTL
- **Response cache:** Not implemented (read-only, always fresh)
- **Connection pooling:** Use httpx.AsyncClient

### Database Considerations

- Current: Stateless (no DB)
- Future: PostgreSQL for audit logs (Phase 03+)
- Never sync I/O in async context

### Optimization Checklist

- [ ] Use async/await for I/O
- [ ] Connection pooling for HTTP
- [ ] Token caching with refresh buffer
- [ ] Configured worker count for load
- [ ] Query pagination (max 100 items)

## 15. Code Review Checklist

Before submitting PR:

- [ ] Follows PEP 8 & naming conventions
- [ ] Type hints on all functions
- [ ] Tests written & passing (80%+ coverage)
- [ ] Docstrings added (Google format)
- [ ] No hardcoded secrets
- [ ] Error handling complete
- [ ] Documentation updated
- [ ] Commit messages clear
- [ ] No console.log/print (production code)

## 16. Deprecation Policy

- **Deprecation notice:** Log warnings for 2 versions minimum
- **Removal:** Only in major version changes
- **Communicating:** Document in release notes

```python
import warnings

def old_function():
    """Deprecated function."""
    warnings.warn(
        "old_function is deprecated, use new_function instead",
        DeprecationWarning,
        stacklevel=2
    )
```

