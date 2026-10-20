"""Hand-made frames for Case 003 (edits of existing storyboard frames — no new generations).
Writes episodes/0004-fake-sale/images/{m1,m2,e5,x6}.png. Run from the repo root after the storyboard is downloaded:
python episodes/0004-fake-sale/make_edits.py"""
import sys
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
from factory.led import led_panel  # noqa: E402

CACHE = ROOT / ".cache" / "images" / "0004-fake-sale"
OUT = HERE / "images"
OUT.mkdir(exist_ok=True)
FRAMES = {"m1": "m1-8d5af3cedf", "e5": "e5-cc01e0fb6b", "k3": "k3-28068c555c", "x6": "x6-3655986e7a"}


def load(k):
    return np.array(Image.open(CACHE / f"{FRAMES[k]}.png").convert("RGB"))


# ---- m1: the suspect tag without the painted X (the hand writes "WAS $—" and strikes it on screen)
im = load("m1")
H, W = im.shape[:2]
x0, x1, y0, y1 = int(0.37 * W), int(0.63 * W), int(0.36 * H), int(0.62 * H)
reg = im[y0:y1, x0:x1]
dark = (reg.max(2) < 90).astype(np.uint8)
dark = cv2.dilate(dark, np.ones((5, 5), np.uint8))
mask = np.zeros(im.shape[:2], np.uint8)
mask[y0:y1, x0:x1] = dark * 255
clean = cv2.inpaint(im, mask, 9, cv2.INPAINT_TELEA)
# redraw the tag's own black outline where the X crossed it (measured just below the X)
rows = slice(int(0.66 * H), int(0.80 * H))
for lo, hi in ((0.385, 0.43), (0.57, 0.615)):
    seg = im[rows, int(lo * W):int(hi * W)].max(2) < 90
    cols = np.where(seg.mean(0) > 0.5)[0]
    if len(cols):
        cx = int(lo * W) + int(cols.mean())
        th = max(3, len(cols))
        cv2.line(clean, (cx, y0), (cx, y1), (30, 27, 24), th, cv2.LINE_AA)
Image.fromarray(clean).save(OUT / "m1.png")

# ---- m2: a digital countdown on the grey booking wall (same LED style as the laptop timers)
bg = np.full((768, 1376, 3), (200, 200, 196), np.uint8)
bg = np.clip(bg.astype(np.int16) + np.random.default_rng(3).normal(0, 3, bg.shape[:2])[..., None], 0, 255).astype(np.uint8)
pan = led_panel("02:59:59", "Sale ends in", height=240)
k = 560 / pan.shape[1]
pan = cv2.resize(pan, (560, int(pan.shape[0] * k)), interpolation=cv2.INTER_AREA)
pil = Image.fromarray(bg).convert("RGBA")
sh = Image.new("RGBA", (pan.shape[1] + 40, pan.shape[0] + 40), (0, 0, 0, 0))
ImageDraw.Draw(sh).rounded_rectangle((20, 26, pan.shape[1] + 20, pan.shape[0] + 26), radius=24, fill=(0, 0, 0, 90))
from PIL import ImageFilter  # noqa: E402
sh = sh.filter(ImageFilter.GaussianBlur(10))
px, py = (1376 - pan.shape[1]) // 2, (768 - pan.shape[0]) // 2
pil.alpha_composite(sh, (px - 20, py - 20))
pil.alpha_composite(Image.fromarray(pan), (px, py))
pil.convert("RGB").save(OUT / "m2.png")

# ---- e5: all mattresses green/white (like e3); sale tags red on the left pan, one white tag on the right
im = load("e5")
H, W = im.shape[:2]
hsv = cv2.cvtColor(im, cv2.COLOR_RGB2HSV).astype(np.int16)
green_ref = im[int(0.57 * H), int(0.25 * W)].astype(np.float32)  # the green mattress on the left pan
for (a, b, c, d) in [(0.24, 0.40, 0.42, 0.63), (0.59, 0.82, 0.35, 0.53)]:
    ys, ye, xs_, xe = int(c * H), int(d * H), int(a * W), int(b * W)
    sub = im[ys:ye, xs_:xe].astype(np.float32)
    r, g, bl = sub[..., 0], sub[..., 1], sub[..., 2]
    red = (r > g + 50) & (r > bl + 50)
    lum = (0.3 * r + 0.59 * g + 0.11 * bl) / max(1.0, float(0.3 * 210 + 0.59 * 69 + 0.11 * 47))
    tgt = green_ref[None, None, :] * np.clip(lum, 0.6, 1.4)[..., None]
    sub[red] = np.clip(tgt[red], 0, 255)
    im[ys:ye, xs_:xe] = sub.astype(np.uint8)
pil = Image.fromarray(im).convert("RGBA")
d = ImageDraw.Draw(pil)
def tag(cx, cy, s, fill, ang):
    t = Image.new("RGBA", (int(s * 1.6), int(s * 1.6)), (0, 0, 0, 0))
    td = ImageDraw.Draw(t)
    w, h = s * 0.55, s * 0.9
    ox, oy = (t.width - w) / 2, (t.height - h) / 2
    poly = [(ox + w * 0.2, oy), (ox + w * 0.8, oy), (ox + w, oy + h * 0.2), (ox + w, oy + h), (ox, oy + h), (ox, oy + h * 0.2)]
    td.polygon(poly, fill=fill, outline=(30, 27, 24, 255))
    td.line(poly + [poly[0]], fill=(30, 27, 24, 255), width=3)
    r = s * 0.05
    td.ellipse((ox + w / 2 - r, oy + h * 0.14 - r, ox + w / 2 + r, oy + h * 0.14 + r), fill=(250, 246, 236, 255), outline=(30, 27, 24, 255))
    t = t.rotate(ang, resample=Image.BICUBIC)
    pil.alpha_composite(t, (int(cx * W - t.width / 2), int(cy * H - t.height / 2)))
RED, WHITE = (210, 69, 47, 255), (250, 246, 236, 255)
tag(0.235, 0.555, 80, RED, 18)
tag(0.355, 0.495, 80, RED, -12)
tag(0.775, 0.425, 80, WHITE, -15)
pil.convert("RGB").save(OUT / "e5.png")

# ---- x6: Larry's mixer (the k3 drawing) on the x6 green band
k3 = load("k3")
x6 = load("x6")
H, W = x6.shape[:2]
cream = np.median(np.concatenate([x6[:20, :20].reshape(-1, 3), x6[-20:, -20:].reshape(-1, 3)]), axis=0)
band = x6[int(0.45 * H), int(0.08 * W)].astype(np.uint8)
out = np.full_like(x6, cream.astype(np.uint8))
out = np.clip(out.astype(np.int16) + np.random.default_rng(5).normal(0, 2.5, out.shape[:2])[..., None], 0, 255).astype(np.uint8)
out[int(0.19 * H):int(0.70 * H), int(0.05 * W):int(0.95 * W)] = band
crop = k3[int(0.08 * H):int(0.80 * H), int(0.28 * W):int(0.69 * W)]
back = np.median(k3[5:30, int(0.6 * W):int(0.9 * W)].reshape(-1, 3), axis=0)
diff = np.abs(crop.astype(np.float32) - back).max(2)
m8 = (diff > 24).astype(np.uint8)
m8 = cv2.morphologyEx(m8, cv2.MORPH_CLOSE, np.ones((11, 11), np.uint8))
cnts, _ = cv2.findContours(m8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
m8 = np.zeros_like(m8)
for c in cnts:
    if cv2.contourArea(c) > 0.01 * m8.size:
        cv2.drawContours(m8, [c], -1, 1, -1)
m = cv2.GaussianBlur(m8.astype(np.float32), (0, 0), 1.2)
s = 0.78 * H / crop.shape[0]
cw, ch = int(crop.shape[1] * s), int(crop.shape[0] * s)
crop = cv2.resize(crop, (cw, ch), interpolation=cv2.INTER_CUBIC)
m = cv2.resize(m, (cw, ch))[..., None]
ox, oy = (W - cw) // 2, int(0.85 * H) - ch  # sits high: the base and its plate stay above the subtitles
reg = out[oy:oy + ch, ox:ox + cw].astype(np.float32)
out[oy:oy + ch, ox:ox + cw] = (reg * (1 - m) + crop * m).astype(np.uint8)
# a small brushed-metal model plate on the front of the base (the target of the "model number" circle)
pl = Image.fromarray(out).convert("RGBA")
d = ImageDraw.Draw(pl)
PX, PY, PW, PH = 0.365, 0.808, 0.06, 0.026
bx0, by0, bx1, by1 = int((PX - PW / 2) * W), int((PY - PH / 2) * H), int((PX + PW / 2) * W), int((PY + PH / 2) * H)
d.rounded_rectangle((bx0, by0, bx1, by1), radius=5, fill=(196, 196, 186, 255), outline=(30, 27, 24, 255), width=3)
for k in range(1, 4):
    yy = by0 + (by1 - by0) * k // 4
    d.line((bx0 + 8, yy, bx1 - 8, yy), fill=(120, 120, 112, 255), width=2)
for cxp in (bx0 + 6, bx1 - 6):
    d.ellipse((cxp - 3, (by0 + by1) // 2 - 3, cxp + 3, (by0 + by1) // 2 + 3), fill=(30, 27, 24, 255))
pl.convert("RGB").save(OUT / "x6.png")
print("edits written:", sorted(p.name for p in OUT.iterdir()))
