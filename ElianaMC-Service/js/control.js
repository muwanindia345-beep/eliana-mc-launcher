// ===== js/control.js =====

let currentStatus = 'stopped';
let targetRPM     = 0;
let currentRPM    = 0;
let rpmInterval   = null;
let updateInterval= null;
let timerInterval = null;
let timerSeconds  = 10;

const RPM = { stopped:0, starting:800, started:3200, restarting:600, stopping:400 };

window.addEventListener('DOMContentLoaded', () => {
  document.addEventListener('click', () => FanSound.resume());
  loadServerBadge();
  fetchStatus();
  startAutoUpdate();
  socket.on((data) => {
    if (data.status && data.status !== currentStatus) applyStatus(data.status);
  });
  socket.connect('dashboard');
});

function loadServerBadge() {
  const type = localStorage.getItem('eliana-server') || 'java';
  api.setServerType(type).catch(() => {});
  const badge = document.getElementById('server-badge');
  const infoServer = document.getElementById('info-server');
  const infoEngine = document.getElementById('info-engine');
  if (type === 'java') {
    badge.textContent = '☕ JAVA';
    badge.style.color = 'var(--orange)';
    badge.style.borderColor = 'rgba(255,170,0,0.3)';
    infoServer.textContent = 'SeraphinaMC';
    infoEngine.textContent = 'Paper.jar';
  } else {
    badge.textContent = '🪨 BEDROCK';
    badge.style.color = 'var(--blue)';
    badge.style.borderColor = 'rgba(0,180,255,0.3)';
    infoServer.textContent = 'LuciaMC';
    infoEngine.textContent = 'bedrock_server';
  }
}

async function fetchStatus() {
  try {
    const data   = await api.status();
    const status = data.status || 'stopped';
    if (
      (currentStatus === 'starting'   && status === 'stopped') ||
      (currentStatus === 'restarting' && status === 'stopped') ||
      (currentStatus === 'stopping'   && status === 'started')
    ) { resetTimer(); return; }
    applyStatus(status);
  } catch {}
  resetTimer();
}

function applyStatus(status) {
  currentStatus = status;
  localStorage.setItem('eliana-status', status);
  const dot        = document.getElementById('status-dot');
  const statusText = document.getElementById('status-text');
  const label      = document.getElementById('fan-status-label');
  const infoStatus = document.getElementById('info-status');
  const fan        = document.getElementById('fan');
  fan.classList.remove('stopped','slow','fast');
  switch (status) {
    case 'started':
      dot.className = 'dot online';
      statusText.textContent = 'ONLINE';
      label.textContent = 'STARTED';
      label.className = 'fan-status-label started';
      fan.classList.add('fast');
      infoStatus.textContent = 'RUNNING';
      infoStatus.style.color = 'var(--green)';
      targetRPM = RPM.started;
      FanSound.start(FanSound.rpmToFreq(RPM.started));
      break;
    case 'starting':
      dot.className = 'dot pending';
      statusText.textContent = 'STARTING...';
      label.textContent = 'STARTING...';
      label.className = 'fan-status-label starting';
      fan.classList.add('slow');
      infoStatus.textContent = 'STARTING';
      infoStatus.style.color = 'var(--orange)';
      targetRPM = RPM.starting;
      FanSound.start(FanSound.rpmToFreq(RPM.starting));
      break;
    case 'restarting':
      dot.className = 'dot pending';
      statusText.textContent = 'RESTARTING...';
      label.textContent = 'RESTARTING...';
      label.className = 'fan-status-label restarting';
      fan.classList.add('slow');
      infoStatus.textContent = 'RESTARTING';
      infoStatus.style.color = 'var(--orange)';
      targetRPM = RPM.restarting;
      FanSound.start(FanSound.rpmToFreq(RPM.restarting));
      break;
    case 'stopping':
      dot.className = 'dot pending';
      statusText.textContent = 'STOPPING...';
      label.textContent = 'STOPPING...';
      label.className = 'fan-status-label stopping';
      fan.classList.add('slow');
      infoStatus.textContent = 'STOPPING';
      infoStatus.style.color = 'var(--red)';
      targetRPM = RPM.stopping;
      FanSound.setFreq(FanSound.rpmToFreq(RPM.stopping));
      break;
    default:
      dot.className = 'dot offline';
      statusText.textContent = 'OFFLINE';
      label.textContent = 'OFFLINE';
      label.className = 'fan-status-label';
      fan.classList.add('stopped');
      infoStatus.textContent = 'STOPPED';
      infoStatus.style.color = 'var(--red)';
      targetRPM = RPM.stopped;
      FanSound.stop();
  }
  animateRPM();
  updateButtons(status);
}

function animateRPM() {
  if (rpmInterval) clearInterval(rpmInterval);
  rpmInterval = setInterval(() => {
    const diff = targetRPM - currentRPM;
    if (Math.abs(diff) < 5) {
      currentRPM = targetRPM;
      clearInterval(rpmInterval);
      rpmInterval = null;
    } else {
      currentRPM += diff * 0.06;
    }
    const val   = Math.round(currentRPM);
    const rpmEl = document.getElementById('rpm-value');
    rpmEl.textContent = val.toLocaleString();
    rpmEl.style.color = currentRPM > 2000 ? 'var(--green)' : currentRPM > 400 ? 'var(--orange)' : 'var(--dim)';
    if (!FanSound.muted && FanSound.osc) FanSound.setFreq(FanSound.rpmToFreq(currentRPM));
  }, 50);
}

function updateButtons(status) {
  const isRunning    = status === 'started';
  const isStopped    = status === 'stopped';
  const isTransition = ['starting','stopping','restarting'].includes(status);
  document.getElementById('btn-start').disabled   = isRunning  || isTransition;
  document.getElementById('btn-stop').disabled    = isStopped  || isTransition;
  document.getElementById('btn-restart').disabled = isStopped  || isTransition;
}

async function serverAction(action) {
  try {
    if (action === 'start') {
      FanSound.init();
      applyStatus('starting');
      await api.start();
      const poll = setInterval(async () => {
        const d = await api.status().catch(() => ({}));
        if (d.status === 'started') { clearInterval(poll); applyStatus('started'); }
      }, 5000);
      setTimeout(() => clearInterval(poll), 180000);
    }
    if (action === 'stop') {
      applyStatus('stopping');
      await api.stop();
      setTimeout(fetchStatus, 4000);
    }
    if (action === 'restart') {
      FanSound.init();
      applyStatus('restarting');
      await api.restart();
      const poll = setInterval(async () => {
        const d = await api.status().catch(() => ({}));
        if (d.status === 'started') { clearInterval(poll); applyStatus('started'); }
      }, 5000);
      setTimeout(() => clearInterval(poll), 180000);
    }
  } catch (e) {
    console.error(e);
    setTimeout(fetchStatus, 3000);
  }
}

function toggleMute() {
  FanSound.toggleMute(document.getElementById('mute-btn'));
  if (!FanSound.muted && currentStatus !== 'stopped') {
    FanSound.start(FanSound.rpmToFreq(currentRPM));
  }
}

function startAutoUpdate() {
  updateInterval = setInterval(fetchStatus, 10000);
  startTimer();
}

function startTimer() {
  timerSeconds = 10;
  if (timerInterval) clearInterval(timerInterval);
  timerInterval = setInterval(() => {
    timerSeconds--;
    document.getElementById('update-timer').textContent = `Next update in ${timerSeconds}s`;
    if (timerSeconds <= 0) timerSeconds = 10;
  }, 1000);
}

function resetTimer() { timerSeconds = 10; startTimer(); }
