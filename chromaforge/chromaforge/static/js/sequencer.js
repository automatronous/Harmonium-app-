/**
 * ChromaForge Step Sequencer
 * 16-column × 8-row grid for composing melodic loops.
 * Uses setTimeout-based scheduling for portability (no AudioWorklet needed).
 */
class Sequencer {
  constructor(container, audio, piano) {
    this.container = container;
    this.audio     = audio;
    this.piano     = piano;

    this.STEPS   = 16;
    this.bpm     = 120;
    this.playing = false;
    this.step    = -1;
    this._tid    = null;

    // Rows: top = highest pitch
    this.ROWS = ['C5', 'B4', 'A4', 'G4', 'F4', 'E4', 'D4', 'C4'];
    this.LABELS = ['C5', 'B', 'A', 'G', 'F', 'E', 'D', 'C'];

    // grid[row][step] = true/false
    this.grid = this.ROWS.map(() => new Array(this.STEPS).fill(false));

    // Built-in presets: [row, step] pairs
    this.PRESETS = {
      'Arpeggio': [
        [7,0],[5,1],[3,2],[0,3],[7,4],[5,5],[3,6],[0,7],
        [7,8],[5,9],[3,10],[0,11],[7,12],[5,13],[3,14],[0,15],
      ],
      'Scale Run': [
        [7,0],[6,2],[5,4],[4,6],[3,8],[2,10],[1,12],[0,14],
      ],
      'Bounce': [
        [0,0],[7,2],[0,4],[7,6],[0,8],[7,10],[0,12],[7,14],
        [3,1],[3,5],[3,9],[3,13],
      ],
      'Groove': [
        [7,0],[7,4],[7,8],[7,12],
        [3,2],[3,6],[3,10],[3,14],
        [5,1],[5,9],
      ],
      'Waltz': [
        [7,0],[7,4],[7,8],[7,12],
        [5,2],[5,6],[3,10],[3,14],
        [0,1],[2,5],[4,9],[1,13],
      ],
    };

    this._render();
  }

  // ── Render ────────────────────────────────────────────────────────────────

  _render() {
    this.container.innerHTML = '';
    const grid = document.createElement('div');
    grid.className = 'seq-grid';

    this.ROWS.forEach((note, ri) => {
      const row = document.createElement('div');
      row.className = 'seq-row';

      const lbl = document.createElement('div');
      lbl.className   = 'seq-row-label';
      lbl.textContent = this.LABELS[ri];
      row.appendChild(lbl);

      const cells = document.createElement('div');
      cells.className = 'seq-cells';

      for (let si = 0; si < this.STEPS; si++) {
        const cell = document.createElement('div');
        cell.className = `seq-cell${si % 4 === 0 ? ' beat' : ''}`;
        cell.dataset.row  = ri;
        cell.dataset.step = si;

        cell.addEventListener('click', () => this._toggle(ri, si, cell));

        // Drag support
        cell.addEventListener('mouseenter', e => {
          if (e.buttons === 1) this._toggle(ri, si, cell, true);
        });

        cells.appendChild(cell);
      }

      row.appendChild(cells);
      grid.appendChild(row);
    });

    this.container.appendChild(grid);
    this._gridEl = grid;
  }

  _toggle(ri, si, cell, onlyOn = false) {
    if (onlyOn && this.grid[ri][si]) return;
    this.grid[ri][si] = !this.grid[ri][si];
    cell.classList.toggle('on', this.grid[ri][si]);
  }

  // ── Transport ─────────────────────────────────────────────────────────────

  play() {
    if (this.playing) return;
    this.playing = true;
    this.step    = -1;
    this._tick();
  }

  stop() {
    this.playing = false;
    if (this._tid) clearTimeout(this._tid);
    this._clearCursor();
    this.step = -1;
  }

  _tick() {
    if (!this.playing) return;
    this.step = (this.step + 1) % this.STEPS;
    this._moveCursor(this.step);

    // Trigger active notes
    this.ROWS.forEach((note, ri) => {
      if (this.grid[ri][this.step]) {
        this.audio.playNote(note, 0.8);
        this.piano?.flashNote(note);
      }
    });

    const ms = (60 / this.bpm / 4) * 1000; // 16th-note interval
    this._tid = setTimeout(() => this._tick(), ms);
  }

  _moveCursor(step) {
    this._gridEl.querySelectorAll('.seq-cell').forEach(c => c.classList.remove('cursor'));
    this._gridEl.querySelectorAll(`[data-step="${step}"]`)
      .forEach(c => c.classList.add('cursor'));
  }

  _clearCursor() {
    this._gridEl?.querySelectorAll('.seq-cell').forEach(c => c.classList.remove('cursor'));
  }

  // ── Controls ──────────────────────────────────────────────────────────────

  setBPM(bpm) { this.bpm = bpm; }

  clear() {
    this.grid = this.ROWS.map(() => new Array(this.STEPS).fill(false));
    this._gridEl.querySelectorAll('.seq-cell').forEach(c => c.classList.remove('on'));
  }

  loadPreset(name) {
    const pattern = this.PRESETS[name];
    if (!pattern) return;
    this.clear();
    pattern.forEach(([ri, si]) => {
      if (ri < this.ROWS.length && si < this.STEPS) {
        this.grid[ri][si] = true;
        const cell = this._gridEl.querySelector(`[data-row="${ri}"][data-step="${si}"]`);
        if (cell) cell.classList.add('on');
      }
    });
  }

  get presetNames() { return Object.keys(this.PRESETS); }
}
