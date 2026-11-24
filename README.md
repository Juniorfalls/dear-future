# Before You: Buy / Play / Watch

Fast-cut review videos: stock footage, gameplay or trailers as the full-bleed
background, one image of the actual subject floating in the middle, and bold
outlined subtitles carrying the verdict.

The old history/documentary pipeline (`generate_video.py`, the Fall of Rome
episode, Pollinations prompts and its narration) has been removed. The
reference-film subtitle system, music bed, colour grades and optional presenter
layouts from the previous pass are retained.

## Pipeline

```
fetch_media.py "iPhone 15" --format buy
        │
        ├─ remotion/public/episodes/iphone-15/bg-1..N.mp4   background clips
        ├─ remotion/public/episodes/iphone-15/subject.jpg   subject overlay
        ├─ remotion/public/episodes/iphone-15/credits.json  source + licence
        └─ remotion/data/scenes.json                        Remotion scene list
                │
                └─ remotion/src/CinematicDoc.tsx
                     OffthreadVideo  → full-screen background
                     Img             → floating subject with drop shadow
                     Oswald italic   → thick outlined pop-on subtitles
```

## Quick start

```bash
# 1. Python + Node dependencies
python -m pip install -r requirements.txt
cd remotion && npm ci && cd ..

# 2. A free Pexels key: https://www.pexels.com/api/
export PEXELS_API_KEY="your-key"

# 3. Download footage + subject image and write the scene list
python fetch_media.py "iPhone 15" --format buy

# 4. Render
cd remotion && node render.js
```

Output: `remotion/out/cinematic_video.mp4` (1920×1080). Add `--vertical` to
`render.js` for 1080×1920 shorts.

### Test render without an API key

`--test` uses a stable pool of public Mixkit phone clips and fetches the subject
image from Wikimedia Commons, so the pipeline can be exercised before the
Pexels key exists:

```bash
python fetch_media.py "iPhone 15" --format buy --test
cd remotion && node render.js
```

The committed iPhone 15 test episode was produced this way.

## Stickman horror pipeline (active, CPU-only)

The GPU/AnimateDiff renderer is retired and archived in `archive_animatdiff/`.
The active horror engine is `make_horror_stickman.py`: it reads the same episode
schema, draws the scenes with the [stickman skill](https://github.com/krishnagoswami52/stickman-skill)
(Canvas + Playwright), speaks the voiceover with Kokoro-82M, mixes sound and
encodes an MP4. No GPU, no paid API.

```bash
# one-time setup
python3 -m venv .venv
.venv/bin/pip install -r requirements-stickman.txt
.venv/bin/python -m playwright install chromium

# 15-second Fog Ridge test (first run also downloads the ~350 MB voice model)
.venv/bin/python make_horror_stickman.py --shots 1-5 --max-seconds 15

# full episode, dark narrator
.venv/bin/python make_horror_stickman.py --voice am_onyx
```

Output: `out/stickman/silence-on-the-fog-ridge-test.mp4`. The working film
folder is `out/stickman/film/` (`film.js`, `vo.wav`, `audio.wav`, shots). The
wrapper auto-clones the skill into `vendor/stickman-skill/` if it is missing;
set `STICKMAN_SKILL_DIR` to use another install. The wrapper currently renders
the 2D route; the skill's 3D route is available upstream when a scene needs a
real camera orbit.

## Episode options

| Flag | Default | Meaning |
| --- | --- | --- |
| `--format buy\|play\|watch` | `buy` | Selects the caption beats and kicker labels. |
| `--clips 3-5` | `4` | Number of background clips to download. |
| `--scene-seconds` | `4` | Requested hold per clip, capped to the clip length. |
| `--image PATH` | auto | Use a local product/game/film image instead. |
| `--out PATH` | `remotion/data/scenes.json` | Where to write the scene list. |
| `--test` | off | Force the keyless public-clip fallback. |

## Scene schema

```json
{
  "title": "Before You",
  "topic": "iPhone 15",
  "style": {"letterbox": false, "atmosphereOpacity": 0, "lightSweep": false,
            "vignette": false, "wordmark": "intro", "scrim": 0.2},
  "audio": {"src": "audio/bg_music.mp3", "volume": 0.12, "loop": true},
  "scenes": [
    {
      "video_url": "episodes/iphone-15/bg-1.mp4",
      "image_url": "episodes/iphone-15/subject.jpg",
      "text": "Before you buy the iPhone 15...",
      "layout": "broll_only",
      "transition": "cut",
      "grade": "neutral",
      "kicker": "BEFORE YOU BUY",
      "durationInSeconds": 3.5
    }
  ]
}
```

- `video_url` — full-bleed background, rendered with `<OffthreadVideo>`.
- `image_url` — with a video, this opens as the floating subject overlay. With
  no video it stays a legacy full-bleed still.
- `text` — narration line; it is automatically chunked into short subtitles.
  Pass explicit `captions: [{text, from, to}]` to control the cues.
- `layout` — `broll_only` for this channel. `host_pip` / `host_full` keep the
  earlier presenter framing available.
- `transition` — `cut` (default) or `crossfade`; `grade` — `cold`, `warm`,
  `neutral`.

Paths are relative to `remotion/public`. Absolute `http(s)` URLs also work.

## Look

- Full-bleed footage with a slow push-in and hard cuts.
- Floating subject image with a spring settle, slow float and deep shadow.
- Oswald bold italic caps, white fill over a 6px black stroke, chunked so a
  line never sits on screen longer than ~1.6s.
- Yellow `BEFORE YOU ...` kicker above the subtitle, optional brand wordmark on
  the opening shot, short fade-out.
- Music bed at low volume; the bundled track is CC0.

## Credits and licensing

Every run writes `remotion/public/episodes/<topic>/credits.json` with the
Pexels creator, source page and Wikimedia licence where relevant. Pexels and
Mixkit do not require attribution, but keep the file with the episode so the
source is always known. Check the licence before publishing footage from any
other source.

## Continuous integration

`.github/workflows/render.yml` renders on push to `main` and via **Run
workflow**. Add `PEXELS_API_KEY` as a repository secret for real footage;
without it the workflow automatically falls back to `--test` clips.

## Requirements

- Python 3.10+ and `requests`
- Node 18+ (CI uses Node 20)
- `ffmpeg`/`ffprobe` on `PATH` (optional, used to cap scene length to the clip)

## Optional extras kept from the reference pass

- `generate_voice.py` + `requirements-voice.txt`: local Kokoro narration for any
  `remotion/data/script.json` you provide. `voice` blocks in `scenes.json` size
  each shot to its spoken line.
- `REFERENCE_VIDEO_ANALYSIS.md`: measurements behind the subtitle, grade and
  cut style.
- `remotion/public/host/presenter.mp4` and the `host_*` layouts.
- `generate_video_free.py` and the AnimateDiff helpers now live in
  `archive_animatdiff/` and are reference-only.
- `generate_script.py`: topic in, 12-shot `episode_schema.json` out (below).
- `sound_design.sh`: the canonical teaser build — grades the nine clips and
  synthesises the drone/riser/stinger bed from committed inputs.
- `sound_design_mix.sh`: an alternative audio stage for an already-graded
  picture (bed duck + two-pass R128 + delivery check).

## Writing an episode script

`episode_schema.json` used to be hand-written. `generate_script.py` writes it
from a topic, so a new 60 s episode is data entry plus one API call:

```bash
python3 generate_script.py "A haunted asylum"
python3 generate_script.py "A flooded car park" --seed 4 --out /tmp/ep.json --overwrite
python3 generate_script.py --offline "shapes test" --out /tmp/ep.json --overwrite
.venv/bin/python make_horror_stickman.py --episode /tmp/ep.json --max-seconds 30
```

The LLM is Pollinations' classic text API — free, keyless, **one anonymous
request per IP every 45 s**. So the script makes exactly one call and gets the
story and all twelve beats back together; a second call would mean waiting out
the slot. It sends **no** `Authorization` header (a dummy key turns a working
anonymous call into a 402) unless `POLLINATIONS_TOKEN` holds a real
`enter.pollinations.ai` key. On 402/429 it honours `Retry-After` up to
`--max-wait` (120 s).

Every field is validated, because a bad duration or a missing line breaks the
render silently later:

- a **cast of 2–3 characters**, each with `id`, `name`, `role`
  (`protagonist` / `antagonist` / `victim` / `supporting`), a prompt-safe
  `look` (clothing, hair, build — never a face), a full `reference` block
  (`age`, `hair`, `clothing`, `features`, `build`) and a generated
  `reference_prompt` for drawing a character sheet. Sheets may show faces;
  AnimateDiff shots may not.
- **exactly one focus character per shot.** A two-hander is written as
  coverage — `shot_type` is one of `wide`, `medium`, `close_up`,
  `over_shoulder`, `insert`, `pov` — instead of two bodies in one frame. A
  model that returns a list of focuses is trimmed to the first, with a warning.
  The only legal second body is `foreground` on an `over_shoulder` shot, and
  the prompt then renders it as a dark out-of-focus shoulder and back.
- `insert`/`pov` shots take `focus: "none"`; a character on one is dropped so
  the frame stays empty (an insert of a person is a different shot).
- the shot prompt names the character's `look`, not just a name, so the model
  can actually render them, and it is re-attached if the model forgets.
- `speaker` is `narrator` or a character id for a spoken line (the character
  may be off-screen), so dialogue lands on the right shot.
- **on camera beats must be the protagonist.** A `host_full` shot focused on
  anyone else renders the wrong person full frame, so that is warned about.
- a character who never appears as a focus is flagged: their reference sheet
  would be wasted and the cast is effectively smaller.
- exactly 12 shots, ids 1..12, unique slugs — otherwise nothing is written
- `duration_s` clamped to 3.0–5.0 and scaled to `--total` (60) only when the
  model misses by more than 10%, so its pacing survives
- `frames = duration_s × fps`, which `generate_video_free.py` now honours per
  shot via `--schema` (a 5 s beat asks for 40 frames, not 24)
- `layout` is derived from the model's `on_camera` flag: `host_full` for at
  most two non-consecutive beats, and only the first or last shot; the rest are
  `broll_only`. `host_pip` is never auto-assigned.
- face / eye / teeth / gore clauses are stripped from prompts, because the
  shared negative prompt lists them and "her eyes wide" fights its own
  negative; a figure is reworded to "seen from behind as a featureless black
  silhouette"
- a voice line longer than ~2.6 words per second is flagged as rushed

When the model gets the cast or the shot count wrong, the script re-asks once
(`--retries 1`) with the broken rules quoted back at it. A truncated or
malformed JSON reply is treated the same way rather than being fatal; each
retry costs another 45 s slot. `--max-tokens` (4000) leaves room for a
12-shot, 3-character reply.

```json
{
  "characters": [
    {"id": "mara", "name": "Mara", "role": "protagonist",
     "look": "thirties, dark wet shoulder-length hair, long grey wool coat, black boots",
     "reference": {"age": "thirties", "hair": "dark, wet", "clothing": "grey wool coat",
                   "features": "sharp nose, tired eyes", "build": "lean"},
     "reference_prompt": "character reference sheet of Mara, ..."}
  ],
  "shots": [
    {"id": 3, "shot_type": "over_shoulder", "focus": "mara", "foreground": "shad",
     "vo": "On the cliff, a silhouette watches.", "speaker": "narrator",
     "layout": "broll_only", "duration_s": 5.0, "frames": 40}
  ]
}
```

Two hardware/plumbing notes it prints when relevant:

- **40-frame shots** (5 s at 8 fps) are above the comfortable 15 GB T4 point;
  `--max-frames 32` caps them and shortens `duration_s` to match (12 shots ×
  4 s = 48 s), rather than leaving the OOM ladder to drop the clip later.
- **`sound_design.sh` hardcodes 9 × 3 s** boundaries (`DUR=27`, `HIT_AT=21.6`)
  for the hand-written teaser. Any other episode length needs those constants
  recomputed before the stinger lands on the right beat.

## Character reference sheets

`generate_characters.py` draws the cast without a GPU: it reads the
`characters` array and sends each `reference_prompt` to Pollinations' free image
API, one JPEG per character in `refs/characters/`, plus a `manifest.json`
recording the prompt, seed and byte size.

```bash
python3 generate_characters.py --schema episodes/silence-on-the-fog-ridge.json
python3 generate_characters.py --only mara --overwrite      # redraw one
python3 generate_characters.py --dry-run                    # print the URLs only
```

Things that shape the output:

- the free tier serves **one image at a time, 45 s apart per IP**, so three
  sheets is ~2.5 minutes; `--delay` changes the spacing
- `--size` is capped at 768x768 (the free area limit) and larger values are
  refused rather than silently shrunk
- 402/429 (the slot) and 5xx (`"Classic API is at its limit, retry after 10s"`)
  are both retried, using `Retry-After` or the number in the body, up to
  `--max-wait`
- images are validated as JPEG before being saved, so a JSON error card cannot
  masquerade as a sheet
- the free tier bakes a small `pollinations.ai` watermark into the bottom right
- sheets may show faces; the AnimateDiff shot prompts still may not

The checked-in `episodes/silence-on-the-fog-ridge.json` and
`refs/characters/*.jpg` are the first real run (Mara, Shad, Captain).

## HD delivery for the archived AnimateDiff clips

This section describes the retired GPU path; see `archive_animatdiff/`.
AnimateDiff ran at 512x896 (or the schema's 512x512) to fit a 15 GB T4, so the
model output was a proxy, not a master. `generate_video_free.py` wrote the raw
clip to `out/video/raw/` and post-processed it with ffmpeg:

```
scale=1080:1920:flags=lanczos:force_original_aspect_ratio=increase,crop=1080:1920,
unsharp=5:5:0.8:5:5:0.0,format=yuv420p
```

`lanczos` upscales with a smoother edge response than bicubic's stair-stepping,
and `unsharp` runs on luma only (chroma amount `0.0`) so it puts contrast back
into the figure and corridor without blooming colour noise. The delivery encode
is H.264 CRF 16, `slow` preset, `yuv420p`, `+faststart`.

`--fit` decides how a source that is not 9:16 meets the 1080x1920 frame:
`cover` (default) centre-crops, `pad` letterboxes, `stretch` distorts but is
warned about. A 512x896 clip is already within 2% of 9:16, so `cover` costs
nothing; a square 512x512 run logs a loud warning instead of silently cropping
78% of the frame.

```bash
python3 generate_video_free.py --all                    # 1080x1920 delivery
python3 generate_video_free.py --only 1 --fit pad        # keep the whole frame
python3 generate_video_free.py --upscale-to 720x1280     # quick preview
python3 generate_video_free.py --no-upscale              # raw model frames
python3 generate_video_free.py --sharpen-amount 1.2      # harder edges
python3 generate_video_free.py --dry-run                 # print the filter
```

`manifest.json` records the raw path, both sizes, the `fit`, the filter string
and the CRF, so a re-render at different sharpen settings is reproducible from
the manifest alone. `--keep-raw/--no-keep-raw` controls the raw clips.

## Sound design mix (optional)

`sound_design_mix.sh` takes a graded picture and gives it a delivery mix. It
needs the ffmpeg skill installed (`.pi/skills/ffmpeg-skill/`) and never touches
the video stream.

```bash
./sound_design_mix.sh 12th-street-ep01.mp4 --music bed.wav --music-volume 0.18
./sound_design_mix.sh out/video/teaser.mp4 --no-music --lufs -16 -o out/final.mp4
./sound_design_mix.sh out/video/teaser.mp4 --platform youtube-shorts -o /tmp/x.mp4
```

1. **mix** — folds the bed under the narration with a sidechain duck (6 dB by
   default), loops and fades it to the film length.
2. **normalise** — two-pass EBU R128 (`--lufs -14 --tp -1 --lra 11` by default).
3. **verify** — the delivery check table; a FAIL exits 3.

`--no-duck`, `--denoise`, `--dry-run` and `--no-check` cover the usual cases.
The canonical `sound_design.sh` stays the one that builds the teaser end to end.
