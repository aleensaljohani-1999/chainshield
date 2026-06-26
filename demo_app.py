"""
ChainShield — Interactive Demo Dashboard
"""

from flask import Flask, jsonify, request, render_template_string
from chainshield import Guardian, GuardianConfig
import time

app = Flask(__name__)

guardian = Guardian(
    GuardianConfig(
        max_requests=5,
        window_size=30,
        blacklist_duration=15,
        global_max_requests=20,
    )
)

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ChainShield — Live Demo</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: 'SF Mono', 'Fira Code', monospace;
    background: #0d1117;
    color: #e6edf3;
    min-height: 100vh;
  }
  .header {
    background: #161b22;
    border-bottom: 1px solid #30363d;
    padding: 20px 40px;
    display: flex;
    align-items: center;
    gap: 16px;
  }
  .logo { font-size: 28px; }
  .header h1 { font-size: 22px; color: #58a6ff; font-weight: 700; }
  .header span { font-size: 13px; color: #8b949e; }
  .container { max-width: 1100px; margin: 0 auto; padding: 32px 24px; }

  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 28px; }

  .card {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 24px;
  }
  .card h2 { font-size: 13px; color: #8b949e; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 20px; }

  .users { display: flex; flex-direction: column; gap: 12px; }
  .user-row {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 16px;
    background: #0d1117;
    border: 1px solid #21262d;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.15s;
  }
  .user-row:hover { border-color: #58a6ff; background: #1c2128; }
  .user-avatar {
    width: 36px; height: 36px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 16px;
    font-weight: bold;
  }
  .user-name { flex: 1; font-size: 14px; }
  .user-badge {
    font-size: 11px;
    padding: 3px 10px;
    border-radius: 20px;
    font-weight: 600;
  }
  .badge-ok { background: #1a3a1a; color: #3fb950; border: 1px solid #3fb950; }
  .badge-blocked { background: #3a1a1a; color: #f85149; border: 1px solid #f85149; }
  .badge-global { background: #2a1a3a; color: #d2a8ff; border: 1px solid #d2a8ff; }

  .send-btn {
    background: #21262d;
    border: 1px solid #30363d;
    color: #e6edf3;
    padding: 6px 14px;
    border-radius: 6px;
    cursor: pointer;
    font-size: 12px;
    font-family: inherit;
    transition: all 0.15s;
  }
  .send-btn:hover { background: #30363d; border-color: #58a6ff; }

  .stat-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  .stat-box {
    background: #0d1117;
    border: 1px solid #21262d;
    border-radius: 8px;
    padding: 16px;
    text-align: center;
  }
  .stat-num { font-size: 32px; font-weight: 700; margin-bottom: 4px; }
  .stat-label { font-size: 11px; color: #8b949e; text-transform: uppercase; letter-spacing: 0.5px; }
  .green { color: #3fb950; }
  .red { color: #f85149; }
  .blue { color: #58a6ff; }
  .purple { color: #d2a8ff; }

  .log {
    background: #0d1117;
    border: 1px solid #21262d;
    border-radius: 8px;
    height: 280px;
    overflow-y: auto;
    padding: 12px;
    font-size: 12px;
    line-height: 1.8;
  }
  .log-entry { display: flex; gap: 10px; align-items: flex-start; }
  .log-time { color: #484f58; min-width: 70px; }
  .log-user { min-width: 80px; }
  .log-ok { color: #3fb950; }
  .log-blocked { color: #f85149; }
  .log-global { color: #d2a8ff; }

  .global-bar-wrap {
    margin-top: 16px;
    background: #0d1117;
    border: 1px solid #21262d;
    border-radius: 8px;
    padding: 16px;
  }
  .bar-label { font-size: 12px; color: #8b949e; margin-bottom: 8px; display: flex; justify-content: space-between; }
  .bar-track { background: #21262d; border-radius: 4px; height: 8px; overflow: hidden; }
  .bar-fill { height: 100%; border-radius: 4px; transition: width 0.3s, background 0.3s; }

  .full-width { grid-column: 1 / -1; }

  .reset-btn {
    background: #21262d;
    border: 1px solid #30363d;
    color: #8b949e;
    padding: 8px 18px;
    border-radius: 6px;
    cursor: pointer;
    font-size: 12px;
    font-family: inherit;
    margin-top: 16px;
    display: block;
    width: 100%;
    transition: all 0.15s;
  }
  .reset-btn:hover { color: #f85149; border-color: #f85149; }

  .window-info {
    font-size: 11px;
    color: #8b949e;
    margin-top: 8px;
    text-align: center;
  }
</style>
</head>
<body>

<div class="header">
  <div class="logo">🛡️</div>
  <div>
    <h1>ChainShield</h1>
    <span>Live Rate Limiting Demo — 5 req / 30s window · 15s blacklist · Global limit: 20</span>
  </div>
</div>

<div class="container">
  <div class="grid">

    <!-- Users Panel -->
    <div class="card">
      <h2>📡 Simulate Requests</h2>
      <div class="users" id="users">
        <div class="user-row" onclick="sendRequest('alice')">
          <div class="user-avatar" style="background:#1a3a2a;color:#3fb950">A</div>
          <div class="user-name">alice</div>
          <span class="user-badge badge-ok" id="badge-alice">OK</span>
          <span style="font-size:12px;color:#8b949e" id="count-alice">0/5</span>
          <button class="send-btn">Send →</button>
        </div>
        <div class="user-row" onclick="sendRequest('bob')">
          <div class="user-avatar" style="background:#1a2a3a;color:#58a6ff">B</div>
          <div class="user-name">bob</div>
          <span class="user-badge badge-ok" id="badge-bob">OK</span>
          <span style="font-size:12px;color:#8b949e" id="count-bob">0/5</span>
          <button class="send-btn">Send →</button>
        </div>
        <div class="user-row" onclick="sendRequest('attacker')">
          <div class="user-avatar" style="background:#3a1a1a;color:#f85149">⚠</div>
          <div class="user-name">attacker</div>
          <span class="user-badge badge-ok" id="badge-attacker">OK</span>
          <span style="font-size:12px;color:#8b949e" id="count-attacker">0/5</span>
          <button class="send-btn">Send →</button>
        </div>
        <div class="user-row" onclick="sendRequest('carol')">
          <div class="user-avatar" style="background:#2a1a3a;color:#d2a8ff">C</div>
          <div class="user-name">carol</div>
          <span class="user-badge badge-ok" id="badge-carol">OK</span>
          <span style="font-size:12px;color:#8b949e" id="count-carol">0/5</span>
          <button class="send-btn">Send →</button>
        </div>
      </div>
      <button class="reset-btn" onclick="resetAll()">⟳ Reset All State</button>
    </div>

    <!-- Stats Panel -->
    <div class="card">
      <h2>📊 Live Statistics</h2>
      <div class="stat-grid">
        <div class="stat-box">
          <div class="stat-num green" id="stat-accepted">0</div>
          <div class="stat-label">Accepted</div>
        </div>
        <div class="stat-box">
          <div class="stat-num red" id="stat-blocked">0</div>
          <div class="stat-label">Blocked</div>
        </div>
        <div class="stat-box">
          <div class="stat-num blue" id="stat-blacklisted">0</div>
          <div class="stat-label">Currently Blacklisted</div>
        </div>
        <div class="stat-box">
          <div class="stat-num purple" id="stat-global">0</div>
          <div class="stat-label">Global / 20</div>
        </div>
      </div>
      <div class="global-bar-wrap">
        <div class="bar-label">
          <span>Global Window Usage</span>
          <span id="bar-label-text">0 / 20</span>
        </div>
        <div class="bar-track">
          <div class="bar-fill" id="global-bar" style="width:0%;background:#3fb950"></div>
        </div>
        <div class="window-info" id="window-info">Window: 30s sliding</div>
      </div>
    </div>

    <!-- Log -->
    <div class="card full-width">
      <h2>📋 Request Log</h2>
      <div class="log" id="log">
        <div style="color:#484f58;text-align:center;margin-top:100px">
          Click a user above to simulate requests...
        </div>
      </div>
    </div>

  </div>
</div>

<script>
  const userCounts = { alice: 0, bob: 0, attacker: 0, carol: 0 };

  async function sendRequest(user) {
    const res = await fetch('/api/check', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ identity: user })
    });
    const data = await res.json();
    updateUI(user, data);
  }

  function updateUI(user, data) {
    const badge = document.getElementById('badge-' + user);
    const countEl = document.getElementById('count-' + user);

    if (data.decision.allowed) {
      badge.textContent = 'OK';
      badge.className = 'user-badge badge-ok';
      userCounts[user] = data.decision.requests_in_window;
    } else {
      const reason = data.decision.block_reason;
      if (reason === 'temporary_blacklist') {
        badge.textContent = `BLACKLISTED ${Math.round(data.decision.blacklist_expires_at - Date.now()/1000)}s`;
        badge.className = 'user-badge badge-blocked';
      } else if (reason === 'rate_limit_exceeded') {
        badge.textContent = 'RATE LIMITED';
        badge.className = 'user-badge badge-blocked';
      } else {
        badge.textContent = 'GLOBAL LIMIT';
        badge.className = 'user-badge badge-global';
      }
    }
    countEl.textContent = userCounts[user] + '/5';

    addLog(user, data.decision);
    updateStats(data.stats);
  }

  function addLog(user, d) {
    const log = document.getElementById('log');
    const now = new Date().toLocaleTimeString('en', {hour12: false});
    const allowed = d.allowed;
    const reason = d.block_reason || '';
    const cls = allowed ? 'log-ok' : (reason === 'global_limit_exceeded' ? 'log-global' : 'log-blocked');
    const icon = allowed ? '✓' : '✗';
    const msg = allowed
      ? `accepted  (window: ${d.requests_in_window}/5  global: ${d.global_requests}/20)`
      : `blocked   reason=${reason}`;

    const firstEntry = log.querySelector('[style*="text-align:center"]');
    if (firstEntry) firstEntry.remove();

    const entry = document.createElement('div');
    entry.className = 'log-entry';
    entry.innerHTML = `
      <span class="log-time">${now}</span>
      <span class="log-user" style="color:#8b949e">${user}</span>
      <span class="${cls}">${icon} ${msg}</span>
    `;
    log.prepend(entry);
  }

  function updateStats(s) {
    document.getElementById('stat-accepted').textContent = s.total_accepted;
    document.getElementById('stat-blocked').textContent = s.total_blocked;
    document.getElementById('stat-blacklisted').textContent = s.active_blacklisted_count;
    document.getElementById('stat-global').textContent = s.global_requests_in_window;

    const pct = Math.min(100, (s.global_requests_in_window / 20) * 100);
    const bar = document.getElementById('global-bar');
    bar.style.width = pct + '%';
    bar.style.background = pct >= 100 ? '#f85149' : pct > 70 ? '#e3b341' : '#3fb950';
    document.getElementById('bar-label-text').textContent = `${s.global_requests_in_window} / 20`;
  }

  async function resetAll() {
    await fetch('/api/reset', { method: 'POST' });
    Object.keys(userCounts).forEach(u => {
      userCounts[u] = 0;
      document.getElementById('badge-' + u).textContent = 'OK';
      document.getElementById('badge-' + u).className = 'user-badge badge-ok';
      document.getElementById('count-' + u).textContent = '0/5';
    });
    document.getElementById('log').innerHTML = '<div style="color:#484f58;text-align:center;margin-top:100px">State reset — start fresh!</div>';
    updateStats({ total_accepted: 0, total_blocked: 0, active_blacklisted_count: 0, global_requests_in_window: 0 });
  }

  // Auto-refresh blacklist timers
  setInterval(async () => {
    const res = await fetch('/api/stats');
    const s = await res.json();
    updateStats(s);
  }, 2000);
</script>
</body>
</html>
"""

user_windows = {}

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/api/check", methods=["POST"])
def check():
    identity = request.json.get("identity", "unknown")
    decision = guardian.check(identity)
    stats = guardian.stats()
    return jsonify({
        "decision": decision.as_dict(),
        "stats": {
            "total_accepted": stats.total_accepted,
            "total_blocked": stats.total_blocked,
            "active_blacklisted_count": stats.active_blacklisted_count,
            "global_requests_in_window": stats.global_requests_in_window,
        }
    })

@app.route("/api/stats")
def get_stats():
    s = guardian.stats()
    return jsonify({
        "total_accepted": s.total_accepted,
        "total_blocked": s.total_blocked,
        "active_blacklisted_count": s.active_blacklisted_count,
        "global_requests_in_window": s.global_requests_in_window,
    })

@app.route("/api/reset", methods=["POST"])
def reset():
    guardian.reset()
    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(port=5050, debug=False)
