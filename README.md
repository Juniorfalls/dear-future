# 12th Street — cinematic documentary engine

Documentary-style shorts for the **12th Street** channel, rendered entirely in
[Remotion](https://remotion.dev). The whole film — photos, Ken Burns camera
moves, crossfades, lower-third captions and the wordmark — is React code, driven
by one JSON file per episode. GitHub Actions renders it and publishes the MP4 as
an artifact.

## Where the video is

The rendered film is a build artifact, not a tracked file.

1. Open the repo → **Actions** → **Render Cinematic Video** → latest green run.
2. Scroll to the bottom of the run summary → **Artifacts** → **`cinematic-video`**.

```bash
gh run download --name cinematic-video --dir ./video   # needs gh, logged in
gh run watch                                           # follow a render
```

## Writing an episode

Everything an episode needs lives in `remotion/data/scenes.json`:

```json
{
  "title": "12th Street",
  "scenes": [
    {
      "image": "https://picsum.photos/1920/1080?random=1",
      "kicker": "Chapter One",
      "caption": "The year is 1942, and 12th Street is the loudest street in the city."
    }
  ]
}
```

- `image` — any URL or a file under `remotion/public/`. It is cropped to cover
  the frame, so portrait and landscape photos both work.
- `kicker` — optional small serif line above the caption ("Chapter One").
- `caption` — the narration line burned into the lower third.

Change the file, push to `main`, and CI renders the new episode. Scene length
and crossfade length are `--scene-seconds` / `--overlap-seconds` flags (defaults
6s and 1s), so a 3-scene episode is 16s long.

## What the composition does

`remotion/src/CinematicDoc.tsx`:

- **Ken Burns** — every still is pushed from 1.05× to 1.24× with a slow eased
  scale plus a small pan, so a static photo reads as a camera move.
- **Crossfades** — the incoming scene fades in on top of the outgoing one, which
  stays fully opaque underneath, so transitions never dip to black.
- **Captions** — Merriweather 58px, off-white, rising 28px on a spring, over a
  bottom gradient wash; they fade in after the crossfade and out before the cut.
- **Typography** — Cinzel for the `12TH STREET` wordmark (top-left, with a hair
  rule under it) and the kicker; Merriweather for narration.
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
| `remotion/src/CinematicDoc.tsx` | the film: scenes, Ken Burns, captions, wordmark |
| `remotion/src/Root.tsx` | `CinematicDoc` composition + dynamic duration/dimensions |
| `remotion/data/scenes.json` | episode content (images + captions) |
| `remotion/render.js` | bundles the composition and renders it with `@remotion/renderer` |
| `remotion/remotion.config.ts` | codec/CRF/image-format defaults |
| `.github/workflows/render.yml` | installs dependencies, renders, uploads the artifact |
| `remotion-overlay/` | retired Manim-era overlay project; unused, kept for history |

## Requirements

Node 18+ and network access (images and Google Fonts are fetched at render time).
There are no Python dependencies — `requirements.txt` is intentionally a stub.
