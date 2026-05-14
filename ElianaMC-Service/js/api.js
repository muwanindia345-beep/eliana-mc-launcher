// ===== js/api.js =====

const API_BASE = 'http://localhost:8007';

const api = {

  async start() {
    const res = await fetch(`${API_BASE}/start`, { method: 'POST' });
    return res.json();
  },

  async stop() {
    const res = await fetch(`${API_BASE}/stop`, { method: 'POST' });
    return res.json();
  },

  async restart() {
    const res = await fetch(`${API_BASE}/restart`, { method: 'POST' });
    return res.json();
  },

  async status() {
    const res = await fetch(`${API_BASE}/status`);
    const data = await res.json();
    // Normalize — backend "online/offline" → frontend "started/stopped"
    return {
      ...data,
      status: data.status === 'online'  ? 'started' :
              data.status === 'offline' ? 'stopped' : data.status
    };
  },

  async setServerType(type) {
    const res = await fetch(`${API_BASE}/server-type`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ type })
    });
    return res.json();
  },

  async getServerType() {
    const res = await fetch(`${API_BASE}/server-type`);
    return res.json();
  }

};

