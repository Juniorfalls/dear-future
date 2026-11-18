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

Everything an episode needs lives in `remotion/data/scenes.json`:

```json
{
  "_notes": {
    "image_source": "PLACEHOLDER IMAGES — swap each `image` for an AI-generated still."
  },
  "title": "12th Street",
  "scenes": [
    {
      "image": "https://picsum.photos/seed/ziggurat-dawn-1/1920/1080",
      "kicker": "Chapter One — The First Cities",
      "caption": "Six thousand years ago, the first cities rose out of the mud of the Tigris and the Euphrates."
    }
  ]
}
```

- `image` — any URL or a file under `remotion/public/`, cropped to cover the
  frame. **These are placeholders today.** The `_notes.image_source` field marks
  the exact spot where images from the (future) AI image API drop in — one URL
  per scene, nothing else in the pipeline changes.
- `kicker` — optional gold uppercase chapter line, e.g. "Chapter Two — Writing
  the World".
- `caption` — the narration line burned into the lower third.

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
