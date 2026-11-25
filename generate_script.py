#!/usr/bin/env python3
"""
generate_script.py — write a 60 s horror short as episode_schema.json.

Every episode is a four-act short: hook (1-2), escalation (3-6), climax
(7-9), twist/cliffhanger (10-12), with short show-don't-tell narration.

"The End of the Corridor" was hand-written. This is the head of the pipeline:
topic in, shot list out, shaped exactly like the schema that
make_horror_stickman.py (the active CPU engine) reads.

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
  * a cast of 2-3 characters, each with a prompt-safe `look` (clothing, hair,
    build) and a full `reference` + `reference_prompt` for a reference sheet
  * exactly one focus character per shot: a two-hander is written as coverage
    (close-up, over-the-shoulder, insert) instead of two bodies in one frame
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

# 4-Act structure, mapped onto the 12 shots. The writer must hit these turns;
# validate() checks the model actually labelled them correctly.
ACTS = {
    1: (1, 2, "THE HOOK"),
    2: (3, 6, "THE ESCALATION"),
    3: (7, 9, "THE CLIMAX"),
    4: (10, 12, "THE TWIST / CLIFFHANGER"),
}

# A cast of two or three: one protagonist, one antagonist, optionally a victim.
MIN_CHARS, MAX_CHARS = 2, 3
ROLES = ("protagonist", "antagonist", "victim", "supporting")

# Filmmaking coverage with a single subject per setup. This is the whole point:
# the image model renders one character per frame reliably and two unreliably,
# so a two-hander is written as a sequence of cuts, never one wide shot.
SHOT_TYPES = {
    "wide": "wide shot, full environment",
    "medium": "medium shot, waist up",
    "close_up": "extreme close-up, shallow depth of field",
    "over_shoulder": "over-the-shoulder shot, foreground shoulder out of focus",
    "insert": "macro insert shot of an object, no people",
    "pov": "point of view shot, hand held, no visible subject",
}

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

# Show, don't tell: narration that names the feeling instead of the evidence.
TELLING = re.compile(
    r"\b(scared|terrified|afraid|frightened|horrified|panic|panicked|petrified|"
    r"fear|fearful|terrifying)\b", re.I)

# Lines that break the fiction instead of deepening it.
META = re.compile(
    r"\b(tune in|next time|subscribe|like and|follow|comment|stay tuned|"
    r"episode|series|channel)\b", re.I)

SYSTEM = f"""You write 60-second horror shorts for a channel called "The End of \
the Corridor". You are a master of quiet dread: Stephen King's ordinary \
detail meeting a creepypasta's rules and wrongness. One impossible thing, seen \
at a distance, never fully explained. No gore.

Every episode MUST follow this 4-Act structure, mapped onto the {SHOT_COUNT} shots:
1. THE HOOK (shots 1-2): shot 1 opens mid-crisis with a terrifying line that \
makes the viewer stop scrolling. No setup, no weather report, no waking up.
2. THE ESCALATION (shots 3-6): the protagonist realises they are in danger. \
Establish the creepy setting and, when it fits, a RULE they must obey ("never \
look at the passenger"). Raise the pressure every shot; let ordinary objects \
turn wrong.
3. THE CLIMAX (shots 7-9): the visual reveal or jump-scare. Show the threat \
clearly for one beat, then take it away.
4. THE TWIST / CLIFFHANGER (shots 10-12): the last voiceover line \
recontextualises what we saw or leaves dread hanging. Never resolve safely.

Cast every episode with {MIN_CHARS}-{MAX_CHARS} named characters. The image model \
renders ONE character per frame reliably and two unreliably, so write the \
episode as standard coverage: each shot is its own single-subject setup, cut \
together in the edit.

Return ONLY a JSON object, no prose and no markdown fence:

{{
  "title": "short episode title",
  "logline": "one sentence",
  "story": "the 60 second story as continuous prose, 80-100 words",
  "characters": [
    {{"id": "mara",
      "name": "Mara",
      "role": "protagonist",
      "look": "thirties, dark wet shoulder-length hair, long grey wool coat, black boots, lean build",
      "reference": {{"age": "thirties", "hair": "dark, wet, shoulder length",
                     "clothing": "long grey wool coat, black boots",
                     "features": "sharp nose, tired eyes, pale skin",
                     "build": "lean, average height"}}}}
  ],
  "shots": [
    {{"title": "beat title",
      "act": 1,
      "shot_type": "close_up",
      "focus": "mara",
      "foreground": null,
      "prompt": "the image: place, light, action, 15-25 words",
      "vo": "the line spoken over this shot",
      "speaker": "narrator",
      "duration_s": 5.0,
      "on_camera": false}}
  ]
}}

Writing rules, all mandatory:
- one present-tense sentence per shot, 10-15 words, never more than 15. Shot 1 \
carries the hook line; shot 12 carries the twist.
- Show, don't tell. Never name an emotion ("she was terrified"); write its \
physical evidence ("her hands shook on the wheel", "the wipers stopped \
mid-swipe"). Put the fear in objects, movement and sound.
- The monster stays mysterious: no name, origin, motive or full explanation. \
Give one or two concrete wrong details (too many joints, a smile that does not \
move, a thumb on the wrong side) and never let a character explain it.
- Reveal order: wrongness before danger, danger before the full sight. The \
climax shows only what the protagonist can see.
- The antagonist must be the focus of at least one climax shot (7-9), seen from \
behind, in profile or as a silhouette. The viewer must see the threat, even if \
they cannot understand it.
- Every character in "characters" must appear as a focus or foreground in at \
least one shot. Do not invent filler cast.
- Count the words in every "vo": 10-15, never fewer than 10 and never more \
than 15.

Technical rules, all mandatory:
- every shot carries "act": 1-4, matching the structure above (shots 1-2 -> 1, \
3-6 -> 2, 7-9 -> 3, 10-12 -> 4)
- exactly {SHOT_COUNT} shots in story order, each {MIN_SHOT}-{MAX_SHOT} seconds, \
total about 60 seconds
- roles: exactly one "protagonist" and exactly one "antagonist"; "victim" and \
"supporting" are optional
- "id" is lowercase with hyphens; every focus, foreground and speaker must use \
those ids
- ONE focus character per shot. Never two people in one frame. A second body is \
only allowed as the optional "foreground" of an over_shoulder shot, described \
as a dark out-of-focus shoulder and back
- varied coverage: wide establish, medium, close_up, over_shoulder, insert (an \
object or empty room, focus "none"), pov. Never repeat the same setup twice in \
a row
- identify characters by their "look" in the prompt (clothing, hair, build), \
never by name alone, so the image model can actually render them
- each "vo" must belong to the shot it sits on. "speaker" is "narrator" for \
narration, or a character id when that character says the line (they may be \
off-screen)
- prompts never contain faces, eyes, teeth or gore: a figure is seen from \
behind, in profile, out of focus, or as a silhouette. Start each prompt with \
"cinematic film still, horror,".
- set on_camera true for at most TWO shots, and only the opening and final beat
"""

POLISH_SYSTEM = f"""You are the head writer on a horror anthology. You receive a \
finished {SHOT_COUNT}-shot, four-act episode and rewrite ONLY its voiceover \
lines.

Return ONLY a JSON object, no prose and no fence:
{{"vo": ["line for shot 1", "line for shot 2", ... exactly {SHOT_COUNT} strings]}}

Rules, all mandatory:
- each line is ONE present-tense sentence of 10-15 words. Count the words; \
never go below 10 or above 15.
- show, don't tell: no emotion words. Use physical evidence, objects and sound.
- keep each line tied to that shot's image, action and speaker.
- shots 1-2 are the hook (line 1 must stop a scroll). Shots 3-6 escalate; keep \
any rule stated in the original. Shots 7-9 are the reveal. Shots 10-12 are the \
twist; line 12 must recontextualise the story.
- never address the audience. No "tune in", "next time", "subscribe" or \
episode/series talk.
- the monster stays unexplained: no name, origin or motive.
"""


class SoftError(RuntimeError):
    """A reply we can usefully re-ask for: truncated, fenced, malformed."""


def log(msg):
    print(f"[script] {msg}", flush=True)


def die(msg, code=1):
    print(f"[script] ERROR: {msg}", file=sys.stderr, flush=True)
    sys.exit(code)


# --------------------------------------------------------------------- the LLM
def call_llm(topic: str, args, correction: str | None = None, *,
             system: str | None = None, user: str | None = None) -> dict:
    """One anonymous Pollinations request; retries only on the 45 s slot."""
    user = user or (
        f"Topic: {topic}\n"
        f"Write the episode now with {MIN_CHARS}-{MAX_CHARS} characters and "
        f"{SHOT_COUNT} shots, about {args.total} seconds in total. JSON only."
    )
    if correction:
        user = f"{user}\n\n{correction}"
    payload = {
        "model": args.model,
        "messages": [
            {"role": "system", "content": system or SYSTEM},
            {"role": "user", "content": user},
        ],
        "temperature": args.temperature,
        "seed": args.seed,
        "max_tokens": args.max_tokens,
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
        except (KeyError, IndexError) as exc:
            raise SoftError(f"unexpected API response: {exc}") from exc
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
        raise SoftError(f"no JSON object in the reply: {text[:200]!r}")
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError as exc:
        # most often the reply was cut off, which a retry can fix
        raise SoftError(f"invalid or truncated JSON ({exc})") from exc


OFFLINE = {
    "title": "Offline Test Episode",
    "logline": "A canned three-hander used to prove the cast writer works offline.",
    "story": "Offline story text.",
    "characters": [
        {"id": "mara", "name": "Mara", "role": "protagonist",
         "look": "woman in her thirties, dark wet shoulder-length hair, long grey "
                 "wool coat, black boots, lean build",
         "reference": {"age": "thirties", "hair": "dark, wet, shoulder length",
                       "clothing": "long grey wool coat, black boots",
                       "features": "sharp nose, tired eyes, pale skin",
                       "build": "lean, average height"}},
        {"id": "hollow-man", "name": "The Hollow Man", "role": "antagonist",
         "look": "very tall emaciated man, long black coat, black gloves, bald "
                 "pale head, unnaturally long arms",
         "reference": {"age": "indeterminate", "hair": "none, bald",
                       "clothing": "long black coat, black gloves",
                       "features": "pale featureless face, sunken sockets",
                       "build": "very tall, emaciated"}},
        {"id": "june", "name": "June", "role": "victim",
         "look": "teenage girl in a red rain jacket, dark ponytail, small build",
         "reference": {"age": "sixteen", "hair": "dark ponytail",
                       "clothing": "red rain jacket, dark jeans",
                       "features": "freckles, wide eyes",
                       "build": "small, slight"}},
    ],
    "shots": [
        {
            "title": f"Offline beat {i}",
            "shot_type": ["wide", "medium", "close_up", "over_shoulder", "insert",
                          "pov"][i % 6],
            "focus": "mara" if i in (1, 12) else ["mara", "hollow-man", "june"][i % 3],
            "foreground": "hollow-man" if i % 6 == 3 else None,
            "prompt": "an empty corridor at night, single ceiling lamp, patterned "
                      "carpet, deep shadow",
            "vo": f"Narration line {i}.",
            "speaker": "mara" if i == 6 else "narrator",
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


PLACEHOLDER = re.compile(
    r"reference sheet|prompt-safe|face details|no facial features|"
    r"visual identity|one clause|^\.\.\.$", re.I)


def is_placeholder(value: str) -> bool:
    """True when the model echoed an instruction instead of writing content."""
    return bool(value) and bool(PLACEHOLDER.search(value))


def clean_look(text: str) -> str:
    """A prompt-safe identity clause: drop anything about a face.

    Shots are rendered by AnimateDiff, which cannot hold a face across 24
    frames and whose negative prompt already bans face/eyes/teeth, so the
    look that goes into a shot prompt is clothing, hair and build only. The
    full face description stays in `reference` for the reference sheet.
    """
    fragments = [f.strip() for f in re.split(r"[,;]", str(text)) if f.strip()]
    return ", ".join(f for f in fragments if not BANNED.search(f))


def reference_prompt(character: dict) -> str:
    """A sheet an image model can draw faces on — unlike the shot prompts."""
    ref = character["reference"]
    bits = [f"character reference sheet of {character['name']}", character["look"]]
    for key in ("age", "hair", "clothing", "features", "build"):
        value = ref.get(key)
        if value:
            bits.append(f"{key}: {value}")
    bits += [
        "neutral standing pose, full body, front view and back view side by side",
        "flat even lighting, plain mid-grey backdrop, no props, no text, no logo",
        "cinematic film still, 35mm film grain",
    ]
    return ", ".join(bits)


def normalise_characters(data: dict, warnings: list[str]) -> list[dict]:
    """Validate and complete the cast. Returns characters in schema order."""
    raw = data.get("characters")
    if not isinstance(raw, list) or not raw:
        die("the model returned no 'characters' array (the cast is required); "
            "rerun, or use --offline to test the format")
    if len(raw) > MAX_CHARS:
        warnings.append(f"{len(raw)} characters returned; kept the first "
                        f"{MAX_CHARS} (MAX_CHARS={MAX_CHARS})")
        raw = raw[:MAX_CHARS]
    if len(raw) < MIN_CHARS:
        die(f"the model returned {len(raw)} character(s); at least {MIN_CHARS} "
            f"needed for a cast")

    characters = []
    seen = set()
    for index, item in enumerate(raw, 1):
        if not isinstance(item, dict):
            die(f"character {index} is not an object")
        name = " ".join(str(item.get("name") or f"Character {index}").split())
        cid = slugify(item.get("id") or name)
        if cid in seen:
            cid = f"{cid}-{index}"
        seen.add(cid)
        role = str(item.get("role") or "supporting").strip().lower()
        if role not in ROLES:
            warnings.append(f"character {cid}: unknown role {role!r}, set supporting")
            role = "supporting"
        look = clean_look(item.get("look") or "")
        ref_raw = item.get("reference") if isinstance(item.get("reference"), dict) else {}
        reference = {key: " ".join(str(ref_raw.get(key) or "").split())
                     for key in ("age", "hair", "clothing", "features", "build")}
        echoed = [k for k, v in reference.items() if is_placeholder(v)]
        for key in echoed:
            warnings.append(
                f"character {cid}: reference.{key} echoed the instruction "
                f"({reference[key]!r}); dropped so it cannot leak into a prompt")
            reference[key] = ""
        if not look:
            look = clean_look(", ".join(v for k, v in reference.items()
                                         if k != "features" and v))
        if not look:
            die(f"character {cid} has no 'look' and no usable reference; "
                f"give a visual description so it can be rendered")
        missing = [k for k, v in reference.items() if not v and k != "features"]
        if missing:
            warnings.append(f"character {cid}: reference is missing "
                            f"{', '.join(missing)} (weaker reference sheet)")
        character = {"id": cid, "name": name, "role": role, "look": look,
                     "reference": reference}
        character["reference_prompt"] = reference_prompt(character)
        characters.append(character)

    roles = [c["role"] for c in characters]
    for needed in ("protagonist", "antagonist"):
        if needed not in roles:
            warnings.append(f"the cast has no {needed}; the model did not follow "
                            f"the role rule, so prompts rely on 'look' alone")
    return characters


def build_prompt(text: str, focus: dict | None = None,
                 shot_type: str = "medium",
                 foreground: dict | None = None) -> tuple[str, bool]:
    body, changed = sanitise_prompt(text)
    framing = SHOT_TYPES.get(shot_type, SHOT_TYPES["medium"])
    pieces = [PROMPT_PREFIX, framing]
    if body:
        pieces.append(body)
    if focus is not None:
        pieces.append(f"subject {focus['name']}: {focus['look']}")
    if foreground is not None:
        pieces.append(f"foreground {foreground['name']}: {foreground['look']}, "
                      f"only a dark out-of-focus shoulder and back visible")
    pieces = [p for p in pieces if p]
    if "grain" not in body.lower():
        pieces.append(PROMPT_TAIL)
    return ", ".join(pieces), changed


def structural_problems(data) -> list[str]:
    """Cheap checks worth one more (45 s) request before field validation."""
    if not isinstance(data, dict):
        return ["the reply was not a JSON object"]
    problems = []
    chars = data.get("characters")
    if not isinstance(chars, list) or not chars:
        problems.append("no 'characters' array")
    else:
        if not MIN_CHARS <= len(chars) <= MAX_CHARS:
            problems.append(f"{len(chars)} characters returned, need "
                            f"{MIN_CHARS}-{MAX_CHARS}")
        roles = {str(c.get("role", "")).strip().lower()
                 for c in chars if isinstance(c, dict)}
        for needed in ("protagonist", "antagonist"):
            if needed not in roles:
                problems.append(f"no {needed} in the cast")
    shots = data.get("shots")
    if not isinstance(shots, list):
        problems.append("no 'shots' array")
    elif len(shots) != SHOT_COUNT:
        problems.append(f"{len(shots)} shots returned, need exactly {SHOT_COUNT}")
    else:
        built = [s for s in shots if isinstance(s, dict)]
        # ---- voiceover must never exceed 15 words; shorter is a warning
        long = [f"shot {i}:{len(str(s.get('vo', '')).split())}"
                for i, s in enumerate(built, 1)
                if len(str(s.get("vo", "")).split()) > 15]
        if long:
            problems.append("vo over the 15-word limit on " + ", ".join(long))
        # ---- the antagonist has to actually be seen in the climax
        by_role = {str(c.get("role", "")).strip().lower(): slugify(str(c.get("id", "")))
                   for c in (chars or []) if isinstance(c, dict)}
        antagonist = by_role.get("antagonist")
        climax = built[6:9]
        if antagonist and not any(
                slugify(str(s.get("focus", ""))) == antagonist for s in climax):
            problems.append("the antagonist is never the focus of a climax shot (7-9)")
        # ---- no filler cast: every named character must be on screen somewhere
        seen = set()
        for s in built:
            focus = s.get("focus")
            for value in (focus if isinstance(focus, list) else [focus]):
                seen.add(slugify(str(value or "")))
            seen.add(slugify(str(s.get("foreground") or "")))
        unused = [str(c.get("id")) for c in (chars or [])
                  if isinstance(c, dict) and slugify(str(c.get("id", ""))) not in seen]
        if unused:
            problems.append("characters never on screen: " + ", ".join(unused))
    return problems


def validate(data: dict, args, characters: list[dict]) -> tuple[list[dict], list[str]]:
    if not isinstance(data, dict):
        die("the model did not return a JSON object")
    raw_shots = data.get("shots")
    if not isinstance(raw_shots, list) or not raw_shots:
        die("the model returned no 'shots' array")
    if len(raw_shots) != SHOT_COUNT:
        die(f"the model returned {len(raw_shots)} shots, expected {SHOT_COUNT}. "
            f"Nothing was written; rerun (the model is sampled) or use --offline.")

    by_id = {c["id"]: c for c in characters}
    default_focus = next((c for c in characters if c["role"] == "protagonist"),
                         characters[0])
    warnings = []
    shots = []
    seen_slugs = set()
    seen_characters = set()

    for index, raw in enumerate(raw_shots, 1):
        if not isinstance(raw, dict):
            die(f"shot {index} is not an object")

        # ---- one subject per frame: this is the multi-character guarantee
        raw_focus = raw.get("focus")
        if isinstance(raw_focus, list):
            if len(raw_focus) > 1:
                warnings.append(
                    f"shot {index}: {len(raw_focus)} characters in one frame; kept "
                    f"{raw_focus[0]} and cut the rest (one subject per frame)")
            raw_focus = raw_focus[0] if raw_focus else None
        focus_key = slugify(str(raw_focus or ""))
        if focus_key in ("", "none", "null"):
            focus = None
        else:
            focus = by_id.get(focus_key)
            if focus is None:
                warnings.append(
                    f"shot {index}: focus {raw_focus!r} is not in the cast; "
                    f"using {default_focus['id']}")
                focus = default_focus

        shot_type = slugify(raw.get("shot_type") or "medium").replace("-", "_")
        if shot_type not in SHOT_TYPES:
            warnings.append(f"shot {index}: unknown shot_type {shot_type!r}; medium")
            shot_type = "medium"
        if focus is None and shot_type not in ("insert", "pov"):
            warnings.append(
                f"shot {index}: no focus character on a {shot_type} shot; "
                f"using {default_focus['id']}")
            focus = default_focus
        if focus is not None and shot_type in ("insert", "pov"):
            warnings.append(
                f"shot {index}: {shot_type} with focus {focus['id']}; "
                f"inserts read better empty")
            focus = None

        # ---- the only legal second body: a foreground shoulder on an OTS
        foreground = None
        raw_fg = raw.get("foreground")
        if raw_fg:
            fg_key = slugify(str(raw_fg[0] if isinstance(raw_fg, list) else raw_fg))
            candidate = by_id.get(fg_key)
            if shot_type != "over_shoulder":
                warnings.append(
                    f"shot {index}: foreground {raw_fg!r} dropped, only an "
                    f"over_shoulder shot may carry a second body")
            elif candidate is None or candidate is focus:
                warnings.append(
                    f"shot {index}: foreground {raw_fg!r} is unknown or is the "
                    f"focus; dropped")
            else:
                foreground = candidate

        # ---- who says the line on this shot
        speaker = " ".join(str(raw.get("speaker") or "narrator").split()).lower()
        if speaker not in ("narrator", "none") and speaker not in by_id:
            warnings.append(
                f"shot {index}: speaker {speaker!r} is not in the cast; narrator")
            speaker = "narrator"

        raw_prompt = " ".join(str(raw.get("prompt") or "").split())
        prompt, scrubbed = build_prompt(raw_prompt, focus, shot_type, foreground)
        if scrubbed:
            warnings.append(
                f"shot {index}: prompt mentioned a face/eyes/gore; those clauses "
                f"were removed to match the negative prompt")
        vo = " ".join(str(raw.get("vo") or "").split())
        title = " ".join(str(raw.get("title") or f"Shot {index}").split())
        if not raw_prompt:
            die(f"shot {index} has no prompt (the image generator needs one)")
        if not vo:
            die(f"shot {index} has no narrator line (vo)")

        # ---- the 4-act structure, as the writer labelled it
        expected_act = next(a for a, (lo, hi, _) in ACTS.items()
                            if lo <= index <= hi)
        raw_act = raw.get("act")
        try:
            raw_act = int(raw_act)
        except (TypeError, ValueError):
            raw_act = None
        if raw_act is None:
            warnings.append(f"shot {index}: no act label; placed in act "
                            f"{expected_act} ({ACTS[expected_act][2]})")
        elif raw_act != expected_act:
            warnings.append(
                f"shot {index}: labelled act {raw_act} but lands in act "
                f"{expected_act} ({ACTS[expected_act][2]}); reclassified")

        # ---- voiceover length and the show-don't-tell rule
        words = len(vo.split())
        if words > 15:
            warnings.append(f"shot {index}: {words}-word line exceeds the "
                            f"15-word voiceover limit")
        elif words < 10:
            warnings.append(f"shot {index}: {words}-word line is under the "
                            f"10-word target")
        if TELLING.search(vo):
            warnings.append(
                f"shot {index}: vo names an emotion ({TELLING.search(vo).group(0)}); "
                f"show it through physical detail instead")

        slug = slugify(raw.get("slug") or title)
        if slug in seen_slugs:
            slug = f"{slug}-{index}"
        seen_slugs.add(slug)
        if focus is not None:
            seen_characters.add(focus["id"])
        shots.append({
            "id": index,
            "slug": slug,
            "title": title,
            "act": expected_act,
            "shot_type": shot_type,
            "focus": focus["id"] if focus else "none",
            "foreground": foreground["id"] if foreground else None,
            "prompt": prompt,
            "vo": vo,
            "speaker": speaker,
            "duration_s": float(raw.get("duration_s") or 5.0),
            "on_camera": bool(raw.get("on_camera")),
            "seed": args.seed * 10000 + index * 1101,
        })

    warnings += clamp_durations(shots, args.total)
    warnings += assign_layouts(shots)

    protagonist = next((c["id"] for c in characters
                         if c["role"] == "protagonist"), None)
    for shot in shots:
        if (shot["layout"] == "host_full" and protagonist
                and shot["focus"] not in (protagonist, "none")):
            warnings.append(
                f"shot {shot['id']}: on camera but focused on "
                f"{shot['focus']}; the narrator is the person on screen, so "
                f"this shot will render the wrong character full frame")

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

    unused = [c["id"] for c in characters if c["id"] not in seen_characters]
    if unused:
        warnings.append(
            f"{', '.join(unused)} never appears as a focus in any shot; their "
            f"reference sheet is wasted and the cast is effectively smaller")

    for shot in shots:
        who = shot["focus"] if shot["focus"] != "none" else "no subject"
        shot["note"] = (f"{'On camera' if shot['layout'] == 'host_full' else 'B-roll'}"
                        f" \u00b7 {who} \u00b7 {shot['shot_type']}"
                        f" \u00b7 beat {shot['id']}/{SHOT_COUNT}")

    order = ["id", "slug", "title", "act", "shot_type", "focus", "foreground",
             "prompt", "vo", "speaker", "layout", "duration_s", "frames", "seed",
             "note"]
    shots = [{k: shot[k] for k in order} for shot in shots]
    return shots, warnings


def vo_problems(shots: list[dict]) -> list[str]:
    """Reasons the narration needs the head-writer pass."""
    out = []
    for shot in shots:
        words = len(shot["vo"].split())
        if words > 15:
            out.append(f"shot {shot['id']}: {words} words")
        elif words < 10:
            out.append(f"shot {shot['id']}: {words} words")
        if TELLING.search(shot["vo"]):
            out.append(f"shot {shot['id']}: names an emotion")
        if META.search(shot["vo"]):
            out.append(f"shot {shot['id']}: breaks the fiction")
    return out


def polish_vo(episode: dict, args) -> dict:
    """Rewrite narration to the 10-15 word, show-don't-tell bar.

    Small reply, so it fits the free model's output cap far more often than a
    full episode. On failure the draft is kept rather than lost.
    """
    shots = episode["shots"]
    problems = vo_problems(shots)
    if not problems:
        return episode
    log("polish: " + "; ".join(problems[:6])
        + (" ..." if len(problems) > 6 else ""))
    brief = {
        "title": episode["episode"],
        "logline": episode["logline"],
        "story": episode["story"],
        "shots": [
            {"id": s["id"], "act": s["act"], "title": s["title"],
             "shot_type": s["shot_type"], "speaker": s["speaker"],
             "image": s["prompt"][:180], "current_vo": s["vo"]}
            for s in shots
        ],
    }
    user = ("Episode:\n" + json.dumps(brief, indent=1)
            + f"\nReturn exactly {SHOT_COUNT} replacement lines as JSON.")
    for attempt in range(1, 4):
        try:
            data = call_llm(episode["episode"], args, system=POLISH_SYSTEM,
                            user=user)
        except SystemExit:
            log("WARN polish request failed; keeping the original narration")
            return episode
        except SoftError as exc:
            log(f"polish attempt {attempt}/3: {exc}")
            continue
        lines = data.get("vo")
        if (not isinstance(lines, list) or len(lines) != SHOT_COUNT
                or not all(isinstance(x, str) for x in lines)):
            log(f"polish attempt {attempt}/3: expected {SHOT_COUNT} strings")
            continue
        cleaned = [" ".join(x.split()) for x in lines]
        bad = [i + 1 for i, x in enumerate(cleaned)
               if not 10 <= len(x.split()) <= 15]
        wrong = [i + 1 for i, x in enumerate(cleaned)
                 if TELLING.search(x) or META.search(x)]
        if bad or wrong:
            log(f"polish attempt {attempt}/3: length {bad}, telling/meta {wrong}")
            continue
        for shot, line in zip(shots, cleaned):
            shot["vo"] = line
        log(f"polish: rewrote {len(cleaned)} narration lines")
        return episode
    log("WARN kept the original narration (polish gave no usable lines)")
    return episode


def build(topic: str, data: dict, args) -> dict:
    warnings = []
    characters = normalise_characters(data, warnings)
    shots, shot_warnings = validate(data, args, characters)
    warnings += shot_warnings
    title = " ".join(str(data.get("title") or topic).split()) or topic
    episode = {
        "episode": title,
        "slug": slugify(title),
        "format": "horror-teaser",
        "logline": " ".join(str(data.get("logline") or "").split()),
        "story": " ".join(str(data.get("story") or "").split()),
        "source": {"topic": topic, "model": args.model,
                   "provider": "offline" if args.offline else "pollinations"},
        "characters": characters,
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
    log(f"{len(characters)} characters, {len(shots)} shots, {total:.1f}s, "
        f"{sum(1 for s in shots if s['layout'] == 'host_full')} on camera")
    return episode


def summary(episode: dict) -> None:
    print(f"\n  {episode['episode']}  ({episode['slug']})")
    print(f"  {episode['logline']}\n")
    print("  CAST")
    for character in episode["characters"]:
        print(f"   {character['id']:<14} {character['role']:<12} "
              f"{character['name']}")
        print(f"   {'':<14} look: {character['look']}")
    print("\n  SHOTS")
    for shot in episode["shots"]:
        cam = "CAM " if shot["layout"] == "host_full" else "broll"
        fg = f" o/s {shot['foreground']}" if shot["foreground"] else ""
        said = "" if shot["speaker"] == "narrator" else f"  [{shot['speaker']} speaks]"
        print(f"  {shot['id']:>2} [act {shot['act']}] {shot['duration_s']:.1f}s "
              f"{shot['frames']:>2}f  {shot['shot_type']:<13} "
              f"{shot['focus']}{fg}")
        print(f"      vo: {shot['vo']}{said}")


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
    p.add_argument("--max-tokens", type=int, default=4000,
                   help="reply budget; 12 shots + 3 characters needs ~2000")
    p.add_argument("--max-wait", type=float, default=120.0,
                   help="seconds to wait out the free 45 s slot")
    p.add_argument("--retries", type=int, default=3,
                   help="re-ask when the cast or shot count is wrong (each "
                        "retry costs one 45 s slot)")
    p.add_argument("--no-polish", action="store_true",
                   help="skip the head-writer narration pass")
    p.add_argument("--polish-file",
                   help="rewrite only the narration of an existing episode JSON")
    p.add_argument("--print-only", action="store_true",
                   help="show the schema on stdout, write nothing")
    args = p.parse_args(argv)

    if args.polish_file:
        path = Path(args.polish_file)
        if not path.exists():
            die(f"no such episode: {path}")
        episode = json.loads(path.read_text(encoding="utf8"))
        (path.parent / (path.stem + ".prepolish.json")).write_text(
            json.dumps(episode, indent=2) + "\n", encoding="utf8")
        episode = polish_vo(episode, args)
        path.write_text(json.dumps(episode, indent=2) + "\n", encoding="utf8")
        summary(episode)
        log(f"wrote {path}")
        return 0

    if not args.topic:
        die('no topic given; e.g. python3 generate_script.py "A haunted asylum"')
    if args.offline and not args.topic:
        die("--offline still needs a topic for the filename")

    out = Path(args.out)
    if out.exists() and not (args.overwrite or args.print_only):
        die(f"{out.name} exists; pass --overwrite or --out another/file.json")

    log(f"topic: {args.topic}")
    attempts = (args.retries + 1) if not args.offline else 1
    correction = None
    data = None
    for attempt in range(1, attempts + 1):
        try:
            data = OFFLINE if args.offline else call_llm(args.topic, args, correction)
        except SoftError as exc:
            log(f"attempt {attempt}/{attempts}: {exc}")
            if attempt == attempts:
                die(f"no usable reply after {attempts} attempt(s): {exc}\n"
                    f"Nothing was written. Rerun, or use --offline.")
            correction = ("Your previous reply was not usable JSON ("
                          + str(exc) + "). Return ONLY the complete JSON object, "
                          "with exactly "
                          f"{MIN_CHARS}-{MAX_CHARS} characters and {SHOT_COUNT} "
                          "shots, and no commentary.")
            continue
        problems = structural_problems(data)
        if not problems:
            break
        log(f"attempt {attempt}/{attempts}: " + "; ".join(problems))
        if attempt == attempts:
            die("the model would not follow the format after "
                f"{attempts} attempt(s):\n  - " + "\n  - ".join(problems)
                + "\nNothing was written. Rerun, or use --offline.")
        correction = (
            "Your previous JSON broke these rules: " + "; ".join(problems) +
            f". Return the complete JSON again with exactly {MIN_CHARS}-{MAX_CHARS} "
            f"characters (one protagonist, one antagonist) and exactly "
            f"{SHOT_COUNT} shots."
        )

    episode = build(args.topic, data, args)
    if not args.offline and not args.no_polish:
        episode = polish_vo(episode, args)
    summary(episode)

    text = json.dumps(episode, indent=2) + "\n"
    if args.print_only:
        print(text)
        return 0
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)
    log(f"wrote {out}"
        + ("" if out.is_absolute() else f" ({out.resolve()})"))
    log("next: python3 make_horror_stickman.py --episode %s --max-seconds 15" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
