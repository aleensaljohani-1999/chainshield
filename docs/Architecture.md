# Architecture

## Overview

ChainShield implements a three-layer defence stack in pure Python. Each layer is a standalone, independently-testable component that shares one storage backend. The `Guardian` class wires them together and enforces the evaluation order.

```
                         Incoming Request
                               │
                               ▼
                    ┌──────────────────────┐
                    │      Guardian        │  ← single entry point
                    └──────────────────────┘
                               │
                ┌──────────────┼──────────────┐
                │              │              │
                ▼              ▼              ▼
        ┌──────────┐  ┌──────────────┐  ┌──────────────┐
        │Temporary │  │Sliding-Window│  │   Global     │
        │Blacklist │  │Rate Limiter  │  │   Limiter    │
        └──────────┘  └──────────────┘  └──────────────┘
                │              │              │
                └──────────────┼──────────────┘
                               │
                    ┌──────────▼──────────┐
                    │   BaseStorage       │
                    │ (MemoryStorage /    │
                    │  Redis / custom)    │
                    └─────────────────────┘
```

## Component Responsibilities

| Component | Responsibility |
|---|---|
| `Guardian` | Orchestrates evaluation order; accumulates stats |
| `SlidingWindowRateLimiter` | Per-identity request count within a time window |
| `TemporaryBlacklist` | Time-limited identity blocking with auto-expiry |
| `GlobalLimiter` | System-wide request ceiling across all identities |
| `BaseStorage` | Abstract I/O — swap backends without changing logic |
| `MemoryStorage` | Thread-safe in-process dict-backed implementation |

## Evaluation Order

The Guardian always evaluates in this order and short-circuits on the first failure:

1. **Blacklist check** — O(1) lookup, fastest possible rejection path
2. **Expired-blacklist cleanup** — auto-lift expired blocks before checking rate
3. **Per-identity window check** — reject + blacklist if over the per-identity limit
4. **Global ceiling check** — reject if total system traffic exceeds configured cap
5. **Accept** — increment both per-identity and global counters

This ordering ensures that:
- Blacklisted identities are rejected before touching the rate limiter (avoids counter noise)
- Global check runs last so per-identity state is already updated before the decision

## Storage Interface

All state is accessed through `BaseStorage`. Implement it to add any backend:

```python
class RedisStorage(BaseStorage):
    def get_identity(self, identity: str) -> Optional[IdentityState]: ...
    def set_identity(self, state: IdentityState) -> None: ...
    def get_global(self) -> GlobalState: ...
    def set_global(self, state: GlobalState) -> None: ...
    def count_active_blacklisted(self, now: float) -> int: ...
    def clear(self) -> None: ...
```

## Threading Model

`MemoryStorage` wraps all dict mutations in a `threading.Lock`. The `Guardian` itself is stateless between calls — all mutable state lives in storage. This makes it safe to share a single `Guardian` across Flask/FastAPI worker threads.

For multi-process deployments (gunicorn with `--workers > 1`), use a shared backend like Redis so state is consistent across processes.
