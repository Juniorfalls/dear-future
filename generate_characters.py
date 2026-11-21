#!/usr/bin/env python3
"""
generate_characters.py — draw a reference sheet per character, no GPU needed.

Reads the `characters` array from an episode schema and sends each character's
`reference_prompt` to Pollinations' free image API, saving one JPEG per
character so a human can check the cast before any video is generated.

    python3 generate_characters.py
    python3 generate_characters.py --schema /tmp/lighthouse.json
    python3 generate_characters.py --schema /tmp/lighthouse.json --only mara
    python3 generate_characters.py --only mara,shad --overwrite
    python3 generate_characters.py --size 576x768 --delay 60
    python3 generate_characters.py --dry-run        # print the URLs, fetch nothing

Pollinations' free tier is one image at a time, **at least 45 s apart per IP**.
The script therefore sleeps between characters and honours `Retry-After` on a
402/429 up to `--max-wait`. Three sheets is roughly 90-135 s of wall clock;
`--delay` is the knob if the tier changes.

Images come back as JPEG with a small Pollinations logo in the corner. Free
tier caps the area at 768x768 (`--size` defaults to 768x768 and larger values
are refused rather than silently shrunk).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCHEMA_PATH = ROOT / "episode_schema.json"
OUTDIR = ROOT / "refs" / "characters"

API = "https://image.pollinations.ai/prompt/"
MAX_AREA = 768 * 768          # free-tier cap on width x height
FREE_SLOT = 45.0              # seconds between anonymous images


def log(msg):
    print(f"[chars] {msg}", flush=True)


def die(msg, code=1):
    print(f"[chars] ERROR: {msg}", file=sys.stderr, flush=True)
    sys.exit(code)


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-") or "character"


def parse_size(text: str) -> tuple[int, int]:
    try:
        width, height = (int(part) for part in str(text).lower().split("x", 1))
    except ValueError:
        die(f"bad --size {text!r}; expected e.g. 768x768")
    if width <= 0 or height <= 0:
        die(f"bad --size {text!r}; sizes must be positive")
    if width * height > MAX_AREA:
        die(f"--size {width}x{height} is {width * height} px²; the free tier "
            f"caps the area at {MAX_AREA} (768x768)")
    return width, height


def load_characters(path: Path) -> tuple[str, list[dict]]:
    if not path.exists():
        die(f"no schema at {path}")
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        die(f"{path.name} is not valid JSON: {exc}")
    characters = data.get("characters")
    if not isinstance(characters, list) or not characters:
        die(f"{path.name} has no 'characters' array. Generate one with "
            f"generate_script.py first.")
    for index, character in enumerate(characters, 1):
        for key in ("id", "name", "reference_prompt"):
            if not character.get(key):
                die(f"character {index} has no '{key}'")
    return str(data.get("episode") or path.stem), characters


def build_url(character: dict, size: tuple[int, int], seed: int,
              model: str | None, safe: str) -> str:
    params = {
        "width": size[0],
        "height": size[1],
        "seed": seed,
        "safe": safe,
    }
    if model:
        params["model"] = model
    prompt = urllib.parse.quote(character["reference_prompt"], safe="")
    return f"{API}{prompt}?{urllib.parse.urlencode(params)}"


def retry_after(exc, body: str = "") -> float | None:
    """Retry-After header, or the 'Retry after 10s' the API puts in its body."""
    raw = exc.headers.get("Retry-After") if exc.headers else None
    for candidate in (raw, *(m.group(1) for m in
                             re.finditer(r"[Rr]etry after (\d+(?:\.\d+)?)\s*s",
                                         body or ""))):
        if not candidate:
            continue
        try:
            return float(candidate)
        except ValueError:
            continue
    return None


def fetch(url: str, timeout: float, max_wait: float, retries: int) -> bytes:
    """GET one image, waiting out the free slot instead of failing."""
    deadline = time.monotonic() + max_wait
    last = ""
    for attempt in range(1, retries + 2):
        request = urllib.request.Request(
            url, headers={"User-Agent": "dear-future/generate_characters"})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as resp:
                ctype = resp.headers.get("Content-Type", "")
                body = resp.read()
                if not ctype.startswith("image/"):
                    snippet = body.decode("utf-8", "replace")[:300]
                    raise ValueError(f"returned {ctype or 'no type'}, not an "
                                     f"image: {snippet}")
                return body
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", "replace")[:300]
            wait = retry_after(exc, body)
            last = f"HTTP {exc.code}: {body}"
            # 402/429 = the 45 s slot; 5xx = "Classic API is at its limit",
            # which the service itself asks to retry after ~10 s
            retryable = exc.code in (402, 429, 500, 502, 503, 504)
            if retryable and attempt <= retries:
                pause = wait if wait is not None else (
                    FREE_SLOT if exc.code in (402, 429) else 10.0)
                if time.monotonic() + pause >= deadline:
                    die(f"--max-wait {max_wait:.0f}s is not enough ({last})")
                log(f"HTTP {exc.code}; retrying in {pause:.0f}s")
                time.sleep(pause + 1)
                continue
            die(f"{last}")
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            last = str(exc)
            if attempt <= retries:
                log(f"attempt {attempt} failed ({exc}); retrying in 5s")
                time.sleep(5)
                continue
            die(f"cannot fetch the image: {exc}")
        if time.monotonic() > deadline:
            die(f"gave up after {attempt} attempt(s): {last}")
    die(f"cannot fetch the image: {last}")


def looks_like_jpeg(body: bytes) -> bool:
    return len(body) > 2048 and body[:2] == b"\xff\xd8" and body[-2:] == b"\xff\xd9"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Draw a Pollinations reference sheet per character",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--schema", default=str(SCHEMA_PATH),
                        help="episode schema with a characters array")
    parser.add_argument("--out-dir", default=str(OUTDIR))
    parser.add_argument("--only", default="",
                        help="comma list of character ids, e.g. mara,shad")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--size", default="768x768", help="WxH, max 768x768")
    parser.add_argument("--delay", type=float, default=FREE_SLOT,
                        help="seconds between images (free tier is 45)")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--model", help="Pollinations image model override")
    parser.add_argument("--safe", choices=["true", "false"], default="false")
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--max-wait", type=float, default=180.0,
                        help="seconds to wait out 402/429 before giving up")
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    schema = Path(args.schema)
    outdir = Path(args.out_dir)
    size = parse_size(args.size)
    episode, characters = load_characters(schema)

    wanted = {slugify(n) for n in args.only.split(",") if n.strip()}
    if wanted:
        characters = [c for c in characters if slugify(c["id"]) in wanted]
        if not characters:
            die(f"--only {args.only!r} matched none of the cast")

    log(f"episode: {episode}")
    log(f"cast: {', '.join(c['id'] for c in characters)}")
    log(f"size: {size[0]}x{size[1]}  out: {outdir}")

    if not args.dry_run:
        outdir.mkdir(parents=True, exist_ok=True)

    results = []
    started = time.monotonic()
    for index, character in enumerate(characters, 1):
        cid = slugify(character["id"])
        target = outdir / f"{cid}.jpg"
        seed = args.seed + index * 101
        url = build_url(character, size, seed, args.model, args.safe)

        if target.exists() and not args.overwrite:
            size_kb = target.stat().st_size / 1024
            log(f"[{index}/{len(characters)}] {cid:<14} exists "
                f"({size_kb:.0f} KB), skipping (--overwrite to redraw)")
            results.append({"id": cid, "file": str(target.relative_to(ROOT)),
                            "status": "skipped", "bytes": target.stat().st_size})
            continue

        if args.dry_run:
            log(f"[{index}/{len(characters)}] {cid:<14} would GET {url}")
            results.append({"id": cid, "status": "dry-run", "url": url})
            continue

        # the free tier serves one image at a time
        if index > 1 and args.delay:
            time.sleep(args.delay)

        log(f"[{index}/{len(characters)}] {cid:<14} drawing "
            f"({character['role']}, {len(character['reference_prompt'])} char prompt)")
        began = time.monotonic()
        body = fetch(url, args.timeout, args.max_wait, args.retries)
        took = time.monotonic() - began

        if not looks_like_jpeg(body):
            target.write_bytes(body)
            die(f"{cid}: response is not a JPEG ({len(body)} bytes); it was "
                f"written to {target.name} for inspection")
        target.write_bytes(body)
        log(f"[{index}/{len(characters)}] {cid:<14} ok  {len(body) / 1024:.0f} KB  "
            f"{took:.1f}s  -> {target.relative_to(ROOT)}")
        results.append({
            "id": cid,
            "name": character["name"],
            "role": character["role"],
            "file": str(target.relative_to(ROOT)),
            "status": "ok",
            "bytes": len(body),
            "seed": seed,
            "prompt": character["reference_prompt"],
        })

    total = time.monotonic() - started
    ok = [r for r in results if r["status"] == "ok"]
    log(f"done: {len(ok)}/{len(results)} drawn in {total:.0f}s")
    if args.dry_run:
        return 0

    manifest = outdir / "manifest.json"
    previous = []
    if manifest.exists():
        try:
            previous = json.loads(manifest.read_text()).get("characters", [])
        except json.JSONDecodeError:
            previous = []
    by_id = {entry.get("id"): entry for entry in previous}
    for result in results:
        if result["status"] != "skipped":
            by_id[result["id"]] = result
    manifest.write_text(json.dumps({
        "episode": episode,
        "schema": str(schema),
        "size": list(size),
        "characters": [by_id[k] for k in sorted(by_id) if k],
    }, indent=2) + "\n")
    log(f"manifest: {manifest.relative_to(ROOT)}")
    log("look at the sheets before generating video: "
        f"open {outdir.relative_to(ROOT)}/*.jpg")
    return 0


if __name__ == "__main__":
    sys.exit(main())
