"""
ChainShield custom exceptions.
"""


class ChainShieldError(Exception):
    """Base exception for all ChainShield errors."""


class IdentityBlockedError(ChainShieldError):
    """Raised when a request is blocked due to temporary blacklist."""

    def __init__(self, identity: str, expires_at: float):
        self.identity = identity
        self.expires_at = expires_at
        super().__init__(f"Identity '{identity}' is temporarily blocked until {expires_at:.0f}")


class RateLimitExceededError(ChainShieldError):
    """Raised when per-identity request rate is exceeded."""

    def __init__(self, identity: str, limit: int, window: int):
        self.identity = identity
        self.limit = limit
        self.window = window
        super().__init__(
            f"Identity '{identity}' exceeded {limit} requests per {window}s window"
        )


class GlobalLimitExceededError(ChainShieldError):
    """Raised when the system-wide request quota is exhausted."""

    def __init__(self, limit: int, window: int):
        self.limit = limit
        self.window = window
        super().__init__(f"Global request limit of {limit} per {window}s window exceeded")


class StorageError(ChainShieldError):
    """Raised when the storage backend encounters an error."""
