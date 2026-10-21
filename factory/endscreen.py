"""20-second end sequence (long videos): CASE CLOSED stamp + the verdict handwritten on the folder, then the
next case is sketched by the drawing hands (two identical baskets, two different price tags), while the
YouTube end-screen zones stay clear: right = next-video element, bottom-left = subscribe element. Our own
retro SUBSCRIBE button + bell sits beside the subscribe zone and gets clicked by the hand.

visual: {"type": "endscreen", "endscreen": {
   "number": "001", "title": "The casino", "stamp": "Case closed",
   "verdict": ["Guilty: your brain.", "Accomplice: plastic."],
   "next": {"number": "002", "title": "Same basket", "tagline": "Same basket. Different price.",
            "image": "<frame key of the subject to sketch>", "copies": 2, "prices": ["$114.34", "$123.93"]},
   "times": {...optional overrides, seconds from the shot start...}}}
"""
from __future__ import annotations

import math

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .config import hex_to_rgb, resolve_font
from .draw import COLOR_START, LINES_END, LineDrawing, hand_path, paste_hand, subject_mask
from .evidence import _aged_paper, desk
from .shots import Shot, add_grain, ease
from .text import blend, fit_font, font

# YouTube end-screen element zones (fractions of the frame) — kept free of anything important
VIDEO_ZONE = (0.605, 0.205, 0.955, 0.555)   # x0, y0, x1, y1 (16:9 element on the right)
SUB_ZONE = (0.045, 0.695, 0.145, 0.875)     # round subscribe element, bottom-left
SHEET = (0.035, 0.055, 0.565, 0.665)        # next-case sheet (left), above the subscribe zone

T = {"stamp": 0.15, "v1": 0.9, "v2": 2.6, "vdur": 1.45, "swap": 5.0, "draw": 5.75, "ddur": 3.6,
     "tags": 9.45, "p1": 9.85, "p2": 10.75, "pdur": 0.8, "tagline": 12.0, "zone": 12.35, "zdur": 0.8,
     "sketch": 13.0, "skdur": 1.1, "sub": 14.1, "click": 15.15, "push": 15.9,
     "fees": 9.6, "fgap": 0.75, "fdur": 0.55}
# "next": {"fees": ["$30", "+ $8 fee", ...]} — a price that grows: lines handwritten one under another beside the
# sketched subject (last line red, ringed); "label": a small typed plate on the sheet (e.g. "Illustration").


def _pal(cfg):
    return {k: hex_to_rgb(v) for k, v in cfg["style"]["palette"].items()}


class Writing:
    """Text that gets handwritten: revealed left to right with the pen tip on the ink."""

    def __init__(self, text: str, fnt, color, stroke_fill=None, stroke_w=None):
        w = int(fnt.getlength(text) + fnt.size * 0.6)
        h = int(fnt.size * 1.5)
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        if stroke_fill:
            d.text((fnt.size * 0.2, fnt.size * 0.1), text, font=fnt, fill=stroke_fill + (255,), stroke_width=stroke_w or max(2, fnt.size // 16),
                   stroke_fill=stroke_fill + (255,))
        d.text((fnt.size * 0.2, fnt.size * 0.1), text, font=fnt, fill=tuple(color) + (255,))
        self.img = np.array(img)
        a = self.img[..., 3]
        cols = np.where(a.max(0) > 40)[0]
        self.x0, self.x1 = (int(cols.min()), int(cols.max())) if len(cols) else (0, w)
        # pen height per column: centre of the ink in that column (smoothed), mid-line where there is none
        ys = np.arange(h, dtype=np.float32)[:, None]
        wsum = a.astype(np.float32).sum(0)
        cy = np.where(wsum > 0, (a * ys).sum(0) / np.maximum(wsum, 1), h * 0.55)
        self.pen_y = np.convolve(cy, np.ones(9) / 9, mode="same")
        self.w, self.h = w, h

    def at(self, p: float) -> np.ndarray:
        if p >= 1:
            return self.img
        out = self.img.copy()
        xr = self.x0 + (self.x1 - self.x0) * max(0.0, p)
        xs = np.arange(self.w, dtype=np.float32)
        a = np.clip((xr - xs) / 6.0, 0, 1)
        out[..., 3] = (out[..., 3] * a[None, :]).astype(np.uint8)
        return out

    def tip(self, p: float) -> tuple[float, float]:
        xr = self.x0 + (self.x1 - self.x0) * min(1.0, max(0.0, p))
        y = float(self.pen_y[min(self.w - 1, int(xr))])
        return xr, y + math.sin(p * 90) * self.h * 0.10  # the pen bobs up and down through the letters


def _stamp(text: str, cfg, width: int, color, angle: float, seed: int, max_h: int | None = None) -> np.ndarray:
    head = resolve_font(cfg["fonts"]["headline"])
    sf, sl = fit_font(text.upper(), head, int(width * 0.9), int(max_h or width * 0.4), start=int(width * 0.22))
    pad = int(sf.size * 0.28)
    padx = int(sf.size * 0.42)  # the glyphs' ink (not the advance width) keeps clear of the border
    ink = [sf.getbbox(l) for l in sl]
    tw = int(max(b[2] - b[0] for b in ink)) + 2 * padx
    th = int(len(sl) * sf.size * 1.12) + 2 * pad
    img = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    bw = max(5, sf.size // 10)
    d.rectangle((bw // 2, bw // 2, tw - bw // 2, th - bw // 2), outline=tuple(color) + (255,), width=bw)
    y = pad
    for l, b in zip(sl, ink):
        d.text(((tw - (b[2] - b[0])) / 2 - b[0], y), l, font=sf, fill=tuple(color) + (255,))
        y += int(sf.size * 1.12)
    arr = np.array(img)
    holes = cv2.GaussianBlur(np.random.default_rng(seed).random(arr.shape[:2]).astype(np.float32), (0, 0), 1.2) > 0.58
    arr[..., 3] = np.where(holes, (arr[..., 3] * 0.35).astype(np.uint8), arr[..., 3])
    return np.array(Image.fromarray(arr).rotate(angle, resample=Image.BICUBIC, expand=True))


def _price_tag(text: str, cfg, width: int, seed: int) -> tuple[np.ndarray, "Writing", tuple[int, int]]:
    """Blank shop tag (paper, red border, hole + string); the price is handwritten onto it later."""
    pal = _pal(cfg)
    h = int(width * 0.62)
    tag = Image.new("RGBA", (width, h + int(width * 0.5)), (0, 0, 0, 0))
    d = ImageDraw.Draw(tag)
    top = int(width * 0.5)
    c = int(h * 0.22)
    poly = [(c, top), (width - c, top), (width, top + c), (width, top + h), (0, top + h), (0, top + c)]
    d.polygon(poly, fill=(250, 244, 228, 255), outline=pal["red"] + (255,))
    d.line(poly + [poly[0]], fill=pal["red"] + (255,), width=max(4, width // 40))
    hx, hy, r = width // 2, top + int(h * 0.16), max(5, width // 22)
    d.ellipse((hx - r, hy - r, hx + r, hy + r), fill=(0, 0, 0, 0), outline=pal["ink"] + (255,), width=2)
    d.line((hx, hy - r, hx - width * 0.08, 0), fill=pal["ink"] + (255,), width=max(2, width // 70))  # string
    size = int(h * 0.42)
    fpath = resolve_font(cfg["fonts"]["marker"])
    while size > 10 and font(fpath, size).getlength(text) > width * 0.82:
        size -= 2
    wr = Writing(text, font(fpath, size), pal["ink"])
    return np.array(tag), wr, (int((width - wr.w) / 2), top + int(h * 0.30))


class EndScreenShot(Shot):
    def __init__(self, start, duration, spec: dict, cfg: dict, size, subject: Image.Image | None = None,
                 lead_in: float = 0.0, seed: int = 0):
        super().__init__(start, duration)
        self.W, self.H = W, H = size
        self.cfg, self.spec = cfg, spec
        self.pal = pal = _pal(cfg)
        self.t = {k: v + lead_in for k, v in {**T, **(spec.get("times") or {})}.items()}
        self.desk = desk(W, H, pal, 3)
        marker = resolve_font(cfg["fonts"]["marker"])
        head = resolve_font(cfg["fonts"]["headline"])
        typew = resolve_font(cfg["fonts"].get("typewriter") or cfg["fonts"]["serif"])
        # ---- phase 1: the closed folder, lying landscape on the desk
        fw, fh = int(W * 0.66), int(H * 0.70)
        self.fx, self.fy = (W - fw) // 2, int(H * 0.06)
        manila = (222, 186, 120)
        folder = Image.new("RGBA", (fw, fh + int(fh * 0.06)), (0, 0, 0, 0))
        d = ImageDraw.Draw(folder)
        tab = int(fh * 0.06)
        d.rectangle((int(fw * 0.06), 0, int(fw * 0.32), tab + 4), fill=tuple(int(c * 0.93) for c in manila) + (255,))
        d.rectangle((0, tab, fw - 1, tab + fh - 1), fill=manila + (255,), outline=tuple(int(c * 0.7) for c in manila) + (255,), width=4)
        lab = (int(fw * 0.05), tab + int(fh * 0.07), int(fw * 0.47), tab + int(fh * 0.30))
        d.rectangle(lab, fill=(250, 246, 236, 255), outline=pal["ink"] + (255,), width=3)
        f1 = font(typew, int(fh * 0.050))
        d.text((lab[0] + int(fw * 0.02), lab[1] + int(fh * 0.03)), f"CASE FILE #{spec.get('number', '001')}", font=f1, fill=pal["ink"])
        f2, l2 = fit_font(str(spec.get("title", "")).upper(), head, int((lab[2] - lab[0]) * 0.9), int(fh * 0.12), start=int(fh * 0.10))
        d.text((lab[0] + int(fw * 0.02), lab[1] + int(fh * 0.10)), " ".join(l2), font=f2, fill=pal["ink"])
        d.text((int(fw * 0.05), tab + int(fh * 0.92)), "CONFIDENTIAL", font=font(typew, int(fh * 0.035)), fill=tuple(int(c * 0.55) for c in manila))
        self.folder = add_grain(np.array(folder), 0.0)
        self.stamp = _stamp(spec.get("stamp", "Case closed"), cfg, int(fw * 0.50), pal["red"], 8, seed + 3)
        self.stamp_pos = (self.fx + int(fw * 0.72), self.fy + int(fh * 0.25))
        vsz = int(H * 0.10)
        while vsz > 20 and max((font(marker, vsz).getlength(v) for v in (spec.get("verdict") or [""])), default=0) > fw * 0.86:
            vsz -= 2  # long verdict lines shrink to stay on the folder
        vf = font(marker, vsz)
        self.verdict = [Writing(v, vf, pal["ink"]) for v in (spec.get("verdict") or [])][:2]
        self.v_pos = [(self.fx + int(fw * 0.06), self.fy + int(fh * 0.47) + i * int(H * 0.15)) for i in range(len(self.verdict))]
        # ---- phase 2: next-case sheet with the subject drawn twice
        nx = spec.get("next") or {}
        sx0, sy0, sx1, sy1 = (int(SHEET[0] * W), int(SHEET[1] * H), int(SHEET[2] * W), int(SHEET[3] * H))
        self.sheet_box = (sx0, sy0)
        sw, sh = sx1 - sx0, sy1 - sy0
        paper = _aged_paper(sw, sh, seed + 11)
        paper_rgb = tuple(int(c) for c in np.median(paper.reshape(-1, 3), axis=0))
        sheet = Image.fromarray(paper).convert("RGBA")
        d = ImageDraw.Draw(sheet)
        f3 = font(typew, int(sh * 0.055))
        d.text((int(sw * 0.05), int(sh * 0.05)), f"NEXT: CASE FILE #{nx.get('number', '002')}", font=f3, fill=pal["ink"])
        d.line((int(sw * 0.05), int(sh * 0.14), int(sw * 0.95), int(sh * 0.14)), fill=pal["ink"], width=2)
        self.sheet = np.array(sheet)
        self.sheet_paper = paper
        # the subject: cut out of its own backdrop, pasted `copies` times side by side
        self.draw = None
        self.tags = []
        if subject is not None:
            src = np.array(subject.convert("RGB"))
            hh, ww = src.shape[:2]
            src = src[int(hh * 0.07): int(hh * 0.93), int(ww * 0.05): int(ww * 0.95)]  # drop any printed border
            back = np.median(np.concatenate([src[:8].reshape(-1, 3), src[-8:].reshape(-1, 3),
                                             src[:, :8].reshape(-1, 3), src[:, -8:].reshape(-1, 3)]), axis=0)
            diff = np.abs(src.astype(np.float32) - back).max(2)
            m8 = (diff > 26).astype(np.uint8)
            m8 = cv2.morphologyEx(m8, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
            cnts, _ = cv2.findContours(m8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            m8 = np.zeros_like(m8)
            for c in cnts:
                if cv2.contourArea(c) > 0.002 * m8.size:
                    cv2.drawContours(m8, [c], -1, 1, -1)
            m8[diff < 14] = 0  # holes that show the backdrop (inside the handles) stay empty
            m8 = cv2.morphologyEx(m8, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
            m = cv2.GaussianBlur(m8.astype(np.float32), (0, 0), 1.0)
            ys, xs = np.where(m > 0.5)
            if len(xs) > 100:
                x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
                crop, mcrop = src[y0:y1 + 1, x0:x1 + 1], m[y0:y1 + 1, x0:x1 + 1]
                copies = int(nx.get("copies", 2))
                area_w, area_h = sw * 0.94 / copies, sh * (0.36 if nx.get("label_under") else 0.50)
                k = min(area_w * (0.52 if nx.get("fees") else 0.62) / crop.shape[1], area_h / crop.shape[0])
                cw, ch = int(crop.shape[1] * k), int(crop.shape[0] * k)
                crop = cv2.resize(crop, (cw, ch), interpolation=cv2.INTER_AREA)
                mcrop = cv2.resize(mcrop.astype(np.float32), (cw, ch))
                base = paper.copy()
                mask = np.zeros(paper.shape[:2], np.float32)
                self.slots = []
                for i in range(copies):
                    px, py = int(sw * 0.03 + area_w * i), int(sh * 0.43)
                    if copies == 1 and not nx.get("fees"):  # a single subject sits in the middle of the sheet
                        px = int((sw - cw) / 2)
                    a = mcrop[..., None]
                    reg = base[py:py + ch, px:px + cw].astype(np.float32)
                    base[py:py + ch, px:px + cw] = (reg * (1 - a) + crop * a).astype(np.uint8)
                    mask[py:py + ch, px:px + cw] = np.maximum(mask[py:py + ch, px:px + cw], mcrop)
                    self.slots.append((px, py, cw, ch))
                self.draw = LineDrawing(base, paper_rgb, mask)
                self.strike = None
                if nx.get("strike"):  # a red marker line through a printed price on the subject (fractions of it)
                    a0, b0, a1, b1 = nx["strike"]
                    px, py, cw0, ch0 = self.slots[0]
                    self.strike = (sx0 + px + a0 * cw0, sy0 + py + b0 * ch0, sx0 + px + a1 * cw0, sy0 + py + b1 * ch0)
                prices = nx.get("prices") or []
                for i, p in enumerate(prices[: len(self.slots)]):
                    px, py, cw, ch = self.slots[i]
                    tag, wr, off = _price_tag(p, cfg, int(area_w * 0.36), seed + i)
                    self.tags.append((tag, wr, off, (sx0 + px + cw + int(area_w * 0.17), sy0 + py + int(ch * 0.30))))
        self.sketch = None
        if self.draw is not None:
            zx0, zy0, zx1, zy1 = (int(VIDEO_ZONE[0] * W), int(VIDEO_ZONE[1] * H), int(VIDEO_ZONE[2] * W), int(VIDEO_ZONE[3] * H))
            zw, zh = zx1 - zx0, zy1 - zy0
            news_c = np.array((208, 205, 196), np.float32)
            news = np.clip(np.full((zh, zw, 3), news_c) + np.random.default_rng(seed + 21).standard_normal((zh, zw, 1)) * 4, 0, 255).astype(np.uint8)
            xa = min(sl[0] for sl in self.slots)
            xb = max(sl[0] + sl[2] for sl in self.slots) + int(self.tags[0][0].shape[1] * 1.1 if self.tags else 0)
            ya = min(sl[1] for sl in self.slots)
            yb = max(sl[1] + sl[3] for sl in self.slots)
            g = cv2.cvtColor(self.draw.base[ya:yb, xa:xb], cv2.COLOR_RGB2GRAY).astype(np.float32)
            g = 255 - (255 - g) * 0.85  # grey newsprint pencil
            k = min(zw * 0.86 / g.shape[1], zh * 0.66 / g.shape[0])
            g = cv2.resize(g, (int(g.shape[1] * k), int(g.shape[0] * k)), interpolation=cv2.INTER_AREA)
            gx, gy = (zw - g.shape[1]) // 2, int(zh * 0.12)
            reg = news[gy:gy + g.shape[0], gx:gx + g.shape[1]].astype(np.float32)
            news[gy:gy + g.shape[0], gx:gx + g.shape[1]] = np.minimum(reg, g[..., None]).astype(np.uint8)
            mk = np.zeros((zh, zw), np.float32)
            mk[gy:gy + g.shape[0], gx:gx + g.shape[1]] = (g < 200).astype(np.float32)
            mk = cv2.dilate(mk, np.ones((5, 5), np.uint8))
            lab = Writing(f"CASE FILE #{nx.get('number', '002')}", font(marker, int(zh * 0.10)), (60, 58, 54))
            la = lab.img[..., 3:4].astype(np.float32) / 255
            ly, lx = zh - lab.h - int(zh * 0.04), int(zw * 0.04)
            reg = news[ly:ly + lab.h, lx:lx + lab.w].astype(np.float32)
            news[ly:ly + lab.h, lx:lx + lab.w] = (reg * (1 - la) + lab.img[..., :3] * la).astype(np.uint8)
            mk[ly:ly + lab.h, lx:lx + lab.w] = np.maximum(mk[ly:ly + lab.h, lx:lx + lab.w], la[..., 0])
            self.sketch = LineDrawing(news, tuple(int(c) for c in news_c), mk)
            self.sketch_pos = (zx0, zy0)
        self.fees = []
        if nx.get("fees") and getattr(self, "slots", None):
            px, py, cw, ch = self.slots[0]
            fx = sx0 + px + cw + int(sw * 0.05)
            room = sx0 + sw - int(sw * 0.04) - fx
            n = len(nx["fees"])
            top, bot = int(sh * 0.36), int(sh * 0.95)  # under the tagline stamp
            lh = min(int(sh * 0.12), int((bot - top) / max(1, n + 0.25)))
            fy0 = sy0 + top
            fpath = resolve_font(cfg["fonts"]["marker"])
            size = int(lh * 0.78)
            while size > 12 and max(font(fpath, size).getlength(f) for f in nx["fees"]) > room:
                size -= 2
            for k, f in enumerate(nx["fees"]):
                col = pal["red"] if k == n - 1 else pal["ink"]
                extra = int(lh * 0.22) if k == n - 1 else 0  # the total sits a little apart (room for its ring)
                self.fees.append((Writing(f, font(fpath, size), col), (fx, fy0 + k * lh + extra)))
        self.nwrites = []  # "writes": short handwritten notes on the sketched subject (fractions of it), e.g. "No tip"
        if nx.get("writes") and getattr(self, "slots", None):
            px, py, cw, ch = self.slots[0]
            fpath = resolve_font(cfg["fonts"]["marker"])
            for wdef in nx["writes"]:
                wr = Writing(str(wdef["text"]), font(fpath, max(12, int(ch * float(wdef.get("h", 0.06))))), pal["red"])
                self.nwrites.append((wr, (int(sx0 + px + float(wdef["x"]) * cw - wr.w / 2), int(sy0 + py + float(wdef["y"]) * ch - wr.h / 2))))
        self.plate = None
        if nx.get("label"):  # small typed plate on the sheet (drawn over the sketch); a list = one line per item
            lines = [str(x).upper() for x in (nx["label"] if isinstance(nx["label"], list) else [nx["label"]])]
            size = int(sh * 0.045)
            while size > 10 and max(font(typew, size).getlength(l) for l in lines) > sw * 0.90:
                size -= 1
            lf = font(typew, size)
            tw = int(max(lf.getlength(l) for l in lines))
            lh = int(lf.size * 1.25)
            pl = Image.new("RGBA", (tw + 20, lh * len(lines) + 12), pal["ink"] + (230,))
            for k, l in enumerate(lines):
                ImageDraw.Draw(pl).text((10, 6 + k * lh), l, font=lf, fill=(250, 246, 236, 255))
            if nx.get("label_under") and getattr(self, "slots", None):  # centred under the sketched subject
                px, py, cw, ch = self.slots[0]
                self.plate = (np.array(pl), int(max(sw * 0.02, min(sw * 0.98 - pl.width, px + cw / 2 - pl.width / 2))), int(py + ch + sh * 0.025))
            else:
                px_ = int(sw * 0.04) if nx.get("fees") or int(nx.get("copies", 2)) > 1 else sw - pl.width - int(sw * 0.04)
                self.plate = (np.array(pl), px_, sh - int(sh * 0.06) - pl.height)  # bottom-left (bottom-right beside a single subject)
        self.tagline = _stamp(nx.get("tagline", ""), cfg, int(sw * 0.90), pal["red"], -2, seed + 5, max_h=int(sh * 0.11)) if nx.get("tagline") else None
        self.tagline_pos = (sx0 + sw // 2, sy0 + int(sh * 0.27))
        # ---- end-screen furniture
        self.label = Writing("NEXT CASE  >", font(marker, int(H * 0.055)), pal["paper"])
        bf = font(resolve_font(cfg["fonts"]["headline"]), int(H * 0.062))
        self.btn = {False: self._button("SUBSCRIBE", bf, pal["red"]), True: self._button("SUBSCRIBED", bf, (90, 90, 90))}
        self.bell = self._bell(int(H * 0.075))

    # ------------------------------------------------------------------ pieces
    def _button(self, text, fnt, fill) -> np.ndarray:
        pal = self.pal
        pad = int(fnt.size * 0.45)
        w, h = int(fnt.getlength(text) + pad * 2.4), int(fnt.size * 1.55)
        img = Image.new("RGBA", (w + 10, h + 12), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle((6, 9, w + 6, h + 9), radius=h // 4, fill=(0, 0, 0, 110))
        d.rounded_rectangle((0, 0, w, h), radius=h // 4, fill=tuple(fill) + (255,), outline=pal["ink"] + (255,), width=max(3, fnt.size // 12))
        d.rounded_rectangle((6, 5, w - 6, h * 0.42), radius=h // 6, fill=(255, 255, 255, 40))  # 50s enamel shine
        d.text((w / 2, h / 2 + 2), text, font=fnt, fill=(250, 246, 236, 255), anchor="mm")
        return np.array(img)

    def _bell(self, s: int) -> np.ndarray:
        pal = self.pal
        img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        gold, ink = pal["red"] + (255,), (250, 246, 236, 255)  # channel bell: red, cream outline
        d.pieslice((s * 0.18, s * 0.12, s * 0.82, s * 0.95), 180, 360, fill=gold, outline=ink, width=3)
        d.polygon([(s * 0.18, s * 0.53), (s * 0.82, s * 0.53), (s * 0.90, s * 0.76), (s * 0.10, s * 0.76)], fill=gold, outline=ink)
        d.ellipse((s * 0.42, s * 0.74, s * 0.58, s * 0.90), fill=ink)
        d.ellipse((s * 0.45, s * 0.03, s * 0.55, s * 0.14), fill=gold, outline=ink, width=2)
        return np.array(img)

    def _drop(self, t, t0, dur=0.35):
        """0 -> 1 landing curve with a small settle."""
        p = (t - t0) / dur
        if p <= 0:
            return None
        if p >= 1:
            return 1.0
        return ease(p) + 0.06 * math.sin(p * math.pi)

    # ------------------------------------------------------------------ frame
    def frame(self, t: float) -> np.ndarray:
        W, H, tt = self.W, self.H, self.t
        out = self.desk.copy()
        hand = None  # (kind, x, y, mirrored)
        # phase 1: folder (slides out to the left at swap)
        sw_p = ease((t - tt["swap"]) / 0.55) if t > tt["swap"] else 0.0
        if sw_p < 1:
            dx = -int(W * 0.9 * sw_p)
            blend(out, self.folder, self.fx + dx, self.fy)
            if t >= tt["stamp"]:
                p = min(1.0, (t - tt["stamp"]) / 0.14)
                sc = 2.4 - 1.4 * p
                st = cv2.resize(self.stamp, (max(1, int(self.stamp.shape[1] * sc)), max(1, int(self.stamp.shape[0] * sc))))
                blend(out, st, self.stamp_pos[0] + dx - st.shape[1] // 2, self.stamp_pos[1] - st.shape[0] // 2, opacity=min(1.0, 0.3 + p))
            for i, wr in enumerate(self.verdict):
                t0 = tt["v1"] if i == 0 else tt["v2"]
                p = (t - t0) / tt["vdur"]
                if p <= 0:
                    continue
                vx, vy = self.v_pos[i]
                blend(out, wr.at(p), vx + dx, vy)
                if p < 1.25 and dx == 0:
                    tip = hand_path(lambda q, wr=wr, vx=vx, vy=vy, t0=t0: (vx + wr.tip((q - t0) / tt["vdur"])[0], vy + wr.tip((q - t0) / tt["vdur"])[1]),
                                    t0, t0 + tt["vdur"], t, W, H, False, from_below=True)
                    if tip:
                        hand = ("ink_under", tip[0], tip[1], False)
        # phase 2: the next-case sheet slides in from the right
        if t > tt["swap"] + 0.1:
            p = ease((t - tt["swap"] - 0.1) / 0.6)
            sx, sy = self.sheet_box
            dx = int(W * (1 - p))
            if self.draw is not None:
                q = (t - tt["draw"]) / tt["ddur"]
                pic = self.draw.blank if q <= 0 else self.draw.state(min(1.0, q))
                sheet = self.sheet.copy()
                sheet[..., :3] = pic
                hdr = int(self.sheet.shape[0] * 0.16)
                sheet[:hdr] = self.sheet[:hdr]
            else:
                sheet = self.sheet
            shadow = np.zeros_like(sheet)
            shadow[..., 3] = 120
            blend(out, cv2.GaussianBlur(shadow, (0, 0), 12), sx + dx + 10, sy + 14)
            blend(out, sheet, sx + dx, sy)
            if self.plate is not None and t >= tt.get("label", 0.0):  # "label" time: the plate appears then (fade)
                blend(out, self.plate[0], sx + dx + self.plate[1], sy + self.plate[2],
                      opacity=min(1.0, (t - tt.get("label", 0.0)) / 0.25) if tt.get("label") else 1.0)
            if self.draw is not None and 0 < (t - tt["draw"]) / tt["ddur"] < 1.08:
                q = (t - tt["draw"]) / tt["ddur"]
                kind = "pencil" if q < (LINES_END + COLOR_START) / 2 else "colour"
                t0, t1 = (tt["draw"], tt["draw"] + tt["ddur"] * LINES_END) if kind == "pencil" else \
                         (tt["draw"] + tt["ddur"] * COLOR_START, tt["draw"] + tt["ddur"])
                tip = hand_path(lambda qq: (sx + self.draw.tip((qq - tt["draw"]) / tt["ddur"])[0],
                                            sy + self.draw.tip((qq - tt["draw"]) / tt["ddur"])[1]), t0, t1, t, W, H, False)
                if tip:
                    hand = (kind, tip[0], tip[1], False)
            for i, (tag, wr, off, (tx, ty)) in enumerate(self.tags):
                d = self._drop(t, tt["tags"] + i * 0.15)
                if d is None:
                    continue
                y = int(ty - tag.shape[0] * 0.3 - (1 - d) * H * 0.25)
                blend(out, tag, tx - tag.shape[1] // 2, y)
                t0 = tt["p1"] if i == 0 else tt["p2"]
                pp = (t - t0) / tt["pdur"]
                if pp > 0:
                    blend(out, wr.at(pp), tx - tag.shape[1] // 2 + off[0], y + off[1])
                    if pp < 1.2:
                        bx, by = tx - tag.shape[1] // 2 + off[0], y + off[1]
                        tip = hand_path(lambda q, wr=wr, bx=bx, by=by, t0=t0: (bx + wr.tip((q - t0) / tt["pdur"])[0], by + wr.tip((q - t0) / tt["pdur"])[1]),
                                        t0, t0 + tt["pdur"], t, W, H, False, from_below=True)
                        if tip:
                            hand = ("ink_under", tip[0], tip[1], False)
            if len(self.tags) >= 2 and t >= tt["p2"] + tt["pdur"] + 0.1:  # red marker rings the odd price out
                tag, wr, off, (tx, ty) = self.tags[-1]
                c0 = tt["p2"] + tt["pdur"] + 0.1
                q = min(1.0, (t - c0) / 0.55)
                cxr, cyr = tx, int(ty - tag.shape[0] * 0.3 + off[1] + wr.h * 0.5)
                rx, ry = int(tag.shape[1] * 0.62), int(wr.h * 0.95)
                a0 = -150
                cv2.ellipse(out, (cxr, cyr), (rx, ry), -6, a0, a0 + 380 * q, tuple(int(c) for c in self.pal["red"]), max(5, H // 160), cv2.LINE_AA)
                if q < 1:
                    ang = math.radians(a0 + 380 * q)
                    hx, hy = cxr + rx * math.cos(ang), cyr + ry * math.sin(ang)
                    tip = hand_path(lambda _q: (hx, hy), c0, c0 + 0.55, t, W, H, False, from_below=True)
                    if tip:
                        hand = ("marker_under", tip[0], tip[1], False)
            if getattr(self, "strike", None) and t >= tt["p2"]:  # the "WAS" price gets struck out
                q = min(1.0, (t - tt["p2"]) / 0.5)
                x0s, y0s, x1s, y1s = self.strike
                xe, ye = x0s + (x1s - x0s) * q, y0s + (y1s - y0s) * q
                cv2.line(out, (int(x0s), int(y0s)), (int(xe), int(ye)), tuple(int(c) for c in self.pal["red"]), max(6, H // 110), cv2.LINE_AA)
                cv2.line(out, (int(x0s), int(y0s + H * 0.012)), (int(xe), int(ye + H * 0.012)), tuple(int(c) for c in self.pal["red"]), max(4, H // 160), cv2.LINE_AA)
                if q < 1:
                    tip = hand_path(lambda _q: (xe, ye), tt["p2"], tt["p2"] + 0.5, t, W, H, False, from_below=True)
                    if tip:
                        hand = ("marker_under", tip[0], tip[1], False)
            for k, (wr, (fx, fy)) in enumerate(self.fees):  # the price grows, fee by fee
                t0 = tt["fees"] + k * tt["fgap"]
                pp = (t - t0) / tt["fdur"]
                if pp > 0:
                    blend(out, wr.at(pp), fx, fy)
                    if pp < 1.2:
                        tip = hand_path(lambda q, wr=wr, fx=fx, fy=fy, t0=t0: (fx + wr.tip((q - t0) / tt["fdur"])[0], fy + wr.tip((q - t0) / tt["fdur"])[1]),
                                        t0, t0 + tt["fdur"], t, W, H, False, from_below=True)
                        if tip:
                            hand = ("marker_under" if k == len(self.fees) - 1 else "ink_under", tip[0], tip[1], False)
            for k, (wr, (wx, wy)) in enumerate(self.nwrites):  # small notes written by the red marker hand
                t0 = tt.get("writes", tt["tagline"] - 1.4) + k * 0.9
                pp = (t - t0) / 0.6
                if pp > 0:
                    blend(out, wr.at(pp), wx, wy)
                    if pp < 1.2:
                        tip = hand_path(lambda q, wr=wr, wx=wx, wy=wy, t0=t0: (wx + wr.tip((q - t0) / 0.6)[0], wy + wr.tip((q - t0) / 0.6)[1]),
                                        t0, t0 + 0.6, t, W, H, False, from_below=True)
                        if tip:
                            hand = ("marker_under", tip[0], tip[1], False)
            if self.fees:  # ring the final price
                wr, (fx, fy) = self.fees[-1]
                c0 = tt["fees"] + (len(self.fees) - 1) * tt["fgap"] + tt["fdur"] + 0.15
                if t >= c0:
                    q = min(1.0, (t - c0) / 0.55)
                    cxr, cyr = fx + wr.w // 2, fy + wr.h // 2
                    rx, ry = int(wr.w * 0.62), int(wr.h * 0.62)
                    cv2.ellipse(out, (cxr, cyr), (rx, ry), -5, -150, -150 + 380 * q, tuple(int(c) for c in self.pal["red"]), max(5, H // 160), cv2.LINE_AA)
                    if q < 1:
                        ang = math.radians(-150 + 380 * q)
                        tip = hand_path(lambda _q: (cxr + rx * math.cos(ang), cyr + ry * math.sin(ang)), c0, c0 + 0.55, t, W, H, False, from_below=True)
                        if tip:
                            hand = ("marker_under", tip[0], tip[1], False)
            if self.tagline is not None and t >= tt["tagline"]:
                p = min(1.0, (t - tt["tagline"]) / 0.14)
                sc = 2.0 - 1.0 * p
                st = cv2.resize(self.tagline, (max(1, int(self.tagline.shape[1] * sc)), max(1, int(self.tagline.shape[0] * sc))))
                blend(out, st, self.tagline_pos[0] - st.shape[1] // 2, self.tagline_pos[1] - st.shape[0] // 2, opacity=min(1.0, 0.3 + p))
        # the next-video zone: a hand-drawn dashed frame + label (YouTube puts the video element inside it)
        if t >= tt["zone"]:
            p = min(1.0, (t - tt["zone"]) / tt["zdur"])
            x0, y0, x1, y1 = (int(VIDEO_ZONE[0] * W) - 14, int(VIDEO_ZONE[1] * H) - 14, int(VIDEO_ZONE[2] * W) + 14, int(VIDEO_ZONE[3] * H) + 14)
            per = 2 * ((x1 - x0) + (y1 - y0))
            pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
            budget, dash = per * p, 26
            col = tuple(int(c) for c in self.pal["paper"])
            for (ax, ay), (bx, by) in zip(pts, pts[1:]):
                L = math.hypot(bx - ax, by - ay)
                s = 0.0
                while s < L and budget > 0:
                    e = min(L, s + dash, s + budget)
                    cv2.line(out, (int(ax + (bx - ax) * s / L), int(ay + (by - ay) * s / L)),
                             (int(ax + (bx - ax) * e / L), int(ay + (by - ay) * e / L)), col, 5, cv2.LINE_AA)
                    budget -= dash * 2
                    s += dash * 2
            lp = (t - tt["zone"] - 0.3) / 0.8
            if lp > 0:  # printed label: fades in with the frame (no pen, so nothing is "written" by itself)
                blend(out, self.label.img, x0, y0 - self.label.h - 6, opacity=min(1.0, lp * 2))
            if self.sketch is not None and t >= tt["sketch"]:  # faded pencil preview inside the box (~40 %)
                q = (t - tt["sketch"]) / tt["skdur"]
                pic = self.sketch.state(q * LINES_END if q < 1 else 1.0)
                zx, zy = self.sketch_pos
                reg = out[zy:zy + pic.shape[0], zx:zx + pic.shape[1]].astype(np.float32)
                out[zy:zy + pic.shape[0], zx:zx + pic.shape[1]] = (reg * 0.6 + pic.astype(np.float32) * 0.4).astype(np.uint8)
                if q < 1.1:
                    tip = hand_path(lambda qq: (zx + self.sketch.tip((qq - tt["sketch"]) / tt["skdur"] * LINES_END)[0],
                                                zy + self.sketch.tip((qq - tt["sketch"]) / tt["skdur"] * LINES_END)[1]),
                                    tt["sketch"], tt["sketch"] + tt["skdur"], t, W, H, False)
                    if tip:
                        hand = ("pencil", tip[0], tip[1], False)
        # our subscribe button beside YouTube's subscribe zone, with a drawn arrow pointing at it
        if t >= tt["sub"]:
            pressed = t >= tt["click"]
            img = self.btn[pressed]
            pop = min(1.0, (t - tt["sub"]) / 0.22)
            sc = 0.6 + 0.4 * ease(pop) + (0.06 * math.sin(pop * math.pi))
            down = 4 if tt["click"] - 0.1 <= t <= tt["click"] + 0.45 else 0  # the button is pushed in under the finger
            im2 = cv2.resize(img, (max(1, int(img.shape[1] * sc)), max(1, int(img.shape[0] * sc))))
            bx, by = int(W * 0.17), int(H * 0.69)
            blend(out, im2, bx, by + down + (img.shape[0] - im2.shape[0]) // 2)
            # arrow from the button to the subscribe zone
            ax0, ay0 = bx - 8, by + img.shape[0] // 2
            ax1 = int(SUB_ZONE[2] * W) + 10
            ap = min(1.0, (t - tt["sub"] - 0.3) / 0.4)
            if ap > 0:
                xe = int(ax0 + (ax1 - ax0) * ap)
                cv2.line(out, (ax0, ay0), (xe, ay0 + int(4 * math.sin(ap * 3))), tuple(int(c) for c in self.pal["paper"]), 5, cv2.LINE_AA)
                if ap >= 1:
                    for s in (+1, -1):
                        cv2.line(out, (ax1, ay0), (ax1 + 22, ay0 + s * 16), tuple(int(c) for c in self.pal["paper"]), 5, cv2.LINE_AA)
            if True:
                age = t - tt["click"] if pressed else 9.0
                ang = 22 * math.sin(age * 22) * math.exp(-age * 2.2) if pressed else 6 * math.sin((t - tt["sub"]) * 5)
                bell = np.array(Image.fromarray(self.bell).rotate(ang, resample=Image.BICUBIC))
                blend(out, bell, bx + im2.shape[1] + 12, by + (img.shape[0] - bell.shape[0]) // 2)
                if pressed and age < 1.2:
                    cxb, cyb = bx + im2.shape[1] + 12 + bell.shape[1] // 2, by + img.shape[0] // 2
                    for k in (1, 2):
                        r = int(bell.shape[0] * (0.55 + 0.18 * k))
                        cv2.ellipse(out, (cxb, cyb), (r, r), 0, -50, -10, tuple(int(c) for c in self.pal["accent"]), 4, cv2.LINE_AA)
                        cv2.ellipse(out, (cxb, cyb), (r, r), 0, 190, 230, tuple(int(c) for c in self.pal["accent"]), 4, cv2.LINE_AA)
            # the hand comes in and presses it
            tc = tt["click"]
            if tc - 0.6 <= t <= tc + 1.0:  # enters, presses and holds ~0.6 s, then leaves
                target = (bx + img.shape[1] * 0.5, by + down + img.shape[0] * 0.5)
                tip = hand_path(lambda q: target, tc - 0.1, tc + 0.5, t, W, H, False, from_below=True)
                if tip:
                    hand = ("ink_under", tip[0], tip[1], False)
        if hand:
            paste_hand(out, hand[0], hand[1], hand[2], hand[3])
        if t > tt["push"]:  # the end frame keeps breathing: slow 2.5 % push-in until the cut
            z = 1 + 0.025 * ease((t - tt["push"]) / max(0.5, self.duration - tt["push"]))
            M = cv2.getRotationMatrix2D((W / 2, H / 2), 0, z)
            out = cv2.warpAffine(out, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        return out

    def sfx(self, start_abs: float) -> list[tuple[float, str]]:
        tt = self.t
        out = [(start_abs + tt["stamp"], "stamp")]
        for i in range(len(self.verdict)):
            t0 = tt["v1"] if i == 0 else tt["v2"]
            out += [(start_abs + t0 + k * 0.3, "marker") for k in range(int(tt["vdur"] / 0.3))]
        out += [(start_abs + tt["swap"], "whoosh"), (start_abs + tt["swap"] + 0.5, "paper")]
        if self.draw is not None:
            k = 0.0
            while k < tt["ddur"] * LINES_END:
                out.append((start_abs + tt["draw"] + k, "pencil"))
                k += 0.17
            k = tt["ddur"] * COLOR_START
            while k < tt["ddur"]:
                out.append((start_abs + tt["draw"] + k, "marker"))
                k += 0.24
        for i in range(len(self.tags)):
            out.append((start_abs + tt["tags"] + i * 0.15 + 0.3, "paper"))
            t0 = tt["p1"] if i == 0 else tt["p2"]
            out += [(start_abs + t0, "marker"), (start_abs + t0 + 0.4, "marker")]
        if len(self.tags) >= 2:
            out.append((start_abs + tt["p2"] + tt["pdur"] + 0.1, "scribble"))
        if getattr(self, "strike", None):
            out.append((start_abs + tt["p2"], "scribble"))
        for k in range(len(self.fees)):
            out.append((start_abs + tt["fees"] + k * tt["fgap"], "marker"))
        if self.fees:
            out.append((start_abs + tt["fees"] + (len(self.fees) - 1) * tt["fgap"] + tt["fdur"] + 0.15, "scribble"))
        for k in range(len(getattr(self, "nwrites", []))):
            out.append((start_abs + tt.get("writes", tt["tagline"] - 1.4) + k * 0.9, "marker"))
        if self.tagline is not None:
            out.append((start_abs + tt["tagline"], "stamp"))
        out += [(start_abs + tt["zone"], "marker")]
        if self.sketch is not None:
            k = 0.0
            while k < tt["skdur"]:
                out.append((start_abs + tt["sketch"] + k, "pencil"))
                k += 0.18
        out += [(start_abs + tt["sub"], "pop"), (start_abs + tt["click"] - 0.1, "tick"), (start_abs + tt["click"], "ding")]
        return out
