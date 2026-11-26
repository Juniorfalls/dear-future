#!/usr/bin/env python3
"""Render the three.js math classroom with Playwright, then mux edge-tts voice."""
import argparse, base64, functools, http.server, socketserver, subprocess, sys, threading
from pathlib import Path

import imageio_ffmpeg
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
PORT = 8137
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
OUT = ROOT / "out" / "math_engine"


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def serve():
    handler = functools.partial(Quiet, directory=str(ROOT))
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("127.0.0.1", PORT), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stills", type=str, default="", help="comma seconds: save PNGs, no video")
    ap.add_argument("--out", default="out/math_engine/math-classroom-2.5d.mp4")
    ap.add_argument("--format", choices=["landscape", "vertical"], default="landscape")
    ap.add_argument("--gl", choices=["swiftshader", "egl", "angle-gl", "default"], default="egl")
    ap.add_argument("--internal", type=float, default=.667, help="3D render scale (1 = full output size)")
    ap.add_argument("--duration", type=float, default=60.0)
    o = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    server = serve()

    with sync_playwright() as p:
        gl = {"swiftshader": ["--use-angle=swiftshader", "--use-gl=angle", "--enable-unsafe-swiftshader"],
              "egl": ["--use-gl=egl", "--enable-unsafe-swiftshader"],
              "angle-gl": ["--use-gl=angle", "--use-angle=gl", "--ignore-gpu-blocklist"],
              "default": []}[o.gl]
        browser = p.chromium.launch(args=gl + ["--ignore-gpu-blocklist", "--disable-dev-shm-usage"])
        size = (1080, 1920) if o.format == "vertical" else (1920, 1080)
        page = browser.new_page(viewport={"width": size[0], "height": size[1]}, device_scale_factor=1)
        errs = []
        page.on("pageerror", lambda e: errs.append(str(e)))
        page.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        page.goto(f"http://127.0.0.1:{PORT}/math_engine/index.html?format={o.format}&scale={o.internal}")
        try:
            page.wait_for_function("window.READY === true", timeout=120000)
        except Exception:
            print("LOAD FAILED", errs[:5]); sys.exit(1)

        if o.stills:
            for s in [float(v) for v in o.stills.split(",")]:
                r = page.evaluate("t=>window.renderFrame(t)", s)
                (OUT / f"still-{s:05.2f}.png").write_bytes(base64.b64decode(r.split(",")[1]))
                print("still", s)
            browser.close(); server.shutdown(); return

        frames = int(o.duration * 30)
        silent = OUT / "silent.mp4"
        proc = subprocess.Popen([FFMPEG, "-y", "-loglevel", "error", "-f", "image2pipe",
                                 "-framerate", "30", "-c:v", "mjpeg", "-i", "-",
                                 "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                                 "-pix_fmt", "yuv420p", str(silent)], stdin=subprocess.PIPE)
        for i in range(frames):
            r = page.evaluate("t=>window.renderFrame(t)", i / 30)
            proc.stdin.write(base64.b64decode(r.split(",")[1]))
            if i % 30 == 0:
                print("frame", i, "/", frames, flush=True)
        proc.stdin.close(); proc.wait()
        browser.close()
    server.shutdown()

    final = ROOT / o.out
    final.parent.mkdir(parents=True, exist_ok=True)
    cmd = [FFMPEG, "-y", "-loglevel", "error", "-i", str(silent),
           "-i", str(ROOT / "math_engine/assets/vo.wav"),
           "-filter_complex", "[1:a]loudnorm=I=-16:TP=-1.5:LRA=9,apad[a]",
           "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
           "-shortest", "-movflags", "+faststart", str(final)]
    subprocess.run(cmd, check=True)
    print("READY", final, f"{final.stat().st_size/1e6:.1f} MB")
    if errs:
        print("console errors:", errs[:3])


if __name__ == "__main__":
    main()
