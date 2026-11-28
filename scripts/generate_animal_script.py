#!/usr/bin/env python3
"""generate_animal_script.py — 4-act narration engine for the animal series.

Topic: "5 Animals With Impossible Superpowers".

Every episode is exactly four acts, in this order, with a word budget that lands
the act on its slot at Kokoro's ~155 wpm delivery:

    THE HOOK        0:00-0:15  30-50 words   impossible question; NO animal yet
    THE REVEAL      0:15-0:25  16-32 words   name the animal as the answer
    THE BREAKDOWN   0:25-0:50  45-80 words   the science + 2-3 hard stats
    THE CLIFFHANGER 0:50-1:00  22-40 words   tease the NEXT animal, unnamed

The acts are validated, not just requested: a hook that names the animal, a
reveal that does not, a missing stat, or a cliffhanger that names the next
animal is a hard error (`--check` only, no writing).

    # see exactly what would be sent to the model
    python3 scripts/generate_animal_script.py --dry-run

    # curated draft (no API key), load animal #1 into the Remotion episode, print it
    python3 scripts/generate_animal_script.py --provider none --apply 1

    # OpenAI / OpenRouter / Groq / Anthropic
    python3 scripts/generate_animal_script.py --provider openai --model gpt-4o-mini --apply 1

Outputs: remotion/public/series.json (all five) and, with `--apply N`,
remotion/public/animal.json + cast.json for the renderer.
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
WORDS_PER_SECOND = 2.55  # measured Kokoro af_heart pace at speed 1.0

# act id -> (label, slot start, slot end, min words, max words, cue key)
ACTS = [
    ("hook", "THE HOOK", 0, 15, 30, 50, "hookAt"),
    ("reveal", "THE REVEAL", 15, 25, 16, 32, "titleAt"),
    ("breakdown", "THE BREAKDOWN", 25, 50, 45, 80, "breakdownAt"),
    ("cliffhanger", "THE CLIFFHANGER", 50, 60, 22, 40, "cliffhangAt"),
]

SYSTEM_PROMPT = """\
You are the head writer for a premium short-form nature documentary channel.
Voice: calm, precise, awe-struck; David Attenborough meets a science desk.

Every script you write is EXACTLY four acts, in order, and the act structure is
not negotiable:

1. THE HOOK (0:00-0:15, 30-50 words). A mind-blowing, impossible-sounding
   question or fact. NEVER name the animal and never say the word "animal" in
   the hook. Open on the phenomenon, not the subject.
2. THE REVEAL (0:15-0:25, 16-32 words). Name the animal as the answer to the
   hook. This is the only act allowed to reveal it.
3. THE BREAKDOWN (0:25-0:50, 45-80 words). The science. Two or three hard,
   verifiable numbers (speed, voltage, temperature, receptor count, lifespan) and
   the mechanism that produces them.
4. THE CLIFFHANGER (0:50-1:00, 22-40 words). Turn to the next creature through
   its habitat or its impossible ability. Do NOT name the next animal.

Hard rules:
- Every claim must be real and defensible. No invented numbers, no myths.
- Write for the ear: short clauses, concrete nouns, no semicolons, no em dashes,
  no "imagine", no "in this video", no call to action.
- Numbers may be written as words ("fifty miles an hour") or digits ("50 mph").
- Never say "superpower" inside a script; the channel title carries that.
"""

USER_PROMPT = """\
Topic: {topic}

Write all five episodes of the series opener. Rank 1 is the mantis shrimp, rank
5 is the immortal jellyfish (finale). Return JSON only, matching this schema:

{{
  "topic": "{topic}",
  "animals": [
    {{
      "rank": 1,
      "animal": "Mantis Shrimp",
      "title": "The Mantis Shrimp",
      "subtitle": "six words, cinematic, present tense, no full stop",
      "species": "Latin binomial",
      "acts": {{
        "hook": "30-50 words, impossible question, animal never named",
        "reveal": "16-32 words, names the animal",
        "breakdown": "45-80 words, science + 2-3 real numbers",
        "cliffhanger": "22-40 words, teases the NEXT animal without naming it"
      }},
      "stats": [
        {{"value": 50, "unit": "MPH", "label": "strike speed underwater"}},
        {{"value": 4400, "unit": "°C", "label": "peak cavitation temperature"}}
      ],
      "cues": {{
        "hookAt": ["first", "words"],
        "titleAt": ["the", "animal", "name"],
        "breakdownAt": ["start", "of", "the", "science"],
        "stat1At": ["phrase", "for", "stat", "one"],
        "stat2At": ["phrase", "for", "stat", "two"],
        "flashAt": ["the", "turn", "phrase"],
        "cliffhangAt": ["but", "the", "next", "tease"]
      }},
      "imagePrompt": "one cinematic documentary still prompt, no text"
    }}
  ]
}}

Cue phrases must be 2-5 words copied verbatim from that animal's own text, and
every act must be present and within its word budget.
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
            "acts": {
                "hook": ("What if I told you a creature in the ocean punches so fast the water boils? One "
                         "strike, and the sea flashes brighter than the surface of the sun. And the culprit is "
                         "smaller than your hand."),
                "reveal": ("Meet the mantis shrimp. Not a shrimp, not a mantis, and far stranger than "
                           "either. It lives on the seafloor, and it is armed."),
                "breakdown": ("It fires its club at fifty miles an hour, faster than a speeding bullet. The "
                              "strike is so violent it vaporises the water in front of it. That vapour bubble "
                              "collapses in a flash of four thousand four hundred degrees Celsius. And its "
                              "eyes carry twelve to sixteen colour receptors. We have three. It sees a world "
                              "we cannot even name."),
                "cliffhanger": ("But the mantis shrimp is just the beginning. Because in the canals of "
                                "Mexico, there is a creature that regrows limbs, its spine, and part of its "
                                "brain."),
            },
            "stats": [
                {"value": 50, "unit": "MPH", "label": "strike speed underwater"},
                {"value": 4400, "unit": "°C", "label": "peak bubble temperature"},
                {"value": 16, "unit": "RECEPTORS", "label": "colour channels in its eyes"},
            ],
            "cues": {
                "hookAt": ["what", "if", "i", "told"],
                "titleAt": ["meet", "the", "mantis"],
                "breakdownAt": ["fires", "its", "club"],
                "stat1At": ["fifty", "miles", "an", "hour"],
                "stat2At": ["four", "thousand", "four", "hundred"],
                "flashAt": ["collapses", "in", "a", "flash"],
                "cliffhangAt": ["but", "the", "mantis", "shrimp", "is", "just"],
            },
            "imagePrompt": ("macro underwater still of a peacock mantis shrimp, iridescent teal and magenta, "
                            "dark volcanic sand, single light shaft, prestige documentary"),
        },
        {
            "rank": 2,
            "animal": "Axolotl",
            "title": "The Axolotl",
            "subtitle": "It grows back pieces of its own brain",
            "species": "Ambystoma mexicanum",
            "acts": {
                "hook": ("What if a body could lose a leg, or a spine, or a piece of its brain, and simply "
                         "grow them back? No scar. No trace. Working parts, rebuilt from nothing at all."),
                "reveal": ("That animal exists. The axolotl, a smiling amphibian that never leaves the canals "
                           "of Mexico City."),
                "breakdown": ("Cut off a limb and it rebuilds muscle, bone, nerve and blood vessels in three "
                              "weeks. Sever its spinal cord and within eight weeks the cord reconnects. Remove "
                              "part of its heart and the heart returns. Its secret is that it never truly grows "
                              "up. Its cells stay young, and young cells still remember how to build a body. We "
                              "keep a scar. The axolotl keeps a blueprint."),
                "cliffhanger": ("But regrowing a limb is nothing. Because on the highest, driest ground on "
                                "Earth, there is a creature that survives being boiled, frozen, and left in the "
                                "vacuum of space."),
            },
            "stats": [
                {"value": 100, "unit": "%", "label": "of a lost limb rebuilt"},
                {"value": 3, "unit": "ORGANS", "label": "regrown including the heart"},
                {"value": 1, "unit": "SPECIES", "label": "left in the wild habitat"},
            ],
            "cues": {
                "hookAt": ["what", "if", "a", "body"],
                "titleAt": ["that", "animal", "exists"],
                "breakdownAt": ["cut", "off", "a", "limb"],
                "stat1At": ["rebuilds", "muscle", "bone"],
                "stat2At": ["remove", "part", "of", "its", "heart"],
                "flashAt": ["young", "cells", "still", "remember"],
                "cliffhangAt": ["but", "regrowing", "a", "limb", "is", "nothing"],
            },
            "imagePrompt": ("cinematic still of a pink axolotl in dark water, feathery gills backlit, "
                            "black-green aquatic plants, shallow depth of field"),
        },
        {
            "rank": 3,
            "animal": "Tardigrade",
            "title": "The Tardigrade",
            "subtitle": "It survives the vacuum of space",
            "species": "Milnesium tardigradum",
            "acts": {
                "hook": ("What if something no bigger than a grain of salt could be boiled, frozen, dried to "
                         "dust and fired into space, and still walk away? Not a rumour, and not a myth."),
                "reveal": ("It is the tardigrade. The water bear. Eight legs, a see-through body, and almost "
                           "nothing that can kill it."),
                "breakdown": ("Strip away its water and it does not die. It curls into a tun, a glassy ball "
                              "with no measurable metabolism at all. In that state it survives six thousand "
                              "atmospheres of pressure, radiation that would shred human DNA, and decades "
                              "without a drop of water. Add water, and it unfolds and walks away. It has already "
                              "outlived five mass extinctions."),
                "cliffhanger": ("But surviving is not the strangest trick. Because in the rivers of South "
                                "America, there is a fish that hunts by taking control of another animal's "
                                "nerves."),
            },
            "stats": [
                {"value": 6000, "unit": "ATM", "label": "pressure survived"},
                {"value": 30, "unit": "YEARS", "label": "dry, without water"},
                {"value": 5, "unit": "EXTINCTIONS", "label": "already outlived"},
            ],
            "cues": {
                "hookAt": ["what", "if", "something", "no"],
                "titleAt": ["it", "is", "the", "tardigrade"],
                "breakdownAt": ["strip", "away", "its", "water"],
                "stat1At": ["six", "thousand", "atmospheres"],
                "stat2At": ["decades", "without", "a", "drop"],
                "flashAt": ["add", "water"],
                "cliffhangAt": ["but", "surviving", "is", "not"],
            },
            "imagePrompt": ("extreme macro of a tardigrade, translucent segmented body and claws, crystalline "
                            "ice field, cool blue rim light, documentary microscopy aesthetic"),
        },
        {
            "rank": 4,
            "animal": "Electric Eel",
            "title": "The Electric Eel",
            "subtitle": "It hunts with eight hundred volts",
            "species": "Electrophorus voltai",
            "acts": {
                "hook": ("What if a fish could reach into your nerves and switch them on from across the water? "
                         "No teeth. No venom. Just raw current, aimed with surgical precision into a body it "
                         "cannot even see."),
                "reveal": ("The electric eel. Nearly three metres of muscle, mud and voltage, hunting in the "
                           "dark rivers of the Amazon."),
                "breakdown": ("Three separate organs stack thousands of cells the way a battery stacks plates. "
                              "The discharge peaks at eight hundred and sixty volts. But the voltage is not the "
                              "trick. It fires weak pulses first and reads the twitch of a hidden fish's "
                              "muscles. Then it sends a full burst that forces those muscles to fire and gives "
                              "the prey away. It does not only shock. It takes control."),
                "cliffhanger": ("But every animal so far can still die. Because somewhere in the Mediterranean, "
                                "there is a creature that has found a way to skip death entirely."),
            },
            "stats": [
                {"value": 860, "unit": "VOLTS", "label": "peak discharge"},
                {"value": 3, "unit": "ORGANS", "label": "stacked like batteries"},
                {"value": 3, "unit": "METRES", "label": "nose to tail"},
            ],
            "cues": {
                "hookAt": ["what", "if", "a", "fish"],
                "titleAt": ["the", "electric", "eel"],
                "breakdownAt": ["three", "separate", "organs"],
                "stat1At": ["eight", "hundred", "and", "sixty"],
                "stat2At": ["fires", "weak", "pulses"],
                "flashAt": ["it", "does", "not", "only", "shock"],
                "cliffhangAt": ["but", "every", "animal", "so", "far"],
            },
            "imagePrompt": ("cinematic underwater still of a large electric eel in murky dark river water, "
                            "bioelectric shimmer along its flank, single torch beam"),
        },
        {
            "rank": 5,
            "animal": "Immortal Jellyfish",
            "title": "The Immortal Jellyfish",
            "subtitle": "It ages backwards to escape death",
            "species": "Turritopsis dohrnii",
            "finale": True,
            "acts": {
                "hook": ("What if death was optional? What if growing old was something a living body could "
                         "simply decide to undo, the way you undo a sentence you did not mean to write, again "
                         "and again, without end?"),
                "reveal": ("Turritopsis dohrnii. The immortal jellyfish. Smaller than your fingernail, and the "
                           "only animal known to reverse its own life."),
                "breakdown": ("Wounded or starving, it does not die. Its adult body dissolves back into a "
                              "juvenile polyp, a ball of tissue that begins again. Then it grows, matures, and "
                              "repeats the loop. It is not invulnerable. A fish can still eat it. But at three "
                              "millimetres across, it has no fixed lifespan, and after one hundred years of "
                              "study we still do not know its limit."),
                "cliffhanger": ("Five animals. Five impossible powers. And the ocean is still full of "
                                "creatures we have never once seen. The next one is already down there, "
                                "waiting."),
            },
            "stats": [
                {"value": 0, "unit": "LIMIT", "label": "known natural lifespan"},
                {"value": 3, "unit": "MM", "label": "across the bell"},
                {"value": 5, "unit": "ANIMALS", "label": "in this series"},
            ],
            "cues": {
                "hookAt": ["what", "if", "death", "was"],
                "titleAt": ["turritopsis", "dohrnii"],
                "breakdownAt": ["wounded", "or", "starving"],
                "stat1At": ["dissolves", "back", "into", "a", "juvenile"],
                "stat2At": ["no", "fixed", "lifespan"],
                "flashAt": ["then", "it", "grows"],
                "cliffhangAt": ["five", "animals"],
            },
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


def tokens(text: str) -> list[str]:
    return re.sub(r"[^a-z0-9 ]", " ", text.lower()).split()


def script_of(animal: dict) -> str:
    """The spoken script: the four acts in order, joined."""
    return " ".join(animal["acts"][a[0]].strip() for a in ACTS if animal["acts"].get(a[0]))


def estimate(animal: dict) -> dict[str, float]:
    """Rough per-act timings at the measured kokoro pace (voiceover refines them)."""
    stats: dict[str, float] = {}
    clock = 0.0
    for act, *_rest in ACTS:
        words = len(animal["acts"][act].split())
        secs = words / WORDS_PER_SECOND
        stats[act] = round(clock, 2)
        clock += secs
    stats["total"] = round(clock, 2)
    return stats


# --------------------------------------------------------------------------- #
# validation
# --------------------------------------------------------------------------- #
def validate_acts(animal: dict, next_animal: dict | None) -> None:
    name = animal["animal"]
    name_tokens = set(tokens(name))
    acts = animal.get("acts") or {}
    where = f"#{animal['rank']} {name}"

    for act, label, start, end, lo, hi, _cue in ACTS:
        text = (acts.get(act) or "").strip()
        if not text:
            die(f"{where}: act {act!r} is missing")
        words = len(text.split())
        if not lo <= words <= hi:
            die(f"{where}: {label} is {words} words, must be {lo}-{hi}")
        est = words / WORDS_PER_SECOND
        if est > (end - start) + 2.5:
            die(f"{where}: {label} runs ~{est:.1f}s, over its {end - start}s slot")

    hook = acts["hook"]
    if hook.count("?") == 0:
        die(f"{where}: THE HOOK must ask a question (it has no '?')")
    leaked = name_tokens & set(tokens(hook))
    if leaked:
        die(f"{where}: THE HOOK names the animal ({', '.join(sorted(leaked))}) — it must not")
    if "animal" in tokens(hook) and "animals" not in tokens(hook):
        die(f"{where}: THE HOOK must not say 'animal' — open on the phenomenon")

    if not name_tokens & set(tokens(acts["reveal"])):
        die(f"{where}: THE REVEAL must name the animal ({name})")

    stats = animal.get("stats") or []
    if not 2 <= len(stats) <= 3:
        die(f"{where}: needs 2-3 stats, has {len(stats)}")
    numbers = re.findall(r"\b\d+\b", script_of(animal)) + [
        w for w in tokens(script_of(animal))
        if w in {"one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
                 "twenty", "thirty", "forty", "fifty", "sixty", "hundred", "thousand"}
    ]
    if len(numbers) < 2:
        die(f"{where}: THE BREAKDOWN needs at least two real numbers")
    for s in stats:
        if not str(s.get("unit", "")).strip() or not str(s.get("label", "")).strip():
            die(f"{where}: every stat needs a unit and a label")

    cliff = acts["cliffhanger"]
    if animal.get("finale"):
        if next_animal is not None:
            die(f"{where}: marked finale but another animal follows it")
    else:
        if next_animal is None:
            die(f"{where}: not marked finale, so a next animal must exist to tease")
        if set(tokens(acts["cliffhanger"])) & set(tokens(next_animal["animal"])):
            die(f"{where}: THE CLIFFHANGER names the next animal — tease it, do not spoil it")
        if not re.search(r"\b(but|because|yet|still|until|nothing)\b", cliff.lower()):
            die(f"{where}: THE CLIFFHANGER needs a turn ('But...', 'Because...')")

    spoken = tokens(script_of(animal))
    for cue, phrase in (animal.get("cues") or {}).items():
        want = tokens(" ".join(phrase)) if isinstance(phrase, list) else tokens(str(phrase))
        if not want:
            die(f"{where}: cue {cue!r} is empty")
        if not any(spoken[i:i + len(want)] == want for i in range(len(spoken))):
            die(f"{where}: cue {cue!r} ({' '.join(want)!r}) is not in the script")

    total = len(script_of(animal).split())
    if not 113 <= total <= 202:
        die(f"{where}: script totals {total} words, expected 113-202 for a 60s slot")


def validate(doc: dict) -> dict:
    animals = doc.get("animals") or []
    if len(animals) != 5:
        die(f"expected 5 animals, got {len(animals)}")
    required = {"rank", "animal", "title", "subtitle", "species", "acts", "stats"}
    for a in animals:
        missing = required - set(a)
        if missing:
            die(f"animal {a.get('animal')!r} is missing {sorted(missing)}")
    animals.sort(key=lambda a: a["rank"])
    for i, a in enumerate(animals):
        validate_acts(a, animals[i + 1] if i + 1 < len(animals) else None)
        a["script"] = script_of(a)
        a["estimatedSeconds"] = estimate(a)["total"]
        a.setdefault("duration", round(a["estimatedSeconds"], 1))
        a.setdefault("imagePrompt", f"cinematic documentary still of a {a['animal'].lower()}")
        a.setdefault("cues", {"hookAt": tokens(a["acts"]["hook"])[:3],
                              "titleAt": tokens(a["acts"]["reveal"])[:3],
                              "breakdownAt": tokens(a["acts"]["breakdown"])[:3],
                              "cliffhangAt": tokens(a["acts"]["cliffhanger"])[:3]})
    doc["topic"] = TOPIC
    return doc


# --------------------------------------------------------------------------- #
# providers
# --------------------------------------------------------------------------- #
def chat_openai_compatible(url: str, key: str, model: str) -> str:
    body = json.dumps({
        "model": model,
        "temperature": 0.85,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT.format(topic=TOPIC)},
        ],
    }).encode()
    req = urllib.request.Request(url, data=body, headers={
        "Content-Type": "application/json", "Authorization": f"Bearer {key}",
    })
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.load(resp)
    return data["choices"][0]["message"]["content"]


def chat_anthropic(key: str, model: str) -> str:
    body = json.dumps({
        "model": model,
        "max_tokens": 8192,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": USER_PROMPT.format(topic=TOPIC)}],
    }).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body, headers={
        "content-type": "application/json", "x-api-key": key,
        "anthropic-version": "2023-06-01",
    })
    with urllib.request.urlopen(req, timeout=180) as resp:
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


# --------------------------------------------------------------------------- #
# output
# --------------------------------------------------------------------------- #
def mmss(sec: float) -> str:
    return f"{int(sec) // 60}:{int(sec) % 60:02d}"


def print_script(doc: dict, rank: int) -> None:
    animal = next((a for a in doc["animals"] if a["rank"] == rank), None)
    if animal is None:
        die(f"no animal ranked {rank}")
    est = estimate(animal)
    total = est["total"]
    bar = "=" * 74
    print(f"\n{bar}\n  {animal['title'].upper()}  ·  {animal['species']}\n"
          f"  {animal['subtitle']}\n  {len(script_of(animal).split())} words  ·  "
          f"~{total:.0f}s at {WORDS_PER_SECOND} wps  ·  act structure lock\n{bar}")
    for act, label, start, end, lo, hi, cue in ACTS:
        text = animal["acts"][act]
        words = len(text.split())
        cue_phrases = animal["cues"].get(cue)
        print(f"\n{label}   {mmss(est[act])}–{mmss(est[act] + words / WORDS_PER_SECOND)} "
              f"(slot {mmss(start)}–{mmss(end)}, {words} words)")
        print(f"  {text}")
        if cue_phrases:
            print(f"  cue: \"{' '.join(cue_phrases)}\"")
        if act == "breakdown":
            for i, s in enumerate(animal["stats"], 1):
                print(f"  stat {i}: {s['value']} {s['unit']} — {s['label']}")
    print(f"\n{bar}")
    for key, value in animal["cues"].items():
        shown = f'"{" ".join(value)}"' if isinstance(value, list) else value
        print(f"  cue {key:14s} {shown}")
    print(bar + "\n")


def apply_to_episode(series: dict, rank: int, episode_path: Path) -> dict:
    animal = next((a for a in series["animals"] if a["rank"] == rank), None)
    if animal is None:
        die(f"no animal ranked {rank}")
    slug = re.sub(r"[^a-z0-9]+", "-", animal["animal"].lower()).strip("-")
    episode = json.loads(episode_path.read_text()) if episode_path.exists() else {}
    episode.update({
        "series": "IMPOSSIBLE SUPERPOWERS",
        "episode": animal["rank"],
        "total": len(series["animals"]),
        "title": animal["title"],
        "titleWords": animal["title"].split(),
        "subtitle": animal["subtitle"],
        "species": animal["species"],
        "script": animal["script"],
        "acts": animal["acts"],
        "stats": animal["stats"],
        "stat": animal["stats"][0],
        "cues": animal["cues"],
        "image": f"animals/{slug}.jpg",
        "audio": f"vo_{slug}.mp3",
        # the length now belongs to the 60s script; generate_voiceover.py
        # replaces it with the measured take and rewrites `timeline`
        "duration": round(animal["estimatedSeconds"], 1),
        "timeline": {k: 0 for k in animal["cues"]},
    })
    episode_path.write_text(json.dumps(episode, indent=2, ensure_ascii=False) + "\n")
    log(f"loaded animal #{rank} ({animal['title']}) into {episode_path.name}")

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
    log("script changed — run generate_voiceover.py to time the visuals (~60s take)")
    return episode


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=f"4-act script generator — {TOPIC}")
    p.add_argument("--provider", default="auto", choices=["auto", "none", *PROVIDERS.keys()])
    p.add_argument("--model", default="")
    p.add_argument("--out", default=str(SERIES_OUT))
    p.add_argument("--apply", type=int, default=0,
                   help="merge this rank into remotion/public/animal.json")
    p.add_argument("--print", dest="do_print", action="store_true", default=True,
                   help="print the formatted 4-act script (default)")
    p.add_argument("--no-print", dest="do_print", action="store_false")
    p.add_argument("--dry-run", action="store_true", help="print the prompt and exit")
    args = p.parse_args(argv)

    if args.dry_run:
        print("=== SYSTEM ===\n" + SYSTEM_PROMPT)
        print("=== USER ===\n" + USER_PROMPT.format(topic=TOPIC))
        return 0

    provider = pick_provider(args.provider)
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
                chat_openai_compatible(url, key, model)
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
            f"~{a['estimatedSeconds']:.0f}s  {len(a['stats'])} stats")

    if args.apply:
        apply_to_episode(doc, args.apply, EPISODE)
    if args.do_print:
        print_script(doc, args.apply or 1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
