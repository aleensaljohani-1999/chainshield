# Changelog

## [1.0.0] — 2026-06-26

### Added
- `Guardian` orchestrator with three-layer protection pipeline
- `SlidingWindowRateLimiter` — per-identity sliding window counter
- `TemporaryBlacklist` — time-limited blocking with auto-expiry
- `GlobalLimiter` — system-wide request ceiling
- `MemoryStorage` — thread-safe in-memory backend
- `BaseStorage` — abstract interface for custom backends
- Flask middleware (`FlaskChainShield`)
- FastAPI/Starlette middleware (`FastAPIChainShield`)
- `Decision` dataclass with full request context
- `GuardianStats` for aggregate monitoring
- Comprehensive test suite (90%+ coverage)
- Flask and FastAPI integration examples
- Performance benchmarks
- Full security analysis documentation
- Arabic README (`README_AR.md`)
