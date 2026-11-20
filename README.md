# 12th Street — cinematic documentary engine

Cinematic **history and ancient-civilization** documentaries for the **12th
Street** channel, rendered entirely in [Remotion](https://remotion.dev). The
whole film — stills, camera moves, hard cuts, outlined subtitles, per-scene colour
grades, a music bed and a locally generated voiceover — is React code driven by
one JSON file per episode.
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
skip the HTTP check. `--layouts` sets the framing per scene, as a comma list or
a JSON list (`--layouts host_full,broll_only,host_pip,broll_only,host_full`,
`--count 5`); without it the generator opens on `host_full` and alternates
`host_pip` / `broll_only`.

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
  "sceneDurationInSeconds": 2.5,
  "style": {"letterbox": false, "atmosphereOpacity": 0, "wordmark": "none", "scrim": 0.15},
  "outro": {"title": "The History of Rome", "durationInSeconds": 3.5},
  "audio": {"src": "audio/bg_music.mp3", "volume": 0.15, "loop": true},
  "scenes": [
    {
      "layout": "host_full",
      "transition": "cut",
      "grade": "warm",
      "image_url": "episodes/the-history-of-rome/scene-1.jpg",
      "text": "Rome did not fall in a day.",
      "durationInSeconds": 3,
      "kicker": "The History of Rome"
    },
    {
      "layout": "broll_only",
      "transition": "cut",
      "grade": "cold",
      "image_url": "episodes/the-history-of-rome/scene-2.jpg",
      "text": "At its height, Rome reached farther than any empire before it.",
      "captions": [
        {"text": "At its height,", "from": 0.0, "to": 0.9},
        {"text": "Rome reached farther", "from": 0.9, "to": 1.7},
        {"text": "than any empire before it.", "from": 1.7, "to": 2.5}
      ],
      "durationInSeconds": 2.5
    }
  ]
}
```

- `layout` — how the shot is framed: `host_full` (presenter only, b-roll
  hidden), `host_pip` (b-roll full screen, presenter in a rounded bottom-left
  inset) or `broll_only` (b-roll full screen). Missing/unknown values fall back
  to `broll_only`. Host layouts play `remotion/public/host/presenter.mp4`
  through `<OffthreadVideo>`: full-frame over a blurred backplate for
  `host_full`, rounded inset for `host_pip`. Swap that file to change the host.
- `transition` — `cut` (default, and what the reference film uses) replaces the
  previous shot on a single frame; `crossfade` fades in over the tail of it,
  using `overlapInSeconds` (default 0.8s).
- `grade` — `cold` (cool blue, night interiors), `warm` (muted amber, daylight)
  or `neutral`. The filter sits on the still, a soft tint wash goes over the
  finished shot.
- `captions` — optional subtitle chunks timed in seconds from the start of the
  scene. Without them, `text` is split automatically to fit the shot.
- `image_url` — any URL or a file under `remotion/public/`, cropped to cover the
  frame. Pollinations.ai stills are downloaded there; the AI image API drops in
  here too. Optional for a `host_full` scene, which never shows b-roll.
- `text` — the full narration line; it is chunked into subtitles.
- `durationInSeconds` — how long that shot holds (the composition falls back to
  a global default when it is missing).
- `kicker` — optional gold identification line, shown on `host_full` scenes only.
- `style` — film-wide switches: `letterbox`, `atmosphereOpacity`, `lightSweep`,
  `vignette`, `wordmark` (`all` / `intro` / `none`) and `scrim` (strength of the
  gradient behind the subtitles; 0 gives the reference's outline-only look).
- `outro` — title card after the last scene: `{title, durationInSeconds}`.
- `audio` — the music bed: `{src, volume, loop, trimBeforeSeconds}`. `src` is a
  file under `remotion/public/` or a full URL; it plays under the whole film,
  from the first frame to the end card, and loops when it is shorter than the
  episode. Omit the block to get the bundled track at 0.15. Only `src` is
  required; `volume` is clamped to 0–1.

`render.js` also accepts the older `image` / `caption` keys, so a hand-written
scene file still renders.

Change the file, push to `main`, and CI renders the new episode. Shot length and
crossfade length are `--scene-seconds` / `--overlap-seconds` flags (defaults
2.5s and 0.8s).

## Voiceover

The narration is spoken locally by [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M)
(Apache-2.0, commercial use allowed): no API key, no per-word cost, and the
voice files are committed with the episode so CI can render without a GPU.

```bash
python3 -m venv .venv
.venv/bin/pip install torch --index-url https://download.pytorch.org/whl/cpu
.venv/bin/pip install -r requirements-voice.txt
sudo apt install espeak-ng          # only if your distro needs it

.venv/bin/python generate_script.py "The Fall of Rome"   # → remotion/data/script.json
.venv/bin/python generate_voice.py                       # → public/audio/scene_N.wav
```

`generate_script.py` writes the shot list: `scene_id`, `text`, `duration_hint`,
plus the framing and grade for that shot. Scripts live in the `SCRIPTS` table in
that file; add a topic there and it appears in `--list`.

`generate_voice.py` speaks each line with `am_michael` (deep, unhurried; `--voice
am_adam` is the clipped alternative), trims the silence Kokoro pads around it,
and writes 24 kHz mono wavs. It then rewrites `scenes.json` with two things per
scene:

```json
"durationInSeconds": 3.662,
"voice": {"src": "audio/scene_1.wav", "durationInSeconds": 3.162}
```

The shot is the spoken line plus 0.5 s of air. At render time
`calculateMetadata` re-measures each wav with `getAudioDuration` and passes the
per-scene durations back into the composition, so the sequences and the
composition length are derived from the audio, not from the JSON — replacing a
wav re-times the film on the next render. Subtitles are chunked over the speech
only, so the last chunk lands with the voice rather than hanging in the tail.

If torch will not install on your machine (Termux/Android), `edge-tts` is a
drop-in fallback: it needs no key either, and its mp3s can be written to
`public/audio/scene_N.wav`-equivalent paths. Kokoro is preferred for quality and
for staying fully local.

## What the composition does

`remotion/src/CinematicDoc.tsx`:

- **Layouts** — each scene names its framing. `host_full` hides the b-roll and
  fills the frame with the presenter video (contained over a blurred copy of
  itself, so an off-ratio source is framed in blur, not black). `host_pip`
  keeps the b-roll full-bleed and insets the presenter bottom-left in a rounded
  brass-bordered frame, sliding the caption right so the two never collide.
  `broll_only` is the original film look. The presenter is muted until the film
  has an audio track.
- **Transitions** — every shot cuts in on a single frame by default. A scene can
  ask for `"transition": "crossfade"` to fade in over the previous shot instead.
- **Subtitles** — one short chunk at a time, in Oswald bold italic caps, white
  with a thick black outline (`-webkit-text-stroke` + `paint-order`), centred
  above the bottom edge. Chunk timings come from `captions`, or from splitting
  `text` to fit the shot; the text swaps hard, never fades. A `scrim` setting
  controls how much dark gradient sits behind it — the reference uses almost
  none and relies on the outline.
- **Grade** — per-scene `cold` / `warm` / `neutral`: a CSS filter plus a
  `soft-light` tint over the shot, so the night interiors go blue and the
  daylight scenes go amber, like the reference's location-coded palette.
- **Narration** — each scene owns its wav, played by an `<Audio>` inside that
  scene's sequence, so a line can never drift across a cut. Volume defaults to 1.
- **Music bed** — one track under the whole composition (`<Audio>` at the top
  level, not inside a scene), at 0.15 so a voice-over can sit on top. The
  bundled `public/audio/bg_music.mp3` is a CC0 ambient piece (Wikimedia
  Commons, `Ambient music test, Yamaha CK61`), transcoded to 48 kHz stereo MP3;
  replace that file or point `audio.src` elsewhere per episode.
- **End card** — an optional `outro` title, heavy rounded sans on near-black
  with a faint warm cast, fading up before the closing fade to black.
- **Extras are opt-in** — letterbox, dust/fog, light sweep, vignette and the
  wordmark are all `style` switches, so one episode can be clean reference-style
  and another keeps the legacy look.
- **Ken Burns** — b-roll stills push from 1.05× to 1.17× with a slow lateral
  drift that alternates per shot, sized for 2.5s cuts rather than 5s holds.
- **2.5D camera** — the still sits on a perspective plane and orbits a couple of
  degrees over the shot, while a softened, dimmed copy of the same still drifts
  behind it at 30% of the travel. That differential motion reads as depth and
  fills the edges the tilt exposes. The bottom 20px of the frame are cropped to
  drop the watermark some free image hosts bake into their output.
- **Atmosphere** — when `atmosphereOpacity` is above 0, a dust-and-fog layer
  (24 deterministic motes plus three slow fog banks) and a soft diagonal shaft
  of light crossing every 5s. Both are frame-driven, so previews and MP4s match.
- **Captions layering** — the subtitle sits above the presenter, the scrim and
  the grade, so it is always pure white with a clean outline.
- **Typography** — Cinzel for the wordmark and the host-scene identification
  line, Oswald for subtitles, Nunito 800 for the end card. All load from Google
  Fonts through `@remotion/google-fonts`, so renders wait for the real files.
- **Finish** — an optional radial vignette and a 0.8s fade to black at the end.

Duration, resolution and fps are computed from the scene list in
`calculateMetadata`, so long-form (1920×1080) and vertical shorts (1080×1920)
use the same composition.

## Running it locally

```bash
cd remotion
npm install
node render.js                     # → remotion/out/cinematic_video.mp4 (1920x1080)
node render.js --vertical          # → 1080x1920 shorts
node render.js --out out/ep1.mp4 --scene-seconds 2.5 --overlap-seconds 0.8
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
| `generate_script.py` | topic → `remotion/data/script.json` (narration, scene ids, duration hints) |
| `generate_voice.py` | script → `public/audio/scene_N.wav` + real durations in `scenes.json` |
| `requirements.txt` | Python dependencies for image generation (installed by CI) |
| `requirements-voice.txt` | Kokoro/soundfile for the voiceover, kept out of CI |
| `remotion/src/CinematicDoc.tsx` | the film: scenes, 2.5D camera, subtitles, grades, end card |
| `remotion/public/audio/` | music bed + per-scene narration wavs (committed) |
| `remotion/public/episodes/<slug>/` | committed stills for an episode (scene-1.jpg, …) |
| `remotion/public/host/presenter.mp4` | the virtual presenter clip played by the host layouts |
| `remotion/src/Root.tsx` | `CinematicDoc` composition + dynamic duration/dimensions |
| `remotion/data/scenes.json` | episode content (images, layouts, captions) |
| `remotion/render.js` | bundles the composition and renders it with `@remotion/renderer` |
| `remotion/remotion.config.ts` | codec/CRF/image-format defaults |
| `.github/workflows/render.yml` | generates the scenes for a topic, renders, uploads the artifact |

## Requirements

Python 3.10+, Node 18+ for Remotion, and network access (images and Google Fonts
are fetched at render time). Rendering the film needs no Python packages at all;
the voiceover step additionally needs the `requirements-voice.txt` environment.

## The workflow

`Render Cinematic Video` takes an optional **topic** input (manual runs; defaults
to *The History of Rome*) and on every push to `main`:

1. installs the Python requirements and runs `generate_video.py "<topic>"`,
2. installs Remotion and runs `node render.js`,
3. uploads `cinematic-video` with the MP4 **and** the generated `scenes.json`.
