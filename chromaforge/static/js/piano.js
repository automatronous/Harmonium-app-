/**
 * ChromaForge Piano Keyboard
 * Renders an interactive one-octave chromatic keyboard (C4–C5).
 * Input: mouse drag, touch, and QWERTY keyboard shortcuts.
 */
class Piano {
  constructor(container, audio, onNote) {
    this.container = container;
    this.audio     = audio;
    this.onNote    = onNote;     // callback(note, velocity)
    this.held      = new Set();  // keys currently held

    // White keys C4→C5 (8 keys)
    this.WHITE = ['C4', 'D4', 'E4', 'F4', 'G4', 'A4', 'B4', 'C5'];
    this.WHITE_NAMES = ['C', 'D', 'E', 'F', 'G', 'A', 'B', 'C'];

    // Black keys: note → left% position relative to white-key container
    // 8 white keys each = 12.5% wide
    // Black key centres at ~65% through the preceding white key
    this.BLACK = [
      { note: 'C#4', left: 8.2  },
      { note: 'D#4', left: 20.7 },
      //  no F# sample
      { note: 'G#4', left: 58.2 },
      { note: 'A#4', left: 70.7 },
    ];

    // Keyboard map: QWERTY key → note
    this.KB_MAP = {
      'a': 'C4', 'w': 'C#4', 's': 'D4', 'e': 'D#4',
      'd': 'E4', 'f': 'F4',
      'g': 'G4', 'y': 'G#4', 'h': 'A4', 'u': 'A#4',
      'j': 'B4', 'k': 'C5',
    };

    this._render();
    this._bind();
  }

  // ── Render ────────────────────────────────────────────────────────────────

  _render() {
    this.container.innerHTML = '';

    // White keys row
    this.WHITE.forEach((note, i) => {
      const el = this._makeKey(note, 'white-key');
      const lbl = document.createElement('span');
      lbl.className   = 'key-label';
      lbl.textContent = this.WHITE_NAMES[i];
      el.appendChild(lbl);
      this.container.appendChild(el);
    });

    // Black keys (absolutely positioned)
    this.BLACK.forEach(({ note, left }) => {
      const el = this._makeKey(note, 'black-key');
      el.style.left = `${left}%`;
      this.container.appendChild(el);
    });
  }

  _makeKey(note, cls) {
    const el = document.createElement('div');
    el.className    = `piano-key ${cls}`;
    el.dataset.note = note;
    return el;
  }

  // ── Events ────────────────────────────────────────────────────────────────

  _bind() {
    // Mouse
    this.container.addEventListener('mousedown', e => {
      const k = e.target.closest('.piano-key');
      if (k) { e.preventDefault(); this._press(k.dataset.note, true); }
    });
    // Drag over other keys while mouse held
    this.container.addEventListener('mouseover', e => {
      if (!e.buttons) return;
      const k = e.target.closest('.piano-key');
      if (k && !this.held.has(k.dataset.note)) this._press(k.dataset.note, true);
    });
    document.addEventListener('mouseup', () => {
      this.held.forEach(n => this._release(n));
    });

    // Touch
    this.container.addEventListener('touchstart', e => {
      e.preventDefault();
      [...e.changedTouches].forEach(t => {
        const el = document.elementFromPoint(t.clientX, t.clientY)?.closest('.piano-key');
        if (el) this._press(el.dataset.note, true);
      });
    }, { passive: false });
    this.container.addEventListener('touchend', e => {
      e.preventDefault();
      [...e.changedTouches].forEach(t => {
        const el = document.elementFromPoint(t.clientX, t.clientY)?.closest('.piano-key');
        if (el) this._release(el.dataset.note);
      });
    }, { passive: false });

    // Keyboard
    document.addEventListener('keydown', e => {
      if (e.repeat || e.target.tagName === 'SELECT' || e.target.tagName === 'INPUT') return;
      const note = this.KB_MAP[e.key.toLowerCase()];
      if (note) this._press(note, true);
    });
    document.addEventListener('keyup', e => {
      const note = this.KB_MAP[e.key.toLowerCase()];
      if (note) this._release(note);
    });
  }

  _press(note, fromUser = false) {
    if (this.held.has(note)) return;
    this.held.add(note);
    this._setActive(note, true);
    this.audio.playNote(note, fromUser ? 1.0 : 0.75);
    if (this.onNote) this.onNote(note, 1.0);
  }

  _release(note) {
    this.held.delete(note);
    this._setActive(note, false);
  }

  _setActive(note, on) {
    const el = this.container.querySelector(`[data-note="${note}"]`);
    if (el) el.classList.toggle('active', on);
  }

  // ── Public API ────────────────────────────────────────────────────────────

  /** Highlight keys belonging to a scale / chord (external call) */
  highlightNotes(notes) {
    this.container.querySelectorAll('.piano-key')
      .forEach(k => k.classList.remove('highlighted'));
    notes.forEach(note => {
      // Accept bare names like 'C' → try C4 first, then C5
      const candidates = note.includes('4') || note.includes('5')
        ? [note]
        : [`${note}4`, `${note}5`];
      candidates.forEach(n => {
        const el = this.container.querySelector(`[data-note="${n}"]`);
        if (el) el.classList.add('highlighted');
      });
    });
  }

  clearHighlights() {
    this.container.querySelectorAll('.piano-key')
      .forEach(k => k.classList.remove('highlighted'));
  }

  /** Visually flash a key (for sequencer playback) */
  flashNote(note) {
    const el = this.container.querySelector(`[data-note="${note}"]`);
    if (!el) return;
    el.classList.add('active');
    setTimeout(() => el.classList.remove('active'), 180);
  }
}
