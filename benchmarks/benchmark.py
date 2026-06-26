"""
ChainShield performance benchmark.

Measures throughput (checks/second) for single-identity and multi-identity
workloads using the in-memory storage backend.

Run:
    python benchmarks/benchmark.py
"""

import statistics
import time
from typing import Callable

from chainshield import Guardian, GuardianConfig
from chainshield.storage.memory import MemoryStorage


def run_benchmark(name: str, fn: Callable, iterations: int = 100_000) -> None:
    times = []
    for _ in range(5):  # 5 warm-up runs
        fn()

    start = time.perf_counter()
    for _ in range(iterations):
        fn()
    elapsed = time.perf_counter() - start

    throughput = iterations / elapsed
    print(f"  {name:<40} {throughput:>12,.0f} checks/sec  ({elapsed*1000:.1f} ms total)")


def main():
    print("\nChainShield Benchmark")
    print("=" * 70)

    # ── Single identity (worst case: always same key) ──────────────────
    print("\n[Single-identity workload]")
    g = Guardian(GuardianConfig(max_requests=999_999, global_max_requests=999_999))
    run_benchmark("check() — single identity", lambda: g.check("user-1"))

    # ── Multi-identity (realistic: rotating IPs) ───────────────────────
    print("\n[Multi-identity workload (1000 rotating identities)]")
    g2 = Guardian(GuardianConfig(max_requests=999_999, global_max_requests=999_999))
    counter = [0]

    def rotating():
        counter[0] = (counter[0] + 1) % 1000
        g2.check(f"user-{counter[0]}")

    run_benchmark("check() — 1000 rotating identities", rotating)

    # ── Blacklist check path ───────────────────────────────────────────
    print("\n[Blacklist path workload]")
    g3 = Guardian(GuardianConfig(max_requests=1, global_max_requests=999_999))
    g3.check("blocked-user")  # trigger blacklist
    g3.check("blocked-user")  # confirm blocked

    run_benchmark("check() — blacklisted identity (fast-path)", lambda: g3.check("blocked-user"))

    # ── Stats call overhead ────────────────────────────────────────────
    print("\n[Stats overhead]")
    g4 = Guardian()
    run_benchmark("stats()", g4.stats, iterations=1_000_000)

    print()


if __name__ == "__main__":
    main()
