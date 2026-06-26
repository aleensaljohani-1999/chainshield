"""
ChainShield — Basic usage walkthrough.

Run with:
    python examples/basic_usage.py
"""

import time
from chainshield import Guardian, GuardianConfig, BlockReason


def separator(title: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print('─' * 60)


def main():
    guardian = Guardian(
        GuardianConfig(
            max_requests=5,
            window_size=60,
            blacklist_duration=10,   # short for demo
            global_max_requests=20,
        )
    )

    # ── Example 1: Normal traffic ──────────────────────────────────────
    separator("Example 1 — Normal traffic (5 requests within limit)")
    for i in range(1, 6):
        d = guardian.check("alice")
        status = "✓ ALLOWED" if d.allowed else "✗ BLOCKED"
        print(f"  Request {i:>2}: {status}  (in-window count: {d.requests_in_window})")

    # ── Example 2: Rate limit exceeded ────────────────────────────────
    separator("Example 2 — 6th request triggers rate limit + temporary blacklist")
    d = guardian.check("alice")
    print(f"  Request  6: {'✓ ALLOWED' if d.allowed else '✗ BLOCKED'}")
    print(f"  Reason      : {d.block_reason.value if d.block_reason else 'none'}")
    if d.blacklist_expires_at:
        print(f"  Blacklisted until: t+{d.blacklist_expires_at - time.time():.1f}s")

    # ── Example 3: Still blocked (blacklist active) ────────────────────
    separator("Example 3 — Subsequent requests blocked while blacklisted")
    for i in range(7, 10):
        d = guardian.check("alice")
        print(f"  Request {i:>2}: {'✓' if d.allowed else '✗'} {d.block_reason.value if d.block_reason else ''}")

    # ── Example 4: Independent identities ─────────────────────────────
    separator("Example 4 — Bob is unaffected by Alice's blacklist")
    d = guardian.check("bob")
    print(f"  Bob request : {'✓ ALLOWED' if d.allowed else '✗ BLOCKED'}")

    # ── Example 5: Blacklist expiry ────────────────────────────────────
    separator("Example 5 — Wait for blacklist to expire, Alice sends again")
    print("  Sleeping 11 seconds for blacklist to expire...")
    time.sleep(11)
    d = guardian.check("alice")
    print(f"  Alice request after expiry: {'✓ ALLOWED' if d.allowed else '✗ BLOCKED'}")
    print(f"  In-window count reset to  : {d.requests_in_window}")

    # ── Example 6: Global limit ────────────────────────────────────────
    separator("Example 6 — Global limit (20 total requests)")
    guardian.reset()
    guardian2 = Guardian(GuardianConfig(max_requests=100, global_max_requests=5))
    for i in range(1, 6):
        d = guardian2.check(f"user-{i}")
        print(f"  user-{i}: {'✓' if d.allowed else '✗'}  global={d.global_requests}")
    d = guardian2.check("user-6")
    print(f"  user-6: {'✓ ALLOWED' if d.allowed else '✗ BLOCKED'}  reason={d.block_reason.value if d.block_reason else 'none'}")

    # ── Final stats ────────────────────────────────────────────────────
    separator("Stats")
    s = guardian.stats()
    print(f"  Total accepted : {s.total_accepted}")
    print(f"  Total blocked  : {s.total_blocked}")
    print(f"  Active blocked : {s.active_blacklisted_count}")


if __name__ == "__main__":
    main()
