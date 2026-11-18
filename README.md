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

Stills come from `picsum.photos` placeholders for now. `image_urls()` in
`generate_video.py` is the single swap point for a real generator (DALL·E,
Stable Diffusion, a hosted endpoint); it only has to return one URL per scene.

The generated file looks like this:

```json
{
  "title": "12th Street",
  "topic": "The History of Rome",
  "scenes": [
    {
      "image_url": "https://picsum.photos/seed/the-history-of-rome-1-.../1920/1080",
      "text": "The History of Rome. It began like any other story — with ambition, and with time.",
      "durationInSeconds": 5,
      "kicker": "Chapter One — The Beginning"
    }
  ]
}
```

- `image_url` — any URL or a file under `remotion/public/`, cropped to cover the
  frame. Placeholders today; the AI image API drops in here.
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
- **Ken Burns** — every still pushes from 1.04× to 1.17× on a linear ramp with a
  slow lateral drift that alternates per shot, so nothing ever sits still.
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

## Repository layout

| Path | Purpose |
| --- | --- |
| `generate_video.py` | topic → `remotion/data/scenes.json` (chapters, captions, image URLs) |
| `requirements.txt` | Python dependency for the generator (`requests`) |
| `remotion/src/CinematicDoc.tsx` | the film: scenes, Ken Burns, captions, wordmark |
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
