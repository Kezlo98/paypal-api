"""PayPal API routes - balance and transactions endpoints."""

import re
from typing import Any, Dict, List, Optional, Union

import httpx
from fastapi import APIRouter, HTTPException, Query, Request, status

from app.services.paypal_client import paypal_client
from app.services.rate_limiter import limiter

router = APIRouter(prefix="/api/v1/paypal", tags=["paypal"])


def to_snake_case(data: Union[Dict[str, Any], List[Any]]) -> Union[Dict[str, Any], List[Any]]:
    """
    Convert camelCase keys to snake_case recursively.

    PayPal uses camelCase; we normalize to snake_case for consistency.
    """
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
async def get_balance(request: Request):
    """
    Get PayPal account balance.

    Returns cached balance info from PayPal with camelCase converted to snake_case.
    """
    try:
        response = await paypal_client.get_balances()
        return to_snake_case(response)
    except httpx.HTTPStatusError as e:
        # Pass through PayPal error with original status code
        raise HTTPException(
            status_code=e.response.status_code,
            detail=e.response.json(),
        )
    except httpx.RequestError as e:
        # Network/service error
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "service_unavailable", "message": str(e)},
        )


@router.get("/transactions")
@limiter.limit("60/minute")
async def get_transactions(
    request: Request,
    start_date: str = Query(..., description="Start date (ISO 8601 format)"),
    end_date: str = Query(..., description="End date (ISO 8601 format)"),
    page: int = Query(1, ge=1, description="Page number (starts at 1)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    transaction_status: Optional[str] = Query(None, description="Filter by transaction status"),
):
    """
    Get PayPal transactions with pagination.

    Query parameters are forwarded directly to PayPal's reporting API.
    Response is normalized from camelCase to snake_case.
    """
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
        # Pass through PayPal error with original status code
        raise HTTPException(
            status_code=e.response.status_code,
            detail=e.response.json(),
        )
    except httpx.RequestError as e:
        # Network/service error
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "service_unavailable", "message": str(e)},
        )
