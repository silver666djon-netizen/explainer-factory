"""Builds assets/hands/hand_stamp.png (code-drawn, from the existing marker hand — no generation):
the hand comes from above gripping a rubber stamp (wooden handle + knob, wooden mount, red rubber base).
Tip = bottom centre of the rubber (the point that touches the paper)."""
import json, math
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw

HD = Path(__file__).resolve().parent.parent / "assets" / "hands"
src = np.array(Image.open(HD / "hand_marker_under.png").convert("RGBA"))
H0, W0 = src.shape[:2]
tip = np.array([691.0, 11.0])
back = np.array([1090.0, 480.0])  # far end of the marker
r, g, b, a = [src[..., i].astype(int) for i in range(4)]
red = (r > g + 95) & (r > b + 95) & (a > 0)
# recolour the marker body to wood (fingers in front of it stay; black outlines stay)
lum = (0.3 * r + 0.59 * g + 0.11 * b) / 120.0
k = np.clip(lum, 0.55, 1.35)
for i, c in enumerate((176, 120, 66)):
    ch = src[..., i].astype(np.float32)
    ch[red] = np.clip(c * k[red], 0, 255)
    src[..., i] = ch.astype(np.uint8)
# rotate so the marker axis points straight down, tip at the bottom
v = tip - back
ang = math.degrees(math.atan2(v[1], v[0]))  # direction back -> tip
rot = 90 - ang  # make it +90 (down)
L = int(math.hypot(W0, H0)) + 200
M = cv2.getRotationMatrix2D((float(tip[0]), float(tip[1])), -rot, 1.0)
M[0, 2] += L / 2 - tip[0]
M[1, 2] += L * 0.75 - tip[1]
hand = cv2.warpAffine(src, M, (L, L), flags=cv2.INTER_LINEAR, borderValue=(0, 0, 0, 0))
cx, ty = L // 2, int(L * 0.75)  # tip after rotation
mlen = float(np.hypot(*v))
# stamp: drawn behind the hand (handle shows where the marker was)
st = Image.new("RGBA", (L, L), (0, 0, 0, 0))
d = ImageDraw.Draw(st)
ink = (30, 27, 24, 255)
wood, wood_d = (176, 120, 66, 255), (128, 82, 42, 255)
hw = 44  # handle half width (≈ the marker's width)
top = ty - mlen - 40
base_top = ty - 190
d.ellipse((cx - 88, top - 40, cx + 88, top + 110), fill=wood, outline=ink, width=8)  # knob
d.ellipse((cx - 50, top - 10, cx - 5, top + 30), fill=(214, 160, 104, 255))
out = Image.alpha_composite(st, Image.fromarray(hand))
fr = Image.new("RGBA", (L, L), (0, 0, 0, 0))
fd = ImageDraw.Draw(fr)
fd.rounded_rectangle((cx - 190, base_top, cx + 190, ty - 50), radius=14, fill=wood_d, outline=ink, width=8)
fd.line((cx - 170, base_top + 22, cx + 170, base_top + 22), fill=(160, 108, 60, 255), width=6)
fd.rectangle((cx - 180, ty - 54, cx + 180, ty), fill=(205, 52, 38, 255), outline=ink, width=8)
out = Image.alpha_composite(out, fr)
arr = np.array(out)
ys, xs = np.where(arr[..., 3] > 0)
x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ty + 6
arr = arr[y0:y1, x0:x1]
Image.fromarray(arr).save(HD / "hand_stamp.png")
meta = json.loads((HD / "hand.json").read_text())
meta["stamp"] = {"tip": [int(cx - x0), int(ty - y0)], "ref": 1024}
(HD / "hand.json").write_text(json.dumps(meta))
print("hand_stamp.png", arr.shape, meta["stamp"])
