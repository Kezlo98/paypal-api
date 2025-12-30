"""PayPal API routes - balance and transactions endpoints."""

import logging
import re
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union

import httpx
from fastapi import APIRouter, HTTPException, Query, Request, status

from app.services.exchange_rate_service import exchange_rate_service
from app.services.paypal_client import paypal_client
from app.services.rate_limiter import limiter

router = APIRouter(prefix="/api/v1/paypal", tags=["paypal"])
logger = logging.getLogger(__name__)


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


def mask_transaction_ids(transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Mask the last 5 characters of transaction IDs for security.

    Replaces last 5 characters with asterisks (e.g., ABC123DEF456GHI789 -> ABC123DEF456GH*****)

    Args:
        transactions: List of transaction dicts

    Returns:
        List of transactions with masked transaction IDs
    """
    for tx in transactions:
        try:
            # Mask transaction_info.transaction_id
            if "transaction_info" in tx and "transaction_id" in tx["transaction_info"]:
                tx_id = tx["transaction_info"]["transaction_id"]
                if tx_id and len(tx_id) > 5:
                    # Keep all but last 5 chars, replace last 5 with asterisks
                    tx["transaction_info"]["transaction_id"] = tx_id[:-5] + "*****"

            # Also mask top-level transaction_id if exists
            if "transaction_id" in tx:
                tx_id = tx["transaction_id"]
                if tx_id and len(tx_id) > 5:
                    tx["transaction_id"] = tx_id[:-5] + "*****"

        except Exception as e:
            logger.warning(f"Failed to mask transaction ID: {e}")

    return transactions


async def add_usd_conversion(transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Add USD conversion to transactions.

    Adds 'amount_usd' field to each transaction's transaction_info.

    Args:
        transactions: List of transaction dicts

    Returns:
        List of transactions with USD amounts added
    """
    for tx in transactions:
        try:
            # Extract transaction info
            tx_info = tx.get("transaction_info", {})
            tx_amount = tx_info.get("transaction_amount", {})

            # Get amount and currency
            amount_value = tx_amount.get("value")
            currency_code = tx_amount.get("currency_code", "USD")

            if amount_value is not None:
                # Convert to USD
                amount_float = float(amount_value)
                usd_amount = await exchange_rate_service.convert_to_usd(
                    amount_float, currency_code
                )

                # Add USD amount to transaction_amount
                tx_amount["value_usd"] = float(usd_amount)
                tx_amount["original_currency"] = currency_code

                logger.debug(
                    f"Converted {amount_value} {currency_code} to {usd_amount} USD"
                )

        except Exception as e:
            # Log error but don't fail the whole request
            logger.warning(f"Failed to convert transaction to USD: {e}")
            # Add null value to indicate conversion failed
            if "transaction_info" in tx and "transaction_amount" in tx["transaction_info"]:
                tx["transaction_info"]["transaction_amount"]["value_usd"] = None

    return transactions


async def add_usd_conversion_to_balance(balance_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add USD conversion to balance data.

    Args:
        balance_data: Balance response from PayPal

    Returns:
        Balance data with USD amounts added
    """
    try:
        # Extract balances array
        balances = balance_data.get("balances", [])

        for balance in balances:
            # Get total balance info
            total_balance = balance.get("total_balance", {})
            available_balance = balance.get("available_balance", {})

            # Convert total_balance to USD
            if total_balance:
                value = total_balance.get("value")
                currency_code = total_balance.get("currency_code", "USD")

                if value is not None:
                    value_float = float(value)
                    usd_amount = await exchange_rate_service.convert_to_usd(
                        value_float, currency_code
                    )
                    total_balance["value_usd"] = float(usd_amount)
                    total_balance["original_currency"] = currency_code

            # Convert available_balance to USD
            if available_balance:
                value = available_balance.get("value")
                currency_code = available_balance.get("currency_code", "USD")

                if value is not None:
                    value_float = float(value)
                    usd_amount = await exchange_rate_service.convert_to_usd(
                        value_float, currency_code
                    )
                    available_balance["value_usd"] = float(usd_amount)
                    available_balance["original_currency"] = currency_code

        balance_data["_usd_conversion_enabled"] = True

    except Exception as e:
        logger.warning(f"Failed to convert balance to USD: {e}")

    return balance_data


@router.get("/balance")
@limiter.limit("60/minute")
async def get_balance(
    request: Request,
    convert_to_usd: bool = Query(True, description="Convert amounts to USD"),
):
    """
    Get PayPal account balance with optional USD conversion.

    Returns cached balance info from PayPal with camelCase converted to snake_case.
    If convert_to_usd=true, adds value_usd field to balance amounts.
    """
    try:
        response = await paypal_client.get_balances()

        # Add USD conversion if requested
        if convert_to_usd:
            response = await add_usd_conversion_to_balance(response)

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
    convert_to_usd: bool = Query(True, description="Convert amounts to USD"),
):
    """
    Get PayPal transactions with pagination and optional USD conversion.

    Query parameters are forwarded directly to PayPal's reporting API.
    Response is normalized from camelCase to snake_case.
    If convert_to_usd=true, adds value_usd field to each transaction.
    """
    try:
        response = await paypal_client.get_transactions(
            start_date=start_date,
            end_date=end_date,
            page=page,
            page_size=page_size,
            transaction_status=transaction_status,
        )

        # Add USD conversion if requested
        if convert_to_usd and "transaction_details" in response:
            transactions = response["transaction_details"]
            await add_usd_conversion(transactions)
            response["transaction_details"] = transactions
            response["_usd_conversion_enabled"] = True

        # Mask transaction IDs for security (last 5 characters)
        if "transaction_details" in response:
            transactions = response["transaction_details"]
            mask_transaction_ids(transactions)
            response["transaction_details"] = transactions

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
