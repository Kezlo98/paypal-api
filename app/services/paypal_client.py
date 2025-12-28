"""PayPal API client with OAuth2 and in-memory token caching."""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.config import settings

# Configure logging
logger = logging.getLogger(__name__)

# PayPal API constants
MAX_DATE_RANGE_DAYS = 31
MAX_CONCURRENT_REQUESTS = 100


class PayPalClient:
    """PayPal API client with OAuth2 client credentials flow and token caching."""

    def __init__(self) -> None:
        """Initialize client with in-memory token cache and httpx async client."""
        # Token cache: {mode: {"token": str, "expires_at": int}}
        self._token_cache: Dict[str, Dict[str, Any]] = {}
        # httpx client with 5s timeout and connection pooling
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(5.0),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )

    async def close(self) -> None:
        """Close the httpx client (call on app shutdown)."""
        await self._client.aclose()

    def _get_cache_key(self) -> str:
        """Get cache key based on current PayPal mode."""
        return settings.paypal_mode

    async def _get_access_token(self) -> str:
        """
        Get OAuth2 access token from cache or fetch new one.

        Returns cached token if valid, otherwise fetches new token from PayPal.
        Token refreshed 60s before expiry to prevent edge cases.
        """
        cache_key = self._get_cache_key()
        cached = self._token_cache.get(cache_key)

        now = int(time.time())
        if cached and cached["expires_at"] > now:
            logger.info(f"Token cache hit (mode: {cache_key})")
            return cached["token"]

        logger.info(f"Fetching new token from PayPal (mode: {cache_key})")
        logger.debug(f"PayPal base URL: {settings.paypal_base_url}")
        logger.debug(f"Client ID: {settings.paypal_client_id[:10]}...{settings.paypal_client_id[-4:]}")

        # Fetch new token with basic auth
        auth = httpx.BasicAuth(
            username=settings.paypal_client_id,
            password=settings.paypal_client_secret,
        )

        token_url = f"{settings.paypal_base_url}/v1/oauth2/token"
        logger.info(f"POST {token_url}")

        response = await self._client.post(
            token_url,
            auth=auth,
            data={"grant_type": "client_credentials"},
        )

        logger.info(f"Token response status: {response.status_code}")

        if response.status_code != 200:
            logger.error(f"Token request failed: {response.status_code} - {response.text}")

        response.raise_for_status()

        data = response.json()
        token = data["access_token"]
        expires_in = data.get("expires_in", 32400)  # PayPal default: 9 hours

        logger.info(f"Token obtained, expires_in: {expires_in}s")

        # Cache with 60s buffer to refresh before actual expiry
        self._token_cache[cache_key] = {
            "token": token,
            "expires_at": now + expires_in - 60,
        }

        return token

    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Make authenticated request to PayPal API with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: API path (e.g., /v1/reporting/balances)
            params: Query parameters

        Returns:
            JSON response as dict

        Raises:
            httpx.HTTPStatusError: On 4xx/5xx responses
            httpx.RequestError: On network errors after retries
            RuntimeError: If max retries exceeded
        """
        max_retries = 3
        base_delay = 0.5

        url = f"{settings.paypal_base_url}{path}"
        logger.info(f"{method} {url} (attempt {1}/{max_retries})")
        if params:
            logger.debug(f"Query params: {params}")

        for attempt in range(max_retries):
            try:
                token = await self._get_access_token()
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                }

                response = await self._client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                )

                logger.info(f"Response status: {response.status_code} (attempt {attempt + 1}/{max_retries})")

                # Handle 401: clear cache and retry once
                if response.status_code == 401 and attempt == 0:
                    logger.warning("Got 401, clearing token cache and retrying...")
                    cache_key = self._get_cache_key()
                    self._token_cache.pop(cache_key, None)
                    continue

                # Log error responses for debugging
                if response.status_code >= 400:
                    logger.error(f"PayPal API error {response.status_code}: {response.text[:500]}")

                response.raise_for_status()
                logger.info(f"Request successful")
                return response.json()

            except httpx.HTTPStatusError as e:
                # Retry 401 once after clearing cache
                if e.response.status_code == 401 and attempt == 0:
                    continue
                logger.error(f"HTTPStatusError: {e.response.status_code} - {e.response.text[:300]}")
                raise
            except httpx.RequestError as e:
                logger.error(f"RequestError (attempt {attempt + 1}): {e}")
                # Retry network errors with exponential backoff
                if attempt < max_retries - 1:
                    await asyncio.sleep(base_delay * (2**attempt))
                    continue
                raise

        raise RuntimeError("Max retries exceeded")

    async def get_balances(self) -> Dict[str, Any]:
        """Get PayPal account balances."""
        return await self._request("GET", "/v1/reporting/balances")

    def _split_date_range(self, start_date: str, end_date: str) -> List[Tuple[str, str]]:
        """
        Split date range into chunks of MAX_DATE_RANGE_DAYS.

        Args:
            start_date: ISO 8601 start date
            end_date: ISO 8601 end date

        Returns:
            List of (start_date, end_date) tuples
        """
        start = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))

        ranges = []
        current_start = start

        while current_start < end:
            # Calculate end of current chunk (max 31 days)
            current_end = min(current_start + timedelta(days=MAX_DATE_RANGE_DAYS), end)

            # Format as ISO 8601
            range_start = current_start.strftime("%Y-%m-%dT%H:%M:%SZ")
            range_end = current_end.strftime("%Y-%m-%dT%H:%M:%SZ")

            ranges.append((range_start, range_end))
            logger.debug(f"Date range chunk: {range_start} to {range_end}")

            # Move to next chunk
            current_start = current_end

        logger.info(f"Split date range into {len(ranges)} chunks (max {MAX_DATE_RANGE_DAYS} days each)")
        return ranges

    async def _get_transactions_chunk(
        self,
        start_date: str,
        end_date: str,
        page: int,
        page_size: int,
        transaction_status: Optional[str],
    ) -> Dict[str, Any]:
        """Get transactions for a single date range chunk."""
        params = {
            "start_date": start_date,
            "end_date": end_date,
            "page": page,
            "page_size": page_size,
        }
        if transaction_status:
            params["transaction_status"] = transaction_status

        return await self._request("GET", "/v1/reporting/transactions", params=params)

    async def get_transactions(
        self,
        start_date: str,
        end_date: str,
        page: int = 1,
        page_size: int = 20,
        transaction_status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get PayPal transactions with automatic date range splitting.

        Automatically splits date ranges > 31 days into multiple parallel requests
        and merges the results.

        Args:
            start_date: ISO 8601 start date
            end_date: ISO 8601 end date
            page: Page number (default: 1)
            page_size: Items per page (default: 20)
            transaction_status: Optional filter by status

        Returns:
            Merged transaction response with all transactions
        """
        # Check if date range needs splitting
        start = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        days_diff = (end - start).days

        if days_diff <= MAX_DATE_RANGE_DAYS:
            # Single request sufficient
            logger.info(f"Date range is {days_diff} days, single request")
            return await self._get_transactions_chunk(
                start_date, end_date, page, page_size, transaction_status
            )

        # Split into chunks and make parallel requests
        logger.info(f"Date range is {days_diff} days, splitting into chunks")
        date_ranges = self._split_date_range(start_date, end_date)

        # Limit concurrent requests
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

        async def fetch_with_semaphore(rng: Tuple[str, str]) -> Dict[str, Any]:
            async with semaphore:
                return await self._get_transactions_chunk(
                    rng[0], rng[1], page, page_size, transaction_status
                )

        # Fetch all chunks in parallel
        logger.info(f"Fetching {len(date_ranges)} chunks with max {MAX_CONCURRENT_REQUESTS} concurrent")
        results = await asyncio.gather(*[fetch_with_semaphore(rng) for rng in date_ranges])

        # Merge results
        all_transactions = []
        total_items = 0

        for result in results:
            if "transaction_details" in result:
                all_transactions.extend(result["transaction_details"])
            if "total_items" in result:
                total_items += result.get("total_items", 0)

        merged_response = {
            "transaction_details": all_transactions,
            "total_items": total_items,
            "total_pages": 1,  # Merged result, pagination info not meaningful
            "_chunks": len(date_ranges),  # Metadata: number of chunks merged
            "_date_range_days": days_diff,  # Metadata: original date range in days
        }

        logger.info(f"Merged {len(date_ranges)} chunks: {len(all_transactions)} transactions total")

        return merged_response


# Singleton instance for use across the app
paypal_client = PayPalClient()
