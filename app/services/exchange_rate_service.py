"""Exchange rate service using Frankfurter API for currency conversion."""

import logging
import time
from decimal import Decimal
from typing import Any, Dict, Optional

import httpx

# Configure logging
logger = logging.getLogger(__name__)

# Frankfurter API base URL (free, no API key required)
FRANKFURTER_BASE_URL = "https://api.frankfurter.app"

# Cache exchange rates for 1 hour (3600 seconds)
CACHE_TTL_SECONDS = 3600


class ExchangeRateService:
    """
    Currency exchange rate service using Frankfurter API.

    Features:
    - Free API, no authentication required
    - Real-time ECB exchange rates
    - 1-hour caching to minimize API calls
    - Support for 30+ currencies
    """

    def __init__(self) -> None:
        """Initialize exchange rate service with cache."""
        # Rate cache: {currency: {"rate": Decimal, "timestamp": int}}
        self._rate_cache: Dict[str, Dict[str, Any]] = {}
        # httpx client with 5s timeout
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(5.0))

    async def close(self) -> None:
        """Close the httpx client (call on app shutdown)."""
        await self._client.aclose()

    def _is_cache_valid(self, currency: str) -> bool:
        """Check if cached rate for currency is still valid."""
        if currency not in self._rate_cache:
            return False

        cached = self._rate_cache[currency]
        now = int(time.time())
        return cached["timestamp"] + CACHE_TTL_SECONDS > now

    async def _fetch_rate_from_api(self, from_currency: str, to_currency: str = "USD") -> Decimal:
        """
        Fetch exchange rate from Frankfurter API.

        Args:
            from_currency: Source currency code (e.g., "EUR")
            to_currency: Target currency code (default: "USD")

        Returns:
            Exchange rate as Decimal

        Raises:
            httpx.HTTPStatusError: If API returns error
            httpx.RequestError: On network errors
        """
        # Handle USD to USD case
        if from_currency == to_currency:
            return Decimal("1.0")

        url = f"{FRANKFURTER_BASE_URL}/latest"
        params = {"from": from_currency, "to": to_currency}

        logger.info(f"Fetching exchange rate: {from_currency} -> {to_currency}")

        try:
            response = await self._client.get(url, params=params)
            response.raise_for_status()

            data = response.json()

            # Extract rate from response
            # Response format: {"amount": 1.0, "base": "EUR", "date": "2025-12-29", "rates": {"USD": 1.234}}
            rate = data.get("rates", {}).get(to_currency)

            if rate is None:
                raise ValueError(f"Rate for {to_currency} not found in API response")

            logger.info(f"Rate fetched: {from_currency} -> {to_currency} = {rate}")
            return Decimal(str(rate))

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Exchange rate API error: {e.response.status_code} - {e.response.text}"
            )
            raise
        except httpx.RequestError as e:
            logger.error(f"Network error fetching exchange rate: {e}")
            raise
        except (KeyError, ValueError) as e:
            logger.error(f"Error parsing exchange rate response: {e}")
            raise

    async def get_rate_to_usd(self, from_currency: str) -> Decimal:
        """
        Get exchange rate from currency to USD.

        Uses cache if available and valid, otherwise fetches from API.

        Args:
            from_currency: Source currency code (e.g., "EUR", "GBP")

        Returns:
            Exchange rate to USD as Decimal

        Examples:
            >>> rate = await service.get_rate_to_usd("EUR")
            >>> print(rate)  # 1.234
        """
        # Normalize currency code
        from_currency = from_currency.upper()

        # Check cache
        if self._is_cache_valid(from_currency):
            logger.info(f"Cache hit for {from_currency}")
            return self._rate_cache[from_currency]["rate"]

        # Fetch from API
        logger.info(f"Cache miss for {from_currency}, fetching from API")
        rate = await self._fetch_rate_from_api(from_currency, "USD")

        # Update cache
        self._rate_cache[from_currency] = {
            "rate": rate,
            "timestamp": int(time.time()),
        }

        return rate

    async def convert_to_usd(self, amount: float, from_currency: str) -> Decimal:
        """
        Convert amount from currency to USD.

        Args:
            amount: Amount to convert
            from_currency: Source currency code

        Returns:
            Converted amount in USD as Decimal

        Examples:
            >>> usd_amount = await service.convert_to_usd(100, "EUR")
            >>> print(usd_amount)  # 123.40
        """
        # Handle USD directly
        if from_currency.upper() == "USD":
            return Decimal(str(amount))

        rate = await self.get_rate_to_usd(from_currency)
        converted = Decimal(str(amount)) * rate

        # Round to 2 decimal places for currency
        return converted.quantize(Decimal("0.01"))

    def clear_cache(self) -> None:
        """Clear the exchange rate cache."""
        self._rate_cache.clear()
        logger.info("Exchange rate cache cleared")


# Singleton instance for use across the app
exchange_rate_service = ExchangeRateService()
