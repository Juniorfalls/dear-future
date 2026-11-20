# Reference video analysis — `12th-street-video-reference.mp4`

Analysis of the style reference supplied for the 12th Street history channel, and
what it means for our Remotion pipeline. Everything below was measured from the
file itself: `ffprobe` for the container, 1 frame every 0.25 s (286 frames) for
motion and colour, and a vision pass over 2 s contact sheets plus full-resolution
crops for typography.

- **File:** `12th-street-video-reference.mp4` (17.5 MB, committed at `ec04018`)
- **Title card on screen:** “Where No One Sees”

---

## 1. Technical metadata

| Property | Value |
| --- | --- |
| Resolution | 1920 × 1080 |
| Aspect ratio | 16:9 |
| Frame rate | 30 fps (constant) |
| Duration | 71.26 s |
| Frames | 2136 |
| Video codec | H.264, ~1.96 Mb/s total |
| Audio codec | AAC, 44.1 kHz, stereo |

Resolution and frame rate are identical to our `CinematicDoc` composition
(1920×1080 @ 30 fps), so nothing in the reference needs rescaling to match —
the gap is entirely style, not format.

---

## 2. What the video actually is

A **2D animated narrative short**, not live-action documentary. Characters,
interiors and props are illustrated and animated; there is **no on-camera host,
no presenter, no voice-over face**, and no archival photography or maps. The
story is carried by the animation plus burned-in subtitles, and closes on a
title card.

This matters because our current pipeline is built around a presenter slot
(`host_full` / `host_pip`) and Ken Burns stills. The reference uses neither: it
is full-frame animation with hard cuts. See §8 for how to reconcile that.

---

## 3. Edit rhythm — hard cuts only

I sampled at 4 fps and measured the frame-to-frame difference for the whole
runtime. **Every scene change is a hard cut**: 34 single-frame spikes, no ramps,
no dissolves, no wipes, no swipes. The slower-looking stretches are hand-drawn
motion *inside* a shot (e.g. the envelope being pushed into the ballot box at
03.25–04.75 s), not blends.

| Shot metric | Value |
| --- | --- |
| Cuts | 34 in 71 s |
| Mean shot length | 1.98 s |
| Median shot length | 1.50 s |
| Shortest / longest | 0.75 s / 6.75 s |
| Opening shot | 0–3.25 s (longest hold, carries no dialogue) |

Cuts cluster into **1–3 s shots with occasional 0.75 s accents**. The rhythm is
fast by documentary standards — roughly three times faster than our current 5 s
scenes with a 1 s crossfade.

First 20 s of cut points (s): `3.25, 6.25, 9.00, 10.50, 12.75, 15.00, 15.75,
19.00, 20.50, 21.75`.

---

## 4. Timestamped breakdown

Content read from the 2 s contact sheets, cut points from the frame-difference
pass. Short shots between samples are described from the nearest sampled frame.

| Time | Shot | Subtitle |
| --- | --- | --- |
| 00:00–00:03.2 | Cold open. Wide animated church interior at night, an older man seated alone among the pews. Cool blue, very dark (mean RGB 31,41,49). No dialogue. | — |
| 00:03.2–00:06.2 | Close-up: a hand pushes a pale envelope into a wooden ballot box. | — |
| 00:06.2–00:09.0 | Close-up of the older man's face, tearful. First speech. | “RUTH THEY'RE” → “HUNGRY” |
| 00:09.0–00:10.5 | Legs walking away, a paper left on the floor. Very dark (luma 0.09). | — |
| 00:10.5–00:12.8 | **Palette change.** Animated office: bespectacled man at a desk, an older cleaner visible through the doorway. Warm beige (mean RGB 138,119,91). | — |
| 00:12.8–00:15.0 | Hands counting cash on a desk. | “RUTH'S FUND” |
| 00:15.0–00:19.0 | The bespectacled man in a white shirt and tie, talking, close and medium. | short spoken lines |
| 00:19.0–00:20.5 | Over-the-shoulder: he watches the cleaner mop the office. | — |
| 00:20.5–00:21.8 | He now wears a dark suit and holds books. | “THE ROOF” |
| 00:21.8–00:25.5 | Church interior, congregation seated; he holds up a small yellow note. | “1 SHORT.” |
| 00:25.5–00:28.2 | An older man with a moustache holds a dark book among the congregation. | “PANTRY.” |
| 00:28.2–00:30.5 | Closer on the same man, congregation behind him. | — |
| 00:30.5–00:31.5 | The suited man at the lectern, holding up the note. | “PEW.” |
| 00:31.5–00:33.0 | Close-up of the suited man speaking. | “TELL US.” |
| 00:33.0–00:37.5 | An older man in a flat cap speaks, hand raised near his chest. | “RUTH TAUGHT.” |
| 00:37.5–00:39.0 | Closer on the flat-cap man. | “SEES.” |
| 00:39.0–00:40.5 | Close-up of the suited man. | “LEAVE YOUR.” |
| 00:40.5–00:42.0 | Flat-cap man beside a pew; a bunch of keys sits in the foreground. | — |
| 00:42.0–00:42.8 | A hand reaches for a dark wooden door; the opening widens to bright daylight. | “WAIT!” |
| 00:42.8–00:49.5 | Outside the church: a heavyset man in a green vest holds up a small burgundy pouch. | “WAIT I PROMISED HIM” |
| 00:49.5–00:50.5 | An older Black man in a suit in a hall or courtroom, facing the camera. | — |
| 00:50.5–00:51.5 | A hand reaches toward money inside an open book. | — |
| 00:51.5–00:52.2 | Close-up of a worried man with glasses. | “LEDGER ALL” |
| 00:52.2–00:54.5 | The bespectacled man offers a set of keys. | “SAMUEL” |
| 00:54.5–00:55.8 | Two suited men stand before seated people in the church. | “COULDN'T SEE” |
| 00:55.8–00:58.0 | The pouch is passed into an open hand. | “GRAY COAT” |
| 00:58.0–00:59.0 | A bald, moustached man in a green vest, seated in the church. | — |
| 00:59.0–01:00.0 | Same man, smiling. | “TELL SAMUEL” |
| 01:00.0–01:00.8 | Close-up of a grey-haired man in a suit. | “HIM” |
| 01:00.8–01:01.5 | View through the open doors toward the street, framed by two figures. | “ANYONE” |
| 01:01.5–01:06.0 | Long hold (4.5 s): wide church interior, the congregation settling. | — |
| 01:06.0–01:08.0 | Exterior / street beat. | — |
| 01:08.0–01:08.8 | Fast final cut back inside. | — |
| 01:08.8–01:11.3 | **End card.** Near-black, faint reddish-brown texture. Centred white title: “Where No One Sees”. | title |

---

## 5. Layout

- **Full-frame 16:9, edge to edge.** No letterbox bars, no pillarboxing, no
  split screen, no PiP inset anywhere in the 71 s.
- **No host.** Nobody addresses the camera; the "presenter" role is carried by
  the characters in the animation plus subtitles.
- **No graphics layer.** No maps, arrows, callout labels, lower-third names,
  archival stills or date stamps. All information is in the artwork and the
  subtitle line.
- The composition is consistently **centred and shallow-depth**: subjects sit
  middle-frame, backgrounds are simplified, and the lower third is kept clear
  for subtitles.

## 6. Typography and subtitles

The only text in the body of the video is the subtitle track. Measured from a
full-resolution frame at 08.0 s:

| Attribute | Observation |
| --- | --- |
| Style | Bold, italic, **condensed sans-serif**, all caps |
| Size | Cap height ≈ 50 px at 1080p (≈ 4.6 % of frame height; ~64–70 px type) |
| Colour | White to off-white |
| Treatment | Thick black outline plus a slight drop shadow; **no background box or plate** |
| Alignment | Horizontally centred (measured text centre x = 961 px vs frame centre 960 px) |
| Position | One line, in the lower third; baseline roughly 130–190 px (12–17 %) above the bottom edge |
| Chunking | 1–3 word phrases, swapped every ~0.5–2 s: “RUTH THEY'RE”, “HUNGRY”, “PEW.”, “WAIT!”, “SAMUEL”, “HIM” |
| Animation | Changes read as hard swaps at 0.25 s sampling — no builds, no fades, no karaoke highlight |
| Punctuation | Kept (“WAIT!”, “1 SHORT.”, “RUTH'S FUND”), which is what makes it read as dialogue rather than narration |

The kicker/caption hierarchy we use today (gold Cinzel chapter line + 56 px
Merriweather sentence) has **no counterpart** in the reference. The reference is
one line, one weight, one style, no ornament.

## 7. Colour, texture and finish

Measured per shot (mean RGB of the frame, saturation, luminance). Two distinct
grades, and the switch is a story beat rather than a global look:

| Stretch | Mean RGB | Character |
| --- | --- | --- |
| 00:00–00:10.5 | (31,41,49) → (20,25,27) | Cold, dark, desaturated blue. Luminance 0.09–0.21. |
| 00:10.5–01:08 | (138,119,91) → (168,142,113) | Warm, muted amber/tan. Luminance 0.23–0.58, saturation 0.27–0.42. |
| 01:08.8–end | (24,8,8) | Near-black with a faint red-brown cast for the title card. |

- **Grade is location-coded**: cold blue for the night church / ominous opening,
  warm beige for the office and the rest of the film. This is the single most
  reproducible colour idea in the reference, and we can do it per scene.
- **Contrast is soft.** Blacks sit around 20–40, never crushed to 0; highlights
  are muted, no clipped whites in the artwork (the subtitle outline is the
  brightest thing on screen).
- **No film grain, no dust, no lens flares, no light sweeps, no vignette of note.**
  The image is clean vector-style animation.
- **No motion blur or camera shake**; movement is what is drawn, not what the
  virtual camera does.

## 8. Audio (what can be measured without listening)

Extracted the audio track and measured RMS in 0.5 s windows (142 windows):

- Continuous energy, **no silence anywhere** (minimum window ≈ 0.01, mean 0.11).
- Opening 0–6 s sits low (0.01–0.02) — music/ambience only, matching the fact
  that no subtitle appears before 6.2 s.
- Speech-range peaks (0.13–0.28) recur from ~6.5 s onward, separated by quiet
  troughs of 0.01–0.03.

That pattern — quiet bed plus sharply fluctuating speech bursts — is consistent
with **dialogue/narration over a continuous music bed**, starting ~6.5 s in.
I cannot verify voice, language or music style from the file alone.

---

## 9. What our pipeline already gets right

- 1920×1080 / 30 fps — pixel-identical format.
- Per-scene durations from JSON, overlap configurable (so hard cuts are reachable
  today with `--overlap-seconds 0`).
- A layout switch per scene already exists, so `broll_only` full-frame shots and
  an end card can be expressed without new architecture.
- Fonts load through `@remotion/google-fonts`, so a condensed display face is a
  one-line addition.

## 10. What is missing, in priority order

1. **Hard cuts instead of crossfades.** The default 1 s crossfade is the most
   obvious deviation: the reference never blends.
2. **Subtitle styling and chunking.** Our 56 px Merriweather sentence with a
   gold kicker is a different language from 1–3 word outlined capitals swapped
   every second.
3. **Shot length.** Reference mean shot 2.0 s vs our 5 s (+1 s overlap). We are
   roughly 2.5× too slow.
4. **Per-scene colour grade.** Cold/warm location coding is absent from our
   global look.
5. **An end card.** The reference closes on a titled black card; we fade to black
   with the wordmark still up.
6. **The clean, un-graded finish.** Our dust, fog, light sweep, vignette and
   letterbox are all extra texture the reference does not have.
7. **Moving footage.** The core difference — animated action inside each shot vs a
   Ken Burns push over a still — cannot be closed by CSS. It needs motion plates.

---

## 11. Recommendations for `src/CinematicDoc.tsx`

### 11.1 Make the transition a scene property (highest impact, small change)

Add `transition: 'cut' | 'crossfade'` to `Scene` (default `cut`), and keep a
composition-level `overlapInSeconds` as the fallback for `crossfade`.

```ts
// types.ts
export type SceneTransition = 'cut' | 'crossfade';
export type Scene = { ..., transition?: SceneTransition };
```

```tsx
// CinematicDoc.tsx — duration/starts already computed per scene
const sceneOverlap = (i: number) =>
  scenes[i].transition === 'crossfade' ? overlap : 0;
```

With cuts, `reveal` becomes `1` and the `opacity` ramp is skipped entirely, so
the outgoing scene is replaced in a single frame. Keep the existing crossfade
code path behind the flag.

Also shorten the defaults: `sceneDurationInSeconds` → 3, and let `fetch_media.py`
write 2–4 s scenes. Model the rhythm on the measured distribution (median 1.5 s,
occasional 4–6 s hold).

### 11.2 Replace the lower third with a subtitle-style caption

Target styling (all from §6):

```tsx
const subtitles = {
  fontFamily: oswald.fontFamily,        // condensed; skew for the italic
  fontWeight: 700,
  fontSize: 66,
  fontStyle: 'italic',
  letterSpacing: 1.5,
  textTransform: 'uppercase',
  color: '#FFFFFF',
  textAlign: 'center',
  WebkitTextStroke: '7px #000',         // thick outline, like the reference
  paintOrder: 'stroke fill',
  filter: 'drop-shadow(0 3px 6px rgba(0,0,0,0.65))',
};
```

Implementation notes:

- **Drop the gold kicker** for the subtitle look, or reduce it to a small line
  above only in `host_full` scenes. The reference has no secondary line.
- **Position:** centred, baseline ~14 % above the bottom edge
  (`bottom: 150px` at 1080p). Remove the readability gradient's dependence on
  position — the reference relies on the outline, not on a dark plate.
- **Remove `maxWidth: 1400 / 56px` sentence layout.** One short line, ~90 %
  frame width available, wraps only if a chunk is longer than ~40 characters.
- **No fade in/out on text.** Swap instantly at chunk boundaries.

### 11.3 Chunk the captions

Our captions are one sentence per 5 s scene. The reference is 1–3 words per
~0.5–2 s. Add an optional `captions` array to `Scene`:

```ts
type Subtitle = {text: string; from: number; to: number}; // seconds, scene-relative
type Scene = { ..., captions?: Subtitle[] };
```

`CinematicDoc` picks the chunk whose window contains `frame / fps` and renders
it with no transition. Fallback for old scene files: split `caption` on
punctuation into ~3 chunks spread across the scene with equal time, so episodes
that predate the schema still get the new look.

`fetch_media.py` can emit chunk timings from a script/LLM writer later, or
derive them now by splitting on `—`, `,` and `.`.

### 11.4 Per-scene grade

Add `grade?: 'cold' | 'warm' | 'neutral'` and apply it to the B-roll and presenter
layers (not the subtitles, which must stay white):

```tsx
const GRADE = {
  cold: 'saturate(0.78) brightness(0.72) contrast(1.05) hue-rotate(-8deg)',
  warm: 'saturate(0.88) brightness(0.98) contrast(1.02) sepia(0.08)',
  neutral: 'saturate(0.9) contrast(1.03)',
};
```

Plus a tint wash: `radial-gradient` in `#2b3d4d` at 12–18 % for `cold`, `#d8b483`
at 8–12 % for `warm`, `mixBlendMode: 'soft-light'`. Measured targets from §7 —
cold ~ (25,32,38) at luma 0.15, warm ~ (140,120,90) at luma 0.45.

### 11.5 Make the film-craft layers optional

The reference is clean. Add composition props so the look is a choice:

```ts
letterbox?: boolean;        // default false for reference-style episodes
atmosphereOpacity?: number; // dust/fog strength, default 0 in reference mode
lightSweep?: boolean;       // default false
vignette?: boolean;
wordmark?: 'all' | 'intro' | 'none';
```

Keep the current values as defaults for the existing episode, and pass the
reference values from `scenes.json` under a `style` block. That way both looks
render from one component without forking the file.

### 11.6 Add an end card

```ts
type Outro = {title: string; durationInSeconds: number};
```

Render after the last scene: near-black background `#0b0505` with a faint
texture gradient, the title centred in a bold rounded sans (Nunito/Inter 800)
at ~70 % frame width, white `#FFFFFF`, plus a 0.6 s fade-in and the existing
`Curtain` fade-out. Reference: §5 of the timeline, measured RGB (24,8,8).

### 11.7 Reconcile the presenter

The reference has **no host at all**, so `host_full` / `host_pip` will read as a
different format. Two sane options:

- **Reference-faithful:** use `broll_only` for the body, keep `host_full` for at
  most an opening and closing line (0–6 s), and drop the persistent wordmark.
- **Channel-personality:** keep the presenter for intros/outros and use the
  subtitle + hard-cut treatment for the body.

Either way, the presenter should be framed with the same grade and should not
have a caption laid over the face; the reference's clear lower third is what
makes its subtitles so readable.

### 11.8 The one thing CSS cannot fix

Every shot in the reference **moves within itself**: a hand lowers an envelope,
a man raises a pouch, a door swings open. Our stills only push and tilt. To get
close, either:

- generate 3–5 s AI video clips per scene and play them as `OffthreadVideo`
  plates (the presenter component already proves that path works), or
- **animate the stills** — cut the subject out, add 2–3 parallax layers plus a
  small vertical bob and a light flicker, so each shot has drawn motion rather
  than camera motion.

I would do the second first: it is cheap, deterministic, and reuses the
`CinematicDoc` camera code, while AI clips can be layered in per scene later via
a new `video` field next to `image`.

---

## 12. Suggested target structure

```jsonc
{
  "title": "12th Street",
  "style": {
    "letterbox": false,
    "atmosphereOpacity": 0,
    "lightSweep": false,
    "wordmark": "none"
  },
  "outro": { "title": "Where No One Sees", "durationInSeconds": 3 },
  "scenes": [
    {
      "layout": "broll_only",
      "transition": "cut",
      "grade": "cold",
      "image_url": "episodes/x/scene-1.jpg",
      "captions": [
        { "text": "In 1910,", "from": 0.4, "to": 1.1 },
        { "text": "the church counted", "from": 1.1, "to": 1.9 },
        { "text": "its money twice.", "from": 1.9, "to": 3.0 }
      ],
      "durationInSeconds": 3
    }
  ]
}
```

This keeps every existing episode renderable (new fields are optional and the
normalisers in `Root.tsx` / `render.js` already default missing values) while
letting new episodes opt into the reference look.

---

## 13. What not to copy

- **The zero-silence audio.** A continuous bed with no gaps fits a 71 s story
  short; our longer episodes need breaths and hard pauses.
- **Sub-1 s shots as a default.** 0.75 s cuts work here because the animation is
  simple and the subtitles carry meaning. Over photographic stills they would read
  as a slideshow blink. Keep 2–3 s as the floor unless the plate is moving.
- **No lower-third identification at all.** The reference never names a person,
  place or date on screen. For history content, a restrained name/date line in
  the `host_full` scenes is worth keeping.

---

*Method recap: `ffprobe` metadata; 286 frames at 4 fps, frame-difference pass for
cuts (34 detected, no dissolves); 36 frames at 2 s for the visual pass; PIL colour
statistics per shot; 0.5 s RMS audio profile. Temporary frame folders were deleted
after the analysis.*
