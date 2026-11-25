#!/usr/bin/env python3
"""
generate_story_director.py — a Director Mode writer for the stickman engine.

Why this exists: generate_script.py writes 12 good-looking shots that read like
disconnected captions. This script directs the other way round:

  1. WRITER  — the whole 12-beat narration is written first, as ONE continuous
     monologue with a single through-line, a rule, an escalation and a twist.
  2. DIRECTOR — each monologue beat is then assigned a shot (coverage, focus,
     image prompt), so the pictures illustrate the story instead of the story
     describing the pictures.

The direction follows the kaomei/stickman-video-director "Director Mode"
(A-mode) structure: hook, escalation, climax, twist; one subject per frame;
faceless, unexplained threat; 10-15 word narration beats. That skill is agent
guidance rather than a callable API, so its rules are encoded in the prompts
below rather than invoked as a command.

    python3 generate_story_director.py "A hitchhiker on a deserted highway"
    python3 generate_story_director.py "..." --out episodes/my-episode.json
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API = "https://text.pollinations.ai/openai"
MODEL = "openai"           # the only anonymous model on this endpoint
SHOTS = 12
FPS = 30

ROOT = Path(__file__).resolve().parent
DEFAULT_OUT = ROOT / "episodes" / "director-episode.json"

SHOT_TYPES = {
    "wide": "wide shot, full environment",
    "medium": "medium shot, waist up",
    "close_up": "extreme close-up, shallow depth of field",
    "over_shoulder": "over-the-shoulder shot, foreground shoulder out of focus",
    "insert": "macro insert shot of an object, no people",
    "pov": "point of view shot, hand held, no visible subject",
}

ACTS = {1: (1, 2, "THE HOOK"),
        2: (3, 6, "THE ESCALATION"),
        3: (7, 9, "THE CLIMAX"),
        4: (10, 12, "THE TWIST / CLIFFHANGER")}

TELLING = re.compile(
    r"\b(scared|terrified|afraid|frightened|horrified|panic|panicked|petrified|"
    r"fear|fearful|terrifying|agitation|agitated|anxious|nervous|uneasy|"
    r"disturbed|dread)\b", re.I)
META = re.compile(
    r"\b(tune in|next time|subscribe|like and|follow|comment|stay tuned|"
    r"episode|series|channel)\b", re.I)
BANNED_IMAGE = re.compile(
    r"\b(face|faces|facial|eye|eyes|teeth|smile|grin|gore|blood|bloody|"
    r"severed|dismembered|corpse|guts)\b", re.I)

WRITER_SYSTEM = f"""You are the head writer of a horror anthology. You write a \
{SHOTS}-beat, 60-second episode as ONE continuous monologue from the \
protagonist's point of view, then it is illustrated. The narration must weave \
the story together; it must not describe the pictures.

Return ONLY a JSON object, no prose and no fence:
{{
  "title": "short, specific title",
  "logline": "one sentence",
  "characters": [
    {{"id": "lowercase-id", "name": "Name", "role": "protagonist",
      "look": "age, hair, clothing, build in plain words"}},
    {{"id": "lowercase-id", "name": "Name", "role": "antagonist",
      "look": "age, clothing, and one wrong physical detail"}}
  ],
  "monologue": ["beat 1", "beat 2", ... exactly {SHOTS} strings]
}}

THE 4 ACTS (the monologue is one unbroken story across all {SHOTS} beats):
1. THE HOOK (beats 1-2): start mid-action with the wrong thing already \
happening. Beat 1 is the line that stops a scroll. Beat 2 tightens it.
2. THE ESCALATION (beats 3-6): the protagonist works out they are in danger \
and discovers the RULE they must not break. Every beat raises the cost of \
breaking it. Let ordinary objects behave wrongly.
3. THE CLIMAX (beats 7-9): the sighting. Show only what the protagonist sees, \
in the order they see it. Do not explain it.
4. THE TWIST (beats 10-12): recontextualise what came before. The final beat \
must make beat 1 mean something different and leave dread hanging. Never \
resolve safely.

COHESION RULES, all mandatory:
- Write it as spoken narration, one speaker, consistent tense and pronouns. \
Each beat must continue the previous beat's thought (use "and", "then", "but", \
"still", "because"), so the 12 lines read as one paragraph when joined.
- Never write captions like "she sees a door". Tell the story: what she does, \
what changes, what it costs her.
- 10-15 words per beat. Count them: never fewer than 10, never more than 15.
- Show, don't tell: no emotion words ("terrified", "afraid"). Use physical \
evidence, objects and sound.
- Keep the threat unexplained: no name, origin, motive or full description. \
Give it one concrete wrong detail and let the protagonist fail to finish \
describing it.
- English, present tense, no gore, no audience address.
"""

DIRECTOR_SYSTEM = f"""You are the director of a faceless stickman horror \
anthology. You receive a finished {SHOTS}-beat monologue and the cast. Assign \
one shot to every beat so the pictures carry the story.

Return ONLY a JSON object, no prose and no fence:
{{"shots": [
  {{"act": 1, "title": "beat title", "shot_type": "close_up",
    "focus": "character-id or none", "prompt": "the image, 15-25 words"}}
  ... exactly {SHOTS} shots in order
]}}

Rules, all mandatory:
- one focus character per shot, using the cast ids. Never two people in frame.
- varied coverage: wide, medium, close_up, over_shoulder, insert (focus \
"none"), pov. Never repeat the same setup twice in a row.
- the antagonist must be the focus of at least one climax shot (7-9), seen \
from behind, in profile or as a silhouette. The viewer must see the threat.
- inserts show the object or empty place that the line is about; no people.
- prompts are image-only: place, light, action, 15-25 words. No faces, eyes, \
teeth, smiles or gore. Start each prompt with "cinematic film still, horror,".
- set "act" to 1 for shots 1-2, 2 for 3-6, 3 for 7-9, 4 for 10-12.
"""


EDITOR_SYSTEM = f"""You are the script editor on a horror anthology. You \
receive the {SHOTS}-beat narration of one episode, already divided into beats. \
Rewrite ONLY the wording so it reads as one continuous, grammatical piece of \
storytelling.

Return ONLY a JSON object: {{"monologue": ["beat 1", ... exactly {SHOTS} strings]}}

Rules, all mandatory:
- keep every event and the same order; do not add or remove plot.
- one speaker, present tense, consistent pronouns, natural connective flow \
from beat to beat.
- 10-15 words per beat. Count: never below 10, never above 15.
- show, don't tell: no emotion words; use physical evidence.
- fix broken grammar and unclear references ("it", "the thing").
- keep the threat unexplained. The final beat must recontextualise beat 1 \
without explaining the monster.
- no audience address, no episode/series talk.
"""


def log(msg):
    print(f"[director] {msg}", flush=True)


def die(msg, code=1):
    print(f"[director] ERROR: {msg}", file=sys.stderr, flush=True)
    sys.exit(code)


def slugify(text):
    slug = re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")
    return slug[:48].rstrip("-") or "episode"


class SoftError(RuntimeError):
    """A reply worth retrying: truncated, fenced, or the wrong shape."""


def parse_json(content):
    text = content.strip()
    fence = re.search(r"```(?:json)?\s*(.+?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise SoftError(f"no JSON object in the reply: {text[:160]!r}")
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError as exc:
        raise SoftError(f"invalid or truncated JSON ({exc})") from exc


def ask(system, user, args):
    """One anonymous Pollinations request, with the free-slot wait."""
    payload = {
        "model": args.model,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "temperature": args.temperature,
        "seed": args.seed,
        "max_tokens": args.max_tokens,
        "stream": False,
    }
    headers = {"Content-Type": "application/json"}
    token = os.environ.get("POLLINATIONS_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    deadline = time.monotonic() + args.max_wait
    while True:
        req = urllib.request.Request(API, data=json.dumps(payload).encode(),
                                    headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=args.timeout) as resp:
                body = json.loads(resp.read().decode())
            return parse_json(body["choices"][0]["message"]["content"])
        except urllib.error.HTTPError as exc:
            raw = exc.headers.get("Retry-After") if exc.headers else None
            try:
                wait = float(raw) if raw else None
            except ValueError:
                wait = None
            if exc.code in (402, 429) and wait and time.monotonic() + wait < deadline:
                log(f"HTTP {exc.code}; free slot returns in {wait:.0f}s")
                time.sleep(wait + 1)
                continue
            die(f"HTTP {exc.code} from Pollinations (use --max-wait to wait longer)")
        except (urllib.error.URLError, TimeoutError) as exc:
            if time.monotonic() + 5 < deadline:
                log(f"network error ({exc}); retrying")
                time.sleep(5)
                continue
            die(f"cannot reach Pollinations: {exc}")
        except (KeyError, IndexError) as exc:
            raise SoftError(f"unexpected API response: {exc}") from exc


def clean_line(text):
    return " ".join(str(text).split())


def clean_prompt(text):
    """Drop face/eye/gore clauses and guarantee a usable image prompt."""
    parts = [p.strip() for p in clean_line(text).split(",")]
    body = ", ".join(p for p in parts if p and not BANNED_IMAGE.search(p))
    if not body.lower().startswith("cinematic film still"):
        body = "cinematic film still, horror, " + body
    if len(body.split()) < 12:
        body += ", crushed blacks, heavy vignette, 35mm film grain"
    return body


def normalize_cast(written):
    """Human ids (eli, the-echo), never role words, before shots reference them."""
    for raw in written.get("characters", []):
        name = clean_line(raw.get("name") or "Unnamed")
        raw_id = slugify(raw.get("id") or "")
        if raw_id in ("", "protagonist", "antagonist", "character", "none"):
            raw_id = slugify(name) or "character"
        raw["id"] = raw_id
        raw["name"] = name
        raw["role"] = str(raw.get("role") or "supporting").lower()
    return written


def problems_in_monologue(lines):
    if not isinstance(lines, list) or len(lines) != SHOTS:
        return [f"expected {SHOTS} beats, got "
                f"{len(lines) if isinstance(lines, list) else 'none'}"]
    out = []
    for i, line in enumerate(lines, 1):
        text = clean_line(line)
        words = len(text.split())
        if words > 15:
            out.append(f"beat {i}: {words} words (max 15)")
        elif words < 10:
            out.append(f"beat {i}: {words} words (min 10)")
        if TELLING.search(text):
            out.append(f"beat {i}: names an emotion")
        if META.search(text):
            out.append(f"beat {i}: breaks the fiction")
    return out


def write_monologue(topic, args):
    user = (f"Topic: {topic}\nWrite the episode now: one continuous "
            f"{SHOTS}-beat monologue, 10-15 words per beat, four acts, "
            f"JSON only.")
    last = []
    for attempt in range(1, args.retries + 2):
        try:
            data = ask(WRITER_SYSTEM, user, args)
        except SoftError as exc:
            last = [str(exc)]
            log(f"writer attempt {attempt}: {exc}")
            continue
        last = problems_in_monologue(data.get("monologue"))
        chars = data.get("characters")
        if not isinstance(chars, list) or not 2 <= len(chars) <= 3:
            last.append("cast must be 2-3 characters")
        else:
            roles = {str(c.get("role", "")).lower() for c in chars
                     if isinstance(c, dict)}
            if "protagonist" not in roles or "antagonist" not in roles:
                last.append("cast needs one protagonist and one antagonist")
        if last:
            log(f"writer attempt {attempt}: " + "; ".join(last[:5]))
            user += ("\nFix exactly these problems and return the full JSON "
                     "again: " + "; ".join(last[:6]) + ".")
            continue
        data["monologue"] = [clean_line(x) for x in data["monologue"]]
        return data
    die("the writer would not produce a usable monologue: "
        + "; ".join(last[:6]))


def directed_shots(episode, args):
    brief = {
        "title": episode["title"],
        "logline": episode["logline"],
        "characters": episode["characters"],
        "monologue": [{"beat": i, "act": next(a for a, (lo, hi, _) in ACTS.items()
                                              if lo <= i <= hi), "line": line}
                      for i, line in enumerate(episode["monologue"], 1)],
    }
    user = ("Episode:\n" + json.dumps(brief, indent=1)
            + f"\nReturn exactly {SHOTS} shots as JSON.")
    last = []
    for attempt in range(1, args.retries + 2):
        try:
            data = ask(DIRECTOR_SYSTEM, user, args)
        except SoftError as exc:
            last = [str(exc)]
            log(f"director attempt {attempt}: {exc}")
            continue
        shots = data.get("shots")
        if not isinstance(shots, list) or len(shots) != SHOTS:
            last = [f"expected {SHOTS} shots"]
            log(f"director attempt {attempt}: {last[0]}")
            continue
        cast = {slugify(c["id"]): c for c in episode["characters"]}
        antagonist = next((slugify(c["id"]) for c in episode["characters"]
                           if c["role"] == "antagonist"), None)
        protagonist = next((c for c in episode["characters"]
                            if c["role"] == "protagonist"), episode["characters"][0])
        cleaned, last = [], []
        for i, raw in enumerate(shots, 1):
            shot_type = str(raw.get("shot_type", "medium")).lower()
            if shot_type not in SHOT_TYPES:
                log(f"shot {i}: coerced shot_type {shot_type!r} -> medium")
                shot_type = "medium"
            focus = cast.get(slugify(raw.get("focus") or "none"))
            if shot_type in ("insert", "pov"):
                focus = None          # an insert of a person is a different shot
            elif focus is None:
                log(f"shot {i}: unknown focus; using {protagonist['id']}")
                focus = protagonist
            prompt = clean_prompt(raw.get("prompt") or "")
            cleaned.append({
                "act": next(a for a, (lo, hi, _) in ACTS.items() if lo <= i <= hi),
                "title": clean_line(raw.get("title") or f"Beat {i}"),
                "shot_type": shot_type,
                "focus": focus["id"] if focus else "none",
                "prompt": prompt,
            })
        climax_focus = [slugify(s["focus"]) for s in cleaned[6:9]]
        if antagonist and antagonist not in climax_focus:
            # The sighting has to be visible: put the antagonist on the reveal
            # beat rather than discard an otherwise usable board.
            log("director: antagonist missing from the climax; forcing shot 8")
            cleaned[7]["focus"] = cast[antagonist]["id"]
        return cleaned
    die("the director would not assign usable shots: " + "; ".join(last[:6]))


def edit_monologue(written, args):
    """Third pass: continuity, grammar and the twist, wording only."""
    brief = {"title": written["title"], "logline": written["logline"],
             "characters": written["characters"],
             "monologue": written["monologue"]}
    user = ("Episode:\n" + json.dumps(brief, indent=1)
            + f"\nRewrite the {SHOTS} beats as JSON.")
    for attempt in range(1, args.retries + 2):
        try:
            data = ask(EDITOR_SYSTEM, user, args)
        except SoftError as exc:
            log(f"editor attempt {attempt}: {exc}")
            continue
        lines = data.get("monologue")
        problems = problems_in_monologue(lines)
        if problems:
            log(f"editor attempt {attempt}: " + "; ".join(problems[:5]))
            user += ("\nFix exactly these and return all beats: "
                     + "; ".join(problems[:6]) + ".")
            continue
        written["monologue"] = [clean_line(x) for x in lines]
        log("editor: smoothed the narration")
        return written
    log("WARN editor gave no usable rewrite; keeping the draft")
    return written


def build_episode(topic, written, shots):
    chars = []
    for raw in written["characters"]:
        name = clean_line(raw.get("name") or "Unnamed")
        raw_id = slugify(raw.get("id") or "")
        role = str(raw.get("role") or "supporting").lower()
        if raw_id in ("", "protagonist", "antagonist", "character", "none"):
            raw_id = slugify(name) or "character"
        chars.append({"id": raw_id, "name": name, "role": role,
                      "look": clean_line(raw.get("look") or "")})
    by_role = {c["role"]: c for c in chars}
    def humanise(text):
        for role, c in by_role.items():
            text = re.sub(rf"\b{role}\b", c["name"], text, flags=re.I)
        return text
    built = []
    for i, (line, shot) in enumerate(zip(written["monologue"], shots), 1):
        built.append({
            "id": i,
            "slug": slugify(shot["title"]),
            "title": shot["title"],
            "act": shot["act"],
            "shot_type": shot["shot_type"],
            "focus": shot["focus"],
            "foreground": None,
            "prompt": humanise(shot["prompt"]),
            "vo": line,
            "speaker": "narrator",
            "layout": "broll_only",
            "duration_s": 5.0,
            "frames": 5 * FPS,
            "on_camera": False,
        })
    return {
        "episode": written["title"],
        "slug": slugify(written["title"]),
        "format": "horror-teaser",
        "logline": written["logline"],
        "story": " ".join(written["monologue"]),
        "source": {"topic": topic, "model": "pollinations",
                   "director": "kaomei/stickman-video-director (Director Mode)"},
        "characters": chars,
        "base": {"model": "sticks", "width": 1920, "height": 1080,
                 "fps": FPS, "frames": 150},
        "shots": built,
    }


def print_board(episode):
    print(f"\n  {episode['episode']}  ({episode['slug']})")
    print(f"  {episode['logline']}\n")
    print("  CAST")
    for c in episode["characters"]:
        print(f"   {c['id']:<14} {c['role']:<12} {c['name']}: {c['look']}")
    print("\n  STORYBOARD")
    current = None
    for shot in episode["shots"]:
        if shot["act"] != current:
            current = shot["act"]
            lo, hi, name = ACTS[current]
            print(f"\n  ACT {current} · {name}  (shots {lo}-{hi})")
        print(f"   {shot['id']:>2} {shot['shot_type']:<13} {shot['focus']:<12} "
              f"| {shot['title']}")
        print(f"      image: {shot['prompt']}")
        print(f"      vo:    {shot['vo']}")
    print("\n  NARRATION AS ONE MONOLOGUE")
    print("  " + " ".join(s["vo"] for s in episode["shots"]))


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Director Mode: one continuous horror monologue, then a "
                    "12-shot storyboard")
    ap.add_argument("topic")
    ap.add_argument("--out", default=None)
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--seed", type=int, default=3)
    ap.add_argument("--temperature", type=float, default=0.8)
    ap.add_argument("--max-tokens", type=int, default=3000)
    ap.add_argument("--timeout", type=float, default=180.0)
    ap.add_argument("--max-wait", type=float, default=180.0)
    ap.add_argument("--retries", type=int, default=3)
    ap.add_argument("--no-edit", action="store_true",
                    help="skip the editor pass on the monologue")
    ap.add_argument("--resume", action="store_true",
                    help="reuse the monologue checkpoint written next to --out")
    ap.add_argument("--print-only", action="store_true")
    args = ap.parse_args(argv)

    log(f"topic: {args.topic}")
    out = Path(args.out) if args.out else None
    check = out.with_suffix(".written.json") if out else None
    if args.resume and check and check.exists():
        written = json.loads(check.read_text(encoding="utf8"))
        log(f"resumed monologue from {check}")
    else:
        log("stage 1/2: writer (one continuous monologue)")
        written = write_monologue(args.topic, args)
        if check:
            check.write_text(json.dumps(written, indent=2) + "\n", encoding="utf8")
    written = normalize_cast(written)
    if not args.no_edit:
        log("stage 1b: editor (continuity and grammar)")
        written = edit_monologue(written, args)
        if check:
            check.write_text(json.dumps(written, indent=2) + "\n", encoding="utf8")
    log(f"writer: {written['title']!r}, {len(written['monologue'])} beats")
    log("stage 2/2: director (one shot per beat)")
    shots = directed_shots(written, args)
    episode = build_episode(args.topic, written, shots)

    out = out or (ROOT / "episodes" / f"{episode['slug']}.json")
    print_board(episode)
    if args.print_only:
        return 0
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(episode, indent=2) + "\n", encoding="utf8")
    log(f"wrote {out}")
    log(f"next: python3 make_horror_stickman.py --episode {out} --max-seconds 15")
    return 0


if __name__ == "__main__":
    sys.exit(main())
