#!/usr/bin/env python3
"""
generate_script.py — write a 60 s horror short as episode_schema.json.

"The End of the Corridor" was hand-written. This is the head of the pipeline:
topic in, shot list out, shaped exactly like the schema that
generate_video_free.py and sound_design.sh already read.

    python3 generate_script.py "A haunted asylum"
    python3 generate_script.py "A flooded car park" --out /tmp/ep.json --overwrite
    python3 generate_script.py "A motel at 3am" --total 60 --seed 7
    python3 generate_script.py --offline "test"          # no network, canned story

The LLM is Pollinations' classic text API: free, keyless, one anonymous request
per IP every 45 s. Two consequences are baked in:

  * ONE request produces both the story and the twelve beats. Asking twice
    would mean waiting out the 45 s slot again.
  * No Authorization header is ever sent. A dummy key turns a working
    anonymous call into a 402, so a key is only used if
    POLLINATIONS_TOKEN is set (that means an enter.pollinations.ai key).

Every field the model returns is validated, because a 60 s story is editorial
and a bad duration or a missing voice line silently breaks the render:

  * exactly 12 shots, ids 1..12, unique slugs
  * duration_s clamped to 3.0-5.0 and scaled to --total seconds
  * frames = duration * fps (what AnimateDiff is asked for)
  * layout in broll_only / host_pip / host_full, at most two on-camera beats,
    never consecutive
  * a voiceover line per shot, flagged when too long to say in its duration

The prompt is the image prompt (AnimateDiff conditioning); `vo` is the
narrator; `layout` is the Remotion layout for that beat.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCHEMA_PATH = ROOT / "episode_schema.json"

API = "https://text.pollinations.ai/openai"
LLM_MODEL = "openai"          # the free anonymous model (gpt-oss-20b)

LAYOUTS = ("broll_only", "host_pip", "host_full")
MIN_SHOT, MAX_SHOT = 3.0, 5.0
SHOT_COUNT = 12

# Keep the look of the hand-written schema: same model, same grade, same
# faceless-figure rule that AnimateDiff can actually hold for 24 frames.
BASE = {
    "model": "SG161222/Realistic_Vision_V5.1_noVAE",
    "adapter": "guoyww/animatediff-motion-adapter-v1-5-2",
    "width": 512,
    "height": 512,
    "frames": 24,
    "fps": 8,
    "steps": 25,
    "guidance": 7.0,
}

NEGATIVE = (
    "face, facial features, close-up face, eyes, teeth, gore, blood, cartoon, "
    "anime, 3d render, lowres, jpeg artifacts, watermark, text, logo, extra "
    "fingers, deformed hands, duplicate figure, split screen, oversaturated, "
    "daylight, bright, cheerful, cgi"
)

GRADE = {
    "note": "AnimateDiff cannot hold a face across 24 frames, so the figure is "
            "deliberately faceless: always shot from behind, always crushed into "
            "silhouette. Post: lift contrast, crush blacks to #000, hold a cold "
            "teal shadow, no rim light on the figure."
}

STYLE = (
    "cinematic film still, horror, crushed blacks, heavy vignette, cold tungsten "
    "or sickly fluorescent light, deep black shadows, 35mm film grain, anamorphic, "
    "high contrast, no visible face, no gore, unsettling stillness"
)

# The prompt is assembled from these two halves so the model's own wording can
# be sanitised in between instead of duplicating the house style.
PROMPT_PREFIX = "cinematic film still, horror"
PROMPT_TAIL = (
    "crushed blacks, heavy vignette, cold tungsten or sickly fluorescent light, "
    "deep black shadows, 35mm film grain, anamorphic, high contrast, "
    "unsettling stillness"
)

# AnimateDiff cannot hold a face across 24 frames, and NEGATIVE already lists
# face/eyes/teeth, so anything the model writes about them has to go: a prompt
# that says "her eyes wide" fights its own negative prompt.
BANNED = re.compile(
    r"\b(face|faces|facial|eye|eyes|teeth|smile|smiles|grin|grins|grinning|gore|"
    r"blood|bloody|mouth|skin|pupils?)\b", re.I)
FIGURE = re.compile(
    r"\b(figure|silhouette|narrator|she|he|her|his|woman|man|nurse|girl|boy|"
    r"someone|something)\b", re.I)

SYSTEM = f"""You write 60-second horror shorts for a channel called "The End of \
the Corridor". The house style is quiet dread, not gore: one impossible thing, \
seen at a distance, never explained. The figure is always faceless and usually \
seen from behind.

Return ONLY a JSON object, no prose and no markdown fence, with this shape:

{{
  "title": "short episode title",
  "logline": "one sentence",
  "story": "the 60 second story as continuous prose, 120-160 words",
  "shots": [
    {{"title": "beat title",
      "prompt": "image prompt for a still, 25-45 words",
      "vo": "the narrator line spoken over this shot",
      "duration_s": 5.0,
      "on_camera": false}}
  ]
}}

Rules, all mandatory:
- exactly {SHOT_COUNT} shots that tell the whole story in order
- each duration_s between {MIN_SHOT} and {MAX_SHOT}; total about 60 seconds
- each `vo` is ONE spoken sentence, at most 14 words, in present tense
- each `prompt` describes a single concrete image: place, light, framing.
  Describe the subject from behind or as a distant silhouette. Never a face,
  never gore. Start each prompt with "cinematic film still, horror,".
- set on_camera true for at most TWO shots, and only for the opening beat and
  the final beat (the narrator speaking to camera). All others false.
"""


def log(msg):
    print(f"[script] {msg}", flush=True)


def die(msg, code=1):
    print(f"[script] ERROR: {msg}", file=sys.stderr, flush=True)
    sys.exit(code)


# --------------------------------------------------------------------- the LLM
def call_llm(topic: str, args) -> dict:
    """One anonymous Pollinations request; retries only on the 45 s slot."""
    user = (
        f"Topic: {topic}\n"
        f"Write the episode now. {SHOT_COUNT} shots, about {args.total} seconds "
        f"in total. JSON only."
    )
    payload = {
        "model": args.model,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user},
        ],
        "temperature": args.temperature,
        "seed": args.seed,
        "stream": False,
    }
    data = json.dumps(payload).encode()

    headers = {"Content-Type": "application/json"}
    # Only an enter.pollinations.ai key belongs here; a dummy one is a 402.
    token = os.environ.get("POLLINATIONS_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
        log("using POLLINATIONS_TOKEN")
    else:
        log("anonymous request (no key, 45 s/IP slot)")

    deadline = time.monotonic() + args.max_wait
    attempt = 0
    while True:
        attempt += 1
        req = urllib.request.Request(API, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=args.timeout) as resp:
                body = json.loads(resp.read().decode())
            content = body["choices"][0]["message"]["content"]
            return parse_json(content)
        except urllib.error.HTTPError as exc:
            wait = _retry_after(exc)
            if exc.code in (402, 429) and wait and time.monotonic() + wait < deadline:
                log(f"HTTP {exc.code}; free slot returns in {wait:.0f}s, waiting")
                time.sleep(wait + 1)
                continue
            die(f"HTTP {exc.code} from Pollinations: {_short(exc.read())}")
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt < 3 and time.monotonic() + 5 < deadline:
                log(f"network error ({exc}); retrying")
                time.sleep(5)
                continue
            die(f"cannot reach Pollinations: {exc} (use --offline to test)")
        except (KeyError, IndexError, json.JSONDecodeError) as exc:
            die(f"unexpected API response: {exc}")
        if time.monotonic() > deadline:
            die(f"gave up after {attempt} attempts (--max-wait {args.max_wait}s)")


def _retry_after(exc) -> float | None:
    raw = exc.headers.get("Retry-After") if exc.headers else None
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _short(raw: bytes, limit: int = 300) -> str:
    text = raw.decode("utf-8", "replace").strip()
    return text[:limit] or "(empty body)"


def parse_json(content: str) -> dict:
    """Pull the JSON object out of a reply that may still carry a fence."""
    text = content.strip()
    fence = re.search(r"```(?:json)?\s*(.+?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        die(f"no JSON object in the reply: {text[:300]!r}")
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError as exc:
        die(f"the model returned invalid JSON ({exc}): {text[:300]!r}")


OFFLINE = {
    "title": "Offline Test Episode",
    "logline": "A canned story used to prove the schema writer works without a network.",
    "story": "Offline story text.",
    "shots": [
        {
            "title": f"Offline beat {i}",
            "prompt": "cinematic film still, horror, an empty corridor at night, "
                      "single ceiling lamp, patterned carpet, deep shadow, no people",
            "vo": f"Narration line {i}.",
            "duration_s": 5.0,
            "on_camera": i in (1, 12),
        }
        for i in range(1, 13)
    ],
}


# ------------------------------------------------------------------ validation
def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:40].rstrip("-") or "shot"


def clamp_durations(shots: list[dict], total: float) -> list[str]:
    """Clamp to 3-5 s, then scale to the requested total without leaving range."""
    warnings = []
    for shot in shots:
        shot["duration_s"] = float(shot.get("duration_s") or 5.0)
        if not MIN_SHOT <= shot["duration_s"] <= MAX_SHOT:
            warnings.append(
                f"shot {shot['id']}: duration_s {shot['duration_s']} clamped to "
                f"{MIN_SHOT}-{MAX_SHOT}"
            )
            shot["duration_s"] = min(max(shot["duration_s"], MIN_SHOT), MAX_SHOT)

    model_total = sum(s["duration_s"] for s in shots)
    # Keep the model's own pacing unless it missed the mark badly; rescaling a
    # 56 s answer to 60 s would flatten every shot to the same length.
    if abs(model_total - total) <= max(1.0, total * 0.10):
        return warnings

    # Proportional scale, then redistribute the leftover so the total is exact
    # without pushing anyone out of range.
    scale = total / model_total
    for shot in shots:
        shot["duration_s"] = round(
            min(max(shot["duration_s"] * scale, MIN_SHOT), MAX_SHOT), 2)
    for shot in sorted(shots, key=lambda s: s["duration_s"]):
        short = total - sum(s["duration_s"] for s in shots)
        if abs(short) < 0.01:
            break
        room = (MAX_SHOT if short > 0 else MIN_SHOT) - shot["duration_s"]
        step = min(short, room) if short > 0 else max(short, room)
        shot["duration_s"] = round(shot["duration_s"] + step, 2)
    warnings.append(
        f"model totalled {model_total:.1f}s; rescaled to "
        f"{sum(s['duration_s'] for s in shots):.1f}s"
    )
    return warnings


def assign_layouts(shots: list[dict]) -> list[str]:
    """Map on_camera to a layout, capped at two non-consecutive beats.

    Only the opening and closing beat may go on camera; that matches the
    host_full convention in remotion/src/types.ts (intro and outro).
    """
    warnings = []
    last_on = None
    on_count = 0
    ending = len(shots) - 1
    for index, shot in enumerate(shots):
        want = bool(shot.get("on_camera"))
        ok = (want and index in (0, ending) and on_count < 2
              and (last_on is None or index - last_on > 1))
        if want and not ok:
            warnings.append(
                f"shot {index + 1}: on_camera dropped (only the first/last beat, "
                f"at most two, never consecutive)"
            )
        if ok:
            shot["layout"] = "host_full"
            last_on = index
            on_count += 1
        else:
            shot["layout"] = "broll_only"
    return warnings


def sanitise_prompt(text: str) -> tuple[str, bool]:
    """Strip face/eye/gore clauses and re-attach the faceless-figure rule.

    Returns (body, changed). A prompt that survives empty falls back to an
    empty-room description rather than shipping a face the model cannot render.
    """
    body = text.strip()
    for prefix in (PROMPT_PREFIX, STYLE.split(", ", 2)[0]):
        while body.lower().startswith(prefix.lower()):
            body = body[len(prefix):].lstrip(", ")
    fragments = [f.strip() for f in re.split(r"[,;]", body) if f.strip()]
    kept = [f for f in fragments if not BANNED.search(f)]
    changed = len(kept) != len(fragments)
    body = ", ".join(kept)
    if not body:
        body = "an empty room at night, deep black shadow, no people"
        return body, True
    if FIGURE.search(body) and "behind" not in body.lower():
        body = f"{body}, seen from behind as a featureless black silhouette"
        changed = True
    return body, changed


def build_prompt(text: str) -> tuple[str, bool]:
    body, changed = sanitise_prompt(text)
    lower = body.lower()
    if "grain" in lower or "vignette" in lower:
        # the model already wrote house-style clauses; keep them once
        return f"{PROMPT_PREFIX}, {body}", changed
    return f"{PROMPT_PREFIX}, {body}, {PROMPT_TAIL}", changed


def validate(data: dict, args) -> tuple[list[dict], list[str]]:
    if not isinstance(data, dict):
        die("the model did not return a JSON object")
    raw_shots = data.get("shots")
    if not isinstance(raw_shots, list) or not raw_shots:
        die("the model returned no 'shots' array")
    if len(raw_shots) != SHOT_COUNT:
        die(f"the model returned {len(raw_shots)} shots, expected {SHOT_COUNT}. "
            f"Nothing was written; rerun (the model is sampled) or use --offline.")

    warnings = []
    shots = []
    seen_slugs = set()
    for index, raw in enumerate(raw_shots, 1):
        if not isinstance(raw, dict):
            die(f"shot {index} is not an object")
        raw_prompt = " ".join(str(raw.get("prompt") or "").split())
        prompt, scrubbed = build_prompt(raw_prompt)
        vo = " ".join(str(raw.get("vo") or "").split())
        title = " ".join(str(raw.get("title") or f"Shot {index}").split())
        if scrubbed:
            warnings.append(
                f"shot {index}: prompt mentioned a face/eyes/gore; those clauses "
                f"were removed to match the negative prompt"
            )
        if not prompt:
            die(f"shot {index} has no prompt (the image generator needs one)")
        if not vo:
            die(f"shot {index} has no narrator line (vo)")
        slug = slugify(raw.get("slug") or title)
        if slug in seen_slugs:
            slug = f"{slug}-{index}"
        seen_slugs.add(slug)
        shots.append({
            "id": index,
            "slug": slug,
            "title": title,
            "prompt": prompt,
            "vo": vo,
            "duration_s": float(raw.get("duration_s") or 5.0),
            "on_camera": bool(raw.get("on_camera")),
            "seed": args.seed * 10000 + index * 1101,
        })

    warnings += clamp_durations(shots, args.total)
    warnings += assign_layouts(shots)

    fps = args.fps or BASE["fps"]
    heavy = []
    for shot in shots:
        frames = int(round(shot["duration_s"] * fps))
        if frames % 2:
            frames += 1
        if args.max_frames and frames > args.max_frames:
            frames = args.max_frames
            if frames % 2:
                frames -= 1
            shot["duration_s"] = round(frames / fps, 2)
            warnings.append(
                f"shot {shot['id']}: capped to {frames} frames, so duration_s "
                f"became {shot['duration_s']}s (--max-frames {args.max_frames})"
            )
        shot["frames"] = frames
        if frames > 32:
            heavy.append(shot["id"])
        # ordinary narration is ~2.5 words/second at a documentary pace
        budget = shot["duration_s"] * 2.6
        if len(shot["vo"].split()) > budget:
            warnings.append(
                f"shot {shot['id']}: {len(shot['vo'].split())} words in "
                f"{shot['duration_s']}s will feel rushed (budget {budget:.0f})"
            )
    if heavy:
        warnings.append(
            f"shots {', '.join(str(i) for i in heavy)} ask for more than 32 frames "
            f"(@ {fps}fps); a 15 GB T4 may OOM and the ladder will drop the "
            f"clip to 24 frames"
        )

    for shot in shots:
        shot["note"] = (f"{'On camera' if shot['layout'] == 'host_full' else 'B-roll'}"
                        f" beat {shot['id']}/{SHOT_COUNT}")

    order = ["id", "slug", "title", "prompt", "vo", "layout", "duration_s",
             "frames", "seed", "note"]
    shots = [{k: shot[k] for k in order} for shot in shots]
    return shots, warnings


def build(topic: str, data: dict, args) -> dict:
    shots, warnings = validate(data, args)
    title = " ".join(str(data.get("title") or topic).split()) or topic
    episode = {
        "episode": title,
        "slug": slugify(title),
        "format": "horror-teaser",
        "logline": " ".join(str(data.get("logline") or "").split()),
        "story": " ".join(str(data.get("story") or "").split()),
        "source": {"topic": topic, "model": args.model,
                   "provider": "offline" if args.offline else "pollinations"},
        "base": {**BASE, "fps": args.fps or BASE["fps"],
                 "width": args.width or BASE["width"],
                 "height": args.height or BASE["height"]},
        "negative_prompt": NEGATIVE,
        "grade": GRADE,
        "shots": shots,
    }
    for warning in warnings:
        log(f"WARN {warning}")
    total = sum(s["duration_s"] for s in shots)
    # sound_design.sh hardcodes 9 x 3 s boundaries (DUR=27, HIT_AT=21.6s) for
    # the hand-written teaser. A generated episode of any other length needs
    # that block recomputed before the stinger will land on the right beat.
    if abs(total - 27.0) > 0.5:
        log(f"NOTE {total:.1f}s of picture: sound_design.sh's HIT_AT/RISER_AT/"
            f"DUR constants assume the 9-shot 27s teaser and must be recomputed "
            f"for this episode")
    log(f"{len(shots)} shots, {total:.1f}s, "
        f"{sum(1 for s in shots if s['layout'] == 'host_full')} on camera")
    return episode


def summary(episode: dict) -> None:
    print(f"\n  {episode['episode']}  ({episode['slug']})")
    print(f"  {episode['logline']}\n")
    for shot in episode["shots"]:
        cam = "CAM " if shot["layout"] == "host_full" else "broll"
        print(f"  {shot['id']:>2} [{cam}] {shot['duration_s']:.1f}s "
              f"{shot['frames']:>2}f  {shot['title']}")
        print(f"      vo: {shot['vo']}")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Write a 60 s horror short into episode_schema.json",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("topic", nargs="?", help='e.g. "A haunted asylum"')
    p.add_argument("--out", default=str(SCHEMA_PATH),
                   help="destination schema (default episode_schema.json)")
    p.add_argument("--overwrite", action="store_true")
    p.add_argument("--offline", action="store_true",
                   help="skip the network and use a canned story (shapes test)")
    p.add_argument("--model", default=LLM_MODEL)
    p.add_argument("--total", type=float, default=60.0, help="target seconds")
    p.add_argument("--fps", type=int, help="frames per second (overrides base)")
    p.add_argument("--max-frames", type=int, default=0,
                   help="cap frames per shot (e.g. 32 for a 15 GB T4); "
                        "duration_s follows the cap")
    p.add_argument("--width", type=int)
    p.add_argument("--height", type=int)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--temperature", type=float, default=0.9)
    p.add_argument("--timeout", type=float, default=180.0)
    p.add_argument("--max-wait", type=float, default=120.0,
                   help="seconds to wait out the free 45 s slot")
    p.add_argument("--print-only", action="store_true",
                   help="show the schema on stdout, write nothing")
    args = p.parse_args(argv)

    if not args.topic:
        die('no topic given; e.g. python3 generate_script.py "A haunted asylum"')
    if args.offline and not args.topic:
        die("--offline still needs a topic for the filename")

    out = Path(args.out)
    if out.exists() and not (args.overwrite or args.print_only):
        die(f"{out.name} exists; pass --overwrite or --out another/file.json")

    log(f"topic: {args.topic}")
    data = OFFLINE if args.offline else call_llm(args.topic, args)
    episode = build(args.topic, data, args)
    summary(episode)

    text = json.dumps(episode, indent=2) + "\n"
    if args.print_only:
        print(text)
        return 0
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)
    log(f"wrote {out}"
        + ("" if out.is_absolute() else f" ({out.resolve()})"))
    log("next: python3 generate_video_free.py --dry-run   # check the shot list")
    return 0


if __name__ == "__main__":
    sys.exit(main())
