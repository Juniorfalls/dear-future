#!/usr/bin/env python3
"""Turn a topic into remotion/data/scenes.json.

    python generate_video.py "The History of Rome"
    python generate_video.py "Ancient Egypt" --scene-seconds 6 --count 7
    python generate_video.py "The Fall of Rome" --images openai     # needs OPENAI_API_KEY

Where the pictures come from, in priority order:

  auto (default)  local stills in remotion/public/episodes/<topic-slug>/ if any,
                  otherwise free AI-generated stills from Pollinations.ai
  assets          local stills only (fails if the folder is empty)
  pollinations    free AI-generated stills only, no API key or account needed
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
import time
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "remotion" / "public"
DEFAULT_OUT = ROOT / "remotion" / "data" / "scenes.json"

# Free, keyless text-to-image endpoint. The prompt is URL-encoded into the path.
POLLINATIONS_URL = (
    "https://image.pollinations.ai/prompt/{prompt}"
    "?width={width}&height={height}&nologo=true"
)

# Chapter beats, turned into cinematic historical prompts below. Keeping the
# same prompt for a given chapter keeps the artwork stable across re-runs
# (Pollinations caches identical prompts).
IMAGE_PROMPTS = [
    "the birth of an ancient civilisation at dawn, monumental stone architecture "
    "rising above a river valley, processions of robed figures, golden haze, "
    "birds wheeling in a wide sky",
    "the height of a great civilisation, crowded marble forum and temples, banners "
    "and colonnades, merchants and soldiers, warm late-afternoon light, immense scale",
    "a weathered clay tablet covered in cuneiform script on dark stone, a scholar's "
    "hand in the frame, raking tungsten light, dust in the air, shallow depth of field",
    "ruined columns and broken walls at dusk, smoke and embers drifting, long "
    "shadows, storm light, desaturated teal and gold",
    "ancient artefacts in dim museum light, a broken marble bust, dust motes, "
    "single warm spotlight, deep black background",
]

# Shared look for every generated still, so the episode reads as one film.
CINEMATIC_STYLE = (
    "cinematic historical documentary still, 35mm film grain, dramatic volumetric "
    "light, rich period detail, muted gold and teal colour grade, shallow depth of "
    "field, highly detailed, no text, no watermark"
)

CHAPTERS = [
    "Chapter One — The Beginning",
    "Chapter Two — The Height",
    "Chapter Three — The Turn",
    "Chapter Four — The Unravelling",
    "Chapter Five — What Remains",
]

# Presenter framing per scene. The host opens the episode full-frame, then the
# film alternates between a picture-in-picture host and b-roll-only shots. The
# virtual presenter is not rendered yet: host layouts draw a placeholder panel,
# so real host footage can be dropped in later without editing the scene list.
LAYOUT_CYCLE = ["host_pip", "broll_only"]


def layouts_for(count: int) -> list[str]:
    return ["host_full"] + [LAYOUT_CYCLE[i % len(LAYOUT_CYCLE)] for i in range(count - 1)]

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
    """A cinematic historical prompt for one chapter of the topic."""
    beat = IMAGE_PROMPTS[index % len(IMAGE_PROMPTS)]
    return f"{beat}. Subject: {topic}. {CINEMATIC_STYLE}"


def pollinations_images(topic: str, count: int, width: int, height: int) -> list[str]:
    """Generate one still per scene with Pollinations.ai and save it locally.

    Free and keyless, but the anonymous tier allows one image every ~45s per IP
    and answers 402 with a retry hint when that is exceeded. Downloading here
    (instead of leaving remote URLs in scenes.json) keeps Remotion's render
    from tripping that limit, and identical prompts are cached upstream so a
    re-run reproduces the same artwork.
    """
    try:
        import requests
    except ImportError:
        raise SystemExit(
            "Pollinations images need the requests package (pip install -r requirements.txt)"
        )

    folder = episode_dir(topic)
    folder.mkdir(parents=True, exist_ok=True)

    for index in range(count):
        target = folder / f"scene-{index + 1}.jpg"
        if target.is_file() and target.stat().st_size > 0:
            print(f"  keeping existing {target.relative_to(ROOT)}")
            continue

        url = POLLINATIONS_URL.format(
            prompt=quote(scene_prompt(topic, index), safe=""),
            width=width,
            height=height,
        )
        for attempt in range(1, 9):
            print(f"  generating scene {index + 1}/{count} with Pollinations.ai...")
            response = requests.get(url, timeout=240, stream=True)
            content_type = response.headers.get("Content-Type", "")
            if response.status_code == 200 and "image" in content_type:
                blob = response.content
                response.close()
                target.write_bytes(blob)
                print(f"    wrote {target.relative_to(ROOT)} ({len(blob) // 1024} kB)")
                break

            detail = response.text[:300].replace("\n", " ")
            response.close()
            wait = 10.0
            match = re.search(r"Retry after (\d+)s", detail)
            if response.status_code == 402 and match:
                wait = float(match.group(1)) + 2
            if attempt == 8:
                raise SystemExit(
                    f"Pollinations.ai error {response.status_code} for scene {index + 1}: {detail}"
                )
            print(f"    {response.status_code}: waiting {wait:.0f}s for the free tier")
            time.sleep(wait)

    return local_images(topic, count)


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

    if provider == "pollinations":
        urls = pollinations_images(topic, count, width, height)
        if not urls:
            raise SystemExit("Pollinations.ai returned no images")
        return urls, f"pollinations-ai:{slug(topic)}"

    if provider in ("auto", "assets"):
        assets = local_images(topic, count)
        if assets:
            return assets, f"local-assets:{slug(topic)}"
        if provider == "assets":
            raise SystemExit(
                f"--images assets: no stills in {episode_dir(topic).relative_to(ROOT)} "
                f"(expected scene-1.jpg, scene-2.jpg, ...)"
            )

    return pollinations_images(topic, count, width, height), "pollinations-ai"


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
    layouts = layouts_for(count)

    return {
        "_notes": {
            "generated_by": "generate_video.py",
            "topic": topic,
            "image_source": source,
            "layouts": (
                "layout is one of host_full (presenter only), host_pip (b-roll + "
                "presenter PiP) or broll_only. Missing layout falls back to "
                "broll_only. host_full scenes may omit image_url."
            ),
            "swap_images": (
                "Put stills in remotion/public/episodes/<topic-slug>/ as scene-1.jpg, "
                "scene-2.jpg, ... and they are picked up automatically. Otherwise "
                "Pollinations.ai generates a still per scene from its prompt, or run "
                "with --images openai to use OpenAI's image API."
            ),
        },
        "title": "12th Street",
        "topic": topic,
        "scenes": [
            {
                "layout": layout,
                "image_url": url,
                "text": line,
                "durationInSeconds": scene_seconds,
                "kicker": chapter,
            }
            for url, line, chapter, layout in zip(urls, lines, chapters, layouts)
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
        # Pollinations renders on demand, so the first hit for a prompt can
        # take a while; allow for that and retry once on a transient error.
        fine = False
        for attempt in range(2):
            try:
                response = requests.get(url, timeout=120, stream=True, allow_redirects=True)
                content_type = response.headers.get("Content-Type", "")
                response.close()
                fine = response.status_code == 200 and "image" in content_type
                if fine:
                    break
                print(f"  ! {url} -> {response.status_code} {content_type} (attempt {attempt + 1})")
            except Exception as error:  # noqa: BLE001 - report, do not crash the build
                print(f"  ! {url} -> {error} (attempt {attempt + 1})")
            time.sleep(3 * (attempt + 1))
        print(f"  {'ok' if fine else '!!'} {url}")
        ok = ok and fine
    return ok


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate Remotion-ready scenes.json for a topic")
    parser.add_argument("topic", help='e.g. "The Fall of Rome"')
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--count", type=int, default=5, help="number of scenes (default 5)")
    parser.add_argument("--scene-seconds", type=float, default=5.0)
    parser.add_argument("--width", type=int, default=1080, help="still width in px")
    parser.add_argument("--height", type=int, default=1920, help="still height in px")
    parser.add_argument("--beats", type=Path, default=None,
                        help="JSON list (or {'beats': [...]}) of caption templates")
    parser.add_argument("--images", default="auto",
                        choices=("auto", "assets", "pollinations", "openai"),
                        help="image source (default: auto = local stills, else Pollinations.ai)")
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
        print(f"  {index}. [{scene['layout']}] {scene['text']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
