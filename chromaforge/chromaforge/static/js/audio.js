/**
 * ChromaForge Audio Engine
 * Web Audio API wrapper: sample loading, polyphonic playback, analyser for visualiser
 */
class AudioEngine {
  constructor() {
    this.ctx        = null;
    this.analyser   = null;
    this.masterGain = null;
    this.buffers    = {};
    this.loading    = false;

    // Map note names → WAV filenames in /static/sounds/
    this.NOTE_FILES = {
      'C4':  'c1.wav',
      'C#4': 'c1s.wav',
      'D4':  'd1.wav',
      'D#4': 'd1s.wav',
      'E4':  'e1.wav',
      'F4':  'f1.wav',
      'G4':  'g1.wav',
      'G#4': 'g1s.wav',
      'A4':  'a1.wav',
      'A#4': 'a1s.wav',
      'B4':  'b1.wav',
      'C5':  'c2.wav',
    };
  }

  async init(onProgress) {
    this.ctx = new (window.AudioContext || window.webkitAudioContext)();

    // Master gain  → analyser → destination
    this.masterGain = this.ctx.createGain();
    this.masterGain.gain.value = 0.85;

    this.analyser = this.ctx.createAnalyser();
    this.analyser.fftSize            = 2048;
    this.analyser.smoothingTimeConstant = 0.88;

    this.masterGain.connect(this.analyser);
    this.analyser.connect(this.ctx.destination);

    await this._loadSamples(onProgress);
  }

  async _loadSamples(onProgress) {
    const entries = Object.entries(this.NOTE_FILES);
    let loaded = 0;
    await Promise.all(entries.map(async ([note, file]) => {
      try {
        const res = await fetch(`/static/sounds/${file}`);
        const buf = await res.arrayBuffer();
        this.buffers[note] = await this.ctx.decodeAudioData(buf);
      } catch (e) {
        console.warn(`[Audio] Failed to load ${file}`, e);
      } finally {
        loaded++;
        if (onProgress) onProgress(loaded / entries.length);
      }
    }));
  }

  /** Resume context after user gesture (required by browsers) */
  resume() {
    if (this.ctx && this.ctx.state === 'suspended') this.ctx.resume();
  }

  /**
   * Play a note.
   * @param {string} note   e.g. 'C4'
   * @param {number} velocity  0–1
   * @param {number} duration  seconds (0 = let sample play naturally)
   */
  playNote(note, velocity = 1.0, duration = 0) {
    if (!this.ctx || !this.buffers[note]) return null;
    this.resume();

    const src  = this.ctx.createBufferSource();
    src.buffer = this.buffers[note];

    const gain = this.ctx.createGain();
    gain.gain.setValueAtTime(velocity * 0.9, this.ctx.currentTime);

    // Natural decay envelope
    const decayTime = duration > 0 ? duration : 3.5;
    gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + decayTime);

    src.connect(gain);
    gain.connect(this.masterGain);
    src.start(0);

    return { src, gain };
  }

  /** Frequency data for the visualiser (Uint8Array) */
  getFreqData() {
    if (!this.analyser) return null;
    const data = new Uint8Array(this.analyser.frequencyBinCount);
    this.analyser.getByteFrequencyData(data);
    return data;
  }

  setVolume(v) {
    if (this.masterGain) this.masterGain.gain.value = Math.max(0, Math.min(1.5, v));
  }

  get notes() { return Object.keys(this.NOTE_FILES); }
}
