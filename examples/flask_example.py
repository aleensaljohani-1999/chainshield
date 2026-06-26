"""
ChainShield + Flask integration example.

Install: pip install flask chainshield
Run    : python examples/flask_example.py
Test   : curl http://localhost:5000/api/data   (run 6 times quickly)
"""

from flask import Flask, jsonify
from chainshield import Guardian, GuardianConfig
from chainshield.middleware import FlaskChainShield

app = Flask(__name__)

guardian = Guardian(
    GuardianConfig(
        max_requests=5,
        window_size=60,
        blacklist_duration=30,
        global_max_requests=100,
    )
)

FlaskChainShield(app, guardian)


@app.route("/api/data")
def get_data():
    return jsonify({"message": "Hello from protected endpoint"})


@app.route("/health")
def health():
    s = guardian.stats()
    return jsonify(
        {
            "accepted": s.total_accepted,
            "blocked": s.total_blocked,
            "active_blacklisted": s.active_blacklisted_count,
            "uptime_seconds": round(s.uptime_seconds, 1),
        }
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
