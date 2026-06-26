"""
ChainShield data models.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class BlockReason(str, Enum):
    TEMPORARY_BLACKLIST = "temporary_blacklist"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    GLOBAL_LIMIT_EXCEEDED = "global_limit_exceeded"


@dataclass(frozen=True)
class Decision:
    """Result of a single request check."""

    allowed: bool
    identity: str
    timestamp: float = field(default_factory=time.time)
    block_reason: Optional[BlockReason] = None
    requests_in_window: int = 0
    global_requests: int = 0
    blacklist_expires_at: Optional[float] = None

    @property
    def is_blacklisted(self) -> bool:
        return self.block_reason == BlockReason.TEMPORARY_BLACKLIST

    def as_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "identity": self.identity,
            "timestamp": self.timestamp,
            "block_reason": self.block_reason.value if self.block_reason else None,
            "requests_in_window": self.requests_in_window,
            "global_requests": self.global_requests,
            "blacklist_expires_at": self.blacklist_expires_at,
        }


@dataclass
class IdentityState:
    """Per-identity tracking state."""

    identity: str
    request_count: int = 0
    window_start: float = field(default_factory=time.time)
    blacklisted_until: float = 0.0

    def is_blacklisted(self, now: Optional[float] = None) -> bool:
        return self.blacklisted_until > (now or time.time())

    def is_window_expired(self, window_size: int, now: Optional[float] = None) -> bool:
        return (now or time.time()) > self.window_start + window_size

    def reset_window(self, now: Optional[float] = None) -> None:
        self.window_start = now or time.time()
        self.request_count = 0

    def clear_blacklist(self, now: Optional[float] = None) -> None:
        self.blacklisted_until = 0.0
        self.reset_window(now)


@dataclass
class GlobalState:
    """System-wide traffic tracking state."""

    request_count: int = 0
    window_start: float = 0.0  # 0 = uninitialized; reset on first check

    def is_window_expired(self, window_size: int, now: Optional[float] = None) -> bool:
        return (now or time.time()) > self.window_start + window_size

    def reset_window(self, now: Optional[float] = None) -> None:
        self.window_start = now or time.time()
        self.request_count = 0


@dataclass
class GuardianStats:
    """Aggregate statistics snapshot."""

    total_accepted: int
    total_blocked: int
    total_blacklisted: int
    total_global_blocked: int
    active_blacklisted_count: int
    global_requests_in_window: int
    uptime_seconds: float
