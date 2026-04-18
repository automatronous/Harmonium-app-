# SoundFonts for Astra Keys

Place your `.sf2` files in this folder.

Recommended naming:

- `default.sf2`
  Use a full General MIDI SoundFont such as `FluidR3_GM.sf2`, `Timbres of Heaven.sf2`, or another GM-compatible bank.
- `indian.sf2`
  Optional second SoundFont for Indian instruments. If its filename contains words like `indian`, `tabla`, `bansuri`, or `ethnic`, the app will try to route Indian presets to it first.

Startup behavior:

1. `main.py` launches the app immediately.
2. If this folder contains one or more `.sf2` files, the first one is loaded automatically.
3. You can also load a SoundFont from the app UI, and the app will copy it into this folder.

Notes:

- The app uses `pyFluidSynth`, so Windows also needs the native FluidSynth library available on the system path.
- If you only have one GM SoundFont, the app still works. Indian voices will use the closest compatible program in that SoundFont.
