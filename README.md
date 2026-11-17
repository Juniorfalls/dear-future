# dear-future — automated Manim explainer factory

Short finance-psychology explainers, rendered by Manim Community Edition in CI.
A topic queue drives prompt generation, each scene is a plain Python file, and a
second CI job adds a gTTS voiceover plus WhisperX captions and muxes the result.

## Where the videos are

Videos live in the **GitHub Actions artifacts**, not in the repository (they are
build output, and `media/`, `outputs/` and `audio/` are gitignored).

1. Open the repo on GitHub → **Actions** tab.
2. Pick the **Render Manim Scenes** workflow on `main` and open the latest run
   (green checkmark = the batch built).
3. Scroll to the bottom of the run summary → **Artifacts**.

| Artifact | Contents |
| --- | --- |
| **`final-videos`** | `final_<topic_id>.mp4` (video + voiceover + burned-in captions) and `<topic_id>.srt` |
| **`rendered-videos`** | the silent Manim renders from the render job, kept for debugging |

From a terminal:

```bash
gh run download --name final-videos --dir ./videos   # needs gh, logged in
gh run watch                                          # follow the live render
```

Runs started by hand (**workflow_dispatch**) accept a `quality` input
(`l`, `m`, `h`, `k`) and a `scene_files` glob, so you can build just one scene.

## Pipeline

The workflow has two jobs, because WhisperX pins `ctranslate2==4.4.0`, which has
no wheel for the Python 3.14 interpreter inside the Manim image.

1. **render** (`manimcommunity/manim:stable`, Python 3.14) — plan the queue,
   render every `scenes/*.py`, upload the silent mp4s as `rendered-videos`.
2. **assemble** (`python:3.11-slim`, with `ffmpeg` and DejaVu fonts) — install
   `requirements.txt` (CPU torch from PyTorch's index), download the silent
   renders, then run `assemble.py`: gTTS voiceover → WhisperX `tiny` (int8, CPU)
   → `.srt` → MoviePy mux and caption burn-in → `outputs/final_<id>.mp4` →
   upload `final-videos`.

## Repository layout

| Path | Purpose |
| --- | --- |
| `topics.json` | the topic queue: `id`, `title`, `narrative` per video |
| `voiceover.json` | optional real narration per topic id (overrides the placeholder) |
| `scripts/<id>.txt` | optional narration as a plain text file |
| `factory.py` | turns each topic into `prompts/<id>_prompt.txt` (Style Contract + brief) |
| `scenes/*.py` | one Manim scene file per topic (class name derived from the id) |
| `assemble.py` | gTTS + WhisperX + MoviePy: silent render → captioned `final_<id>.mp4` |
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

`assemble.py` writes `outputs/audio/<id>.mp3`, `outputs/<id>.srt` and
`outputs/final_<id>.mp4`. Flags: `--text "..."` to override the voiceover,
`--model` for a bigger WhisperX model, `--caption-mode even` to skip WhisperX.

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
