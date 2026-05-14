// ===== js/index.js =====

let selectedServer = localStorage.getItem('eliana-server') || null;

function selectServer(type) {
  selectedServer = type;
  localStorage.setItem('eliana-server', type);

  // Cards update
  document.getElementById('card-java').classList.remove('selected');
  document.getElementById('card-bedrock').classList.remove('selected');
  document.getElementById(`card-${type}`).classList.add('selected');

  // Info text
  const dot  = document.getElementById('sel-dot');
  const text = document.getElementById('selected-text');

  if (type === 'java') {
    text.textContent = 'Java Edition — SeraphinaMC';
    dot.className = 'dot online';
  } else {
    text.textContent = 'Bedrock Edition — LuciaMC';
    dot.className = 'dot online';
  }

  // Enable launch
  document.getElementById('launch-btn').disabled = false;

  // Sync to backend
  api.setServerType(type).catch(() => {
    console.warn('[ElianaMC] Could not sync server type to backend');
  });
}

function launch() {
  if (!selectedServer) return;
  window.location.href = 'control.html';
}

// On load — restore selection
window.addEventListener('DOMContentLoaded', () => {
  if (selectedServer) {
    selectServer(selectedServer);
  }
});
