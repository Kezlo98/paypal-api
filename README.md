# PayPal API Service

FastAPI wrapper for PayPal Reporting APIs (read-only) with OAuth2, token caching, and rate limiting.

## Features

- **OAuth2 Client Credentials** - Automatic token management with in-memory caching
- **Rate Limiting** - 60 requests/minute per IP (configurable)
- **Sandbox & Live** - Easy mode switching via environment variable
- **Retry Logic** - Up to 3 retries with exponential backoff
- **Response Normalization** - camelCase to snake_case conversion
- **Auto Token Refresh** - 60-second buffer before expiry

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your PayPal credentials

# Run development server
uvicorn app.main:app --reload --port $PORT

# Access Swagger docs
open http://localhost:8000/docs
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PAYPAL_CLIENT_ID` | Yes | - | PayPal OAuth2 client ID |
| `PAYPAL_CLIENT_SECRET` | Yes | - | PayPal OAuth2 client secret |
| `PAYPAL_MODE` | No | `sandbox` | PayPal environment: `sandbox` or `live` |
| `PORT` | No | `8000` | Server port |
| `RATE_LIMIT_PER_MINUTE` | No | `60` | Rate limit per IP per minute |

## API Endpoints

### GET /health
Health check endpoint.

### GET /api/v1/paypal/balance
Get PayPal account balance.

**Response:** PayPal balance data with snake_case keys

### GET /api/v1/paypal/transactions
Get PayPal transactions with pagination.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `start_date` | string | Yes | Start date (ISO 8601) |
| `end_date` | string | Yes | End date (ISO 8601) |
| `page` | integer | No | Page number (default: 1) |
| `page_size` | integer | No | Items per page (default: 20, max: 100) |
| `transaction_status` | string | No | Filter by transaction status |

**Response:** Transaction data with pagination info

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
├── tests/                   # pytest tests
├── requirements.txt
├── .env.example
└── README.md
```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/
```

## Rate Limiting

Requests are limited to 60 per minute per IP address. When exceeded:

- **Status:** 429 Too Many Requests
- **Headers:** `X-RateLimit-Remaining`, `X-RateLimit-Reset`

## Error Handling

- **PayPal errors (4xx/5xx):** Passed through with original status code and body
- **Network errors:** Returns 503 Service Unavailable
- **Rate limit:** Returns 429 Too Many Requests

## Docker Deployment

Production-ready Docker image (220MB) with multi-stage build, security hardening, and health checks.

### Quick Docker Run

```bash
docker build -t paypal-api:latest .

docker run -d \
  --name paypal-api \
  -p 8000:8000 \
  -e PAYPAL_CLIENT_ID=your_id \
  -e PAYPAL_CLIENT_SECRET=your_secret \
  -e PAYPAL_MODE=sandbox \
  paypal-api:latest
```

### Key Features

- **Multi-stage build:** 220MB final image
- **Security:** Non-root user (appuser), minimal base image
- **Health check:** Built-in Python http.client
- **Configurable:** PORT and WORKERS environment variables
- **Production-ready:** Restart policy, proper signal handling

### Full Documentation

See [deployment-guide.md](./docs/deployment-guide.md) for:
- Environment variables and configuration
- Docker Compose setup
- Security best practices
- Performance tuning
- Troubleshooting guide

## License

MIT
