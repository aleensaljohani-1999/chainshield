"""
Tests for SlidingWindowRateLimiter.
"""

import pytest

from chainshield.core.rate_limiter import SlidingWindowRateLimiter
from chainshield.models import IdentityState
from chainshield.storage.memory import MemoryStorage


@pytest.fixture
def storage():
    return MemoryStorage()


@pytest.fixture
def limiter(storage):
    return SlidingWindowRateLimiter(storage, max_requests=5, window_size=60)


class TestSlidingWindowBasic:
    def test_first_request_allowed(self, limiter):
        allowed, _ = limiter.check("user-1", now=1000.0)
        assert allowed is True

    def test_requests_within_limit_are_allowed(self, limiter):
        now = 1000.0
        for _ in range(5):
            allowed, state = limiter.check("user-1", now=now)
            assert allowed is True
            limiter.record_accepted(state, now=now)

    def test_sixth_request_blocked(self, limiter):
        now = 1000.0
        for _ in range(5):
            allowed, state = limiter.check("user-1", now=now)
            limiter.record_accepted(state, now=now)
        allowed, _ = limiter.check("user-1", now=now)
        assert allowed is False

    def test_different_identities_are_independent(self, limiter):
        now = 1000.0
        for _ in range(5):
            _, state = limiter.check("user-a", now=now)
            limiter.record_accepted(state, now=now)

        # user-a exhausted; user-b should still be free
        allowed, _ = limiter.check("user-b", now=now)
        assert allowed is True

    def test_window_reset_allows_new_requests(self, limiter):
        now = 1000.0
        for _ in range(5):
            _, state = limiter.check("user-1", now=now)
            limiter.record_accepted(state, now=now)

        # Advance past the 60-second window
        future = now + 61
        allowed, _ = limiter.check("user-1", now=future)
        assert allowed is True

    def test_remaining_decrements_correctly(self, limiter):
        now = 1000.0
        assert limiter.remaining("user-1", now=now) == 5
        _, state = limiter.check("user-1", now=now)
        limiter.record_accepted(state, now=now)
        assert limiter.remaining("user-1", now=now) == 4

    def test_window_boundary_exact(self, limiter):
        """Request at exactly window_start + window_size should NOT reset."""
        now = 1000.0
        for _ in range(5):
            _, state = limiter.check("user-1", now=now)
            limiter.record_accepted(state, now=now)

        at_boundary = now + 60  # exactly == window_start + window_size
        allowed, _ = limiter.check("user-1", now=at_boundary)
        assert allowed is False  # still in same window

    def test_window_boundary_just_after(self, limiter):
        now = 1000.0
        for _ in range(5):
            _, state = limiter.check("user-1", now=now)
            limiter.record_accepted(state, now=now)

        just_after = now + 60.001
        allowed, _ = limiter.check("user-1", now=just_after)
        assert allowed is True


class TestSlidingWindowConfig:
    def test_invalid_max_requests(self, storage):
        with pytest.raises(ValueError):
            SlidingWindowRateLimiter(storage, max_requests=0)

    def test_invalid_window_size(self, storage):
        with pytest.raises(ValueError):
            SlidingWindowRateLimiter(storage, window_size=0)

    def test_custom_limit(self, storage):
        limiter = SlidingWindowRateLimiter(storage, max_requests=2, window_size=60)
        now = 1000.0
        for _ in range(2):
            _, state = limiter.check("u", now=now)
            limiter.record_accepted(state, now=now)
        allowed, _ = limiter.check("u", now=now)
        assert allowed is False
