"""
Flask middleware for ChainShield.

Usage
-----
    from flask import Flask
    from chainshield import Guardian, GuardianConfig
    from chainshield.middleware import FlaskChainShield

    app = Flask(__name__)
    guardian = Guardian(GuardianConfig(max_requests=10, window_size=60))
    FlaskChainShield(app, guardian)

The middleware uses the real client IP (respecting X-Forwarded-For when
TRUST_PROXY is set) as the identity. Blocked requests receive HTTP 429.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Optional

from chainshield.core.guardian import Guardian

if TYPE_CHECKING:
    from flask import Flask


def _get_client_ip(request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.remote_addr or "unknown"


class FlaskChainShield:
    """
    Installs a before_request hook that runs every incoming request
    through the Guardian.

    Parameters
    ----------
    app:
        The Flask application instance.
    guardian:
        Pre-configured Guardian. If None, a default one is created.
    identity_func:
        Optional callable that receives (flask.Request) and returns the
        identity string. Defaults to client IP extraction.
    """

    def __init__(
        self,
        app: "Flask",
        guardian: Optional[Guardian] = None,
        identity_func: Optional[Callable] = None,
    ) -> None:
        self.guardian = guardian or Guardian()
        self._identity_func = identity_func or _get_client_ip
        self._init_app(app)

    def _init_app(self, app: "Flask") -> None:
        from flask import jsonify, request

        @app.before_request
        def chainshield_check():
            identity = self._identity_func(request)
            decision = self.guardian.check(identity)
            if not decision.allowed:
                response = jsonify(
                    {
                        "error": "Too Many Requests",
                        "reason": decision.block_reason.value if decision.block_reason else None,
                        "retry_after": (
                            int(decision.blacklist_expires_at - __import__("time").time())
                            if decision.blacklist_expires_at
                            else None
                        ),
                    }
                )
                response.status_code = 429
                if decision.blacklist_expires_at:
                    response.headers["Retry-After"] = str(
                        int(decision.blacklist_expires_at - __import__("time").time())
                    )
                return response
