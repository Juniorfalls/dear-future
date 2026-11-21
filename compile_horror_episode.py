#!/usr/bin/env python3
"""Assemble a horror short with OpenFilm from AI clips and a voiceover.

What it does:

  1. copies the per-shot clips into <project>/public/media/
  2. copies the voiceover into <project>/public/audio/ (per shot, one file, or
     synthesises it locally with Kokoro when --tts is given)
  3. writes film.html: nine video clips cut at the timings in episode.json, the
     voiceover on its own track, and a subtitle page on top
  4. writes horror_overlay.html: a transparent page whose frame(t) draws the
     thick outlined captions and a vignette over the footage
  5. runs `npx openfilm render` to <project>/12th-street-ep01.mp4

OpenFilm's format keeps film.html as the edit and puts frame(t) on a page, so
the page draws the captions; the videos and sound are clips in film.html.

Examples:

    # real clips and one continuous voiceover
    python3 compile_horror_episode.py \
      --clips-dir clips/ --voiceover voice.wav --vtt voice.vtt

    # one voice file per shot (shot-01.wav ... shot-09.wav)
    python3 compile_horror_episode.py --clips-dir clips/ --voice-dir vo/

    # no voiceover yet: synthesise one line per shot with Kokoro
    python3 compile_horror_episode.py --clips-dir clips/ --tts

    # write the project without rendering
    python3 compile_horror_episode.py --clips-dir clips/ --tts --no-render
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_EPISODE = HERE / "episode.json"
DEFAULT_SERIES = HERE / "series.json"

VIDEO_EXTS = (".mp4", ".webm", ".mov", ".m4v")
AUDIO_EXTS = (".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg")

# The cold grade on every shot. OpenFilm applies clip CSS as it draws, and the
# subtitle page adds the vignette on top.
SHOT_FILTER = "contrast(1.2) hue-rotate(-10deg) saturate(0.86) brightness(0.94)"


@dataclass
class Shot:
    index: int
    start: float
    duration: float
    caption: str
    description: str
    vo: str = ""
    clip: Path | None = None
    voice: Path | None = None
    voice_seconds: float = 0.0


@dataclass
class Cue:
    start: float
    end: float
    text: str


def load_json(path: Path) -> dict:
    if not path.exists():
        sys.exit(f"compile_horror_episode: {path} not found")
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        sys.exit(f"compile_horror_episode: {path}: {exc}")


def media_duration(path: Path) -> float | None:
    """Seconds: wave for PCM wav, ffprobe if present, else ffmpeg's banner."""
    if path.suffix.lower() == ".wav":
        try:
            import wave

            with wave.open(str(path), "rb") as wav:
                return wav.getnframes() / float(wav.getframerate())
        except (wave.Error, OSError):
            pass
    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        result = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", str(path)],
            capture_output=True, text=True,
        )
        try:
            return float(result.stdout.strip())
        except ValueError:
            pass
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        try:
            import imageio_ffmpeg

            ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            ffmpeg = None
    if ffmpeg:
        result = subprocess.run([ffmpeg, "-i", str(path)], capture_output=True, text=True)
        match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", result.stderr)
        if match:
            h, m, s = match.groups()
            return int(h) * 3600 + int(m) * 60 + float(s)
    return None


def index_media(folder: Path, exts: tuple[str, ...]) -> dict[int, Path]:
    """Map shot numbers to files named shot-01, shot_1, panel-01, 01, ..."""
    found: dict[int, Path] = {}
    if not folder or not folder.exists():
        return found
    for path in sorted(folder.iterdir()):
        if not path.is_file() or path.suffix.lower() not in exts:
            continue
        match = re.search(r"(\d+)\s*$", path.stem)
        if not match:
            continue
        number = int(match.group(1))
        found.setdefault(number, path)
    return found


def place(source: Path, destination_dir: Path, stem: str) -> Path:
    destination_dir.mkdir(parents=True, exist_ok=True)
    target = destination_dir / f"{stem}{source.suffix.lower()}"
    if source.resolve() != target.resolve():
        shutil.copy2(source, target)
    return target


def build_shots(episode: dict, duration: float) -> list[Shot]:
    shots: list[Shot] = []
    cursor = 0.0
    index = 0
    for part in episode.get("parts", []):
        for raw in part.get("shots", []):
            index += 1
            seconds = float(raw.get("dur") or 0)
            if seconds <= 0:
                sys.exit(f"compile_horror_episode: shot {index} has no dur")
            caption = (raw.get("caption") or raw.get("text") or "").strip()
            shots.append(Shot(
                index=index,
                start=round(cursor, 3),
                duration=seconds,
                caption=caption,
                description=(raw.get("desc") or "").strip(),
                vo=(raw.get("vo") or caption).strip(),
            ))
            cursor += seconds
    if not shots:
        sys.exit("compile_horror_episode: episode.json has no parts[].shots[]")
    if abs(cursor - duration) > 0.05:
        print(f"! shots total {cursor:.2f}s, episode.duration is {duration:.2f}s; using the shots")
    return shots


def collect_clips(shots: list[Shot], clips_dir: Path | None, media_dir: Path,
                  allow_missing: bool) -> None:
    sources = index_media(clips_dir, VIDEO_EXTS) if clips_dir else {}
    for shot in shots:
        source = sources.get(shot.index)
        if source is None:
            existing = next(iter(sorted(media_dir.glob(f"shot-{shot.index:02d}.*"))), None)
            source = existing
        if source is None:
            if allow_missing:
                print(f"! shot {shot.index:02d}: no clip, leaving black")
                continue
            sys.exit(f"compile_horror_episode: no clip for shot {shot.index:02d} "
                     f"({shot.duration:.1f}s). Use --clips-dir or --allow-missing.")
        shot.clip = place(source, media_dir, f"shot-{shot.index:02d}")
        measured = media_duration(shot.clip)
        if measured is not None:
            if measured + 0.05 < shot.duration:
                print(f"! shot {shot.index:02d}: clip {measured:.2f}s is shorter than "
                      f"the {shot.duration:.2f}s shot; it will hold its last frame")
            elif measured > shot.duration + 0.05:
                print(f"  shot {shot.index:02d}: trimming {measured:.2f}s clip to "
                      f"{shot.duration:.2f}s")


def synthesise_voices(shots: list[Shot], audio_dir: Path, voice: str, speed: float,
                      force: bool = False) -> None:
    """Kokoro, locally: one wav per spoken line, only when the wav is missing."""
    try:
        from generate_voice import load_kokoro, speak  # noqa: WPS433 - needs numpy/kokoro
        import soundfile as sf
    except Exception as exc:  # noqa: BLE001 - the message is the point
        sys.exit("compile_horror_episode: Kokoro is not available "
                 f"({type(exc).__name__}: {exc}). Install requirements-voice.txt "
                 "or pass --voice-dir/--voiceover.")

    pipeline = load_kokoro()(lang_code="a")
    for shot in shots:
        line = shot.vo or shot.caption
        if not line:
            continue
        target = audio_dir / f"shot-{shot.index:02d}.wav"
        if target.exists() and target.stat().st_size > 0 and not force:
            shot.voice = target
            shot.voice_seconds = media_duration(target) or 0.0
            continue
        audio = speak(pipeline, line, voice, speed)
        sf.write(target, audio, 24000, subtype="PCM_16")
        shot.voice = target
        shot.voice_seconds = round(audio.size / 24000, 3)
        if shot.voice_seconds > shot.duration + 0.05:
            print(f"! voice shot {shot.index:02d}: {shot.voice_seconds:.2f}s for a "
                  f"{shot.duration:.2f}s shot; the tail will be cut")
        print(f"  voice shot {shot.index:02d}: {shot.voice_seconds:.2f}s  {line}")


def collect_voices(shots: list[Shot], voice_dir: Path | None, audio_dir: Path,
                   tts: bool, voice: str, speed: float, allow_missing: bool,
                   force_tts: bool = False) -> None:
    sources = index_media(voice_dir, AUDIO_EXTS) if voice_dir else {}
    for shot in shots:
        source = sources.get(shot.index)
        if source is None:
            source = next(iter(sorted(audio_dir.glob(f"shot-{shot.index:02d}.*"))), None)
        if source is not None:
            shot.voice = place(source, audio_dir, f"shot-{shot.index:02d}")
            shot.voice_seconds = media_duration(shot.voice) or 0.0
            if shot.voice_seconds > shot.duration + 0.05:
                print(f"! voice shot {shot.index:02d}: {shot.voice_seconds:.2f}s for a "
                      f"{shot.duration:.2f}s shot; the tail will be cut")
    if tts:
        synthesise_voices(shots, audio_dir, voice, speed, force=force_tts)
    for shot in shots:
        if shot.caption and shot.voice is None and not allow_missing:
            sys.exit(f"compile_horror_episode: no voiceover for shot {shot.index:02d}. "
                     "Use --voice-dir, --voiceover, --tts or --allow-missing.")


def per_shot_cues(shots: list[Shot]) -> list[Cue]:
    cues: list[Cue] = []
    for shot in shots:
        if not shot.caption:
            continue
        start = shot.start + min(0.3, shot.duration * 0.08)
        end = shot.start + shot.duration - 0.12
        if shot.voice_seconds:
            end = min(end, start + max(1.6, shot.voice_seconds + 0.55))
        if end > start:
            cues.append(Cue(round(start, 3), round(end, 3), shot.caption))
    return cues


def parse_vtt(path: Path) -> list[Cue]:
    text = path.read_text(errors="replace").replace("\r\n", "\n")
    stamp = r"(\d+):(\d{2}):(\d{2})[.,](\d{3})"
    pattern = re.compile(rf"{stamp}\s*-->\s*{stamp}")
    cues: list[Cue] = []
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        match = pattern.search(lines[i])
        if not match:
            i += 1
            continue
        h1, m1, s1, ms1, h2, m2, s2, ms2 = match.groups()
        start = int(h1) * 3600 + int(m1) * 60 + int(s1) + int(ms1) / 1000
        end = int(h2) * 3600 + int(m2) * 60 + int(s2) + int(ms2) / 1000
        i += 1
        body: list[str] = []
        while i < len(lines) and lines[i].strip():
            body.append(re.sub(r"<[^>]+>", "", lines[i]).strip())
            i += 1
        label = " ".join(part for part in body if part)
        if label:
            cues.append(Cue(round(start, 3), round(end, 3), label))
    return cues


def proportional_cues(shots: list[Shot], voice_seconds: float) -> list[Cue]:
    """Fallback for one voice file without a VTT: split it by caption length."""
    spoken = [shot for shot in shots if shot.caption]
    if not spoken or voice_seconds <= 0:
        return per_shot_cues(shots)
    weights = [len(shot.caption) + 12 for shot in spoken]
    total_weight = sum(weights)
    gap = 0.12
    window = max(0.5, voice_seconds - gap * (len(spoken) - 1))
    cues: list[Cue] = []
    cursor = 0.0
    for shot, weight in zip(spoken, weights):
        span = window * weight / total_weight
        cues.append(Cue(round(cursor, 3), round(cursor + span, 3), shot.caption))
        cursor += span + gap
    return cues


def write_film_html(project: Path, shots: list[Shot], duration: float,
                    width: int, height: int, single_voice: Path | None,
                    music: Path | None, music_volume: float, title: str) -> Path:
    video_tags: list[str] = []
    voice_tags: list[str] = []
    for shot in shots:
        if shot.clip is not None:
            rel = shot.clip.relative_to(project).as_posix()
            video_tags.append(
                f'  <video id="shot-{shot.index:02d}" src="{html.escape(rel)}'
                f'#t=0,{shot.duration:.3f}" at="{shot.start:.3f}" volume="0" class="shot"'
                f' style="left:0;top:0;width:{width}px;height:{height}px"></video>'
            )
        if single_voice is None and shot.voice is not None:
            rel = shot.voice.relative_to(project).as_posix()
            heard = min(shot.duration, shot.voice_seconds or shot.duration)
            voice_tags.append(
                f'  <audio id="vo-{shot.index:02d}" src="{html.escape(rel)}'
                f'#t=0,{heard:.3f}" at="{shot.start:.3f}" volume="1"></audio>'
            )

    sections: list[str] = []
    sections.append(
        "<!-- Captions and vignette: a transparent page drawn by frame(t). -->\n"
        "<section>\n"
        f'  <iframe id="captions" src="horror_overlay.html" at="0"'
        f' style="left:0;top:0;width:{width}px;height:{height}px"></iframe>\n'
        "</section>"
    )
    if video_tags:
        sections.append("<!-- The shots, trimmed to the episode timings. -->\n<section>\n"
                        + "\n".join(video_tags) + "\n</section>")
    if single_voice is not None:
        rel = single_voice.relative_to(project).as_posix()
        sections.append(
            "<!-- One continuous voiceover. -->\n<section>\n"
            f'  <audio id="voiceover" src="{html.escape(rel)}#t=0,{duration:.3f}"'
            f' at="0" volume="1"></audio>\n</section>'
        )
    elif voice_tags:
        sections.append("<!-- One voice line per shot. -->\n<section>\n"
                        + "\n".join(voice_tags) + "\n</section>")
    if music is not None:
        rel = music.relative_to(project).as_posix()
        sections.append(
            "<!-- Music bed under the voice. -->\n<section>\n"
            f'  <audio id="music" src="{html.escape(rel)}#t=0,{duration:.3f}"'
            f' at="0" volume="{music_volume:.2f}"></audio>\n</section>'
        )

    document = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width={width}, height={height}">
<title>{html.escape(title)}</title>
<style>
  .shot {{
    object-fit: cover;
    filter: {SHOT_FILTER};
  }}
</style>
</head>
<body>

{chr(10).join(sections)}

</body>
</html>
"""
    path = project / "film.html"
    path.write_text(document)
    return path


def write_overlay_page(project: Path, cues: list[Cue], duration: float,
                       width: int, height: int) -> Path:
    cue_data = json.dumps([{"start": c.start, "end": c.end, "text": c.text} for c in cues],
                          ensure_ascii=False, indent=2)
    page = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width={width}, height={height}">
<style>
  html, body {{ margin: 0; width: 100%; height: 100%; background: transparent; overflow: hidden; }}
  canvas {{ position: fixed; inset: 0; width: 100%; height: 100%; display: block; }}
</style>
</head>
<body>
<canvas id="c"></canvas>
<script>
(() => {{
  'use strict';
  const CUES = {cue_data};
  const DURATION = {duration};
  const REF_W = {width};
  const REF_H = {height};
  const canvas = document.getElementById('c');
  const ctx = canvas.getContext('2d', {{ alpha: true }});
  let w = REF_W, h = REF_H;

  const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
  const smoothstep = (a, b, x) => {{
    const t = clamp((x - a) / (b - a), 0, 1);
    return t * t * (3 - 2 * t);
  }};

  function resize() {{
    w = Math.max(1, window.innerWidth);
    h = Math.max(1, window.innerHeight);
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }}

  function wrap(text, maxWidth, font) {{
    ctx.font = font;
    const words = text.split(/\\s+/);
    const lines = [];
    let line = '';
    for (const word of words) {{
      const next = line ? line + ' ' + word : word;
      if (line && ctx.measureText(next).width > maxWidth) {{
        lines.push(line);
        line = word;
      }} else {{
        line = next;
      }}
    }}
    if (line) lines.push(line);
    return lines;
  }}

  function drawVignette() {{
    const v = ctx.createRadialGradient(w / 2, h / 2, h * 0.24, w / 2, h / 2, Math.max(w, h) * 0.76);
    v.addColorStop(0, 'rgba(0,0,0,0)');
    v.addColorStop(0.62, 'rgba(0,0,0,0.14)');
    v.addColorStop(1, 'rgba(0,0,0,0.62)');
    ctx.fillStyle = v;
    ctx.fillRect(0, 0, w, h);
  }}

  function drawCue(t) {{
    const cue = CUES.find((c) => t >= c.start && t < c.end);
    if (!cue) return;
    const fade = Math.min(0.18, (cue.end - cue.start) * 0.25);
    const opacity = smoothstep(cue.start, cue.start + fade, t)
      * (1 - smoothstep(cue.end - fade, cue.end, t));
    if (opacity <= 0) return;

    const fs = Math.round(h * 0.064);
    const font = `900 ${{fs}}px Impact, Haettenschweiler, "Arial Narrow Bold", "Arial Black", sans-serif`;
    const maxWidth = w * 0.84;
    const lines = wrap(cue.text, maxWidth, font);
    const lineHeight = fs * 1.04;
    const baseY = h * 0.855 - (lines.length - 1) * lineHeight;

    ctx.save();
    ctx.globalAlpha = opacity;
    ctx.font = font;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'alphabetic';
    ctx.lineJoin = 'round';
    ctx.miterLimit = 2;
    ctx.strokeStyle = '#000';
    ctx.fillStyle = '#fff';
    ctx.lineWidth = Math.max(6, fs * 0.19);
    ctx.shadowColor = 'rgba(0,0,0,0.9)';
    ctx.shadowBlur = fs * 0.26;
    lines.forEach((line, i) => {{
      const y = baseY + i * lineHeight;
      ctx.strokeText(line, w / 2, y);
      ctx.fillText(line, w / 2, y);
    }});
    ctx.restore();
  }}

  function frame(t) {{
    ctx.clearRect(0, 0, w, h);
    drawVignette();
    if (t >= 0 && t < DURATION) drawCue(t);
  }}

  resize();
  window.film = {{
    duration: DURATION,
    width: REF_W,
    height: REF_H,
    ready: document.fonts.ready,
    frame,
  }};
}})();
</script>
</body>
</html>
"""
    path = project / "horror_overlay.html"
    path.write_text(page)
    return path


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--episode", default=str(DEFAULT_EPISODE))
    parser.add_argument("--series", default=str(DEFAULT_SERIES))
    parser.add_argument("--project", default=str(HERE), help="OpenFilm project folder")
    parser.add_argument("--clips-dir", help="folder of shot-01.mp4 ... shot-09.mp4")
    parser.add_argument("--voice-dir", help="folder of shot-01.wav ... shot-09.wav")
    parser.add_argument("--voiceover", help="one continuous voiceover file")
    parser.add_argument("--vtt", help="WebVTT cues for --voiceover")
    parser.add_argument("--tts", action="store_true", help="synthesise missing lines with Kokoro")
    parser.add_argument("--force-tts", action="store_true", help="regenerate existing Kokoro lines")
    parser.add_argument("--voice", default="am_michael", help="Kokoro voice id")
    parser.add_argument("--speed", type=float, default=0.9, help="Kokoro speaking speed")
    parser.add_argument("--music", help="optional music bed file")
    parser.add_argument("--music-volume", type=float, default=0.24)
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--out", default="12th-street-ep01.mp4")
    parser.add_argument("--allow-missing", action="store_true",
                        help="leave black where a clip/voice is missing")
    parser.add_argument("--no-render", action="store_true", help="write the project only")
    args = parser.parse_args()

    episode = load_json(Path(args.episode))
    series = load_json(Path(args.series))
    project = Path(args.project).resolve()
    project.mkdir(parents=True, exist_ok=True)
    media_dir = project / "public" / "media"
    audio_dir = project / "public" / "audio"
    media_dir.mkdir(parents=True, exist_ok=True)
    audio_dir.mkdir(parents=True, exist_ok=True)

    duration = float(episode.get("duration") or 30)
    shots = build_shots(episode, duration)
    total = round(sum(shot.duration for shot in shots), 3)
    title = episode.get("title") or series.get("title") or "Horror short"

    print(f"{title}: {len(shots)} shots, {total:.2f}s, {args.width}x{args.height} @ {args.fps}fps")
    collect_clips(shots, Path(args.clips_dir).resolve() if args.clips_dir else None,
                  media_dir, args.allow_missing)

    single_voice: Path | None = None
    cues: list[Cue]
    if args.voiceover:
        source = Path(args.voiceover).resolve()
        if not source.exists():
            sys.exit(f"compile_horror_episode: {source} not found")
        single_voice = place(source, audio_dir, "voiceover")
        seconds = media_duration(single_voice) or total
        if seconds + 0.05 < total:
            print(f"! voiceover is {seconds:.2f}s for a {total:.2f}s film")
        if seconds > total + 0.05:
            print(f"! voiceover is {seconds:.2f}s; it will be trimmed at {total:.2f}s")
        if args.vtt:
            vtt = Path(args.vtt).resolve()
            if not vtt.exists():
                sys.exit(f"compile_horror_episode: {vtt} not found")
            cues = parse_vtt(vtt)
            if not cues:
                sys.exit(f"compile_horror_episode: no cues in {vtt}")
            shutil.copy2(vtt, audio_dir / "voiceover.vtt")
        else:
            print("! no --vtt: splitting the voiceover by caption length (approximate sync)")
            cues = proportional_cues(shots, seconds)
    else:
        collect_voices(shots, Path(args.voice_dir).resolve() if args.voice_dir else None,
                       audio_dir, args.tts, args.voice, args.speed, args.allow_missing,
                       args.force_tts)
        cues = per_shot_cues(shots)

    music: Path | None = None
    if args.music:
        music_source = Path(args.music).resolve()
        if not music_source.exists():
            sys.exit(f"compile_horror_episode: {music_source} not found")
        music = place(music_source, audio_dir, "music")
        measured = media_duration(music)
        if measured and measured + 0.05 < total:
            print(f"! music bed is {measured:.2f}s for a {total:.2f}s film (it will stop)")

    film = write_film_html(project, shots, total, args.width, args.height,
                           single_voice, music, args.music_volume, title)
    overlay = write_overlay_page(project, cues, total, args.width, args.height)

    print(f"  {film.relative_to(project)}")
    print(f"  {overlay.relative_to(project)}")
    voice_label = ("1 continuous voiceover" if single_voice
                   else f"{sum(1 for s in shots if s.voice)} voice lines")
    print(f"  {len(cues)} captions, {sum(1 for s in shots if s.clip)} clips, {voice_label}")

    if args.no_render:
        print("  --no-render: project written, nothing rendered")
        return

    output = Path(args.out)
    if not output.is_absolute():
        output = project / output
    output.parent.mkdir(parents=True, exist_ok=True)
    command = ["npx", "-y", "openfilm@latest", "render",
               "--out", str(output), "--fps", str(args.fps), "--workers", str(args.workers)]
    print("Rendering:", " ".join(command))
    result = subprocess.run(command, cwd=project)
    if result.returncode != 0:
        sys.exit(f"compile_horror_episode: openfilm render failed ({result.returncode})")
    if output.exists():
        print(f"Wrote {output} ({output.stat().st_size / 1024 / 1024:.1f} MB)")


if __name__ == "__main__":
    main()
