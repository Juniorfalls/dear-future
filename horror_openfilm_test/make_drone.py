#!/usr/bin/env python3
"""Synthesise the 30-second drone under horror_openfilm_test.

Pure standard library: a low beating drone, a sub, filtered noise and three
resonant creaks, faded in and out so the loop has no click at either end.
"""
import math
import random
import struct
import wave
from pathlib import Path

RATE = 48_000
DURATION = 30.0
N = int(RATE * DURATION)
OUT = Path(__file__).parent / "assets" / "drone.wav"

rng = random.Random(7)
lp = 0.0
samples = []


def env_at(t):
    fade_in = min(1.0, t / 3.0)
    fade_out = min(1.0, max(0.0, (DURATION - t) / 2.5))
    return fade_in * fade_out


def creak(t, start, freq, amp, decay):
    if t < start:
        return 0.0
    d = t - start
    if d > 1.6:
        return 0.0
    return amp * math.sin(2 * math.pi * freq * d) * math.exp(-d / decay)


for i in range(N):
    t = i / RATE

    tremolo = 0.78 + 0.22 * math.sin(2 * math.pi * 0.06 * t)
    drone = (
        0.26 * math.sin(2 * math.pi * 41.20 * t)
        + 0.20 * math.sin(2 * math.pi * 41.35 * t + 1.1)
        + 0.10 * math.sin(2 * math.pi * 82.40 * t + 0.4)
        + 0.06 * math.sin(2 * math.pi * 61.70 * t + 2.0)
    )
    sub = 0.12 * math.sin(2 * math.pi * 27.5 * t) * (0.6 + 0.4 * math.sin(2 * math.pi * 0.03 * t))

    white = rng.uniform(-1.0, 1.0)
    lp += 0.0025 * (white - lp)
    hiss = lp * (0.10 + 0.05 * math.sin(2 * math.pi * 0.045 * t + 0.7))

    creaks = (
        creak(t, 7.6, 196.0, 0.045, 0.35)
        + creak(t, 13.1, 233.0, 0.035, 0.30)
        + creak(t, 22.4, 174.0, 0.040, 0.40)
    )

    # A low hit right as the hallway appears.
    thump = creak(t, 15.0, 44.0, 0.10, 0.45)

    value = (drone + sub + hiss + creaks + thump) * env_at(t) * tremolo
    samples.append(math.tanh(value * 1.2))

peak = max(1e-9, max(abs(v) for v in samples))
gain = 0.62 / peak
pcm = b"".join(struct.pack("<h", int(max(-1.0, min(1.0, v * gain)) * 32767)) for v in samples)

with wave.open(str(OUT), "wb") as wav:
    wav.setnchannels(1)
    wav.setsampwidth(2)
    wav.setframerate(RATE)
    wav.writeframes(pcm)

print(f"wrote {OUT}: {DURATION:.0f}s, {RATE} Hz, peak {gain * peak:.2f}")
