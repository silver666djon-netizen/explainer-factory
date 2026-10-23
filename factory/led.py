"""Code-drawn digital countdown timer: red seven-segment LED digits on a black bezel (1950s-meets-checkout).
Used as a picture (the Suspect No. 2 mugshot) and as a mark (type "led") on illustrations, so every timer
in an episode has the same digital style."""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SEGS = {"0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc", "5": "afgcd", "6": "afgedc",
        "7": "abc", "8": "abcdefg", "9": "abcfgd", "-": "g", " ": ""}


def _digit(d: ImageDraw.ImageDraw, x, y, w, h, ch, on, off):
    t = max(3, int(w * 0.18))  # segment thickness
    sk = w * 0.12  # italic skew
    def P(px, py):  # skew to the right going up
        return (x + px + sk * (1 - py / h), y + py)
    def hseg(py):
        return [P(t * 0.6, py), P(t, py - t / 2), P(w - t, py - t / 2), P(w - t * 0.6, py), P(w - t, py + t / 2), P(t, py + t / 2)]
    def vseg(px, y0, y1):
        return [P(px, y0 + t * 0.6), P(px + t / 2, y0 + t), P(px + t / 2, y1 - t), P(px, y1 - t * 0.6), P(px - t / 2, y1 - t), P(px - t / 2, y0 + t)]
    segs = {"a": hseg(t / 2), "g": hseg(h / 2), "d": hseg(h - t / 2),
            "f": vseg(t / 2, 0, h / 2), "b": vseg(w - t / 2, 0, h / 2),
            "e": vseg(t / 2, h / 2, h), "c": vseg(w - t / 2, h / 2, h)}
    lit = SEGS.get(ch, "")
    for k, poly in segs.items():
        d.polygon(poly, fill=on if k in lit else off)


def led_panel(text: str = "02:59:59", label: str | None = None, height: int = 220, red=(236, 60, 40)) -> np.ndarray:
    """RGBA panel. `text` digits/colons, optional small label above the digits (e.g. 'SALE ENDS IN')."""
    dh = int(height * (0.56 if label else 0.66))
    dw = int(dh * 0.55)
    gap = int(dw * 0.28)
    colw = int(dw * 0.35)
    n_d = sum(1 for c in text if c != ":")
    n_c = text.count(":")
    pad = int(height * 0.16)
    W = pad * 2 + n_d * dw + (n_d - 1) * gap + n_c * colw
    H = height
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = int(H * 0.12)
    d.rounded_rectangle((0, 0, W - 1, H - 1), radius=r, fill=(26, 24, 22, 255), outline=(150, 146, 136, 255), width=max(4, H // 30))
    d.rounded_rectangle((int(H * 0.06), int(H * 0.06), W - int(H * 0.06), H - int(H * 0.06)), radius=int(r * 0.7),
                        fill=(12, 10, 10, 255))
    on, off = red + (255,), (52, 22, 20, 255)
    y0 = H - pad - dh
    if label:
        from .config import resolve_font
        from PIL import ImageFont
        try:
            f = ImageFont.truetype(str(resolve_font([*__import__("factory.i18n", fromlist=["fonts"]).fonts().get("body", []), "assets/fonts/ArchivoBlack-Regular.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"])),
                                   int(H * 0.13))
        except Exception:  # noqa: BLE001
            f = ImageFont.load_default()
        while hasattr(f, "getlength") and f.getlength(label.upper()) > W * 0.88 and getattr(f, "size", 0) > 10:
            f = ImageFont.truetype(f.path, f.size - 1)  # a longer (translated) label shrinks to the panel
        d.text((W / 2, pad * 0.45 + H * 0.08), label.upper(), font=f, fill=(230, 222, 205, 255), anchor="mm")
    x = pad
    for ch in text:
        if ch == ":":
            cx = x + colw / 2
            rr = max(3, int(dw * 0.09))
            for fy in (0.32, 0.70):
                for dd in (d, gd):
                    dd.ellipse((cx - rr, y0 + dh * fy - rr, cx + rr, y0 + dh * fy + rr), fill=on)
            x += colw
            continue
        _digit(d, x, y0, dw, dh, ch, on, off)
        _digit(gd, x, y0, dw, dh, ch, on, (0, 0, 0, 0))
        x += dw + gap
    glow = glow.filter(ImageFilter.GaussianBlur(H * 0.035))
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    out.alpha_composite(img)
    ga = np.array(glow).astype(np.float32)
    ga[..., 3] *= 0.55
    out.alpha_composite(Image.fromarray(ga.astype(np.uint8)))
    return np.array(out)
