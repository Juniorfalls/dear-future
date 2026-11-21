# Dummy nine-cut OpenFilm test

Proof that the Section 5 assembly works before any GPU time is spent:

- nine separate 3-second clips,
- placed on the 30-second episode timeline as nine hard cuts,
- with a transparent flicker/vignette/subtitle page on top,
- and the existing voice lines plus drone bed underneath.

## Files

| | |
| --- | --- |
| `make_dummy_clips.py` | builds `assets/clips/shot-01.mp4` … `shot-09.mp4` |
| `assets/clips/` | nine 3 s, 1920×1080, 30 fps flat-colour clips with giant `SHOT N` labels |
| `assets/audio/` | the nine Kokoro voice lines + `drone.wav` copied from the main project |
| `film.html` | the edit: nine `<video>` clips, nine `<audio>` lines, drone |
| `story.html` | transparent overlay page: deterministic flicker, bands, grain, vignette, thick outlined captions |
| `dummy_timeline.mp4` | 30 s delivery render |

## Timeline

All sources are 3 s. The episode has four 4-second shots, so those clips play at
`speed="0.75"` (3 s ÷ 0.75 = 4 s). The video is still a hard cut; nothing is
crossfaded.

| Shot | `at` | Slot | Source | Speed |
| --- | --- | --- | --- | --- |
| 1 | 0 | 3 s | `shot-01.mp4#t=0,3` | 1 |
| 2 | 3 | 3 s | `shot-02.mp4#t=0,3` | 1 |
| 3 | 6 | 4 s | `shot-03.mp4#t=0,3` | 0.75 |
| 4 | 10 | 3 s | `shot-04.mp4#t=0,3` | 1 |
| 5 | 13 | 3 s | `shot-05.mp4#t=0,3` | 1 |
| 6 | 16 | 4 s | `shot-06.mp4#t=0,3` | 0.75 |
| 7 | 20 | 3 s | `shot-07.mp4#t=0,3` | 1 |
| 8 | 23 | 3 s | `shot-08.mp4#t=0,3` | 1 |
| 9 | 26 | 4 s | `shot-09.mp4#t=0,3` | 0.75 |

Using the real cumulative starts (0, 3, 6, 10, 13, 16, 20, 23, 26) rather than
0, 3, 6 … 24 keeps the 30-second episode length. Nine 3-second clips alone would
end at 27 s.

## Render

```bash
export PATH=/tmp/ofbin/bin:$PATH
export PLAYWRIGHT_BROWSERS_PATH=/tmp/pw-browsers
export OPENFILM_HOME=/tmp/openfilm-home
export OPENFILM_LIBRARY=/tmp/openfilm-projects

npx -y openfilm@latest render \
  --out dummy_timeline.mp4 --scale 0.6667 --workers 2
```

`--scale 0.6667` produces a 1280×720 file from the 1920×1080 stage. The full-size
CRF 16 render is much larger than the delivery copy; this test was rendered at
720p to stay inside the free space on `/home`.

| | |
| --- | --- |
| Render time | **510.4 s** (2 workers, software WebGL) |
| Output | 30.00 s, 1280×720, 30 fps, H.264 + AAC stereo |
| Raw render | 109 MB, kept at `/tmp/dummy-timeline-raw.mp4` |
| Delivery copy | 1.9 MB, H.264 CRF 26, `dummy_timeline.mp4` |
| Audio | same 10 sounds as the main assembly; −24.1 dB mean / −5.5 dB peak |

## Hard-cut check

Frame `N` is the last frame of the old shot, frame `N+1` is the first frame of
the next. Every boundary switches on the intended frame and the two frames have
different colours; there is no blended/dissolve frame.

| Cut | Frames | Before RGB | After RGB | Distance |
| --- | --- | --- | --- | --- |
| 3.000 s | 89 → 90 | (1, 18, 19) | (2, 19, 41) | 22.0 |
| 6.000 s | 179 → 180 | (1, 19, 41) | (31, 4, 6) | 48.5 |
| 10.000 s | 299 → 300 | (33, 5, 7) | (16, 18, 18) | 24.1 |
| 13.000 s | 389 → 390 | (18, 20, 20) | (14, 6, 30) | 17.7 |
| 16.000 s | 479 → 480 | (8, 4, 19) | (17, 23, 4) | 25.8 |
| 20.000 s | 599 → 600 | (16, 22, 3) | (1, 10, 24) | 28.5 |
| 23.000 s | 689 → 690 | (1, 12, 27) | (32, 16, 6) | 37.7 |
| 26.000 s | 779 → 780 | (32, 16, 6) | (1, 7, 1) | 32.7 |

Sampled from the left side of the 1280×720 frame, away from the label and the
captions. First frame is SHOT 1, last frame is SHOT 9.

## Swapping in real AI clips

When the real clips exist:

1. Put them in `assets/clips/` with the same names.
2. Remove `speed` from each `<video>` (or set it to `1`).
3. Set the fragment to the shot's real length, e.g. `shot-03.mp4#t=0,4`.
4. Keep the same `at` values and the same `story.html` overlay.
5. Run `openfilm look 10.5` and `openfilm render`.

The dummy clips carry a small `DUMMY 3.0s` note at the bottom; it overlaps the
subtitle a little in a few frames. Real clips will not have it.
