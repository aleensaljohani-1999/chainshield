"""
Integration tests for the Guardian orchestrator.

These tests mirror the exact test scenarios from the original Solidity contract
testing (B1-B6, E1-E7) to confirm behavioral parity.
"""

import pytest

from chainshield import BlockReason, Guardian, GuardianConfig
from chainshield.storage.memory import MemoryStorage


@pytest.fixture
def config():
    return GuardianConfig(
        max_requests=5,
        window_size=60,
        blacklist_duration=30,
        global_max_requests=20,
    )


@pytest.fixture
def guardian(config):
    return Guardian(config=config, storage=MemoryStorage())


# ── Scenario: Normal traffic ───────────────────────────────────────────────

class TestNormalTraffic:
    def test_five_requests_all_accepted(self, guardian):
        """B3 / E3 equivalent: first 5 requests must be accepted."""
        now = 1000.0
        for i in range(5):
            d = guardian.check("user-1", now=now + i)
            assert d.allowed is True, f"Request {i+1} should be accepted"

    def test_moderate_traffic_spacing(self, guardian):
        """E4.3 moderate traffic test: requests spread over window are accepted."""
        timestamps = [0, 10, 20, 35, 50]
        base = 1000.0
        for t in timestamps:
            d = guardian.check("user-1", now=base + t)
            assert d.allowed is True, f"Request at t={t} should be accepted"


# ── Scenario: Rate limit blocking ─────────────────────────────────────────

class TestRateLimitBlocking:
    def test_sixth_request_blocked(self, guardian):
        """B4 / E3 equivalent: 6th request within window must be blocked."""
        now = 1000.0
        for _ in range(5):
            guardian.check("attacker", now=now)
        d = guardian.check("attacker", now=now)
        assert d.allowed is False
        assert d.block_reason == BlockReason.RATE_LIMIT_EXCEEDED

    def test_blocked_request_triggers_blacklist(self, guardian):
        """Exceeding rate limit sets blacklist_expires_at."""
        now = 1000.0
        for _ in range(5):
            guardian.check("attacker", now=now)
        d = guardian.check("attacker", now=now)
        assert d.blacklist_expires_at is not None
        assert d.blacklist_expires_at > now

    def test_state_is_preserved_after_block(self, guardian):
        """E3 key improvement over B5: blocked counter IS preserved (no revert rollback)."""
        now = 1000.0
        for _ in range(5):
            guardian.check("attacker", now=now)
        guardian.check("attacker", now=now)  # triggers block

        stats = guardian.stats()
        assert stats.total_accepted == 5
        assert stats.total_blocked == 1


# ── Scenario: Temporary blacklist ─────────────────────────────────────────

class TestTemporaryBlacklist:
    def test_blacklisted_user_is_blocked(self, guardian):
        """User blocked after exceeding limit stays blocked within duration."""
        now = 1000.0
        for _ in range(5):
            guardian.check("attacker", now=now)
        guardian.check("attacker", now=now)  # triggers blacklist

        # still blocked at t=1005
        d = guardian.check("attacker", now=now + 5)
        assert d.allowed is False
        assert d.block_reason == BlockReason.TEMPORARY_BLACKLIST

    def test_blacklist_expires_automatically(self, guardian):
        """E4 / E5: After blacklist_duration, user is automatically unblocked."""
        now = 1000.0
        for _ in range(5):
            guardian.check("attacker", now=now)
        guardian.check("attacker", now=now)

        # After 31 seconds (> 30s blacklist_duration), should be allowed again
        d = guardian.check("attacker", now=now + 31)
        assert d.allowed is True

    def test_manual_unblock(self, guardian):
        now = 1000.0
        for _ in range(5):
            guardian.check("attacker", now=now)
        guardian.check("attacker", now=now)

        removed = guardian.unblock("attacker")
        assert removed is True

        d = guardian.check("attacker", now=now + 1)
        assert d.allowed is True

    def test_unblock_non_blacklisted_returns_false(self, guardian):
        assert guardian.unblock("nobody") is False


# ── Scenario: Independent accounts ────────────────────────────────────────

class TestIndependentAccounts:
    def test_accounts_tracked_independently(self, guardian):
        """B6 / E6: Blocking user-A must not affect user-B."""
        now = 1000.0
        for _ in range(5):
            guardian.check("user-a", now=now)
        guardian.check("user-a", now=now)  # triggers blacklist

        d = guardian.check("user-b", now=now)
        assert d.allowed is True

    def test_multiple_users_fill_global_limit(self, guardian):
        """E7: Global limit is shared across all identities."""
        now = 1000.0
        # 4 users × 5 requests = 20 accepted → global limit reached
        for uid in range(4):
            for _ in range(5):
                guardian.check(f"user-{uid}", now=now)

        # 21st request should hit global limit
        d = guardian.check("user-new", now=now)
        assert d.allowed is False
        assert d.block_reason == BlockReason.GLOBAL_LIMIT_EXCEEDED


# ── Scenario: Global limit ────────────────────────────────────────────────

class TestGlobalLimit:
    def test_global_limit_triggers_correctly(self, guardian):
        """E7 full scenario: accepted=20, blocked=1."""
        now = 1000.0
        for i in range(20):
            d = guardian.check(f"user-{i}", now=now)
            assert d.allowed is True

        d = guardian.check("user-extra", now=now)
        assert d.allowed is False
        assert d.block_reason == BlockReason.GLOBAL_LIMIT_EXCEEDED

        stats = guardian.stats()
        assert stats.total_accepted == 20
        assert stats.total_blocked == 1

    def test_global_window_resets(self, guardian):
        now = 1000.0
        for i in range(20):
            guardian.check(f"u{i}", now=now)

        d = guardian.check("new-user", now=now + 61)
        assert d.allowed is True


# ── Scenario: Window reset ────────────────────────────────────────────────

class TestWindowReset:
    def test_counter_resets_after_window(self, guardian):
        now = 1000.0
        for _ in range(5):
            guardian.check("user-1", now=now)

        # user-1 exhausted; after window passes they can send again
        d = guardian.check("user-1", now=now + 61)
        assert d.allowed is True

    def test_requests_in_window_reflects_new_window(self, guardian):
        now = 1000.0
        for _ in range(5):
            guardian.check("user-1", now=now)

        d = guardian.check("user-1", now=now + 61)
        assert d.requests_in_window == 1  # only this new request counted


# ── Scenario: Edge cases ──────────────────────────────────────────────────

class TestEdgeCases:
    def test_empty_identity_string(self, guardian):
        d = guardian.check("", now=1000.0)
        assert d.allowed is True  # empty string is valid identity

    def test_very_long_identity(self, guardian):
        identity = "x" * 1000
        d = guardian.check(identity, now=1000.0)
        assert d.allowed is True

    def test_decision_as_dict(self, guardian):
        d = guardian.check("user", now=1000.0)
        result = d.as_dict()
        assert "allowed" in result
        assert "identity" in result
        assert "block_reason" in result

    def test_reset_clears_all_state(self, guardian):
        now = 1000.0
        for _ in range(5):
            guardian.check("user-1", now=now)
        guardian.check("user-1", now=now)

        guardian.reset()
        stats = guardian.stats()
        assert stats.total_accepted == 0
        assert stats.total_blocked == 0

        d = guardian.check("user-1", now=now)
        assert d.allowed is True

    def test_stats_structure(self, guardian):
        guardian.check("u", now=1000.0)
        s = guardian.stats()
        assert hasattr(s, "total_accepted")
        assert hasattr(s, "total_blocked")
        assert hasattr(s, "active_blacklisted_count")
        assert hasattr(s, "uptime_seconds")
        assert s.uptime_seconds >= 0


# ── Scenario: Decision metadata ───────────────────────────────────────────

class TestDecisionMetadata:
    def test_allowed_decision_has_no_block_reason(self, guardian):
        d = guardian.check("user", now=1000.0)
        assert d.block_reason is None
        assert d.blacklist_expires_at is None

    def test_blocked_decision_has_reason(self, guardian):
        now = 1000.0
        for _ in range(5):
            guardian.check("attacker", now=now)
        d = guardian.check("attacker", now=now)
        assert d.block_reason is not None
        assert not d.allowed

    def test_requests_in_window_increments(self, guardian):
        now = 1000.0
        counts = []
        for _ in range(3):
            d = guardian.check("user", now=now)
            counts.append(d.requests_in_window)
        assert counts == [1, 2, 3]
