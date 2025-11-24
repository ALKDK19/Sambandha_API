"""
Rate limiting utilities for API endpoints
"""
import time
from collections import defaultdict
from typing import Dict, Optional
from fastapi import HTTPException, Request


class RateLimiter:
    def __init__(self):
        self.requests: Dict[str, list] = defaultdict(list)

    def is_allowed(self, identifier: str, max_requests: int, window_seconds: int) -> bool:
        """Check if request is allowed based on rate limits"""
        now = time.time()
        # Clean old requests
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier]
            if now - req_time < window_seconds
        ]

        # Check if limit exceeded
        if len(self.requests[identifier]) >= max_requests:
            return False

        # Add current request
        self.requests[identifier].append(now)
        return True


# Global rate limiter instance
rate_limiter = RateLimiter()


def check_rate_limit(request: Request, max_requests: int = 10, window_seconds: int = 60):
    """Rate limiting dependency for FastAPI routes"""
    client_ip = request.client.host
    if not rate_limiter.is_allowed(client_ip, max_requests, window_seconds):
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please try again later."
        )
