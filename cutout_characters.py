#!/usr/bin/env python3
"""Chroma-key the teacher sheet into four transparent sprites and trim them."""
from pathlib import Path
from PIL import Image, ImageFilter
import numpy as np

SRC = Path("images/teacher-sheet-521398.jpg")
OUT = Path("math_engine/assets/characters")
NAMES = ["teacher_talk", "teacher_point", "teacher_write", "teacher_walk"]

im = Image.open(SRC).convert("RGB")
a = np.array(im).astype(np.int16)
r, g, b = a[..., 0], a[..., 1], a[..., 2]
# magenta screen: high red+blue, low green
mask = (r > 130) & (b > 110) & (g < 135) & ((r - g) > 45) & ((b - g) > 25)
alpha = np.where(mask, 0, 255).astype(np.uint8)
rgba = np.dstack([np.array(im), alpha])
w, h = im.size
for i, name in enumerate(NAMES):
    x0, y0 = (i % 2) * (w // 2), (i // 2) * (h // 2)
    q = Image.fromarray(rgba[y0:y0 + h // 2, x0:x0 + w // 2], "RGBA")
    box = q.getbbox()
    q = q.crop(box)
    # feather the alpha edge a little
    q = q.filter(ImageFilter.GaussianBlur(.4)) if False else q
    q.save(OUT / f"{name}.png")
    print(name, q.size)
