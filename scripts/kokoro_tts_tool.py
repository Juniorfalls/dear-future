#!/usr/bin/env python3
"""kokoro-tts-tool — local Kokoro-82M text-to-speech CLI.

`kokoro-tts-tool` does not exist on PyPI, so this is the project's own
implementation of the same idea, built on `kokoro-onnx` (the official
Kokoro-82M v1.0 ONNX export).  The command surface matches what the pipeline
expects:

    kokoro-tts-tool init                       # download the 82M model + voices
    kokoro-tts-tool voices                     # list the available voices
    kokoro-tts-tool say --text "..." --voice af_heart --out vo.wav
    kokoro-tts-tool say --file script.txt --voice am_adam --out vo.wav --speed 1.05

Installed by `scripts/install_kokoro.sh`, which drops a `kokoro-tts-tool`
shim on PATH inside the local virtualenv.

Models live in `<repo>/.voice-models/kokoro/` (gitignored) so a fresh clone
only needs `init` once.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = Path(os.environ.get("KOKORO_HOME", ROOT / ".voice-models" / "kokoro"))

RELEASE = os.environ.get(
    "KOKORO_RELEASE",
    "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0",
)
# fp16 keeps the download at ~177 MB instead of ~325 MB and sounds identical
# on CPU; override with KOKORO_MODEL_FILE=kokoro-v1.0.onnx for the fp32 export.
MODEL_FILE = os.environ.get("KOKORO_MODEL_FILE", "kokoro-v1.0.fp16.onnx")
VOICES_FILE = "voices-v1.0.bin"

# The voices the pipeline uses; the rest are listed by `voices`.
VOICE_NOTES = {
    "af_heart": "female, warm and natural — the documentary default",
    "af_bella": "female, brighter, more energetic",
    "af_nicole": "female, calm and low",
    "am_adam": "male, steady narrator",
    "am_michael": "male, deeper and slower",
    "bf_emma": "British female, crisp",
    "bm_george": "British male, classic documentary",
}


def log(msg: str) -> None:
    print(f"[kokoro] {msg}", flush=True)


def die(msg: str, code: int = 1) -> None:
    print(f"[kokoro] ERROR: {msg}", file=sys.stderr, flush=True)
    sys.exit(code)


def download(url: str, dest: Path) -> None:
    if dest.exists() and dest.stat().st_size > 1024:
        log(f"already have {dest.name} ({dest.stat().st_size / 1e6:.0f} MB)")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    log(f"downloading {dest.name} from {url}")
    with urllib.request.urlopen(url, timeout=60) as resp, tmp.open("wb") as out:
        total = int(resp.headers.get("content-length") or 0)
        done = 0
        while chunk := resp.read(1 << 20):
            out.write(chunk)
            done += len(chunk)
            if total:
                pct = 100 * done / total
                print(f"\r  {pct:5.1f}%  {done / 1e6:6.1f} / {total / 1e6:.1f} MB", end="")
        print()
    tmp.replace(dest)


def cmd_init(args: argparse.Namespace) -> int:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    download(f"{RELEASE}/{MODEL_FILE}", MODEL_DIR / MODEL_FILE)
    download(f"{RELEASE}/{VOICES_FILE}", MODEL_DIR / VOICES_FILE)
    (MODEL_DIR / "model.json").write_text(
        json.dumps({"model": MODEL_FILE, "voices": VOICES_FILE, "release": RELEASE}, indent=2) + "\n"
    )
    log(f"ready in {MODEL_DIR}")
    return 0


def model_paths() -> tuple[Path, Path]:
    model, voices = MODEL_DIR / MODEL_FILE, MODEL_DIR / VOICES_FILE
    if not model.exists() or not voices.exists():
        die(f"model missing — run `kokoro-tts-tool init` first ({MODEL_DIR})")
    return model, voices


def load():
    try:
        from kokoro_onnx import Kokoro
    except ImportError:
        die("kokoro-onnx is not installed — run scripts/install_kokoro.sh")
    model, voices = model_paths()
    return Kokoro(str(model), str(voices))


def cmd_voices(args: argparse.Namespace) -> int:
    k = load()
    names = sorted(k.get_voices())
    for name in names:
        note = VOICE_NOTES.get(name.split("_")[0] * 0 + name, "")
        print(f"{name:14s} {note}")
    return 0


def synth(text: str, voice: str, speed: float, lang: str):
    """Return (samples_float32, sample_rate, phoneme_timings_or_None)."""
    k = load()
    try:
        audio, rate, timings = k.create_timed(text, voice=voice, speed=speed, lang=lang)
    except Exception:  # model without duration output
        audio, rate = k.create(text, voice=voice, speed=speed, lang=lang)
        timings = None
    return audio, rate, timings


def cmd_say(args: argparse.Namespace) -> int:
    import numpy as np
    import soundfile as sf

    text = Path(args.file).read_text().strip() if args.file else args.text
    if not text:
        die("nothing to say — pass --text or --file")
    audio, rate, timings = synth(text, args.voice, args.speed, args.lang)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    sf.write(out, np.asarray(audio, dtype="float32"), rate)
    log(f"wrote {out} ({len(audio) / rate:.2f}s @ {rate} Hz, voice {args.voice})")
    if timings and args.timings:
        payload = [{"phoneme": t.phoneme, "start": t.start, "end": t.end} for t in timings]
        Path(args.timings).write_text(json.dumps(payload, indent=1) + "\n")
        log(f"wrote {args.timings} ({len(payload)} phoneme timings)")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="kokoro-tts-tool", description="Kokoro-82M TTS")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init", help="download the Kokoro-82M model and voices").set_defaults(func=cmd_init)
    sub.add_parser("voices", help="list available voices").set_defaults(func=cmd_voices)

    s = sub.add_parser("say", help="synthesize speech to a WAV file")
    s.add_argument("--text", default="")
    s.add_argument("--file", default="", help="read the text from a file instead")
    s.add_argument("--voice", default="af_heart")
    s.add_argument("--speed", type=float, default=1.0)
    s.add_argument("--lang", default="en-us")
    s.add_argument("--out", required=True)
    s.add_argument("--timings", default="", help="write phoneme timings to this JSON file")
    s.set_defaults(func=cmd_say)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
