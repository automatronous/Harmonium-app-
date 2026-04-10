"""
ChromaForge — Visual Music Production Studio
Flask backend: serves the app + music theory API
"""

from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

# ─── Music Theory Data ────────────────────────────────────────────────────────

CHROMATIC = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

SCALES = {
    'major':           {'intervals': [0, 2, 4, 5, 7, 9, 11], 'label': 'Major'},
    'natural_minor':   {'intervals': [0, 2, 3, 5, 7, 8, 10], 'label': 'Natural Minor'},
    'pentatonic_major':{'intervals': [0, 2, 4, 7, 9],        'label': 'Pentatonic Major'},
    'pentatonic_minor':{'intervals': [0, 3, 5, 7, 10],       'label': 'Pentatonic Minor'},
    'blues':           {'intervals': [0, 3, 5, 6, 7, 10],    'label': 'Blues'},
    'dorian':          {'intervals': [0, 2, 3, 5, 7, 9, 10], 'label': 'Dorian'},
    'phrygian':        {'intervals': [0, 1, 3, 5, 7, 8, 10], 'label': 'Phrygian'},
    'lydian':          {'intervals': [0, 2, 4, 6, 7, 9, 11], 'label': 'Lydian'},
    'mixolydian':      {'intervals': [0, 2, 4, 5, 7, 9, 10], 'label': 'Mixolydian'},
    'harmonic_minor':  {'intervals': [0, 2, 3, 5, 7, 8, 11], 'label': 'Harmonic Minor'},
    'whole_tone':      {'intervals': [0, 2, 4, 6, 8, 10],    'label': 'Whole Tone'},
}

CHORD_INTERVALS = {
    'major':   [0, 4, 7],
    'minor':   [0, 3, 7],
    'dim':     [0, 3, 6],
    'aug':     [0, 4, 8],
    'maj7':    [0, 4, 7, 11],
    'min7':    [0, 3, 7, 10],
    'dom7':    [0, 4, 7, 10],
    'sus2':    [0, 2, 7],
    'sus4':    [0, 5, 7],
    'dim7':    [0, 3, 6, 9],
    'hdim7':   [0, 3, 6, 10],
}

CHORD_SUFFIX = {
    'major': '', 'minor': 'm', 'dim': '°', 'aug': '+',
    'maj7': 'maj7', 'min7': 'm7', 'dom7': '7',
    'sus2': 'sus2', 'sus4': 'sus4', 'dim7': '°7', 'hdim7': 'ø7',
}

# Diatonic qualities for 7-note scales
SCALE_DIATONIC = {
    'major':          ['major', 'minor', 'minor', 'major', 'major', 'minor', 'dim'],
    'natural_minor':  ['minor', 'dim',   'major', 'minor', 'minor', 'major', 'major'],
    'dorian':         ['minor', 'minor', 'major', 'major', 'minor', 'dim',   'major'],
    'phrygian':       ['minor', 'major', 'major', 'minor', 'dim',   'major', 'minor'],
    'lydian':         ['major', 'major', 'minor', 'dim',   'major', 'minor', 'minor'],
    'mixolydian':     ['major', 'minor', 'dim',   'major', 'minor', 'minor', 'major'],
    'harmonic_minor': ['minor', 'dim',   'aug',   'minor', 'major', 'major', 'dim'],
}

PROGRESSIONS = {
    'pop':       {'name': 'Pop Anthem',    'degrees': ['I',  'V',  'VI', 'IV']},
    'jazz':      {'name': 'Jazz ii-V-I',   'degrees': ['II', 'V',  'I',  'VI']},
    'blues':     {'name': '12-Bar Blues',  'degrees': ['I',  'I',  'I',  'I',  'IV', 'IV', 'I',  'I',  'V',  'IV', 'I',  'V']},
    'classical': {'name': 'Classical Cadence', 'degrees': ['I', 'IV', 'V', 'I']},
    'emotional': {'name': 'Emotional',     'degrees': ['VI', 'IV', 'I',  'V']},
    'epic':      {'name': 'Epic/Cinematic','degrees': ['I',  'VI', 'III','VII']},
    'andalusian':{'name': 'Andalusian',    'degrees': ['I',  'VII','VI', 'V']},
    'royal':     {'name': 'Royal',         'degrees': ['I',  'IV', 'VI', 'V']},
}

ROMAN = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII']

# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/chords')
def get_chords():
    key   = request.args.get('key',   'C')
    scale = request.args.get('scale', 'major')

    root_i    = CHROMATIC.index(key) if key in CHROMATIC else 0
    scale_cfg = SCALES.get(scale, SCALES['major'])
    intervals = scale_cfg['intervals']
    qualities = SCALE_DIATONIC.get(scale, SCALE_DIATONIC['major'])

    chords = []
    for i, semitones in enumerate(intervals[:7]):
        ni      = (root_i + semitones) % 12
        quality = qualities[i] if i < len(qualities) else 'major'
        cints   = CHORD_INTERVALS[quality]
        cnotes  = [CHROMATIC[(ni + x) % 12] for x in cints]
        suffix  = CHORD_SUFFIX[quality]
        chords.append({
            'degree':  ROMAN[i],
            'root':    CHROMATIC[ni],
            'quality': quality,
            'name':    f'{CHROMATIC[ni]}{suffix}',
            'notes':   cnotes,
        })

    return jsonify({'key': key, 'scale': scale, 'chords': chords})


@app.route('/api/scale')
def get_scale():
    key   = request.args.get('key',   'C')
    scale = request.args.get('scale', 'major')

    root_i    = CHROMATIC.index(key) if key in CHROMATIC else 0
    scale_cfg = SCALES.get(scale, SCALES['major'])
    notes     = [CHROMATIC[(root_i + i) % 12] for i in scale_cfg['intervals']]

    return jsonify({'key': key, 'scale': scale, 'notes': notes,
                    'label': scale_cfg['label']})


@app.route('/api/progressions')
def get_progressions():
    return jsonify(PROGRESSIONS)


@app.route('/api/scales')
def get_scales():
    return jsonify({k: v['label'] for k, v in SCALES.items()})


@app.route('/api/detect-chord')
def detect_chord():
    """Given a comma-separated list of note names, return the chord name."""
    raw   = request.args.get('notes', '')
    notes = [n.strip() for n in raw.split(',') if n.strip()]
    if len(notes) < 2:
        return jsonify({'name': notes[0] if notes else '—', 'quality': 'note'})

    root_i    = CHROMATIC.index(notes[0]) if notes[0] in CHROMATIC else 0
    semitones = sorted({(CHROMATIC.index(n) - root_i) % 12 for n in notes if n in CHROMATIC})

    for ctype, cint in CHORD_INTERVALS.items():
        if semitones == sorted(cint):
            suffix = CHORD_SUFFIX[ctype]
            return jsonify({'name': f'{notes[0]}{suffix}', 'quality': ctype,
                            'root': notes[0]})

    return jsonify({'name': f'{notes[0]}?', 'quality': 'unknown'})


# ─── Run ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print('\n  🎹  ChromaForge starting at  http://127.0.0.1:5000\n')
    app.run(debug=True, port=5000)
