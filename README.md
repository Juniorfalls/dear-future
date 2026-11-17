# dear-future — automated Manim explainer factory

Short finance-psychology explainers, rendered by Manim Community Edition in CI.
A topic queue drives prompt generation, each scene is a plain Python file, and
follow-up CI jobs add a Remotion overlay, a gTTS voiceover and WhisperX captions
before compositing everything into one file.

## Where the videos are

Videos live in the **GitHub Actions artifacts**, not in the repository (they are
build output, and `media/`, `outputs/` and `audio/` are gitignored).

1. Open the repo on GitHub → **Actions** tab.
2. Pick the **Render Manim Scenes** workflow on `main` and open the latest run
   (green checkmark = the batch built).
3. Scroll to the bottom of the run summary → **Artifacts**.

| Artifact | Contents |
| --- | --- |
| **`final-videos`** | `final_<topic_id>.mp4` (Manim video + Remotion overlay + voiceover + burned-in captions) and `<topic_id>.srt` |
| **`rendered-videos`** | the silent Manim renders from the render job, kept for debugging |
| **`remotion-overlay`** | `overlay.webm`, the transparent "Math Explained" card |

From a terminal:

```bash
gh run download --name final-videos --dir ./videos   # needs gh, logged in
gh run watch                                          # follow the live render
```

Runs started by hand (**workflow_dispatch**) accept a `quality` input
(`l`, `m`, `h`, `k`) and a `scene_files` glob, so you can build just one scene.

## Pipeline

The workflow has three jobs. `render` and `overlay` run in parallel; `assemble`
needs both.

1. **render** (`manimcommunity/manim:stable`, Python 3.14) — plan the queue,
   render every `scenes/*.py`, upload the silent mp4s as `rendered-videos`.
2. **overlay** (hosted runner + Node 22) — `npm ci` in `remotion-overlay/`, then
   `node render.js` bundles the Remotion composition and renders it to a
   transparent VP8/`yuva420p` WebM, uploaded as `remotion-overlay`.
3. **assemble** (`python:3.11-slim`, with `ffmpeg` and DejaVu fonts) — install
   `requirements.txt` (CPU torch from PyTorch's index, cached in `~/.cache/pip`),
   download the silent renders plus the overlay, then run `assemble.py`: gTTS
   voiceover → WhisperX `tiny` (int8, CPU) → `.srt` → MoviePy mux, overlay
   composite and caption burn-in → `outputs/final_<id>.mp4` → upload
   `final-videos`.

Assembling lives in its own Python 3.11 job because WhisperX pins
`ctranslate2==4.4.0`, which has no wheel for the 3.14 interpreter inside the
Manim image. The overlay job lives outside the container because it needs Node.

## Repository layout

| Path | Purpose |
| --- | --- |
| `topics.json` | the topic queue: `id`, `title`, `narrative` per video |
| `voiceover.json` | optional real narration per topic id (overrides the placeholder) |
| `scripts/<id>.txt` | optional narration as a plain text file |
| `factory.py` | turns each topic into `prompts/<id>_prompt.txt` (Style Contract + brief) |
| `scenes/*.py` | one Manim scene file per topic (class name derived from the id) |
| `assemble.py` | gTTS + WhisperX + MoviePy: silent render → captioned, overlaid `final_<id>.mp4` |
| `remotion-overlay/` | Remotion (React) project producing the transparent corner card |
| `remotion-overlay/render.js` | bundles + renders the `Overlay` composition to `out/overlay.webm` |
| `add_audio.py` | earlier, simpler muxer (no captions); kept for ad-hoc use |
| `requirements.txt` | `gTTS`, `moviepy`, `whisperx`, `soundfile` (+ CPU torch index) |
| `.github/workflows/render.yml` | render job → assemble job → artifacts |

## Running it locally

Manim needs Cairo/Pango and a TeX install; the quickest route is the same image
CI uses:

```bash
# rendering
docker run --rm -it -v "$PWD:/manim" -w /manim manimcommunity/manim:stable bash
manim -ql scenes/loss_aversion.py LossAversionScene

# assembly (needs Python 3.11 + ffmpeg)
docker run --rm -it -v "$PWD:/manim" -w /manim python:3.11-slim bash
apt-get update && apt-get install -y ffmpeg fonts-dejavu-core
python -m pip install -r requirements.txt
python assemble.py
```

Rendering the overlay locally needs Node 18+:

```bash
cd remotion-overlay
npm install
node render.js          # → remotion-overlay/out/overlay.webm
```

`assemble.py` writes `outputs/audio/<id>.mp3`, `outputs/<id>.srt` and
`outputs/final_<id>.mp4`. Flags: `--text "..."` to override the voiceover,
`--model` for a bigger WhisperX model, `--caption-mode even` to skip WhisperX,
`--overlay <path>` to pick another WebM and `--no-overlay` to skip it entirely.

The overlay is read from `remotion-overlay/out/overlay.webm` (falling back to
`./overlay.webm`). It is looped for the whole video and scaled to 26% of the
video width, sitting bottom-right above the caption band. Compositing happens in
a single `ffmpeg` pass (`overlay` filter over `-stream_loop -1` input) rather
than as one MoviePy layer per loop, so assembly time does not grow with video
length. If no overlay file is
present the assembly still succeeds, just without the card.

Real narration, when it exists, can be dropped in as `voiceover.json`:

```json
{ "compound_interest": "Five thousand dollars, left alone for thirty years..." }
```

## Adding the next video

1. Append `{"id": ..., "title": ..., "narrative": ...}` to `topics.json`.
2. `python3 factory.py` — prints the queue and writes `prompts/<id>_prompt.txt`.
3. Hand that prompt to a coding agent; save the result as `scenes/<id>.py` with
   the class name the prompt asks for.
4. Push to `main` — CI renders, narrates, captions and uploads the video.
