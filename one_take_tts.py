#!/usr/bin/env python3
"""Speak a whole episode in one Kokoro call (the audiobook take).

tts.py parses a script into sentences and synthesises each one separately, so
pitch and breathing reset at every beat. This driver sends the entire
paragraph to Kokoro once, then writes the same files the renderer expects
(vo.wav, narration_full.wav, vo_lines.json, vo_script.txt) and runs the
skill's aligner for word timestamps.

usage: one_take_tts.py <folder> <script.txt> [--voice am_onyx] [--speed .88]
"""
import argparse
import json
import subprocess
import sys
import wave
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE / "vendor" / "stickman-skill" / "skills" / "stickman" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import tts  # noqa: E402  (vendored skill module, reused on purpose)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("script")
    ap.add_argument("--voice", default="am_onyx")
    ap.add_argument("--speed", type=float, default=.88)
    o = ap.parse_args()

    folder = Path(o.folder).resolve()
    text = " ".join(Path(o.script).read_text(encoding="utf8").split())
    if not text:
        sys.exit("empty narration script")
    if not 0.5 <= o.speed <= 2.0:
        sys.exit("--speed must be between 0.5 and 2.0")

    d = tts.model_dir(None)
    model = tts.fetch(d, tts.MODEL["full"])
    voices = tts.fetch(d, tts.VOICES)
    print("one take: loading Kokoro", flush=True)
    kokoro = tts.load_engine()(str(model), str(voices))

    lang = tts.LANG.get(o.voice[0], "en-us")
    if o.voice not in kokoro.get_voices():
        sys.exit(f"unknown voice {o.voice}")
    print("one take: speaking the full monologue in a single pass", flush=True)
    audio, _ = kokoro.create(text, voice=o.voice, speed=o.speed, lang=lang)
    audio = tts.trim(audio)
    wav = folder / "vo.wav"
    audio = tts.loudness_match(wav, audio)
    tts.save_wav(wav, audio)
    narration = folder / "narration_full.wav"
    narration.write_bytes(wav.read_bytes())

    with wave.open(str(wav), "rb") as w:
        dur = w.getnframes() / float(w.getframerate())
    rows = [{"n": 0, "beat": 0, "voice": o.voice, "start": 0.0,
             "end": round(dur, 3), "text": text}]
    (folder / "vo_lines.json").write_text(json.dumps(rows, indent=1), encoding="utf8")
    (folder / "vo_script.txt").write_text(text + "\n", encoding="utf8")
    (folder / "pauses.json").write_text("[]", encoding="utf8")
    print(f"one take: {dur:.2f} s, 1 line, 1 beat, {len(text.split())} words, "
          f"pace {len(text.split()) / dur * 60:.0f} wpm", flush=True)

    # Word timestamps for cutting shots inside the single take. The aligner is
    # optional; the renderer falls back to word-count proportions.
    if lang.startswith("en"):
        print("aligning words (English)", flush=True)
        subprocess.run([sys.executable, str(SCRIPTS / "align.py"),
                        str(folder), str(wav), str(folder / "vo_script.txt")])
    print("OUTPUT", narration, flush=True)


if __name__ == "__main__":
    main()
