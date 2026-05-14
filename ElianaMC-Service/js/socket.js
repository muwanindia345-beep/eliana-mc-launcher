// ===== js/socket.js =====

const WS_URL = 'ws://localhost:8007/ws/console';

const socket = {
  ws: null,
  listeners: [],
  reconnectTimer: null,
  reconnectDelay: 3000,
  isConnected: false,
  manualClose: false,

  connect() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) return;
    this.manualClose = false;

    try {
      this.ws = new WebSocket(WS_URL);
    } catch (e) {
      console.error('[ElianaMC] WebSocket init failed:', e);
      this._scheduleReconnect();
      return;
    }

    this.ws.onopen = () => {
      this.isConnected = true;
      this.reconnectDelay = 3000;
      console.log('[ElianaMC] WebSocket connected');
      this._emit({ type: 'connected' });
    };

    this.ws.onmessage = (event) => {
      let data;
      try {
        data = JSON.parse(event.data);
      } catch {
        // Raw string — wrap it
        data = { type: 'log', message: String(event.data) };
      }
      this._emit(data);
    };

    this.ws.onclose = () => {
      this.isConnected = false;
      this._emit({ type: 'disconnected' });
      if (!this.manualClose) {
        this._scheduleReconnect();
      }
    };

    this.ws.onerror = () => {
      this.isConnected = false;
      this._emit({ type: 'error', message: 'WebSocket error' });
    };
  },

  disconnect() {
    this.manualClose = true;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.isConnected = false;
  },

  send(data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(typeof data === 'string' ? data : JSON.stringify(data));
      return true;
    }
    return false;
  },

  on(callback) {
    this.listeners.push(callback);
  },

  off(callback) {
    this.listeners = this.listeners.filter(l => l !== callback);
  },

  _emit(data) {
    this.listeners.forEach(cb => {
      try { cb(data); } catch(e) { console.error(e); }
    });
  },

  _scheduleReconnect() {
    if (this.reconnectTimer) return;
    console.log(`[ElianaMC] Reconnecting in ${this.reconnectDelay}ms...`);
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
      // Exponential backoff — max 15s
      this.reconnectDelay = Math.min(this.reconnectDelay * 1.5, 15000);
    }, this.reconnectDelay);
  }

};
