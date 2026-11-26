# Dear Future — 2.5D math lessons

A local pipeline for short, cinematic math lessons: three.js renders a warm 2.5D
classroom, edge-tts narrates at a brisk pace with word-level timings, and
Playwright captures deterministic frames into an MP4.

## Quick start

```bash
# one-time: three.js + GSAP kit and the voice environment
(cd vendor/claude-animation-skills/kit && npm install && curl -fsSL \
  https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js -o vendor/gsap.min.js)
python3 -m venv .venv-voice && .venv-voice/bin/pip install edge-tts

# 1. voiceover + word timings  -> math_engine/assets/vo.{mp3,wav}, vo_words.json
.venv-voice/bin/python voiceover_edge.py

# 2. render the 2.5D scene     -> out/math_engine/*.mp4
.venv/bin/python render_math.py --out out/math_engine/math-classroom-2.5d.mp4

# fast look at four frames
.venv/bin/python render_math.py --stills 0.6,2.9,6.0,8.2
```

## Scene

`math_engine/scene.js` builds the room with real perspective and shadows:
warm walls, a wooden floor, a framed whiteboard, a sunny window, desks, three
students seen from behind, and a consistent teacher with shirt, tie, trousers
and articulated arms. The whiteboard is a canvas texture whose lines reveal in
sync with the narration; the camera performs a slow push-in. Captions are
composited onto the captured frame and switch on edge-tts word boundaries.

## Voice

`voiceover_edge.py` uses `en-US-GuyNeural` at `+15%`, writes `vo_words.json`
(exact word starts and ends), and converts to 48 kHz mono. The render script
loudness-normalises the mix to −16 LUFS.

## Notes

- Frames are captured as JPEG and encoded at 30 fps, 1920×1080, H.264 + AAC.
- `vendor/claude-animation-skills` supplies three.js; `vendor/motion-video-skills`
  supplies the voiceover workflow reference.
- The retired canvas stickman engine, its TTS, horror audio and episode files
  have been removed.
