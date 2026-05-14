// ===== js/console.js =====

let logCount      = 0;
let currentRPM    = 0;
let targetRPM     = 0;
let rpmInterval   = null;
let cmdHistory    = [];
let historyIndex  = -1;

const RPM = {
  stopped:    0,
  starting:   800,
  started:    3200,
  restarting: 600,
  stopping:   400
};

// ── Init ──────────────────────────────────────────
window.addEventListener('DOMContentLoaded', () => {
  loadServerTag();

  // Restore status from localStorage
  const saved = localStorage.getItem('eliana-status') || 'stopped';
  applyStatus(saved);

  // Sync server type
  const type = localStorage.getItem('eliana-server') || 'java';
  api.setServerType(type).catch(() => {});

  // WebSocket
  socket.on(handleSocketEvent);
  socket.connect();

  // Fetch real status from backend
  fetchServerStatus();
});

// ── Server Tag ────────────────────────────────────
function loadServerTag() {
  const type = localStorage.getItem('eliana-server') || 'java';
  const tag  = document.getElementById('console-server-tag');
  tag.textContent = type === 'java' ? '☕ SeraphinaMC' : '🪨 LuciaMC';
}

// ── Socket Events ─────────────────────────────────
function handleSocketEvent(data) {
  switch (data.type) {

    case 'connected':
      setWsStatus(true);
      appendLog('WebSocket connected', 'system');
      updateDCLine(2, 'WS: CONNECTED');
      break;

    case 'disconnected':
      setWsStatus(false);
      appendLog('WebSocket disconnected — reconnecting...', 'warn');
      updateDCLine(2, 'WS: RECONNECTING');
      break;

    case 'error':
      appendLog('WebSocket error', 'error');
      updateDCLine(2, 'WS: ERROR');
      break;

    case 'command':
      // Ignore echo
      break;

    case 'log':
    case 'console':
    case 'message':
    case 'output': {
      const msg = data.message || data.data || data.output || '';
      if (msg) {
        appendLog(msg, detectLogType(msg));
        updateDCLine(1, msg.slice(0, 22));
      }
      break;
    }

    case 'status':
      applyStatus(data.status);
      break;

    default:
      if (data.message && typeof data.message === 'string') {
        appendLog(data.message, detectLogType(data.message));
        updateDCLine(1, data.message.slice(0, 22));
      } else if (typeof data === 'string' && data.trim()) {
        appendLog(data, detectLogType(data));
        updateDCLine(1, data.slice(0, 22));
      }
      break;
  }
}

// ── Detect Log Type ───────────────────────────────
function detectLogType(msg) {
  if (!msg) return 'info';
  const m = msg.toLowerCase();
  if (m.includes('error') || m.includes('exception') || m.includes('fatal') || m.includes('crash')) return 'error';
  if (m.includes('warn'))  return 'warn';
  if (m.includes('done!') || m.includes('success') || m.includes('started') || m.includes('ready')) return 'success';
  if (m.includes('info'))  return 'info';
  return 'info';
}

// ── Append Log ────────────────────────────────────
function appendLog(message, type = 'info') {
  const body = document.getElementById('console-body');
  const now  = new Date();
  const time = now.toTimeString().slice(0, 8);

  const line = document.createElement('div');
  line.className = 'log-line';
  line.innerHTML = `
    <span class="log-time">[${time}]</span>
    <span class="log-msg ${type}">${escapeHtml(String(message))}</span>
  `;

  body.appendChild(line);

  // Auto scroll
  body.scrollTop = body.scrollHeight;

  // Log count
  logCount++;
  document.getElementById('log-count').textContent = logCount;
}

// ── Clear Console ─────────────────────────────────
function clearConsole() {
  const body = document.getElementById('console-body');
  body.innerHTML = `
    <div class="console-welcome">
      <span class="glow-green">ElianaMC Service</span> — Console Cleared
    </div>
  `;
  logCount = 0;
  document.getElementById('log-count').textContent = '0';
}

// ── Send Command ──────────────────────────────────
function sendCommand() {
  const input = document.getElementById('console-input');
  const cmd   = input.value.trim();
  if (!cmd) return;

  cmdHistory.unshift(cmd);
  if (cmdHistory.length > 50) cmdHistory.pop();
  historyIndex = -1;

  appendLog('> ' + cmd, 'system');

  // Send plain string — backend expects this
  const sent = socket.send(cmd);
  if (!sent) appendLog('WebSocket not connected — command not sent', 'error');

  input.value = '';
}

function handleInput(e) {
  if (e.key === 'Enter') {
    sendCommand();
  } else if (e.key === 'ArrowUp') {
    historyIndex = Math.min(historyIndex + 1, cmdHistory.length - 1);
    document.getElementById('console-input').value = cmdHistory[historyIndex] || '';
    e.preventDefault();
  } else if (e.key === 'ArrowDown') {
    historyIndex = Math.max(historyIndex - 1, -1);
    document.getElementById('console-input').value =
      historyIndex === -1 ? '' : cmdHistory[historyIndex];
    e.preventDefault();
  }
}

// ── WebSocket Status ──────────────────────────────
function setWsStatus(connected) {
  const dot = document.getElementById('ws-dot');
  const txt = document.getElementById('ws-status');
  const led = document.getElementById('dc-led');

  if (connected) {
    dot.className = 'dot online';
    txt.textContent = 'CONNECTED';
    txt.style.color = 'var(--green)';
    led.className = 'dc-led online';
  } else {
    dot.className = 'dot offline';
    txt.textContent = 'DISCONNECTED';
    txt.style.color = 'var(--red)';
    led.className = 'dc-led offline';
  }
}

// ── Server Status ─────────────────────────────────
async function fetchServerStatus() {
  try {
    const data = await api.status();
    applyStatus(data.status || 'stopped');
  } catch {
    applyStatus('stopped');
  }
}

function applyStatus(status) {
  // Save to localStorage
  localStorage.setItem('eliana-status', status);

  const dot       = document.getElementById('srv-dot');
  const txt       = document.getElementById('srv-status');
  const miniLabel = document.getElementById('mini-status-label');
  const miniFan   = document.getElementById('mini-fan');

  miniFan.classList.remove('stopped', 'slow', 'fast');

  switch (status) {
    case 'started':
      dot.className = 'dot online';
      txt.textContent = 'ONLINE';
      txt.style.color = 'var(--green)';
      miniLabel.textContent = 'STARTED';
      miniLabel.className = 'mini-label started';
      miniFan.classList.add('fast');
      targetRPM = RPM.started;
      updateDCLine(3, 'MC: RUNNING');
      break;

    case 'starting':
      dot.className = 'dot pending';
      txt.textContent = 'STARTING';
      txt.style.color = 'var(--orange)';
      miniLabel.textContent = 'STARTING';
      miniLabel.className = 'mini-label starting';
      miniFan.classList.add('slow');
      targetRPM = RPM.starting;
      updateDCLine(3, 'MC: STARTING');
      break;

    case 'restarting':
      dot.className = 'dot pending';
      txt.textContent = 'RESTARTING';
      txt.style.color = 'var(--orange)';
      miniLabel.textContent = 'RESTARTING';
      miniLabel.className = 'mini-label restarting';
      miniFan.classList.add('slow');
      targetRPM = RPM.restarting;
      updateDCLine(3, 'MC: RESTARTING');
      break;

    case 'stopping':
      dot.className = 'dot pending';
      txt.textContent = 'STOPPING';
      txt.style.color = 'var(--red)';
      miniLabel.textContent = 'STOPPING';
      miniLabel.className = 'mini-label stopping';
      miniFan.classList.add('slow');
      targetRPM = RPM.stopping;
      updateDCLine(3, 'MC: STOPPING');
      break;

    default:
      dot.className = 'dot offline';
      txt.textContent = 'OFFLINE';
      txt.style.color = 'var(--red)';
      miniLabel.textContent = 'OFFLINE';
      miniLabel.className = 'mini-label';
      miniFan.classList.add('stopped');
      targetRPM = RPM.stopped;
      updateDCLine(3, 'MC: OFFLINE');
  }

  animateRPM();
}

// ── RPM Animation ─────────────────────────────────
function animateRPM() {
  if (rpmInterval) clearInterval(rpmInterval);

  rpmInterval = setInterval(() => {
    const diff = targetRPM - currentRPM;
    if (Math.abs(diff) < 5) {
      currentRPM = targetRPM;
      clearInterval(rpmInterval);
      rpmInterval = null;
    } else {
      currentRPM += diff * 0.08;
    }

    const val   = Math.round(currentRPM);
    const rpmEl = document.getElementById('mini-rpm-value');
    rpmEl.textContent = val.toLocaleString();

    if (currentRPM > 2000)     rpmEl.style.color = 'var(--green)';
    else if (currentRPM > 400) rpmEl.style.color = 'var(--orange)';
    else                       rpmEl.style.color = 'var(--dim)';

  }, 50);
}

// ── DC Screen ─────────────────────────────────────
function updateDCLine(lineNum, text) {
  const el = document.getElementById(`dc-line-${lineNum}`);
  if (el) el.textContent = String(text).toUpperCase().slice(0, 22);
}

// ── Escape HTML ───────────────────────────────────
function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
