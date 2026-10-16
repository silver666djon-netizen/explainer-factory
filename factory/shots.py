"""Shots: a picture that moves for a stretch of time.

Kinds: illustration/photo with camera motion (+ optional red-marker marks drawn on the picture),
title cards, animated charts and big-number "stat" cards.
"""
from __future__ import annotations

import math

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

from .config import hex_to_rgb, resolve_font
from .text import blend, fit_font, font, text_block

MARGIN = 1.25  # source is prepared 25% larger than the frame so the camera can travel


def ease(p: float) -> float:
    p = min(1.0, max(0.0, p))
    return p * p * (3 - 2 * p)


def cover(img: Image.Image, w: int, h: int) -> np.ndarray:
    src_w, src_h = img.size
    scale = max(w / src_w, h / src_h)
    nw, nh = math.ceil(src_w * scale), math.ceil(src_h * scale)
    resized = img.resize((nw, nh), Image.LANCZOS)
    left, top = (nw - w) // 2, (nh - h) // 2
    return np.array(resized.crop((left, top, left + w, top + h)).convert("RGB"))


def paper_grain(h: int, w: int, strength: float, seed: int = 3) -> np.ndarray:
    """Static paper texture baked into pictures (moves with the image, compresses well)."""
    if strength <= 0:
        return np.zeros((h, w, 1), dtype=np.int16)
    rng = np.random.default_rng(seed)
    small = rng.standard_normal((h // 2 + 1, w // 2 + 1)).astype(np.float32)
    small = cv2.GaussianBlur(small, (0, 0), 0.6)
    grain = cv2.resize(small, (w, h), interpolation=cv2.INTER_LINEAR)
    return (grain * 255 * strength).astype(np.int16)[..., None]


def add_grain(arr: np.ndarray, strength: float, seed: int = 3) -> np.ndarray:
    if strength <= 0:
        return arr
    g = paper_grain(arr.shape[0], arr.shape[1], strength, seed)
    return np.clip(arr.astype(np.int16) + g, 0, 255).astype(np.uint8)


def archival_print(img: Image.Image, cfg: dict, w: int, h: int, seed: int = 0) -> Image.Image:
    """Real archive photo -> warm halftone print with a white border, laid on paper, slightly rotated."""
    pal = {k: hex_to_rgb(v) for k, v in cfg["style"]["palette"].items()}
    gray = ImageOps.autocontrast(img.convert("L"), cutoff=1)
    # coarse halftone feel: posterize lightly + soft blur, then tint ink/paper
    gray = gray.filter(ImageFilter.UnsharpMask(radius=2, percent=80))
    tinted = ImageOps.colorize(gray, black=pal["ink"], white=tuple(min(255, c + 8) for c in pal["paper"]))
    # fit inside the canvas with a border
    max_w, max_h = int(w * 0.78), int(h * 0.80)
    scale = min(max_w / tinted.width, max_h / tinted.height)
    tinted = tinted.resize((max(1, int(tinted.width * scale)), max(1, int(tinted.height * scale))), Image.LANCZOS)
    border = max(12, int(min(w, h) * 0.018))
    printed = ImageOps.expand(tinted, border=border, fill=(250, 246, 236))
    rnd = np.random.default_rng(seed)
    angle = float(rnd.uniform(-3.0, 3.0))
    printed = printed.convert("RGBA").rotate(angle, resample=Image.BICUBIC, expand=True)
    canvas = Image.new("RGB", (w, h), pal["paper"])
    shadow = Image.new("RGBA", printed.size, (0, 0, 0, 0))
    shadow.paste((0, 0, 0, 90), mask=printed.split()[3])
    shadow = shadow.filter(ImageFilter.GaussianBlur(border))
    x, y = (w - printed.width) // 2, (h - printed.height) // 2
    canvas.paste(shadow, (x + border // 2, y + border), shadow)
    canvas.paste(printed, (x, y), printed)
    # two strips of tape
    draw = ImageDraw.Draw(canvas, "RGBA")
    tw, th = int(w * 0.09), int(h * 0.035)
    for tx, ty in ((x + printed.width * 0.18, y - th * 0.3), (x + printed.width * 0.72, y - th * 0.3)):
        draw.rectangle((tx, ty, tx + tw, ty + th), fill=(232, 220, 180, 200))
    return canvas


# ---------------------------------------------------------------- red marker

def _jitter(n: int, amp: float, seed: int) -> np.ndarray:
    rnd = np.random.default_rng(seed)
    knots = rnd.uniform(-amp, amp, size=max(4, n // 12))
    return np.interp(np.linspace(0, len(knots) - 1, n), np.arange(len(knots)), knots)


def mark_strokes(mark: dict, W: int, H: int, seed: int) -> list[np.ndarray]:
    """Hand-drawn stroke polylines (pixel coords) for one mark. Coordinates are 0..1 of the picture."""
    kind = mark.get("type", "circle")
    x, y = float(mark.get("x", 0.5)) * W, float(mark.get("y", 0.5)) * H
    w, h = float(mark.get("w", 0.22)) * W, float(mark.get("h", 0.18)) * H
    amp = min(W, H) * 0.006
    if kind == "circle":
        n = 140
        a0 = -2.2
        ang = np.linspace(a0, a0 + 2 * math.pi * 1.1, n)
        r = 1 + _jitter(n, 0.05, seed)
        pts = np.stack([x + w / 2 * r * np.cos(ang), y + h / 2 * r * np.sin(ang)], 1)
        return [pts]
    if kind == "underline":
        n = 60
        xs = np.linspace(x - w / 2, x + w / 2, n)
        ys = y + _jitter(n, amp * 1.2, seed) + np.linspace(0, h * 0.08, n)
        return [np.stack([xs, ys], 1)]
    if kind == "cross":
        a = np.stack([np.linspace(x - w / 2, x + w / 2, 30), np.linspace(y - h / 2, y + h / 2, 30) + _jitter(30, amp, seed)], 1)
        b = np.stack([np.linspace(x + w / 2, x - w / 2, 30), np.linspace(y - h / 2, y + h / 2, 30) + _jitter(30, amp, seed + 1)], 1)
        return [a, b]
    if kind == "check":
        p1, p2, p3 = (x - w / 2, y), (x - w / 8, y + h / 2), (x + w / 2, y - h / 2)
        a = np.stack([np.linspace(p1[0], p2[0], 20), np.linspace(p1[1], p2[1], 20)], 1)
        b = np.stack([np.linspace(p2[0], p3[0], 40), np.linspace(p2[1], p3[1], 40)], 1)
        return [a, b]
    if kind == "arrow":
        fx, fy = float(mark.get("from_x", 0.2)) * W, float(mark.get("from_y", 0.8)) * H
        n = 60
        tt = np.linspace(0, 1, n)
        # gentle curve
        mx, my = (fx + x) / 2 + (y - fy) * 0.15, (fy + y) / 2 - (x - fx) * 0.15
        xs = (1 - tt) ** 2 * fx + 2 * (1 - tt) * tt * mx + tt ** 2 * x
        ys = (1 - tt) ** 2 * fy + 2 * (1 - tt) * tt * my + tt ** 2 * y
        shaft = np.stack([xs, ys], 1)
        dx, dy = xs[-1] - xs[-5], ys[-1] - ys[-5]
        ang = math.atan2(dy, dx)
        L = min(W, H) * 0.04
        heads = []
        for s in (+1, -1):
            a = ang + math.pi + s * 0.5
            heads.append(np.array([[x, y], [x + L * math.cos(a), y + L * math.sin(a)]]))
        return [shaft] + heads
    return []


def draw_marks(base: np.ndarray, marks: list[dict], t: float, red, cfg: dict) -> np.ndarray:
    """Draw marks progressively onto a copy of `base`. Mark timing: 'at' (start, s) and 'dur' (s)."""
    out = None
    H, W = base.shape[:2]
    thick = max(4, int(min(W, H) * 0.007))
    for i, mark in enumerate(marks):
        at, dur = float(mark.get("at", 0.6)), float(mark.get("dur", 0.45))
        p = (t - at) / max(dur, 1e-3)
        if p <= 0:
            continue
        if out is None:
            out = base.copy()
        p = min(1.0, p)
        strokes = mark.get("_strokes")
        if strokes is None:
            strokes = mark_strokes(mark, W, H, seed=17 + i)
            mark["_strokes"] = strokes
        total = sum(len(s) for s in strokes)
        budget = int(total * p)
        for s in strokes:
            if budget <= 1:
                break
            seg = s[: min(len(s), budget)]
            budget -= len(seg)
            cv2.polylines(out, [seg.astype(np.int32).reshape(-1, 1, 2)], False, red, thick, cv2.LINE_AA)
        if mark.get("text") and p >= 1.0:
            note = mark.get("_note")
            if note is None:
                fpath = resolve_font(cfg["fonts"]["marker"])
                fnt = font(fpath, max(24, int(min(W, H) * 0.055)))
                note = text_block([str(mark["text"])], fnt, fill=red)
                angle = float(mark.get("angle", -4))
                pil = Image.fromarray(note).rotate(angle, resample=Image.BICUBIC, expand=True)
                note = np.array(pil)
                mark["_note"] = note
            age = (t - at - dur) / 0.25
            nx = float(mark.get("text_x", mark.get("x", 0.5))) * W - note.shape[1] / 2
            ny = float(mark.get("text_y", float(mark.get("y", 0.5)) + float(mark.get("h", 0.18)) * 0.75)) * H
            blend(out, note, int(nx), int(ny), opacity=min(1.0, max(0.0, age)))
    return base if out is None else out


# ---------------------------------------------------------------- shots

class Shot:
    def __init__(self, start: float, duration: float):
        self.start = start
        self.duration = duration

    @property
    def end(self) -> float:
        return self.start + self.duration

    def frame(self, t: float) -> np.ndarray:  # t = seconds since shot start
        raise NotImplementedError


class ImageShot(Shot):
    def __init__(self, start, duration, image: Image.Image, motion: str, size, cfg: dict,
                 marks: list[dict] | None = None, photo: bool = False, seed: int = 0, ad: dict | None = None):
        super().__init__(start, duration)
        self.W, self.H = size
        self.BW, self.BH = int(self.W * MARGIN), int(self.H * MARGIN)
        if photo:
            base = np.array(archival_print(image, cfg, self.BW, self.BH, seed))
        else:
            base = cover(image, self.BW, self.BH)
        if ad:
            base = draw_ad_overlay(base, ad, cfg)
        self.base = add_grain(base, float(cfg["style"].get("grain", 0)), seed)
        self.motion = motion
        self.marks = [dict(m) for m in (marks or [])]
        self.red = tuple(int(c) for c in hex_to_rgb(cfg["style"]["palette"]["red"]))
        self.cfg = cfg

    def _camera(self, p: float):
        e = ease(p)
        zmax = MARGIN
        m = self.motion
        if m == "zoom_in":
            z, dx, dy = 1.0 + (zmax * 0.98 - 1.0) * e, 0.0, 0.0
        elif m == "zoom_out":
            z, dx, dy = zmax * 0.98 - (zmax * 0.98 - 1.0) * e, 0.0, 0.0
        elif m in ("pan_left", "pan_right", "pan_up", "pan_down"):
            z = 1.12
            travel = 2 * e - 1
            sign = 1 if m in ("pan_left", "pan_up") else -1
            dx = -sign * travel if m in ("pan_left", "pan_right") else 0.0
            dy = -sign * travel if m in ("pan_up", "pan_down") else 0.0
        elif m == "drift":
            z, dx, dy = 1.05 + 0.12 * e, 0.6 * (e - 0.5), 0.4 * (0.5 - e)
        else:  # static: slow push so the frame never looks frozen
            z, dx, dy = 1.02 + 0.06 * p, 0.0, 0.0
        return z, dx, dy

    def frame(self, t: float) -> np.ndarray:
        p = t / max(self.duration, 1e-6)
        z, dx, dy = self._camera(p)
        win_w, win_h = self.BW / z, self.BH / z
        free_x, free_y = (self.BW - win_w) / 2, (self.BH - win_h) / 2
        cx = self.BW / 2 + dx * free_x * 0.95
        cy = self.BH / 2 + dy * free_y * 0.95
        s = self.W / win_w
        M = np.float32([[s, 0, self.W / 2 - s * cx], [0, s, self.H / 2 - s * cy]])
        src = draw_marks(self.base, self.marks, t, self.red, self.cfg) if self.marks else self.base
        return cv2.warpAffine(src, M, (self.W, self.H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def _sunburst(size, pal, cfg, seed=5) -> np.ndarray:
    W, H = size
    bg = Image.new("RGB", size, pal["paper"])
    draw = ImageDraw.Draw(bg)
    cx, cy, r = W / 2, H / 2, max(W, H)
    for i in range(24):
        a0, a1 = i * 15, i * 15 + 7.5
        pts = [(cx, cy)] + [(cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a))) for a in (a0, a1)]
        draw.polygon(pts, fill=tuple(int(c * 0.93) for c in pal["paper"]))
    return add_grain(np.array(bg), float(cfg["style"].get("grain", 0)), seed)


class TitleShot(Shot):
    def __init__(self, start, duration, text: str, cfg: dict, size):
        super().__init__(start, duration)
        self.W, self.H = size
        self.pal = {k: hex_to_rgb(v) for k, v in cfg["style"]["palette"].items()}
        self.bg = _sunburst(size, self.pal, cfg)
        head = resolve_font(cfg["fonts"]["headline"])
        fnt, lines = fit_font(text.upper(), head, int(self.W * 0.8), int(self.H * 0.45), start=int(self.H * 0.16))
        self.title = text_block(lines, fnt, fill=self.pal["ink"])

    def frame(self, t: float) -> np.ndarray:
        out = self.bg.copy()
        p = ease(t / 0.45)
        scale = 0.85 + 0.15 * p + 0.02 * (t / max(self.duration, 1e-6))
        th, tw = self.title.shape[:2]
        img = cv2.resize(self.title, (max(1, int(tw * scale)), max(1, int(th * scale))), interpolation=cv2.INTER_LINEAR)
        h, w = img.shape[:2]
        blend(out, img, (self.W - w) // 2, (self.H - h) // 2, opacity=p)
        bar_w = int(self.W * 0.35 * ease((t - 0.2) / 0.6))
        if bar_w > 0:
            y = (self.H + h) // 2 + int(self.H * 0.02)
            x = (self.W - bar_w) // 2
            out[y : y + max(6, self.H // 120), x : x + bar_w] = self.pal["red"]
        return out


class StatShot(Shot):
    """Big number that counts up: value, prefix, suffix, label, decimals."""

    def __init__(self, start, duration, spec: dict, cfg: dict, size):
        super().__init__(start, duration)
        self.W, self.H = size
        self.spec = spec
        self.pal = {k: hex_to_rgb(v) for k, v in cfg["style"]["palette"].items()}
        self.bg = _sunburst(size, self.pal, cfg, seed=9)
        self.head = resolve_font(cfg["fonts"]["headline"])
        self.body = resolve_font(cfg["fonts"]["body"])
        label = str(spec.get("label", ""))
        self.label = None
        if label:
            fnt, lines = fit_font(label.upper(), self.body, int(self.W * 0.8), int(self.H * 0.16), start=int(self.H * 0.06))
            self.label = text_block(lines, fnt, fill=self.pal["ink"])
        self.cache: dict[str, np.ndarray] = {}

    def _num(self, v: float) -> str:
        dec = int(self.spec.get("decimals", 0))
        txt = f"{v:,.{dec}f}"
        return f"{self.spec.get('prefix', '')}{txt}{self.spec.get('suffix', '')}"

    def frame(self, t: float) -> np.ndarray:
        out = self.bg.copy()
        p = ease(t / max(0.6, min(1.4, self.duration * 0.45)))
        txt = self._num(float(self.spec["value"]) * p)
        if txt not in self.cache:
            fnt = font(self.head, int(self.H * (0.26 if self.W > self.H else 0.14)))
            self.cache[txt] = text_block([txt], fnt, fill=self.pal["red"], stroke=max(4, self.H // 160), stroke_fill=self.pal["ink"])
        num = self.cache[txt]
        y_num = int(self.H * 0.42) - num.shape[0] // 2
        blend(out, num, (self.W - num.shape[1]) // 2, y_num)
        if self.label is not None:
            blend(out, self.label, (self.W - self.label.shape[1]) // 2, y_num + num.shape[0] + int(self.H * 0.02),
                  opacity=ease((t - 0.3) / 0.4))
        return out


class ChartShot(Shot):
    """Bar or line chart that draws itself. Spec: kind, labels, values, title, unit, highlight, note."""

    def __init__(self, start, duration, spec: dict, cfg: dict, size):
        super().__init__(start, duration)
        self.W, self.H = size
        self.spec = spec
        self.pal = {k: hex_to_rgb(v) for k, v in cfg["style"]["palette"].items()}
        self.head = resolve_font(cfg["fonts"]["headline"])
        self.body = resolve_font(cfg["fonts"]["body"])
        bg = np.full((self.H, self.W, 3), self.pal["paper"], dtype=np.uint8)
        title = spec.get("title", "")
        if title:
            fnt, lines = fit_font(title.upper(), self.head, int(self.W * 0.86), int(self.H * 0.16), start=int(self.H * 0.09))
            blk = text_block(lines, fnt, fill=self.pal["ink"])
            blend(bg, blk, (self.W - blk.shape[1]) // 2, int(self.H * 0.05))
        self.bg = add_grain(bg, float(cfg["style"].get("grain", 0)), 11)
        portrait = self.H > self.W
        self.area = (int(self.W * 0.1), int(self.H * (0.30 if portrait else 0.26)), int(self.W * 0.9), int(self.H * (0.58 if portrait else 0.70)))
        self.grow_time = max(0.8, duration * 0.55)

    def _fmt(self, v: float) -> str:
        unit = self.spec.get("unit", "")
        dec = self.spec.get("decimals")
        if dec is None:
            dec = 0 if float(v).is_integer() else 2
        txt = f"{v:,.{int(dec)}f}"
        return f"{unit}{txt}" if unit in ("$", "€", "£") else f"{txt}{unit}"

    def reveal_times(self) -> list[float]:
        n = len(self.spec["values"])
        g = self.grow_time
        if self.spec["kind"] == "bar":
            return [i * g / (n * 1.6) + g / 1.6 for i in range(n)]
        return [g * i / max(1, n - 1) for i in range(n)]

    def frame(self, t: float) -> np.ndarray:
        img = Image.fromarray(self.bg.copy())
        draw = ImageDraw.Draw(img)
        x0, y0, x1, y1 = self.area
        labels, values = self.spec["labels"], [float(v) for v in self.spec["values"]]
        vmax = max(values) * 1.15 or 1.0
        n = len(values)
        g = self.grow_time
        lab_font = font(self.body, max(18, int(min(self.W, self.H) * 0.04)))
        val_font = font(self.head, max(22, int(min(self.W, self.H) * 0.06)))
        highlight = self.spec.get("highlight")
        draw.line((x0, y1, x1, y1), fill=self.pal["ink"], width=max(3, self.H // 300))
        if self.spec["kind"] == "bar":
            slot = (x1 - x0) / n
            bw = slot * 0.62
            for i, (lab, v) in enumerate(zip(labels, values)):
                p = ease((t - i * g / (n * 1.6)) / (g / 1.6))
                bx = x0 + slot * i + (slot - bw) / 2
                top = y1 - (y1 - y0) * (v / vmax) * p
                color = self.pal["red"] if (highlight is not None and i == highlight) else self.pal["green"]
                if p > 0:
                    draw.rectangle((bx, top, bx + bw, y1), fill=color, outline=self.pal["ink"], width=3)
                draw.text((bx + bw / 2, y1 + 12), str(lab), font=lab_font, fill=self.pal["ink"], anchor="ma")
                if p >= 0.999:
                    draw.text((bx + bw / 2, top - 8), self._fmt(v), font=val_font, fill=self.pal["ink"], anchor="md")
        else:
            p_all = ease(t / g)
            pts = [(x0 + (x1 - x0) * i / max(1, n - 1), y1 - (y1 - y0) * (v / vmax)) for i, v in enumerate(values)]
            upto = p_all * (n - 1)
            k = int(math.floor(upto))
            drawn = pts[: k + 1]
            if k < n - 1:
                f = upto - k
                (ax, ay), (bx2, by2) = pts[k], pts[k + 1]
                drawn.append((ax + (bx2 - ax) * f, ay + (by2 - ay) * f))
            if len(drawn) >= 2:
                draw.line(drawn, fill=self.pal["green"], width=max(6, self.H // 120), joint="curve")
            for i, (lab, pt) in enumerate(zip(labels, pts)):
                draw.text((pt[0], y1 + 12), str(lab), font=lab_font, fill=self.pal["ink"], anchor="ma")
                if i <= upto + 1e-6:
                    r = max(7, self.H // 110)
                    color = self.pal["red"] if (highlight is not None and i == highlight) else self.pal["ink"]
                    draw.ellipse((pt[0] - r, pt[1] - r, pt[0] + r, pt[1] + r), fill=color)
                    draw.text((pt[0], pt[1] - r - 6), self._fmt(values[i]), font=val_font, fill=self.pal["ink"], anchor="md")
        return np.array(img)


# ---------------------------------------------------------------- Vox-style document + highlighter

class DocShot(Shot):
    """A paper clipping of a study/article; a yellow highlighter sweeps over the key phrase.

    spec: source (e.g. "Journal of Consumer Research, 2005"), headline, body (2–4 sentences, paraphrased),
          highlight (exact substring of body), at (s after narration start, default 1.0)
    """

    def __init__(self, start, duration, spec: dict, cfg: dict, size, lead_in: float = 0.0, seed: int = 0):
        super().__init__(start, duration)
        self.W, self.H = size
        pal = {k: hex_to_rgb(v) for k, v in cfg["style"]["palette"].items()}
        self.pal = pal
        portrait = self.H > self.W
        BW, BH = int(self.W * MARGIN), int(self.H * MARGIN)
        self.BW, self.BH = BW, BH
        desk = np.full((BH, BW, 3), tuple(int(c * 0.82) for c in pal["paper"]), dtype=np.uint8)
        self.desk = add_grain(desk, 0.05, seed)
        pw = int(BW * (0.78 if portrait else 0.56))
        head_f = resolve_font(cfg["fonts"]["headline"])
        body_f = resolve_font(cfg["fonts"]["serif"])
        small = font(resolve_font(cfg["fonts"]["body"]), max(16, int(pw * 0.028)))
        hfnt, hlines = fit_font(spec.get("headline", "").upper(), head_f, int(pw * 0.86), int(pw * 0.30), start=int(pw * 0.085))
        bfnt = font(body_f, max(18, int(pw * 0.045)))
        from .text import wrap as _wrap
        body = spec.get("body", "")
        blines = _wrap(body, bfnt, int(pw * 0.86))
        lh = int(bfnt.size * 1.35)
        ph = int(pw * 0.12 + len(hlines) * hfnt.size * 1.1 + len(blines) * lh + pw * 0.16)
        paper = Image.new("RGB", (pw, ph), (250, 246, 236))
        d = ImageDraw.Draw(paper)
        x0 = int(pw * 0.07)
        y = int(pw * 0.05)
        d.text((x0, y), spec.get("source", "").upper(), font=small, fill=pal["red"])
        y += int(small.size * 1.8)
        for ln in hlines:
            d.text((x0, y), ln, font=hfnt, fill=pal["ink"])
            y += int(hfnt.size * 1.1)
        y += int(pw * 0.02)
        d.line((x0, y, pw - x0, y), fill=pal["ink"], width=2)
        y += int(pw * 0.03)
        # find highlight span (line, start x, end x) per line
        target = spec.get("highlight", "")
        self.spans = []  # (y_top, x_start, x_end, height) in paper coords
        flat, positions = "", []
        for i, ln in enumerate(blines):
            positions.append((len(flat), i))
            flat += ln + " "
        hs = flat.find(target) if target else -1
        he = hs + len(target)
        line_y = []
        for i, ln in enumerate(blines):
            line_y.append(y)
            y += lh
        if hs >= 0:
            for (off, i) in positions:
                ln = blines[i]
                a, b = max(hs, off), min(he, off + len(ln))
                if a < b:
                    xa = x0 + bfnt.getlength(ln[: a - off])
                    xb = x0 + bfnt.getlength(ln[: b - off])
                    self.spans.append((line_y[i], xa, xb, bfnt.size))
        self.paper_plain = paper.copy()
        for i, ln in enumerate(blines):
            d.text((x0, line_y[i]), ln, font=bfnt, fill=pal["ink"])
        self.text_layer = paper  # paper with text
        self.blines, self.line_y, self.bfnt, self.x0 = blines, line_y, bfnt, x0
        self.angle = float(np.random.default_rng(seed).uniform(-2.5, 2.5))
        self.at = float(spec.get("at", 1.0)) + lead_in
        self.hl_dur = float(spec.get("dur", 0.9))
        self.pw, self.ph = pw, ph
        self.yellow = (255, 222, 89)
        self._cache_p = None
        self._cache_base = None

    def _compose(self, p: float) -> np.ndarray:
        paper = self.paper_plain.copy()
        d = ImageDraw.Draw(paper)
        total = sum(xb - xa for _y, xa, xb, _h in self.spans) or 1
        budget = total * p
        for (ly, xa, xb, h) in self.spans:
            if budget <= 0:
                break
            wlen = min(xb - xa, budget)
            budget -= wlen
            d.rectangle((xa - 4, ly + h * 0.12, xa + wlen + 4, ly + h * 1.12), fill=self.yellow)
        for i, ln in enumerate(self.blines):
            d.text((self.x0, self.line_y[i]), ln, font=self.bfnt, fill=self.pal["ink"])
        # header area from the text layer (source + headline)
        top_h = self.line_y[0] if self.line_y else self.ph
        paper.paste(self.text_layer.crop((0, 0, self.pw, top_h)), (0, 0))
        rgba = paper.convert("RGBA").rotate(self.angle, resample=Image.BICUBIC, expand=True)
        base = Image.fromarray(self.desk.copy())
        shadow = Image.new("RGBA", rgba.size, (0, 0, 0, 0))
        shadow.paste((0, 0, 0, 80), mask=rgba.split()[3])
        shadow = shadow.filter(ImageFilter.GaussianBlur(14))
        x, y = (self.BW - rgba.width) // 2, max(0, (self.BH - rgba.height) // 2 - int(self.BH * 0.06))
        base.paste(shadow, (x + 10, y + 16), shadow)
        base.paste(rgba, (x, y), rgba)
        return np.array(base)

    def frame(self, t: float) -> np.ndarray:
        p = round(min(1.0, max(0.0, (t - self.at) / self.hl_dur)) * 24) / 24  # quantised: fewer recomposes
        if p != self._cache_p:
            self._cache_base = self._compose(p)
            self._cache_p = p
        z = 1.0 + 0.12 * ease(t / max(self.duration, 1e-6))
        win_w = self.BW / z
        s = self.W / win_w
        cx, cy = self.BW / 2, self.BH / 2
        M = np.float32([[s, 0, self.W / 2 - s * cx], [0, s, self.H / 2 - s * cy]])
        return cv2.warpAffine(self._cache_base, M, (self.W, self.H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


# ---------------------------------------------------------------- kinetic typography

class KineticShot(Shot):
    """Words slam in exactly when they are spoken. Words wrapped in *stars* get the accent colour.

    spec: text (defaults to the beat text), bg ("paper"|"ink"|"red")
    """

    def __init__(self, start, duration, text: str, words_timed, cfg: dict, size, lead_in: float, bg: str = "paper"):
        super().__init__(start, duration)
        self.W, self.H = size
        pal = {k: hex_to_rgb(v) for k, v in cfg["style"]["palette"].items()}
        self.pal = pal
        bg_color = {"paper": pal["paper"], "ink": pal["ink"], "red": pal["red"], "green": pal["green"]}.get(bg, pal["paper"])
        fg = pal["paper"] if bg in ("ink", "red", "green") else pal["ink"]
        self.bg = add_grain(np.full((self.H, self.W, 3), bg_color, dtype=np.uint8), 0.04, 21)
        head = resolve_font(cfg["fonts"]["headline"])
        raw = text.split()
        clean = [w.strip("*") for w in raw]
        accent = [w.startswith("*") or w.endswith("*") for w in raw]
        fnt, lines = fit_font(" ".join(clean).upper(), head, int(self.W * 0.84), int(self.H * 0.62),
                              start=int(min(self.W, self.H) * 0.2), min_size=40)
        # positions of each word
        lh = int(fnt.size * 1.05)
        total_h = lh * len(lines)
        y = (self.H - total_h) // 2
        self.items = []  # (word_img, x, y, appear_time)
        wi = 0
        times = [s for _w, s, _e in words_timed] if words_timed else []
        for line in lines:
            ws = line.split(" ")
            widths = [fnt.getlength(w) for w in ws]
            space = fnt.getlength(" ")
            line_w = sum(widths) + space * (len(ws) - 1)
            x = (self.W - line_w) / 2
            for w, ww in zip(ws, widths):
                color = pal["red"] if (wi < len(accent) and accent[wi]) else fg
                img = text_block([w], fnt, fill=color)
                appear = (times[wi] if wi < len(times) else wi * 0.25) + lead_in
                self.items.append((img, int(x), int(y), appear))
                x += ww + space
                wi += 1
            y += lh

    def frame(self, t: float) -> np.ndarray:
        out = self.bg.copy()
        for img, x, y, appear in self.items:
            age = t - appear
            if age < 0:
                continue
            p = min(1.0, age / 0.12)
            scale = 1.35 - 0.35 * ease(p)
            im = img
            if abs(scale - 1) > 1e-3:
                h, w = img.shape[:2]
                im = cv2.resize(img, (max(1, int(w * scale)), max(1, int(h * scale))))
            dx, dy = (im.shape[1] - img.shape[1]) // 2, (im.shape[0] - img.shape[0]) // 2
            blend(out, im, x - dx, y - dy, opacity=min(1.0, p * 2))
        return out


# ---------------------------------------------------------------- fake 1950s ad gag

def draw_ad_overlay(base: np.ndarray, ad: dict, cfg: dict) -> np.ndarray:
    """Starburst badge + slogan ribbon baked onto the picture: the recurring '1950s ad' gag."""
    pal = {k: hex_to_rgb(v) for k, v in cfg["style"]["palette"].items()}
    img = Image.fromarray(base).convert("RGBA")
    W, H = img.size
    d = ImageDraw.Draw(img)
    head = resolve_font(cfg["fonts"]["headline"])
    if ad.get("badge"):
        r = int(min(W, H) * 0.15)
        cx, cy = int(W * float(ad.get("badge_x", 0.76))), int(H * float(ad.get("badge_y", 0.3)))
        pts = []
        for k in range(32):
            rr = r if k % 2 == 0 else r * 0.78
            a = math.pi * 2 * k / 32
            pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
        d.polygon(pts, fill=pal["accent"] + (255,), outline=pal["ink"] + (255,), width=6)
        fnt, lines = fit_font(str(ad["badge"]).upper(), head, int(r * 1.25), int(r * 1.1), start=int(r * 0.5), min_size=20)
        blk = Image.fromarray(text_block(lines, fnt, fill=pal["ink"])).rotate(12, resample=Image.BICUBIC, expand=True)
        img.alpha_composite(blk, (cx - blk.width // 2, cy - blk.height // 2))
    if ad.get("slogan"):
        fnt, lines = fit_font(str(ad["slogan"]).upper(), head, int(W * 0.62), int(H * 0.14), start=int(H * 0.07), min_size=24)
        blk = text_block(lines, fnt, fill=pal["paper"], pad=int(fnt.size * 0.35))
        bh, bw = blk.shape[:2]
        ribbon = Image.new("RGBA", (bw, bh), pal["red"] + (255,))
        ribbon.alpha_composite(Image.fromarray(blk))
        ribbon = ribbon.rotate(-3, resample=Image.BICUBIC, expand=True)
        img.alpha_composite(ribbon, ((W - ribbon.width) // 2, int(H * float(ad.get("slogan_y", 0.55)))))
    return np.array(img.convert("RGB"))
