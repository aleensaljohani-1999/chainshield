# API Reference

## `Guardian`

The main entry point. Orchestrates all three protection layers.

```python
from chainshield import Guardian, GuardianConfig

guardian = Guardian(config=GuardianConfig(), storage=MemoryStorage())
```

### `Guardian.check(identity, now=None) → Decision`

Evaluate a single request.

| Parameter | Type | Description |
|---|---|---|
| `identity` | `str` | Opaque requester identifier (IP, API key, etc.) |
| `now` | `float \| None` | Override current time (Unix timestamp). For testing. |

Returns a `Decision` object.

### `Guardian.unblock(identity) → bool`

Manually remove an active blacklist entry. Returns `True` if a block was lifted.

### `Guardian.stats() → GuardianStats`

Snapshot of aggregate counters since startup or last `reset()`.

### `Guardian.reset() → None`

Wipe all state. Intended for testing only.

---

## `GuardianConfig`

```python
GuardianConfig(
    max_requests: int = 5,
    window_size: int = 60,
    blacklist_duration: int = 30,
    global_max_requests: int = 20,
)
```

| Field | Default | Description |
|---|---|---|
| `max_requests` | 5 | Per-identity cap within one window |
| `window_size` | 60 | Window duration in seconds |
| `blacklist_duration` | 30 | How long an offender stays blocked (seconds) |
| `global_max_requests` | 20 | Total accepted requests per window across all identities |

---

## `Decision`

Immutable result of `Guardian.check()`.

| Field | Type | Description |
|---|---|---|
| `allowed` | `bool` | True = pass through, False = block |
| `identity` | `str` | The evaluated identity |
| `timestamp` | `float` | Unix time of the check |
| `block_reason` | `BlockReason \| None` | Why it was blocked, or None |
| `requests_in_window` | `int` | Current count for this identity in this window |
| `global_requests` | `int` | Current global count |
| `blacklist_expires_at` | `float \| None` | When the blacklist lifts (Unix timestamp) |

### `Decision.as_dict() → dict`

Serialise to a plain dict (JSON-safe).

---

## `BlockReason`

```python
class BlockReason(str, Enum):
    TEMPORARY_BLACKLIST = "temporary_blacklist"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    GLOBAL_LIMIT_EXCEEDED = "global_limit_exceeded"
```

---

## `GuardianStats`

Returned by `Guardian.stats()`.

| Field | Type | Description |
|---|---|---|
| `total_accepted` | `int` | Lifetime accepted requests |
| `total_blocked` | `int` | Lifetime blocked requests |
| `total_blacklisted` | `int` | Times rate limit triggered a blacklist |
| `total_global_blocked` | `int` | Times the global ceiling was hit |
| `active_blacklisted_count` | `int` | Identities currently blacklisted |
| `global_requests_in_window` | `int` | Current window global count |
| `uptime_seconds` | `float` | Seconds since Guardian was created or reset |

---

## `BaseStorage`

Implement to add a custom backend.

```python
class BaseStorage(ABC):
    def get_identity(self, identity: str) -> Optional[IdentityState]: ...
    def set_identity(self, state: IdentityState) -> None: ...
    def get_global(self) -> GlobalState: ...
    def set_global(self, state: GlobalState) -> None: ...
    def count_active_blacklisted(self, now: float) -> int: ...
    def clear(self) -> None: ...
```

---

## Middleware

### Flask

```python
FlaskChainShield(app, guardian=None, identity_func=None)
```

| Parameter | Description |
|---|---|
| `app` | Flask app instance |
| `guardian` | Pre-configured Guardian (optional) |
| `identity_func` | `(flask.Request) → str` override for identity extraction |

### FastAPI / Starlette

```python
app.add_middleware(FastAPIChainShield, guardian=guardian)
```

Both middlewares return `HTTP 429` with:
```json
{
  "error": "Too Many Requests",
  "reason": "rate_limit_exceeded",
  "retry_after": "28"
}
```
And a `Retry-After` header when the blacklist expiry is known.
