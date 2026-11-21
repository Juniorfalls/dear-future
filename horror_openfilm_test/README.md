# OpenFilm horror test — "The Last Customer"

A 30-second OpenFilm test: fifteen seconds of a dying fluorescent corridor with
one slowly fading subtitle, then a static AI-generated hallway, over a low drone.

## Run it

```bash
# This container has no system ffmpeg/browser: both live in /tmp for this test.
export PATH=/tmp/ofbin/bin:$PATH
export PLAYWRIGHT_BROWSERS_PATH=/tmp/pw-browsers
export OPENFILM_HOME=/tmp/openfilm-home
export OPENFILM_LIBRARY=/tmp/openfilm-projects

npx -y openfilm@latest doctor
npx -y openfilm@latest look 12       # one frame → .film/cache/look/12s.jpg
npx -y openfilm@latest render --out horror_openfilm_test.mp4 --workers 2
```

`openfilm doctor` passes everything except one warning: WebGL runs on SwiftShader
(no GPU in the container), so drawing is slower and can differ slightly from a
GPU render. The render below still completed correctly.

## Result

`horror_openfilm_test.mp4` is not checked in (34 MB). It was moved to
`/tmp/horror_openfilm_test.mp4` to free disk for the 1080p final assembly; run
the render command above to recreate it.

| | |
| --- | --- |
| `horror_openfilm_test.mp4` | 30.00 s, 1280×720, 30 fps, H.264 + AAC stereo, 34 MB |
| OpenFilm's direct render | 114 MB at CRF 16 (grain is expensive); the file here is a CRF 26 delivery copy of that render |
| Render time | 314 s with 2 workers on 2 CPU cores, software WebGL |
| Checks | `openfilm look` drew 12 frames twice in shuffled orders: same `t`, same picture |

`openfilm look` initially flagged a flat frame at exactly 15 s, where the
hallway fade started from black. `drawHallway` now draws the flickering corridor
under the dissolve, so the cut never dips to black.

## Files

| File | Purpose |
| --- | --- |
| `film.html` | the edit: one 30 s page clip + one 30 s audio clip. No script. |
| `story.html` | the page that draws the film: `window.film.frame(t)`. |
| `assets/hallway.jpg` | the static AI-generated hallway (1280x720). |
| `assets/drone.wav` | 30 s drone, 48 kHz mono, made by `make_drone.py`. |
| `make_drone.py` | regenerates the drone from sine waves, noise and three creaks. |

## How `frame(t)` is split

OpenFilm's film format keeps `film.html` as the timeline (tracks and clips) and
puts drawing code on **pages**. So the required `frame(t)` lives in
`story.html`, and `film.html` calls it through an `<iframe>`. A page has no
sound; the drone is an `<audio>` clip on its own track.

`frame(t)` is pure: the same `t` always draws the same frame. The flicker is a
hash of `floor(t * 24)`, the grain is a prebuilt tile moved by a frame hash, and
the subtitle opacity is a `smoothstep` of `t`. No clocks, no `Math.random`.

Timeline inside the page:

| t | picture |
| --- | --- |
| 0–15 | dark corridor, deterministic tube flicker, grain, subtitle fading in at 1.6–6.4 s and out at 13.4–14.9 s |
| 15–15.9 | 0.9 s crossfade from black into the hallway |
| 15–30 | static hallway, graded teal, vignetted |

## Swapping in the Colab clips

The generated clips become video clips in `film.html`, not drawing code. Each
shot is a `<video>` on a free track at its cue, with its own source trim:

```html
<section>
  <video id="shot-01" src="assets/clips/shot-01.mp4#t=0,3" at="0" volume="0"
         style="left:0;top:0;width:1280px;height:720px;object-fit:cover"></video>
  <video id="shot-02" src="assets/clips/shot-02.mp4#t=0,3" at="3" volume="0"
         style="left:0;top:0;width:1280px;height:720px;object-fit:cover"></video>
</section>
```

Keep the generated clips muted (`volume="0"`) and put the drone on the audio
track, so the mix and the captions stay editable. Hard cuts are adjacent clips;
a crossfade puts the outgoing and incoming clips on two tracks that overlap,
with `overrides='[{"fade":[0.4,0.4]}]'`. Captions can be a WebVTT `<track>` or
the same code-drawn `frame(t)` page.
