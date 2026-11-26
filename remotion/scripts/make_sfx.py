#!/usr/bin/env python3
"""Synthesize the three subtle cues used by the data visualizer."""
from pathlib import Path
import wave, numpy as np

OUT = Path(__file__).resolve().parent.parent / "public" / "sfx"
OUT.mkdir(parents=True, exist_ok=True)
SR = 48000

def save(name, x):
    x = np.clip(x, -1, 1)
    pcm = (x * 32767).astype(np.int16)
    with wave.open(str(OUT / name), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print(name, round(len(x)/SR, 2), "s")

def env(n, a=0.02, r=0.3):
    t = np.linspace(0, 1, n)
    up = np.minimum(t/a, 1)
    down = np.minimum((1-t)/r, 1)
    return up * down

# soft downward slide
n = int(0.62*SR); t = np.arange(n)/SR
f = 480 * np.exp(-t*2.4) + 110
phase = 2*np.pi*np.cumsum(f)/SR
save("down.wav", 0.22*np.sin(phase)*env(n, .015, .55)**1.3)

# upward two-note chime
n = int(0.65*SR); t = np.arange(n)/SR
e = np.exp(-t*3.2)
x = 0.16*np.sin(2*np.pi*659*t) + 0.13*np.sin(2*np.pi*988*t + .3)
x += 0.07*np.sin(2*np.pi*1319*t) * (t > .12)
save("up.wav", x*e*np.minimum(t/.01,1))

# low thud
n = int(0.38*SR); t = np.arange(n)/SR
x = 0.55*np.sin(2*np.pi*(78 - 20*t)*t) * np.exp(-t*11)
rng = np.random.default_rng(7)
noise = rng.normal(0, .12, n) * np.exp(-t*30)
save("thud.wav", (x + noise)*np.minimum(t/.004,1))
