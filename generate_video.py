#!/usr/bin/env python3
"""Turn a topic into remotion/data/scenes.json.

    python generate_video.py "The Fall of Rome"
    python generate_video.py "The History of Rome" --scene-seconds 5 --count 5
    python generate_video.py "Ancient Egypt" --beats my_lines.json --no-verify

Stills come from a free placeholder service today. `image_urls()` is the single
 place to swap in a real AI image generator later (DALL-E, Stable Diffusion,
 a hosted endpoint): it only has to return one image URL per scene.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent
DEFAULT_OUT = ROOT / "remotion" / "data" / "scenes.json"

# --------------------------------------------------------------------------- #
# Where the pictures come from
# --------------------------------------------------------------------------- #
# PLACEHOLDER PROVIDER. `picsum.photos` returns a deterministic photo per seed,
# so re-running the same topic keeps the same stills (important for CI diffs).
# TODO(images): replace this with the AI image API, e.g.
#   POST https://api.12thstreet.tv/generate  {"prompt": "<scene prompt>", ...}
# and return the resulting CDN URL. Nothing downstream has to change.
PLACEHOLDER_URL = "https://picsum.photos/seed/{seed}/{width}/{height}"

# Visual prompts handed to the future image generator, one per chapter. They are
# also what the placeholder seeds are derived from, so the pairing stays stable.
IMAGE_PROMPTS = [
    "ancient city at dawn, monumental stone architecture, golden mist, cinematic",
    "aerial view of a vast empire's capital, temples and roads, epic scale",
    "cracked marble column in a dust storm, long shadows, ominous sky",
    "ruined walls at dusk, embers and drifting smoke, desaturated",
    "artifacts in museum light, broken statue, dust motes, quiet",
]

CHAPTERS = [
    "Chapter One — The Beginning",
    "Chapter Two — The Height",
    "Chapter Three — The Turn",
    "Chapter Four — The Unravelling",
    "Chapter Five — What Remains",
]

# Dramatic narration beats. Only the first and last name the topic, so the middle
# reads naturally for any subject; pass --beats to supply LLM-written lines.
BEATS = [
    "{topic}. It began like any other story — with ambition, and with time.",
    "At its height, its reach was measured not in miles, but in months of travel.",
    "Then the borders thinned, and the cost of holding them rose year after year.",
    "The end did not arrive in a single day. It arrived in a hundred small surrenders.",
    "What survives of {topic} is stone, dust, and a warning we are still learning to read.",
]


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "topic"


def image_urls(topic: str, count: int, width: int, height: int) -> list[str]:
    """One still per scene. Swap this function for the AI image API later."""
    base = slug(topic)
    urls = []
    for index in range(count):
        prompt = IMAGE_PROMPTS[index % len(IMAGE_PROMPTS)]
        seed = f"{base}-{index + 1}-{slug(prompt)[:24]}"
        urls.append(PLACEHOLDER_URL.format(seed=quote(seed), width=width, height=height))
    return urls


def captions(topic: str, count: int, beats_file: Path | None) -> list[str]:
    if beats_file:
        data = json.loads(beats_file.read_text())
        lines = data["beats"] if isinstance(data, dict) else data
        if not isinstance(lines, list) or not lines:
            raise SystemExit(f"{beats_file}: expected a non-empty list of beats")
        lines = [str(line) for line in lines]
    else:
        lines = BEATS

    out = []
    for index in range(count):
        template = lines[min(index, len(lines) - 1)]
        out.append(template.format(topic=topic) if "{topic}" in template else template)
    return out


def build(topic: str, count: int, scene_seconds: float, width: int, height: int,
          beats_file: Path | None) -> dict:
    urls = image_urls(topic, count, width, height)
    lines = captions(topic, count, beats_file)
    chapters = [CHAPTERS[i % len(CHAPTERS)] for i in range(count)]

    return {
        "_notes": {
            "generated_by": "generate_video.py",
            "topic": topic,
            "image_source": (
                "PLACEHOLDER IMAGES from picsum.photos. Replace image_urls() in "
                "generate_video.py with the AI image API; scene schema stays the same."
            ),
        },
        "title": "12th Street",
        "topic": topic,
        "scenes": [
            {
                "image_url": url,
                "text": line,
                "durationInSeconds": scene_seconds,
                "kicker": chapter,
            }
            for url, line, chapter in zip(urls, lines, chapters)
        ],
    }


def verify(urls: list[str]) -> bool:
    """Best-effort check that every still resolves. Needs the `requests` package."""
    try:
        import requests
    except ImportError:
        print("requests not installed; skipping URL verification")
        return True

    ok = True
    for url in urls:
        try:
            response = requests.get(url, timeout=20, stream=True, allow_redirects=True)
            response.close()
            fine = response.status_code == 200 and "image" in response.headers.get("Content-Type", "")
        except Exception as error:  # noqa: BLE001 - report, do not crash the build
            print(f"  ! {url} -> {error}")
            ok = False
            continue
        print(f"  {'ok' if fine else '!!'} {response.status_code} {url}")
        ok = ok and fine
    return ok


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate remake-ready scenes.json for a topic")
    parser.add_argument("topic", help='e.g. "The Fall of Rome"')
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--count", type=int, default=5, help="number of scenes (default 5)")
    parser.add_argument("--scene-seconds", type=float, default=5.0)
    parser.add_argument("--width", type=int, default=1920, help="still width in px")
    parser.add_argument("--height", type=int, default=1080, help="still height in px")
    parser.add_argument("--beats", type=Path, default=None,
                        help="JSON list (or {'beats': [...]}) of caption templates")
    parser.add_argument("--no-verify", action="store_true",
                        help="skip the HTTP check of the image URLs")
    parser.add_argument("--strict", action="store_true",
                        help="fail if any image URL does not resolve")
    args = parser.parse_args(argv)

    if args.count < 1:
        parser.error("--count must be at least 1")

    data = build(args.topic, args.count, args.scene_seconds, args.width, args.height, args.beats)

    if not args.no_verify:
        print(f"Checking {len(data['scenes'])} image URL(s)...")
        if not verify([scene["image_url"] for scene in data["scenes"]]) and args.strict:
            print("Some image URLs did not resolve (--strict).", file=sys.stderr)
            return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")

    print(f"\nWrote {args.out} — {len(data['scenes'])} scenes / "
          f"{len(data['scenes']) * args.scene_seconds:.0f}s on \"{args.topic}\"")
    for index, scene in enumerate(data["scenes"], start=1):
        print(f"  {index}. {scene['text']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
