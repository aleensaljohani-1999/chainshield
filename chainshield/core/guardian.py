"""
Guardian — the main request evaluation engine.

The Guardian coordinates all three protection layers in strict order:

  Layer 1 → TemporaryBlacklist   (fastest check, O(1))
  Layer 2 → SlidingWindowRateLimiter (per-identity quota)
  Layer 3 → GlobalLimiter        (system-wide ceiling)

Only if all three layers pass does the Guardian record the request as
accepted and return Decision(allowed=True).

Request flow
------------
                          ┌─────────────┐
    incoming request ────▶│  Blacklist  │──blocked──▶ Decision(allowed=False,
                          └──────┬──────┘              reason=TEMPORARY_BLACKLIST)
                                 │ clear
                          ┌──────▼──────┐
                          │  Rate Limit │──exceeded─▶ Decision(allowed=False,
                          └──────┬──────┘  + blacklist  reason=RATE_LIMIT_EXCEEDED)
                                 │ ok
                          ┌──────▼──────┐
                          │   Global   │──exceeded──▶ Decision(allowed=False,
                          └──────┬──────┘              reason=GLOBAL_LIMIT_EXCEEDED)
                                 │ ok
                          ┌──────▼──────┐
                          │   Accept   │────────────▶ Decision(allowed=True)
                          └─────────────┘
"""

import time
from dataclasses import dataclass, field
from typing import Optional

from chainshield.core.blacklist import TemporaryBlacklist
from chainshield.core.global_limit import GlobalLimiter
from chainshield.core.rate_limiter import SlidingWindowRateLimiter
from chainshield.models import BlockReason, Decision, GuardianStats
from chainshield.storage.base import BaseStorage
from chainshield.storage.memory import MemoryStorage


@dataclass
class GuardianConfig:
    """
    All tunable parameters in one place.

    Attributes
    ----------
    max_requests:
        Per-identity request cap within `window_size` seconds.
    window_size:
        Sliding window duration (seconds) applied to both per-identity
        and global counters.
    blacklist_duration:
        How long (seconds) an offending identity stays blocked.
    global_max_requests:
        System-wide request ceiling within `window_size` seconds.
    """

    max_requests: int = 5
    window_size: int = 60
    blacklist_duration: int = 30
    global_max_requests: int = 20


class Guardian:
    """
    Orchestrates all DDoS protection layers.

    Parameters
    ----------
    config:
        Tunable parameters. Defaults match the original Solidity contract values.
    storage:
        Storage backend. Defaults to MemoryStorage.

    Example
    -------
    >>> g = Guardian()
    >>> decision = g.check("192.168.1.1")
    >>> decision.allowed
    True
    """

    def __init__(
        self,
        config: Optional[GuardianConfig] = None,
        storage: Optional[BaseStorage] = None,
    ) -> None:
        self.config = config or GuardianConfig()
        self.storage = storage or MemoryStorage()
        self._started_at = time.time()

        self._rate_limiter = SlidingWindowRateLimiter(
            storage=self.storage,
            max_requests=self.config.max_requests,
            window_size=self.config.window_size,
        )
        self._blacklist = TemporaryBlacklist(
            storage=self.storage,
            blacklist_duration=self.config.blacklist_duration,
        )
        self._global_limiter = GlobalLimiter(
            storage=self.storage,
            global_max_requests=self.config.global_max_requests,
            window_size=self.config.window_size,
        )

        self._total_accepted = 0
        self._total_blocked = 0
        self._total_rate_blocked = 0
        self._total_global_blocked = 0
        self._total_blacklist_blocks = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check(self, identity: str, now: Optional[float] = None) -> Decision:
        """
        Evaluate a single request from `identity`.

        This is the only method most callers need. It is thread-safe when
        using MemoryStorage (all storage ops are lock-protected).

        Parameters
        ----------
        identity:
            Opaque string identifying the requester — typically an IP
            address, API key, or Ethereum address.
        now:
            Override the current time (Unix timestamp). Primarily for testing.

        Returns
        -------
        Decision
            decision.allowed == True  →  pass the request through.
            decision.allowed == False →  block the request; check block_reason.
        """
        t = now or time.time()

        # ── Layer 1: Temporary blacklist ──────────────────────────────
        state = self.storage.get_identity(identity)
        if state is not None:
            self._blacklist.expire_check(state, t)

        blocked, expires_at = self._blacklist.is_blocked(identity, t)
        if blocked:
            self._total_blocked += 1
            self._total_blacklist_blocks += 1
            _, g_state = self._global_limiter.check(t)
            return Decision(
                allowed=False,
                identity=identity,
                timestamp=t,
                block_reason=BlockReason.TEMPORARY_BLACKLIST,
                requests_in_window=state.request_count if state else 0,
                global_requests=g_state.request_count,
                blacklist_expires_at=expires_at,
            )

        # ── Layer 2: Per-identity sliding window ──────────────────────
        rate_ok, id_state = self._rate_limiter.check(identity, t)
        if not rate_ok:
            expires_at = self._blacklist.add(id_state, t)
            self._total_blocked += 1
            self._total_rate_blocked += 1
            _, g_state = self._global_limiter.check(t)
            return Decision(
                allowed=False,
                identity=identity,
                timestamp=t,
                block_reason=BlockReason.RATE_LIMIT_EXCEEDED,
                requests_in_window=id_state.request_count,
                global_requests=g_state.request_count,
                blacklist_expires_at=expires_at,
            )

        # ── Layer 3: Global ceiling ───────────────────────────────────
        global_ok, g_state = self._global_limiter.check(t)
        if not global_ok:
            self._total_blocked += 1
            self._total_global_blocked += 1
            return Decision(
                allowed=False,
                identity=identity,
                timestamp=t,
                block_reason=BlockReason.GLOBAL_LIMIT_EXCEEDED,
                requests_in_window=id_state.request_count,
                global_requests=g_state.request_count,
            )

        # ── Accept ────────────────────────────────────────────────────
        self._rate_limiter.record_accepted(id_state, t)
        self._global_limiter.record_accepted(g_state)
        self._total_accepted += 1

        return Decision(
            allowed=True,
            identity=identity,
            timestamp=t,
            requests_in_window=id_state.request_count,
            global_requests=g_state.request_count,
        )

    def unblock(self, identity: str) -> bool:
        """Manually lift a temporary blacklist. Returns True if a block was removed."""
        return self._blacklist.clear(identity)

    def stats(self) -> GuardianStats:
        """Return a snapshot of aggregate statistics."""
        now = time.time()
        return GuardianStats(
            total_accepted=self._total_accepted,
            total_blocked=self._total_blocked,
            total_blacklisted=self._total_rate_blocked,
            total_global_blocked=self._total_global_blocked,
            active_blacklisted_count=self.storage.count_active_blacklisted(now),
            global_requests_in_window=self._global_limiter.current_count,
            uptime_seconds=now - self._started_at,
        )

    def reset(self) -> None:
        """Clear all state. Intended for testing only."""
        self.storage.clear()
        self._total_accepted = 0
        self._total_blocked = 0
        self._total_rate_blocked = 0
        self._total_global_blocked = 0
        self._total_blacklist_blocks = 0
        self._started_at = time.time()
