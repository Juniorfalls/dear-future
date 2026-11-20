#!/usr/bin/env python3
"""Speak a script with Kokoro-82M and time the film to the result.

Kokoro runs locally (Apache-2.0, commercial use allowed), needs no API key and
no network after the model is cached. Each scene in remotion/data/script.json
becomes remotion/public/audio/scene_<id>.wav, and scenes.json is rewritten so
every shot is as long as its narration plus a small breath at the end.

    python3 generate_voice.py                      # am_michael, 0.95x
    python3 generate_voice.py --voice am_adam --speed 0.9
    python3 generate_voice.py --check              # report only, write nothing

Install (Ubuntu / Termux):
    python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
    sudo apt install espeak-ng      # phoneme fallback for unusual words
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
DEFAULT_SCRIPT = HERE / "remotion" / "data" / "script.json"
DEFAULT_SCENES = HERE / "remotion" / "data" / "scenes.json"
DEFAULT_AUDIO_DIR = HERE / "remotion" / "public" / "audio"

SAMPLE_RATE = 24000
# Breathing room after the last word before the cut: the shot has to outlast the
# voice or the edit clips the sentence, but a long tail kills the pace.
TAIL_PADDING = 0.5
# Silence trimming: Kokoro pads a little; keeping ~80ms keeps consonants intact.
KEEP_HEAD = 0.06
KEEP_TAIL = 0.12


def load_kokoro():
    """Import Kokoro with a message that says what to do, not just a traceback."""
    try:
        from kokoro import KPipeline  # noqa: WPS433 (deliberate late import)
    except Exception as exc:  # pragma: no cover - depends on the machine
        sys.exit(
            "generate_voice: Kokoro is not available "
            f"({type(exc).__name__}: {exc}).\n"
            "  python3 -m venv .venv && .venv/bin/pip install -r requirements.txt\n"
            "If torch cannot be installed on this machine (Termux/Android), use the\n"
            "edge-tts fallback instead: pip install edge-tts, then\n"
            '  edge-tts --voice en-US-GuyNeural --text "..." --write-media scene_1.mp3'
        )
    return KPipeline


def trim(audio: np.ndarray, threshold: float = 0.006) -> np.ndarray:
    """Drop the dead air Kokoro leaves around a line, keeping a short margin."""
    loud = np.flatnonzero(np.abs(audio) > threshold)
    if loud.size == 0:
        return audio
    start = max(0, loud[0] - int(KEEP_HEAD * SAMPLE_RATE))
    end = min(audio.size, loud[-1] + int(KEEP_TAIL * SAMPLE_RATE))
    return audio[start:end]


def speak(pipeline, text: str, voice: str, speed: float) -> np.ndarray:
    """Synthesise one scene and return mono float32 audio at 24kHz."""
    pieces: list[np.ndarray] = []
    for _graphemes, _phonemes, chunk in pipeline(text, voice=voice, speed=speed):
        if chunk is None:
            continue
        pieces.append(np.asarray(chunk, dtype=np.float32).reshape(-1))
    if not pieces:
        sys.exit(f"generate_voice: Kokoro produced no audio for: {text!r}")

    audio = trim(np.concatenate(pieces))
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    if peak > 0.99:  # never clip the master mix
        audio = audio * (0.99 / peak)
    # 30ms fade in/out: a hard start on a sustained vowel clicks.
    ramp = min(int(0.03 * SAMPLE_RATE), audio.size // 2)
    if ramp > 0:
        fade = np.linspace(0.0, 1.0, ramp, dtype=np.float32)
        audio[:ramp] *= fade
        audio[-ramp:] *= fade[::-1]
    return audio


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--script", default=str(DEFAULT_SCRIPT))
    ap.add_argument("--scenes", default=str(DEFAULT_SCENES))
    ap.add_argument("--audio-dir", default=str(DEFAULT_AUDIO_DIR))
    ap.add_argument("--voice", default=None, help="Kokoro voice id (default: the script's voice)")
    ap.add_argument("--speed", type=float, default=0.95, help="0.95 reads with documentary weight")
    ap.add_argument("--check", action="store_true", help="report what would be done, write nothing")
    args = ap.parse_args()

    script_path = Path(args.script)
    if not script_path.exists():
        sys.exit(f"generate_voice: {script_path} not found. Run generate_script.py first.")
    script = json.loads(script_path.read_text())
    voice = args.voice or script.get("voice") or "am_michael"
    scenes_path = Path(args.scenes)
    episode = json.loads(scenes_path.read_text()) if scenes_path.exists() else {}
    film_scenes = episode.get("scenes", [])

    if len(film_scenes) != len(script["scenes"]):
        sys.exit(
            f"generate_voice: script has {len(script['scenes'])} scenes but "
            f"{scenes_path} has {len(film_scenes)}. Keep them in sync."
        )

    audio_dir = Path(args.audio_dir)
    audio_dir.mkdir(parents=True, exist_ok=True)

    if args.check:
        for s in script["scenes"]:
            print(f"{s['scene_id']}. [{voice}] {s['text']}")
        return

    pipeline = load_kokoro()(lang_code="a")
    total = 0.0
    rows = []
    for entry, film_scene in zip(script["scenes"], film_scenes):
        scene_id = entry["scene_id"]
        audio = speak(pipeline, entry["text"], voice, args.speed)
        rel = f"audio/scene_{scene_id}.wav"
        import soundfile as sf

        sf.write(audio_dir / f"scene_{scene_id}.wav", audio, SAMPLE_RATE, subtype="PCM_16")
        seconds = round(audio.size / SAMPLE_RATE, 3)
        shot = round(seconds + TAIL_PADDING, 3)
        total += shot

        # The renderer reads these two fields: one to play the line, one to size
        # the shot. calculateMetadata re-measures the wav and would only differ
        # if the file were replaced without re-running this script.
        film_scene["durationInSeconds"] = shot
        film_scene["voice"] = {"src": rel, "durationInSeconds": seconds}
        rows.append((scene_id, seconds, shot, entry["text"]))

    scenes_path.write_text(json.dumps(episode, indent=2) + "\n")

    print(f"voice {voice}, speed {args.speed} -> {len(rows)} wavs in {audio_dir}")
    for scene_id, seconds, shot, text in rows:
        print(f"  scene {scene_id}: {seconds:5.2f}s speech -> {shot:5.2f}s shot  {text}")
    print(f"film: {total:.2f}s of narration-driven runtime (before outro)")


if __name__ == "__main__":
    main()
