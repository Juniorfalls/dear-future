# Dear Future — Remotion math classroom

A local pipeline for short, cinematic math lessons. The classroom is a pure
HTML/CSS set rendered by Remotion, with AI-generated 2D character sprites,
KaTeX equations and edge-tts narration aligned to the frame.

## Quick start

```bash
# one-time voice env
python3 -m venv .venv-voice && .venv-voice/bin/pip install edge-tts

cd remotion
npm install

# 1. voiceover + word-level timings -> public/vo.mp3, vo_words.json, episode.json
FFMPEG=/path/to/ffmpeg ../.venv-voice/bin/python scripts/make_voice.py

# 2. animated sprites + chalk hand
../.venv/bin/python scripts/clean_sprites.py
../.venv/bin/python scripts/make_hand.py

# 3. render 1920x1080, 30 fps -> out/solving-for-x.mp4
npx remotion render MathClassroom out/solving-for-x.mp4 --crf=18
```

Preview in the browser with `npx remotion studio`.

## How it works

- `src/MathClassroom.tsx` builds the room, window, desks and whiteboard from
  absolutely positioned divs, so board text and character positions share one
  pixel coordinate system.
- Teacher and student PNGs live in `public/characters/`; walk and talk are
  six-frame loops, and the teacher switches to a pointing pose beside the board.
- Each equation line is rendered with KaTeX and revealed left-to-right by a
  clip path driven by `useCurrentFrame`. A chalk-hand sprite rides the revealed
  edge, so the writing hand follows the text.
- `scripts/make_voice.py` gets word boundaries from edge-tts, finds the spoken
  trigger for every equation and writes `public/episode.json`. Typing starts on
  the exact frame the narrator reaches the trigger word.
- The camera performs a slow push-in by scaling the whole CSS set.

## Output

- Landscape 1920×1080, 30 fps, H.264 + AAC, 15 s test.
- Rendered media stays under `remotion/out/` and is gitignored.

## Skills

`skills/cartoon-3d-short/` is copied from
[fahniazz/claude-shorts-skills](https://github.com/fahniazz/claude-shorts-skills)
and kept as workflow reference. The active set is deliberately 2D HTML/CSS,
not three.js.
