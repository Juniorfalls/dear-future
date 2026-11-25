#!/usr/bin/env python3
"""One command per episode: write -> render -> QA -> package.

Resumable: every stage records itself in out/episodes/<slug>/state.json, so a
failed render or a flaky writer does not throw away the earlier work.

    python3 make_episode.py "a night bus that stops where no stop exists"
    python3 make_episode.py "..." --max-seconds 15     # short test cut
    python3 make_episode.py --episode episodes/x.json  # skip the writer
    python3 make_episode.py "..." --resume

The box is small: a disk guard refuses to start below --min-free-gb and the
retention pass keeps only the newest --keep finals.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from archive_kit import archive as archive_files

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out" / "episodes"
LOCK = OUT / ".lock"
PY = str(ROOT / ".venv" / "bin" / "python")


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return "-".join(s.split("-")[:6]) or "episode"


def free_gb() -> float:
    return shutil.disk_usage(ROOT).free / 1e9


def guard(min_gb: float, where: str) -> None:
    g = free_gb()
    print(f"disk: {g:.2f} GB free ({where})")
    if g < min_gb:
        raise SystemExit(f"only {g:.2f} GB free, need {min_gb:.2f} GB; "
                         "archive or delete old renders first")


def acquire_lock() -> None:
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    fd = open(LOCK, "w")
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit("another episode is already rendering (out/episodes/.lock)")
    fd.write(str(os.getpid()))
    fd.flush()


def run_stage(name: str, cmd: list[str], log: Path, timeout: float) -> None:
    log.parent.mkdir(parents=True, exist_ok=True)
    print(f"\n[{name}] {' '.join(cmd[:6])} ...")
    started = time.time()
    with open(log, "w") as fh:
        p = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT,
                           timeout=timeout, cwd=ROOT)
    secs = time.time() - started
    if p.returncode != 0:
        tail = "\n".join(log.read_text(errors="replace").splitlines()[-18:])
        raise SystemExit(f"[{name}] failed after {secs:.0f}s (exit {p.returncode})\n{tail}")
    print(f"[{name}] ok in {secs:.0f}s")


def mobile_mp4_durations(path: Path) -> dict[str, float]:
    """Video/audio durations without ffprobe (ISO-BMFF boxes)."""
    data = path.read_bytes()

    def boxes(start: int, end: int):
        i = start
        while i < end - 8:
            size = struct.unpack(">I", data[i:i + 4])[0]
            kind = data[i + 4:i + 8].decode("latin1")
            head = 8
            if size == 1:
                size = struct.unpack(">Q", data[i + 8:i + 16])[0]
                head = 16
            if size < 8:
                break
            yield kind, i, size, head
            i += size

    moov = next(b for b in boxes(0, len(data)) if b[0] == "moov")
    out = {}
    for kind, off, size, _ in boxes(moov[1] + 8, moov[1] + moov[2]):
        if kind != "trak":
            continue
        mdia = next(b for b in boxes(off + 8, off + size) if b[0] == "mdia")

        def child(want):
            return next(b for b in boxes(mdia[1] + 8, mdia[1] + mdia[2]) if b[0] == want)

        hdlr, mdhd = child("hdlr"), child("mdhd")
        track = data[hdlr[1] + 16:hdlr[1] + 20].decode()
        version = data[mdhd[1] + 8]
        if version == 0:
            timescale, duration = struct.unpack(">II", data[mdhd[1] + 20:mdhd[1] + 28])
        else:
            timescale = struct.unpack(">I", data[mdhd[1] + 28:mdhd[1] + 32])[0]
            duration = struct.unpack(">Q", data[mdhd[1] + 32:mdhd[1] + 40])[0]
        out[track] = round(duration / timescale, 3) if timescale else 0.0
    return out


def make_srt(episode: dict, timing: dict, align: Path, at: float, srt: Path,
             rendered: int | None = None) -> None:
    shots = episode["shots"]
    cuts = timing.get("cuts") or []
    n = rendered or (len(cuts) - 1 if cuts else len(shots))
    shots = shots[:max(1, n)]
    if timing.get("fixed"):
        cues = []
        for i, shot in enumerate(shots):
            line = str(shot.get("vo", "")).strip()
            if not line:
                continue
            start = float(shot.get("vo_start") or (cuts[i] / 30 if i < len(cuts) else 0))
            end = start + min(4.5, max(1.2, len(line) / 3.2))
            if i + 1 < len(cuts):
                end = min(end, cuts[i + 1] / 30 - .06)
            cues.append((start, max(start + .5, end), line))
        _write_srt(cues, srt)
        return
    vo = [str(s.get("vo", "")).strip() for s in shots]
    words = []
    if align.exists():
        try:
            words = [(float(a[1]) + at, float(a[2]) + at)
                     for a in json.loads(align.read_text(encoding="utf8"))]
        except (ValueError, TypeError, IndexError):
            words = []
    counts = [max(1, len(re.findall(r"[A-Za-z0-9']+", line))) for line in vo]
    total = sum(counts)
    cues = []
    if words and len(words) >= total * .9:
        cum = 0
        for i, n in enumerate(counts):
            frac = cum / total
            idx = min(len(words) - 1, int(round(frac * len(words))))
            nxt = min(len(words), idx + max(1, int(round(n / total * len(words)))))
            start = words[idx][0]
            end = words[min(nxt, len(words)) - 1][1]
            if cuts and i + 1 < len(cuts):
                end = min(end, cuts[i + 1] / 30 - .06)
            cues.append((start, max(start + .4, end), vo[i]))
            cum += n
    else:
        for i, line in enumerate(vo):
            start = cuts[i] / 30 if i < len(cuts) else at
            end = cuts[i + 1] / 30 - .06 if i + 1 < len(cuts) else start + 3
            cues.append((start, end, line))

    _write_srt(cues, srt)


def _write_srt(cues: list[tuple[float, float, str]], srt: Path) -> None:
    def stamp(t: float) -> str:
        h, rem = divmod(max(0.0, t), 3600)
        m, s = divmod(rem, 60)
        return f"{int(h):02d}:{int(m):02d}:{s:06.3f}".replace(".", ",")

    lines = []
    for n, (start, end, text) in enumerate(cues, 1):
        body, line = [], ""
        for w in text.split():
            if len(line) + len(w) + 1 > 42:
                body.append(line); line = w
            else:
                line = (line + " " + w).strip()
        if line:
            body.append(line)
        lines += [str(n), f"{stamp(start)} --> {stamp(end)}", *body, ""]
    srt.write_text("\n".join(lines), encoding="utf8")


def read_scenes(base: Path) -> dict:
    """Rendered shot list lives in the film.js SCENES payload."""
    path = base / "film" / "film.js"
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf8")
    marker = "const SCENES = "
    start = text.find(marker)
    if start < 0:
        return {}
    try:
        obj, _ = json.JSONDecoder().raw_decode(text[start + len(marker):])
        return obj if isinstance(obj, dict) else {}
    except ValueError:
        return {}


def package(base: Path, mp4: Path, episode_path: Path, speed: float,
            log: Path, vertical: bool = True) -> dict:
    episode = json.loads(episode_path.read_text(encoding="utf8"))
    timing_path = base / "film" / "timing.json"
    timing = json.loads(timing_path.read_text(encoding="utf8")) if timing_path.exists() else {}
    at = float(timing.get("at", .7))
    srt = base / f"{base.name}.srt"
    film = read_scenes(base)
    shots = film.get("shots") or episode.get("shots", [])
    cuts = timing.get("cuts") or []
    rendered = len(shots) if film else (len(cuts) - 1 if cuts else len(shots))
    make_srt(episode, timing, base / "film" / "align.json", at, srt, rendered)

    vert = base / f"{base.name}-vertical.mp4"
    if vertical:
        subprocess.run([PY, str(ROOT / "make_vertical.py"), str(mp4), str(vert)], check=True)
    durations = mobile_mp4_durations(mp4)
    video = durations.get("vide", 0.0)
    audio = durations.get("soun", 0.0)
    kinds = [s.get("kind", "") for s in shots]
    manifest = {
        "slug": base.name,
        "title": episode.get("episode", base.name),
        "logline": episode.get("logline", ""),
        "created": now(),
        "mp4": str(mp4.relative_to(ROOT)),
        "srt": str(srt.relative_to(ROOT)),
        "vertical": str(vert.relative_to(ROOT)) if vertical else "",
        "video_seconds": video,
        "audio_seconds": audio,
        "shots": len(shots),
        "kinds": kinds,
        "speed": speed,
        "one_take": bool(timing.get("one_take", True)),
        "bytes": mp4.stat().st_size,
    }
    (base / f"{base.name}.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf8")
    return manifest


def prune(keep: int, require_archived: bool) -> None:
    """Delete old finals, but never one whose manifest is not archived."""
    if keep < 1:
        return
    finals = sorted(OUT.glob("*/*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in finals[keep:]:
        folder = old.parent
        manifest_path = folder / f"{old.stem}.json"
        archived = False
        if manifest_path.exists():
            try:
                archived = bool(json.loads(manifest_path.read_text(encoding="utf8")).get("archive"))
            except ValueError:
                archived = False
        if require_archived and not archived:
            print(f"retention: keeping {old.name} (not archived yet)")
            continue
        old.unlink(missing_ok=True)
        if folder.is_dir():
            shutil.rmtree(folder, ignore_errors=True)
        print(f"retention: removed {old.name} and {folder.name}/")


def main() -> None:
    ap = argparse.ArgumentParser(description="Write, render, QA and package one episode.")
    ap.add_argument("topic", nargs="?", help="story seed for the writer")
    ap.add_argument("--episode", type=Path, help="use an existing episode JSON")
    ap.add_argument("--slug")
    ap.add_argument("--speed", type=float, default=.82)
    ap.add_argument("--max-seconds", type=float, default=None)
    ap.add_argument("--keep", type=int, default=3, help="finals to keep in out/episodes")
    ap.add_argument("--archive", default=os.environ.get("ARCHIVE_DIR"),
                    help="local folder or rsync:user@host:/path for finished episodes")
    ap.add_argument("--min-free-gb", type=float, default=.8)
    ap.add_argument("--render-timeout", type=float, default=3600)
    ap.add_argument("--no-vertical", action="store_true", help="skip the 9:16 cut")
    ap.add_argument("--force", action="store_true", help="redo every stage")
    ap.add_argument("--resume", action="store_true", help="keep finished stages (default)")
    o = ap.parse_args()
    if not o.topic and not o.episode:
        ap.error("give a topic or --episode")

    OUT.mkdir(parents=True, exist_ok=True)
    acquire_lock()
    guard(o.min_free_gb, "preflight")

    slug = o.slug or slugify(o.topic or o.episode.stem)
    base = OUT / slug
    base.mkdir(parents=True, exist_ok=True)
    state_path, state = base / "state.json", {}
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf8"))
    state.setdefault("stages", {})
    state.update({"slug": slug, "topic": o.topic or o.episode.stem, "updated": now()})
    state.setdefault("created", now())

    episode_path = (ROOT / o.episode) if o.episode else ROOT / "episodes" / f"{slug}.json"
    mp4 = base / f"{slug}.mp4"
    log_dir = base / "logs"

    def finish(stage: str, **extra) -> None:
        state["stages"][stage] = {"done": True, "at": now(), **extra}
        state_path.write_text(json.dumps(state, indent=2), encoding="utf8")

    def done(stage: str, artifact: Path | None = None) -> bool:
        return (not o.force and state["stages"].get(stage, {}).get("done")
                and (artifact is None or artifact.exists()))

    # ---- 1. write
    if o.episode:
        episode_path = (ROOT / o.episode).resolve()
        print(f"[write] using {episode_path.name}")
    elif done("write", episode_path):
        print(f"[write] cached {episode_path.name}")
    else:
        cmd = [PY, str(ROOT / "generate_story_director.py"), o.topic,
               "--out", str(episode_path)]
        run_stage("write", cmd, log_dir / "write.log", timeout=1200)
        finish("write")
    if not episode_path.exists():
        raise SystemExit(f"episode JSON missing: {episode_path}")

    # ---- 2. render
    if done("render", mp4):
        print(f"[render] cached {mp4.name}")
    else:
        guard(o.min_free_gb, "before render")
        cmd = [PY, str(ROOT / "make_horror_stickman.py"),
               "--episode", str(episode_path), "--out", str(mp4),
               "--work", str(base / "film"), "--speed", str(o.speed), "--force"]
        if o.max_seconds:
            cmd += ["--max-seconds", str(o.max_seconds)]
        run_stage("render", cmd, log_dir / "render.log", timeout=o.render_timeout)
        finish("render")
    if not mp4.exists():
        raise SystemExit(f"render finished without {mp4}")

    # ---- 3. QA
    durations = mobile_mp4_durations(mp4)
    video, audio = durations.get("vide", 0.0), durations.get("soun", 0.0)
    issues = []
    if video <= 1.0:
        issues.append("video track is missing or too short")
    if abs(video - audio) > .35:
        issues.append(f"audio/video drift {abs(video - audio):.3f}s")
    if mp4.stat().st_size < 500_000:
        issues.append("file smaller than 0.5 MB")
    qa = {"video_seconds": video, "audio_seconds": audio,
          "bytes": mp4.stat().st_size, "issues": issues}
    state["stages"]["qa"] = {"done": not issues, "at": now(), **qa}
    state_path.write_text(json.dumps(state, indent=2), encoding="utf8")
    if issues:
        raise SystemExit("QA failed: " + "; ".join(issues))
    print(f"[qa] {video:.2f}s video / {audio:.2f}s audio, ok")

    # ---- 4. package + retention
    guard(o.min_free_gb, "before packaging")
    manifest = package(base, mp4, episode_path, o.speed, log_dir / "render.log",
                       vertical=not o.no_vertical)
    finish("package", manifest=str(base / f"{slug}.json"))

    previous = state["stages"].get("archive", {})
    already = previous.get("done") and previous.get("dest") == o.archive
    if o.archive and not already:
        receipt = archive_files(base, o.archive)
        manifest["archive"] = receipt
        (base / f"{slug}.json").write_text(json.dumps(manifest, indent=2), encoding="utf8")
        finish("archive", **receipt)
        print(f"[archive] {receipt['mode']} -> {receipt['dest']}")
    elif o.archive:
        # Re-packaging rewrites the manifest: put the receipt back so retention
        # can still prove this final is safe to delete locally.
        receipt = {k: v for k, v in previous.items() if k not in ("done", "at")}
        manifest["archive"] = receipt
        (base / f"{slug}.json").write_text(json.dumps(manifest, indent=2), encoding="utf8")
        print(f"[archive] cached {o.archive}")

    prune(o.keep, require_archived=bool(o.archive))
    state.update({"mp4": str(mp4.relative_to(ROOT)), "duration": video})
    state_path.write_text(json.dumps(state, indent=2), encoding="utf8")

    with open(OUT / "runs.jsonl", "a") as fh:
        fh.write(json.dumps({"at": now(), "slug": slug, "mp4": manifest["mp4"],
                             "seconds": video, "bytes": manifest["bytes"],
                             "issues": 0}) + "\n")
    print(f"\nDONE {mp4} ({video:.1f}s, {manifest['bytes'] / 1e6:.1f} MB)")
    print(f"     captions {manifest['srt']}")
    print(f"     manifest {base / (slug + '.json')}")


if __name__ == "__main__":
    main()
