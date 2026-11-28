# Impossible Superpowers — cinematic 3D animal documentary

A local Remotion + Three.js + Kokoro-82M pipeline for a nature-documentary
channel: a stylized 3D creature in a graded underwater set, a rotating-camera
reveal, film grain and serif title cards, narrated by a natural local voice and
cut to a documentary slot.

Series opener: **5 Animals With Impossible Superpowers**.

| # | Animal | The impossible part |
|---|--------|---------------------|
| 1 | Mantis Shrimp | punches at 50 mph, boils water into light |
| 2 | Axolotl | regrows limbs, spinal cord and brain tissue |
| 3 | Tardigrade | survives vacuum, radiation and decades of drought |
| 4 | Electric Eel | 860 volts, and it can remote-control a fish's muscles |
| 5 | Immortal Jellyfish | ages backwards into a juvenile polyp, forever |

## Quick start

```bash
# 1. voices (Kokoro-82M, CPU) — downloads ~205 MB of model into .voice-models/
scripts/install_kokoro.sh

# 2. renderer
cd remotion && npm install

# 3. write the five scripts (LLM if a key is set, curated draft otherwise)
../.venv-voice/bin/python ../scripts/generate_animal_script.py --provider none --apply 1

# 4. narration + word timings for the loaded animal
../.venv-voice/bin/python ../scripts/generate_voiceover.py

# 5. render
npx remotion render AnimalScene         out/mantis-shrimp-3d.mp4 --crf=18
npx remotion render AnimalSceneVertical out/mantis-shrimp-3d-vertical.mp4 --crf=18
npx remotion render SeriesIntro out/intro.mp4 --crf=18
npx remotion render SeriesOutro out/outro.mp4 --crf=18
```

`--provider openai|openrouter|groq|anthropic` (with the matching `*_API_KEY`)
writes a fresh script; `--dry-run` prints the exact prompt and sends nothing.

## The voice

`scripts/install_kokoro.sh` creates `.venv-voice/`, installs `kokoro-onnx`
(the official Kokoro-82M v1.0 ONNX export) and exposes a `kokoro-tts-tool`
shim with `init`, `voices` and `say`. The PyPI name `kokoro-tts-tool` does not
exist — `scripts/kokoro_tts_tool.py` is this project's implementation of it.

```bash
.venv-voice/bin/kokoro-tts-tool init                 # model + voices
.venv-voice/bin/kokoro-tts-tool voices               # af_heart, am_adam, ...
.venv-voice/bin/kokoro-tts-tool say --voice am_adam --text "..." --out vo.wav
```

`generate_voiceover.py` speaks the episode script with `af_heart` (female) by
default, normalizes to −16 LUFS, then aligns the words on the final mp3 with
faster-whisper — that is what `remotion/public/vo_words.json` contains.

## How the sync works

`remotion/public/animal.json` is the whole episode: title words, subtitle,
species, still, stat, `script`, and `cues` — 2–5 word phrases copied from the
script. `generate_voiceover.py` resolves every cue against the spoken word
times and rewrites `timeline`:

```json
"cues":     {"statAt": ["fifty", "miles", "an", "hour"]},
"timeline": {"statAt": 1.2, ...}
```

`AnimatedAnimalScene.tsx` reads `timeline` for the title stagger, the subtitle,
the counting stat reveal and the club throw: `flashAt` drives both the punch
(0 → cock → strike → recoil) and the cavitation flash. The karaoke caption
highlights each token from `vo_words.json` directly. Digits in the ASR output
("50") are expanded to number words so cues still match.

## The 3D scene

`src/AnimatedAnimalScene.tsx` renders inside `<ThreeCanvas>` from
`@remotion/three`, so every transform is a pure function of
`useCurrentFrame()` — no `useFrame`, no run-time state, scrub-safe.

- **Set** — a CSS deep-water gradient behind a transparent WebGL canvas, exponential
  fog, four additive god-ray cones, a caustic pool, four flat-shaded reef rocks
  and forty-six rising bubbles.
- **Rig** — a slow orbit + dolly, three-point underwater lighting (warm key,
  coral rim, cyan fill) and a strike point light that spikes on the punch.
- **Creature** — `src/three/MantisShrimp.tsx`, a procedural plush mantis shrimp
  built from primitives (see `3d/mantis-shrimp/`), animated with a float/bob
  cycle, per-band swim undulation, paddling legs, darting stalked eyes and a
  cocked-then-fired raptorial club with a cavitation ring.
- **Grade and type** — vignette, animated SVG grain, strike bloom, then the same
  serif title stack, stat block and letterspaced karaoke captions as before
  (`src/animal.css`).

`AnimalScene` is 1920×1080, `AnimalSceneVertical` is 1080×1920 from the same
component; `SeriesIntro` / `SeriesOutro` in `src/SeriesCard.tsx` open and close
the full documentary.

## Files

```
scripts/install_kokoro.sh        venv + kokoro-onnx + kokoro-tts-tool shim
scripts/kokoro_tts_tool.py       init / voices / say
scripts/generate_animal_script.py  LLM prompt + curated five-animal draft
scripts/generate_voiceover.py    Kokoro narration, -16 LUFS, word alignment
remotion/src/AnimatedAnimalScene.tsx  the 3D composition (ThreeCanvas + overlay)
remotion/src/three/MantisShrimp.tsx    procedural plush mantis shrimp
remotion/src/SeriesCard.tsx           intro / cast outro cards
remotion/src/animal.css               grade, typography, landscape + vertical layout
3d/mantis-shrimp/                     img2threejs spec, assessment and build notes
remotion/public/animal.json      the current episode (data only)
remotion/public/series.json      all five animals
remotion/public/animals/         episode stills
```

Rendered media stays in `remotion/out/` and is gitignored.
