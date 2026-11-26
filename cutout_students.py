#!/usr/bin/env python3
"""Chroma-key the three-student sheet into individual transparent sprites."""
from pathlib import Path
from PIL import Image
import numpy as np

SRC = Path("images/students-sheet-af01da.jpg")
OUT = Path("math_engine/assets/characters")
im = Image.open(SRC).convert("RGB")
a = np.array(im).astype(np.int16)
r, g, b = a[..., 0], a[..., 1], a[..., 2]
mask = (r > 130) & (b > 110) & (g < 135) & ((r - g) > 45) & ((b - g) > 25)
rgba = np.dstack([np.array(im), np.where(mask, 0, 255).astype(np.uint8)])
w, h = im.size
for i in range(3):
    q = Image.fromarray(rgba[:, i * w // 3:(i + 1) * w // 3], "RGBA")
    q = q.crop(q.getbbox())
    q.save(OUT / f"student_{i+1}.png")
    print("student", i + 1, q.size)
