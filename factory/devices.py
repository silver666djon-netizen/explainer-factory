"""Running devices of the case-file style:

* Ledger — Larry's tab: a small index card pinned in the top-right corner for the whole story. At each
  loss moment the ink hand writes the next line (losses in red), so the card tells the money story on its own.
* HouseEdgeShot — 1950s infographic on green felt: two chip stacks drawn by the hands, hand-written labels.
* ExhibitShot — wraps a live-action clip as evidence: film grain, vignette, a paper-photo border with a
  typed EVIDENCE line, and a red EXHIBIT tag slapped on by the hand.
"""
from __future__ import annotations

import math

import cv2
import numpy as np
from PIL import Image, ImageDraw

from .config import hex_to_rgb, resolve_font
from .draw import COLOR_START, LINES_END, LineDrawing, hand_path, paste_hand
from .endscreen import Writing
from .evidence import _aged_paper, desk, evidence_tag, tape_strip
from .shots import Shot, ease
from .text import blend, fit_font, font


def _pal(cfg):
    return {k: hex_to_rgb(v) for k, v in cfg["style"]["palette"].items()}


def _typew(cfg):
    return resolve_font(cfg["fonts"].get("typewriter") or cfg["fonts"]["serif"])


# ---------------------------------------------------------------------------------------------- ledger

class Ledger:
    """rows: [{"label": "CASH IN", "amount": "$500", "loss": False, "at": abs_time, "end": abs_time?}]
    The card appears with the first row; every later row is handwritten at its time (0.7 s)."""

    WRITE = 0.7

    def __init__(self, rows: list[dict], cfg: dict, size, title: str = "LARRY'S TAB", hide: list | None = None):
        self.W, self.H = W, H = size
        self.rows = sorted(rows, key=lambda r: r["at"])
        self.pal = pal = _pal(cfg)
        self.hide = hide or []  # [(t0, t1)] spans where the card steps aside (full-frame cards, titles)
        portrait = H > W
        cw = int(W * (0.40 if portrait else 0.20))
        self.row_h = rh = int(cw * 0.105)
        head_h = int(rh * 1.45)
        ch = head_h + rh * len(self.rows) + int(rh * 0.5)
        self.cw, self.ch = cw, ch
        paper = _aged_paper(cw, ch, 31)
        card = Image.fromarray(paper).convert("RGBA")
        d = ImageDraw.Draw(card)
        tf = font(_typew(cfg), int(rh * 0.52))
        d.text((int(cw * 0.06), int(rh * 0.36)), title, font=tf, fill=pal["ink"])
        d.line((0, head_h - 3, cw, head_h - 3), fill=pal["red"] + (255,), width=3)
        for k in range(len(self.rows) + 1):  # ledger ruling
            y = head_h + k * rh
            d.line((int(cw * 0.04), y + rh - 4, int(cw * 0.96), y + rh - 4), fill=(150, 170, 190, 160), width=1)
        d.line((int(cw * 0.60), head_h, int(cw * 0.60), ch - 6), fill=(200, 120, 110, 150), width=1)
        lf = font(_typew(cfg), int(rh * 0.44))
        mf = font(resolve_font(cfg["fonts"]["marker"]), int(rh * 0.70))
        self.labels, self.amounts = [], []
        for k, r in enumerate(self.rows):
            y = head_h + k * rh
            lab = Image.new("RGBA", (int(cw * 0.56), rh), (0, 0, 0, 0))
            ImageDraw.Draw(lab).text((int(cw * 0.06), int(rh * 0.30)), r["label"], font=lf, fill=pal["ink"] + (255,))
            self.labels.append((np.array(lab), y))
            col = pal["red"] if r.get("loss") else pal["ink"]
            self.amounts.append((Writing(r["amount"], mf, col), y))
        self.card = np.array(card.convert("RGB"))
        tape = np.array(tape_strip(int(cw * 0.30), int(rh * 0.55), 5).rotate(-4, expand=True))
        self.tape = tape
        self.x = int(W * (0.565 if portrait else 0.765))
        self.y = int(H * (0.035 if not portrait else 0.03))
        self.angle = 1.5

    def visible(self, t: float) -> bool:
        return bool(self.rows) and t >= self.rows[0]["at"] - 0.3 and not any(a <= t <= b for a, b in self.hide)

    def draw(self, frame: np.ndarray, t: float) -> None:
        if not self.visible(t):
            return
        img = self.card.copy()
        hand = None
        for k, r in enumerate(self.rows):
            if t < r["at"]:
                break
            lab, y = self.labels[k]
            blend(img, lab, 0, y)
            wr, y = self.amounts[k]
            p = (t - r["at"] - 0.15) / self.WRITE
            if p > 0:
                ax = int(self.cw * 0.62)
                blend(img, wr.at(p), ax, y - int(self.row_h * 0.12))
                if p < 1.3:
                    hand = (ax, y - int(self.row_h * 0.12), wr, r["at"] + 0.15)
        # appear: drop in on the first row
        a = min(1.0, (t - self.rows[0]["at"] + 0.3) / 0.3)
        dy = int((1 - ease(a)) * -self.ch * 0.4)
        sh = np.zeros(img.shape[:2] + (4,), np.uint8)
        sh[..., 3] = 115
        blend(frame, cv2.GaussianBlur(sh, (0, 0), 8), self.x + 6, self.y + dy + 9)
        blend(frame, np.dstack([img, np.full(img.shape[:2], 255, np.uint8)]), self.x, self.y + dy)
        blend(frame, self.tape, self.x + self.cw // 2 - self.tape.shape[1] // 2, self.y + dy - self.tape.shape[0] // 3)
        if hand:
            ax, ay, wr, t0 = hand
            tip = hand_path(lambda q: (self.x + ax + wr.tip((q - t0) / self.WRITE)[0], self.y + ay + wr.tip((q - t0) / self.WRITE)[1]),
                            t0, t0 + self.WRITE, t, self.W, self.H, False, from_below=True)
            if tip:
                paste_hand(frame, "ink_under", tip[0], tip[1], False, scale=0.72)

    def sfx(self) -> list[tuple[float, str]]:
        out = [(self.rows[0]["at"] - 0.3, "paper")] if self.rows else []
        for r in self.rows:
            out += [(r["at"] + 0.15, "marker"), (r["at"] + 0.5, "marker")]
            if r.get("loss"):
                out.append((r["at"] + 0.9, "cash"))
        return out


# ---------------------------------------------------------------------------------------------- house edge

def _felt(W, H, pal, seed=8):
    base = np.array(pal["green"], np.float32) * 0.92
    rnd = np.random.default_rng(seed)
    fib = cv2.GaussianBlur(rnd.standard_normal((H, W)).astype(np.float32), (0, 0), 0.8) * 7
    blot = cv2.resize(cv2.GaussianBlur(rnd.standard_normal((H // 30 + 2, W // 30 + 2)).astype(np.float32), (0, 0), 1.5), (W, H)) * 6
    img = base[None, None, :] + (fib + blot)[..., None]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    img *= (1 - 0.32 * np.clip(r - 0.3, 0, 1) ** 1.3)[..., None]
    return np.clip(img, 0, 255).astype(np.uint8)


def chip_stack(n: int, w: int, color, pal, seed: int, thick: int | None = None) -> Image.Image:
    """1950s print-style stack of n chips (side view), black ink outlines, white edge inserts."""
    t = thick or max(6, int(w * 0.13))   # chip thickness
    eh = int(w * 0.30)          # ellipse height of a chip face
    H = n * t + eh + 8
    img = Image.new("RGBA", (w + 8, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    ink = pal["ink"] + (255,)
    col = tuple(color) + (255,)
    dark = tuple(int(c * 0.72) for c in color) + (255,)
    rnd = np.random.default_rng(seed)
    for k in range(n):
        yb = H - 4 - eh // 2 - k * t  # centre of this chip's bottom ellipse
        ox = int(rnd.uniform(-w * 0.03, w * 0.03))  # hand-stacked, not perfect
        x0, x1 = 4 + ox, 4 + w + ox
        d.ellipse((x0, yb - eh // 2, x1, yb + eh // 2), fill=dark, outline=ink, width=3)
        d.rectangle((x0, yb - t, x1, yb), fill=dark)
        d.line((x0, yb - t, x0, yb), fill=ink, width=3)
        d.line((x1, yb - t, x1, yb), fill=ink, width=3)
        for f in (0.14, 0.38, 0.62, 0.86):  # white edge inserts
            xi = x0 + (x1 - x0) * f
            d.rectangle((xi - w * 0.04, yb - t * 0.85, xi + w * 0.04, yb - t * 0.15 + eh * 0.05 * math.sin(f * math.pi)), fill=(250, 244, 230, 255))
        d.ellipse((x0, yb - t - eh // 2, x1, yb - t + eh // 2), fill=col, outline=ink, width=3)
    # inlay on the top chip
    ytop = H - 4 - eh // 2 - (n - 1) * t - t
    cx = 4 + w // 2
    d.ellipse((cx - w * 0.30, ytop - eh * 0.30, cx + w * 0.30, ytop + eh * 0.30), fill=(250, 244, 230, 255), outline=ink, width=2)
    return img


class HouseEdgeShot(Shot):
    """spec: {"title": "House edge", "sub": "kept from every $100 bet",
              "bars": [{"name": "American wheel", "note": "0 and 00", "value": 5.26, "color": "red"},
                       {"name": "European wheel", "note": "single 0", "value": 2.70, "color": "ink"}],
              "per_chip": 0.25, "draw_at": [s, s], "write_at": [s, s]}"""

    def __init__(self, start, duration, spec: dict, cfg: dict, size, lead_in: float = 0.0, seed: int = 0):
        super().__init__(start, duration)
        self.W, self.H = W, H = size
        self.pal = pal = _pal(cfg)
        BW, BH = int(W * 1.06), int(H * 1.06)
        self.BW, self.BH = BW, BH
        felt = _felt(BW, BH, pal)
        img = Image.fromarray(felt).convert("RGBA")
        d = ImageDraw.Draw(img)
        # printed table lines (like a betting layout), faint
        cream = (238, 230, 205)
        d.rounded_rectangle((int(BW * 0.06), int(BH * 0.20), int(BW * 0.94), int(BH * 0.80)), radius=int(BH * 0.08),
                            outline=cream + (90,), width=4)
        head = resolve_font(cfg["fonts"]["headline"])
        tf, tl = fit_font(spec.get("title", "House edge").upper(), head, int(W * 0.6), int(H * 0.12), start=int(H * 0.11))
        off_x, off_y = (BW - W) // 2, (BH - H) // 2
        d.text((BW // 2, off_y + int(H * 0.085)), " ".join(tl), font=tf, fill=cream + (255,), anchor="mm")
        sf = font(_typew(cfg), int(H * 0.034))
        d.text((BW // 2, off_y + int(H * 0.165)), spec.get("sub", "what the house keeps from every $100 bet"), font=sf, fill=cream + (230,), anchor="mm")
        bars = spec.get("bars") or []
        per = float(spec.get("per_chip", 0.5))
        colors = {"red": pal["red"], "ink": (52, 52, 58), "green": pal["green"], "accent": pal["accent"]}
        self.layers = []  # (LineDrawing over the felt for this stack, bbox)
        base = np.array(img.convert("RGB"))
        self.labels = []
        cw = int(W * 0.13)
        floor = off_y + int(H * 0.72)
        xs = [off_x + int(W * 0.34), off_x + int(W * 0.66)] if len(bars) == 2 else [off_x + int(W * (i + 1) / (len(bars) + 1)) for i in range(len(bars))]
        nf = font(head, int(H * 0.048))
        notef = font(_typew(cfg), int(H * 0.03))
        vf = font(resolve_font(cfg["fonts"]["marker"]), int(H * 0.085))
        masks = []
        n_max = max(max(1, int(round(float(b["value"]) / per))) for b in bars) if bars else 1
        thick = max(8, min(int(cw * 0.15), int((H * 0.36 - cw * 0.30) / n_max)))
        for i, b in enumerate(bars):
            n = max(1, int(round(float(b["value"]) / per)))
            st = chip_stack(n, cw, colors.get(b.get("color", "red"), pal["red"]), pal, seed + i, thick)
            x = xs[i] - st.width // 2
            y = floor - st.height
            a = np.array(st)
            al = a[..., 3:4].astype(np.float32) / 255
            reg = base[y:y + st.height, x:x + st.width].astype(np.float32)
            base[y:y + st.height, x:x + st.width] = (reg * (1 - al) + a[..., :3] * al).astype(np.uint8)
            m = np.zeros(base.shape[:2], np.float32)
            m[y:y + st.height, x:x + st.width] = al[..., 0]
            masks.append(m)
            # name (display font) printed on the felt under the stack
            nimg = Image.new("RGBA", (int(W * 0.30), int(H * 0.13)), (0, 0, 0, 0))
            nd = ImageDraw.Draw(nimg)
            nd.text((nimg.width // 2, int(H * 0.03)), b["name"].upper(), font=nf, fill=cream + (255,), anchor="mm")
            if b.get("note"):
                nd.text((nimg.width // 2, int(H * 0.085)), f"({b['note']})", font=notef, fill=cream + (220,), anchor="mm")
            self.labels.append((np.array(nimg), xs[i] - nimg.width // 2 - off_x, floor + int(H * 0.025) - off_y))
            # value: handwritten above the stack
            wr = Writing(f"{float(b['value']):.2f}%", vf, (250, 244, 228) if b.get("color") != "red" else (255, 214, 92))
            self.labels_v = getattr(self, "labels_v", []) + [(wr, xs[i] - wr.w // 2, y - wr.h - int(H * 0.01))]
        self.base = base
        self.draws = []
        for i, m in enumerate(masks):  # each stack drawn on its own (the felt stays as is)
            only = base.copy()
            for j, m2 in enumerate(masks):
                if j != i:  # other stacks shown as they are at that moment: handled at compose time
                    pass
            self.draws.append(LineDrawing(base, tuple(int(c) for c in np.array(pal["green"]) * 0.92), m))
        self.masks = masks
        self.felt = felt
        da = spec.get("draw_at") or [0.3, 2.6]
        wa = spec.get("write_at") or [da[0] + 2.0, da[1] + 2.0]
        self.draw_at = [float(x) + lead_in for x in da]
        self.write_at = [float(x) + lead_in for x in wa]
        self.ddur = float(spec.get("draw_dur", 1.8))

    def _board(self, t):
        out = self.felt.copy()
        # titles/lines (everything that is not a stack) come from the base where no mask is
        anym = np.clip(sum(self.masks), 0, 1)[..., None]
        out = (self.base * (1 - anym) + out * anym).astype(np.uint8)
        hand = None
        for i, ld in enumerate(self.draws):
            q = (t - self.draw_at[i]) / self.ddur
            if q <= 0:
                continue
            pic = ld.state(min(1.0, q))
            m = self.masks[i][..., None]
            out = (out * (1 - m) + pic * m).astype(np.uint8)
            if q < 1.08:
                kind = "pencil" if q < (LINES_END + COLOR_START) / 2 else "colour"
                t0, t1 = (self.draw_at[i], self.draw_at[i] + self.ddur * LINES_END) if kind == "pencil" else \
                         (self.draw_at[i] + self.ddur * COLOR_START, self.draw_at[i] + self.ddur)
                hand = (kind, ld, self.draw_at[i], t0, t1)
        return out, hand

    def frame(self, t: float) -> np.ndarray:
        W, H = self.W, self.H
        board, hand = self._board(t)
        off_x, off_y = (self.BW - W) // 2, (self.BH - H) // 2
        z = 1 + 0.035 * ease(t / max(self.duration, 1e-6))
        M = cv2.getRotationMatrix2D((self.BW / 2, self.BH / 2), 0, z)
        M[0, 2] -= off_x
        M[1, 2] -= off_y
        out = cv2.warpAffine(board, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

        def scr(x, y):
            return M[0, 0] * x + M[0, 1] * y + M[0, 2], M[1, 0] * x + M[1, 1] * y + M[1, 2]
        for i, (img, lx, ly) in enumerate(self.labels):
            if t >= self.draw_at[i] + self.ddur * 0.5:
                x, y = scr(lx + off_x, ly + off_y)
                blend(out, img, int(x), int(y))
        whand = None
        for i, (wr, vx, vy) in enumerate(getattr(self, "labels_v", [])):
            p = (t - self.write_at[i]) / 0.8
            if p > 0:
                x, y = scr(vx, vy)
                blend(out, wr.at(p), int(x), int(y))
                if p < 1.3:
                    whand = (wr, x, y, self.write_at[i])
        if whand:
            wr, x, y, t0 = whand
            tip = hand_path(lambda q: (x + wr.tip((q - t0) / 0.8)[0], y + wr.tip((q - t0) / 0.8)[1]), t0, t0 + 0.8, t, W, H, False, from_below=True)
            if tip:
                paste_hand(out, "ink_under", tip[0], tip[1], False)
        elif hand:
            kind, ld, a0, t0, t1 = hand
            tip = hand_path(lambda q: scr(*ld.tip((q - a0) / self.ddur)), t0, t1, t, W, H, False)
            if tip:
                paste_hand(out, kind, tip[0], tip[1], False)
        return out

    def sfx(self, start_abs: float) -> list[tuple[float, str]]:
        out = []
        for a in self.draw_at:
            k = 0.0
            while k < self.ddur * LINES_END:
                out.append((start_abs + a + k, "pencil"))
                k += 0.16
            out.append((start_abs + a + self.ddur * 0.9, "chips"))
        for a in self.write_at:
            out += [(start_abs + a, "marker"), (start_abs + a + 0.4, "marker")]
        return out


# ---------------------------------------------------------------------------------------------- exhibit

def exhibit_frame(rgb: np.ndarray, W: int, H: int, cfg: dict, t: float, seed: int, label: str, tag: str,
                  tag_p: float = 1.0) -> np.ndarray:
    """One frame of a live-action clip presented as evidence on the desk."""
    pal = _pal(cfg)
    out = desk(W, H, pal, 6)
    pw, ph = int(W * 0.80), int(H * 0.70)
    # grade: a little warmer and softer, grain that changes every frame, vignette
    v = cv2.resize(rgb, (pw, ph), interpolation=cv2.INTER_AREA).astype(np.float32)
    g = v.mean(2, keepdims=True)
    v = v * 0.78 + g * 0.22
    v = v * np.array([1.04, 1.0, 0.92], np.float32) + 6
    rnd = np.random.default_rng(int(t * 24) + seed)
    v += cv2.GaussianBlur(rnd.standard_normal((ph, pw)).astype(np.float32), (0, 0), 0.7)[..., None] * 9
    yy, xx = np.mgrid[0:ph, 0:pw].astype(np.float32)
    r = np.sqrt(((xx - pw / 2) / (pw / 2)) ** 2 + ((yy - ph / 2) / (ph / 2)) ** 2)
    v *= (1 - 0.38 * np.clip(r - 0.45, 0, 1) ** 1.2)[..., None]
    v = np.clip(v, 0, 255).astype(np.uint8)
    # paper-photo border with a typed evidence line
    b = int(H * 0.022)
    bb = int(H * 0.075)
    pr = np.full((ph + b + bb, pw + 2 * b, 3), (246, 240, 226), np.uint8)
    pr = np.clip(pr.astype(np.int16) + (cv2.GaussianBlur(np.random.default_rng(seed).standard_normal(pr.shape[:2]).astype(np.float32), (0, 0), 0.8) * 3).astype(np.int16)[..., None], 0, 255).astype(np.uint8)
    pr[b:b + ph, b:b + pw] = v
    pil = Image.fromarray(pr)
    d = ImageDraw.Draw(pil)
    tf = font(_typew(cfg), int(bb * 0.42))
    d.text((b + int(W * 0.01), b + ph + int(bb * 0.24)), label.upper(), font=tf, fill=pal["ink"])
    pr = np.array(pil.convert("RGBA").rotate(-1.2, resample=Image.BICUBIC, expand=True))
    x, y = (W - pr.shape[1]) // 2, int(H * 0.035)
    sh = np.zeros_like(pr)
    sh[..., 3] = (pr[..., 3] * 0.5).astype(np.uint8)
    blend(out, cv2.GaussianBlur(sh, (0, 0), 12), x + 10, y + 16)
    blend(out, pr, x, y)
    # two strips of tape and the red EXHIBIT tag slapped on the corner
    for fx in (0.12, 0.80):
        tp = np.array(tape_strip(int(W * 0.09), int(H * 0.035), seed + int(fx * 10)).rotate(-6 if fx < 0.5 else 5, expand=True))
        blend(out, tp, x + int(pr.shape[1] * fx), y - tp.shape[0] // 3)
    if tag_p > 0:
        tg = evidence_tag(cfg, tag, int(W * 0.20), seed, word="EXHIBIT")
        s = 1.6 - 0.6 * ease(min(1.0, tag_p))
        tg = tg.rotate(9, resample=Image.BICUBIC, expand=True)
        tg = tg.resize((int(tg.width * s), int(tg.height * s)), Image.LANCZOS)
        ta = np.array(tg)
        blend(out, ta, x + pr.shape[1] - int(ta.shape[1] * 0.80), y + pr.shape[0] - int(ta.shape[0] * 0.95), opacity=min(1.0, tag_p * 2))
    return out
