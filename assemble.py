"""Multi-modal assembly: Manim video + gTTS voiceover + WhisperX captions.

For every rendered video under ``media/videos`` this script
  1. derives the topic id from the scene class name (via ``topics.json``),
  2. picks voiceover text (``voiceover.json`` -> ``scripts/<id>.txt`` -> placeholder),
  3. synthesises ``outputs/audio/<id>.mp3`` with gTTS,
  4. transcribes it with WhisperX (``tiny``, int8, CPU) and writes ``outputs/<id>.srt``,
  5. burns the captions over the video, adds the audio and writes
     ``outputs/final_<id>.mp4``.

Usage:  python3 assemble.py [--video-dir DIR] [--out-dir DIR] [--text TEXT]
                            [--model NAME] [--caption-mode whisper|even]
"""

import argparse
import json
import math
import re
import sys
import time
from pathlib import Path

import shutil
import subprocess
import tempfile

import imageio_ffmpeg
import numpy as np
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont
from moviepy import (
    AudioFileClip,
    CompositeAudioClip,
    CompositeVideoClip,
    ImageClip,
    ImageSequenceClip,
    VideoFileClip,
)
from moviepy.audio.AudioClip import AudioClip

import factory

VIDEO_DIRS = (Path("media/videos"), Path("scenes"))
OUT_DIR = Path("outputs")
AUDIO_DIR = OUT_DIR / "audio"
QUEUE_PATH = Path("topics.json")
VOICEOVER_JSON = Path("voiceover.json")
SCRIPT_DIR = Path("scripts")
DEFAULT_VOICE = "en"
OVERLAY_CANDIDATES = (Path("remotion-overlay/out/overlay.webm"), Path("overlay.webm"))
OVERLAY_WIDTH_RATIO = 0.26
OVERLAY_RIGHT_MARGIN = 0.035
OVERLAY_BOTTOM_MARGIN = 0.15
OVERLAY_ASPECT = 190 / 600  # Overlay composition is 600x190
FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
)
TTS_RETRIES = 3


# --------------------------------------------------------------------------- #
# naming / lookup
# --------------------------------------------------------------------------- #
def snake(name):
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", name)
    return re.sub(r"[^0-9a-z]+", "_", spaced.lower()).strip("_")


def humanise(name):
    words = snake(name).replace("_", " ").strip()
    return re.sub(r"\s+scene$", "", words)


def topic_maps():
    """class name -> topic id, and topic id -> title."""
    try:
        topics = json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"warning: cannot read {QUEUE_PATH} ({exc}); using file names")
        return {}, {}

    by_class, titles = {}, {}
    for topic in topics:
        topic_id = snake(topic.get("id") or "explainer")
        by_class[factory.topic_to_class_name(topic_id)] = topic_id
        titles[topic_id] = topic.get("title") or humanise(topic_id)
    return by_class, titles


def load_voiceovers():
    if not VOICEOVER_JSON.exists():
        return {}
    try:
        data = json.loads(VOICEOVER_JSON.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"warning: {VOICEOVER_JSON} is not valid JSON ({exc}); ignoring it")
        return {}
    return data if isinstance(data, dict) else {}


def voiceover_text(topic_id, base_name, titles, overrides):
    """Real narration if we have it, otherwise a clearly-marked placeholder."""
    if topic_id in overrides and str(overrides[topic_id]).strip():
        return str(overrides[topic_id]).strip(), "voiceover.json"
    script = SCRIPT_DIR / f"{topic_id}.txt"
    if script.exists() and script.read_text(encoding="utf-8").strip():
        return script.read_text(encoding="utf-8").strip(), str(script)
    title = titles.get(topic_id) or base_name.replace("_", " ")
    return f"Welcome to this explainer on {title}.", "placeholder"


# --------------------------------------------------------------------------- #
# discovery
# --------------------------------------------------------------------------- #
def find_videos(root, exclude=()):
    excluded = [Path(item).resolve() for item in exclude]
    found, seen = [], set()
    for base in (root, *VIDEO_DIRS):
        if not base.exists():
            continue
        for path in sorted(base.rglob("*.mp4")):
            if "partial_movie_files" in path.parts:
                continue
            resolved = path.resolve()
            if any(resolved == item or item in resolved.parents for item in excluded):
                continue
            if resolved in seen:
                continue
            seen.add(resolved)
            found.append(path)
    return found


# --------------------------------------------------------------------------- #
# audio + captions
# --------------------------------------------------------------------------- #
def speak(text, mp3_path):
    last = None
    for attempt in range(1, TTS_RETRIES + 1):
        try:
            gTTS(text=text, lang=DEFAULT_VOICE).save(str(mp3_path))
            return
        except Exception as exc:  # noqa: BLE001 - reported below
            last = exc
            print(f"  tts attempt {attempt}/{TTS_RETRIES} failed: {exc}")
            if attempt < TTS_RETRIES:
                time.sleep(3 * attempt)
    raise RuntimeError(f"gTTS failed for {mp3_path.name}: {last}")


def transcribe(mp3_path, model_name):
    """WhisperX (tiny, int8) -> list of (start, end, text) cues."""
    import whisperx  # imported lazily so the rest of the script works without it

    print(f"  whisperx: model={model_name} device=cpu int8")
    model = whisperx.load_model(model_name, device="cpu", compute_type="int8")
    audio = whisperx.load_audio(str(mp3_path))
    result = model.transcribe(audio, batch_size=4, language="en")

    cues = []
    for seg in result.get("segments", []):
        text = (seg.get("text") or "").strip()
        if text:
            cues.append((float(seg["start"]), float(seg["end"]), text))
    if not cues:
        raise RuntimeError("whisperx returned no segments")
    return refine_cues(cues)


def refine_cues(cues, max_words=5):
    """Whisper segments can run a whole sentence; cut them into caption-sized
    chunks and spread the segment's own timings over the chunks."""
    refined = []
    for start, end, text in cues:
        words = text.split()
        if len(words) <= max_words:
            refined.append((start, end, text))
            continue
        chunks = [" ".join(words[i:i + max_words])
                  for i in range(0, len(words), max_words)]
        step = (end - start) / len(chunks)
        for index, chunk in enumerate(chunks):
            refined.append((start + index * step, start + (index + 1) * step, chunk))
    return refined


def even_cues(text, duration, words_per_cue=4):
    """Fallback timing when WhisperX is unavailable: spread the words evenly."""
    words = text.split()
    chunks = [
        " ".join(words[i:i + words_per_cue])
        for i in range(0, len(words), words_per_cue)
    ] or [text]
    step = duration / len(chunks)
    return [(i * step, (i + 1) * step, chunk) for i, chunk in enumerate(chunks)]


def srt_timestamp(seconds):
    milliseconds = int(round(seconds * 1000))
    hours, rest = divmod(milliseconds, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    secs, ms = divmod(rest, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def write_srt(cues, path, offset=0.0):
    lines = []
    for index, (start, end, text) in enumerate(cues, start=1):
        begin = max(0.0, start + offset)
        finish = max(begin + 0.2, end + offset)
        lines.append(f"{index}\n{srt_timestamp(begin)} --> {srt_timestamp(finish)}\n{text}\n")
    path.write_text("\n".join(lines), encoding="utf-8")


def find_font():
    for candidate in FONT_CANDIDATES:
        if Path(candidate).exists():
            return candidate
    return None


def wrap_lines(draw, text, font, max_width):
    words, lines, current = text.split(), [], ""
    for word in words:
        trial = f"{current} {word}".strip()
        if not current or draw.textlength(trial, font=font) <= max_width:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def make_caption(text, video_size, font_path):
    """Draw one caption onto a transparent RGBA tile (Pillow, no ImageMagick)."""
    width, height = video_size
    font_size = max(16, int(height * 0.045))
    font = (ImageFont.truetype(font_path, font_size) if font_path
            else ImageFont.load_default())

    probe = ImageDraw.Draw(Image.new("RGBA", (8, 8)))
    max_text_width = int(width * 0.80)
    lines = wrap_lines(probe, text, font, max_text_width)

    ascent, descent = font.getmetrics()
    line_height = ascent + descent
    pad = max(6, int(height * 0.012))
    box_width = int(max(probe.textlength(line, font=font) for line in lines)) + 2 * pad
    box_height = line_height * len(lines) + 2 * pad

    tile = Image.new("RGBA", (box_width, box_height), (0, 0, 0, 175))
    draw = ImageDraw.Draw(tile)
    for index, line in enumerate(lines):
        draw.text(
            (pad, pad + index * line_height),
            line,
            font=font,
            fill=(255, 255, 255, 255),
            stroke_width=1,
            stroke_fill=(0, 0, 0, 255),
        )
    return np.array(tile)


def caption_clips(cues, size, offset=0.0):
    """Burn the cues in as image tiles anchored to the bottom edge."""
    font_path = find_font()
    if font_path is None:
        print("  warning: no usable TTF font found; captions may render small")
    clips = []
    for start, end, text in cues:
        tile = make_caption(text, size, font_path)
        clip = ImageClip(tile, transparent=True)
        clip = clip.with_start(max(0.0, start + offset))
        clip = clip.with_end(max(0.0, end + offset))
        margin = int(size[1] * 0.06)
        clip = clip.with_position(("center", size[1] - tile.shape[0] - margin))
        clips.append(clip)
    return clips


def find_overlay(explicit=None):
    if explicit:
        candidate = Path(explicit)
        return candidate if candidate.exists() else None
    for path in OVERLAY_CANDIDATES:
        if path.exists():
            return path
    return None


OVERLAY_FPS = 30


def overlay_geometry(video_size):
    width, height = video_size
    ov_w = max(80, int(width * OVERLAY_WIDTH_RATIO))
    ov_h = int(round(ov_w * OVERLAY_ASPECT))
    x = width - ov_w - int(width * OVERLAY_RIGHT_MARGIN)
    y = height - ov_h - int(height * OVERLAY_BOTTOM_MARGIN)
    return ov_w, x, y


def extract_overlay_frames(overlay_path):
    """Expand the transparent WebM to RGBA PNGs.

    `-c:v libvpx` is required: ffmpeg's default VP8 decoder silently drops the
    alpha plane (WebM keeps alpha in a side channel) and the overlay would be
    composited as an opaque black box.
    """
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    frames_dir = Path(tempfile.mkdtemp(prefix="overlay-"))
    subprocess.run(
        [ffmpeg, "-v", "error", "-y", "-c:v", "libvpx", "-i", str(overlay_path),
         "-pix_fmt", "rgba", str(frames_dir / "f%04d.png")],
        check=True,
    )
    if not sorted(frames_dir.glob("f*.png")):
        shutil.rmtree(frames_dir, ignore_errors=True)
        raise RuntimeError(f"no frames decoded from {overlay_path}")
    return frames_dir


def apply_overlay(video_path, frames_dir, out_path, video_size):
    """Composite the looping overlay in a single ffmpeg pass.

    The PNG sequence is looped (`-stream_loop -1`) instead of the WebM: looping
    a VP8 file back through the decoder loses the alpha plane after a couple of
    iterations, which made the badge vanish mid-video.
    """
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    ov_w, x, y = overlay_geometry(video_size)
    filter_complex = (
        f"[1:v]scale={ov_w}:-1,format=yuva420p[ov];"
        f"[0:v][ov]overlay={x}:{y}:shortest=1,format=yuv420p[v]"
    )
    subprocess.run(
        [
            ffmpeg, "-v", "error", "-y",
            "-i", str(video_path),
            "-framerate", str(OVERLAY_FPS), "-stream_loop", "-1",
            "-i", str(frames_dir / "f%04d.png"),
            "-filter_complex", filter_complex,
            "-map", "[v]", "-map", "0:a?",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
            "-c:a", "copy", "-movflags", "+faststart",
            str(out_path),
        ],
        check=True,
    )


def build_final(video_path, mp3_path, cues, out_path, overlay_path=None):
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

        layer = video.with_audio(audio)
        clips = caption_clips(cues, (video.w, video.h))
        final = CompositeVideoClip([layer, *clips], size=(video.w, video.h))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        captioned = out_path
        if overlay_path is not None:
            captioned = out_path.with_name(out_path.stem + "_captioned.mp4")
        final.write_videofile(
            str(captioned),
            codec="libx264",
            audio_codec="aac",
            fps=video.fps,
            preset="veryfast",
            logger=None,
        )
        if overlay_path is not None:
            frames_dir = extract_overlay_frames(overlay_path)
            try:
                apply_overlay(captioned, frames_dir, out_path, (video.w, video.h))
            finally:
                shutil.rmtree(frames_dir, ignore_errors=True)
            captioned.unlink(missing_ok=True)
            print(f"  overlay: {overlay_path.name} over {video.duration:.1f}s")
        return video.duration, speech.duration
    finally:
        video.close()
        speech.close()


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video-dir", default=".")
    parser.add_argument("--out-dir", default=str(OUT_DIR))
    parser.add_argument("--text", default=None, help="override voiceover for every video")
    parser.add_argument("--model", default="tiny", help="whisperx model name")
    parser.add_argument("--caption-mode", choices=("whisper", "even"), default="whisper")
    parser.add_argument("--overlay", default=None,
                        help="Remotion overlay .webm (default: remotion-overlay/out/overlay.webm)")
    parser.add_argument("--no-overlay", action="store_true", help="skip the overlay")
    args = parser.parse_args(argv)

    out_dir = Path(args.out_dir)
    audio_dir = out_dir / "audio"
    out_dir.mkdir(parents=True, exist_ok=True)
    audio_dir.mkdir(parents=True, exist_ok=True)

    overlay_path = None if args.no_overlay else find_overlay(args.overlay)
    if args.no_overlay:
        print("Overlay disabled (--no-overlay).")
    elif overlay_path:
        print(f"Overlay: {overlay_path}")
    else:
        print("warning: no Remotion overlay found; rendering without it")

    by_class, titles = topic_maps()
    overrides = load_voiceovers()

    videos = find_videos(Path(args.video_dir), exclude=(out_dir,))
    if not videos:
        print("No rendered mp4 files found - nothing to assemble.")
        return 0

    failures = []
    for video_path in videos:
        topic_id = by_class.get(video_path.stem) or snake(video_path.stem)
        text, source = voiceover_text(topic_id, topic_id, titles, overrides)
        if args.text:
            text, source = args.text, "cli"
        mp3_path = audio_dir / f"{topic_id}.mp3"
        srt_path = out_dir / f"{topic_id}.srt"
        out_path = out_dir / f"final_{topic_id}.mp4"

        print(f"[{video_path.name}] -> {out_path.name}")
        print(f"  voiceover ({source}): {text}")
        try:
            speak(text, mp3_path)

            if args.caption_mode == "even":
                cues = even_cues(text, AudioFileClip(str(mp3_path)).duration)
                print(f"  captions: {len(cues)} cues, evenly spaced (whisperx skipped)")
            else:
                try:
                    cues = transcribe(mp3_path, args.model)
                    print(f"  captions: {len(cues)} cues from whisperx")
                except ImportError as exc:
                    print(f"  warning: whisperx unavailable ({exc}); using even cues")
                    cues = even_cues(text, AudioFileClip(str(mp3_path)).duration)
            write_srt(cues, srt_path)

            video_len, speech_len = build_final(
                video_path, mp3_path, cues, out_path, overlay_path=overlay_path
            )
        except Exception as exc:  # noqa: BLE001 - collected and reported below
            print(f"  FAILED: {exc}", file=sys.stderr)
            failures.append(f"{topic_id}: {exc}")
            continue

        print(f"  video {video_len:.1f}s + speech {speech_len:.1f}s "
              f"-> {out_path} ({out_path.stat().st_size / 1e6:.1f} MB)")

    if failures:
        print(f"\n{len(failures)} video(s) failed:", file=sys.stderr)
        for line in failures:
            print(f"  {line}", file=sys.stderr)
        return 1

    print(f"\nAssembled {len(videos)} video(s) into {out_dir}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
