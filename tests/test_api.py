"""API endpoint tests."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status


@pytest.mark.asyncio
async def test_health_endpoint(async_client):
    """Health check should return 200 OK."""
    response = await async_client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
@patch("app.api.v1.paypal.paypal_client.get_balances")
async def test_get_balance_success(mock_get_balances, async_client):
    """GET /balance should return PayPal data with snake_case keys."""
    mock_get_balances.return_value = {
        "balances": [{"currency": "USD", "availableAmount": "100.00"}]
    }

    response = await async_client.get("/api/v1/paypal/balance")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "balances" in data
    # Check snake_case conversion
    assert "available_amount" in data["balances"][0]


@pytest.mark.asyncio
@patch("app.api.v1.paypal.paypal_client.get_transactions")
async def test_get_transactions_success(mock_get_transactions, async_client):
    """GET /transactions should forward query params to PayPal."""
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
    mock_get_transactions.assert_called_once_with(
        start_date="2024-01-01T00:00:00Z",
        end_date="2024-01-31T23:59:59Z",
        page=1,
        page_size=20,
        transaction_status=None,
    )


@pytest.mark.asyncio
@patch("app.api.v1.paypal.paypal_client.get_transactions")
async def test_get_transactions_with_status_filter(mock_get_transactions, async_client):
    """GET /transactions should pass transaction_status param to PayPal."""
    mock_get_transactions.return_value = {"transaction_details": [], "total_items": 0}

    response = await async_client.get(
        "/api/v1/paypal/transactions",
        params={
            "start_date": "2024-01-01T00:00:00Z",
            "end_date": "2024-01-31T23:59:59Z",
            "transaction_status": "S",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    mock_get_transactions.assert_called_once()
    # Verify transaction_status was passed
    call_kwargs = mock_get_transactions.call_args.kwargs
    assert call_kwargs["transaction_status"] == "S"


@pytest.mark.asyncio
@patch("app.api.v1.paypal.paypal_client.get_balances")
async def test_rate_limiting(mock_get_balances, async_client):
    """Requests exceeding 60/minute should return 429."""
    mock_get_balances.return_value = {"balances": []}

    responses = []
    for _ in range(61):
        responses.append(await async_client.get("/api/v1/paypal/balance"))

    rate_limited = [r for r in responses if r.status_code == status.HTTP_429_TOO_MANY_REQUESTS]
    assert len(rate_limited) > 0, "Expected some requests to be rate limited"
