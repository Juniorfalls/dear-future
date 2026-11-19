# 12th Street — cinematic documentary engine

Cinematic **history and ancient-civilization** documentaries for the **12th
Street** channel, rendered entirely in [Remotion](https://remotion.dev). The
whole film — stills, Ken Burns camera moves, crossfades, letterbox, lower-third
captions and the wordmark — is React code driven by one JSON file per episode.
GitHub Actions renders it and publishes the MP4 as an artifact.

## Where the video is

The rendered film is a build artifact, not a tracked file.

1. Open the repo → **Actions** → **Render Cinematic Video** → latest green run.
2. Scroll to the bottom of the run summary → **Artifacts** → **`cinematic-video`**.

```bash
gh run download --name cinematic-video --dir ./video   # needs gh, logged in
gh run watch                                           # follow a render
```

## Writing an episode

`generate_video.py` turns a topic into the scene list:

```bash
pip install -r requirements.txt
python generate_video.py "The Fall of Rome"     # → remotion/data/scenes.json (5 scenes / 25s)
python generate_video.py "Ancient Egypt" --scene-seconds 6 --count 7
```

It writes five chapters — beginning, height, turn, unravelling, what remains —
with dramatic narration, per-scene durations and one still per scene, then checks
that every image URL resolves. Pass `--beats lines.json` to supply your own
captions (that is the hook for an LLM script writer later), and `--no-verify` to
skip the HTTP check.

Images are resolved in this order (`--images auto`, the default):

1. **Committed stills** — `remotion/public/episodes/<topic-slug>/scene-1.jpg`,
   `scene-2.jpg`, … are picked up automatically and served by Remotion through
   `staticFile()`. Episode 1 ships with five generated stills there.
2. **AI stills** — otherwise **Pollinations.ai** generates one free,
   keyless, cinematic historical still per scene from that chapter's prompt.

`--images assets` requires committed stills, `--images pollinations` forces AI
stills, and `--images openai` uses OpenAI's image API instead (next section).
Pollinations needs no key or account: the script builds a prompt such as
*"ruined columns and broken walls at dusk… Subject: The Fall of Rome. cinematic
historical documentary still, 35mm film grain…"* and requests
`https://image.pollinations.ai/prompt/<encoded prompt>?width=1080&height=1920&nologo=true`
for that scene. The still is then downloaded to
`remotion/public/episodes/<topic-slug>/scene-N.jpg` and `scenes.json` points at
the local file, so Remotion renders offline and the artwork can be committed.
The anonymous tier allows one image every ~45 seconds per IP, so the script
waits out any `402`/`503` (about a minute per extra scene) and re-runs keep
already-downloaded stills. Free-tier output currently comes back at ~576×1024
with a small bottom-right watermark, which the frame's dark lower gradient
covers; the requested 1080×1920 is a hint, not a guarantee, and a pollen key
lifts both the cap and the resolution. Stills are requested at 1080×1920
(vertical) by default; pass `--width 1920 --height 1080` for the landscape
composition, since the frame crops to fill either way. Identical prompts are
cached upstream, so re-running the same topic keeps the same artwork.

The generated file looks like this:

```json
{
  "title": "12th Street",
  "topic": "The History of Rome",
  "scenes": [
    {
      "image_url": "episodes/the-history-of-rome/scene-1.jpg",
      "text": "The History of Rome. It began like any other story — with ambition, and with time.",
      "durationInSeconds": 5,
      "kicker": "Chapter One — The Beginning"
    }
  ]
}
```

- `image_url` — any URL or a file under `remotion/public/`, cropped to cover the
  frame. Pollinations.ai stills are downloaded there; the AI image API drops in
  here too.
- `text` — the narration line burned into the lower third.
- `durationInSeconds` — how long that shot holds (the composition falls back to
  a global default when it is missing).
- `kicker` — optional gold uppercase chapter line.

`render.js` also accepts the older `image` / `caption` keys, so a hand-written
scene file still renders.

Change the file, push to `main`, and CI renders the new episode. Scene length
and crossfade length are `--scene-seconds` / `--overlap-seconds` flags (defaults
6s and 1s), so a 3-scene episode is 16s long.

## What the composition does

`remotion/src/CinematicDoc.tsx`:

- **Letterbox** — solid black bars (9.5% of frame height, top and bottom) drawn
  over everything, for the 2.35:1 film feel.
- **Ken Burns** — every still pushes from 1.06× to 1.26× on a linear ramp with a
  slow lateral drift that alternates per shot, so nothing ever sits still.
- **2.5D camera** — the still sits on a perspective plane and orbits a couple of
  degrees over the shot, while a softened, dimmed copy of the same still drifts
  behind it at 30% of the travel. That differential motion reads as depth and
  fills the edges the tilt exposes. The bottom 20px of the frame are cropped to
  drop the watermark some free image hosts bake into their output.
- **Atmosphere** — a 12% dust-and-fog layer (24 deterministic motes plus three
  slow fog banks) and a soft diagonal shaft of light that crosses the frame
  every 5s. Both are frame-driven, so previews and MP4s match exactly.
- **Crossfades** — the incoming scene fades in on top of the outgoing one, which
  stays fully opaque underneath, so transitions never dip to black.
- **Captions** — Merriweather 56px off-white, center-aligned, fading in over
  ~1.1s after each shot settles, holding, then fading out before the cut; they
  sit above the bottom bar on a gradient that reaches solid black so the text is
  always readable.
- **Typography** — Cinzel (a Trajan-style capital serif, the documentary
  standard) for the `12TH STREET` wordmark and gold chapter kickers;
  Merriweather for narration. Both load from Google Fonts through
  `@remotion/google-fonts`, so renders wait for the real font files.
- **Finish** — a radial vignette over everything and a 0.8s fade to black at the
  end.

Duration, resolution and fps are computed from the scene list in
`calculateMetadata`, so long-form (1920×1080) and vertical shorts (1080×1920)
use the same composition.

## Running it locally

```bash
cd remotion
npm install
node render.js                     # → remotion/out/cinematic_video.mp4 (1920x1080)
node render.js --vertical          # → 1080x1920 shorts
node render.js --out out/ep1.mp4 --scene-seconds 7 --overlap-seconds 1.2
npm run studio                     # Remotion Studio for live editing
```

The first render downloads a headless Chrome build (~100 MB); CI caches it.

## Plugging in a real image API (DALL·E 3)

`generate_video.py` already calls OpenAI's Images API — it just needs a key.

1. Create one at **platform.openai.com → API keys**.
2. Repo → **Settings → Secrets and variables → Actions → New repository
   secret**, name `OPENAI_API_KEY`.
3. Actions → **Render Cinematic Video** → **Run workflow**, and set
   `images: openai`.

Locally:

```bash
export OPENAI_API_KEY=sk-...
python generate_video.py "The Fall of Rome" --images openai
```

What the script does per scene: `POST https://api.openai.com/v1/images/generations`
with the chapter prompt from `IMAGE_PROMPTS` plus the topic, `model=dall-e-3`
(change with `--model gpt-image-1`), `size=1024x1792` — or `1792x1024` when
`--width > --height`. Both response shapes are handled (a temporary URL for
`dall-e-3`, base64 for `gpt-image-1`). The files land in
`remotion/public/episodes/<topic-slug>/scene-N.jpg`, so every later
`--images auto` run reuses them.

Cost: `dall-e-3` at 1792×1024 is about **$0.08 per image**, so roughly
**$0.40 per five-scene episode**. The CI job only calls the API when dispatched
with `images: openai` — plain pushes never spend money. Commit the generated
folder to keep the artwork, otherwise each online run regenerates it.

Any other provider (Stable Diffusion, a hosted endpoint): replace
`openai_images()`. It only has to write `scene-N.jpg` files into
`episode_dir(topic)` and return `local_images(topic, count)`.

## Repository layout

| Path | Purpose |
| --- | --- |
| `generate_video.py` | topic → `remotion/data/scenes.json` (chapters, captions, image URLs) |
| `requirements.txt` | Python dependency for the generator (`requests`) |
| `remotion/src/CinematicDoc.tsx` | the film: scenes, 2.5D camera, dust/light overlays, captions, wordmark |
| `remotion/public/episodes/<slug>/` | committed stills for an episode (scene-1.jpg, …) |
| `remotion/src/Root.tsx` | `CinematicDoc` composition + dynamic duration/dimensions |
| `remotion/data/scenes.json` | episode content (images + captions) |
| `remotion/render.js` | bundles the composition and renders it with `@remotion/renderer` |
| `remotion/remotion.config.ts` | codec/CRF/image-format defaults |
| `.github/workflows/render.yml` | generates the scenes for a topic, renders, uploads the artifact |

## Requirements

Python 3.10+ (`requests`) for the generator, Node 18+ for Remotion, and network
access (images and Google Fonts are fetched at render time).

## The workflow

`Render Cinematic Video` takes an optional **topic** input (manual runs; defaults
to *The History of Rome*) and on every push to `main`:

1. installs the Python requirements and runs `generate_video.py "<topic>"`,
2. installs Remotion and runs `node render.js`,
3. uploads `cinematic-video` with the MP4 **and** the generated `scenes.json`.
