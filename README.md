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
- `generate_video_free.py`: local AnimateDiff for "The End of the Corridor",
  with the ffmpeg 1080x1920 delivery step described below.
- `sound_design.sh`: the canonical teaser build — grades the nine clips and
  synthesises the drone/riser/stinger bed from committed inputs.
- `sound_design_mix.sh`: an alternative audio stage for an already-graded
  picture (bed duck + two-pass R128 + delivery check).

## HD delivery for the AnimateDiff clips

AnimateDiff runs at 512x896 (or the schema's 512x512) to fit a 15 GB T4, so the
model output is a proxy, not a master. `generate_video_free.py` now writes the
raw clip to `out/video/raw/` and post-processes it with ffmpeg:

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
