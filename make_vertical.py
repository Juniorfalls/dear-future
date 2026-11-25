#!/usr/bin/env python3
"""Make a 1080x1920 Shorts cut: sharp 16:9 picture, blurred fill above/below.

usage: make_vertical.py <input.mp4> <output.mp4>
"""
import subprocess
import sys
from pathlib import Path

try:
    import imageio_ffmpeg
    FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
except ImportError:
    FFMPEG = "ffmpeg"

FILTER = (
    "[0:v]split=2[bg][fg];"
    "[bg]scale=1080:1920:force_original_aspect_ratio=increase,"
    "crop=1080:1920,boxblur=36:3,eq=brightness=-0.10:saturation=0.8[bg2];"
    "[fg]scale=1080:-2[fg2];"
    "[bg2][fg2]overlay=(W-w)/2:(H-h)/2,format=yuv420p[v]"
)


def main() -> None:
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    cmd = [FFMPEG, "-y", "-v", "error", "-i", str(src),
           "-filter_complex", FILTER, "-map", "[v]", "-map", "0:a?",
           "-c:v", "libx264", "-crf", "20", "-preset", "medium",
           "-c:a", "copy", "-movflags", "+faststart", str(dst)]
    subprocess.run(cmd, check=True)
    print("VERTICAL", dst)


if __name__ == "__main__":
    main()
