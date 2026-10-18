"""Channel signature: a newspaper-clipping hand that draws a picture (or a red marker mark) on screen.

Line art comes from the picture itself (1950s ad style = strong black outlines), so no extra generations:
outlines are traced stroke by stroke in fast motion with the pencil tip on the current stroke, then the
colour sweeps in behind the hand, and the hand leaves the frame. The hand always enters from the nearest
side edge with the wrist outside the picture, so it covers as little as possible.
"""
from __future__ import annotations

import json
import math
from functools import lru_cache

import cv2
import numpy as np
from PIL import Image

from .config import ROOT

HAND_DIR = ROOT / "assets" / "hands"
HAND_HEIGHT = 0.62  # hand clipping height as a share of the frame height
LINES_SHARE = 0.72  # share of the draw time spent on outlines (rest = colour sweep)


def ease(p: float) -> float:
    p = min(1.0, max(0.0, p))
    return p * p * (3 - 2 * p)


@lru_cache(maxsize=8)
def _hand(kind: str, height: int, mirrored: bool) -> tuple[np.ndarray, tuple[int, int]]:
    meta = json.loads((HAND_DIR / "hand.json").read_text())
    img = Image.open(HAND_DIR / f"hand_{kind}.png").convert("RGBA")
    s = height / img.height
    img = img.resize((max(1, int(img.width * s)), height), Image.LANCZOS)
    tx, ty = meta["tip"][0] * s, meta["tip"][1] * s
    if mirrored:
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
        tx = img.width - 1 - tx
    return np.array(img), (int(tx), int(ty))


def paste_hand(frame: np.ndarray, kind: str, x: float, y: float, mirrored: bool) -> None:
    """Paste the hand so that its pencil tip sits at (x, y) on the frame."""
    from .text import blend
    H = min(frame.shape[0], frame.shape[1])  # Shorts: sized to the picture window, not the tall frame
    img, (tx, ty) = _hand(kind, int(H * HAND_HEIGHT), mirrored)
    blend(frame, img, int(x - tx), int(y - ty), opacity=1.0)


def hand_path(tip_at, t0: float, t1: float, t: float, W: int, H: int, mirrored: bool):
    """Tip position while the hand is in the frame: slides in before t0 from the side edge (wrist side),
    follows tip_at(t) between t0 and t1, slides out after t1. Returns None when off screen."""
    enter, leave = 0.28, 0.32
    off = (W * (-0.35 if mirrored else 1.35), H * 1.05)
    if t < t0 - enter or t > t1 + leave:
        return None
    if t < t0:
        a = ease((t - (t0 - enter)) / enter)
        x1, y1 = tip_at(t0)
        return off[0] + (x1 - off[0]) * a, off[1] + (y1 - off[1]) * a
    if t > t1:
        a = ease((t - t1) / leave)
        x1, y1 = tip_at(t1)
        return x1 + (off[0] - x1) * a, y1 + (off[1] - y1) * a
    x, y = tip_at(t)
    # tiny tremor so the hand feels alive
    return x + math.sin(t * 31.0) * H * 0.002, y + math.cos(t * 23.0) * H * 0.002


class LineDrawing:
    """Stroke plan for one picture (base pixels)."""

    def __init__(self, base: np.ndarray, paper_rgb):
        gray = cv2.cvtColor(base, cv2.COLOR_RGB2GRAY)
        self.ink = gray < 90
        ink8 = self.ink.astype(np.uint8)
        contours, _ = cv2.findContours(ink8, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
        min_len = max(24, int(min(base.shape[:2]) * 0.03))
        strokes = [c[::2, 0, :].astype(np.float32) for c in contours if len(c) >= min_len]
        strokes.sort(key=len, reverse=True)
        strokes = strokes[:400]
        # greedy nearest-neighbour order, starting from the longest outline (draws like a person would)
        ordered = []
        if strokes:
            left = strokes[1:]
            cur = strokes[0]
            ordered.append(cur)
            while left:
                end = cur[-1]
                starts = np.array([s[0] for s in left])
                j = int(np.argmin(((starts - end) ** 2).sum(1)))
                cur = left.pop(j)
                ordered.append(cur)
        self.strokes = ordered
        self.lengths = np.array([len(s) for s in ordered], dtype=np.int64)
        self.cum = np.concatenate([[0], np.cumsum(self.lengths)])
        self.total = int(self.cum[-1])
        self.thick = max(6, int(min(base.shape[:2]) * 0.012))
        self.base = base
        self.paper = np.array(paper_rgb, dtype=np.float32)
        self.reveal = np.zeros(base.shape[:2], np.uint8)
        self.done = 0
        H, W = base.shape[:2]
        yy, xx = np.mgrid[0:H, 0:W]
        self.diag = ((xx / W) * 0.6 + (yy / H) * 0.4).astype(np.float32)  # colour sweep coordinate 0..1

    def point(self, k: int) -> tuple[float, float]:
        if self.total == 0:
            H, W = self.base.shape[:2]
            return W / 2, H / 2
        k = min(max(k, 0), self.total - 1)
        i = int(np.searchsorted(self.cum, k, side="right") - 1)
        x, y = self.strokes[i][k - self.cum[i]]
        return float(x), float(y)

    def _reveal_to(self, k: int) -> None:
        if k < self.done:
            self.reveal[:] = 0
            self.done = 0
        i0 = int(np.searchsorted(self.cum, self.done, side="right") - 1)
        i1 = int(np.searchsorted(self.cum, k, side="right") - 1)
        for i in range(max(0, i0), min(len(self.strokes), i1 + 1)):
            a = max(0, self.done - self.cum[i])
            b = min(self.lengths[i], k - self.cum[i])
            if b > a:
                seg = self.strokes[i][max(0, a - 1):b].astype(np.int32).reshape(-1, 1, 2)
                cv2.polylines(self.reveal, [seg], False, 1, self.thick, cv2.LINE_8)
        self.done = k

    def tip(self, p: float) -> tuple[float, float]:
        """Pencil tip (base px) at drawing progress p — pure, safe to call for any time."""
        p = min(1.0, max(0.0, p))
        if p <= LINES_SHARE:
            return self.point(int(self.total * p / LINES_SHARE))
        pc = (p - LINES_SHARE) / (1 - LINES_SHARE)
        H, W = self.base.shape[:2]
        f = min(1.0, pc * 1.25)
        s = 0.5 + 0.5 * math.sin(pc * math.pi * 9)  # hatching back and forth along the colour front
        x = W * min(0.95, max(0.05, s * min(1.0, f / 0.6)))
        y = H * min(0.92, max(0.08, (f - 0.6 * x / W) / 0.4))
        return x, y

    def state(self, p: float) -> np.ndarray:
        """Picture at drawing progress p (0..1)."""
        if p >= 1.0:
            return self.base
        pl = min(1.0, max(0.0, p) / LINES_SHARE)
        self._reveal_to(int(self.total * pl))
        out = np.empty_like(self.base)
        out[:] = self.paper.astype(np.uint8)
        m = (self.reveal > 0) & self.ink
        out[m] = self.base[m]
        if p <= LINES_SHARE:
            return out
        pc = (p - LINES_SHARE) / (1 - LINES_SHARE)
        a = np.clip((pc * 1.25 - self.diag) / 0.22, 0, 1)[..., None]
        return (out * (1 - a) + self.base * a).astype(np.uint8)


def mark_pen(marks: list[dict], t: float, W: int, H: int):
    """Pencil tip (base px) of the mark being drawn at time t, with the hand's in/out timing."""
    from .shots import mark_strokes
    for i, m in enumerate(marks):
        if not m.get("hand"):
            continue
        at, dur = float(m.get("at", 0.6)), float(m.get("dur", 0.45))
        strokes = m.get("_strokes")
        if strokes is None:
            strokes = mark_strokes(m, W, H, seed=17 + i)
            m["_strokes"] = strokes
        pts = np.concatenate(strokes)

        def tip(tt, pts=pts, at=at, dur=dur):
            q = min(1.0, max(0.0, (tt - at) / max(dur, 1e-3)))
            x, y = pts[min(len(pts) - 1, int(q * (len(pts) - 1)))]
            return float(x), float(y)
        if at - 0.3 <= t <= at + dur + 0.35:
            return tip, at, at + dur
    return None
