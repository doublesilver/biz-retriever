"""
Rate Limiting Service
Implements rate limiting for API endpoints
"""

from typing import Callable

import redis
from fastapi import HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["100/hour"])


class RateLimiter:
    """Custom rate limiter with Redis backend"""

    def __init__(self):
        try:
            self.redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                decode_responses=True,
            )
            self.enabled = True
        except Exception:
            self.enabled = False

    def check_rate_limit(
        self, key: str, max_requests: int = 10, window_seconds: int = 60
    ) -> bool:
        """
        Check if request is within rate limit

        Args:
            key: Unique identifier (e.g., IP address, user ID)
            max_requests: Maximum requests allowed
            window_seconds: Time window in seconds

        Returns:
            True if within limit, False otherwise
        """
        if not self.enabled:
            return True

        try:
            current = self.redis_client.get(key)

            if current is None:
                # First request in window
                self.redis_client.setex(key, window_seconds, 1)
                return True

            if int(current) >= max_requests:
                return False

            # Increment counter
            self.redis_client.incr(key)
            return True

        except Exception:
            # If Redis fails, allow request
            return True

    def get_remaining(self, key: str, max_requests: int = 10) -> int:
        """Get remaining requests in current window"""
        if not self.enabled:
            return max_requests

        try:
            current = self.redis_client.get(key)
            if current is None:
                return max_requests
            return max(0, max_requests - int(current))
        except Exception:
            return max_requests


# Global instance
rate_limiter = RateLimiter()


def rate_limit(max_requests: int = 10, window_seconds: int = 60):
    """
    Decorator for rate limiting endpoints

    Usage:
        @app.get("/api/endpoint")
        @rate_limit(max_requests=5, window_seconds=60)
        async def endpoint(request: Request):
            ...
    """

    def decorator(func: Callable):
        async def wrapper(request: Request, *args, **kwargs):
            # Get client identifier
            client_id = get_remote_address(request)
            key = f"rate_limit:{func.__name__}:{client_id}"

            # Check rate limit
            if not rate_limiter.check_rate_limit(key, max_requests, window_seconds):
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded. Max {max_requests} requests per {window_seconds} seconds.",
                )

            # Add rate limit headers
            remaining = rate_limiter.get_remaining(key, max_requests)

            # Call original function
            response = await func(request, *args, **kwargs)

            # Add headers if response supports it
            if hasattr(response, "headers"):
                response.headers["X-RateLimit-Limit"] = str(max_requests)
                response.headers["X-RateLimit-Remaining"] = str(remaining)

            return response

        return wrapper

    return decorator
