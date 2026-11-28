#!/usr/bin/env python3
"""generate_voiceover.py — Kokoro-82M narration with word-accurate timings.

Replaces the old edge-tts `make_voice.py` / `make_beat.py` scripts. For one
episode JSON it:

  1. speaks the episode `script` with the local Kokoro-82M model
     (`kokoro-tts-tool`, voices af_heart / am_adam / bm_george / ...);
  2. loudness-normalizes the take to -16 LUFS and writes the mp3 the Remotion
     composition plays;
  3. aligns the words on the *final* mp3 (faster-whisper) and writes
     `vo_words.json` — the karaoke captions and every reveal in
     AnimalDocumentary.tsx are timed from this file;
  4. resolves the episode `cues` against those word times and rewrites
     `timeline` in the episode JSON.

Usage
-----
    .venv-voice/bin/python scripts/generate_voiceover.py                 # animal.json
    .venv-voice/bin/python scripts/generate_voiceover.py --voice am_adam
    .venv-voice/bin/python scripts/generate_voiceover.py --speed 1.05 --align estimate
    .venv-voice/bin/python scripts/generate_voiceover.py --episode remotion/public/animal.json

Without faster-whisper (`--align estimate`) word times are interpolated across
the take, which is fine for a draft and ±200 ms rough for a final.
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

ROOT = Path(__file__).resolve().parent.parent
VENV = ROOT / ".venv-voice"
KOKORO = VENV / "bin" / "kokoro-tts-tool"
PUBLIC = ROOT / "remotion" / "public"
DEFAULT_EPISODE = PUBLIC / "animal.json"

# Remotion ships its own ffmpeg/ffprobe build, which is enough for loudness
# normalization and duration probes. Prefer a system ffmpeg, fall back to it.
COMPOSITOR = ROOT / "remotion" / "node_modules" / "@remotion" / "compositor-linux-x64-gnu"

# The two voices the channel standardizes on.
VOICES = {"female": "af_heart", "male": "am_adam"}


def log(msg: str) -> None:
    print(f"[voice] {msg}", flush=True)


def die(msg: str, code: int = 1) -> None:
    print(f"[voice] ERROR: {msg}", file=sys.stderr, flush=True)
    sys.exit(code)


def norm(token: str) -> str:
    return re.sub(r"[^a-z0-9']", "", token.lower())


# faster-whisper returns digits where the script has number words, so cues are
# matched against a number-expanded token list.
_ONES = "zero one two three four five six seven eight nine ten eleven twelve " \
        "thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
_TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()


def number_words(token: str) -> list[str]:
    if not token.isdigit():
        return [token]
    n = int(token)
    if n < 20:
        return [_ONES[n]]
    if n < 100:
        tens, ones = divmod(n, 10)
        return [_TENS[tens]] + ([_ONES[ones]] if ones else [])
    if n < 1000:
        hundreds, rest = divmod(n, 100)
        out = [_ONES[hundreds], "hundred"] + (number_words(str(rest)) if rest else [])
        return out
    return [norm(c) for c in token]


def _ff_tool(name: str) -> str:
    env = os.environ.get(name.upper())
    if env and (shutil.which(env) or Path(env).exists()):
        return env
    found = shutil.which(name)
    if found:
        return found
    bundled = COMPOSITOR / name
    if bundled.exists():
        return str(bundled)
    die(f"{name} not found; set {name.upper()}=/path/to/{name} or install ffmpeg")
    raise SystemExit(1)


def ff(args: list[str]) -> subprocess.CompletedProcess:
    """Run ffmpeg/ffprobe, wiring LD_LIBRARY_PATH for Remotion's bundled build."""
    tool = _ff_tool(args[0])
    env = dict(os.environ)
    if str(COMPOSITOR) in tool:
        env["LD_LIBRARY_PATH"] = str(COMPOSITOR) + (
            ":" + env["LD_LIBRARY_PATH"] if env.get("LD_LIBRARY_PATH") else ""
        )
    return subprocess.run([tool, *args[1:]], env=env, capture_output=True, text=True)


# --------------------------------------------------------------------------- #
# 1. narration
# --------------------------------------------------------------------------- #
def speak(text: str, wav: Path, voice: str, speed: float) -> None:
    if not KOKORO.exists():
        die(f"{KOKORO} missing — run scripts/install_kokoro.sh")
    wav.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [str(KOKORO), "say", "--text", text, "--voice", voice,
         "--speed", str(speed), "--out", str(wav)],
        check=True,
    )


def normalize(wav: Path, mp3: Path) -> None:
    proc = ff(["ffmpeg", "-y", "-v", "error", "-i", str(wav), "-af",
               "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "48000", "-b:a", "192k", str(mp3)])
    if proc.returncode != 0:
        die(f"loudness normalization failed: {proc.stderr.strip()[:400]}")


# --------------------------------------------------------------------------- #
# 2. word alignment
# --------------------------------------------------------------------------- #
def align_whisper(mp3: Path, model_name: str) -> list[dict] | None:
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        log("faster-whisper not installed — falling back to estimated timings")
        return None
    log(f"aligning with faster-whisper {model_name} (downloads once)")
    try:
        model = WhisperModel(model_name, device="cpu", compute_type="int8")
        segments, _ = model.transcribe(
            str(mp3), language="en", word_timestamps=True, vad_filter=False,
            beam_size=1, condition_on_previous_text=False,
        )
        words: list[dict] = []
        for seg in segments:
            for w in seg.words or []:
                token = w.word.strip()
                if not token:
                    continue
                words.append({"word": token, "start": round(w.start, 3),
                              "end": round(w.end, 3)})
        return words or None
    except Exception as exc:  # model download / runtime failure
        log(f"whisper alignment failed ({exc.__class__.__name__}: {exc}) — estimating")
        return None


def align_estimate(script: str, duration: float) -> list[dict]:
    """Interpolate word times by length. Fallback only."""
    tokens = [t for t in re.split(r"\s+", script.strip()) if t]
    weights = [max(2, len(norm(t)) + 1) for t in tokens]
    total = sum(weights)
    t, out = 0.06, []
    for token, weight in zip(tokens, weights):
        span = (duration - 0.12) * weight / total
        out.append({"word": token, "start": round(t, 3), "end": round(t + span, 3)})
        t += span
    return out


def media_duration(path: Path) -> float:
    proc = ff(["ffprobe", "-v", "error", "-show_entries", "format=duration",
               "-of", "default=nw=1:nk=1", str(path)])
    if proc.returncode != 0 or not proc.stdout.strip():
        die(f"could not read duration of {path.name}: {proc.stderr.strip()[:300]}")
    return float(proc.stdout.strip())


# --------------------------------------------------------------------------- #
# 3. cues -> timeline
# --------------------------------------------------------------------------- #
def find_phrase(words: list[dict], phrase: list[str], after: float = 0.0) -> float | None:
    """Start time of the first spoken occurrence of `phrase` after `after`."""
    tokens: list[str] = []
    starts: list[float] = []
    for w in words:
        for t in number_words(norm(w["word"])):
            tokens.append(t)
            starts.append(w["start"])
    target = [norm(p) for p in phrase]
    for i in range(len(tokens)):
        if starts[i] < after:
            continue
        if all(i + k < len(tokens) and tokens[i + k] == target[k] for k in range(len(target))):
            return starts[i]
    return None


def resolve_timeline(episode: dict, words: list[dict]) -> dict:
    cues = episode.get("cues") or {}
    lead = float(episode.get("cueLead", 0.28))
    timeline: dict[str, float] = {}
    for key, phrase in cues.items():
        at = find_phrase(words, phrase)
        if at is None:
            log(f"cue {key!r} not found ({' '.join(phrase)}) — keeping previous value")
            timeline[key] = float(episode.get("timeline", {}).get(key, 0))
        else:
            timeline[key] = round(max(0.0, at - (0.0 if key == "titleAt" else lead)), 3)
    return timeline


# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Kokoro narration + word timings")
    p.add_argument("--episode", default=str(DEFAULT_EPISODE))
    p.add_argument("--voice", default=os.environ.get("KOKORO_VOICE", VOICES["female"]),
                   help="af_heart (female), am_adam (male), bm_george, ...")
    p.add_argument("--speed", type=float, default=1.0)
    p.add_argument("--script", default="", help="override the episode script")
    p.add_argument("--align", choices=["auto", "whisper", "estimate"], default="auto")
    p.add_argument("--align-model", default="base.en")
    p.add_argument("--no-normalize", action="store_true")
    args = p.parse_args(argv)

    episode_path = Path(args.episode).resolve()
    if not episode_path.exists():
        die(f"missing episode {episode_path}")
    episode = json.loads(episode_path.read_text())
    script = args.script or episode.get("script", "")
    if not script:
        die("episode has no script — run generate_animal_script.py first")
    public = episode_path.parent

    audio_name = episode.get("audio") or "vo.wav"
    mp3 = public / audio_name
    wav = public / "vo_take.wav"

    log(f"speaking {len(script.split())} words as {args.voice} @ {args.speed}x")
    speak(script, wav, args.voice, args.speed)
    if args.no_normalize:
        shutil.copy(wav, mp3)
    else:
        normalize(wav, mp3)
        wav.unlink(missing_ok=True)

    duration = media_duration(mp3)
    words = None
    if args.align in ("auto", "whisper"):
        words = align_whisper(mp3, args.align_model)
    if not words:
        if args.align == "whisper":
            die("whisper alignment requested but unavailable")
        words = align_estimate(script, duration)
    voice_end = words[-1]["end"]
    log(f"{len(words)} words, voice ends at {voice_end:.2f}s of {duration:.2f}s")

    words_path = public / "vo_words.json"
    words_path.write_text(json.dumps(words, indent=1) + "\n")

    timeline = resolve_timeline(episode, words)
    episode["timeline"] = timeline
    episode["voiceEnd"] = round(voice_end, 3)
    episode["audio"] = audio_name
    episode["voice"] = args.voice
    # A 15 s slot is the minimum; never cut the narration short.
    episode["duration"] = round(max(float(episode.get("duration", 15)), voice_end + 0.9), 2)
    episode_path.write_text(json.dumps(episode, indent=2, ensure_ascii=False) + "\n")
    log(f"timeline {timeline}")
    log(f"wrote {words_path.name}, {mp3.name}, {episode_path.name} ({episode['duration']}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
