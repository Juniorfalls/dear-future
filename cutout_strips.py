#!/usr/bin/env python3
"""Split magenta strips into 6 normalized transparent frames each."""
from pathlib import Path
from PIL import Image
import numpy as np
from scipy import ndimage

OUT = Path("math_engine/assets/characters")
JOBS = [("images/teacher-walk-strip-76dc40.jpg", "teacher_walk"),
        ("images/teacher-talk-strip-cfa467.jpg", "teacher_talk")]

def frames(src):
    im = Image.open(src).convert("RGB"); a = np.array(im).astype(np.int16)
    # sample the magenta screen from the border and key by colour distance
    border = np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]])
    bg = np.median(border, axis=0)
    dist = np.sqrt(((a - bg) ** 2).sum(2))
    fg = dist > 40

    lab, n = ndimage.label(fg)
    boxes = []
    for i in range(1, n + 1):
        ys, xs = np.where(lab == i)
        if len(xs) < 4000: continue
        boxes.append([xs.min(), ys.min(), xs.max() + 1, ys.max() + 1])
    widths = sorted(b[2] - b[0] for b in boxes)
    med = widths[0]
    split = []
    for x0, y0, x1, y1 in boxes:
        if x1 - x0 > med * 1.55:
            counts = [fg[y0:y1, x].sum() for x in range(x0 + int((x1 - x0) * .3), x0 + int((x1 - x0) * .7))]
            cut = x0 + int((x1 - x0) * .3) + int(np.argmin(counts))
            split += [[x0, y0, cut, y1], [cut, y0, x1, y1]]
        else:
            split.append([x0, y0, x1, y1])
    boxes = split
    boxes.sort(key=lambda b: b[0])
    assert len(boxes) == 6, [b[2] - b[0] for b in boxes]
    crops = [im.crop(b).convert("RGBA") for b in boxes]
    # alpha from the same mask per crop
    rgba = []
    for b in boxes:
        crop = im.crop(b)
        ca = np.array(crop).astype(np.int16)
        d = np.sqrt(((ca - bg) ** 2).sum(2))
        alpha = np.clip((d - 95) / 45, 0, 1) * 255
        rgba.append(Image.fromarray(np.dstack([np.array(crop), alpha.astype(np.uint8)]), "RGBA"))
    W = max(c.width for c in rgba) + 20; H = max(c.height for c in rgba) + 20
    out = []
    for c in rgba:
        canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        canvas.paste(c, ((W - c.width) // 2, H - c.height - 10), c)
        out.append(canvas)
    return out

for src, prefix in JOBS:
    fs = frames(src)
    for i, f in enumerate(fs):
        f.save(OUT / f"{prefix}_{i}.png")
    print(prefix, len(fs), fs[0].size)
