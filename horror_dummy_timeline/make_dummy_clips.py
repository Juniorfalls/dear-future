#!/usr/bin/env python3
"""Generate nine 3-second labelled dummy clips for the OpenFilm cut test.

Each clip is a different flat colour with a huge "SHOT N" label and a thin
border, so a hard cut is obvious in a single frame.

    python3 make_dummy_clips.py
    python3 make_dummy_clips.py --out assets/clips --seconds 3
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

COLORS = [
    "0x0b2b2b",
    "0x13294b",
    "0x3b1212",
    "0x2a2a2a",
    "0x2b1238",
    "0x28320f",
    "0x0d1f3a",
    "0x3a2410",
    "0x101c16",
]

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]


def ffmpeg_binary() -> str:
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:  # noqa: BLE001 - the message is the point
        sys.exit(f"make_dummy_clips: no ffmpeg ({type(exc).__name__}: {exc})")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default=str(Path(__file__).parent / "assets" / "clips"))
    parser.add_argument("--seconds", type=float, default=3.0)
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)
    parser.add_argument("--fps", type=int, default=30)
    args = parser.parse_args()

    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    ffmpeg = ffmpeg_binary()
    font = next((path for path in FONT_CANDIDATES if Path(path).exists()), None)
    if font is None:
        sys.exit("make_dummy_clips: no bold font found for drawtext")

    for index, color in enumerate(COLORS, 1):
        target = out / f"shot-{index:02d}.mp4"
        label = f"SHOT {index}"
        note = f"DUMMY {args.seconds:.1f}s / {color.upper()}"
        vf = ",".join([
            f"drawbox=x=24:y=24:w=iw-48:h=ih-48:color=white@0.55:t=4",
            (f"drawtext=fontfile='{font}':text='{label}':"
             "fontcolor=white:fontsize=210:x=(w-text_w)/2:y=(h-text_h)/2-40:"
             "borderw=5:bordercolor=black@0.75:"
             "shadowcolor=black@0.65:shadowx=8:shadowy=8"),
            (f"drawtext=fontfile='{font}':text='{note}':"
             "fontcolor=white@0.82:fontsize=56:x=(w-text_w)/2:y=h-190:"
             "borderw=3:bordercolor=black@0.7"),
        ])
        command = [
            ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i",
            f"color=c={color}:s={args.width}x{args.height}:r={args.fps}:d={args.seconds}",
            "-vf", vf,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-pix_fmt", "yuv420p", "-an", str(target),
        ]
        subprocess.run(command, check=True)
        print(f"  {target.name}  {target.stat().st_size / 1024:.0f} kB  {label}")

    print(f"wrote {len(COLORS)} clips to {out}")


if __name__ == "__main__":
    main()
