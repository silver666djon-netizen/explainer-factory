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
HAND_ROT = 18.0  # deg clockwise about the pen tip (R37: hand right of and below the tip)
HAND_ROT_RING = 32.0  # rings: turned further (qc.hand_over_ink: <= 5 % of a ring covered)
LINES_END = 0.5    # outlines by the pencil hand: 0 .. LINES_END of the draw time
COLOR_START = 0.6  # colour by the marker hand: COLOR_START .. 1 (the hands swap in between)


def ease(p: float) -> float:
    p = min(1.0, max(0.0, p))
    return p * p * (3 - 2 * p)


@lru_cache(maxsize=8)
def _hand(kind: str, height: int, mirrored: bool) -> tuple[np.ndarray, tuple[int, int]]:
    mirrored = False  # R37 (Klot r86): the narrator's hand is never mirrored
    rot = HAND_ROT
    if "@" in kind:  # "red@32": the hand turned further for a ring (see mark_pen)
        kind, r_ = kind.split("@", 1)
        rot = float(r_)
    meta = json.loads((HAND_DIR / "hand.json").read_text())
    meta = meta.get(kind, meta.get("pencil", meta))  # per-hand tip position
    img = Image.open(HAND_DIR / f"hand_{kind}.png").convert("RGBA")
    s = height / float(meta.get("ref", img.height))  # extended sleeves: scale by the original hand size
    img = img.resize((max(1, int(img.width * s)), max(1, int(img.height * s))), Image.LANCZOS)
    tx, ty = meta["tip"][0] * s, meta["tip"][1] * s
    if rot and kind not in ("stamp", "stamp_cuff"):  # R37: turned clockwise about the tip, so the fingers sit right
        # of and below the pen tip, clear of the letters just written (padded first: nothing is clipped)
        pad = int(max(img.size))
        big = Image.new("RGBA", (img.width + 2 * pad, img.height + 2 * pad), (0, 0, 0, 0))
        big.paste(img, (pad, pad))
        cx, cy = tx + pad, ty + pad
        big = big.rotate(-rot, resample=Image.BICUBIC, center=(cx, cy))
        bb = big.getbbox() or (0, 0, big.width, big.height)
        img = big.crop(bb)
        tx, ty = cx - bb[0], cy - bb[1]
    if mirrored:
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
        tx = img.width - 1 - tx
    return np.array(img), (int(tx), int(ty))


# Rule (Ep.4 on): no narrator hand wears Larry's yellow check sleeve. With NO_SLEEVE the sleeved hands are swapped for
# the same hand cut at its white cuff (assets/hands/hand_<kind>_cuff.png). Set per episode: config "hands": {"sleeve": false}.
NO_SLEEVE = False
SLEEVED = ("ink", "colour", "marker", "ink_under", "marker_under", "stamp")


def hand_kind(kind: str) -> str:
    if "@" in kind:
        base, r_ = kind.split("@", 1)
        return f"{hand_kind(base)}@{r_}"
    return f"{kind}_cuff" if NO_SLEEVE and kind in SLEEVED else kind


def set_hand_style(cfg: dict) -> None:
    global NO_SLEEVE
    NO_SLEEVE = not bool((cfg.get("hands") or {}).get("sleeve", True))


def paste_hand(frame: np.ndarray, kind: str, x: float, y: float, mirrored: bool, scale: float = 1.0) -> None:
    """Paste the hand so that its pencil tip sits at (x, y) on the frame (scale < 1 for small props)."""
    from .text import blend
    kind = hand_kind(kind)
    H = min(frame.shape[0], frame.shape[1])  # Shorts: sized to the picture window, not the tall frame
    img, (tx, ty) = _hand(kind, int(H * HAND_HEIGHT * scale), mirrored)
    blend(frame, img, int(x - tx), int(y - ty), opacity=1.0)


def hand_path(tip_at, t0: float, t1: float, t: float, W: int, H: int, mirrored: bool, from_below: bool = False):
    """Tip position while the hand is in the frame: slides in before t0 from the side edge (wrist side),
    follows tip_at(t) between t0 and t1, slides out after t1. Returns None when off screen.
    from_below: for the hands held under the line (arm hanging down) — they rise straight up from the
    bottom edge under the spot they write on, instead of crossing the frame diagonally."""
    enter, leave = 0.28, 0.32
    off = (W * 1.35, H * 1.05)  # R37: the right hand enters and leaves on the right
    if from_below:
        sx, _ = tip_at(t0 if t < t0 else t1)
        off = (sx + W * 0.06, H * 1.25)
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


def subject_mask(base: np.ndarray, depth: np.ndarray | None, box=(0.0, 0.0, 1.0, 1.0), mode: str = "auto") -> np.ndarray:
    """0..1 mask of the thing to draw: a hero/object, never the location.
    depth  - nearest layer inside the box (characters, props standing in a scene);
    shape  - filled ink outlines inside the box (icons, small details on a plain background)."""
    H, W = base.shape[:2]
    x0, y0, x1, y1 = int(box[0] * W), int(box[1] * H), int(box[2] * W), int(box[3] * H)
    m = np.zeros((H, W), np.uint8)
    if mode == "auto":
        mode = "depth" if depth is not None else "shape"
    if mode == "depth" and depth is not None:
        d = (np.clip(depth, 0, 1) * 255).astype(np.uint8)
        sub = d[y0:y1, x0:x1]
        t1, _ = cv2.threshold(sub, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        hi = sub[sub > t1]
        t2 = cv2.threshold(hi.reshape(-1, 1), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[0] if hi.size > 50 else t1
        m[y0:y1, x0:x1] = sub > (t1 + t2) / 2
        # the near layer often includes the counter/table the hero stands at; keep only the part that is
        # bounded by the picture's own ink outlines (the character), not the flat furniture around it
        gray = cv2.cvtColor(base, cv2.COLOR_RGB2GRAY)
        ink = cv2.dilate((gray < 100).astype(np.uint8), np.ones((5, 5), np.uint8))
        cs, _ = cv2.findContours(ink, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        shape = np.zeros_like(m)
        cv2.drawContours(shape, cs, -1, 1, thickness=cv2.FILLED)
        tight = m & shape
        if tight.sum() > 0.35 * m.sum():
            m = tight
    else:
        # "shape": everything that is not the flat paper backdrop inside the box (colour or ink), holes closed
        H8 = base.astype(np.int16)
        ring = np.ones((H, W), bool)
        ring[y0:y1, x0:x1] = False
        if ring.sum() < 50:
            ring = np.zeros((H, W), bool); ring[:8] = ring[-8:] = True; ring[:, :8] = ring[:, -8:] = True
        paper = np.median(base[ring].reshape(-1, 3), axis=0).astype(np.int16)
        diff = np.abs(H8 - paper[None, None, :]).max(axis=2)
        m[y0:y1, x0:x1] = (diff[y0:y1, x0:x1] > 28)
        k0 = max(3, int(min(H, W) * 0.006)) | 1
        # thin ink outlines must survive (they close light shapes like a chrome head or white gloves):
        # bridge small gaps, fill every closed outline, then remove specks
        m = cv2.dilate(m, np.ones((k0, k0), np.uint8))
        cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        m = np.zeros_like(m)
        cv2.drawContours(m, [c for c in cs if cv2.contourArea(c) > (H * W) * 0.0004], -1, 1, thickness=cv2.FILLED)
        m = cv2.erode(m, np.ones((k0, k0), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    if n > 1:
        big = st[1:, cv2.CC_STAT_AREA].max()
        m = np.isin(lab, [i for i in range(1, n) if st[i, cv2.CC_STAT_AREA] > 0.08 * big]).astype(np.uint8)
    k = max(5, int(min(H, W) * 0.012)) | 1
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k * 3, k * 3)))
    m = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    return cv2.GaussianBlur(m.astype(np.float32), (0, 0), k / 3)


class LineDrawing:
    """Stroke plan for one picture (base pixels). With a mask only that subject is drawn into the scene."""

    def __init__(self, base: np.ndarray, paper_rgb, mask: np.ndarray | None = None):
        H, W = base.shape[:2]
        gray = cv2.cvtColor(base, cv2.COLOR_RGB2GRAY)
        self.mask = mask if mask is not None else np.ones((H, W), np.float32)
        inside = self.mask > 0.5
        self.ink = (gray < 90) & inside
        ink8 = self.ink.astype(np.uint8)
        contours, _ = cv2.findContours(ink8, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
        min_len = max(24, int(min(H, W) * 0.03))
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
        self.thick = max(6, int(min(H, W) * 0.012))
        self.base = base
        self.paper = np.array(paper_rgb, dtype=np.float32)
        self.reveal = np.zeros((H, W), np.uint8)
        self.done = 0
        ys, xs = np.where(inside) if inside.any() else (np.array([0, H - 1]), np.array([0, W - 1]))
        self.bbox = (float(xs.min()), float(ys.min()), float(xs.max()), float(ys.max()))
        bx0, by0, bx1, by1 = self.bbox
        yy, xx = np.mgrid[0:H, 0:W]
        u = np.clip((xx - bx0) / max(1.0, bx1 - bx0), 0, 1)
        v = np.clip((yy - by0) / max(1.0, by1 - by0), 0, 1)
        self.diag = (u * 0.6 + v * 0.4).astype(np.float32)  # colour sweep coordinate 0..1 over the subject
        # empty state: the scene without the subject. Low frequencies (lighting, vignette) are continued from
        # the surrounding paper by repeated normalised blurring; the paper grain is cloned from a clean patch
        # of the same picture, so the filled area is indistinguishable from untouched paper.
        hole = (self.mask > 0.3).astype(np.uint8)
        if hole.any() and hole.mean() < 0.98:
            k = max(3, int(min(H, W) * 0.012)) | 1
            # also remove the soft drop shadow / halo the generator paints around a subject on plain paper
            gray = cv2.cvtColor(base, cv2.COLOR_RGB2GRAY).astype(np.float32)
            paper_lvl = float(np.median(gray[hole == 0])) if (hole == 0).any() else 235.0
            halo = ((gray < paper_lvl - 10) & (cv2.dilate(hole, np.ones((k * 4 | 1, k * 4 | 1), np.uint8)) > 0)).astype(np.uint8)
            hole = np.maximum(hole, halo)
            hole_d = cv2.dilate(hole, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k * 2 + 1, k * 2 + 1)))
            known = (1 - hole_d).astype(np.float32)
            basef = base.astype(np.float32)
            sig = max(6.0, min(H, W) * 0.02)
            # normalised convolution: smooth colour field from KNOWN pixels only (the subject never leaks in)
            wsum = cv2.GaussianBlur(known, (0, 0), sig)
            csum = cv2.GaussianBlur(basef * known[..., None], (0, 0), sig)
            fill_low = csum / np.maximum(wsum, 1e-4)[..., None]
            cover = wsum > 0.2
            for _ in range(8):  # grow inwards until the whole hole is covered
                wsum = cv2.GaussianBlur(wsum, (0, 0), sig * 1.6)
                csum = cv2.GaussianBlur(csum, (0, 0), sig * 1.6)
                nxt = csum / np.maximum(wsum, 1e-4)[..., None]
                fill_low = np.where(cover[..., None], fill_low, nxt)
                cover = cover | (wsum > 0.2)
            fill_low = cv2.GaussianBlur(fill_low, (0, 0), sig)
            # keep the fill a paper tone: nothing darker/lighter than the backdrop's own gentle variation
            med = np.median(basef[known > 0.5].reshape(-1, 3), axis=0) if (known > 0.5).any() else self.paper
            fill_low = np.clip(fill_low, med - 10, med + 10)
            low = cv2.GaussianBlur(basef, (0, 0), sig)
            # grain: synthetic noise with the backdrop's own grain strength (copying real pixels can drag
            # bits of the picture along, so no cloning)
            hp = basef - cv2.GaussianBlur(basef, (0, 0), 2.0)
            g_std = float(np.std(hp[known > 0.5])) if (known > 0.5).any() else 3.0
            rng = np.random.default_rng(7)
            noise = cv2.GaussianBlur(rng.standard_normal((H, W)).astype(np.float32), (0, 0), 0.8)
            noise *= g_std / max(1e-3, float(noise.std()))
            tile = np.repeat(noise[..., None], 3, axis=2)
            fill = fill_low + tile * 0.9
            a = cv2.GaussianBlur(hole_d.astype(np.float32), (0, 0), k * 0.8)[..., None]
            self.blank = (basef * (1 - a) + np.clip(fill, 0, 255) * a).astype(np.uint8)
        else:
            self.blank = np.full_like(base, 0) + self.paper.astype(np.uint8)

    def point(self, k: int) -> tuple[float, float]:
        if self.total == 0:
            bx0, by0, bx1, by1 = self.bbox
            return (bx0 + bx1) / 2, (by0 + by1) / 2
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

    def _hatch_plan(self) -> None:
        """Zig-zag marker strokes over the subject (only where the mask is), like colouring in."""
        H, W = self.base.shape[:2]
        bx0, by0, bx1, by1 = self.bbox
        step = max(10, int(min(H, W) * 0.035))
        self.cthick = int(step * 1.6)
        pts, row = [], 0
        y = by0
        while y <= by1:
            xs = np.arange(bx0, bx1 + 1, max(3, step // 3), dtype=np.float32)
            if row % 2:
                xs = xs[::-1]
            slant = (xs - bx0) * 0.25  # slight diagonal, like a real hand
            for x, dy in zip(xs, slant):
                yy = int(min(H - 1, max(0, y + dy - (bx1 - bx0) * 0.12)))
                if self.mask[yy, int(min(W - 1, x))] > 0.5:
                    pts.append((float(x), float(yy)))
            y += step
            row += 1
        if not pts:
            pts = [((bx0 + bx1) / 2, (by0 + by1) / 2)]
        self.hatch = np.array(pts, np.float32)
        self.paint = np.zeros((H, W), np.uint8)
        self.painted = 0

    def _paint_to(self, k: int) -> None:
        if k < self.painted:
            self.paint[:] = 0
            self.painted = 0
        if k > self.painted:
            seg = self.hatch[max(0, self.painted - 1):k]
            # split where the path jumps (gaps in the mask) so no stroke crosses empty space
            jump = np.where(np.hypot(*np.diff(seg, axis=0).T) > self.cthick)[0] + 1
            for part in np.split(seg, jump):
                if len(part) >= 1:
                    cv2.polylines(self.paint, [part.astype(np.int32).reshape(-1, 1, 2)], False, 1, self.cthick, cv2.LINE_AA)
            self.painted = k

    def tip(self, p: float) -> tuple[float, float]:
        """Tool tip (base px) at drawing progress p — pencil on outlines, then marker on the colour strokes."""
        p = min(1.0, max(0.0, p))
        if p <= LINES_END or not hasattr(self, "hatch"):
            return self.point(int(self.total * min(1.0, p / LINES_END)))
        q = min(1.0, max(0.0, (p - COLOR_START) / (1 - COLOR_START)))
        x, y = self.hatch[min(len(self.hatch) - 1, int(q * (len(self.hatch) - 1)))]
        return float(x), float(y)

    def state(self, p: float) -> np.ndarray:
        """Picture at drawing progress p (0..1): outlines appear stroke by stroke, then colour stroke by stroke."""
        if p >= 1.0:
            return self.base
        if not hasattr(self, "hatch"):
            self._hatch_plan()
        self._reveal_to(int(self.total * min(1.0, max(0.0, p) / LINES_END)))
        out = self.blank.copy()
        m = (self.reveal > 0) & self.ink
        out[m] = self.base[m]
        if p <= COLOR_START:
            return out
        q = (p - COLOR_START) / (1 - COLOR_START)
        self._paint_to(int(q * len(self.hatch)))
        a = (self.paint.astype(np.float32) * self.mask)[..., None]
        if q > 0.92:  # last touch: fill the tiny gaps the strokes missed
            a = np.maximum(a, ((q - 0.92) / 0.08) * self.mask[..., None])
        return (out * (1 - a) + self.base * a).astype(np.uint8)


def mark_pen(marks: list[dict], t: float, W: int, H: int):
    """Pencil tip (base px) of the mark being drawn at time t, with the hand's in/out timing.
    A mark with "chain": True is written by the same hand straight after the previous hand mark: the hand stays in
    the frame and travels from the end of one to the start of the next (three prices in a row, say)."""
    from .shots import mark_strokes
    groups = []
    order = sorted(range(len(marks)), key=lambda j: float(marks[j].get("at", 0.6)))  # chains follow the time order
    for i in order:
        m = marks[i]
        if not m.get("hand") or m.get("type") in ("led", "stamp", "dot"):
            continue
        at, dur = float(m.get("at", 0.6)), float(m.get("dur", 0.45))
        strokes = m.get("_strokes")
        if strokes is None or m.get("_strokes_WH") != (W, H):
            strokes = mark_strokes(m, W, H, seed=17 + i)
            if m.get("type") != "write" or m.get("_lay") is not None:
                m["_strokes"], m["_strokes_WH"] = strokes, (W, H)
        from .shots import pen_path
        seg = (at, dur, pen_path(strokes, W, H), m)
        if m.get("chain") and groups:
            groups[-1].append(seg)
        else:
            groups.append([seg])
    for g in groups:
        g = sorted(g, key=lambda x: x[0])
        a0, a1 = g[0][0], g[-1][0] + g[-1][1]
        if not (a0 - 0.3 <= t <= a1 + 0.35):
            continue

        def tip(tt, g=g):
            for k, (at, dur, pts, _m) in enumerate(g):
                if tt <= at + dur or k == len(g) - 1:
                    if tt >= at or k == 0:
                        q = min(1.0, max(0.0, (tt - at) / max(dur, 1e-3)))
                        x, y = pts[min(len(pts) - 1, int(q * (len(pts) - 1)))]
                        return float(x), float(y)
                    pa, pd, pp, _ = g[k - 1]  # travelling between two marks
                    u = min(1.0, max(0.0, (tt - pa - pd) / max(0.05, at - pa - pd)))
                    u = u * u * (3 - 2 * u)
                    (x0, y0), (x1, y1) = pp[-1], pts[0]
                    return float(x0 + (x1 - x0) * u), float(y0 + (y1 - y0) * u - math.sin(u * math.pi) * H * 0.03)
            return float(g[-1][2][-1][0]), float(g[-1][2][-1][1])
        kind = pen_for(g[0][3])
        cur = next((m_ for at_, dur_, _p, m_ in g if at_ <= t <= at_ + dur_ + 0.35), g[-1][3])
        if cur.get("type") == "circle":
            kind = f"{kind}@{HAND_ROT_RING:g}"  # R37: rings - the hand turned further, off the ring it has drawn
        if g[0][3].get("hand_scale"):  # a smaller hand for a note written near the frame edge
            kind = (kind, float(g[0][3]["hand_scale"]))
        return tip, a0, a1, kind
    return None


def pen_for(mark: dict) -> str:
    """Ink colour = pen colour: red marks -> red pencil hand, black ink -> graphite pencil, paper-white -> white paint pen."""
    col = str(mark.get("color", "red"))
    if mark.get("type", "circle") != "write":
        col = str(mark.get("color", "red"))
    return {"ink": "pencil", "paper": "white", "#FFFFFF": "white", "#ffffff": "white"}.get(col, "red")


# ---------------------------------------------------------------- rubber-stamp hand (small stamps on paper)
STAMP_IN, STAMP_HOLD, STAMP_OUT = 0.35, 0.13, 0.32  # enter from above, press 3-4 frames, lift and leave
STAMP_RUBBER_W = 360 / 1024  # rubber width / hand ref height in hand_stamp.png


def stamp_window(t_press: float) -> tuple[float, float]:
    return t_press - STAMP_IN, t_press + STAMP_HOLD + STAMP_OUT


STAMP_LOG: list | None = None  # QC: set to [] to record every press (centre, size, target plate)


def stamp_press(frame: np.ndarray, impression: np.ndarray, cx: float, cy: float, t: float, t_press: float,
                plate: tuple | None = None) -> None:
    """A small stamp applied by hand: the hand enters from above holding a rubber stamp, presses at t_press
    (the impression appears on that frame, exactly where the rubber is), holds 3-4 frames, lifts, leaves.
    Rule: stamps on paper are never applied by a pen hand and never drop in."""
    from .shots import ease
    from .text import blend
    H, W = frame.shape[:2]
    ih, iw = impression.shape[:2]
    if STAMP_LOG is not None and abs(t - t_press) < 0.13:
        STAMP_LOG.append({"t_press": t_press, "c": (cx / W, cy / H), "plate": None if plate is None else
                          (plate[0] / W, plate[1] / H, plate[2] / W, plate[3] / H)})
    if t >= t_press:
        blend(frame, impression, int(cx - iw / 2), int(cy - ih / 2))
    w0, w1 = stamp_window(t_press)
    if not (w0 <= t <= w1):
        return
    height = int(max(iw, ih) * 1.12 / STAMP_RUBBER_W)
    img, (tx, ty) = _hand(hand_kind("stamp"), height, False)
    if t < t_press:
        lift = (1 - ease((t - w0) / STAMP_IN)) * (cy + H * 0.15)
    elif t <= t_press + STAMP_HOLD:
        lift = 0.0
    else:
        lift = ease((t - t_press - STAMP_HOLD) / STAMP_OUT) * (cy + H * 0.15)
    bottom = cy + ih / 2 - lift  # rubber bottom sits on the impression when pressed
    blend(frame, img, int(cx - tx), int(bottom - ty), opacity=1.0)
