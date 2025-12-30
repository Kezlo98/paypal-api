"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1.paypal import router as paypal_router
from app.config import settings
from app.services.exchange_rate_service import exchange_rate_service
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
    logging.info("Exchange rate service initialized (using Frankfurter API)")
    yield
    await paypal_client.close()
    await exchange_rate_service.close()
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

# Mount static directories for frontend assets
app.mount("/assets", StaticFiles(directory="static/assets"), name="assets")
app.mount("/data", StaticFiles(directory="static/data"), name="data")

# Include API routes
app.include_router(paypal_router)


@app.get("/")
async def serve_index():
    """Serve portfolio homepage."""
    return FileResponse("static/index.html")


@app.get("/index.html")
async def serve_index_html():
    """Serve portfolio homepage (index.html route)."""
    return FileResponse("static/index.html")


@app.get("/journey.html")
async def serve_journey():
    """Serve career journey page."""
    return FileResponse("static/journey.html")


@app.get("/finance.html")
async def serve_finance():
    """Serve PayPal finance dashboard."""
    return FileResponse("static/finance.html")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}
