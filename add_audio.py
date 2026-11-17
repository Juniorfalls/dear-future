"""Attach a placeholder gTTS voiceover to every rendered Manim video.

Walks the folders where Manim and our scenes drop mp4 files, writes one mp3 per
video, pads the speech with silence to the full video length and muxes the result
into ``outputs/<topic_id>_with_audio.mp4``.

The voiceover text is a placeholder taken from ``topics.json`` (the real script
comes later); override it with ``--text`` for a single ad-hoc video.

Usage:  python3 add_audio.py [--video-dir DIR] [--out-dir DIR] [--text "..."]
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path

import numpy as np
from gtts import gTTS
from moviepy import AudioFileClip, CompositeAudioClip, VideoFileClip
from moviepy.audio.AudioClip import AudioClip

import factory

VIDEO_DIRS = (Path("media/videos"), Path("scenes"))
AUDIO_DIR = Path("audio")
OUTPUT_DIR = Path("outputs")
QUEUE_PATH = Path("topics.json")
TTS_RETRIES = 3


def snake(name):
    """`SavingsTrap` -> `savings_trap`, `compound_interest` -> `compound_interest`."""
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", name)
    return re.sub(r"[^0-9a-z]+", "_", spaced.lower()).strip("_")


def humanise(name):
    """`savings_trap` -> `savings trap`, dropping a trailing `scene`."""
    words = snake(name).replace("_", " ").strip()
    return re.sub(r"\s+scene$", "", words)


def topic_index():
    """Map scene class name -> topic id, so outputs keep the queue's names."""
    try:
        topics = json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"warning: cannot read {QUEUE_PATH} ({exc}); using file names")
        return {}, {}

    by_class, by_id = {}, {}
    for topic in topics:
        topic_id = snake(topic.get("id") or "explainer")
        title = topic.get("title") or "this topic"
        by_class[factory.topic_to_class_name(topic_id)] = topic_id
        by_id[topic_id] = title
    return by_class, by_id


def find_videos(root, exclude=()):
    """Every full render, never the per-animation partial files or our own output."""
    excluded = [Path(item).resolve() for item in exclude]
    videos = []
    seen = set()
    for base in (root, *VIDEO_DIRS):
        if not base.exists():
            continue
        for path in sorted(base.rglob("*.mp4")):
            if "partial_movie_files" in path.parts:
                continue
            if path.name.endswith("_with_audio.mp4"):
                continue
            resolved = path.resolve()
            if any(resolved == item or item in resolved.parents for item in excluded):
                continue
            if resolved in seen:
                continue
            seen.add(resolved)
            videos.append(path)
    return videos


def speak(text, mp3_path):
    """gTTS with a couple of retries - it is a network call."""
    last_error = None
    for attempt in range(1, TTS_RETRIES + 1):
        try:
            gTTS(text=text, lang="en").save(str(mp3_path))
            return
        except Exception as exc:  # noqa: BLE001 - surface the real reason below
            last_error = exc
            print(f"  tts attempt {attempt}/{TTS_RETRIES} failed: {exc}")
            if attempt < TTS_RETRIES:
                time.sleep(3 * attempt)
    raise RuntimeError(f"gTTS could not synthesise {mp3_path.name}: {last_error}")


def mux(video_path, mp3_path, out_path):
    """Silent video + speech, padded with silence to the video's length."""
    video = VideoFileClip(str(video_path))
    speech = AudioFileClip(str(mp3_path))
    try:
        if speech.duration < video.duration:
            pad = video.duration - speech.duration
            silence = AudioClip(
                lambda t: np.zeros((len(np.atleast_1d(t)), 2)),
                duration=pad,
                fps=speech.fps or 44100,
            )
            audio = CompositeAudioClip([speech, silence.with_start(speech.duration)])
        else:
            audio = speech.subclipped(0, video.duration)

        final = video.with_audio(audio)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        final.write_videofile(
            str(out_path),
            codec="libx264",
            audio_codec="aac",
            logger=None,
        )
        return video.duration, speech.duration
    finally:
        video.close()
        speech.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video-dir", default=None,
                        help="only look for mp4 files under this folder")
    parser.add_argument("--out-dir", default=str(OUTPUT_DIR))
    parser.add_argument("--text", default=None,
                        help="voiceover text to use for every video")
    args = parser.parse_args(argv)

    root = Path(args.video_dir) if args.video_dir else Path(".")
    out_dir = Path(args.out_dir)
    by_class, by_id = topic_index()

    videos = find_videos(root, exclude=(out_dir, AUDIO_DIR))
    if not videos:
        print("No rendered mp4 files found - nothing to add audio to.")
        return 0

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    failures = []
    for video_path in videos:
        stem = video_path.stem
        topic_id = by_class.get(stem) or snake(stem)
        title = by_id.get(topic_id)
        text = args.text or (
            f"Welcome to this explainer on {title}." if title
            else f"Welcome to this explainer on {humanise(stem)}."
        )

        mp3_path = AUDIO_DIR / f"{topic_id}.mp3"
        out_path = out_dir / f"{topic_id}_with_audio.mp4"

        print(f"[{video_path.name}] -> {out_path.name}")
        print(f"  voiceover: {text}")
        try:
            speak(text, mp3_path)
            video_len, speech_len = mux(video_path, mp3_path, out_path)
        except Exception as exc:  # noqa: BLE001 - report, keep going, fail at the end
            print(f"  FAILED: {exc}", file=sys.stderr)
            failures.append(f"{topic_id}: {exc}")
            continue

        print(f"  video {video_len:.1f}s + voiceover {speech_len:.1f}s "
              f"-> {out_path} ({out_path.stat().st_size / 1e6:.1f} MB)")

    if failures:
        print(f"\n{len(failures)} video(s) failed:", file=sys.stderr)
        for line in failures:
            print(f"  {line}", file=sys.stderr)
        return 1

    print(f"\nMuxed {len(videos)} video(s) into {out_dir}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
