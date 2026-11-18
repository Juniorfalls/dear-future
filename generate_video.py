#!/usr/bin/env python3
"""Turn a topic into remotion/data/scenes.json.

    python generate_video.py "The History of Rome"
    python generate_video.py "Ancient Egypt" --scene-seconds 6 --count 7
    python generate_video.py "The Fall of Rome" --images openai     # needs OPENAI_API_KEY

Where the pictures come from, in priority order:

  auto (default)  local stills in remotion/public/episodes/<topic-slug>/ if any,
                  otherwise free picsum.photos placeholders
  assets          local stills only (fails if the folder is empty)
  picsum          placeholders only, useful before art exists
  openai          generate stills with OpenAI's image API into the episode
                  folder, then use them (see README for the key setup)
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "remotion" / "public"
DEFAULT_OUT = ROOT / "remotion" / "data" / "scenes.json"

PLACEHOLDER_URL = "https://picsum.photos/seed/{seed}/{width}/{height}"

# Visual prompts per chapter, used both as the AI image prompt and as the seed
# for placeholder photos, so the pairing between chapter and artwork is stable.
IMAGE_PROMPTS = [
    "epic cinematic still of an ancient city at dawn, monumental stone "
    "architecture, golden haze, birds in a wide sky, documentary photography, no text",
    "epic cinematic still of the height of a civilisation, temples and processions, "
    "warm light, immense scale, documentary photography, no text",
    "cinematic still of a weathered clay tablet covered in cuneiform script on dark "
    "stone, raking tungsten light, dust in the air, shallow depth of field, no text",
    "cinematic still of ruined columns and broken walls at dusk, smoke and embers, "
    "long shadows, storm light, desaturated teal and gold, no text",
    "cinematic still of ancient artefacts in dim museum light, broken marble bust, "
    "dust motes, single warm spotlight, deep black background, no text",
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

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


# --------------------------------------------------------------------------- #
# paths and naming
# --------------------------------------------------------------------------- #
def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "topic"


def episode_dir(topic: str) -> Path:
    """Where this episode's stills live, served by Remotion from remotion/public."""
    return PUBLIC / "episodes" / slug(topic)


def _natural_key(path: Path):
    numbers = re.findall(r"\d+", path.stem)
    return (int(numbers[-1]) if numbers else 0, path.name)


def local_images(topic: str, count: int) -> list[str]:
    """Scene URLs for stills already committed under remotion/public."""
    folder = episode_dir(topic)
    if not folder.is_dir():
        return []
    stills = sorted(
        (p for p in folder.iterdir() if p.suffix.lower() in IMAGE_SUFFIXES),
        key=_natural_key,
    )
    if not stills:
        return []
    # No leading slash: the composition passes these through Remotion's
    # staticFile(), which serves remotion/public at its own base path.
    return [
        f"episodes/{slug(topic)}/{stills[index % len(stills)].name}" for index in range(count)
    ]


def scene_prompt(topic: str, index: int) -> str:
    return f"{IMAGE_PROMPTS[index % len(IMAGE_PROMPTS)]}, subject: {topic}"


def picsum_images(topic: str, count: int, width: int, height: int) -> list[str]:
    return [
        PLACEHOLDER_URL.format(
            seed=quote(f"{slug(topic)}-{index + 1}-{slug(IMAGE_PROMPTS[index % len(IMAGE_PROMPTS)])[:32]}"),
            width=width,
            height=height,
        )
        for index in range(count)
    ]


# --------------------------------------------------------------------------- #
# optional real generator (OpenAI Images)
# --------------------------------------------------------------------------- #
def openai_images(topic: str, count: int, width: int, height: int, model: str) -> list[str]:
    """Generate one still per scene with OpenAI and save it into the episode folder.

    Needs OPENAI_API_KEY. In CI, add it as a repository secret and expose it to
    the "Generate scenes from the topic" step via `env:`.
    """
    try:
        import requests
    except ImportError:
        raise SystemExit("--images openai needs the requests package (pip install -r requirements.txt)")

    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        raise SystemExit(
            "OPENAI_API_KEY is not set. Export it locally, or add it as a GitHub "
            "secret and pass it to the generate step."
        )

    size = "1792x1024" if width >= height else "1024x1792"
    folder = episode_dir(topic)
    folder.mkdir(parents=True, exist_ok=True)

    for index in range(count):
        prompt = scene_prompt(topic, index)
        print(f"  generating scene {index + 1}/{count} with {model}...")
        response = requests.post(
            "https://api.openai.com/v1/images/generations",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": model, "prompt": prompt, "size": size, "n": 1},
            timeout=240,
        )
        if response.status_code != 200:
            raise SystemExit(f"OpenAI image API error {response.status_code}: {response.text[:500]}")

        item = response.json()["data"][0]
        if item.get("b64_json"):
            blob = base64.b64decode(item["b64_json"])
        else:  # dall-e-3 returns a temporary URL
            download = requests.get(item["url"], timeout=240)
            download.raise_for_status()
            blob = download.content

        target = folder / f"scene-{index + 1}.jpg"
        target.write_bytes(blob)
        print(f"    wrote {target.relative_to(ROOT)}")

    return local_images(topic, count)


def resolve_images(topic: str, count: int, width: int, height: int,
                   provider: str, model: str) -> tuple[list[str], str]:
    """Return (scene image URLs, human-readable source label)."""
    if provider == "openai":
        return openai_images(topic, count, width, height, model), f"openai:{model}"

    if provider in ("auto", "assets"):
        assets = local_images(topic, count)
        if assets:
            return assets, f"local-assets:{slug(topic)}"
        if provider == "assets":
            raise SystemExit(
                f"--images assets: no stills in {episode_dir(topic).relative_to(ROOT)} "
                f"(expected scene-1.jpg, scene-2.jpg, ...)"
            )

    return picsum_images(topic, count, width, height), "picsum-placeholder"


# --------------------------------------------------------------------------- #
# script
# --------------------------------------------------------------------------- #
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
          beats_file: Path | None, provider: str, model: str) -> dict:
    urls, source = resolve_images(topic, count, width, height, provider, model)
    lines = captions(topic, count, beats_file)
    chapters = [CHAPTERS[i % len(CHAPTERS)] for i in range(count)]

    return {
        "_notes": {
            "generated_by": "generate_video.py",
            "topic": topic,
            "image_source": source,
            "swap_images": (
                "Put stills in remotion/public/episodes/<topic-slug>/ as scene-1.jpg, "
                "scene-2.jpg, ... and they are picked up automatically, or run with "
                "--images openai to have the image API generate them."
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
    """Check local stills exist and remote URLs resolve."""
    ok = True
    remote = []
    for url in urls:
        if not url.startswith("http"):
            path = PUBLIC / url.lstrip("/")
            exists = path.is_file()
            print(f"  {'ok' if exists else '!!'} {url} ({path.stat().st_size // 1024} kB)" if exists else f"  !! missing {path}")
            ok = ok and exists
        else:
            remote.append(url)

    if not remote:
        return ok

    try:
        import requests
    except ImportError:
        print("requests not installed; skipping remote URL verification")
        return ok

    for url in remote:
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
    parser = argparse.ArgumentParser(description="Generate Remotion-ready scenes.json for a topic")
    parser.add_argument("topic", help='e.g. "The Fall of Rome"')
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--count", type=int, default=5, help="number of scenes (default 5)")
    parser.add_argument("--scene-seconds", type=float, default=5.0)
    parser.add_argument("--width", type=int, default=1920, help="still width in px")
    parser.add_argument("--height", type=int, default=1080, help="still height in px")
    parser.add_argument("--beats", type=Path, default=None,
                        help="JSON list (or {'beats': [...]}) of caption templates")
    parser.add_argument("--images", default="auto",
                        choices=("auto", "assets", "picsum", "openai"),
                        help="image source (default: auto = local stills, else placeholders)")
    parser.add_argument("--model", default="dall-e-3", help="OpenAI image model (with --images openai)")
    parser.add_argument("--no-verify", action="store_true", help="skip checking that images resolve")
    parser.add_argument("--strict", action="store_true", help="fail if any image does not resolve")
    args = parser.parse_args(argv)

    if args.count < 1:
        parser.error("--count must be at least 1")

    data = build(args.topic, args.count, args.scene_seconds, args.width, args.height,
                 args.beats, args.images, args.model)

    if not args.no_verify:
        print(f"Checking {len(data['scenes'])} image(s) [{data['_notes']['image_source']}]...")
        if not verify([scene["image_url"] for scene in data["scenes"]]) and args.strict:
            print("Some images did not resolve (--strict).", file=sys.stderr)
            return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")

    total = len(data["scenes"]) * args.scene_seconds
    print(f"\nWrote {args.out} — {len(data['scenes'])} scenes / {total:.0f}s on \"{args.topic}\"")
    for index, scene in enumerate(data["scenes"], start=1):
        print(f"  {index}. {scene['text']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
