#!/usr/bin/env python3
"""Recut static teacher/student sprites with a background-distance matte."""
from pathlib import Path
from PIL import Image
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "public" / "characters"
SHEET = Path("images/teacher-sheet-521398.jpg")
STUDENTS = Path("images/students-sheet-af01da.jpg")

def cut(im, box):
    a = np.array(im.crop(box)).astype(np.int16)
    border = np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]])
    bg = np.median(border, axis=0)
    d = np.sqrt(((a - bg) ** 2).sum(2))
    alpha = np.clip((d - 95) / 45, 0, 1) * 255
    q = Image.fromarray(np.dstack([a.astype(np.uint8), alpha.astype(np.uint8)]), "RGBA")
    return q.crop(q.getbbox())

im = Image.open(SHEET).convert("RGB"); w, h = im.size
for i, name in enumerate(["teacher_talk", "teacher_point", "teacher_write", "teacher_walk"]):
    q = cut(im, ((i % 2) * w // 2, (i // 2) * h // 2, (i % 2 + 1) * w // 2, (i // 2 + 1) * h // 2))
    q.save(OUT / f"{name}.png"); print(name, q.size)

ims = Image.open(STUDENTS).convert("RGB"); w, h = ims.size
for i in range(3):
    q = cut(ims, (i * w // 3, 0, (i + 1) * w // 3, h))
    q.save(OUT / f"student_{i+1}.png"); print("student", i + 1, q.size)
