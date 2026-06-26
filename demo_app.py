from flask import Flask, jsonify, request, render_template_string
from chainshield import Guardian, GuardianConfig

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
<title>ChainShield</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif;
    background: #0a0c10;
    color: #c9d1d9;
    min-height: 100vh;
    font-size: 14px;
  }

  .topbar {
    background: #0d1117;
    border-bottom: 1px solid #21262d;
    padding: 0 40px;
    height: 56px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .topbar-left { display: flex; align-items: center; gap: 24px; }
  .brand { font-size: 16px; font-weight: 700; color: #f0f6fc; letter-spacing: -0.3px; }
  .brand span { color: #388bfd; }
  .topbar-meta { font-size: 12px; color: #484f58; }
  .uptime { font-size: 12px; color: #484f58; font-variant-numeric: tabular-nums; }

  .layout {
    max-width: 1140px;
    margin: 32px auto;
    padding: 0 24px;
    display: grid;
    grid-template-columns: 340px 1fr;
    gap: 20px;
  }

  .panel {
    background: #0d1117;
    border: 1px solid #21262d;
    border-radius: 8px;
    overflow: hidden;
  }
  .panel-header {
    padding: 14px 20px;
    border-bottom: 1px solid #21262d;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .panel-title {
    font-size: 12px;
    font-weight: 600;
    color: #8b949e;
    text-transform: uppercase;
    letter-spacing: 0.8px;
  }
  .panel-body { padding: 16px 20px; }

  /* Clients */
  .client-list { display: flex; flex-direction: column; gap: 8px; }
  .client {
    display: grid;
    grid-template-columns: 32px 1fr auto auto;
    align-items: center;
    gap: 12px;
    padding: 10px 14px;
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 6px;
    cursor: pointer;
    transition: border-color 0.12s;
  }
  .client:hover { border-color: #388bfd; }
  .client.selected { border-color: #388bfd; background: #1c2128; }

  .avatar {
    width: 32px; height: 32px;
    border-radius: 4px;
    display: flex; align-items: center; justify-content: center;
    font-size: 13px;
    font-weight: 700;
    color: #f0f6fc;
    flex-shrink: 0;
  }

  .client-name { font-size: 13px; color: #e6edf3; font-weight: 500; }
  .client-sub { font-size: 11px; color: #484f58; margin-top: 2px; }

  .status-pill {
    font-size: 11px;
    font-weight: 600;
    padding: 3px 9px;
    border-radius: 4px;
    white-space: nowrap;
  }
  .pill-ok       { background: #0d2b1a; color: #3fb950; border: 1px solid #1a4a2a; }
  .pill-blocked  { background: #2d1515; color: #f85149; border: 1px solid #5a2020; }
  .pill-global   { background: #1e1530; color: #a371f7; border: 1px solid #3d2870; }

  .send-btn {
    background: transparent;
    border: 1px solid #30363d;
    color: #8b949e;
    padding: 5px 12px;
    border-radius: 5px;
    cursor: pointer;
    font-size: 12px;
    font-family: inherit;
    font-weight: 500;
    transition: all 0.12s;
    white-space: nowrap;
  }
  .send-btn:hover { border-color: #388bfd; color: #388bfd; }

  .divider { height: 1px; background: #21262d; margin: 16px 0; }

  .reset-btn {
    width: 100%;
    background: transparent;
    border: 1px solid #21262d;
    color: #484f58;
    padding: 8px;
    border-radius: 5px;
    cursor: pointer;
    font-size: 12px;
    font-family: inherit;
    transition: all 0.12s;
  }
  .reset-btn:hover { border-color: #f85149; color: #f85149; }

  /* Right column */
  .right-col { display: flex; flex-direction: column; gap: 20px; }

  /* Stats */
  .stat-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
  .stat {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 6px;
    padding: 16px;
  }
  .stat-val {
    font-size: 28px;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
    line-height: 1;
    margin-bottom: 6px;
  }
  .stat-key { font-size: 11px; color: #484f58; text-transform: uppercase; letter-spacing: 0.5px; }
  .c-green  { color: #3fb950; }
  .c-red    { color: #f85149; }
  .c-blue   { color: #388bfd; }
  .c-purple { color: #a371f7; }

  /* Global bar */
  .bar-section {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 6px;
    padding: 14px 16px;
  }
  .bar-meta {
    display: flex;
    justify-content: space-between;
    font-size: 12px;
    color: #8b949e;
    margin-bottom: 10px;
  }
  .bar-track {
    height: 4px;
    background: #21262d;
    border-radius: 2px;
    overflow: hidden;
  }
  .bar-fill {
    height: 100%;
    border-radius: 2px;
    transition: width 0.3s, background 0.3s;
  }

  /* Log */
  .log-wrap {
    background: #0d1117;
    border: 1px solid #21262d;
    border-radius: 8px;
    overflow: hidden;
  }
  .log-body {
    height: 300px;
    overflow-y: auto;
    padding: 12px 16px;
    font-size: 12px;
    font-family: 'SF Mono', 'Fira Code', monospace;
  }
  .log-body::-webkit-scrollbar { width: 4px; }
  .log-body::-webkit-scrollbar-track { background: #0d1117; }
  .log-body::-webkit-scrollbar-thumb { background: #21262d; border-radius: 2px; }

  .log-row {
    display: grid;
    grid-template-columns: 68px 90px 1fr;
    gap: 8px;
    padding: 3px 0;
    border-bottom: 1px solid #161b22;
    line-height: 1.7;
  }
  .log-t  { color: #30363d; }
  .log-id { color: #8b949e; }
  .log-ok   { color: #3fb950; }
  .log-err  { color: #f85149; }
  .log-glob { color: #a371f7; }
  .log-empty { color: #30363d; text-align: center; padding-top: 120px; }

  .full { grid-column: 1 / -1; }
</style>
</head>
<body>

<div class="topbar">
  <div class="topbar-left">
    <div class="brand">Chain<span>Shield</span></div>
    <div class="topbar-meta">rate-limit: 5 req / 30s &nbsp;·&nbsp; blacklist: 15s &nbsp;·&nbsp; global: 20</div>
  </div>
  <div class="uptime" id="uptime">uptime: 0s</div>
</div>

<div class="layout">

  <!-- Left: clients -->
  <div class="panel">
    <div class="panel-header">
      <span class="panel-title">Clients</span>
    </div>
    <div class="panel-body">
      <div class="client-list">

        <div class="client" onclick="sendRequest('alice')">
          <div class="avatar" style="background:#0d2b1a;">AL</div>
          <div>
            <div class="client-name">alice</div>
            <div class="client-sub" id="sub-alice">0 / 5 requests</div>
          </div>
          <span class="status-pill pill-ok" id="pill-alice">allowed</span>
          <button class="send-btn">Send</button>
        </div>

        <div class="client" onclick="sendRequest('bob')">
          <div class="avatar" style="background:#0c1f3a;">BO</div>
          <div>
            <div class="client-name">bob</div>
            <div class="client-sub" id="sub-bob">0 / 5 requests</div>
          </div>
          <span class="status-pill pill-ok" id="pill-bob">allowed</span>
          <button class="send-btn">Send</button>
        </div>

        <div class="client" onclick="sendRequest('attacker')">
          <div class="avatar" style="background:#2d1515;">AT</div>
          <div>
            <div class="client-name">attacker</div>
            <div class="client-sub" id="sub-attacker">0 / 5 requests</div>
          </div>
          <span class="status-pill pill-ok" id="pill-attacker">allowed</span>
          <button class="send-btn">Send</button>
        </div>

        <div class="client" onclick="sendRequest('carol')">
          <div class="avatar" style="background:#1e1530;">CA</div>
          <div>
            <div class="client-name">carol</div>
            <div class="client-sub" id="sub-carol">0 / 5 requests</div>
          </div>
          <span class="status-pill pill-ok" id="pill-carol">allowed</span>
          <button class="send-btn">Send</button>
        </div>

      </div>
      <div class="divider"></div>
      <button class="reset-btn" onclick="resetAll()">Reset state</button>
    </div>
  </div>

  <!-- Right -->
  <div class="right-col">

    <!-- Stats -->
    <div class="stat-row">
      <div class="stat">
        <div class="stat-val c-green" id="s-accepted">0</div>
        <div class="stat-key">Accepted</div>
      </div>
      <div class="stat">
        <div class="stat-val c-red" id="s-blocked">0</div>
        <div class="stat-key">Blocked</div>
      </div>
      <div class="stat">
        <div class="stat-val c-blue" id="s-blacklisted">0</div>
        <div class="stat-key">Blacklisted</div>
      </div>
      <div class="stat">
        <div class="stat-val c-purple" id="s-global">0</div>
        <div class="stat-key">Global window</div>
      </div>
    </div>

    <!-- Global bar -->
    <div class="bar-section">
      <div class="bar-meta">
        <span>Global window usage</span>
        <span id="bar-label">0 of 20</span>
      </div>
      <div class="bar-track">
        <div class="bar-fill" id="bar-fill" style="width:0%;background:#3fb950;"></div>
      </div>
    </div>

    <!-- Log -->
    <div class="log-wrap">
      <div class="panel-header">
        <span class="panel-title">Request log</span>
        <span style="font-size:11px;color:#484f58" id="log-count">0 entries</span>
      </div>
      <div class="log-body" id="log">
        <div class="log-empty">No requests yet</div>
      </div>
    </div>

  </div>
</div>

<script>
  const counts = { alice:0, bob:0, attacker:0, carol:0 };
  let logCount = 0;
  let startTime = Date.now();

  setInterval(() => {
    const s = Math.floor((Date.now() - startTime) / 1000);
    document.getElementById('uptime').textContent = `uptime: ${s}s`;
  }, 1000);

  async function sendRequest(id) {
    const r = await fetch('/api/check', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({identity: id})
    });
    const data = await r.json();
    const d = data.decision;

    const pill = document.getElementById('pill-' + id);
    const sub  = document.getElementById('sub-' + id);

    if (d.allowed) {
      counts[id] = d.requests_in_window;
      pill.textContent = 'allowed';
      pill.className = 'status-pill pill-ok';
    } else {
      const reason = d.block_reason;
      if (reason === 'temporary_blacklist') {
        const secs = d.blacklist_expires_at ? Math.ceil(d.blacklist_expires_at - Date.now()/1000) : '?';
        pill.textContent = `blacklisted ${secs}s`;
        pill.className = 'status-pill pill-blocked';
      } else if (reason === 'rate_limit_exceeded') {
        pill.textContent = 'rate limited';
        pill.className = 'status-pill pill-blocked';
      } else {
        pill.textContent = 'global limit';
        pill.className = 'status-pill pill-global';
      }
    }

    sub.textContent = `${counts[id]} / 5 requests`;
    addLog(id, d);
    updateStats(data.stats);
  }

  function addLog(id, d) {
    const log = document.getElementById('log');
    const empty = log.querySelector('.log-empty');
    if (empty) empty.remove();

    logCount++;
    document.getElementById('log-count').textContent = `${logCount} entries`;

    const now = new Date().toLocaleTimeString('en-GB', {hour12:false});
    const allowed = d.allowed;
    const reason  = d.block_reason || '';
    const cls     = allowed ? 'log-ok' : (reason === 'global_limit_exceeded' ? 'log-glob' : 'log-err');
    const symbol  = allowed ? 'PASS' : 'DENY';
    const detail  = allowed
      ? `accepted  window=${d.requests_in_window}/5  global=${d.global_requests}/20`
      : `${reason}  global=${d.global_requests}/20`;

    const row = document.createElement('div');
    row.className = 'log-row';
    row.innerHTML = `
      <span class="log-t">${now}</span>
      <span class="log-id">${id}</span>
      <span class="${cls}">${symbol}  ${detail}</span>
    `;
    log.prepend(row);
  }

  function updateStats(s) {
    document.getElementById('s-accepted').textContent   = s.total_accepted;
    document.getElementById('s-blocked').textContent    = s.total_blocked;
    document.getElementById('s-blacklisted').textContent = s.active_blacklisted_count;
    document.getElementById('s-global').textContent     = s.global_requests_in_window;

    const pct = Math.min(100, (s.global_requests_in_window / 20) * 100);
    const fill = document.getElementById('bar-fill');
    fill.style.width = pct + '%';
    fill.style.background = pct >= 100 ? '#f85149' : pct > 70 ? '#e3b341' : '#3fb950';
    document.getElementById('bar-label').textContent = `${s.global_requests_in_window} of 20`;
  }

  async function resetAll() {
    await fetch('/api/reset', {method:'POST'});
    Object.keys(counts).forEach(id => {
      counts[id] = 0;
      document.getElementById('pill-' + id).textContent = 'allowed';
      document.getElementById('pill-' + id).className = 'status-pill pill-ok';
      document.getElementById('sub-' + id).textContent = '0 / 5 requests';
    });
    document.getElementById('log').innerHTML = '<div class="log-empty">State cleared</div>';
    logCount = 0;
    document.getElementById('log-count').textContent = '0 entries';
    updateStats({total_accepted:0, total_blocked:0, active_blacklisted_count:0, global_requests_in_window:0});
  }

  setInterval(async () => {
    const r = await fetch('/api/stats');
    const s = await r.json();
    updateStats(s);
  }, 2000);
</script>
</body>
</html>
"""

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
