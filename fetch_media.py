#!/usr/bin/env python3
"""Fetch footage and a subject image for a "Before You" episode.

    export PEXELS_API_KEY="..."
    python fetch_media.py "iPhone 15" --format buy

    # No Pexels key yet? Use a pool of public MP4 clips for a test render:
    python fetch_media.py "iPhone 15" --format buy --test

What it writes
--------------
remotion/public/episodes/<topic-slug>/
    bg-1.mp4 ... bg-N.mp4   background stock clips (3-5)
    subject.jpg             one image of the thing being reviewed
    credits.json            source + licence notes for every download
remotion/data/scenes.json   the scene list Remotion renders

Pexels is used for both videos and the subject photo when PEXELS_API_KEY is
set. Without a key (or with --test) the script falls back to stable, public
Mixkit MP4s and a Wikimedia Commons photo of the topic, so the render pipeline
can be exercised before the API key exists.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "remotion" / "public"
DEFAULT_OUT = ROOT / "remotion" / "data" / "scenes.json"

PEXELS_VIDEOS = "https://api.pexels.com/videos/search"
PEXELS_PHOTOS = "https://api.pexels.com/v1/search"
WIKIMEDIA_API = "https://commons.wikimedia.org/w/api.php"

USER_AGENT = "before-you-media-fetcher/1.0 (+https://github.com/Juniorfalls/dear-future)"

# Public, directly downloadable stock clips (Mixkit free licence, no key). Used
# by --test and when no Pexels key is configured. Every URL is a phone/tech
# clip so the test episode is at least visually on-topic.
TEST_CLIPS = [
    ("Hands of a person typing on a cell phone", "https://assets.mixkit.co/videos/4915/4915-720.mp4"),
    ("Hands shown texting on a smartphone", "https://assets.mixkit.co/videos/144/144-720.mp4"),
    ("Hands texting on a mobile phone at night", "https://assets.mixkit.co/videos/14669/14669-720.mp4"),
    ("Woman using her cell phone", "https://assets.mixkit.co/videos/39789/39789-720.mp4"),
    ("Man answering a message on his phone", "https://assets.mixkit.co/videos/41165/41165-720.mp4"),
]

# Captions are written fast and short: they are burned in as outlined pop-on
# subtitles, so they must survive one glance. {topic} is substituted.
BEATS = {
    "buy": [
        "So you want the {topic}.",
        "Here is what the spec sheet leaves out.",
        "This is the flaw that shows up in week one.",
        "At this price, it is a hard sell.",
        "Wait for the drop, or buy it used.",
    ],
    "play": [
        "So you want to play {topic}.",
        "The first two hours are not the real game.",
        "This is where the systems fall apart.",
        "How long before it respects your time?",
        "Full price, sale price, or skip it?",
    ],
    "watch": [
        "So you want to watch {topic}.",
        "The trailer is selling a different film.",
        "This is the scene everyone will spoil.",
        "It works, right up until the third act.",
        "Stream it, rent it, or skip it.",
    ],
}

KICKERS = {
    "buy": ["BEFORE YOU BUY", "THE BREAKDOWN", "THE CATCH", "THE VERDICT", "WORTH IT?"],
    "play": ["BEFORE YOU PLAY", "THE BREAKDOWN", "THE CATCH", "THE VERDICT", "WORTH IT?"],
    "watch": ["BEFORE YOU WATCH", "THE BREAKDOWN", "THE CATCH", "THE VERDICT", "WORTH IT?"],
}

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


# --------------------------------------------------------------------------- #
# paths, timing and downloads
# --------------------------------------------------------------------------- #
def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "topic"


def episode_dir(topic: str) -> Path:
    return PUBLIC / "episodes" / slug(topic)


def video_duration(path: Path) -> float | None:
    """Seconds, via ffprobe when it is installed. None means unknown."""
    if not shutil.which("ffprobe"):
        return None
    try:
        out = subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(path)],
            text=True, timeout=30,
        ).strip()
        return float(out) if out else None
    except (subprocess.SubprocessError, ValueError):
        return None


def _requests():
    try:
        import requests
    except ImportError:
        raise SystemExit(
            "fetch_media.py needs the requests package (pip install -r requirements.txt)"
        )
    return requests


def get_json(url: str, *, params: dict, headers: dict | None = None) -> dict:
    requests = _requests()
    merged = {"User-Agent": USER_AGENT}
    merged.update(headers or {})
    response = requests.get(url, params=params, headers=merged, timeout=60)
    response.raise_for_status()
    return response.json()


def download(url: str, target: Path, *, minimum_bytes: int = 40_000) -> Path:
    """Stream a URL to disk atomically and refuse tiny/HTML error pages."""
    requests = _requests()
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + ".part")
    with requests.get(url, stream=True, timeout=300,
                      headers={"User-Agent": USER_AGENT}) as response:
        response.raise_for_status()
        with partial.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1 << 20):
                if chunk:
                    handle.write(chunk)
    size = partial.stat().st_size
    if size < minimum_bytes:
        partial.unlink(missing_ok=True)
        raise RuntimeError(f"download too small ({size} bytes): {url}")
    partial.replace(target)
    print(f"    wrote {target.relative_to(ROOT)} ({size / 1_048_576:.1f} MB)")
    return target


# --------------------------------------------------------------------------- #
# Pexels (keyed) source
# --------------------------------------------------------------------------- #
def pexels_headers(key: str) -> dict:
    return {"Authorization": key, "User-Agent": USER_AGENT}


def pick_pexels_file(files: list[dict]) -> dict | None:
    """Closest MP4 to 1080p/1440p; ignore 4K so episode folders stay small."""
    candidates = [
        item for item in files
        if item.get("file_type") == "video/mp4" and item.get("link")
    ]
    if not candidates:
        return None

    def score(item: dict) -> tuple:
        width = int(item.get("width") or 0)
        return (0 if 1280 <= width <= 2200 else 1, abs(width - 1920), -width)

    return sorted(candidates, key=score)[0]


def fetch_pexels_clips(topic: str, count: int, key: str, folder: Path) -> list[dict]:
    data = get_json(
        PEXELS_VIDEOS,
        params={"query": topic, "per_page": max(15, count * 4), "orientation": "landscape"},
        headers=pexels_headers(key),
    )
    clips: list[dict] = []
    seen: set[int] = set()
    for video in data.get("videos", []):
        if len(clips) >= count:
            break
        if video.get("id") in seen or float(video.get("duration") or 0) < 3:
            continue
        chosen = pick_pexels_file(video.get("video_files") or [])
        if not chosen:
            continue
        seen.add(video.get("id"))
        target = folder / f"bg-{len(clips) + 1}.mp4"
        print(f"  clip {len(clips) + 1}/{count}: {video.get('user', {}).get('name', 'Pexels')}")
        download(chosen["link"], target)
        clips.append({
            "file": target.name,
            "credit": f"Pexels / {video.get('user', {}).get('name', 'unknown')}",
            "source": video.get("url", "https://www.pexels.com/videos/"),
        })
    if len(clips) < 3:
        raise SystemExit(f"Pexels returned only {len(clips)} usable clips for {topic!r}")
    return clips


def fetch_pexels_photo(topic: str, key: str, folder: Path) -> dict:
    data = get_json(
        PEXELS_PHOTOS,
        params={"query": topic, "per_page": 8, "orientation": "landscape"},
        headers=pexels_headers(key),
    )
    for photo in data.get("photos", []):
        src = photo.get("src") or {}
        url = src.get("large2x") or src.get("large") or src.get("original")
        if not url:
            continue
        target = folder / "subject.jpg"
        print(f"  subject photo: {photo.get('alt', topic)[:70]}")
        download(url, target, minimum_bytes=20_000)
        return {
            "file": target.name,
            "credit": f"Pexels / {photo.get('photographer', 'unknown')}",
            "source": photo.get("url", "https://www.pexels.com/"),
        }
    raise SystemExit(f"Pexels found no subject photo for {topic!r}")


# --------------------------------------------------------------------------- #
# keyless fallback source (test renders and Wikimedia subject photo)
# --------------------------------------------------------------------------- #
def strip_tags(value: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", value or "")).strip()


def fetch_wikimedia_photo(topic: str, folder: Path) -> dict:
    data = get_json(WIKIMEDIA_API, params={
        "action": "query", "generator": "search", "gsrsearch": topic,
        "gsrnamespace": 6, "gsrlimit": 12, "prop": "imageinfo",
        "iiprop": "url|mime|size|extmetadata", "iiurlwidth": 1400,
        "format": "json", "formatversion": 2,
    })
    pages = sorted(data.get("query", {}).get("pages", []), key=lambda p: p.get("index", 99))
    for page in pages:
        info = (page.get("imageinfo") or [{}])[0]
        if info.get("mime") not in {"image/jpeg", "image/png", "image/webp"}:
            continue
        if int(info.get("width") or 0) < 600:
            continue
        url = info.get("thumburl") or info.get("url")
        if not url:
            continue
        meta = info.get("extmetadata") or {}
        target = folder / "subject.jpg"
        print(f"  subject photo: {page.get('title', topic)[:70]}")
        download(url, target, minimum_bytes=20_000)
        return {
            "file": target.name,
            "credit": strip_tags((meta.get("Artist") or {}).get("value", "")) or "Wikimedia Commons",
            "source": info.get("descriptionurl", "https://commons.wikimedia.org/"),
            "license": strip_tags((meta.get("LicenseShortName") or {}).get("value", "")),
        }
    raise SystemExit(
        f"No usable Wikimedia Commons photo for {topic!r}. "
        "Set PEXELS_API_KEY or pass --image <file-or-url>."
    )


def fetch_test_clips(count: int, folder: Path) -> list[dict]:
    clips = []
    for index, (label, url) in enumerate(TEST_CLIPS[:count]):
        target = folder / f"bg-{index + 1}.mp4"
        if target.is_file() and target.stat().st_size > 40_000:
            print(f"  clip {index + 1}/{count}: keeping existing {target.name}")
        else:
            print(f"  clip {index + 1}/{count}: {label} (Mixkit, public test clip)")
            download(url, target)
        clips.append({
            "file": target.name,
            "credit": f"Mixkit / {label} (Mixkit Free License)",
            "source": url,
        })
    return clips


def copy_local_image(source: Path, folder: Path) -> dict:
    if source.suffix.lower() not in IMAGE_SUFFIXES:
        raise SystemExit(f"--image must be one of {sorted(IMAGE_SUFFIXES)}")
    target = folder / f"subject{source.suffix.lower()}"
    shutil.copyfile(source, target)
    print(f"  subject photo: copied {source.name}")
    return {"file": target.name, "credit": "user supplied", "source": str(source)}


# --------------------------------------------------------------------------- #
# scenes
# --------------------------------------------------------------------------- #
def caption_lines(topic: str, fmt: str, count: int) -> list[str]:
    templates = BEATS[fmt]
    lines = []
    for index in range(count):
        template = templates[min(index, len(templates) - 1)]
        lines.append(template.format(topic=topic) if "{topic}" in template else template)
    return lines


def build_scenes(topic: str, fmt: str, clips: list[dict], photo: dict,
                 scene_seconds: float, folder: Path) -> list[dict]:
    lines = caption_lines(topic, fmt, len(clips))
    kickers = KICKERS[fmt]
    scenes = []
    for index, clip in enumerate(clips):
        duration = video_duration(folder / clip["file"])
        hold = scene_seconds if duration is None else min(scene_seconds, max(1.5, duration - 0.15))
        scene = {
            "video_url": f"episodes/{folder.name}/{clip['file']}",
            "text": lines[index],
            "layout": "broll_only",
            "transition": "cut",
            "grade": "neutral",
            "kicker": kickers[min(index, len(kickers) - 1)],
            "durationInSeconds": round(hold, 2),
        }
        # The subject image floats over the hook and the verdict; the middle
        # shots stay clean footage so the video does not feel like a slideshow.
        if index == 0 or index == len(clips) - 1:
            scene["image_url"] = f"episodes/{folder.name}/{photo['file']}"
        scenes.append(scene)
    return scenes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fetch stock footage + a subject image and write Remotion scenes.json"
    )
    parser.add_argument("topic", help='the thing being reviewed, e.g. "iPhone 15"')
    parser.add_argument("--format", default="buy", choices=tuple(BEATS),
                        help="episode angle (default: buy)")
    parser.add_argument("--clips", type=int, default=4, help="background clips, 3-5 (default 4)")
    parser.add_argument("--scene-seconds", type=float, default=4.0,
                        help="requested hold per clip (default 4)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--pexels-key", default=os.environ.get("PEXELS_API_KEY", ""),
                        help="Pexels API key (default: PEXELS_API_KEY)")
    parser.add_argument("--test", action="store_true",
                        help="force public Mixkit clips + Wikimedia photo (no API key)")
    parser.add_argument("--image", type=Path, default=None,
                        help="use this local subject image instead of downloading one")
    parser.add_argument("--no-verify", action="store_true", help="skip the final file check")
    args = parser.parse_args(argv)

    if not 3 <= args.clips <= 5:
        parser.error("--clips must be between 3 and 5")
    if args.scene_seconds < 1.5:
        parser.error("--scene-seconds must be at least 1.5")

    folder = episode_dir(args.topic)
    folder.mkdir(parents=True, exist_ok=True)

    key = args.pexels_key.strip()
    use_pexels = bool(key) and not args.test
    if not use_pexels and not args.test:
        raise SystemExit(
            "PEXELS_API_KEY is not set.\n"
            "  export PEXELS_API_KEY=\"...\"   # free key: https://www.pexels.com/api/\n"
            "or run with --test to use public Mixkit clips for a test render."
        )

    print(f"Episode: {args.topic} [{args.format}] -> {folder.relative_to(ROOT)}")
    if use_pexels:
        clips = fetch_pexels_clips(args.topic, args.clips, key, folder)
        photo = (copy_local_image(args.image, folder) if args.image
                 else fetch_pexels_photo(args.topic, key, folder))
        media_source = "pexels"
    else:
        print("  no Pexels key: using public test clips (Mixkit)")
        clips = fetch_test_clips(args.clips, folder)
        photo = (copy_local_image(args.image, folder) if args.image
                 else fetch_wikimedia_photo(args.topic, folder))
        media_source = "test-public-mixkit"

    (folder / "credits.json").write_text(json.dumps(
        {"topic": args.topic, "videos": clips, "image": photo}, indent=2,
    ) + "\n")

    scenes = build_scenes(args.topic, args.format, clips, photo, args.scene_seconds, folder)
    data: dict[str, Any] = {
        "_notes": {
            "generated_by": "fetch_media.py",
            "topic": args.topic,
            "format": args.format,
            "media_source": media_source,
            "image_source": photo.get("source"),
            "credits": f"episodes/{folder.name}/credits.json",
            "schema": "video_url is the full-bleed background; image_url floats as the subject overlay",
        },
        "title": "Before You",
        "topic": args.topic,
        # Reference look: clean full-frame cuts, outlined subtitles, no
        # letterbox/dust, and a short brand wordmark on the opening shot.
        "style": {
            "letterbox": False,
            "atmosphereOpacity": 0,
            "lightSweep": False,
            "vignette": False,
            "wordmark": "intro",
            "scrim": 0.2,
        },
        "audio": {"src": "audio/bg_music.mp3", "volume": 0.12, "loop": True},
        "scenes": scenes,
    }

    if not args.no_verify:
        missing = []
        for scene in scenes:
            for field in ("video_url", "image_url"):
                if scene.get(field) and not (PUBLIC / scene[field]).is_file():
                    missing.append(scene[field])
        if missing:
            raise SystemExit("missing media: " + ", ".join(missing))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")

    total = sum(scene["durationInSeconds"] for scene in scenes)
    print(f"\nWrote {args.out.relative_to(ROOT)}: {len(scenes)} scenes / ~{total:.1f}s")
    for index, scene in enumerate(scenes, start=1):
        overlay = " + subject" if scene.get("image_url") else ""
        print(f"  {index}. {scene['kicker']}: {scene['text']}{overlay}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())