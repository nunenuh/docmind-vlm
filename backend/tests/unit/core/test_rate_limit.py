"""Unit tests for the token rate limiter."""

import time
from unittest.mock import patch

from docmind.core.rate_limit import TokenRateLimiter


class TestTokenRateLimiter:
    def test_allows_under_threshold(self):
        limiter = TokenRateLimiter(max_failures=5, window_seconds=60)
        for _ in range(4):
            limiter.record_failure("key1")
        assert limiter.is_blocked("key1") is False

    def test_blocks_at_threshold(self):
        limiter = TokenRateLimiter(max_failures=5, window_seconds=60)
        for _ in range(5):
            limiter.record_failure("key1")
        assert limiter.is_blocked("key1") is True

    def test_different_keys_tracked_independently(self):
        limiter = TokenRateLimiter(max_failures=3, window_seconds=60)
        for _ in range(3):
            limiter.record_failure("key_a")
        assert limiter.is_blocked("key_a") is True
        assert limiter.is_blocked("key_b") is False

    def test_resets_after_window_expires(self):
        limiter = TokenRateLimiter(max_failures=3, window_seconds=1)
        for _ in range(3):
            limiter.record_failure("key1")
        assert limiter.is_blocked("key1") is True
        time.sleep(1.1)
        assert limiter.is_blocked("key1") is False

    def test_reset_clears_failures(self):
        limiter = TokenRateLimiter(max_failures=3, window_seconds=60)
        for _ in range(3):
            limiter.record_failure("key1")
        assert limiter.is_blocked("key1") is True
        limiter.reset("key1")
        assert limiter.is_blocked("key1") is False

    def test_new_key_is_not_blocked(self):
        limiter = TokenRateLimiter(max_failures=5, window_seconds=60)
        assert limiter.is_blocked("never_seen") is False
