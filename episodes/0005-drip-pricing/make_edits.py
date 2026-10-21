"""Episode 0005 — hand-made frames from the storyboard pictures (no new generations, rule 20: no generated text).
Writes episodes/0005-drip-pricing/images/{c4,l1,m1b,m2,n4,l8}.png. Run from the repo root after the storyboard is downloaded:
  gh release download frames-0005-drip-pricing -D .cache/images/0005-drip-pricing --pattern "*.png"
  python episodes/0005-drip-pricing/make_edits.py"""
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
CACHE = ROOT / ".cache" / "images" / "0005-drip-pricing"
OUT = HERE / "images"
FRAMES = {"c4": "c4-f978b0455f", "l1": "l1-8b76d60501", "m1b": "m1b-1fea7e9bcd", "m2": "m2-8d6150208a", "n4": "n4-047244334d", "l8": "l8-03088a947b"}
INK, RED, PAPER = (30, 27, 24), (210, 69, 47), (252, 247, 233)


def load(k):
    return np.array(Image.open(CACHE / f"{FRAMES[k]}.png").convert("RGB"))


def fnt(name, size):
    for q in (ROOT / "assets" / "fonts" / name, Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")):
        if q.exists():
            return ImageFont.truetype(str(q), size)


# ---- c4: the hotel bill without the generated words (Date, Guest, Room...): glyph-sized blobs painted with paper
im = load("c4")
H, W = im.shape[:2]
x0, y0, x1, y1 = int(0.30 * W), int(0.12 * H), int(0.67 * W), int(0.90 * H)
reg = im[y0:y1, x0:x1].copy()
dark = (reg.max(2) < 150).astype(np.uint8)
n, lab, st, _ = cv2.connectedComponentsWithStats(dark, 8)
mask = np.zeros(dark.shape, np.uint8)
for k in range(1, n):
    _x, _y, w, h, a = st[k]
    if h <= 18 and w <= 24 and a < 200:
        mask[lab == k] = 255
mask = cv2.dilate(mask, np.ones((7, 7), np.uint8))
lines = (reg.max(2) < 110).astype(np.uint8)
n2, lab2, st2, _ = cv2.connectedComponentsWithStats(lines, 8)
for k in range(1, n2):
    if st2[k][2] > 40 or st2[k][3] > 40:
        mask[lab2 == k] = 0  # never paint over the ruled lines
paper = np.median(reg[reg.max(2) > 200], axis=0)
fill = np.clip(paper + np.random.default_rng(3).normal(0, 3.0, reg.shape), 0, 255).astype(np.uint8)
m = cv2.GaussianBlur(mask.astype(np.float32) / 255, (0, 0), 1.2)[..., None]
im[y0:y1, x0:x1] = (reg * (1 - m) + fill * m).astype(np.uint8)
# the two short "field" stubs under the green header go too: a clean strip for the handwritten "$9 – $95 / night"
sy0, sy1, sx0, sx1 = int(0.288 * H), int(0.308 * H), int(0.350 * W), int(0.660 * W)
strip = im[sy0:sy1, sx0:sx1]
im[sy0:sy1, sx0:sx1] = np.where(strip.max(2, keepdims=True) < 200, fill[: sy1 - sy0, : sx1 - sx0] if fill.shape[0] >= sy1 - sy0 else paper, strip)
Image.fromarray(im).save(OUT / "c4.png")

# ---- l1: the customs desk with the code-drawn $30 ticket (same ticket as o1) lying in the middle
desk = Image.open(CACHE / f"{FRAMES['l1']}.png").convert("RGB")
W, H = desk.size
tk = Image.open(OUT / "o1.png").convert("RGB")
tx0, ty0, tx1, ty1 = 250, 190, 1130, 590
ticket = tk.crop((tx0, ty0, tx1, ty1))
d = ImageDraw.Draw(ticket)  # the price, handwritten in ink as in the cold open
d.text(((410 + 740) / 2 - tx0, (460 + 550) / 2 - ty0), "$30", font=fnt("PermanentMarker-Regular.ttf", 74), fill=INK, anchor="mm")
alpha = Image.new("L", ticket.size, 0)
ImageDraw.Draw(alpha).rounded_rectangle((0, 0, ticket.width - 1, ticket.height - 1), radius=26, fill=255)
TW = int(W * 0.50)
TH = int(ticket.height * TW / ticket.width)
ticket = ticket.resize((TW, TH), Image.LANCZOS)
alpha = alpha.resize((TW, TH), Image.LANCZOS)
ANG = -4
tr = ticket.convert("RGBA")
tr.putalpha(alpha)
tr = tr.rotate(ANG, resample=Image.BICUBIC, expand=True)
cx, cy = int(W * 0.47), int(H * 0.43)
shadow = Image.new("RGBA", tr.size, (0, 0, 0, 0))
sa = np.array(tr)[..., 3]
shadow.putalpha(Image.fromarray((sa * 0.35).astype(np.uint8)).filter(__import__("PIL.ImageFilter", fromlist=["GaussianBlur"]).GaussianBlur(8)))
desk.paste(shadow, (cx - tr.width // 2 + 10, cy - tr.height // 2 + 14), shadow)
desk.paste(tr, (cx - tr.width // 2, cy - tr.height // 2), tr)
desk.save(OUT / "l1.png")
print("l1 ticket box (fractions):", round((cx - TW / 2) / W, 3), round((cy - TH / 2) / H, 3), round((cx + TW / 2) / W, 3), round((cy + TH / 2) / H, 3))

# ---- m1b: the blank laptop screen with a code-drawn checkout page (red PAY button, empty TOTAL box)
lap = Image.open(CACHE / f"{FRAMES['m1b']}.png").convert("RGB")
W, H = lap.size
d = ImageDraw.Draw(lap)
px0, py0, px1, py1 = 0.372 * W, 0.19 * H, 0.627 * W, 0.505 * H
d.rounded_rectangle((px0, py0, px1, py1), radius=14, fill=PAPER, outline=(200, 192, 176), width=2)
d.text((0.385 * W, 0.225 * H), "CHECKOUT", font=fnt("ArchivoBlack-Regular.ttf", 24), fill=INK, anchor="lm")
d.line((0.385 * W, 0.25 * H, 0.615 * W, 0.25 * H), fill=(200, 192, 176), width=2)
for k in range(3):  # three item rows, drawn as grey bars (no words)
    yy = (0.28 + k * 0.035) * H
    d.rounded_rectangle((0.39 * W, yy - 5, 0.53 * W, yy + 5), radius=4, fill=(214, 207, 192))
    d.rounded_rectangle((0.575 * W, yy - 5, 0.61 * W, yy + 5), radius=4, fill=(214, 207, 192))
d.text((0.39 * W, 0.40 * H), "TOTAL", font=fnt("ArchivoBlack-Regular.ttf", 22), fill=INK, anchor="lm")
d.rectangle((0.47 * W, 0.375 * H, 0.60 * W, 0.425 * H), outline=INK, width=3)  # empty: "$48" is written by the hand
d.rounded_rectangle((0.50 * W, 0.44 * H, 0.60 * W, 0.487 * H), radius=12, fill=RED, outline=INK, width=2)
d.text((0.55 * W, 0.4635 * H), "PAY", font=fnt("Anton-Regular.ttf", 30), fill=PAPER, anchor="mm")
lap.save(OUT / "m1b.png")

# ---- m2: the key's two-notch bit read as a letter "E" (rule 20): notches filled -> a plain solid bit, shadow squared
im = load("m2")
red = im[616:620, 720:728].reshape(-1, 3).mean(0)
ink, shd = im[610, 700].copy(), im[628, 740:748].reshape(-1, 3).mean(0)
im[620:659, 715:733] = red.astype(np.uint8)
im[612:666, 733:737] = ink
im[616:669, 737:748] = shd.astype(np.uint8)
Image.fromarray(im).save(OUT / "m2.png")

# ---- n4: the index card was generated red; "$30" is written on it in ink -> recolour the card cream, keep its shading
im = load("n4")
H, W = im.shape[:2]
f = im.astype(np.float32)
r, g, b = f[..., 0], f[..., 1], f[..., 2]
card = (r > 170) & (g < 140) & (b < 120) & (r - g > 70)
card[:, : int(0.25 * W)] = False
card[:, int(0.62 * W):] = False
lum = (0.299 * r + 0.587 * g + 0.114 * b)
ref = float(np.median(lum[card]))
cream = np.array([246, 238, 216], np.float32)
new = np.clip(cream[None, None, :] * (lum / ref)[..., None] ** 0.6, 0, 255)
m = cv2.GaussianBlur(card.astype(np.float32), (0, 0), 0.8)[..., None]
im = (f * (1 - m) + new * m).astype(np.uint8)
Image.fromarray(im).save(OUT / "n4.png")
# ---- l8: the learner "L" painted on the blank bumper plate (part of the car, so subtitles may pass over it)
car = Image.open(CACHE / f"{FRAMES['l8']}.png").convert("RGB")
W, H = car.size
ImageDraw.Draw(car).text((0.697 * W, 0.812 * H), "L", font=fnt("ArchivoBlack-Regular.ttf", int(0.062 * H)), fill=RED, anchor="mm")
car.save(OUT / "l8.png")

print("written:", ", ".join(f"images/{k}.png" for k in FRAMES))
