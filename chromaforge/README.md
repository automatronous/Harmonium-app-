# 🎹 ChromaForge — Visual Music Studio

A browser-based interactive music production studio with:
- **Real piano keyboard** using your WAV samples (mouse, touch, and QWERTY keyboard)
- **Live spectrum analyser** that reacts to every note
- **16-step sequencer** for composing loops
- **Music theory engine** (Python backend) — chords, scales, progressions
- **Chord palette** — diatonic chords for any key/scale
- **Performance recorder** — record and replay your playing
- **Auto progressions** — Pop, Jazz, Blues, Classical, Emotional, Cinematic and more

---

## 🚀 Quick Start

```bash
# 1. Install dependencies (only Flask needed)
pip install flask

# 2. Run
python app.py

# 3. Open browser
#    http://127.0.0.1:5000
```

That's it. No build step, no npm, no config.

---

## ⌨️ Keyboard Shortcuts

| Key | Note |
|-----|------|
| A   | C4   |
| W   | C#4  |
| S   | D4   |
| E   | D#4  |
| D   | E4   |
| F   | F4   |
| G   | G4   |
| Y   | G#4  |
| H   | A4   |
| U   | A#4  |
| J   | B4   |
| K   | C5   |

---

## 🎵 Features

### Piano Keyboard
- Click, drag, or use keyboard shortcuts
- Real WAV sample playback via Web Audio API
- Visual key highlighting for scales and chords

### Spectrum Analyser
- Real-time FFT frequency bars
- Peak hold with decay
- Smooth logarithmic frequency mapping

### Step Sequencer
- 8 rows × 16 steps (C4–C5)
- Adjustable BPM (40–240)
- 5 built-in presets: Arpeggio, Scale Run, Bounce, Groove, Waltz
- Drag to paint multiple cells

### Music Theory (Python Backend)
- Diatonic chord palette for any key + scale
- 10 scales: Major, Minor, Pentatonic, Blues, Dorian, Phrygian, Lydian, Mixolydian, Harmonic Minor, Whole Tone
- 8 chord progressions: Pop, Jazz, Blues, Classical, Emotional, Epic, Andalusian, Royal
- Real-time chord detection while playing

### Performance Recorder
- Record your piano performance
- Play it back at any time

---

## 🏗 Architecture

```
chromaforge/
├── app.py               Flask backend + music theory API
├── requirements.txt
├── static/
│   ├── sounds/          12 WAV samples (C4–C5 chromatic)
│   ├── css/style.css    Dark DAW aesthetic
│   └── js/
│       ├── audio.js     Web Audio API engine
│       ├── visualizer.js Canvas spectrum renderer
│       ├── piano.js     Piano keyboard component
│       ├── sequencer.js 16-step grid sequencer
│       └── app.js       Main controller
└── templates/
    └── index.html       Single-page app shell
```

---

## 🛠 Upgrade Ideas

1. **Multiple octaves** — extend the piano to 2–3 octaves
2. **MIDI support** — connect a hardware MIDI keyboard via Web MIDI API
3. **Export** — render the sequencer pattern to a WAV file using Python's `wave` module
4. **Effects chain** — add reverb, delay, and filter with Web Audio nodes
5. **AI suggestions** — use an ML model to suggest next notes based on what you've played
6. **Collaborative** — add WebSockets for multi-user jam sessions
7. **Pattern save/load** — persist sequencer patterns to a JSON file or database
8. **Drum machine** — add a parallel percussion track with hi-hat, kick, snare samples
