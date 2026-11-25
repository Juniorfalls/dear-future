#!/usr/bin/env python3
"""Fog Ridge -> stickman film.

Reads an episode schema (the same JSON the old AnimateDiff pipeline used),
writes an episode script, speaks it with the stickman skill's Kokoro voice,
renders the 2D stickman scenes with Playwright, mixes sound, and encodes an
MP4. Everything runs on CPU.

    python3 make_horror_stickman.py --max-seconds 15
    python3 make_horror_stickman.py --episode episodes/silence-on-the-fog-ridge.json
    python3 make_horror_stickman.py --shots 1-5 --max-seconds 15 --voice am_onyx

The skill is looked up in STICKMAN_SKILL_DIR, ./vendor/stickman-skill/skills/stickman,
and ~/.claude/skills/stickman, in that order. If it is missing, the vendor copy is
cloned from GitHub on first use.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "horror_stickman"
DEFAULT_EPISODE = ROOT / "episodes" / "silence-on-the-fog-ridge.json"
DEFAULT_OUT = ROOT / "out" / "stickman" / "silence-on-the-fog-ridge-test.mp4"
DEFAULT_WORK = ROOT / "out" / "stickman" / "film"
SKILL_REPO = "https://github.com/krishnagoswami52/stickman-skill.git"
FPS = 30

# ---------------------------------------------------------------- runtime


def _have_runtime() -> bool:
    try:
        import numpy  # noqa: F401
        import playwright  # noqa: F401
        import scipy  # noqa: F401
    except Exception:
        return False
    return True


def ensure_runtime() -> None:
    """Re-exec under the project venv when the caller used a bare system python."""
    if _have_runtime():
        return
    venv = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if venv.exists() and Path(sys.executable) != venv:
        os.execv(str(venv), [str(venv), str(Path(__file__).resolve()), *sys.argv[1:]])
    sys.exit(
        "stickman dependencies are missing. Run:\n"
        "  python3 -m venv .venv && .venv/bin/pip install -r requirements-stickman.txt\n"
        "  .venv/bin/python -m playwright install chromium"
    )


def find_skill(auto_clone: bool = True) -> Path:
    env = os.environ.get("STICKMAN_SKILL_DIR")
    candidates = [
        Path(env) if env else None,
        ROOT / "vendor" / "stickman-skill" / "skills" / "stickman",
        Path.home() / ".claude" / "skills" / "stickman",
        ROOT / "skills" / "stickman",
    ]
    for d in candidates:
        if d and (d / "scripts" / "build.py").exists():
            return d.resolve()
    if not auto_clone:
        raise SystemExit("stickman skill not found; set STICKMAN_SKILL_DIR")
    dest = ROOT / "vendor" / "stickman-skill"
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"cloning stickman-skill -> {dest}", flush=True)
    subprocess.run(["git", "clone", "--depth", "1", SKILL_REPO, str(dest)], check=True)
    shutil.rmtree(dest / ".git", ignore_errors=True)
    skill = dest / "skills" / "stickman"
    if not (skill / "scripts" / "build.py").exists():
        raise SystemExit("clone finished but skills/stickman is missing")
    return skill.resolve()


def check_browser() -> None:
    from playwright.sync_api import sync_playwright

    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            b.close()
        return
    except Exception as first:
        print("Chromium is not usable yet; installing the Playwright build", flush=True)
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=False)
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            b.close()
    except Exception as second:
        raise SystemExit(f"Chromium still cannot launch:\n{second}")


# ---------------------------------------------------------------- script


def load_episode(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"episode schema not found: {path}")
    data = json.loads(path.read_text(encoding="utf8"))
    if not data.get("shots"):
        raise SystemExit(f"{path} has no shots")
    return data


def parse_shot_selector(text: str | None, shots: list[dict]) -> list[dict]:
    if not text:
        return list(shots)
    wanted: set[int] = set()
    for part in text.replace(",", " ").split():
        if "-" in part:
            a, b = part.split("-", 1)
            wanted.update(range(int(a), int(b) + 1))
        else:
            wanted.add(int(part))
    picked = [s for s in shots if int(s.get("id", 0)) in wanted]
    if not picked:
        raise SystemExit(f"--shots {text!r} matched no shot ids")
    return picked


def estimate_seconds(shots: list[dict], speed: float) -> float:
    words = sum(len(re.findall(r"\w+", s.get("vo", ""))) for s in shots)
    return words / (2.6 * max(.7, speed)) + .45 * max(0, len(shots) - 1)


def choose_shots(shots: list[dict], max_seconds: float | None, speed: float) -> list[dict]:
    """Fit the opening shots inside the requested length, with room for lead-in/out."""
    if not max_seconds:
        return list(shots)
    budget = max_seconds - 1.4
    picked: list[dict] = []
    for shot in shots:
        trial = picked + [shot]
        if picked and estimate_seconds(trial, speed) > budget:
            break
        picked = trial
    return picked or shots[:1]


def classify(shot: dict) -> str:
    text = f"{shot.get('slug','')} {shot.get('prompt','')}".lower()
    slug = str(shot.get("slug", "")).lower()
    # Director Mode locations (rearview mirror, sign, cabin, road). Checked
    # before the Fog Ridge keywords so "hand on the wheel" is not the radio hand.
    if shot.get("shot_type") == "wide" and ("highway" in text or "road" in text):
        return "highway"
    if "rearview" in text or "rear-view" in text or "mirror" in text:
        return "rearview_mirror"
    if "do not stop" in text or "roadside sign" in text or (
            "rusted" in text and "sign" in text):
        return "roadside_sign"
    if any(k in text for k in ("steering", "dashboard", "windshield", "cabin",
                               "rear window", "glass shard", "shards", "shard",
                               "passenger seat", "door lock")):
        return "car_interior"
    if "highway" in text or "road" in text:
        return "highway"
    if "radio-screen" in slug or "hand-trembl" in slug:
        return "hand" if "hand" in slug or "trembl" in slug else "radio_insert"
    if "console" in slug:
        return "console"
    if "speak" in slug or "mic" in slug:
        return "speaks"
    if "whisper" in slug:
        return "whisper"
    if "beam" in slug:
        return "beam"
    if "storm" in slug:
        return "storm"
    if "fog" in slug:
        return "fog"
    if "captain" in slug:
        return "captain"
    if "final" in slug or "pulse" in slug:
        return "final"
    if slug.endswith("end") or slug == "end":
        return "end"
    if "opening" in slug:
        return "opening"
    # keyword fallback for other horror schemas
    if "radio" in text and ("close" in text or "insert" in text):
        return "radio_insert"
    if "lighthouse" in text and "wide" in text:
        return "storm"
    if "hand" in text:
        return "hand"
    if "silhouette" in text:
        return "fog"
    if "beam" in text:
        return "beam"
    if "storm" in text or "rain" in text:
        return "storm"
    if "fog" in text or "mist" in text:
        return "fog"
    if shot.get("shot_type") == "wide":
        return "end"
    return "console"


def write_voice_script(shots: list[dict], path: Path, one_take: bool = False) -> None:
    blocks = []
    for shot in shots:
        vo = str(shot.get("vo", "")).strip()
        if vo:
            blocks.append(vo)
    if not blocks:
        raise SystemExit("the selected shots have no voiceover lines")
    if one_take:
        # A single spoken paragraph: one line, one Kokoro call, so sentence
        # pitch and breathing carry across beats. "..." would be parsed as a
        # line break by tts.py and reintroduce per-sentence synthesis.
        para = " ".join(" ".join(b.split()) for b in blocks)
        path.write_text(para + "\n", encoding="utf8")
    else:
        path.write_text("\n\n".join(blocks) + "\n", encoding="utf8")


def _tokens(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9']+", text.lower()) if w]


def _silence_gaps(wav_path: Path) -> list[float]:
    """Start time of quiet runs (>=120 ms) in the narration, in seconds."""
    import wave

    import numpy as np

    try:
        with wave.open(str(wav_path), "rb") as w:
            sr = w.getframerate()
            raw = w.readframes(w.getnframes())
    except (OSError, wave.Error):
        return []
    a = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32767
    if not len(a):
        return []
    win = max(1, int(.01 * sr))
    n = len(a) // win
    rms = np.sqrt((a[: n * win].reshape(n, win) ** 2).mean(axis=1) + 1e-12)
    quiet = rms < .012
    gaps, run = [], 0
    for i, q in enumerate(quiet):
        if q:
            run += 1
        else:
            if run * win / sr >= .12:
                gaps.append((i - run) * win / sr)
            run = 0
    if run * win / sr >= .12:
        gaps.append((len(quiet) - run) * win / sr)
    return gaps


def one_take_cuts(work: Path, shots: list[dict], at: float,
                  max_seconds: float | None) -> tuple[list[int], str]:
    """Cut times from the single narration take, using word timestamps."""
    import wave

    with wave.open(str(work / "vo.wav"), "rb") as w:
        voice_dur = w.getnframes() / float(w.getframerate())

    beat_tokens = [_tokens(str(s.get("vo", ""))) for s in shots]
    word_counts = [max(1, len(b)) for b in beat_tokens]
    # Time of the first word of every beat, in vo.wav time.
    starts = [0.0]
    method = "proportional"
    align_path = work / "align.json"
    aligned: list[tuple[str, float, float]] = []
    if align_path.exists():
        try:
            aligned = [(str(a[0]).lower(), float(a[1]), float(a[2]))
                       for a in json.loads(align_path.read_text(encoding="utf8"))]
        except (ValueError, TypeError, IndexError):
            aligned = []
    total_words = sum(word_counts)
    if aligned and len(aligned) >= total_words * .9:
        # Word counts can differ when the aligner splits contractions; walk the
        # aligned list at the same fraction instead of requiring an exact match.
        cum = 0
        for n in word_counts[:-1]:
            cum += n
            frac = cum / total_words
            idx = min(len(aligned) - 1, int(round(frac * len(aligned))))
            starts.append(max(starts[-1] + .05, aligned[idx][1]))
        method = "aligned"
    else:
        cum = 0
        for n in word_counts[:-1]:
            cum += n
            starts.append(voice_dur * cum / total_words)
        # Snap each estimate to the nearest real pause in the take, so a beat
        # change lands in silence rather than mid-word.
        gaps = _silence_gaps(work / "vo.wav")
        if gaps:
            snapped = []
            for s in starts[1:]:
                near = min(gaps, key=lambda g: abs(g - s))
                snapped.append(near if abs(near - s) <= 1.2 else s)
            for i in range(1, len(snapped)):
                snapped[i] = max(snapped[i], snapped[i - 1] + .3)
            starts = [0.0] + snapped
            method = "silence"

    cuts = [0]
    for i in range(1, len(shots)):
        # Change picture a hair before the beat's first word.
        t = at + max(0.0, starts[i] - .10)
        cuts.append(max(cuts[-1] + FPS // 2, int(round(t * FPS))))
    end = at + voice_dur + .95
    if max_seconds and end > max_seconds + .05:
        end = max_seconds
    cuts.append(max(cuts[-1] + FPS // 2, int(round(end * FPS))))
    return cuts, method


# ---------------------------------------------------------------- film


def write_film_js(work: Path, scenes: dict) -> None:
    body = (ASSETS / "film_body.js").read_text(encoding="utf8")
    payload = json.dumps(scenes, ensure_ascii=False, indent=1)
    (work / "film.js").write_text(f"const SCENES = {payload};\n\n{body}", encoding="utf8")


def write_audio_mix(work: Path, at: float, voice: bool,
                    voice_file: str = "vo.wav") -> None:
    voice_value = f'"{voice_file}"' if voice else "None"
    text = f'''"""Sound mix for the Fog Ridge stickman film. Generated by make_horror_stickman.py."""
import json, os, sys
sys.path.insert(0, os.environ["STICKMAN_SCRIPTS"])
from audio_kit import Mix

info = json.load(open("film.json"))
D = info["dur"]
m = Mix(D, seed=13)

m.room_bed([(0, .55), (D * .55, .48), (D, .30)])
m.wind_bed([(0, .20), (D * .35, .34), (D * .72, .46), (D, .22)])
m.rain_bed([(0, .22), (D * .45, .34), (D * .8, .42), (D, .18)])
m.drone([(0, .10), (D * .3, .28), (D * .7, .46), (D, .18)])

for e in info["events"]:
    t, k = e["t"], e["k"]
    if k == "radio":
        m.sfx("metallatch", t, .62, 2600, .22, -.15, .42)
        m.nb(t + .03, 900, 3600, .10, .004, .08, .05, -.15)
    elif k == "signal":
        m.tick(t, .05, -.25)
        m.tick(t + .34, .035, .2)
    elif k == "thunder":
        m.thunder(t, .34, -.2)
    elif k == "wind":
        m.whoosh(t, -.2, 1.3, .16)
    elif k == "heart":
        m.heart(t, .34)

m.music(mood="tense", bpm=60, gain=.9)
if {voice_value}:
    m.voice("{voice_file}", at={at:.3f}, gain_db=-2.5)
m.write("audio.wav")
'''
    (work / "audio_mix.py").write_text(text, encoding="utf8")


def event_list(shots: list[dict], cuts: list[int]) -> list[dict]:
    events = []
    for i, shot in enumerate(shots):
        start = cuts[i] / FPS
        end = cuts[i + 1] / FPS
        kind = shot["kind"]
        if kind in {"opening", "console", "speaks", "final", "radio_insert", "hand"}:
            events.append({"t": round(start + .38, 3), "k": "signal" if kind in {"radio_insert", "final"} else "radio"})
        else:
            events.append({"t": round(start + .30, 3), "k": "wind"})
        if kind == "storm":
            events.append({"t": round(start + .9, 3), "k": "thunder"})
        if kind == "end":
            events.append({"t": round(max(start, end - 1.2), 3), "k": "heart"})
    return events


def voice_groups(work: Path, n_shots: int) -> list[list[dict]]:
    rows = json.loads((work / "vo_lines.json").read_text(encoding="utf8"))
    groups: dict[int, list[dict]] = {}
    for row in rows:
        groups.setdefault(int(row["beat"]), []).append(row)
    ordered = [groups[b] for b in sorted(groups)]
    if len(ordered) != n_shots:
        raise SystemExit(f"voice has {len(ordered)} beats but {n_shots} shots were selected")
    return ordered


def timeline(groups: list[list[dict]], at: float, max_seconds: float | None) -> list[int]:
    ends = []
    for i, group in enumerate(groups):
        hold = .30 if i < len(groups) - 1 else .95
        ends.append(at + float(group[-1]["end"]) + hold)
    natural = ends[-1]
    if max_seconds:
        if natural < max_seconds:
            ends[-1] += max_seconds - natural
        else:
            # Keep the whole last line and shorten its tail to hit the target.
            voice_end = at + float(groups[-1][-1]["end"])
            if max_seconds >= voice_end + .06:
                ends[-1] = max_seconds
    cuts = [0]
    for seconds in ends:
        frame = int(round(seconds * FPS))
        cuts.append(max(cuts[-1] + FPS // 2, frame))
    return cuts


def prepare_work(work: Path, skill: Path, force: bool) -> None:
    if force and work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True, exist_ok=True)
    # Keep the engine files; only film.js and audio_mix.py are ours.
    shutil.copytree(skill / "engine", work, dirs_exist_ok=True)


def run_tts(skill: Path, work: Path, voice: str, speed: float) -> None:
    cmd = [
        sys.executable,
        str(skill / "scripts" / "tts.py"),
        str(work),
        str(work / "script.txt"),
        "--voice",
        voice,
        "--speed",
        str(speed),
    ]
    subprocess.run(cmd, check=True)


def run_one_take(work: Path, voice: str, speed: float) -> None:
    """One Kokoro call for the whole monologue (see one_take_tts.py)."""
    cmd = [
        sys.executable,
        str(ROOT / "one_take_tts.py"),
        str(work),
        str(work / "script.txt"),
        "--voice",
        voice,
        "--speed",
        str(speed),
    ]
    subprocess.run(cmd, check=True)


def build_film(skill: Path, work: Path, out: Path, crf: int) -> None:
    # Encode inside the film folder: the skill's audit resolves the output by
    # basename, so an external absolute path would not be audited.
    local = work / "final.mp4"
    local.unlink(missing_ok=True)
    cmd = [
        sys.executable,
        str(skill / "scripts" / "build.py"),
        str(work),
        "--out",
        local.name,
        "--crf",
        str(crf),
    ]
    subprocess.run(cmd, check=True)
    if not local.exists():
        raise SystemExit(f"build finished but {local} is missing")
    shutil.move(str(local), str(out))


def stills(skill: Path, work: Path, out: Path, times: str) -> None:
    cmd = [sys.executable, str(skill / "scripts" / "stills.py"), str(work), str(out), *times.replace(",", " ").split()]
    subprocess.run(cmd, check=True)


# ---------------------------------------------------------------- main


def main() -> None:
    ensure_runtime()
    ap = argparse.ArgumentParser(description="Render a Fog Ridge episode as a stickman film.")
    ap.add_argument("--episode", type=Path, default=DEFAULT_EPISODE)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--work", type=Path, default=DEFAULT_WORK)
    ap.add_argument("--shots", help='shot ids, e.g. "1-5" or "1,2,3"; default fits --max-seconds')
    ap.add_argument("--max-seconds", type=float, default=None, help="target length; 15 for the test")
    ap.add_argument("--voice", default="am_onyx", help="Kokoro voice (am_onyx is the dark narrator)")
    ap.add_argument("--speed", type=float, default=.88)
    ap.add_argument("--crf", type=int, default=22)
    ap.add_argument("--force", action="store_true", help="delete the work folder first")
    ap.add_argument("--line-by-line", action="store_true",
                    help="old behaviour: speak each beat separately (default is one take)")
    ap.add_argument("--no-voice", action="store_true", help="render picture and effects only")
    ap.add_argument("--dry-run", action="store_true", help="write the film folder but do not render")
    ap.add_argument("--stills", help="comma list of times for a contact sheet after setup")
    o = ap.parse_args()

    episode = load_episode(o.episode.resolve())
    skill = find_skill()
    check_browser()
    print(f"episode: {episode.get('episode', o.episode.name)}")
    print(f"skill:   {skill}")

    shots = parse_shot_selector(o.shots, episode["shots"])
    if not o.shots:
        shots = choose_shots(shots, o.max_seconds, o.speed)
    shots = [dict(s, kind=classify(s)) for s in shots]
    print("shots:   " + ", ".join(f"{s['id']}:{s['slug']} ({s['kind']})" for s in shots))

    work = o.work.resolve()
    prepare_work(work, skill, o.force)
    at = .70

    one_take = not o.line_by_line
    if not o.no_voice:
        groups = []
        if one_take:
            # The whole monologue is spoken once; shot boundaries come from
            # word timestamps inside that single take.
            for attempt in range(2):
                write_voice_script(shots, work / "script.txt", one_take=True)
                run_one_take(work, o.voice, o.speed)
                cuts, method = one_take_cuts(work, shots, at, o.max_seconds)
                natural = cuts[-1] / FPS
                if (not o.max_seconds or natural <= o.max_seconds + .3
                        or len(shots) == 1):
                    break
                print(f"voice runs {natural:.1f}s; dropping shot {shots[-1]['id']} "
                      f"to fit {o.max_seconds:.0f}s")
                shots = shots[:-1]
            shutil.copyfile(work / "vo.wav", work / "narration_full.wav")
            print(f"one take: {natural:.1f}s, {len(shots)} beats, cuts from {method} timings")
        else:
            # If the actual voice runs long, drop the last shot and speak the
            # shorter script again. Every spoken line is cached, so retry is cheap.
            for attempt in range(3):
                write_voice_script(shots, work / "script.txt")
                run_tts(skill, work, o.voice, o.speed)
                groups = voice_groups(work, len(shots))
                natural = at + float(groups[-1][-1]["end"]) + .95
                if not o.max_seconds or natural <= o.max_seconds + 1.5 or len(shots) == 1:
                    break
                print(f"voice runs {natural:.1f}s; dropping shot {shots[-1]['id']} to fit {o.max_seconds:.0f}s")
                shots = shots[:-1]
            groups = voice_groups(work, len(shots))
            # Pull the lead-in tighter when the spoken take is already longer than
            # the target; the alternative is cutting narration off mid-line.
            if o.max_seconds:
                last_end = float(groups[-1][-1]["end"])
                at = min(at, max(.15, o.max_seconds - (last_end + .15)))
            cuts = timeline(groups, at, o.max_seconds)
    else:
        groups = []
        # picture-only fallback: about 2.6 s per shot
        cuts = [0]
        for _ in shots:
            cuts.append(cuts[-1] + int(2.6 * FPS))
        write_voice_script(shots, work / "script.txt")

    dur = cuts[-1] / FPS
    scenes = {
        "dur": dur,
        "cuts": cuts,
        "shots": [
            {
                "slug": s.get("slug", f"shot-{s.get('id', i + 1)}"),
                "kind": s.get("kind", "console"),
                "title": s.get("title", ""),
                "shot_type": s.get("shot_type", ""),
                "focus": s.get("focus", ""),
                "variant": (
                    "radio" if "radio" in str(s.get("prompt", "")).lower()
                    else "paint" if "paint" in str(s.get("prompt", "")).lower()
                    else ""
                ),
            }
            for i, s in enumerate(shots)
        ],
        "events": event_list(shots, cuts),
    }
    write_film_js(work, scenes)
    write_audio_mix(work, at, not o.no_voice,
                    "narration_full.wav" if one_take and not o.no_voice else "vo.wav")
    if groups or one_take:
        (work / "timing.json").write_text(
            json.dumps({"at": at, "cuts": cuts, "groups": groups,
                        "one_take": one_take}, indent=1), encoding="utf8"
        )
    print(f"film:    {dur:.2f}s, {len(shots)} shots, {len(cuts) - 1} cuts -> {work}")
    if o.dry_run:
        print("dry run: film folder written, not rendered")
        return
    if o.stills:
        stills(skill, work, work / "contact_sheet.jpg", o.stills)
    o.out.parent.mkdir(parents=True, exist_ok=True)
    build_film(skill, work, o.out.resolve(), o.crf)
    if not o.out.exists():
        raise SystemExit(f"build finished but {o.out} is missing")
    size = o.out.stat().st_size / 1e6
    print(f"\nREADY {o.out} ({size:.1f} MB, {dur:.1f}s)")


if __name__ == "__main__":
    main()
