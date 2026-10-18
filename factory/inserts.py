"""Cut-out inserts laid OVER any shot (Vox-style collage): a figure cut along its outline peeking in from the
edge, a newspaper clipping with torn edges, a photo print on tape. They enter with a quick slide + settle,
tremble a little while they are on, and leave again; marks and the pencil hand work on them like on frames.

Beat key (list, on any beat):
  "inserts": [{"file": "lv1940_slots.jpg" | "<frame key>", "kind": "cutout" | "clipping" | "photo",
               "from": "left" | "right" | "bottom" | "top", "x": 0.78, "y": 0.5, "w": 0.34,
               "on": "<word>" | "at": s, "dur": s (visible), "crop": [x0,y0,x1,y1], "caption": "...",
               "credit": "..." (archive files), "depth": true (cutout along the depth mask)}]
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

from .archive import ARCHIVE_DIR, _source, _torn_mask
from .config import ROOT, hex_to_rgb, resolve_font
from .text import blend, font


def _pal(cfg):
    return {k: hex_to_rgb(v) for k, v in cfg["style"]["palette"].items()}


def _edge(rgba: Image.Image, color, width: int) -> Image.Image:
    """Paper edge around an alpha shape: the cut-out's white border."""
    a = np.array(rgba.split()[3])
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (width * 2 + 1, width * 2 + 1))
    border = cv2.dilate(a, k)
    out = Image.new("RGBA", rgba.size, color + (0,))
    out.putalpha(Image.fromarray(border))
    out.alpha_composite(rgba)
    return out


def cutout(src: Image.Image, depth: np.ndarray | None, cfg: dict, seed: int) -> Image.Image:
    """Figure cut along its outline (depth near layer, or non-paper pixels), on a white paper edge."""
    from .draw import subject_mask
    base = np.array(src.convert("RGB"))
    d = None
    if depth is not None:
        d = np.array(Image.fromarray((np.clip(depth, 0, 1) * 255).astype(np.uint8)).resize(src.size, Image.BILINEAR)).astype(np.float32) / 255
    m = subject_mask(base, None, (0.0, 0.0, 1.0, 1.0), "shape")  # non-paper pixels (plain backdrops)
    if d is not None:  # light parts (chrome, white gloves) can match the paper: add the near depth layer
        m = np.maximum(m, subject_mask(base, d, (0.0, 0.0, 1.0, 1.0), "depth"))
    m8 = (np.clip(m, 0, 1) * 255).astype(np.uint8)
    ys, xs = np.where(m8 > 60)
    if len(xs) < 50:
        return photo(src, cfg, seed)
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    pad = int(min(src.size) * 0.03)
    box = (max(0, x0 - pad), max(0, y0 - pad), min(src.width, x1 + pad), min(src.height, y1 + pad))
    rgba = src.convert("RGBA").crop(box)
    rgba.putalpha(Image.fromarray(m8).crop(box))
    return _edge(rgba, (250, 246, 236), max(4, int(min(rgba.size) * 0.02)))


def clipping(src: Image.Image, cfg: dict, seed: int, caption: str | None = None) -> Image.Image:
    gray = ImageOps.autocontrast(src.convert("L"), cutoff=0.5).filter(ImageFilter.UnsharpMask(radius=1.5, percent=60))
    aged = ImageOps.colorize(gray, black=(40, 36, 30), white=(241, 232, 206))
    pad = max(8, int(min(aged.size) * 0.03))
    piece = ImageOps.expand(aged, border=pad, fill=(241, 232, 206)).convert("RGBA")
    piece.putalpha(_torn_mask(piece.width, piece.height, seed, rough=pad * 1.3))
    if caption:
        piece = _with_caption(piece, caption, cfg, (40, 36, 30), (241, 232, 206))
    return piece


def photo(src: Image.Image, cfg: dict, seed: int, caption: str | None = None, colour: bool = False) -> Image.Image:
    pal = _pal(cfg)
    if colour:  # modern stock photo: keep colour, slightly warm and soft so it sits on the paper
        from PIL import ImageEnhance
        tinted = ImageEnhance.Color(src.convert("RGB")).enhance(0.85)
        warm = Image.new("RGB", tinted.size, (255, 236, 200))
        tinted = Image.blend(tinted, warm, 0.08)
    else:
        gray = ImageOps.autocontrast(src.convert("L"), cutoff=1).filter(ImageFilter.UnsharpMask(radius=2, percent=80))
        tinted = ImageOps.colorize(gray, black=pal["ink"], white=tuple(min(255, c + 8) for c in pal["paper"]))
    border = max(10, int(min(tinted.size) * 0.035))
    printed = ImageOps.expand(tinted, border=border, fill=(250, 246, 236)).convert("RGBA")
    if caption:
        printed = _with_caption(printed, caption, cfg, pal["ink"], (250, 246, 236))
    return printed


def _with_caption(piece: Image.Image, caption: str, cfg: dict, ink, paper) -> Image.Image:
    fnt = font(resolve_font(cfg["fonts"]["body"]), max(14, int(piece.width * 0.032)))
    d = ImageDraw.Draw(piece)
    tw = d.textlength(caption, font=fnt)
    strip = int(fnt.size * 1.9)
    out = Image.new("RGBA", (piece.width, piece.height + strip), (0, 0, 0, 0))
    out.paste(piece, (0, 0))
    dd = ImageDraw.Draw(out)
    dd.rectangle((0, piece.height - 2, piece.width, piece.height + strip), fill=paper + (255,))
    dd.text(((piece.width - tw) / 2, piece.height + strip * 0.25), caption, font=fnt, fill=ink)
    return out


def _tape(img: Image.Image, seed: int) -> Image.Image:
    rnd = np.random.default_rng(seed)
    out = img.copy()
    d = ImageDraw.Draw(out, "RGBA")
    tw, th = int(img.width * 0.22), int(img.height * 0.06)
    for fx in (0.15, 0.65):
        x = int(img.width * fx + rnd.uniform(-10, 10))
        d.rectangle((x, -th // 2, x + tw, th // 2 + 2), fill=(232, 220, 180, 190))
    return out


class Insert:
    def __init__(self, spec: dict, start: float, end: float, img: Image.Image, size, seed: int):
        self.spec, self.start, self.end = spec, start, end
        self.W, self.H = size
        w = int(self.W * float(spec.get("w", 0.34)))
        s = w / img.width
        img = img.resize((w, max(1, int(img.height * s))), Image.LANCZOS)
        angle = float(spec.get("angle", np.random.default_rng(seed).uniform(-4, 4)))
        img = img.rotate(angle, resample=Image.BICUBIC, expand=True)
        # drop shadow baked in
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        sh.paste((0, 0, 0, 110), mask=img.split()[3])
        sh = sh.filter(ImageFilter.GaussianBlur(max(4, w // 60)))
        canvas = Image.new("RGBA", (img.width + 30, img.height + 30), (0, 0, 0, 0))
        canvas.alpha_composite(sh, (18, 22))
        canvas.alpha_composite(img, (0, 0))
        self.img = np.array(canvas)
        self.cx, self.cy = float(spec.get("x", 0.75)) * self.W, float(spec.get("y", 0.5)) * self.H
        self.side = spec.get("from", "right")
        self.seed = seed

    def _off(self):
        h, w = self.img.shape[:2]
        return {"left": (-w, self.cy), "right": (self.W + w, self.cy),
                "top": (self.cx, -h), "bottom": (self.cx, self.H + h)}[self.side]

    def pos(self, t: float):
        h, w = self.img.shape[:2]
        ox, oy = self._off()
        a_in, a_out = 0.45, 0.35
        if t < self.start or t > self.end:
            return None
        if t < self.start + a_in:
            p = (t - self.start) / a_in
            e = 1 - (1 - p) ** 3  # ease-out with a small overshoot
            e = e + 0.08 * math.sin(p * math.pi)
            x, y = ox + (self.cx - ox) * e, oy + (self.cy - oy) * e
        elif t > self.end - a_out:
            p = (t - (self.end - a_out)) / a_out
            e = p * p
            x, y = self.cx + (ox - self.cx) * e, self.cy + (oy - self.cy) * e
        else:
            x, y = self.cx, self.cy
        # paper tremble
        x += math.sin(t * 9.0 + self.seed) * self.W * 0.0025
        y += math.cos(t * 7.3 + self.seed) * self.H * 0.003
        return int(x - w / 2), int(y - h / 2)

    def draw(self, frame: np.ndarray, t: float) -> None:
        p = self.pos(t)
        if p:
            blend(frame, self.img, p[0], p[1], opacity=1.0)

    def screen_rect(self):
        h, w = self.img.shape[:2]
        return self.cx - w / 2, self.cy - h / 2, w, h


def build_insert(spec: dict, images: dict, depth_of, cfg: dict, size, start: float, end: float, seed: int) -> Insert:
    f = spec["file"]
    cache = ROOT / ".cache" / "inserts"
    cache.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1(repr({k: spec.get(k) for k in ("file", "kind", "crop", "page", "caption", "depth")}).encode()).hexdigest()[:10]
    cpath = cache / f"insert-{key}.png"
    if cpath.exists():
        img = Image.open(cpath).convert("RGBA")
    else:
        depth = None
        if f in images:  # a generated frame
            src = Image.open(images[f]).convert("RGB")
            depth = depth_of(images[f]) if spec.get("depth", True) else None
        else:  # an archive file
            src = _source(spec, cache)
        if spec.get("crop") and f in images:
            x0, y0, x1, y1 = spec["crop"]
            src = src.crop((int(x0 * src.width), int(y0 * src.height), int(x1 * src.width), int(y1 * src.height)))
        kind = spec.get("kind", "cutout" if f in images else "photo")
        if kind == "cutout":
            img = cutout(src, depth, cfg, seed)
        elif kind == "clipping":
            img = clipping(src, cfg, seed, spec.get("caption"))
        else:
            img = _tape(photo(src, cfg, seed, spec.get("caption"), colour=str(f).startswith("stock-") or spec.get("colour", False)), seed)
        img.save(cpath)
    return Insert(spec, start, end, img, size, seed)
