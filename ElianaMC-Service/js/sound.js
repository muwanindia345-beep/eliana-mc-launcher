// ===== js/sound.js =====

const FanSound = {
  ctx: null, osc: null, gain: null, noise: null, ng: null,
  muted: false,

  init() {
    if (this.ctx) return;
    this.ctx = new (window.AudioContext || window.webkitAudioContext)();
  },

  start(freq) {
    if (this.muted) return;
    this.init(); this.stop();
    this.osc  = this.ctx.createOscillator();
    this.gain = this.ctx.createGain();
    this.osc.type = 'sawtooth';
    this.osc.frequency.value = freq;
    this.gain.gain.value = 0.04;
    this.osc.connect(this.gain);
    this.gain.connect(this.ctx.destination);
    this.osc.start();
    const buf = this.ctx.createBuffer(1, this.ctx.sampleRate*2, this.ctx.sampleRate);
    const d   = buf.getChannelData(0);
    for (let i = 0; i < d.length; i++) d[i] = Math.random()*2-1;
    this.noise = this.ctx.createBufferSource();
    this.ng    = this.ctx.createGain();
    const f    = this.ctx.createBiquadFilter();
    this.noise.buffer = buf;
    this.noise.loop   = true;
    f.type = 'bandpass';
    f.frequency.value = freq * 8;
    this.ng.gain.value = 0.025;
    this.noise.connect(f);
    f.connect(this.ng);
    this.ng.connect(this.ctx.destination);
    this.noise.start();
  },

  setFreq(freq) {
    if (!this.osc || !this.ctx) return;
    this.osc.frequency.setTargetAtTime(freq, this.ctx.currentTime, 0.6);
    if (this.ng) this.ng.gain.setTargetAtTime(
      freq > 80 ? 0.05 : 0.025,
      this.ctx.currentTime, 0.6
    );
  },

  stop() {
    try { this.osc?.stop();   } catch {}
    try { this.noise?.stop(); } catch {}
    this.osc = null; this.noise = null;
  },

  resume() {
    if (this.ctx?.state === 'suspended') this.ctx.resume();
  },

  rpmToFreq(rpm) {
    if (rpm <= 0)   return 0;
    if (rpm < 1000) return 30 + rpm / 40;
    if (rpm < 2000) return 55 + rpm / 60;
    return 90 + rpm / 80;
  },

  toggleMute(btn) {
    this.muted = !this.muted;
    if (btn) btn.textContent = this.muted ? '🔇' : '🔊';
    if (this.muted) this.stop();
  }
};
