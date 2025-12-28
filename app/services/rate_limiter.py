"""Rate limiting middleware using slowapi."""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Rate limiter instance - limits requests per IP address
limiter = Limiter(key_func=get_remote_address)
