"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1.paypal import router as paypal_router
from app.config import settings
from app.services.paypal_client import paypal_client
from app.services.rate_limiter import limiter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager - cleanup on shutdown."""
    logging.info(f"Starting PayPal API service (mode: {settings.paypal_mode})")
    logging.info(f"PayPal base URL: {settings.paypal_base_url}")
    yield
    await paypal_client.close()
    logging.info("PayPal API service stopped")


app = FastAPI(
    title="PayPal API",
    description="Read-only PayPal Reporting API wrapper with rate limiting",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS - Same origin only (localhost for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:*", "http://127.0.0.1:*"],
    allow_methods=["GET"],
    allow_headers=["*"],
    allow_credentials=True,
)

# Rate limiting integration
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Include API routes
app.include_router(paypal_router)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}
