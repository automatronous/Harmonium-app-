/**
 * ChromaForge — Main Application Controller
 * Orchestrates: AudioEngine, Visualizer, Piano, Sequencer, API, Recording
 */
class ChromaForge {
  constructor() {
    this.audio      = new AudioEngine();
    this.viz        = null;
    this.piano      = null;
    this.sequencer  = null;

    this.key         = 'C';
    this.scale       = 'major';
    this.chords      = [];

    // Performance recorder
    this.recording   = false;
    this.recStart    = 0;
    this.recNotes    = [];

    // Multi-note chord detection: track recently pressed notes
    this.heldNotes   = new Set();
  }

  // ── Boot ──────────────────────────────────────────────────────────────────

  async init() {
    this._showLoading(true, 'Initialising audio…');

    await this.audio.init(p => {
      document.getElementById('load-bar').style.width = `${Math.round(p * 100)}%`;
      document.getElementById('load-text').textContent =
        `Loading samples… ${Math.round(p * 100)}%`;
    });

    // Visualiser
    this.viz = new Visualizer(
      document.getElementById('vis-canvas'), this.audio
    );
    this.viz.start();

    // Piano
    this.piano = new Piano(
      document.getElementById('piano-keys'),
      this.audio,
      (note, vel) => this._onNote(note, vel)
    );

    // Sequencer
    this.sequencer = new Sequencer(
      document.getElementById('seq-grid-wrap'),
      this.audio,
      this.piano
    );

    // Populate sequencer presets
    const presetWrap = document.getElementById('preset-btns');
    this.sequencer.presetNames.forEach(name => {
      const btn = document.createElement('button');
      btn.className   = 'tag-btn';
      btn.textContent = name;
      btn.addEventListener('click', () => this.sequencer.loadPreset(name));
      presetWrap.appendChild(btn);
    });

    await this._loadChords();
    await this._loadProgressions();
    this._bindControls();
    this._showLoading(false);

    // Entrance animation
    requestAnimationFrame(() =>
      document.getElementById('app').classList.add('ready')
    );
  }

  // ── Music Theory API ──────────────────────────────────────────────────────

  async _loadChords() {
    const res  = await fetch(`/api/chords?key=${this.key}&scale=${this.scale}`);
    const data = await res.json();
    this.chords = data.chords;
    this._renderChords(data.chords);
  }

  _renderChords(chords) {
    const wrap = document.getElementById('chord-palette');
    wrap.innerHTML = '';
    chords.forEach(chord => {
      const btn = document.createElement('button');
      btn.className = 'chord-btn';
      btn.innerHTML = `
        <span class="ch-degree">${chord.degree}</span>
        <span class="ch-name">${chord.name}</span>
        <span class="ch-notes">${chord.notes.join(' ')}</span>
      `;
      btn.addEventListener('click', () => {
        this._playChord(chord);
        document.querySelectorAll('.chord-btn').forEach(b => b.classList.remove('sel'));
        btn.classList.add('sel');
      });
      wrap.appendChild(btn);
    });
  }

  _playChord(chord) {
    chord.notes.forEach((n, i) => {
      const note = n.includes('4') || n.includes('5') ? n : `${n}4`;
      this.audio.playNote(note, 0.72 - i * 0.04);
      this.piano.flashNote(note);
    });
    this.piano.highlightNotes(chord.notes);
  }

  async _loadProgressions() {
    const res  = await fetch('/api/progressions');
    const data = await res.json();
    const wrap = document.getElementById('prog-btns');
    wrap.innerHTML = '';
    Object.entries(data).forEach(([key, prog]) => {
      const btn = document.createElement('button');
      btn.className   = 'tag-btn';
      btn.textContent = prog.name;
      btn.addEventListener('click', () => this._playProgression(prog.degrees));
      wrap.appendChild(btn);
    });
  }

  _playProgression(degrees) {
    const degMap = { I:0, II:1, III:2, IV:3, V:4, VI:5, VII:6 };
    let delay = 0;
    degrees.forEach(deg => {
      const idx = degMap[deg];
      if (idx !== undefined && this.chords[idx]) {
        setTimeout(() => this._playChord(this.chords[idx]), delay);
        delay += 900;
      }
    });
  }

  // ── Note Handling ─────────────────────────────────────────────────────────

  _onNote(note, vel) {
    // Update note display
    document.getElementById('note-display').textContent = note;

    // Record
    if (this.recording) {
      this.recNotes.push({ note, time: Date.now() - this.recStart });
    }

    // Track held notes for chord detection
    this.heldNotes.add(note.replace(/\d/, ''));
    clearTimeout(this._chordTimer);
    this._chordTimer = setTimeout(() => {
      if (this.heldNotes.size >= 2) this._detectChord();
      this.heldNotes.clear();
    }, 180);

    // Note history display
    this._pushHistory(note);
  }

  async _detectChord() {
    const noteList = [...this.heldNotes].join(',');
    try {
      const res  = await fetch(`/api/detect-chord?notes=${noteList}`);
      const data = await res.json();
      document.getElementById('chord-display').textContent = data.name;
      setTimeout(() => document.getElementById('chord-display').textContent = '—', 2500);
    } catch {}
  }

  _pushHistory(note) {
    const hist = document.getElementById('note-history');
    if (!hist) return;
    const span = document.createElement('span');
    span.className   = 'hist-note';
    span.textContent = note;
    hist.prepend(span);
    // Keep max 8
    while (hist.children.length > 8) hist.removeChild(hist.lastChild);
    // Fade-in
    requestAnimationFrame(() => span.classList.add('visible'));
  }

  // ── Recording ─────────────────────────────────────────────────────────────

  _startRec() {
    this.recording = true;
    this.recNotes  = [];
    this.recStart  = Date.now();
    document.getElementById('rec-btn').classList.add('rec-active');
    document.getElementById('rec-btn').textContent = '⏹ Stop';
    document.getElementById('play-rec').disabled = true;
  }

  _stopRec() {
    this.recording = false;
    document.getElementById('rec-btn').classList.remove('rec-active');
    document.getElementById('rec-btn').textContent = '⏺ Record';
    document.getElementById('play-rec').disabled = this.recNotes.length === 0;
  }

  _playRec() {
    if (!this.recNotes.length) return;
    this.recNotes.forEach(({ note, time }) => {
      setTimeout(() => {
        this.audio.playNote(note, 0.9);
        this.piano.flashNote(note);
        this._pushHistory(note);
      }, time);
    });
  }

  // ── UI Bindings ───────────────────────────────────────────────────────────

  _bindControls() {
    // Key / Scale
    const reloadTheory = async () => {
      this.key   = document.getElementById('key-sel').value;
      this.scale = document.getElementById('scale-sel').value;
      await this._loadChords();
    };
    document.getElementById('key-sel').addEventListener('change', reloadTheory);
    document.getElementById('scale-sel').addEventListener('change', reloadTheory);

    // Show scale highlights
    document.getElementById('show-scale').addEventListener('click', async () => {
      const res  = await fetch(`/api/scale?key=${this.key}&scale=${this.scale}`);
      const data = await res.json();
      this.piano.highlightNotes(data.notes);
    });
    document.getElementById('clear-hl').addEventListener('click', () =>
      this.piano.clearHighlights()
    );

    // Volume
    const volSlider = document.getElementById('vol');
    volSlider.addEventListener('input', e => {
      this.audio.setVolume(e.target.value / 100);
      document.getElementById('vol-val').textContent = `${e.target.value}%`;
    });

    // BPM
    document.getElementById('bpm').addEventListener('input', e => {
      this.sequencer.setBPM(parseInt(e.target.value));
      document.getElementById('bpm-val').textContent = e.target.value;
    });

    // Transport
    document.getElementById('seq-play').addEventListener('click', () => {
      this.sequencer.play();
      document.getElementById('seq-play').classList.add('active');
    });
    document.getElementById('seq-stop').addEventListener('click', () => {
      this.sequencer.stop();
      document.getElementById('seq-play').classList.remove('active');
    });
    document.getElementById('seq-clear').addEventListener('click', () =>
      this.sequencer.clear()
    );

    // Recording
    document.getElementById('rec-btn').addEventListener('click', () => {
      this.recording ? this._stopRec() : this._startRec();
    });
    document.getElementById('play-rec').addEventListener('click', () =>
      this._playRec()
    );
  }

  // ── Helpers ───────────────────────────────────────────────────────────────

  _showLoading(on, msg = '') {
    const el = document.getElementById('loading');
    el.style.display = on ? 'flex' : 'none';
    if (msg) document.getElementById('load-text').textContent = msg;
  }
}

// ── Bootstrap ─────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  const forge = new ChromaForge();

  document.getElementById('launch-btn').addEventListener('click', async () => {
    document.getElementById('splash').style.opacity = '0';
    document.getElementById('splash').style.pointerEvents = 'none';
    setTimeout(() => document.getElementById('splash').style.display = 'none', 400);
    document.getElementById('app').style.display = 'block';
    await forge.init();
  });
});
