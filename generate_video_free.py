#!/usr/bin/env python3
"""
generate_video_free.py — local, free AnimateDiff clip generator for
"The End of the Corridor".

No paid API: weights are the public guoyww motion adapter + an SD1.5 base,
run on the local GPU (target hardware: Tesla T4, 15 GB).

T4 rules baked in:
  * float16 only      — Turing (compute 7.5) has no bf16
  * no xformers       — attention slicing + SDPA instead
  * VAE slice + tile  — decode of 24 frames is the peak, not the UNet
  * HF cache off Drive — /content/drive has ~9 GB spare; / has ~113 GB

Usage
  python3 generate_video_free.py --list
  python3 generate_video_free.py --dry-run --only 1
  python3 generate_video_free.py --only 1 --frames 24 --fps 8
  python3 generate_video_free.py --all
"""
import argparse
import gc
import json
import os
import pathlib
import subprocess
import sys
import time

# Keep multi-GB weights on the fast, roomy overlay FS, never the Drive mount.
os.environ.setdefault("HF_HOME", "/root/.cache/huggingface")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

ROOT = pathlib.Path(__file__).resolve().parent
SCHEMA_PATH = ROOT / "episode_schema.json"
OUTDIR = ROOT / "out" / "video"

ADAPTER_ID = "guoyww/animatediff-motion-adapter-v1-5-2"

# Coarse VRAM ladder. Each rung is tried only if the one before it OOMs,
# so a 384x384/16-frame fallback is one crash away, not a manual edit.
LADDER = [
    ("full-gpu", {"width": 512, "height": 512, "frames": None, "offload": False}),
    ("cpu-offload", {"width": 512, "height": 512, "frames": None, "offload": True}),
    ("384-offload", {"width": 384, "height": 384, "frames": None, "offload": True}),
    ("320-16f-offload", {"width": 320, "height": 320, "frames": 16, "offload": True}),
]


def log(msg):
    print(f"[video] {msg}", flush=True)


def die(msg, code=1):
    print(f"[video] ERROR: {msg}", file=sys.stderr, flush=True)
    sys.exit(code)


def load_schema(path=SCHEMA_PATH):
    if not path.exists():
        die(f"missing shot list: {path}")
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        die(f"{path.name} is not valid JSON: {exc}")
    shots = data.get("shots") or []
    if not shots:
        die(f"{path.name} has no 'shots' array")
    for shot in shots:
        for key in ("id", "slug", "prompt"):
            if key not in shot:
                die(f"shot {shot.get('id', '?')} is missing '{key}'")
    return data


def pick_shots(data, only=None, run_all=False):
    shots = data["shots"]
    if run_all:
        return shots
    if only is None:
        return shots[:1]
    for shot in shots:
        if str(shot["id"]) == str(only):
            return [shot]
    ids = ", ".join(str(s["id"]) for s in shots)
    die(f"--only {only} does not exist; ids are: {ids}")


def vram_report():
    """Peak + current VRAM, in GiB. Silent if CUDA is unavailable."""
    try:
        import torch
    except ImportError:
        return "torch missing"
    if not torch.cuda.is_available():
        return "no CUDA device"
    peak = torch.cuda.max_memory_allocated() / 1024**3
    held = torch.cuda.memory_allocated() / 1024**3
    total = torch.cuda.get_device_properties(0).total_memory / 1024**3
    return f"VRAM peak {peak:.2f} GiB / held {held:.2f} / total {total:.1f}"


def free_vram():
    gc.collect()
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.reset_peak_memory_stats()
    except ImportError:
        pass


def write_mp4(frames, path, fps):
    """Encode PIL frames to H.264 with the ffmpeg that imageio ships.

    Avoids cv2 entirely, and pins odd/even dimensions so yuv420p cannot fail.
    """
    import imageio_ffmpeg

    if not frames:
        die("no frames returned by the pipeline")
    width, height = frames[0].size
    if width % 2 or height % 2:
        die(f"frame size {width}x{height} must be even for yuv420p")

    exe = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        exe, "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{width}x{height}", "-r", str(fps), "-i", "-",
        "-an", "-c:v", "libx264", "-preset", "slow", "-crf", "18",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(path),
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        for frame in frames:
            proc.stdin.write(frame.convert("RGB").tobytes())
        proc.stdin.close()
    except BrokenPipeError:
        die(f"ffmpeg died early: {proc.stderr.read().decode()[:500]}")
    err = proc.stderr.read().decode()
    if proc.wait() != 0:
        die(f"ffmpeg failed: {err[:500]}")
    return path

def build_pipe(model_id, offload=True):
    """Load adapter + base. offload=True keeps the UNet on CPU between steps."""
    import torch
    from diffusers import AnimateDiffPipeline, DDIMScheduler, MotionAdapter

    t0 = time.perf_counter()
    adapter = MotionAdapter.from_pretrained(ADAPTER_ID, dtype=torch.float16)
    log(f"motion adapter loaded in {time.perf_counter() - t0:.1f}s")

    t0 = time.perf_counter()
    pipe = AnimateDiffPipeline.from_pretrained(
        model_id, motion_adapter=adapter, dtype=torch.float16
    )
    # AnimateDiff needs clip_sample=False and a linear beta schedule.
    pipe.scheduler = DDIMScheduler.from_pretrained(
        model_id,
        subfolder="scheduler",
        clip_sample=False,
        timestep_spacing="linspace",
        beta_schedule="linear",
        steps_offset=1,
    )
    log(f"base model loaded in {time.perf_counter() - t0:.1f}s")

    # Denoise-of-24-frames peak and decode peak both live here.
    pipe.vae.enable_slicing()
    pipe.vae.enable_tiling()
    pipe.enable_attention_slicing()
    pipe.set_progress_bar_config(disable=False)

    if offload:
        pipe.enable_model_cpu_offload()
    else:
        pipe.to("cuda")
    return pipe


def generate(pipe, prompt, negative, seed, width, height, frames, steps, guidance):
    import torch

    gen = torch.Generator("cpu").manual_seed(int(seed))
    result = pipe(
        prompt=prompt,
        negative_prompt=negative,
        num_frames=frames,
        width=width,
        height=height,
        guidance_scale=guidance,
        num_inference_steps=steps,
        generator=gen,
    )
    return result.frames[0]


class Runner:
    """One loaded pipeline, reused across shots.

    Model load is now paid once per run instead of once per clip; the rung
    only ever moves down, so a clip that OOMed at 512x512 makes every later
    clip start from the reduced setting instead of retrying a known-bad one.
    """

    def __init__(self, data, args):
        base = data.get("base", {})
        self.model_id = args.model or base.get("model")
        if not self.model_id:
            die("no model id: set 'base.model' in the schema or pass --model")
        self.args = args
        self.base = base
        self.negative_default = data.get("negative_prompt", "")
        self.rung_idx = 0
        self.pipe = None
        self.loaded_offload = None
        self.load_seconds = 0.0

    def _ensure_pipe(self, rung):
        if self.pipe is not None and self.loaded_offload == rung["offload"]:
            return self.pipe
        self._dispose()
        t0 = time.perf_counter()
        self.pipe = build_pipe(self.model_id, offload=rung["offload"])
        self.loaded_offload = rung["offload"]
        took = time.perf_counter() - t0
        self.load_seconds += took
        log(f"pipeline ready in {took:.1f}s; {vram_report()}")
        return self.pipe

    def _dispose(self):
        self.pipe = None
        self.loaded_offload = None
        free_vram()

    def run(self, shot):
        """Generate one shot, stepping down LADDER on CUDA OOM."""
        import torch

        a, base = self.args, self.base
        default_frames = a.frames or base.get("frames", 24)
        fps = a.fps or base.get("fps", 8)
        steps = a.steps or base.get("steps", 25)
        guidance = a.guidance if a.guidance is not None else base.get("guidance", 7.0)
        width = a.width or base.get("width", 512)
        height = a.height or base.get("height", 512)
        negative = a.negative or shot.get("negative_prompt") or self.negative_default
        last_error = None

        while True:
            if self.rung_idx >= len(LADDER):
                die(f"every rung OOMed; last error: {last_error}")
            rung_name, cfg = LADDER[self.rung_idx]
            if a.no_offload and cfg["offload"]:
                self.rung_idx += 1
                continue

            w = min(width, cfg["width"])
            h = min(height, cfg["height"])
            n = cfg["frames"] if cfg["frames"] else default_frames
            log(f"rung '{rung_name}': {w}x{h}, {n} frames, {steps} steps, {guidance} cfg")
            free_vram()
            try:
                pipe = self._ensure_pipe(cfg)
                t1 = time.perf_counter()
                frames = generate(pipe, shot["prompt"], negative, shot.get("seed", 0),
                                  w, h, n, steps, guidance)
                elapsed = time.perf_counter() - t1
                log(f"denoised {n} frames in {elapsed:.1f}s ({elapsed / n:.2f}s/frame); {vram_report()}")

                out = OUTDIR / f"{shot['id']:02d}-{shot['slug']}.mp4"
                t2 = time.perf_counter()
                write_mp4(frames, out, fps)
                log(f"encoded {len(frames)} frames @ {fps}fps in {time.perf_counter() - t2:.1f}s")
                return out, {
                    "rung": rung_name, "width": w, "height": h,
                    "frames": len(frames), "fps": fps, "steps": steps,
                    "guidance": guidance, "seconds": round(elapsed, 1),
                    "vram": vram_report(),
                }
            except torch.cuda.OutOfMemoryError as exc:
                last_error = exc
                log(f"CUDA OOM on '{rung_name}' — dropping to the next rung")
                self.rung_idx += 1
                self._dispose()


def dry_run(shots, data, args):
    base = data.get("base", {})
    log("DRY RUN — nothing is loaded, downloaded or written")
    log(f"episode: {data.get('episode')} ({len(data.get('shots', []))} shots on disk)")
    log(f"model:   {args.model or base.get('model')}")
    log(f"adapter: {ADAPTER_ID}")
    for shot in shots:
        n = args.frames or base.get("frames", 24)
        w = args.width or base.get("width", 512)
        h = args.height or base.get("height", 512)
        log(f"  shot {shot['id']:>2} {shot['slug']:<24} {w}x{h} {n}f seed {shot.get('seed')}")
        log(f"        {shot['prompt'][:90]}...")
    log(f"output dir: {OUTDIR}")
    log("DRY RUN OK")


def main(argv=None):
    p = argparse.ArgumentParser(description="Free local AnimateDiff clip generator")
    p.add_argument("--only", type=int, help="generate a single shot by id")
    p.add_argument("--all", action="store_true", help="generate every shot in the schema")
    p.add_argument("--frames", type=int, help="frame count (overrides schema base)")
    p.add_argument("--fps", type=int, help="output fps (overrides schema base)")
    p.add_argument("--steps", type=int, help="denoise steps (overrides schema base)")
    p.add_argument("--guidance", type=float, help="CFG scale")
    p.add_argument("--width", type=int)
    p.add_argument("--height", type=int)
    p.add_argument("--seed", type=int, help="force one seed for every shot")
    p.add_argument("--model", help="override base.model")
    p.add_argument("--negative", help="override the shared negative prompt")
    p.add_argument("--no-offload", action="store_true", help="GPU-resident only")
    p.add_argument("--skip-existing", action="store_true",
                   help="skip shots whose mp4 already exists (resume a batch)")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--list", action="store_true")
    args = p.parse_args(argv)

    data = load_schema()

    if args.list:
        for shot in data["shots"]:
            print(f"{shot['id']:>2}  {shot['slug']:<24} {shot['title']}")
        return 0

    shots = pick_shots(data, only=args.only, run_all=args.all)
    if args.seed is not None:
        for shot in shots:
            shot["seed"] = args.seed

    if args.skip_existing:
        kept = []
        for shot in shots:
            existing = OUTDIR / f"{shot['id']:02d}-{shot['slug']}.mp4"
            if existing.exists():
                log(f"skip shot {shot['id']}: {existing.name} already exists")
            else:
                kept.append(shot)
        shots = kept
        if not shots:
            log("nothing to do — every requested clip already exists")
            return 0

    if args.dry_run:
        dry_run(shots, data, args)
        return 0

    if not args.only and not args.all:
        log("no --only/--all given; defaulting to shot 1")

    started = time.perf_counter()
    runner = Runner(data, args)
    results = []
    for i, shot in enumerate(shots, 1):
        log(f"=== shot {shot['id']}/{len(data['shots'])}: {shot['title']} ({i}/{len(shots)}) ===")
        out, info = runner.run(shot)
        size_mb = out.stat().st_size / 1024**2
        log(f"saved {out.relative_to(ROOT)} ({size_mb:.2f} MB) on rung '{info['rung']}'")
        results.append({"shot": shot["id"], "file": str(out.relative_to(ROOT)), **info})

    total = time.perf_counter() - started
    each = total / len(results) if results else 0.0
    log(f"DONE — {len(results)} clip(s) in {total:.1f}s ({each:.1f}s each)")
    if runner.load_seconds:
        log(f"model load {runner.load_seconds:.1f}s total across the whole batch "
            f"({runner.rung_idx} rung step(s) down, {len(LADDER)} available)")

    # keep earlier clips in the manifest so a later --skip-existing run
    # does not erase the shots it did not touch
    manifest = OUTDIR / "manifest.json"
    previous = []
    if manifest.exists():
        try:
            previous = json.loads(manifest.read_text()).get("clips", [])
        except json.JSONDecodeError:
            previous = []
    by_shot = {c.get("shot"): c for c in previous}
    for result in results:
        by_shot[result["shot"]] = result
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps({
        "episode": data.get("episode"),
        "model": runner.model_id,
        "clips": [by_shot[k] for k in sorted(by_shot) if k is not None],
    }, indent=2))
    log(f"manifest: {manifest.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
