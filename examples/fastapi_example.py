"""
ChainShield + FastAPI integration example.

Install: pip install fastapi uvicorn chainshield
Run    : uvicorn examples.fastapi_example:app --reload
Test   : curl http://localhost:8000/api/data   (run 6 times quickly)
"""

from fastapi import FastAPI
from chainshield import Guardian, GuardianConfig
from chainshield.middleware import FastAPIChainShield

app = FastAPI(title="ChainShield Demo", version="1.0.0")

guardian = Guardian(
    GuardianConfig(
        max_requests=5,
        window_size=60,
        blacklist_duration=30,
        global_max_requests=100,
    )
)

app.add_middleware(FastAPIChainShield, guardian=guardian)


@app.get("/api/data")
async def get_data():
    return {"message": "Hello from protected endpoint"}


@app.get("/health")
async def health():
    s = guardian.stats()
    return {
        "accepted": s.total_accepted,
        "blocked": s.total_blocked,
        "active_blacklisted": s.active_blacklisted_count,
        "uptime_seconds": round(s.uptime_seconds, 1),
    }
