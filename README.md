# dear-future — automated Manim explainer factory

Short finance-psychology explainers, rendered by Manim Community Edition in CI.
A topic queue drives prompt generation, each scene is a plain Python file, and the
workflow renders every scene and muxes a placeholder voiceover onto each video.

## Where the videos are

Rendered videos live in the **GitHub Actions artifacts**, not in the repository
(they are build output, and `media/`, `outputs/` and `audio/` are gitignored).

1. Open the repo on GitHub → **Actions** tab.
2. Pick the **Render Manim Scenes** workflow on `main` and open the latest run
   (green checkmark = the batch built).
3. Scroll to the bottom of the run summary → **Artifacts** → download
   **`manim-videos`** (a zip).

The zip contains one file per scene at the requested quality:

```
SavingsTrap.mp4              # silent render
CompoundInterestScene.mp4
LossAversionScene.mp4
savings_trap_with_audio.mp4  # same video + placeholder voiceover
compound_interest_with_audio.mp4
loss_aversion_with_audio.mp4
```

From a terminal, either of these works too:

```bash
gh run download --name manim-videos --dir ./videos   # needs gh, logged in
gh run watch                                          # follow the live render
```

Runs started by hand (**workflow_dispatch**) accept a `quality` input
(`l`, `m`, `h`, `k`) and a `scene_files` glob, so you can render just one scene.

## Repository layout

| Path | Purpose |
| --- | --- |
| `topics.json` | the topic queue: `id`, `title`, `narrative` per video |
| `factory.py` | turns each topic into `prompts/<id>_prompt.txt` (Style Contract + brief) |
| `scenes/*.py` | one Manim scene file per topic (class name derived from the id) |
| `add_audio.py` | gTTS voiceover + mux into `outputs/<id>_with_audio.mp4` |
| `requirements.txt` | `gTTS` and `moviepy` for the audio step |
| `.github/workflows/render.yml` | plan queue → render every scene → add audio → upload |

## Running it locally

Manim needs Cairo/Pango and a TeX install; the quickest route is the same image
CI uses:

```bash
docker run --rm -it -v "$PWD:/manim" -w /manim manimcommunity/manim:stable bash

# inside the container
manim -ql scenes/loss_aversion.py LossAversionScene   # single scene, fast quality
manim -qh -a scenes/savings_trap.py                   # every scene in a file
python -m pip install -r requirements.txt             # for the audio step
python add_audio.py
```

`python add_audio.py` writes `audio/<id>.mp3`, pads the speech with silence to the
video length and muxes the result to `outputs/<id>_with_audio.mp4`.

## Adding the next video

1. Append `{"id": ..., "title": ..., "narrative": ...}` to `topics.json`.
2. `python3 factory.py` — this prints the queue and writes
   `prompts/<id>_prompt.txt`.
3. Hand that prompt to a coding agent; save the result as `scenes/<id>.py` with
   the class name the prompt asks for.
4. Push to `main` — CI renders and uploads the video automatically.
