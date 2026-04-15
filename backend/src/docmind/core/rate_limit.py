"""
docmind/core/rate_limit.py

Simple in-memory rate limiter for token validation failures.
Prevents brute-force token guessing by tracking failed attempts per key.
"""

import time
import threading
from collections import defaultdict

from docmind.core.config import get_settings


class TokenRateLimiter:
    """In-memory sliding-window rate limiter for token validation failures."""

    def __init__(self, max_failures: int = 10, window_seconds: int = 300) -> None:
        self._max_failures = max_failures
        self._window = window_seconds
        self._failures: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def record_failure(self, key: str) -> None:
        """Record a failed validation attempt."""
        now = time.monotonic()
        with self._lock:
            self._failures[key].append(now)

    def is_blocked(self, key: str) -> bool:
        """Check if key has exceeded failure threshold in the current window."""
        now = time.monotonic()
        cutoff = now - self._window
        with self._lock:
            attempts = self._failures.get(key, [])
            recent = [t for t in attempts if t > cutoff]
            self._failures[key] = recent
            return len(recent) >= self._max_failures

    def reset(self, key: str) -> None:
        """Clear failures for a key (e.g. after successful validation)."""
        with self._lock:
            self._failures.pop(key, None)


# Module-level singleton
_limiter: TokenRateLimiter | None = None


def get_token_rate_limiter() -> TokenRateLimiter:
    """Get or create the global rate limiter instance."""
    global _limiter
    if _limiter is None:
        _limiter = TokenRateLimiter()
    return _limiter
