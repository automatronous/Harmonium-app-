/**
 * ChromaForge Spectrum Visualiser
 * Renders a reactive frequency bar graph on a <canvas> element.
 * Optimised: pixel-ratio aware, requestAnimationFrame loop, GPU-friendly.
 */
class Visualizer {
  constructor(canvas, audio) {
    this.canvas = canvas;
    this.audio  = audio;
    this.ctx    = canvas.getContext('2d');
    this.raf    = null;
    this.bars   = 72;           // number of frequency bars
    this.peak   = [];           // peak hold per bar
    this._initPeaks();

    // Resize on init + window resize
    this._resize();
    this._ro = new ResizeObserver(() => this._resize());
    this._ro.observe(canvas.parentElement || canvas);
  }

  _initPeaks() {
    for (let i = 0; i < this.bars; i++) this.peak[i] = 0;
  }

  _resize() {
    const pr  = window.devicePixelRatio || 1;
    const rect = this.canvas.getBoundingClientRect();
    this.canvas.width  = rect.width  * pr;
    this.canvas.height = rect.height * pr;
    this.ctx.scale(pr, pr);
    this._w = rect.width;
    this._h = rect.height;
  }

  start() { this._draw(); }

  stop() {
    if (this.raf) { cancelAnimationFrame(this.raf); this.raf = null; }
  }

  _draw() {
    this.raf = requestAnimationFrame(() => this._draw());

    const W = this._w, H = this._h;
    const ctx = this.ctx;

    // Clear with faint trail for glow persistence
    ctx.clearRect(0, 0, W, H);

    const freq = this.audio.getFreqData();
    const bw   = W / this.bars;

    for (let i = 0; i < this.bars; i++) {
      // Map bar index to frequency bucket (logarithmic-ish)
      const bucketIdx = Math.floor((i / this.bars) ** 1.6 * (freq ? freq.length * 0.75 : 0));
      const raw       = freq ? (freq[bucketIdx] || 0) / 255 : 0;
      const val       = raw * 0.9 + (this.peak[i] > raw ? 0 : 0); // slight smoothing

      // Peak hold & decay
      if (raw > this.peak[i]) {
        this.peak[i] = raw;
      } else {
        this.peak[i] = Math.max(0, this.peak[i] - 0.012);
      }

      const barH = val * H * 0.88;
      const x    = i * bw;

      // ── Bar gradient: cool electric spectrum ──────────────────────────────
      const hue  = 195 + (i / this.bars) * 120; // cyan → violet
      const sat  = 75 + val * 20;
      const lit  = 45 + val * 20;
      const alpha = 0.55 + val * 0.45;

      const grad = ctx.createLinearGradient(x, H - barH, x, H);
      grad.addColorStop(0,   `hsla(${hue}, ${sat}%, ${lit + 15}%, ${alpha})`);
      grad.addColorStop(0.5, `hsla(${hue + 15}, ${sat}%, ${lit}%, ${alpha * 0.8})`);
      grad.addColorStop(1,   `hsla(${hue + 30}, ${sat}%, ${lit - 10}%, ${alpha * 0.3})`);

      ctx.shadowBlur  = val > 0.15 ? 12 : 0;
      ctx.shadowColor = `hsla(${hue}, 90%, 65%, 0.7)`;

      ctx.fillStyle = grad;
      ctx.fillRect(x + 1, H - barH, bw - 2, barH);

      // ── Peak dot ──────────────────────────────────────────────────────────
      const peakY = H - this.peak[i] * H * 0.88 - 2;
      if (this.peak[i] > 0.05) {
        ctx.shadowBlur = 6;
        ctx.fillStyle  = `hsla(${hue}, 100%, 80%, 0.9)`;
        ctx.fillRect(x + 1, peakY, bw - 2, 2);
      }

      // ── Mirror reflection ─────────────────────────────────────────────────
      ctx.shadowBlur  = 0;
      ctx.globalAlpha = 0.08;
      ctx.fillStyle   = grad;
      ctx.fillRect(x + 1, H, bw - 2, -barH * 0.25);
      ctx.globalAlpha = 1;
    }

    ctx.shadowBlur = 0;

    // Idle baseline wave (when silent)
    if (!freq || freq.every(v => v < 2)) {
      this._drawIdleWave(W, H);
    }
  }

  _drawIdleWave(W, H) {
    const t   = Date.now() / 1200;
    const ctx = this.ctx;
    ctx.beginPath();
    ctx.strokeStyle = 'rgba(0, 212, 255, 0.12)';
    ctx.lineWidth   = 1.5;
    for (let x = 0; x <= W; x += 2) {
      const y = H / 2 + Math.sin(x * 0.025 + t) * 6 + Math.sin(x * 0.06 + t * 1.5) * 3;
      x === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    }
    ctx.stroke();
  }
}
