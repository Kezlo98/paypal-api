"""PayPal API client with OAuth2 and in-memory token caching."""

import asyncio
import json
import logging
import time
import traceback
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.config import settings

# Configure logging
logger = logging.getLogger(__name__)

# PayPal API constants
MAX_DATE_RANGE_DAYS = 31
MAX_CONCURRENT_REQUESTS = 2


def _log_error_details(
    logger_instance: logging.Logger,
    error_type: str,
    url: str,
    method: str = "GET",
    params: Optional[Dict[str, Any]] = None,
    status_code: Optional[int] = None,
    response_body: Optional[str] = None,
    exception: Optional[Exception] = None,
    extra_context: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Log detailed error information for debugging.

    Args:
        logger_instance: Logger instance to use
        error_type: Type of error (e.g., "HTTPStatusError", "RequestError")
        url: Request URL
        method: HTTP method
        params: Query parameters
        status_code: HTTP status code (if available)
        response_body: Response body text (if available)
        exception: Exception object (if available)
        extra_context: Additional context data
    """
    error_details = {
        "error_type": error_type,
        "method": method,
        "url": url,
        "timestamp": datetime.utcnow().isoformat(),
    }

    if params:
        # Mask sensitive data in params
        safe_params = {k: v for k, v in params.items()}
        error_details["params"] = safe_params

    if status_code:
        error_details["status_code"] = status_code

    if response_body:
        try:
            # Try to parse as JSON for better formatting
            parsed = json.loads(response_body)
            error_details["response"] = parsed

            # Extract PayPal debug_id if available
            if isinstance(parsed, dict) and "debug_id" in parsed:
                error_details["paypal_debug_id"] = parsed["debug_id"]

            # Extract error details if available
            if isinstance(parsed, dict) and "details" in parsed:
                error_details["error_details"] = parsed["details"]
        except (json.JSONDecodeError, TypeError):
            # If not JSON, log as text (truncate if too long)
            error_details["response_text"] = response_body[:1000]

    if exception:
        error_details["exception_type"] = type(exception).__name__
        error_details["exception_message"] = str(exception)
        # Add stack trace for debugging
        error_details["traceback"] = traceback.format_exc()

    if extra_context:
        error_details.update(extra_context)

    # Log as formatted JSON for easy parsing
    logger_instance.error(
        f"PayPal API Error - {error_type}",
        extra={"error_details": json.dumps(error_details, indent=2)},
    )

    # Also log a simplified one-liner for quick scanning
    summary = f"{error_type}: {method} {url}"
    if status_code:
        summary += f" -> {status_code}"
    if exception:
        summary += f" ({type(exception).__name__}: {str(exception)})"
    logger_instance.error(summary)


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

        try:
            response = await self._client.post(
                token_url,
                auth=auth,
                data={"grant_type": "client_credentials"},
            )

            logger.info(f"Token response status: {response.status_code}")

            if response.status_code != 200:
                logger.error(f"Token request failed: {response.status_code} - {response.text}")
                # Log detailed error information
                _log_error_details(
                    logger_instance=logger,
                    error_type="TokenAuthenticationError",
                    url=token_url,
                    method="POST",
                    status_code=response.status_code,
                    response_body=response.text,
                    extra_context={
                        "mode": cache_key,
                        "client_id_prefix": settings.paypal_client_id[:10],
                    },
                )

            response.raise_for_status()

            data = response.json()
            token = data["access_token"]
            expires_in = data.get("expires_in", 32400)  # PayPal default: 9 hours

            logger.info(f"Token obtained, expires_in: {expires_in}s")

        except httpx.HTTPStatusError as e:
            _log_error_details(
                logger_instance=logger,
                error_type="TokenHTTPStatusError",
                url=token_url,
                method="POST",
                status_code=e.response.status_code,
                response_body=e.response.text,
                exception=e,
                extra_context={"mode": cache_key},
            )
            raise
        except httpx.RequestError as e:
            _log_error_details(
                logger_instance=logger,
                error_type="TokenRequestError",
                url=token_url,
                method="POST",
                exception=e,
                extra_context={"mode": cache_key},
            )
            raise
        except Exception as e:
            _log_error_details(
                logger_instance=logger,
                error_type="TokenUnexpectedError",
                url=token_url,
                method="POST",
                exception=e,
                extra_context={"mode": cache_key},
            )
            raise

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
                    # Log detailed error information
                    _log_error_details(
                        logger_instance=logger,
                        error_type="PayPalAPIError",
                        url=url,
                        method=method,
                        params=params,
                        status_code=response.status_code,
                        response_body=response.text,
                        extra_context={
                            "attempt": attempt + 1,
                            "max_retries": max_retries,
                            "mode": settings.paypal_mode,
                        },
                    )

                response.raise_for_status()
                logger.info(f"Request successful")
                return response.json()

            except httpx.HTTPStatusError as e:
                # Retry 401 once after clearing cache
                if e.response.status_code == 401 and attempt == 0:
                    continue

                # Log detailed error with full context
                _log_error_details(
                    logger_instance=logger,
                    error_type="HTTPStatusError",
                    url=url,
                    method=method,
                    params=params,
                    status_code=e.response.status_code,
                    response_body=e.response.text,
                    exception=e,
                    extra_context={
                        "attempt": attempt + 1,
                        "max_retries": max_retries,
                        "mode": settings.paypal_mode,
                        "will_retry": False,
                    },
                )
                raise

            except httpx.RequestError as e:
                will_retry = attempt < max_retries - 1

                # Log detailed network error
                _log_error_details(
                    logger_instance=logger,
                    error_type="RequestError",
                    url=url,
                    method=method,
                    params=params,
                    exception=e,
                    extra_context={
                        "attempt": attempt + 1,
                        "max_retries": max_retries,
                        "will_retry": will_retry,
                        "retry_delay": base_delay * (2**attempt) if will_retry else None,
                        "mode": settings.paypal_mode,
                    },
                )

                # Retry network errors with exponential backoff
                if will_retry:
                    await asyncio.sleep(base_delay * (2**attempt))
                    continue
                raise

            except Exception as e:
                # Log any unexpected errors
                _log_error_details(
                    logger_instance=logger,
                    error_type="UnexpectedError",
                    url=url,
                    method=method,
                    params=params,
                    exception=e,
                    extra_context={
                        "attempt": attempt + 1,
                        "max_retries": max_retries,
                        "mode": settings.paypal_mode,
                    },
                )
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
        try:
            # Check if date range needs splitting
            start = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            days_diff = (end - start).days

        except (ValueError, AttributeError) as e:
            # Log invalid date format error
            logger.error(f"Invalid date format - start_date: {start_date}, end_date: {end_date}")
            _log_error_details(
                logger_instance=logger,
                error_type="InvalidDateFormatError",
                url="/v1/reporting/transactions",
                method="GET",
                params={
                    "start_date": start_date,
                    "end_date": end_date,
                    "page": page,
                    "page_size": page_size,
                },
                exception=e,
                extra_context={
                    "transaction_status": transaction_status,
                    "expected_format": "ISO 8601 (YYYY-MM-DDTHH:MM:SSZ)",
                },
            )
            raise ValueError(
                f"Invalid date format. Expected ISO 8601 (e.g., '2025-12-29T21:00:00Z'). "
                f"Got start_date={start_date}, end_date={end_date}"
            ) from e

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

        try:
            results = await asyncio.gather(*[fetch_with_semaphore(rng) for rng in date_ranges])

            # Merge results
            all_transactions = []
            total_items = 0

            for i, result in enumerate(results):
                if result and "transaction_details" in result:
                    all_transactions.extend(result["transaction_details"])
                if result and "total_items" in result:
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

        except Exception as e:
            # Log error during parallel chunk fetching
            logger.error(f"Error during parallel chunk fetching: {e}")
            _log_error_details(
                logger_instance=logger,
                error_type="ParallelFetchError",
                url="/v1/reporting/transactions",
                method="GET",
                params={
                    "start_date": start_date,
                    "end_date": end_date,
                    "page": page,
                    "page_size": page_size,
                },
                exception=e,
                extra_context={
                    "total_chunks": len(date_ranges),
                    "date_ranges": [{"start": r[0], "end": r[1]} for r in date_ranges],
                    "days_diff": days_diff,
                    "transaction_status": transaction_status,
                },
            )
            raise


# Singleton instance for use across the app
paypal_client = PayPalClient()
