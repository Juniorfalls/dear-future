#!/usr/bin/env python3
"""generate_animal_script.py — write a narration script for the animal series.

Topic: "5 Animals With Impossible Superpowers".

The generator asks an LLM for a strict JSON payload (five animals, each with a
short narration script, a cinematic title, one headline statistic, the cue
phrases the visuals sync to, and an image prompt for the episode still). If no
API key is configured — or `--provider none` — it falls back to the curated
editorial draft below, so the pipeline still produces a renderable episode.

    # see exactly what would be sent to the model
    python3 scripts/generate_animal_script.py --dry-run

    # OpenAI (needs OPENAI_API_KEY); also openrouter / groq / anthropic
    python3 scripts/generate_animal_script.py --provider openai --model gpt-4o-mini

    # offline curated draft, then load animal #1 into the Remotion episode
    python3 scripts/generate_animal_script.py --provider none --apply 1

Output: remotion/public/series.json (all five), and with `--apply N` the chosen
animal is merged into remotion/public/animal.json for the renderer.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "remotion" / "public"
SERIES_OUT = PUBLIC / "series.json"
EPISODE = PUBLIC / "animal.json"

TOPIC = "5 Animals With Impossible Superpowers"

SYSTEM_PROMPT = """\
You are the head writer for a premium short-form nature documentary channel.
Voice: calm, precise, awe-struck; David Attenborough meets a science desk.
Rules:
- Every claim must be real and defensible. No invented numbers, no myths.
- One animal per segment; 35-45 spoken words, 4 sentences maximum.
- Open with the animal's name alone as a one-word fragment, then the impossible
  fact, then the mechanism, then a turn back to the viewer.
- Write for the ear: short clauses, concrete nouns, no semicolons, no em dashes,
  no "imagine", no "in this video", no call to action.
- Never say "superpower" inside a segment; the channel title carries that.
"""

USER_PROMPT = """\
Topic: {topic}

Write the five segments for the series opener. Order them weakest to strongest
hook, ranked 1 (first, the mantis shrimp) to 5 (the finale, the immortal
jellyfish). Return JSON only, matching this schema exactly:

{{
  "topic": "{topic}",
  "animals": [
    {{
      "rank": 1,
      "animal": "Mantis Shrimp",
      "title": "The Mantis Shrimp",
      "subtitle": "six words, cinematic, present tense, no full stop",
      "species": "Latin binomial",
      "script": "35-45 words of narration, sentences separated by full stops",
      "stat": {{"value": 50, "unit": "MPH", "label": "what the number measures", "caption": "one short cinematic line"}},
      "cues": {{
        "titleAt": ["first", "two", "words"],
        "subtitleAt": ["phrase", "spoken", "here"],
        "statAt": ["phrase", "for", "the", "number"],
        "flashAt": ["the", "turn", "phrase"],
        "outroAt": ["closing", "words"]
      }},
      "imagePrompt": "one cinematic documentary still prompt for this animal, no text"
    }}
  ]
}}

Cues must be 2-5 word phrases copied verbatim from that animal's own script.
"""

# --------------------------------------------------------------------------- #
# Curated draft — the offline fallback and the quality bar for the LLM.
# --------------------------------------------------------------------------- #
CURATED = {
    "topic": TOPIC,
    "animals": [
        {
            "rank": 1,
            "animal": "Mantis Shrimp",
            "title": "The Mantis Shrimp",
            "subtitle": "It punches fast enough to boil the sea",
            "species": "Odontodactylus scyllarus",
            "script": ("Mantis shrimp. Fifty miles an hour, underwater. Fast enough to boil the water it "
                       "swims in. Every punch fires a bubble that collapses in a flash of light, hotter "
                       "than the surface of the sun. Animal one: impossible superpowers."),
            "stat": {"value": 50, "unit": "MPH", "label": "strike speed underwater",
                     "caption": "The fastest punch in the ocean"},
            "cues": {"titleAt": ["mantis", "shrimp"], "subtitleAt": ["fifty", "miles", "an", "hour"],
                     "statAt": ["fifty", "miles", "an", "hour"], "flashAt": ["flash", "of", "light"],
                     "outroAt": ["animal", "one"]},
            "imagePrompt": ("macro underwater still of a peacock mantis shrimp, iridescent teal and magenta, "
                            "dark volcanic sand, single light shaft, prestige documentary"),
        },
        {
            "rank": 2,
            "animal": "Axolotl",
            "title": "The Axolotl",
            "subtitle": "It grows back pieces of its own brain",
            "species": "Ambystoma mexicanum",
            "script": ("Axolotl. Lose a limb and it grows back whole. Muscle, bone, nerves, even part of the "
                       "spinal cord. Regeneration runs on cells that never finish growing up. It stays a "
                       "child its entire life. Animal two."),
            "stat": {"value": 100, "unit": "%", "label": "of a lost limb regrown",
                     "caption": "A body that rebuilds itself"},
            "cues": {"titleAt": ["axolotl"], "subtitleAt": ["lose", "a", "limb"],
                     "statAt": ["grows", "back", "whole"], "flashAt": ["spinal", "cord"],
                     "outroAt": ["animal", "two"]},
            "imagePrompt": ("cinematic still of a pink axolotl in dark water, feathery gills backlit, "
                            "black-green aquatic plants, shallow depth of field"),
        },
        {
            "rank": 3,
            "animal": "Tardigrade",
            "title": "The Tardigrade",
            "subtitle": "It survives the vacuum of space",
            "species": "Milnesium tardigradum",
            "script": ("Tardigrade. Half a millimetre long, and it survives space. Vacuum, radiation, boiling "
                       "water, decades of drought. It drains itself into a glass-like state and stops. When "
                       "water returns, it walks again. Animal three."),
            "stat": {"value": 6, "unit": "K ATM", "label": "pressure survived",
                     "caption": "The animal that cannot be killed"},
            "cues": {"titleAt": ["tardigrade"], "subtitleAt": ["survives", "space"],
                     "statAt": ["half", "a", "millimetre"], "flashAt": ["glass", "like", "state"],
                     "outroAt": ["animal", "three"]},
            "imagePrompt": ("extreme macro of a tardigrade, translucent segmented body and claws, crystalline "
                            "ice field, cool blue rim light, documentary microscopy aesthetic"),
        },
        {
            "rank": 4,
            "animal": "Electric Eel",
            "title": "The Electric Eel",
            "subtitle": "It hunts with eight hundred volts",
            "species": "Electrophorus voltai",
            "script": ("Electric eel. Eight hundred and sixty volts, fired into the water. Three organs stack "
                       "cells like batteries. It can remote control the muscles of a hiding fish, forcing it "
                       "to twitch and give itself away. Animal four."),
            "stat": {"value": 860, "unit": "VOLTS", "label": "peak discharge",
                     "caption": "A lightning storm with a spine"},
            "cues": {"titleAt": ["electric", "eel"], "subtitleAt": ["eight", "hundred"],
                     "statAt": ["eight", "hundred", "and", "sixty"], "flashAt": ["remote", "control"],
                     "outroAt": ["animal", "four"]},
            "imagePrompt": ("cinematic underwater still of a large electric eel in murky dark river water, "
                            "bioelectric shimmer along its flank, single torch beam"),
        },
        {
            "rank": 5,
            "animal": "Immortal Jellyfish",
            "title": "The Immortal Jellyfish",
            "subtitle": "It ages backwards to escape death",
            "species": "Turritopsis dohrnii",
            "script": ("Immortal jellyfish. Wounded or starving, it reverses its own life. The adult body "
                       "melts back into a juvenile polyp and starts again. It can loop forever. The only "
                       "animal that never has to grow old. Animal five."),
            "stat": {"value": 0, "unit": "LIMIT", "label": "known natural lifespan",
                     "caption": "The creature that refuses to end"},
            "cues": {"titleAt": ["immortal", "jellyfish"], "subtitleAt": ["reverses", "its", "own", "life"],
                     "statAt": ["wounded", "or", "starving"], "flashAt": ["juvenile", "polyp"],
                     "outroAt": ["animal", "five"]},
            "imagePrompt": ("cinematic macro of a translucent Turritopsis jellyfish glowing in black water, "
                            "trailing tentacles, deep red bell, single soft light from below"),
        },
    ],
}


def log(msg: str) -> None:
    print(f"[script] {msg}", flush=True)


def die(msg: str, code: int = 1) -> None:
    print(f"[script] ERROR: {msg}", file=sys.stderr, flush=True)
    sys.exit(code)


# --------------------------------------------------------------------------- #
# providers
# --------------------------------------------------------------------------- #
def chat_openai_compatible(url: str, key: str, model: str, payload: dict) -> str:
    body = json.dumps({
        "model": model,
        "temperature": 0.8,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT.format(topic=TOPIC)},
        ],
        **payload,
    }).encode()
    req = urllib.request.Request(url, data=body, headers={
        "Content-Type": "application/json", "Authorization": f"Bearer {key}",
    })
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.load(resp)
    return data["choices"][0]["message"]["content"]


def chat_anthropic(key: str, model: str) -> str:
    body = json.dumps({
        "model": model,
        "max_tokens": 4096,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": USER_PROMPT.format(topic=TOPIC)}],
    }).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body, headers={
        "content-type": "application/json", "x-api-key": key,
        "anthropic-version": "2023-06-01",
    })
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.load(resp)
    return data["content"][0]["text"]


PROVIDERS = {
    "openai": ("OPENAI_API_KEY", "https://api.openai.com/v1/chat/completions", "gpt-4o-mini"),
    "openrouter": ("OPENROUTER_API_KEY", "https://openrouter.ai/api/v1/chat/completions",
                   "anthropic/claude-3.5-sonnet"),
    "groq": ("GROQ_API_KEY", "https://api.groq.com/openai/v1/chat/completions",
             "llama-3.3-70b-versatile"),
    "anthropic": ("ANTHROPIC_API_KEY", "", "claude-3-5-sonnet-latest"),
}


def pick_provider(requested: str) -> str:
    if requested != "auto":
        return requested
    for name, (env, _, _) in PROVIDERS.items():
        if os.environ.get(env):
            return name
    return "none"


def extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-z]*\n|```$", "", text).strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < 0:
        die("model reply contained no JSON object")
    return json.loads(text[start:end + 1])


def validate(doc: dict) -> dict:
    animals = doc.get("animals") or []
    if len(animals) != 5:
        die(f"expected 5 animals, got {len(animals)}")
    required = {"rank", "animal", "title", "subtitle", "species", "script", "stat", "cues"}
    for a in animals:
        missing = required - set(a)
        if missing:
            die(f"animal {a.get('animal')!r} is missing {sorted(missing)}")
        words = len(a["script"].split())
        if not 25 <= words <= 60:
            die(f"{a['animal']}: script is {words} words, expected 25-60")
        for cue, phrase in a["cues"].items():
            joined = re.sub(r"[^a-z0-9 ]", " ", " ".join(phrase).lower()).split()
            spoken = re.sub(r"[^a-z0-9 ]", " ", a["script"].lower()).split()
            if not any(spoken[i:i + len(joined)] == joined for i in range(len(spoken))):
                die(f"{a['animal']}: cue {cue!r} ({' '.join(joined)!r}) is not in the script")
    for a in animals:
        a.setdefault("duration", 15)
        a.setdefault("imagePrompt", f"cinematic documentary still of a {a['animal'].lower()}")
    doc["topic"] = TOPIC
    doc["animals"].sort(key=lambda a: a["rank"])
    return doc


# --------------------------------------------------------------------------- #
def apply_to_episode(series: dict, rank: int, episode_path: Path) -> dict:
    animal = next((a for a in series["animals"] if a["rank"] == rank), None)
    if animal is None:
        die(f"no animal ranked {rank}")
    episode = json.loads(episode_path.read_text()) if episode_path.exists() else {}
    slug = re.sub(r"[^a-z0-9]+", "-", animal["animal"].lower()).strip("-")
    episode.update({
        "series": "IMPOSSIBLE SUPERPOWERS",
        "episode": animal["rank"],
        "total": len(series["animals"]),
        "title": animal["title"],
        "titleWords": animal["title"].split(),
        "subtitle": animal["subtitle"],
        "species": animal["species"],
        "script": animal["script"],
        "stat": animal["stat"],
        "cues": animal["cues"],
        # per-animal assets: the still and the take are named after the animal
        "image": f"animals/{slug}.jpg",
        "audio": f"vo_{slug}.mp3",
        # Keep the measured length: generate_voiceover.py is authoritative and
        # will rewrite this, plus `timeline`, on the next narration run.
        "duration": max(float(episode.get("duration", 15)), 15.0),
        "timeline": episode.get("timeline", {}),
    })
    episode_path.write_text(json.dumps(episode, indent=2, ensure_ascii=False) + "\n")
    log(f"loaded animal #{rank} ({animal['title']}) into {episode_path.name}")
    log("script changed — re-run generate_voiceover.py to re-time the visuals")

    # the cast list feeds the intro/outro cards in remotion/src/SeriesCard.tsx
    cast = [
        {
            "rank": a["rank"],
            "title": a["title"],
            "subtitle": a["subtitle"],
            "species": a["species"],
            "image": f"animals/{re.sub(r'[^a-z0-9]+', '-', a['animal'].lower()).strip('-')}.jpg",
        }
        for a in series["animals"]
    ]
    (episode_path.parent / "cast.json").write_text(json.dumps(cast, indent=2) + "\n")
    log(f"wrote cast.json ({len(cast)} animals)")
    return episode


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=f"script generator — {TOPIC}")
    p.add_argument("--provider", default="auto",
                   choices=["auto", "none", *PROVIDERS.keys()])
    p.add_argument("--model", default="")
    p.add_argument("--out", default=str(SERIES_OUT))
    p.add_argument("--apply", type=int, default=0,
                   help="merge this rank into remotion/public/animal.json")
    p.add_argument("--dry-run", action="store_true", help="print the prompt and exit")
    args = p.parse_args(argv)

    if args.dry_run:
        print("=== SYSTEM ===\n" + SYSTEM_PROMPT)
        print("=== USER ===\n" + USER_PROMPT.format(topic=TOPIC))
        return 0

    provider = pick_provider(args.provider)
    doc = None
    if provider == "none":
        log("no API key found — using the curated editorial draft")
        doc = json.loads(json.dumps(CURATED))
        doc["generatedBy"] = "curated"
    else:
        env, url, default_model = PROVIDERS[provider]
        key = os.environ.get(env, "")
        if not key:
            die(f"{provider} selected but {env} is not set")
        model = args.model or default_model
        log(f"{provider} / {model} ...")
        try:
            reply = chat_anthropic(key, model) if provider == "anthropic" else \
                chat_openai_compatible(url, key, model, {})
            doc = extract_json(reply)
            doc["generatedBy"] = f"{provider}:{model}"
        except (urllib.error.URLError, urllib.error.HTTPError, KeyError, json.JSONDecodeError) as exc:
            log(f"model call failed ({exc.__class__.__name__}: {exc}) — using the curated draft")
            doc = json.loads(json.dumps(CURATED))
            doc["generatedBy"] = "curated"

    doc = validate(doc)
    doc["generatedAt"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    log(f"wrote {out} ({doc['generatedBy']})")
    for a in doc["animals"]:
        log(f"  #{a['rank']} {a['title']:24s} {len(a['script'].split()):3d} words  "
            f"{a['stat']['value']}{a['stat']['unit']}")

    if args.apply:
        apply_to_episode(doc, args.apply, EPISODE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
