# Impossible Superpowers — cinematic animal documentary engine

A local Remotion + Kokoro-82M pipeline for a nature-documentary channel.
Full-bleed cinematic stills, film-grain grade, serif title reveals and a
word-synced karaoke caption. No 3D, no classroom, no data charts.

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
npx remotion render AnimalDocLandscape out/mantis-shrimp-landscape.mp4 --crf=16
npx remotion render AnimalDocVertical  out/mantis-shrimp-vertical.mp4  --crf=16
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

`AnimalDocumentary.tsx` reads `timeline` for the title stagger, subtitle,
counting stat reveal, the light-flash on the strike, and the outro. The karaoke
caption highlights each token from `vo_words.json` directly. Digits in the ASR
output ("50") are expanded to number words so cues still match.

## Composition

`src/AnimalDocumentary.tsx` (styles in `src/animal.css`) stacks:

1. the still with a slow ken-burns push, cool/warm grade, elliptical vignette
   and animated SVG film grain;
2. a white/cyan bloom pulse on the strike cue plus a brightness kick;
3. top chrome — series eyebrow, `01 / 05` counter and progress pips;
4. lower third — serif title with per-word blur/rise, gold hairline rule,
   italic subtitle and the species binomial;
5. the stat block — counting numeral, gold unit, caps label;
6. a scrim + karaoke caption strip.

Both `AnimalDocLandscape` (1920×1080) and `AnimalDocVertical` (1080×1920) run
the same component; the vertical cut switches to a stacked lower third and a
tighter crop. Length comes from `animal.json` → `duration`, so a longer take
just makes a longer video.

## Files

```
scripts/install_kokoro.sh        venv + kokoro-onnx + kokoro-tts-tool shim
scripts/kokoro_tts_tool.py       init / voices / say
scripts/generate_animal_script.py  LLM prompt + curated five-animal draft
scripts/generate_voiceover.py    Kokoro narration, -16 LUFS, word alignment
remotion/src/AnimalDocumentary.tsx  the cinematic composition
remotion/src/animal.css          grade, typography, landscape + vertical layout
remotion/public/animal.json      the current episode (data only)
remotion/public/series.json      all five animals
remotion/public/animals/         episode stills
```

Rendered media stays in `remotion/out/` and is gitignored.
