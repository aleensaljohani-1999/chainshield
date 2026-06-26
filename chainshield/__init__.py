"""
ChainShield — Blockchain-Inspired DDoS Rate Limiter
====================================================

A production-grade, off-chain implementation of the sliding-window rate
limiting, temporary blacklist, and global request ceiling algorithms
originally designed for Ethereum smart contracts.

Quick start
-----------
    from chainshield import Guardian, GuardianConfig

    guardian = Guardian(GuardianConfig(
        max_requests=5,
        window_size=60,
        blacklist_duration=30,
        global_max_requests=100,
    ))

    decision = guardian.check("192.168.1.1")
    if decision.allowed:
        process_request()
    else:
        reject_with_429(decision.block_reason)
"""

from chainshield.core.guardian import Guardian, GuardianConfig
from chainshield.models import BlockReason, Decision, GuardianStats
from chainshield.storage.memory import MemoryStorage

__version__ = "1.0.0"
__author__ = "ChainShield Contributors"
__license__ = "MIT"

__all__ = [
    "Guardian",
    "GuardianConfig",
    "Decision",
    "BlockReason",
    "GuardianStats",
    "MemoryStorage",
]
