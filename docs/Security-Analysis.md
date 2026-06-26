# Security Analysis

## Threat Model

ChainShield is an **off-chain rate limiting layer**. It enforces access policies at the application gateway. It does not replace network-level firewalls, CDN filtering, or TLS termination.

**Protected against:**
- Burst flooding from a single identity
- Sustained high-frequency traffic from a known identity
- Aggregate traffic spikes across many identities (via global limit)

**Not protected against:**
- Network-layer volumetric attacks (use a CDN or ISP-level scrubbing)
- Layer-3/4 SYN floods (use kernel-level defenses like `syncookies`)
- Attacks that arrive before ChainShield is in the request path

## Attack Vectors

### 1. Sybil Attack (Multi-Address Bypass)

**Description:** Attacker generates N unique identities and sends ≤ `max_requests` from each, staying under the per-identity limit while generating `N × max_requests` aggregate traffic.

**Mitigation:** The global request ceiling (`global_max_requests`) caps total accepted requests per window regardless of how many identities participate. When `global_max_requests` is exhausted, all further requests are blocked irrespective of per-identity status.

**Residual risk:** An attacker who can tolerate the global-limit cooldown can still generate `global_max_requests` requests per window. Tune `global_max_requests` and `window_size` based on your expected legitimate traffic volume.

**Severity:** Medium

---

### 2. Window Boundary Abuse

**Description:** Attacker sends `max_requests` at the very end of a window and `max_requests` at the very start of the next, effectively doubling the burst rate at window boundaries.

**Mitigation:** This is a known limitation of fixed-window counters. ChainShield uses a *resetting* sliding window (not a fixed-period bucket), which means the window anchor (`window_start`) follows the first request in each new period, not a fixed clock. This reduces but does not eliminate the boundary burst.

**For stricter control:** Implement a true sliding-window log (store each request timestamp and count those within `[now - window_size, now]`). This trades O(1) memory for O(k) where k = requests per window.

**Severity:** Low

---

### 3. Identity Spoofing

**Description:** Attacker forges the `X-Forwarded-For` header to present a different IP address on each request.

**Mitigation:** If your deployment is behind a trusted reverse proxy, configure it to strip or override `X-Forwarded-For` before traffic reaches ChainShield. The middleware's `identity_func` parameter lets you use any identity source (API keys, JWT subjects, device fingerprints) instead of raw IP.

**Severity:** High — if IP-based identity is used without a trusted proxy

---

### 4. Blacklist Bypass via Window Reset

**Description:** Attacker waits for the blacklist to expire, sends `max_requests - 1` requests (under the limit), waits for the window to reset, and repeats indefinitely.

**Mitigation:** This is by design — the temporary blacklist is intentionally not permanent. The `global_max_requests` limit constrains the total impact. For persistent offenders, integrate with an external reputation system and use the `unblock()` inverse: a manual `blacklist()` call with a much longer duration.

**Severity:** Low (bounded by global limit)

---

### 5. Timing Attack on Blacklist State

**Description:** An attacker probes the system to determine when a blacklist will expire by observing the `Retry-After` response header.

**Mitigation:** This is intentional — `Retry-After` tells legitimate users when to retry. If you want to hide expiry timing, omit the header (configure the middleware accordingly). Exposing the expiry time does not grant the attacker any capability they don't already have.

**Severity:** Informational

---

### 6. Resource Exhaustion via Identity Inflation

**Description:** Attacker generates millions of unique identities, each making one request. The in-memory storage grows without bound.

**Mitigation:**
- `MemoryStorage` does not expire idle identity records automatically. In practice, most deployments have a bounded set of real clients.
- Add a periodic cleanup task to evict entries where `window_start + window_size < now` and `blacklisted_until == 0`.
- For very large-scale deployments, use Redis with key TTL to handle eviction automatically.

**Severity:** Medium in long-running processes with unbounded identity sets

## Risk Summary

| Attack | Severity | Mitigated By |
|---|---|---|
| Sybil / multi-address | Medium | Global limit |
| Window boundary burst | Low | Resetting window anchor |
| IP spoofing | High | Trusted proxy + custom identity func |
| Repeated after expiry | Low | Global limit |
| Timing side-channel | Info | Acceptable by design |
| Memory exhaustion | Medium | Storage eviction / Redis TTL |

## Deployment Recommendations

1. Place ChainShield **behind** a trusted reverse proxy (nginx, Cloudflare) so `X-Forwarded-For` cannot be forged.
2. Use API keys or JWT subjects as the identity when available — they are harder to spoof than IPs.
3. Set `global_max_requests` to 2–3× your expected peak legitimate load, not a hard minimum.
4. Monitor `GuardianStats` and alert when `total_blocked / total_accepted > 0.05` (5% block rate indicates unusual traffic).
5. For distributed deployments, replace `MemoryStorage` with a Redis-backed implementation to share state across processes.
