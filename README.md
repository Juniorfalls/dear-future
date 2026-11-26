# Dear Future — Kinetic Data Visualizer

A local Remotion engine for premium finance explainers. Clean dark-slate
frames, SVG charts that build on the spoken word, edge-tts narration and
synthesized sound cues. No characters, no classroom.

## Quick start

```bash
python3 -m venv .venv-voice && .venv-voice/bin/pip install edge-tts

cd remotion
npm install

# voice + trigger times -> public/vo_beat.mp3, vo_words.json, beat.json
FFMPEG=/path/to/ffmpeg ../.venv-voice/bin/python scripts/make_beat.py

# sound effects -> public/sfx/{down,up,thud}.wav
../.venv/bin/python scripts/make_sfx.py

# render the 3-minute episode in both formats
npx remotion render DataVisualizer out/the-50-percent-trap-landscape.mp4 --crf=18
npx remotion render DataVisualizerVertical out/the-50-percent-trap-vertical.mp4 --crf=18
```

## The five beats

1. **The Hook** — $100 cut by 50%, then +50% lands at $75.
2. **The Shrinking Base** — ten $10 blocks, one leaves, a $9 recovery is narrower.
3. **The Asymmetry Curve** — recovery bars for −10/−25/−50/−80% losses.
4. **Real-World Traps** — discount-then-tax ($96) and rollercoaster paths ($110.25 vs $75).
5. **The Mental Rule** — a seesaw balancing loss against required gain on a smaller base.

Both `DataVisualizer` (1920×1080) and `DataVisualizerVertical` (1080×1920)
render the same 5400-frame, 180-second timeline.

## The Beat 1 chart

`src/DataVisualizer.tsx` draws the whole chart in SVG over a `#1E232B` stage:

- a teal `$100` bar grows from the baseline;
- a coral `−50%` slice cuts the top half away and slides off, leaving `$50`;
- a gold `+50%` block stacks on top and settles at `$75`;
- a dashed white line marks the original `$100`, and a gold bracket measures
  the `$25` gap;
- a right-side ledger reveals START / AFTER −50% / AFTER +50%.

Every element is keyed to `beat.json` triggers found in the edge-tts word
timings, so the cut, gain, landing, dashed line and gap all land on the exact
spoken phrase. `scripts/make_beat.py` also routes the narration through
loudness normalization (`−16 LUFS`).

## Sound

`scripts/make_sfx.py` synthesizes three cues: a soft downward slide on the
cut, an upward two-note chime on the gain, and a low thud when the block
settles. They sit low under the voice.

## Skills / notes

`skills/write-script/` and `skills/remotion-editing/` remain as reference for
script structure and pre-render QA. Rendered media stays in `remotion/out/` and
is gitignored.
