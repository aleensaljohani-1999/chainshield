"""
FastAPI / Starlette middleware for ChainShield.

Usage
-----
    from fastapi import FastAPI
    from chainshield import Guardian, GuardianConfig
    from chainshield.middleware import FastAPIChainShield

    app = FastAPI()
    guardian = Guardian(GuardianConfig(max_requests=10, window_size=60))
    app.add_middleware(FastAPIChainShield, guardian=guardian)
"""

from __future__ import annotations

import time
from typing import Optional

from chainshield.core.guardian import Guardian


def _get_client_ip(request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


class FastAPIChainShield:
    """
    ASGI middleware that wraps every request through the Guardian.

    Blocked requests receive HTTP 429 with a JSON body and optional
    Retry-After header.
    """

    def __init__(self, app, guardian: Optional[Guardian] = None) -> None:
        self.app = app
        self.guardian = guardian or Guardian()

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        from starlette.requests import Request
        from starlette.responses import JSONResponse

        request = Request(scope, receive)
        identity = _get_client_ip(request)
        decision = self.guardian.check(identity)

        if not decision.allowed:
            headers = {}
            if decision.blacklist_expires_at:
                retry_after = max(0, int(decision.blacklist_expires_at - time.time()))
                headers["Retry-After"] = str(retry_after)

            response = JSONResponse(
                status_code=429,
                content={
                    "error": "Too Many Requests",
                    "reason": decision.block_reason.value if decision.block_reason else None,
                    "retry_after": headers.get("Retry-After"),
                },
                headers=headers,
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)
