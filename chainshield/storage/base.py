"""
Abstract storage backend interface.

Implement this to add Redis, Memcached, or any other backend.
"""

from abc import ABC, abstractmethod
from typing import Optional

from chainshield.models import GlobalState, IdentityState


class BaseStorage(ABC):
    """Protocol all storage backends must satisfy."""

    @abstractmethod
    def get_identity(self, identity: str) -> Optional[IdentityState]:
        """Return current state for an identity, or None if unknown."""

    @abstractmethod
    def set_identity(self, state: IdentityState) -> None:
        """Persist identity state."""

    @abstractmethod
    def get_global(self) -> GlobalState:
        """Return global traffic state."""

    @abstractmethod
    def set_global(self, state: GlobalState) -> None:
        """Persist global state."""

    @abstractmethod
    def count_active_blacklisted(self, now: float) -> int:
        """Return number of identities currently blacklisted."""

    @abstractmethod
    def clear(self) -> None:
        """Wipe all stored state. Useful for testing."""
