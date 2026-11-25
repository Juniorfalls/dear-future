#!/usr/bin/env python3
"""FIFO worker for make_episode.py.

    python3 run_queue.py --once          # drain pending topics (cron-friendly)
    python3 run_queue.py --limit 1       # one episode per invocation

topics.txt holds one seed per line; blank lines and # comments are ignored.
State lives in out/queue_state.json, so re-running is safe: finished topics are
skipped, failed ones stop after --max-attempts. The queue takes its own lock so
two workers cannot overlap, and it stops early if disk falls below --min-free-gb.

    a night bus that stops where no bus stop exists
    the motel key that opens the wrong room
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from make_episode import slugify

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
TOPICS = ROOT / "topics.txt"
STATE = OUT / "queue_state.json"
Q_LOCK = OUT / ".queue.lock"
PY = str(ROOT / ".venv" / "bin" / "python")


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def free_gb() -> float:
    return shutil.disk_usage(ROOT).free / 1e9


def load_state() -> dict:
    if STATE.exists():
        try:
            return json.loads(STATE.read_text(encoding="utf8"))
        except ValueError:
            pass
    return {"topics": []}


def save(state: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=2), encoding="utf8")


def acquire() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fd = open(Q_LOCK, "w")
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit("another queue worker is running (out/.queue.lock)")
    fd.write(str(int(time.time())))
    fd.flush()


def log(line: str) -> None:
    stamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{stamp}] {line}", flush=True)
    with open(OUT / "queue.log", "a") as fh:
        fh.write(f"{now()} {line}\n")


def main() -> None:
    ap = argparse.ArgumentParser(description="Drain topics.txt through make_episode.py")
    ap.add_argument("--queue", type=Path, default=TOPICS)
    ap.add_argument("--limit", type=int, default=0, help="max episodes this run (0 = all)")
    ap.add_argument("--max-attempts", type=int, default=3)
    ap.add_argument("--max-seconds", type=float, default=None)
    ap.add_argument("--speed", type=float, default=.82)
    ap.add_argument("--keep", type=int, default=3)
    ap.add_argument("--min-free-gb", type=float, default=.8)
    ap.add_argument("--archive", default=os.environ.get("ARCHIVE_DIR"),
                    help="local folder or rsync:user@host:/path")
    ap.add_argument("--retry-failed", action="store_true")
    o = ap.parse_args()

    acquire()
    state = load_state()
    by_topic = {t["topic"]: t for t in state["topics"]}
    lines = [ln.strip() for ln in o.queue.read_text(encoding="utf8").splitlines()
             if ln.strip() and not ln.strip().startswith("#")]
    for topic in lines:
        if topic not in by_topic:
            row = {"topic": topic, "slug": slugify(topic), "status": "pending",
                   "attempts": 0, "at": None}
            state["topics"].append(row); by_topic[topic] = row
    if o.retry_failed:
        for row in state["topics"]:
            if row["status"] == "failed" and row["attempts"] < o.max_attempts:
                row["status"] = "pending"
    save(state)

    done = 0
    for row in state["topics"]:
        if o.limit and done >= o.limit:
            break
        if row["status"] != "pending":
            continue
        if free_gb() < o.min_free_gb:
            log(f"stop: {free_gb():.2f} GB free, below {o.min_free_gb:.2f} GB")
            break
        slug = row["slug"]
        log(f"start {slug} (attempt {row['attempts'] + 1})")
        cmd = [PY, str(ROOT / "make_episode.py"), row["topic"],
               "--slug", slug, "--speed", str(o.speed), "--keep", str(o.keep),
               "--min-free-gb", str(o.min_free_gb)]
        if o.max_seconds:
            cmd += ["--max-seconds", str(o.max_seconds)]
        if o.archive:
            cmd += ["--archive", o.archive]
        try:
            p = subprocess.run(cmd, cwd=ROOT)
            ok = p.returncode == 0
            error = "" if ok else f"exit {p.returncode}"
        except Exception as exc:  # noqa: BLE001 - a queue must keep going
            ok, error = False, str(exc)
        row["attempts"] += 1
        row["at"] = now()
        if ok:
            row["status"] = "done"
            row["error"] = ""
            done += 1
            log(f"done {slug}")
        else:
            row["status"] = "pending" if row["attempts"] < o.max_attempts else "failed"
            row["error"] = error
            log(f"failed {slug}: {error} ({row['attempts']}/{o.max_attempts})")
        save(state)

    pending = sum(1 for r in state["topics"] if r["status"] == "pending")
    failed = sum(1 for r in state["topics"] if r["status"] == "failed")
    log(f"queue: {done} done this run, {pending} pending, {failed} failed")


if __name__ == "__main__":
    main()
