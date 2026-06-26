"""
Tests for TemporaryBlacklist.
"""

import pytest

from chainshield.core.blacklist import TemporaryBlacklist
from chainshield.models import IdentityState
from chainshield.storage.memory import MemoryStorage


@pytest.fixture
def storage():
    return MemoryStorage()


@pytest.fixture
def blacklist(storage):
    return TemporaryBlacklist(storage, blacklist_duration=30)


class TestTemporaryBlacklist:
    def test_unknown_identity_not_blocked(self, blacklist):
        blocked, expires = blacklist.is_blocked("new-user", now=1000.0)
        assert blocked is False
        assert expires is None

    def test_blacklisted_identity_is_blocked(self, blacklist, storage):
        state = IdentityState(identity="attacker", window_start=1000.0)
        storage.set_identity(state)
        blacklist.add(state, now=1000.0)

        blocked, expires = blacklist.is_blocked("attacker", now=1005.0)
        assert blocked is True
        assert expires == pytest.approx(1030.0)

    def test_blacklist_expires_after_duration(self, blacklist, storage):
        state = IdentityState(identity="attacker", window_start=1000.0)
        storage.set_identity(state)
        blacklist.add(state, now=1000.0)

        # Still blocked at t=1029
        blocked, _ = blacklist.is_blocked("attacker", now=1029.0)
        assert blocked is True

        # Unblocked at t=1031
        blocked, _ = blacklist.is_blocked("attacker", now=1031.0)
        assert blocked is False

    def test_expire_check_clears_state(self, blacklist, storage):
        state = IdentityState(identity="user", window_start=1000.0)
        state.request_count = 5
        storage.set_identity(state)
        blacklist.add(state, now=1000.0)

        # Expire check at t=1031 should reset request_count
        refreshed = storage.get_identity("user")
        cleared = blacklist.expire_check(refreshed, now=1031.0)
        assert cleared is True

        final = storage.get_identity("user")
        assert final.request_count == 0
        assert final.blacklisted_until == 0.0

    def test_manual_clear_works(self, blacklist, storage):
        state = IdentityState(identity="user", window_start=1000.0)
        storage.set_identity(state)
        blacklist.add(state, now=1000.0)

        result = blacklist.clear("user", now=1005.0)
        assert result is True

        blocked, _ = blacklist.is_blocked("user", now=1005.0)
        assert blocked is False

    def test_clear_non_blacklisted_returns_false(self, blacklist):
        result = blacklist.clear("nobody", now=1000.0)
        assert result is False

    def test_add_returns_expiry_timestamp(self, blacklist, storage):
        state = IdentityState(identity="x", window_start=1000.0)
        storage.set_identity(state)
        expires = blacklist.add(state, now=1000.0)
        assert expires == 1030.0

    def test_invalid_duration(self, storage):
        with pytest.raises(ValueError):
            TemporaryBlacklist(storage, blacklist_duration=0)
