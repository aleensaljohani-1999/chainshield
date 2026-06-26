"""
Thread-safe in-memory storage backend.

Suitable for single-process deployments. For multi-process or distributed
deployments, use a shared backend like Redis.
"""

import threading
import time
from typing import Optional

from chainshield.models import GlobalState, IdentityState
from chainshield.storage.base import BaseStorage


class MemoryStorage(BaseStorage):
    """
    In-memory storage backed by a dict and a threading.Lock.

    All operations are O(1) except count_active_blacklisted which is O(n).
    """

    def __init__(self) -> None:
        self._identities: dict[str, IdentityState] = {}
        self._global = GlobalState()
        self._lock = threading.Lock()

    def get_identity(self, identity: str) -> Optional[IdentityState]:
        with self._lock:
            return self._identities.get(identity)

    def set_identity(self, state: IdentityState) -> None:
        with self._lock:
            self._identities[state.identity] = state

    def get_global(self) -> GlobalState:
        with self._lock:
            return self._global

    def set_global(self, state: GlobalState) -> None:
        with self._lock:
            self._global = state

    def count_active_blacklisted(self, now: float) -> int:
        with self._lock:
            return sum(1 for s in self._identities.values() if s.blacklisted_until > now)

    def clear(self) -> None:
        with self._lock:
            self._identities.clear()
            self._global = GlobalState()
