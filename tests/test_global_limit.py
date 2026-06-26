"""
Tests for GlobalLimiter.
"""

import pytest

from chainshield.core.global_limit import GlobalLimiter
from chainshield.storage.memory import MemoryStorage


@pytest.fixture
def storage():
    return MemoryStorage()


@pytest.fixture
def limiter(storage):
    return GlobalLimiter(storage, global_max_requests=20, window_size=60)


class TestGlobalLimiter:
    def test_initially_allows_requests(self, limiter):
        allowed, _ = limiter.check(now=1000.0)
        assert allowed is True

    def test_blocks_at_limit(self, limiter):
        now = 1000.0
        for _ in range(20):
            allowed, state = limiter.check(now=now)
            assert allowed is True
            limiter.record_accepted(state)

        allowed, _ = limiter.check(now=now)
        assert allowed is False

    def test_global_window_resets(self, limiter):
        now = 1000.0
        for _ in range(20):
            _, state = limiter.check(now=now)
            limiter.record_accepted(state)

        future = now + 61
        allowed, _ = limiter.check(now=future)
        assert allowed is True

    def test_current_count_property(self, limiter):
        assert limiter.current_count == 0
        _, state = limiter.check(now=1000.0)
        limiter.record_accepted(state)
        assert limiter.current_count == 1

    def test_remaining_capacity(self, limiter):
        assert limiter.remaining_capacity == 20
        now = 1000.0
        for _ in range(5):
            _, state = limiter.check(now=now)
            limiter.record_accepted(state)
        assert limiter.remaining_capacity == 15

    def test_remaining_capacity_at_zero(self, limiter):
        now = 1000.0
        for _ in range(20):
            _, state = limiter.check(now=now)
            limiter.record_accepted(state)
        assert limiter.remaining_capacity == 0

    def test_invalid_config(self, storage):
        with pytest.raises(ValueError):
            GlobalLimiter(storage, global_max_requests=0)
