"""Russian pictures with words baked in (code-drawn, no generations): the next-case ticket and the m2 LED mugshot.
Needs the Cyrillic fonts in assets/fonts (python tools/fonts_cyr.py <fonts-cyr download>).
python episodes/0004-fake-sale/lang/make_ru_assets.py"""
import os
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
os.environ["FACTORY_LANG"] = "ru"
from factory.led import led_panel  # noqa: E402

OUT = HERE / "ru"
(OUT / "images").mkdir(parents=True, exist_ok=True)
F = ROOT / "assets" / "fonts"


def fnt(name, size):
    return ImageFont.truetype(str(F / name), size)


# ---- the next-case ticket (same layout as next_ticket.png)
W, H = 1376, 768
im = Image.new("RGB", (W, H), (243, 233, 210))
d = ImageDraw.Draw(im)
ink, red, paper = (30, 27, 24), (210, 69, 47), (252, 247, 233)
x0, y0, x1, y1 = 250, 190, 1130, 590
d.rounded_rectangle((x0, y0, x1, y1), radius=26, fill=paper, outline=ink, width=10)
sx = x1 - 230
for yy in range(y0 + 24, y1 - 20, 34):
    d.ellipse((sx - 7, yy - 7, sx + 7, yy + 7), fill=(243, 233, 210), outline=ink, width=3)
d.rectangle((x0 + 40, y0 + 40, sx - 40, y0 + 150), fill=red)
f = fnt("Oswald-Bold.ttf", 86)
while f.getlength("ВХОДНОЙ БИЛЕТ") > (sx - x0 - 110):
    f = fnt("Oswald-Bold.ttf", f.size - 2)
d.text(((x0 + sx) / 2, y0 + 95), "ВХОДНОЙ БИЛЕТ", font=f, fill=paper, anchor="mm")
d.text(((x0 + sx) / 2, y0 + 215), "РЯД G · МЕСТО 12", font=fnt("Montserrat-Black.ttf", 38), fill=ink, anchor="mm")
d.rectangle((x0 + 160, y0 + 270, sx - 160, y1 - 40), outline=ink, width=6)
d.text((x1 - 115, (y0 + y1) / 2), "№ 004", font=fnt("Montserrat-Black.ttf", 40), fill=ink, anchor="mm")
im.save(OUT / "next_ticket.png")

# ---- m2: the countdown on the grey booking wall, Russian label
bg = np.full((768, 1376, 3), (200, 200, 196), np.uint8)
bg = np.clip(bg.astype(np.int16) + np.random.default_rng(3).normal(0, 3, bg.shape[:2])[..., None], 0, 255).astype(np.uint8)
pan = led_panel("02:59:59", "До конца распродажи", height=240)
k = 560 / pan.shape[1]
pan = cv2.resize(pan, (560, int(pan.shape[0] * k)), interpolation=cv2.INTER_AREA)
pil = Image.fromarray(bg).convert("RGBA")
sh = Image.new("RGBA", (pan.shape[1] + 40, pan.shape[0] + 40), (0, 0, 0, 0))
ImageDraw.Draw(sh).rounded_rectangle((20, 26, pan.shape[1] + 20, pan.shape[0] + 26), radius=24, fill=(0, 0, 0, 90))
sh = sh.filter(ImageFilter.GaussianBlur(10))
px, py = (1376 - pan.shape[1]) // 2, (768 - pan.shape[0]) // 2
pil.alpha_composite(sh, (px - 20, py - 20))
pil.alpha_composite(Image.fromarray(pan), (px, py))
pil.convert("RGB").save(OUT / "images" / "m2.png")
print("written: lang/ru/next_ticket.png, lang/ru/images/m2.png")
