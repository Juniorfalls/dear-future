#!/usr/bin/env python3
"""Build the Episode 1 storyboard grid and subject reference with Pollinations.

The 3x3 sheet is assembled from nine individual 9:16 panels so every cell is
exactly one shot. The panels are also kept in refs/panels/ for AnimateDiff
image-to-video conditioning.

    python3 make_grid.py
    python3 make_grid.py --force --seed 7001
    python3 make_grid.py --no-subject
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from io import BytesIO
from pathlib import Path
from urllib.parse import quote

import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent
API = "https://image.pollinations.ai/prompt/"
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def full_prompt(episode: dict, shot: dict | None = None) -> str:
    look = episode["look"]
    parts = [look["style"]]
    if shot is None or shot.get("figure", True):
        parts.append(look["subject"])
    if shot is None:
        parts.append(episode["subject_prompt"])
    else:
        parts.append(shot["prompt"])
        parts.append(shot.get("figure_note", ""))
    text = ", ".join(p for p in parts if p)
    return " ".join(text.split())


def fetch_image(
    prompt: str,
    width: int,
    height: int,
    seed: int,
    model: str,
    timeout: int,
    session: requests.Session,
    negative: str = "",
    strip_watermark: bool = True,
) -> Image.Image:
    url = API + quote(prompt, safe="")
    params = {
        "width": width,
        "height": height,
        "seed": seed,
        "model": model,
        "nologo": "true",
        "enhance": "false",
        "private": "true",
        "negative_prompt": negative,
    }
    last_error = ""
    for attempt in range(1, 21):
        try:
            response = session.get(url, params=params, timeout=timeout)
            if response.status_code == 200:
                image = Image.open(BytesIO(response.content)).convert("RGB")
                if image.width < 64 or image.height < 64:
                    raise ValueError(f"tiny image {image.size}")
                if strip_watermark:
                    # The anonymous free tier stamps a small logo bottom-right
                    # even with nologo=true; remove it before framing the panel.
                    image = image.crop((0, 0, image.width, int(image.height * 0.935)))
                return ImageOps.fit(image, (width, height), Image.Resampling.LANCZOS)
            last_error = f"HTTP {response.status_code}: {response.text[:180]}"
            if response.status_code == 402 and "FREE_LIMIT" in response.text:
                match = re.search(r"Retry after (\d+)s", response.text)
                wait = int(match.group(1)) + 5 if match else 50
                print(f"    free-tier limit; waiting {wait}s", file=sys.stderr)
                time.sleep(wait)
                continue
            if response.status_code == 503:
                print("    Pollinations busy; waiting 15s", file=sys.stderr)
                time.sleep(15)
                continue
            if response.status_code in (400, 401, 403, 404):
                break
        except Exception as exc:  # noqa: BLE001 - retry the API, report the last reason
            last_error = f"{type(exc).__name__}: {exc}"
        if attempt < 20:
            wait = min(30, 4 * attempt)
            print(f"    retry {attempt}/20 in {wait}s ({last_error})", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError(f"Pollinations failed: {last_error}")


def make_grid(panels: list[Image.Image], shots: list[dict], title: str, out: Path) -> None:
    width, height = 1080, 1920
    margin, top, bottom, gutter = 18, 18, 38, 10
    cell_w = (width - 2 * margin - 2 * gutter) // 3
    cell_h = (height - top - bottom - 2 * gutter) // 3
    canvas = Image.new("RGB", (width, height), "#050707")
    draw = ImageDraw.Draw(canvas)
    label_font = load_font(19)
    index_font = load_font(34)

    for i, (panel, shot) in enumerate(zip(panels, shots)):
        col, row = i % 3, i // 3
        x = margin + col * (cell_w + gutter)
        y = top + row * (cell_h + gutter)
        image = ImageOps.fit(panel, (cell_w, cell_h), Image.Resampling.LANCZOS)
        canvas.paste(image, (x, y))

        # A readable label strip that does not hide the composition.
        strip_h = 58
        overlay = Image.new("RGBA", (cell_w, strip_h), (0, 0, 0, 176))
        canvas.paste(Image.alpha_composite(
            canvas.crop((x, y, x + cell_w, y + strip_h)).convert("RGBA"), overlay
        ).convert("RGB"), (x, y))

        draw.rectangle([x, y, x + cell_w - 1, y + cell_h - 1], outline="#9ab7ac", width=2)
        draw.text((x + 10, y + 8), f"{shot['index']:02d}", font=index_font, fill="#e8f2eb")
        label = shot["title"].upper()
        draw.text((x + 58, y + 15), label[:27], font=label_font, fill="#d3e4da")

    footer = f"{title.upper()}  ·  9 SHOTS  ·  27 SECONDS"
    draw.text((margin, height - 12), footer, font=load_font(15), fill="#6e8b80", anchor="ls")
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out, format="PNG", optimize=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--episode", default=str(ROOT / "episode_schema.json"))
    parser.add_argument("--out", default=str(ROOT / "refs" / "storyboard_grid.png"))
    parser.add_argument("--subject-out", default=str(ROOT / "refs" / "subject.png"))
    parser.add_argument("--panels-dir", default=str(ROOT / "refs" / "panels"))
    parser.add_argument("--width", type=int, default=576)
    parser.add_argument("--height", type=int, default=1024)
    parser.add_argument("--subject-width", type=int, default=768)
    parser.add_argument("--subject-height", type=int, default=1024)
    parser.add_argument("--seed", type=int, default=1307)
    parser.add_argument("--model", default="flux")
    parser.add_argument("--timeout", type=int, default=150)
    parser.add_argument("--delay", type=float, default=47.0,
                        help="free Pollinations allows one image every 45 s")
    parser.add_argument("--force", action="store_true", help="regenerate panels that already exist")
    parser.add_argument("--no-subject", action="store_true")
    parser.add_argument("--keep-watermark", action="store_true")
    args = parser.parse_args()

    episode = json.loads(Path(args.episode).read_text())
    shots = episode["shots"]
    if len(shots) != 9:
        sys.exit(f"episode_schema.json has {len(shots)} shots; expected 9")

    out = Path(args.out)
    panels_dir = Path(args.panels_dir)
    subject_out = Path(args.subject_out)
    panels_dir.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers["User-Agent"] = "dear-future-storyboard/1.0"

    panels: list[Image.Image] = []
    manifest = {
        "episode": episode["id"],
        "title": episode["title"],
        "subject": episode["subject"],
        "model": args.model,
        "seed": args.seed,
        "panels": [],
    }

    for shot in shots:
        panel_path = panels_dir / f"{shot['id']}.png"
        seed = args.seed + shot["index"] * 101
        prompt = full_prompt(episode, shot)
        if panel_path.exists() and not args.force:
            print(f"[{shot['index']}/9] reuse {panel_path}")
            image = Image.open(panel_path).convert("RGB")
        else:
            print(f"[{shot['index']}/9] generating {shot['title']} (seed {seed})")
            image = fetch_image(prompt, args.width, args.height, seed, args.model,
                                args.timeout, session, episode["look"]["negative"],
                                strip_watermark=not args.keep_watermark)
            image.save(panel_path, format="PNG", optimize=True)
            time.sleep(args.delay)
        panels.append(image)
        manifest["panels"].append({
            "shot": shot["id"],
            "file": str(panel_path.relative_to(ROOT)),
            "seed": seed,
            "prompt": prompt,
        })

    print(f"[grid] composing {out}")
    make_grid(panels, shots, episode["title"], out)

    if not args.no_subject:
        subject_seed = args.seed
        subject_prompt = full_prompt(episode)
        print(f"[subject] generating {subject_out} (seed {subject_seed})")
        subject = fetch_image(subject_prompt, args.subject_width, args.subject_height,
                              subject_seed, args.model, args.timeout, session,
                              episode["look"]["negative"],
                              strip_watermark=not args.keep_watermark)
        subject_out.parent.mkdir(parents=True, exist_ok=True)
        subject.save(subject_out, format="PNG", optimize=True)
        manifest["subject"] = {
            "file": str(subject_out.relative_to(ROOT)),
            "seed": subject_seed,
            "prompt": subject_prompt,
        }

    manifest_path = out.with_suffix(".json")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"grid     {out}")
    if not args.no_subject:
        print(f"subject  {subject_out}")
    print(f"manifest {manifest_path}")


if __name__ == "__main__":
    main()
