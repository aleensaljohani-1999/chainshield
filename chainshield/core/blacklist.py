"""
Temporary (time-limited) identity blacklist.

Design rationale
----------------
The original academic project attempted a *permanent* blacklist but
discovered a critical flaw: Solidity's `revert` rolls back all state changes,
so the blacklist flag was never persisted. This Python implementation avoids
that entire class of problem by using time-based expiry instead of a boolean
flag — no rollback mechanism exists in Python, and the temporary nature
reduces false-positive impact on legitimate users.

An identity is "blacklisted" if and only if:
    blacklisted_until > current_time

When the timestamp passes, the identity is automatically unblocked on its
next request — no admin action required.
"""

import time
from typing import Optional

from chainshield.models import IdentityState
from chainshield.storage.base import BaseStorage


class TemporaryBlacklist:
    """
    Time-limited identity blacklist manager.

    Parameters
    ----------
    storage:
        Storage backend shared with the rate limiter.
    blacklist_duration:
        How long (seconds) an identity stays blocked after triggering.
    """

    def __init__(self, storage: BaseStorage, blacklist_duration: int = 30) -> None:
        if blacklist_duration < 1:
            raise ValueError("blacklist_duration must be >= 1 second")
        self.storage = storage
        self.blacklist_duration = blacklist_duration

    def is_blocked(self, identity: str, now: Optional[float] = None) -> tuple[bool, Optional[float]]:
        """
        Check whether an identity is currently blacklisted.

        Returns
        -------
        (blocked, expires_at)
            blocked    – True if the identity must be denied.
            expires_at – Unix timestamp when the block lifts, or None.
        """
        t = now or time.time()
        state = self.storage.get_identity(identity)
        if state is None:
            return False, None
        if state.is_blacklisted(t):
            return True, state.blacklisted_until
        return False, None

    def add(self, state: IdentityState, now: Optional[float] = None) -> float:
        """
        Blacklist an identity for `blacklist_duration` seconds.

        Returns the Unix timestamp when the block will expire.
        """
        t = now or time.time()
        state.blacklisted_until = t + self.blacklist_duration
        self.storage.set_identity(state)
        return state.blacklisted_until

    def clear(self, identity: str, now: Optional[float] = None) -> bool:
        """
        Manually lift the blacklist for an identity.

        Returns True if a block entry existed (active or not), False if the
        identity was never blacklisted.
        """
        state = self.storage.get_identity(identity)
        if state is None or state.blacklisted_until == 0.0:
            return False
        state.clear_blacklist(now)
        self.storage.set_identity(state)
        return True

    def expire_check(self, state: IdentityState, now: Optional[float] = None) -> bool:
        """
        If a prior blacklist has expired, reset the state and return True.
        Called automatically by Guardian on every request.
        """
        t = now or time.time()
        if state.blacklisted_until != 0 and state.blacklisted_until <= t:
            state.clear_blacklist(t)
            self.storage.set_identity(state)
            return True
        return False
