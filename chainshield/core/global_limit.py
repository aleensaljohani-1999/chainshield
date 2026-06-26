"""
System-wide (global) request rate limiter.

Design rationale
----------------
Per-identity limits alone can be bypassed by Sybil attacks: an adversary
generates many addresses and sends requests from each, staying below the
per-identity threshold while generating a large aggregate load. The global
limiter closes this gap by enforcing a ceiling on the *total* number of
requests accepted across *all* identities within the same sliding window.

This mirrors the GLOBAL_MAX_REQUESTS constant from the original Solidity
enhanced contract.
"""

import time
from typing import Optional

from chainshield.models import GlobalState
from chainshield.storage.base import BaseStorage


class GlobalLimiter:
    """
    System-wide sliding-window request limiter.

    Parameters
    ----------
    storage:
        Storage backend shared with other components.
    global_max_requests:
        Maximum total accepted requests across all identities per window.
    window_size:
        Duration of the global observation window in seconds.
    """

    def __init__(
        self,
        storage: BaseStorage,
        global_max_requests: int = 20,
        window_size: int = 60,
    ) -> None:
        if global_max_requests < 1:
            raise ValueError("global_max_requests must be >= 1")

        self.storage = storage
        self.global_max_requests = global_max_requests
        self.window_size = window_size

    def check(self, now: Optional[float] = None) -> tuple[bool, GlobalState]:
        """
        Evaluate whether global capacity allows another request.

        Returns
        -------
        (allowed, state)
            allowed – True if below the global ceiling.
            state   – Current (possibly reset) GlobalState.
        """
        t = now or time.time()
        state = self.storage.get_global()

        if state.window_start == 0 or state.is_window_expired(self.window_size, t):
            state.reset_window(t)
            self.storage.set_global(state)

        allowed = state.request_count < self.global_max_requests
        return allowed, state

    def record_accepted(self, state: GlobalState) -> None:
        """Increment global counter and persist."""
        state.request_count += 1
        self.storage.set_global(state)

    @property
    def current_count(self) -> int:
        """Current global request count within the active window (raw storage read)."""
        return self.storage.get_global().request_count

    @property
    def remaining_capacity(self) -> int:
        """
        Remaining capacity in the current window (raw storage read).

        Note: does not trigger a window reset — call check() for that.
        """
        count = self.storage.get_global().request_count
        return max(0, self.global_max_requests - count)
