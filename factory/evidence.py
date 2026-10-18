"""Research cards as archival EVIDENCE: a yellowed, torn newspaper/journal clipping on the case desk, with a
red EVIDENCE tag carrying the source line. Only the headline and the one key sentence are sharp (the rest of
the summary is out of focus), and the red marker hand underlines or circles the key phrase exactly when the
narrator says it. The clipping drops onto the desk, the camera keeps creeping in (4 %) with a slight tilt.

visual: {"type": "doc", "doc": {
    "source": "Management Science · 1990",            # journal · year (a leading "Summary ·" is dropped)
    "headline": "Gambling with the house money",
    "body": "2–4 sentences, paraphrased",
    "highlight": "exact substring of body",            # the sentence that holds it stays sharp
    "mark": "underline" | "circle",                     # never a strike-through
    "on": "<word>" | "at": s,                           # when the marker starts (narration time)
    "dur": 0.9,                                         # marker time
    "flash": true}}                                     # flashback: drops in already marked (short)
"""
from __future__ import annotations

import math
import re

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .config import hex_to_rgb, resolve_font
from .draw import hand_path, paste_hand
from .shots import Shot, _jitter, add_grain, ease
from .text import font

PAPER = (238, 226, 196)
INK = (38, 32, 26)
PUSH = 0.04   # camera push-in over the shot
TILT = 0.7    # degrees of camera tilt over the shot
DROP = 0.42   # seconds for the clipping to land


def _pal(cfg):
    return {k: hex_to_rgb(v) for k, v in cfg["style"]["palette"].items()}


def _font(cfg, key, fallback_key, size):
    fonts = cfg["fonts"]
    try:
        return font(resolve_font(fonts[key]), size)
    except Exception:  # noqa: BLE001 — older channel configs: fall back to the serif
        return font(resolve_font(fonts[fallback_key]), size)


def desk(W: int, H: int, pal: dict, seed: int = 4) -> np.ndarray:
    """The case desk (same family as the case-file shots): dark green lacquered wood + vignette."""
    base = np.array([int(c * 0.55) for c in pal["green"]], np.float32)
    rnd = np.random.default_rng(seed)
    yy = np.arange(H, dtype=np.float32)[:, None]
    xx = np.arange(W, dtype=np.float32)[None, :]
    warp = cv2.GaussianBlur(rnd.standard_normal((H // 8 + 1, W // 8 + 1)).astype(np.float32), (0, 0), 3)
    warp = cv2.resize(warp, (W, H)) * 18
    grain = np.sin((yy + warp) * 0.09) * 0.5 + np.sin((yy + warp * 1.7) * 0.023) * 0.5
    img = base[None, None, :] * (1 + 0.07 * grain[..., None])
    r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    img *= (1 - 0.35 * np.clip(r - 0.35, 0, 1) ** 1.4)[..., None]
    return add_grain(np.clip(img, 0, 255).astype(np.uint8), 0.04, seed)


def _halftone(w: int, h: int, seed: int, step: int) -> np.ndarray:
    """Multiplicative print texture: a 45° dot screen whose dot size wanders (uneven old ink)."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    u, v = (xx + yy) / math.sqrt(2), (xx - yy) / math.sqrt(2)
    d = np.sqrt(((u % step) - step / 2) ** 2 + ((v % step) - step / 2) ** 2) / (step / 2)
    rnd = np.random.default_rng(seed)
    tone = cv2.resize(cv2.GaussianBlur(rnd.random((h // 40 + 2, w // 40 + 2)).astype(np.float32), (0, 0), 1.2), (w, h))
    radius = 0.25 + 0.35 * tone
    dots = np.clip((radius - d) * 3, 0, 1)
    return 1 - 0.07 * dots


def _aged_paper(w: int, h: int, seed: int) -> np.ndarray:
    rnd = np.random.default_rng(seed)
    img = np.ones((h, w, 3), np.float32) * np.array(PAPER, np.float32)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    # yellowing: darker and warmer towards the edges
    edge = np.minimum.reduce([xx, yy, w - xx, h - yy]) / (0.12 * min(w, h))
    yel = np.clip(1 - edge, 0, 1) ** 1.6
    img *= (1 - 0.13 * yel)[..., None]
    img[..., 2] *= (1 - 0.10 * yel)
    # foxing / tea stains
    for _ in range(int(rnd.integers(3, 6))):
        cx, cy = rnd.uniform(0, w), rnd.uniform(0, h)
        rr = rnd.uniform(0.04, 0.12) * min(w, h)
        s = np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * rr * rr)))
        img *= (1 - 0.06 * s)[..., None]
        img[..., 2] *= (1 - 0.05 * s)
    # one soft fold crease
    fy = rnd.uniform(0.55, 0.75) * h
    crease = np.exp(-((yy - fy - (xx - w / 2) * 0.03) ** 2) / 18)
    img *= (1 - 0.05 * crease)[..., None]
    img *= _halftone(w, h, seed, max(5, int(min(w, h) / 150)))[..., None]
    noise = cv2.GaussianBlur(rnd.standard_normal((h, w)).astype(np.float32), (0, 0), 0.7) * 5
    img += noise[..., None]
    return np.clip(img, 0, 255).astype(np.uint8)


def _torn_alpha(w: int, h: int, seed: int, rough: float) -> np.ndarray:
    rnd = np.random.default_rng(seed)
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)
    pts = []
    n = 70
    def jag(k):
        base = _jitter(n + 1, rough * 0.5, seed + k) + rough * 0.5
        return base + rnd.uniform(0, rough * 0.35, n + 1)
    top, right, bottom, left = jag(1), jag(2), jag(3), jag(4)
    for i in range(n + 1):
        pts.append((w * i / n, top[i]))
    for i in range(n + 1):
        pts.append((w - right[i], h * i / n))
    for i in range(n, -1, -1):
        pts.append((w * i / n, h - bottom[i]))
    for i in range(n, -1, -1):
        pts.append((left[i], h * i / n))
    d.polygon(pts, fill=255)
    return np.array(m.filter(ImageFilter.GaussianBlur(0.7)))


def _sentences(body: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+", body.strip()) if s]


def evidence_tag(cfg: dict, source: str, width: int, seed: int, word: str = "EVIDENCE") -> Image.Image:
    """Red shipping-tag label: EVIDENCE + journal · year, with a grommet hole."""
    pal = _pal(cfg)
    h = int(width * 0.40)
    tag = Image.new("RGBA", (width, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(tag)
    c = int(h * 0.28)
    red = tuple(int(x * 0.95) for x in pal["red"])
    d.polygon([(c, 0), (width, 0), (width, h), (c, h), (0, h - c), (0, c)], fill=red + (255,))
    hole = (int(h * 0.30), h // 2)
    r = int(h * 0.11)
    d.ellipse((hole[0] - r - 5, hole[1] - r - 5, hole[0] + r + 5, hole[1] + r + 5), fill=(214, 200, 168, 255))
    d.ellipse((hole[0] - r, hole[1] - r, hole[0] + r, hole[1] + r), fill=(0, 0, 0, 0))
    big = _font(cfg, "headline", "body", int(h * 0.46))
    small = _font(cfg, "typewriter", "serif", int(h * 0.15))
    x0 = int(h * 0.58)
    d.text((x0, int(h * 0.08)), word, font=big, fill=(250, 244, 230, 255))
    txt = source.upper()
    while small.getlength(txt) > width - x0 - h * 0.08 and small.size > 10:
        small = font(small.path, small.size - 1)
    d.text((x0, int(h * 0.70)), txt, font=small, fill=(250, 244, 230, 255))
    # worn print: speckle the tag a little
    a = np.array(tag)
    rnd = np.random.default_rng(seed)
    speck = cv2.GaussianBlur(rnd.random(a.shape[:2]).astype(np.float32), (0, 0), 1.0) > 0.62
    a[..., :3] = np.where(speck[..., None], (a[..., :3] * 0.9).astype(np.uint8), a[..., :3])
    return Image.fromarray(a)


class Clipping:
    """The clipping itself: aged paper, torn edges, sharp headline + key sentence, the rest out of focus.
    Knows where the highlight sits (spans in clipping pixels) and the marker strokes for it."""

    def __init__(self, spec: dict, cfg: dict, width: int, seed: int, portrait: bool):
        pal = _pal(cfg)
        self.pal = pal
        pw = width
        pad = int(pw * 0.07)
        hfnt = _font(cfg, "serif_bold", "serif", int(pw * (0.092 if portrait else 0.066)))
        bfnt = _font(cfg, "serif_old", "serif", int(pw * (0.060 if portrait else 0.038)))
        kfnt = _font(cfg, "typewriter", "serif", int(pw * (0.030 if portrait else 0.024)))
        from .text import wrap as _wrap
        hlines = _wrap(spec.get("headline", ""), hfnt, pw - 2 * pad)
        target = spec.get("highlight", "")
        sents = _sentences(spec.get("body", ""))
        ki = next((i for i, s in enumerate(sents) if target and target in s), 0)
        keep = sents[max(0, ki - 1): ki + 2]  # key sentence + one either side (out of focus)
        ki = keep.index(sents[ki]) if sents else 0
        # lay out words: (text, x, y, sentence index, in highlight)
        words = []
        hl_start = keep[ki].find(target) if keep and target else -1
        hl_end = hl_start + len(target)
        lh = int(bfnt.size * 1.42)
        y = pad + int(kfnt.size * 2.0) + int(len(hlines) * hfnt.size * 1.08) + int(pw * 0.05)
        body_top = y
        x = pad
        space = bfnt.getlength(" ")
        circle = spec.get("mark") == "circle"
        prev_inh = False
        for si, s in enumerate(keep):
            pos = 0
            for wd in s.split(" "):
                p0 = s.find(wd, pos)
                pos = p0 + len(wd)
                inh = si == ki and hl_start >= 0 and p0 >= hl_start and pos <= hl_end + 1
                if circle and inh != prev_inh and x > pad:  # breathing room either side of a circled phrase
                    x += bfnt.size * 0.95
                prev_inh = inh
                wl = bfnt.getlength(wd)
                if x + wl > pw - pad and x > pad:
                    x, y = pad, y + lh
                words.append((wd, x, y, si, inh))
                x += wl + space
        if spec.get("mark") == "circle":  # room above and below the circled line(s), so the loop never cuts text
            hy = sorted({wy for _w, _x, wy, _s, inh in words if inh})
            if hy:
                g = int(lh * 0.42)
                words = [(wd, wx, wy + (g if wy >= hy[0] else 0) + (g if wy > hy[-1] else 0), si, inh)
                         for wd, wx, wy, si, inh in words]
                y += 2 * g
        ph = y + lh + pad
        self.w, self.h = pw, ph
        paper = _aged_paper(pw, ph, seed)
        sharp = Image.new("L", (pw, ph), 0)
        soft = Image.new("L", (pw, ph), 0)
        ds, dsoft = ImageDraw.Draw(sharp), ImageDraw.Draw(soft)
        ds.text((pad, pad), "STUDY SUMMARY  ·  PARAPHRASED", font=kfnt, fill=200)
        yy = pad + int(kfnt.size * 2.0)
        for ln in hlines:
            ds.text((pad, yy), ln, font=hfnt, fill=255)
            yy += int(hfnt.size * 1.08)
        rule_y = yy + int(pw * 0.018)
        ds.line((pad, rule_y, pw - pad, rule_y), fill=255, width=max(2, pw // 400))
        ds.line((pad, rule_y + 6, pw - pad, rule_y + 6), fill=255, width=1)
        for wd, wx, wy, si, _inh in words:
            (ds if si == ki else dsoft).text((wx, wy), wd, font=bfnt, fill=255)
        soft = soft.filter(ImageFilter.GaussianBlur(max(2.0, bfnt.size * 0.11)))
        ink = np.maximum(np.array(sharp, np.float32), np.array(soft, np.float32) * 0.55) / 255.0
        # letterpress: a hair of bleed and a few dropouts
        rnd = np.random.default_rng(seed + 9)
        ink = cv2.GaussianBlur(ink, (0, 0), 0.45)
        drop = cv2.GaussianBlur(rnd.random(ink.shape).astype(np.float32), (0, 0), 0.8)
        ink *= np.clip((drop - 0.30) * 6, 0.55, 1.0)
        out = paper.astype(np.float32) * (1 - ink[..., None]) + np.array(INK, np.float32) * ink[..., None]
        alpha = _torn_alpha(pw, ph, seed, rough=pad * 0.42)
        self.rgba = np.dstack([np.clip(out, 0, 255).astype(np.uint8), alpha])
        # highlight spans per line: (x0, x1, y_top, y_bottom) in clipping px
        spans: dict[int, list] = {}
        for wd, wx, wy, si, inh in words:
            if inh:
                x1 = wx + bfnt.getlength(wd)
                s = spans.setdefault(wy, [wx, x1])
                s[0], s[1] = min(s[0], wx), max(s[1], x1)
        asc = bfnt.size
        self.spans = [(a, b, yv + asc * 0.12, yv + asc * 1.12) for yv, (a, b) in sorted(spans.items())]
        self.body_top, self.font_px = body_top, bfnt.size

    def strokes(self, kind: str, seed: int) -> list[np.ndarray]:
        """Hand-drawn marker strokes in clipping px. Underline: one stroke under each line of the phrase
        (left to right). Circle: one loose loop around the whole phrase."""
        if not self.spans:
            return []
        amp = self.font_px * 0.07
        if kind == "circle" and len(self.spans) == 1:  # a phrase that wraps gets underlined instead
            f = self.font_px
            x0, x1 = self.spans[0][0] - f * 0.1, self.spans[0][1] + f * 0.1
            y0, y1 = self.spans[0][2] - f * 0.15, self.spans[0][3] + f * 0.1
            a, b = (x1 - x0) / 2, (y1 - y0) / 2
            rx, ry = a * 1.08 + f * 0.1, b * 1.45  # squarish loop (superellipse) that really encloses the words
            n = 170
            a0 = -2.5
            ang = np.linspace(a0, a0 + 2 * math.pi * 1.07, n)
            r = 1 + _jitter(n, 0.025, seed)
            c, s_ = np.cos(ang), np.sin(ang)
            ex = np.sign(c) * np.abs(c) ** 0.5
            ey = np.sign(s_) * np.abs(s_) ** 0.5
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            return [np.stack([cx + rx * r * ex, cy + ry * r * ey], 1)]
        out = []
        for k, (a, b, _t, bot) in enumerate(self.spans):
            n = max(20, int((b - a) / 6))
            xs = np.linspace(a - self.font_px * 0.15, b + self.font_px * 0.2, n)
            ys = bot + self.font_px * 0.10 + _jitter(n, amp, seed + k) + np.linspace(0, self.font_px * 0.08, n)
            out.append(np.stack([xs, ys], 1))
        return out


class EvidenceShot(Shot):
    def __init__(self, start, duration, spec: dict, cfg: dict, size, mark_at: float = 1.0, seed: int = 0):
        super().__init__(start, duration)
        self.W, self.H = size
        self.spec, self.cfg = spec, cfg
        pal = _pal(cfg)
        self.red = tuple(int(c) for c in pal["red"])
        portrait = self.H > self.W
        self.portrait = portrait
        seed = int(spec.get("seed", seed))
        self.seed = seed
        BW, BH = int(self.W * 1.10), int(self.H * 1.10)
        self.BW, self.BH = BW, BH
        self.desk = desk(BW, BH, pal, seed % 7 + 2)
        cw = int(self.W * (0.90 if portrait else 0.60))
        self.clip = Clipping(spec, cfg, cw, seed, portrait)
        source = re.sub(r"^\s*summary\s*[·:\-]\s*", "", spec.get("source", ""), flags=re.I)
        self.tag = evidence_tag(cfg, source, int(cw * (0.50 if portrait else 0.42)), seed)
        self.angle = float(np.random.default_rng(seed).uniform(-1.8, 1.8))
        self.flash = bool(spec.get("flash"))
        self.mark_kind = spec.get("mark", "underline")
        self.mark_at = 0.0 if self.flash else mark_at
        self.mark_dur = float(spec.get("dur", 0.9 if self.mark_kind == "underline" else 1.0))
        self.strokes = self.clip.strokes(self.mark_kind, seed)
        self.thick = max(5, int(self.clip.font_px * 0.12))
        # where the clipping sits on the board: centred, in the part of the screen above the captions
        sw, sh = self.clip.w, self.clip.h
        top_zone = (0.70 if portrait else 0.80) * self.H  # captions live below this line
        y_top_screen = 0.115 * self.H if not portrait else 0.17 * self.H
        max_h = top_zone - y_top_screen - 0.03 * self.H
        self.scale = min(1.0, max_h / (sh * 1.03))
        self.cx = BW / 2
        self.cy = (BH - self.H) / 2 + y_top_screen + sh * self.scale / 2 + 0.01 * self.H
        self._layer_p = None
        self._board = None

    # -- geometry ----------------------------------------------------------------
    def _clip_to_board(self, x, y):
        """Clipping px -> board px (scale, rotate about the clipping centre, translate)."""
        s, a = self.scale, math.radians(-self.angle)
        dx, dy = (x - self.clip.w / 2) * s, (y - self.clip.h / 2) * s
        return (self.cx + dx * math.cos(a) - dy * math.sin(a), self.cy + dx * math.sin(a) + dy * math.cos(a))

    def _camera(self, t):
        p = ease(t / max(self.duration, 1e-6))
        z = (self.W / self.BW) * 1.10 * (1 + PUSH * p)  # board is 10 % larger than the frame
        rot = (-TILT / 2 + TILT * p) * (1 if self.seed % 2 else -1)
        M = cv2.getRotationMatrix2D((self.BW / 2, self.BH / 2), rot, z)
        M[0, 2] += self.W / 2 - self.BW / 2
        M[1, 2] += self.H / 2 - self.BH / 2
        return M

    def to_screen(self, bx, by, t):
        M = self._camera(t)
        return M[0, 0] * bx + M[0, 1] * by + M[0, 2], M[1, 0] * bx + M[1, 1] * by + M[1, 2]

    # -- layers ------------------------------------------------------------------
    def _marked_clip(self, p: float) -> np.ndarray:
        rgba = self.clip.rgba.copy()
        if p > 0 and self.strokes:
            ink = np.zeros(rgba.shape[:2], np.uint8)
            total = sum(len(s) for s in self.strokes)
            budget = int(total * p)
            for s in self.strokes:
                if budget <= 1:
                    break
                seg = s[: min(len(s), budget)]
                budget -= len(seg)
                cv2.polylines(ink, [seg.astype(np.int32).reshape(-1, 1, 2)], False, 255, self.thick, cv2.LINE_AA)
            a = (ink.astype(np.float32) / 255 * 0.92)[..., None]
            # marker over printed ink: multiply so the letters stay readable through the stroke
            mark = rgba[..., :3].astype(np.float32) * np.array(self.red, np.float32) / 255
            rgba[..., :3] = (rgba[..., :3] * (1 - a) + mark * a).astype(np.uint8)
        return rgba

    def _layer(self, p: float) -> tuple[np.ndarray, np.ndarray]:
        """Clipping (+tag) as an RGBA board-sized layer, and its shadow."""
        cl = Image.fromarray(self._marked_clip(p))
        cl = cl.resize((int(cl.width * self.scale), int(cl.height * self.scale)), Image.LANCZOS)
        cl = cl.rotate(self.angle, resample=Image.BICUBIC, expand=True)
        layer = Image.new("RGBA", (self.BW, self.BH), (0, 0, 0, 0))
        layer.alpha_composite(cl, (int(self.cx - cl.width / 2), int(self.cy - cl.height / 2)))
        tag = self.tag.rotate(self.angle - 7, resample=Image.BICUBIC, expand=True)
        tx, ty = self._clip_to_board(self.clip.w * (0.74 if self.portrait else 0.74), self.clip.h * 0.035)
        tsh = Image.new("RGBA", tag.size, (0, 0, 0, 0))
        tsh.paste((0, 0, 0, 90), mask=tag.split()[3])
        tsh = tsh.filter(ImageFilter.GaussianBlur(6))
        layer.alpha_composite(tsh, (int(tx - tag.width / 2) + 5, int(ty - tag.height / 2) + 8))
        layer.alpha_composite(tag, (int(tx - tag.width / 2), int(ty - tag.height / 2)))
        # a strip of real-looking tape over the tag: translucent, torn ends, paper fibres showing through
        tp = tape_strip(int(self.tag.width * 0.34), int(self.tag.height * 0.26), self.seed)
        tp = tp.rotate(self.angle - 7 + 4, resample=Image.BICUBIC, expand=True)
        layer.alpha_composite(tp, (int(tx - tp.width / 2), int(ty - tag.height / 2 - tp.height * 0.18)))
        arr = np.array(layer)
        sh = cv2.GaussianBlur(arr[..., 3].astype(np.float32), (0, 0), 14) / 255 * 0.55
        return arr, sh

    def _compose(self, p: float, drop: float) -> np.ndarray:
        if self._layer_p != p:
            self._layer_cache = self._layer(p)
            self._layer_p = p
        arr, sh = self._layer_cache
        out = self.desk.astype(np.float32)
        if drop < 1:  # landing: a little larger and higher, shadow further away, settles with a bump
            e = ease(drop)
            s = 1 + 0.10 * (1 - e)
            dy = -self.H * 0.05 * (1 - e)
            M = cv2.getRotationMatrix2D((self.cx, self.cy), 2.5 * (1 - e), s)
            M[1, 2] += dy
            arr = cv2.warpAffine(arr, M, (self.BW, self.BH), flags=cv2.INTER_LINEAR, borderValue=(0, 0, 0, 0))
            Ms = M.copy()
            Ms[0, 2] += 30 * (1 - e)
            Ms[1, 2] += 50 * (1 - e)
            sh = cv2.warpAffine(sh, Ms, (self.BW, self.BH)) * (0.5 + 0.5 * e)
        sx, sy = 10, 16
        sh = np.roll(np.roll(sh, sy, 0), sx, 1)
        out *= (1 - sh[..., None])
        a = arr[..., 3:4].astype(np.float32) / 255
        out = out * (1 - a) + arr[..., :3].astype(np.float32) * a
        return out.astype(np.uint8)

    # -- per frame ---------------------------------------------------------------
    def _mark_p(self, t):
        if self.flash:
            return 1.0
        return round(min(1.0, max(0.0, (t - self.mark_at) / self.mark_dur)) * 40) / 40

    def _tip(self, tt):
        q = min(1.0, max(0.0, (tt - self.mark_at) / self.mark_dur))
        pts = np.concatenate(self.strokes)
        x, y = pts[min(len(pts) - 1, int(q * (len(pts) - 1)))]
        bx, by = self._clip_to_board(float(x), float(y))
        return self.to_screen(bx, by, tt)

    def frame(self, t: float) -> np.ndarray:
        drop = min(1.0, t / DROP) if DROP > 0 else 1.0
        if drop >= 1:
            p = self._mark_p(t)
            if self._board is None or self._board[0] != p:
                self._board = (p, self._compose(p, 1.0))
            board = self._board[1]
        else:
            board = self._compose(self._mark_p(t), drop)
        frame = cv2.warpAffine(board, self._camera(t), (self.W, self.H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        if self.flash:  # flashback: a touch faded and warm, so it reads as "we've seen this"
            f = frame.astype(np.float32)
            g = f.mean(2, keepdims=True)
            f = f * 0.55 + g * 0.45
            f = f * 0.92 + np.array([18, 12, 0], np.float32)
            frame = np.clip(f, 0, 255).astype(np.uint8)
        if not self.flash and self.strokes:
            cx = np.concatenate(self.strokes)[:, 0].mean()
            mirrored = self._clip_to_board(cx, 0)[0] < self.BW * 0.4
            tip = hand_path(self._tip, self.mark_at, self.mark_at + self.mark_dur, t, self.W, self.H, mirrored, from_below=True)
            if tip:
                paste_hand(frame, "marker_under", tip[0], tip[1] + self.H * 0.004, mirrored)  # hand below the line: words stay readable
        return frame

    def sfx(self, shot_start: float) -> list[tuple[float, str]]:
        out = [(shot_start + 0.02, "paper")]
        if not self.flash and self.strokes:
            out.append((shot_start + self.mark_at, "marker"))
            if self.mark_dur > 0.6:
                out.append((shot_start + self.mark_at + self.mark_dur * 0.5, "marker"))
        return out


def tape_strip(w: int, h: int, seed: int) -> Image.Image:
    """Translucent adhesive tape: torn zig-zag ends, faint fibres, a soft sheen."""
    rnd = np.random.default_rng(seed + 77)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    # torn ends: each short side is a ragged line
    n = max(6, h // 4)
    left = np.interp(yy[:, 0], np.linspace(0, h, n), rnd.uniform(0, w * 0.06, n))
    right = w - np.interp(yy[:, 0], np.linspace(0, h, n), rnd.uniform(0, w * 0.06, n))
    inside = (xx >= left[:, None]) & (xx <= right[:, None])
    fib = cv2.GaussianBlur(rnd.standard_normal((h, w)).astype(np.float32), (0, 0), 0.9)
    streak = cv2.GaussianBlur(rnd.standard_normal((1, w)).astype(np.float32), (0, 0), 3)[0]
    alpha = (0.42 + 0.06 * fib + 0.05 * streak[None, :]) * inside
    edge = (np.abs(yy - 1) < 1.5) | (np.abs(yy - (h - 2)) < 1.5)
    alpha = np.where(edge & inside, alpha + 0.12, alpha)
    sheen = np.exp(-((yy - h * 0.35) ** 2) / (2 * (h * 0.12) ** 2)) * 18
    rgb = np.stack([238 + sheen + fib * 4, 231 + sheen + fib * 4, 206 + sheen * 0.6 + fib * 4], -1)
    a = np.clip(alpha * 255, 0, 255)
    return Image.fromarray(np.dstack([np.clip(rgb, 0, 255), a]).astype(np.uint8), "RGBA")
