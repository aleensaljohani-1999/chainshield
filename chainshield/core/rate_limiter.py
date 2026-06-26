"""
Sliding-window per-identity rate limiter.

Design rationale
----------------
A cumulative counter (count-forever) permanently penalizes legitimate users
who simply happen to be active over many days. The sliding window fixes this
by resetting the counter once the observation window has passed, so only
*recent* behaviour is judged.

Algorithm
---------
For each identity track (request_count, window_start).

On every request:
  1. If now > window_start + window_size  →  reset counter and window_start.
  2. If request_count >= max_requests     →  deny and trigger blacklist.
  3. Otherwise                            →  increment counter and allow.

Time complexity : O(1) per check
Space complexity: O(n) where n = number of distinct identities seen
"""

import time
from typing import Optional

from chainshield.models import IdentityState
from chainshield.storage.base import BaseStorage


class SlidingWindowRateLimiter:
    """
    Per-identity sliding-window rate limiter.

    Parameters
    ----------
    storage:
        Storage backend (MemoryStorage or any BaseStorage implementation).
    max_requests:
        Maximum number of requests allowed per identity within one window.
    window_size:
        Duration of the observation window in seconds.
    """

    def __init__(
        self,
        storage: BaseStorage,
        max_requests: int = 5,
        window_size: int = 60,
    ) -> None:
        if max_requests < 1:
            raise ValueError("max_requests must be >= 1")
        if window_size < 1:
            raise ValueError("window_size must be >= 1 second")

        self.storage = storage
        self.max_requests = max_requests
        self.window_size = window_size

    def check(self, identity: str, now: Optional[float] = None) -> tuple[bool, IdentityState]:
        """
        Evaluate whether the identity may proceed.

        Returns
        -------
        (allowed, state)
            allowed  – True if the request is within the rate limit.
            state    – The updated IdentityState after evaluation.

        Notes
        -----
        This method does NOT increment the counter on its own. Call
        `record_accepted` after you have confirmed the request is fully allowed
        (i.e. blacklist check also passed). This separation of concerns lets
        the Guardian run all checks before committing any state change.
        """
        t = now or time.time()
        state = self.storage.get_identity(identity)

        if state is None:
            state = IdentityState(identity=identity, window_start=t)

        if state.is_window_expired(self.window_size, t):
            state.reset_window(t)

        allowed = state.request_count < self.max_requests
        return allowed, state

    def record_accepted(self, state: IdentityState, now: Optional[float] = None) -> None:
        """Increment the request counter and persist state."""
        state.request_count += 1
        self.storage.set_identity(state)

    def remaining(self, identity: str, now: Optional[float] = None) -> int:
        """Return how many requests the identity still has available in this window."""
        _, state = self.check(identity, now)
        return max(0, self.max_requests - state.request_count)
