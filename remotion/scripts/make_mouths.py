#!/usr/bin/env python3
"""Clean A-F mouth sprites on a skin patch matched to the pointing face."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "public" / "characters"
S = 4
W, H = 124 * S, 104 * S
CX, CY = W // 2, H // 2
SKIN = (242, 201, 142, 255)
LINE = (78, 45, 34, 255)
INNER = (104, 44, 44, 255)
TEETH = (250, 245, 224, 255)

def base():
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((CX - 45 * S, CY - 32 * S, CX + 45 * S, CY + 32 * S), fill=SKIN)
    return im, d

def finish(im, i):
    im = im.resize((124, 104), Image.LANCZOS)
    a = im.getchannel("A").filter(ImageFilter.GaussianBlur(1.0))
    im.putalpha(a)
    im.save(OUT / f"mouth_v3_{i}.png")

def oval(w, h, teeth, idx):
    im, d = base()
    w, h = w * S, h * S
    box = (CX - w // 2, CY - h // 2, CX + w // 2, CY + h // 2)
    d.ellipse(box, fill=LINE)
    inner = (box[0] + 3 * S, box[1] + 3 * S, box[2] - 3 * S, box[3] - 3 * S)
    d.ellipse(inner, fill=INNER)
    if teeth:
        d.rectangle((inner[0] + 2 * S, inner[1] + S, inner[2] - 2 * S, inner[1] + teeth * S), fill=TEETH)
    finish(im, idx)

def closed():
    im, d = base()
    d.arc((CX - 24 * S, CY - 12 * S, CX + 24 * S, CY + 12 * S), 20, 160, fill=LINE, width=3 * S)
    finish(im, 2)

oval(58, 30, 7, 0)    # A
oval(46, 26, 0, 1)    # B
closed()              # C
oval(24, 20, 0, 3)    # D
oval(34, 25, 0, 4)    # E
oval(64, 36, 9, 5)    # F
print("mouths v3 fixed")
