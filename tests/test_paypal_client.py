"""PayPal client service tests."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest


def test_split_date_range_single_chunk():
    """Date range <= 31 days should return single chunk."""
    from app.services.paypal_client import PayPalClient

    client = PayPalClient()
    ranges = client._split_date_range("2024-01-01T00:00:00Z", "2024-01-31T23:59:59Z")

    assert len(ranges) == 1
    assert ranges[0][0] == "2024-01-01T00:00:00Z"
    assert "2024-01-31" in ranges[0][1]


def test_split_date_range_multiple_chunks():
    """Date range > 31 days should split into multiple chunks."""
    from app.services.paypal_client import PayPalClient

    client = PayPalClient()
    ranges = client._split_date_range("2024-01-01T00:00:00Z", "2024-03-15T23:59:59Z")

    # Jan 1 to Mar 15 = ~74 days, should be 3 chunks
    assert len(ranges) == 3

    # Verify first chunk
    assert ranges[0][0] == "2024-01-01T00:00:00Z"
    # First chunk should be ~31 days
    assert "2024-02-01" in ranges[0][1]


def test_split_date_range_exact_31_days():
    """Exactly 31 days should be single chunk."""
    from app.services.paypal_client import PayPalClient

    client = PayPalClient()
    ranges = client._split_date_range("2024-01-01T00:00:00Z", "2024-02-01T00:00:00Z")

    assert len(ranges) == 1


def test_split_date_range_100_days():
    """100 days should split into 4 chunks (31+31+31+7)."""
    from app.services.paypal_client import PayPalClient

    client = PayPalClient()
    ranges = client._split_date_range("2024-01-01T00:00:00Z", "2024-04-10T00:00:00Z")

    assert len(ranges) == 4


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
@patch("httpx.AsyncClient.request")
async def test_get_transactions_single_range(mock_request, mock_post):
    """Transactions <= 31 days should make single request."""
    from app.services.paypal_client import PayPalClient

    mock_post.return_value = AsyncMock(
        status_code=200,
        json=lambda: {"access_token": "test-token", "expires_in": 3600},
        raise_for_status=lambda: None,
    )

    mock_request.return_value = AsyncMock(
        status_code=200,
        json=lambda: {"transaction_details": [{"id": "TX1"}], "total_items": 1},
        raise_for_status=lambda: None,
    )

    client = PayPalClient()
    result = await client.get_transactions(
        "2024-01-01T00:00:00Z",
        "2024-01-15T00:00:00Z"
    )

    assert "transaction_details" in result
    assert len(result["transaction_details"]) == 1
    assert "_chunks" not in result  # No metadata for single request

    await client.close()


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
@patch("httpx.AsyncClient.request")
async def test_get_transactions_split_and_merge(mock_request, mock_post):
    """Transactions > 31 days should split, parallel fetch, and merge."""
    from app.services.paypal_client import PayPalClient

    mock_post.return_value = AsyncMock(
        status_code=200,
        json=lambda: {"access_token": "test-token", "expires_in": 3600},
        raise_for_status=lambda: None,
    )

    # Mock responses for 2 chunks
    mock_request.return_value = AsyncMock(
        status_code=200,
        json=lambda: {"transaction_details": [{"id": "TX1"}], "total_items": 1},
        raise_for_status=lambda: None,
    )

    client = PayPalClient()
    result = await client.get_transactions(
        "2024-01-01T00:00:00Z",
        "2024-02-20T00:00:00Z"  # 50 days = 2 chunks
    )

    assert "transaction_details" in result
    assert len(result["transaction_details"]) == 2  # 2 chunks merged
    assert result["_chunks"] == 2
    assert result["_date_range_days"] == 50

    await client.close()



@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_token_caching(mock_post):
    """Token should be cached and reused until expiry."""
    from app.services.paypal_client import PayPalClient

    # Mock successful token response
    mock_post.return_value = AsyncMock(
        json=lambda: {"access_token": "test-token", "expires_in": 3600},
        raise_for_status=lambda: None,
    )

    client = PayPalClient()
    token1 = await client._get_access_token()
    token2 = await client._get_access_token()

    assert token1 == token2 == "test-token"
    assert mock_post.call_count == 1  # Second call uses cache

    await client.close()


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_token_refresh_before_expiry(mock_post):
    """Token should be refreshed before actual expiry (60s buffer)."""
    from app.services.paypal_client import PayPalClient

    mock_post.return_value = AsyncMock(
        json=lambda: {"access_token": "new-token", "expires_in": 3600},
        raise_for_status=lambda: None,
    )

    client = PayPalClient()
    await client._get_access_token()

    # Manually expire the token
    cache_key = client._get_cache_key()
    client._token_cache[cache_key]["expires_at"] = 0

    # Should fetch new token
    new_token = await client._get_access_token()
    assert new_token == "new-token"
    assert mock_post.call_count == 2

    await client.close()


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
@patch("httpx.AsyncClient.request")
async def test_401_clears_cache_and_retries(mock_request, mock_post):
    """401 response should clear token cache and retry once."""
    from app.services.paypal_client import PayPalClient

    # Mock successful token response
    mock_post.return_value = AsyncMock(
        json=lambda: {"access_token": "test-token", "expires_in": 3600},
        raise_for_status=lambda: None,
    )

    # First API call returns 401, second succeeds
    mock_401_response = AsyncMock(status_code=401, json=lambda: {"error": "unauthorized"})
    mock_401_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Unauthorized",
        request=AsyncMock(),
        response=mock_401_response,
    )

    mock_success_response = AsyncMock(
        json=lambda: {"balances": []},
        raise_for_status=lambda: None,
        status_code=200,
    )

    mock_request.side_effect = [
        httpx.HTTPStatusError(
            "Unauthorized",
            request=AsyncMock(),
            response=mock_401_response,
        ),
        mock_success_response,
    ]

    client = PayPalClient()
    response = await client._request("GET", "/v1/reporting/balances")

    assert "balances" in response
    await client.close()


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_get_balances_calls_correct_endpoint(mock_post):
    """get_balances should call PayPal balances endpoint."""
    from app.services.paypal_client import PayPalClient

    # Mock token
    mock_post.return_value = AsyncMock(
        status_code=200,
        json=lambda: {"access_token": "token", "expires_in": 3600},
        raise_for_status=lambda: None,
    )

    # Mock balances request
    with patch("httpx.AsyncClient.request") as mock_request:
        mock_request.return_value = AsyncMock(
            status_code=200,
            json=lambda: {"balances": []},
            raise_for_status=lambda: None,
        )

        client = PayPalClient()
        await client.get_balances()

        # Verify correct endpoint was called
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert "balances" in call_args[1]["url"]

        await client.close()
