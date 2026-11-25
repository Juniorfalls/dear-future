#!/usr/bin/env python3
"""Ship a finished episode off the box, then prove it arrived.

dest is either a local directory or an rsync target written as
  rsync:user@host:/srv/stickman
Local copies are verified with SHA-256; remote copies trust rsync's exit code
and the remote is recorded so a later audit can check it.

usage: archive_kit.py <episode-folder> <dest>
"""
from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def archive(folder: Path, dest: str) -> dict:
    """Copy <slug>.mp4/.srt/.json to dest/<slug>/ and return a receipt."""
    folder = folder.resolve()
    slug = folder.name
    files = [folder / f"{slug}.mp4", folder / f"{slug}.srt", folder / f"{slug}.json"]
    files = [f for f in files if f.exists()]
    if not files:
        raise SystemExit(f"nothing to archive in {folder}")

    if dest.startswith("rsync:"):
        target = dest[len("rsync:"):].rstrip("/") + f"/{slug}/"
        if not shutil.which("rsync"):
            raise SystemExit("rsync is not installed")
        subprocess.run(["rsync", "-a", "--partial", *map(str, files), target], check=True)
        return {"mode": "rsync", "dest": target, "files": [f.name for f in files],
                "sha256": {f.name: sha256(f) for f in files}}

    out = Path(dest).expanduser().resolve() / slug
    out.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for src in files:
        dst = out / src.name
        shutil.copyfile(src, dst)
        want, got = sha256(src), sha256(dst)
        if want != got:
            raise SystemExit(f"archive verification failed for {src.name}")
        hashes[src.name] = got
    return {"mode": "local", "dest": str(out), "files": [f.name for f in files],
            "sha256": hashes}


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    print(archive(Path(sys.argv[1]), sys.argv[2]))
