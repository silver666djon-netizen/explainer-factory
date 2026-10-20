"""Code-drawn scenes for Case 002 (reusable): split screen, two receipts, basket infographic, draining battery.
All in the channel's print style, with the drawing / writing hands; no image generation needed."""
from __future__ import annotations

import math

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .config import hex_to_rgb, resolve_font
from .draw import COLOR_START, LINES_END, LineDrawing, hand_path, paste_hand
from .endscreen import Writing, _stamp
from .evidence import _aged_paper
from .shots import Shot, add_grain, cover, cover_geometry, ease
from .text import blend, font


def _pal(cfg):
    return {k: hex_to_rgb(v) for k, v in cfg["style"]["palette"].items()}


def _paper_bg(W, H, pal, seed=3, tone=1.0):
    base = np.full((H, W, 3), [int(c * tone) for c in pal["paper"]], np.uint8)
    out = add_grain(base, 0.035, seed).astype(np.float32)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    out *= (1 - 0.18 * np.clip(r - 0.5, 0, 1))[..., None]
    return np.clip(out, 0, 255).astype(np.uint8)


def _window(W, H):
    """Picture area: full frame for long videos, the square window under the title band for Shorts."""
    if H > W:
        y0 = int(H * 0.17)
        return 0, y0, W, W
    return 0, 0, W, H


def _push(img, z, cx=None, cy=None):
    H, W = img.shape[:2]
    M = cv2.getRotationMatrix2D((W / 2 if cx is None else cx, H / 2 if cy is None else cy), 0, z)
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


# ------------------------------------------------------------------------------------------------ split screen

class SplitShot(Shot):
    """Two pictures at the same moment: left | right (stacked in Shorts), a torn-paper divider and a clock badge."""

    def __init__(self, start, duration, left: Image.Image, right: Image.Image, spec: dict, cfg: dict, size, seed=0,
                 light_at=None, tap_at=None, stamp_at=0.25):
        super().__init__(start, duration)
        self.W, self.H = W, H = size
        pal = _pal(cfg)
        self.pal = pal
        self.light_at, self.tap_at, self.stamp_at = light_at, tap_at, stamp_at
        x0, y0, ww, wh = _window(W, H)
        self.win = (x0, y0, ww, wh)
        portrait = H > W
        fx = spec.get("focus", [0.55, 0.48])
        if portrait:
            pw, ph = ww, wh // 2
            a = cover(left, pw, ph, fx[0], 0.32)
            b = cover(right, pw, ph, fx[1], 0.32)
            board = np.concatenate([a, b], 0)
        else:
            pw, ph = ww // 2, wh
            a = cover(left, pw, ph, fx[0], 0.5)
            b = cover(right, ww - pw, ph, fx[1], 0.5)
            board = np.concatenate([a, b], 1)
        board = add_grain(board, 0.02, seed)
        # phone screens (quads in fractions of each source picture) -> board pixels, plus what may glow there
        self.screens = []
        for k, (img, fxk) in enumerate(((left, fx[0]), (right, fx[1]))):
            q = (spec.get("screens") or [None, None])[k]
            if not q:
                continue
            if portrait:
                gw, gh, ox, oy = pw, ph, 0, k * ph
                nw, nh, lft, top = cover_geometry(img.width, img.height, pw, ph, fxk, 0.32)
            else:
                gw, gh, ox, oy = (pw if k == 0 else ww - pw), ph, (0 if k == 0 else pw), 0
                nw, nh, lft, top = cover_geometry(img.width, img.height, gw, gh, fxk, 0.5)
            pts = np.array([(x * nw - lft + ox, y * nh - top + oy) for x, y in q["quad"]], np.float32)
            m = np.zeros(board.shape[:2], np.uint8)
            cv2.fillConvexPoly(m, pts.astype(np.int32), 1)
            m = cv2.erode(m, np.ones((5, 5), np.uint8))
            r_, g_, b_ = [board[..., c].astype(np.int16) for c in range(3)]
            lum = (r_ + g_ + b_) / 3
            skin = (r_ - b_ > 35) & (r_ > 120)
            sel = (lum < 70) if q.get("mode", "dark") == "dark" else ((lum > 110) & ~skin)
            glow = (m.astype(bool) & sel).astype(np.float32)
            glow = cv2.GaussianBlur(glow, (0, 0), 1.2)
            self.screens.append({"glow": glow, "c": pts.mean(0), "size": float(np.linalg.norm(pts[0] - pts[1]))})
        self.glow_col = np.array((236, 248, 226), np.float32)
        pil = Image.fromarray(board).convert("RGBA")
        d = ImageDraw.Draw(pil)
        rnd = np.random.default_rng(seed)
        cream = (247, 240, 222, 255)
        if portrait:  # horizontal torn strip
            ys = wh // 2
            pts = [(x, ys - 8 + rnd.uniform(-5, 5)) for x in np.linspace(0, ww, 40)] + \
                  [(x, ys + 8 + rnd.uniform(-5, 5)) for x in np.linspace(ww, 0, 40)]
        else:
            xs = ww // 2
            pts = [(xs - 9 + rnd.uniform(-6, 6), y) for y in np.linspace(0, wh, 40)] + \
                  [(xs + 9 + rnd.uniform(-6, 6), y) for y in np.linspace(wh, 0, 40)]
        d.polygon(pts, fill=cream)
        tf = font(resolve_font(cfg["fonts"].get("typewriter") or cfg["fonts"]["serif"]), int(min(ww, wh) * 0.034))
        for i, name in enumerate(spec.get("names", ["LARRY", "LINDA"])):
            if portrait:
                lx, ly = int(ww * 0.04), int(i * wh / 2 + wh * 0.035)
            else:
                lx, ly = int(i * ww / 2 + ww * 0.025), int(wh * 0.05)
            tw = tf.getlength(name)
            d.rectangle((lx - 8, ly - 6, lx + tw + 10, ly + tf.size + 8), fill=(250, 246, 236, 235), outline=pal["ink"] + (255,), width=2)
            d.text((lx, ly), name, font=tf, fill=pal["ink"] + (255,))
        self.board = np.array(pil.convert("RGB"))
        # clock badge on the seam
        r = int(min(ww, wh) * (0.11 if not portrait else 0.13))
        badge = Image.new("RGBA", (2 * r + 8, 2 * r + 8), (0, 0, 0, 0))
        bd = ImageDraw.Draw(badge)
        bd.ellipse((4, 4, 2 * r + 4, 2 * r + 4), fill=(250, 246, 236, 255), outline=pal["red"] + (255,), width=max(4, r // 10))
        hf = font(resolve_font(cfg["fonts"]["headline"]), int(r * 0.52))
        bd.text((r + 4, r + 4), spec.get("clock", "10:15"), font=hf, fill=pal["ink"] + (255,), anchor="mm")
        sub = spec.get("clock_sub", "SAME MINUTE")
        fs = int(r * 0.22)
        sf = font(resolve_font(cfg["fonts"]["body"]), fs)
        while sf.getlength(sub) > r * 1.25 and fs > 8:  # fit inside the circle at that height
            fs -= 1
            sf = font(resolve_font(cfg["fonts"]["body"]), fs)
        bd.text((r + 4, r + 4 + r * 0.45), sub, font=sf, fill=pal["red"] + (255,), anchor="mm")
        self.badge = np.array(badge)
        self.portrait = portrait
        self.bg = _paper_bg(W, H, pal, 5, 0.6) if portrait else None

    def _icon(self, size):
        """A tiny shopping-basket icon (app tile)."""
        s = max(16, int(size))
        im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        red, ink = self.pal["red"] + (255,), self.pal["ink"] + (255,)
        d.rounded_rectangle((0, 0, s - 1, s - 1), radius=s // 5, fill=(250, 246, 236, 255), outline=ink, width=max(2, s // 14))
        d.polygon([(s * 0.18, s * 0.42), (s * 0.82, s * 0.42), (s * 0.72, s * 0.82), (s * 0.28, s * 0.82)], fill=red, outline=ink)
        d.arc((s * 0.3, s * 0.18, s * 0.7, s * 0.62), 180, 360, fill=ink, width=max(2, s // 12))
        return np.array(im)

    def frame(self, t):
        x0, y0, ww, wh = self.win
        pic = self.board
        if self.screens and self.light_at is not None and t >= self.light_at:  # the phone screens light up
            q = min(1.0, (t - self.light_at) / 0.25)
            pulse = 0.85 + 0.15 * math.sin((t - self.light_at) * 5)
            pic = pic.astype(np.float32)
            for sc in self.screens:
                a = (sc["glow"] * q * pulse)[..., None]
                pic = pic * (1 - a) + self.glow_col * a
            pic = pic.astype(np.uint8)
            if self.tap_at is not None and t >= self.tap_at:  # a tap, and a basket pops on each screen
                pic = pic.copy()
                for sc in self.screens:
                    p2 = min(1.0, (t - self.tap_at) / 0.25)
                    sz = sc["size"] * 0.55 * (0.6 + 0.4 * ease(p2) + 0.12 * math.sin(p2 * math.pi))
                    ic = self._icon(sz)
                    cx, cy = sc["c"]
                    blend(pic, ic, int(cx - ic.shape[1] / 2), int(cy - ic.shape[0] / 2))
                    age = t - self.tap_at
                    if age < 0.5:  # tap ripple
                        rr = int(sc["size"] * (0.25 + age * 1.2))
                        cv2.circle(pic, (int(cx), int(cy)), rr, tuple(int(c) for c in self.pal["red"]), 2, cv2.LINE_AA)
        za = self.stamp_at if self.stamp_at is not None else 0.0
        z = 1.0 + 0.012 * min(1.0, t / max(0.5, za)) \
            + 0.03 * ease(max(0.0, t - za) / max(0.5, self.duration - za))  # a drift from the first frame, the 3% push from "Same minute."
        pic = _push(pic, z)
        b = self.badge
        p = min(1.0, max(0.0, (t - za) / 0.14))
        if p > 0:
            s = 1.6 - 0.6 * ease(p)
            bb = cv2.resize(b, (int(b.shape[1] * s), int(b.shape[0] * s)))
            cx, cy = (int(ww * 0.86), wh // 2) if self.portrait else (ww // 2, int(wh * 0.30))
            blend(pic, bb, cx - bb.shape[1] // 2, cy - bb.shape[0] // 2, opacity=min(1.0, p * 1.5))
        if self.bg is None:
            return pic
        out = self.bg.copy()
        out[y0:y0 + wh, x0:x0 + ww] = pic
        return out

    def sfx(self, start_abs):
        out = [(start_abs + (self.stamp_at or 0.25), "stamp"), (start_abs + (self.stamp_at or 0.25) + 0.01, "thud")]
        if self.light_at is not None:
            out.append((start_abs + self.light_at, "pop"))
        if self.tap_at is not None:
            out += [(start_abs + self.tap_at, "tap"), (start_abs + self.tap_at + 0.12, "tap")]
        return out


# ------------------------------------------------------------------------------------------------ receipts

def _receipt(cfg, w: int, name: str, store: str, when: str, items: list, total: str, seed: int):
    pal = _pal(cfg)
    tf = font(resolve_font(cfg["fonts"].get("typewriter") or cfg["fonts"]["serif"]), int(w * 0.052))
    bf = font(resolve_font(cfg["fonts"]["headline"]), int(w * 0.13))
    lh = int(tf.size * 1.45)
    h = int(w * 0.16) + lh * (len(items) + 7) + int(bf.size * 1.6)
    paper = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(paper)
    rnd = np.random.default_rng(seed)
    zig = int(w * 0.025)
    poly = [(0, 0), (w, 0), (w, h - zig)]
    for k, x in enumerate(np.linspace(w, 0, 24)):
        poly.append((x, h - (0 if k % 2 else zig)))
    d.polygon(poly, fill=(251, 248, 240, 255))
    ink = (52, 48, 44, 255)
    y = int(w * 0.07)
    for line in (store, when, f"CUSTOMER: {name}"):
        d.text((w / 2, y), line, font=tf, fill=ink, anchor="ma")
        y += lh
    y += int(lh * 0.3)
    d.line((w * 0.06, y, w * 0.94, y), fill=ink, width=2)
    y += int(lh * 0.5)
    for it, pr in items:
        d.text((w * 0.07, y), it, font=tf, fill=ink)
        d.text((w * 0.93, y), pr, font=tf, fill=ink, anchor="ra")
        y += lh
    y += int(lh * 0.3)
    d.line((w * 0.06, y, w * 0.94, y), fill=ink, width=2)
    y += int(lh * 0.6)
    d.text((w * 0.07, y + bf.size * 0.25), "TOTAL", font=tf, fill=ink)
    d.text((w * 0.93, y), total, font=bf, fill=ink, anchor="ra")
    tot_box = (w * 0.93 - bf.getlength(total), y, w * 0.93, y + bf.size * 1.15)
    arr = np.array(paper)
    # thermal print: slight fade and speckle
    noise = cv2.GaussianBlur(rnd.random(arr.shape[:2]).astype(np.float32), (0, 0), 0.8)
    dark = arr[..., :3].mean(2) < 150
    arr[..., :3] = np.where((dark & (noise > 0.66))[..., None], (arr[..., :3] * 0.6 + 100).astype(np.uint8), arr[..., :3])
    return arr, tot_box


class ReceiptsShot(Shot):
    """Two receipts drop onto the table one after the other; the marker circles both totals; a stamp lands."""

    def __init__(self, start, duration, spec: dict, cfg: dict, size, circle_at: float, stamp_at: float | None, seed=0):
        super().__init__(start, duration)
        self.W, self.H = W, H = size
        self.pal = pal = _pal(cfg)
        x0, y0, ww, wh = _window(W, H)
        self.win = (x0, y0, ww, wh)
        self.portrait = H > W
        table = np.full((wh, ww, 3), (214, 178, 128), np.uint8)
        rnd = np.random.default_rng(seed)
        for yy in range(0, wh, 7):
            table[yy:yy + 3] = np.clip(table[yy:yy + 3].astype(int) + int(rnd.integers(-7, 7)), 0, 255)
        self.table = add_grain(table, 0.04, seed)
        rw = int(ww * (0.40 if self.portrait else 0.25))
        self.receipts = []
        recs = spec["receipts"]
        for i, r in enumerate(recs):
            img, box = _receipt(cfg, rw, r["name"], spec.get("store", "SAME STORE"), spec.get("when", "10:15 AM"),
                                r["items"], r["total"], seed + i)
            k = min(1.0, wh * 0.92 / img.shape[0])
            if k < 1:
                img = cv2.resize(img, (int(img.shape[1] * k), int(img.shape[0] * k)), interpolation=cv2.INTER_AREA)
                box = tuple(v * k for v in box)
            ang = (-3.0, 2.5)[i % 2]
            pil = Image.fromarray(img).rotate(ang, resample=Image.BICUBIC, expand=True)
            cx = ww * (0.30 if i == 0 else 0.70) if not self.portrait else ww * (0.27 if i == 0 else 0.73)
            cy = wh * 0.5
            # total box centre in rotated-image coords
            bx, by = (box[0] + box[2]) / 2 - img.shape[1] / 2, (box[1] + box[3]) / 2 - img.shape[0] / 2
            a = math.radians(-ang)
            rx = bx * math.cos(a) - by * math.sin(a) + pil.width / 2
            ry = bx * math.sin(a) + by * math.cos(a) + pil.height / 2
            self.receipts.append({"img": np.array(pil), "cx": cx, "cy": cy, "tot": (cx - pil.width / 2 + rx, cy - pil.height / 2 + ry),
                                  "tw": box[2] - box[0], "th": box[3] - box[1], "t0": (-0.22 if not self.portrait else -0.4) + 0.25 * i})  # falling on the cut (Shorts: first one already down)
        self.circle_at = circle_at
        self.stamp_at = stamp_at
        self.stamp = _stamp(spec.get("stamp", "Real totals"), cfg, int(ww * (0.42 if self.portrait else 0.14)), pal["red"], -8, seed + 4) \
            if stamp_at is not None else None
        self.red = tuple(int(c) for c in pal["red"])
        self.bg = _paper_bg(W, H, pal, 5, 0.6) if self.portrait else None

    def _ellipse(self, r, q):
        (tx, ty), tw, th = r["tot"], r["tw"], r["th"]
        n = 80
        a0 = -2.4
        ang = np.linspace(a0, a0 + 2 * math.pi * 1.08 * q, max(2, int(n * q)))
        return np.stack([tx + tw * 0.62 * np.cos(ang), ty + th * 0.85 * np.sin(ang)], 1)

    def frame(self, t):
        x0, y0, ww, wh = self.win
        pic = self.table.copy()
        hand = None
        for i, r in enumerate(self.receipts):
            p = (t - r["t0"]) / 0.35
            if p <= 0:
                continue
            e = min(1.0, ease(min(1.0, p)) + 0.05 * math.sin(min(1.0, p) * math.pi))
            img = r["img"]
            y = int(r["cy"] - img.shape[0] / 2 - (1 - e) * wh * 1.1)
            x = int(r["cx"] - img.shape[1] / 2)
            sh = np.zeros_like(img)
            sh[..., 3] = (img[..., 3] * 0.5).astype(np.uint8)
            blend(pic, cv2.GaussianBlur(sh, (0, 0), 9), x + 8, y + 12)
            blend(pic, img, x, y)
        for i, r in enumerate(self.receipts):
            c0 = self.circle_at + 0.45 * i
            q = (t - c0) / 0.4
            if q > 0:
                pts = self._ellipse(r, min(1.0, q))
                cv2.polylines(pic, [pts.astype(np.int32).reshape(-1, 1, 2)], False, self.red, max(5, wh // 130), cv2.LINE_AA)
                if q < 1.0:
                    hand = (x0 + pts[-1][0], y0 + pts[-1][1])
        if self.stamp is not None:  # REAL TOTALS: pressed on by the stamp hand
            from .draw import stamp_press
            stamp_press(pic, self.stamp, ww * 0.5, wh * (0.62 if not self.portrait else 0.12), t, self.stamp_at)
        z = 1.0 + 0.04 * ease(t / max(self.duration, 1e-6))
        pic = _push(pic, z)
        if self.bg is not None:
            out = self.bg.copy()
            out[y0:y0 + wh, x0:x0 + ww] = pic
        else:
            out = pic
        if hand:
            hx = (hand[0] - ww / 2) * z + ww / 2
            hy = (hand[1] - y0 - wh / 2) * z + wh / 2 + y0
            paste_hand(out, "marker_under", hx, hy, False)
        return out

    def sfx(self, start_abs):
        out = []
        for r in self.receipts:
            out += [(start_abs + max(0.0, r["t0"]), "printer"), (start_abs + r["t0"] + 0.3, "paper")]
        out += [(start_abs + self.circle_at, "marker"), (start_abs + self.circle_at + 0.45, "marker")]
        if self.stamp_at is not None:
            out.append((start_abs + self.stamp_at, "kachunk"))
        return out


def receipt_items(total: float, factor_seed: int, base: list[tuple[str, float]], scale: float = 1.0):
    """Items with prices that add up exactly to `total` (reconstruction of a basket)."""
    rnd = np.random.default_rng(factor_seed)
    raw = np.array([p * scale * rnd.uniform(0.97, 1.03) for _n, p in base])
    raw = raw / raw.sum() * total
    cents = np.round(raw * 100).astype(int)
    cents[-1] += int(round(total * 100)) - cents.sum()
    return [(n, f"{c / 100:.2f}") for (n, _p), c in zip(base, cents)]


# ------------------------------------------------------------------------------------------------ baskets

class BasketsShot(Shot):
    """1950s infographic: two copies of the same basket, heights proportional to the totals (from a zero
    baseline), drawn by the pencil hand and coloured by the marker hand; totals and the gap written by hand."""

    def __init__(self, start, duration, spec: dict, subject: Image.Image, cfg: dict, size, draw_at=0.2,
                 write_at=(2.0, 3.0), gap_at=None, seed=0):
        super().__init__(start, duration)
        self.W, self.H = W, H = size
        self.pal = pal = _pal(cfg)
        x0, y0, ww, wh = _window(W, H)
        self.win = (x0, y0, ww, wh)
        portrait = H > W
        self.portrait = portrait
        bg = _paper_bg(ww, wh, pal, 9)
        pil = Image.fromarray(bg).convert("RGBA")
        d = ImageDraw.Draw(pil)
        head = resolve_font(cfg["fonts"]["headline"])
        tf = font(head, int(wh * 0.07))
        d.text((ww / 2, wh * 0.075), spec.get("title", "Same basket").upper(), font=tf, fill=pal["ink"] + (255,), anchor="mm")
        sf = font(resolve_font(cfg["fonts"].get("typewriter") or cfg["fonts"]["serif"]), int(wh * 0.032))
        d.text((ww / 2, wh * 0.14), spec.get("sub", ""), font=sf, fill=pal["ink"] + (230,), anchor="mm")
        floor = int(wh * (0.70 if not portrait else 0.80))  # labels stay above the subtitles
        d.line((ww * 0.12, floor, ww * 0.88, floor), fill=pal["ink"] + (255,), width=4)
        base = np.array(pil.convert("RGB"))
        # basket cut from its backdrop
        src = np.array(subject.convert("RGB"))
        hh, ww0 = src.shape[:2]
        src = src[int(hh * 0.07): int(hh * 0.93), int(ww0 * 0.05): int(ww0 * 0.95)]
        back = np.median(np.concatenate([src[:8].reshape(-1, 3), src[-8:].reshape(-1, 3)]), axis=0)
        diff = np.abs(src.astype(np.float32) - back).max(2)
        m8 = (diff > 26).astype(np.uint8)
        m8 = cv2.morphologyEx(m8, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
        cnts, _ = cv2.findContours(m8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        m8 = np.zeros_like(m8)
        for c in cnts:
            if cv2.contourArea(c) > 0.002 * m8.size:
                cv2.drawContours(m8, [c], -1, 1, -1)
        m8[diff < 14] = 0
        ys, xs = np.where(m8 > 0)
        crop, mcrop = src[ys.min():ys.max() + 1, xs.min():xs.max() + 1], m8[ys.min():ys.max() + 1, xs.min():xs.max() + 1].astype(np.float32)
        values = spec.get("values", [114.34, 123.93])
        vmax = max(values)
        hmax = wh * (0.42 if not portrait else 0.44)
        xs_c = [ww * 0.33, ww * 0.67]
        self.tops = []
        mask = np.zeros((wh, ww), np.float32)
        for i, v in enumerate(values):
            h = hmax * v / vmax  # honest: height proportional to the total, from a zero baseline
            k = h / crop.shape[0]
            cw, ch = max(1, int(crop.shape[1] * k)), max(1, int(h))
            if cw > ww * 0.32:
                k2 = ww * 0.32 / cw
                cw, ch = int(cw * k2), int(ch * k2)
            im = cv2.resize(crop, (cw, ch), interpolation=cv2.INTER_AREA)
            mk = cv2.resize(mcrop, (cw, ch))
            px, py = int(xs_c[i] - cw / 2), floor - ch
            reg = base[py:py + ch, px:px + cw].astype(np.float32)
            base[py:py + ch, px:px + cw] = (reg * (1 - mk[..., None]) + im * mk[..., None]).astype(np.uint8)
            mask[py:py + ch, px:px + cw] = np.maximum(mask[py:py + ch, px:px + cw], mk)
            self.tops.append((xs_c[i], py))
        self.base = base
        self.mask = mask
        self.ld = LineDrawing(base, tuple(int(c) for c in pal["paper"]), mask)
        self.blank = self.ld.blank
        lab = font(head, int(wh * 0.04))
        self.labels = []
        for i, l in enumerate(spec.get("labels", ["Cheapest basket", "Most expensive"])):
            img = Image.new("RGBA", (int(ww * 0.34), int(wh * 0.07)), (0, 0, 0, 0))
            ImageDraw.Draw(img).text((img.width / 2, img.height / 2), l.upper(), font=lab, fill=pal["ink"] + (255,), anchor="mm")
            self.labels.append((np.array(img), int(xs_c[i] - img.width / 2), floor + int(wh * 0.025)))
        mf = font(resolve_font(cfg["fonts"]["marker"]), int(wh * 0.075))
        self.totals = [Writing(f"${v:,.2f}", mf, pal["red"] if i == len(values) - 1 else pal["ink"]) for i, v in enumerate(values)]
        gf = font(resolve_font(cfg["fonts"]["marker"]), int(wh * 0.06))
        self.gap = Writing(spec.get("gap", f"+${values[-1] - values[0]:.2f}"), gf, pal["red"])
        self.draw_at, self.ddur = draw_at, float(spec.get("draw_dur", 2.2))
        self.write_at = list(write_at)
        self.gap_at = gap_at
        self.red = tuple(int(c) for c in pal["red"])
        self.bg = _paper_bg(W, H, pal, 5, 0.6) if portrait else None

    def frame(self, t):
        x0, y0, ww, wh = self.win
        q = (t - self.draw_at) / self.ddur
        pic = self.blank.copy() if q <= 0 else self.ld.state(min(1.0, q)).copy()
        if q <= 0:  # keep title + floor visible before the drawing starts
            m = self.mask[..., None] > 0.01
            pic = np.where(m, self.blank, self.base)
        hand = None
        if 0 < q < 1.08:
            kind = "pencil" if q < (LINES_END + COLOR_START) / 2 else "colour"
            a, b = (self.draw_at, self.draw_at + self.ddur * LINES_END) if kind == "pencil" else \
                   (self.draw_at + self.ddur * COLOR_START, self.draw_at + self.ddur)
            tip = hand_path(lambda tt: self.ld.tip((tt - self.draw_at) / self.ddur), a, b, t, ww, wh, False)
            if tip:
                hand = (kind, tip[0], tip[1])
        if q > 0.6:
            for img, lx, ly in self.labels:
                blend(pic, img, lx, ly, opacity=min(1.0, (q - 0.6) / 0.3))
        for i, wr in enumerate(self.totals):
            p = (t - self.write_at[i]) / 0.8
            if p > 0:
                tx, ty = self.tops[i]
                bx, by = int(tx - wr.w / 2), int(ty - wr.h - wh * 0.02)
                blend(pic, wr.at(p), bx, by)
                if p < 1.25:
                    tip = hand_path(lambda tt, wr=wr, bx=bx, by=by, w0=self.write_at[i]: (bx + wr.tip((tt - w0) / 0.8)[0], by + wr.tip((tt - w0) / 0.8)[1]),
                                    self.write_at[i], self.write_at[i] + 0.8, t, ww, wh, False, from_below=True)
                    if tip:
                        hand = ("ink_under", tip[0], tip[1])
        if self.gap_at is not None and t >= self.gap_at:
            p = min(1.0, (t - self.gap_at) / 0.6)
            (xa, ya), (xb, yb) = self.tops
            xr = int(xb + ww * 0.13)
            # the cheaper basket's height carried across (dashed), then a red bracket shows the gap
            x_end = int(xa + (xr - xa) * min(1.0, p * 2))
            for xs in range(int(xa - ww * 0.06), x_end, 22):
                cv2.line(pic, (xs, ya), (min(x_end, xs + 12), ya), self.pal["ink"], 2, cv2.LINE_AA)
            if p > 0.5:
                q2 = min(1.0, (p - 0.5) / 0.3)
                yb2 = int(ya + (yb - ya) * q2)
                tk = max(4, wh // 160)
                cv2.line(pic, (xr - 12, ya), (xr, ya), self.red, tk, cv2.LINE_AA)
                cv2.line(pic, (xr, ya), (xr, yb2), self.red, tk, cv2.LINE_AA)
                if q2 >= 1:
                    cv2.line(pic, (xr - 12, yb), (xr, yb), self.red, tk, cv2.LINE_AA)
            if p >= 0.8:
                g = self.gap
                gx = int(xr + ww * 0.012)
                if gx + g.w > ww * 0.98:  # Shorts: above the bracket instead
                    blend(pic, g.at((p - 0.8) / 0.2), int(ww * 0.98 - g.w), int(yb - g.h - wh * 0.01))
                else:
                    blend(pic, g.at((p - 0.8) / 0.2), gx, int((ya + yb) / 2 - g.h / 2))
        z = 1.0 + 0.035 * ease(t / max(self.duration, 1e-6))
        pic = _push(pic, z)
        if self.bg is not None:
            out = self.bg.copy()
            out[y0:y0 + wh, x0:x0 + ww] = pic
        else:
            out = pic
        if hand:
            kind, hx, hy = hand
            hx = (hx - ww / 2) * z + ww / 2
            hy = (hy - wh / 2) * z + wh / 2 + y0
            paste_hand(out, kind, hx, hy, False)
        return out

    def sfx(self, start_abs):
        out = []
        k = 0.0
        while k < self.ddur * LINES_END:
            out.append((start_abs + self.draw_at + k, "pencil"))
            k += 0.17
        k = self.ddur * COLOR_START
        while k < self.ddur:
            out.append((start_abs + self.draw_at + k, "marker"))
            k += 0.24
        for a in self.write_at:
            out += [(start_abs + a, "marker"), (start_abs + a + 0.4, "marker")]
        if self.gap_at is not None:
            out.append((start_abs + self.gap_at, "scribble"))
        return out


# ------------------------------------------------------------------------------------------------ battery

class BatteryShot(Shot):
    """The phone's battery drains (the marker hand rides its edge) while the fare tag beside it stays the same."""

    def __init__(self, start, duration, spec: dict, cfg: dict, size, drain_at=0.4, seed=0):
        super().__init__(start, duration)
        self.W, self.H = W, H = size
        self.cfg = cfg
        self.pal = pal = _pal(cfg)
        x0, y0, ww, wh = _window(W, H)
        self.win = (x0, y0, ww, wh)
        self.portrait = H > W
        bg = _paper_bg(ww, wh, pal, 11)
        pil = Image.fromarray(bg).convert("RGBA")
        d = ImageDraw.Draw(pil)
        ink = pal["ink"] + (255,)
        # phone
        ph_h = int(wh * 0.74)
        ph_w = int(ph_h * 0.52)
        self.px, self.py = int(ww * (0.30 if not self.portrait else 0.28)) - ph_w // 2, int(wh * 0.12)
        px, py = self.px, self.py
        d.rounded_rectangle((px, py, px + ph_w, py + ph_h), radius=int(ph_w * 0.14), fill=(244, 236, 214, 255), outline=ink, width=8)
        d.rounded_rectangle((px + ph_w * 0.08, py + ph_h * 0.08, px + ph_w * 0.92, py + ph_h * 0.88), radius=int(ph_w * 0.05),
                            fill=(38, 64, 52, 255), outline=ink, width=4)
        d.ellipse((px + ph_w * 0.45, py + ph_h * 0.91, px + ph_w * 0.55, py + ph_h * 0.97), outline=ink, width=4)
        # battery outline on the screen (horizontal)
        bw, bh = int(ph_w * 0.64), int(ph_w * 0.30)
        self.bx, self.by = int(px + ph_w * 0.18), int(py + ph_h * 0.36)
        d.rounded_rectangle((self.bx, self.by, self.bx + bw, self.by + bh), radius=8, outline=(240, 232, 210, 255), width=7)
        d.rectangle((self.bx + bw, self.by + bh * 0.3, self.bx + bw + bw * 0.07, self.by + bh * 0.7), fill=(240, 232, 210, 255))
        self.bw, self.bh = bw, bh
        # fare tag
        tw, th = int(ww * (0.30 if not self.portrait else 0.40)), int(wh * 0.22)
        self.tx, self.ty = int(ww * (0.68 if not self.portrait else 0.73)) - tw // 2, int(wh * 0.30)
        tx, ty = self.tx, self.ty
        c = int(th * 0.25)
        poly = [(tx + c, ty), (tx + tw, ty), (tx + tw, ty + th), (tx + c, ty + th), (tx, ty + th - c), (tx, ty + c)]
        d.polygon(poly, fill=(250, 244, 228, 255), outline=pal["red"] + (255,))
        d.line(poly + [poly[0]], fill=pal["red"] + (255,), width=6)
        d.ellipse((tx + c * 0.45 - 9, ty + th / 2 - 9, tx + c * 0.45 + 9, ty + th / 2 + 9), outline=ink, width=3)
        lf = font(resolve_font(cfg["fonts"].get("typewriter") or cfg["fonts"]["serif"]), int(th * 0.16))
        d.text((tx + tw * 0.58, ty + th * 0.22), spec.get("tag_label", "RIDE FARE"), font=lf, fill=ink, anchor="mm")
        pf = font(resolve_font(cfg["fonts"]["headline"]), int(th * 0.40))
        d.text((tx + tw * 0.58, ty + th * 0.62), spec.get("fare", "$24.80"), font=pf, fill=ink, anchor="mm")
        self.base = np.array(pil.convert("RGB"))
        self.lv0, self.lv1 = float(spec.get("from", 0.82)), float(spec.get("to", 0.03))
        self.drain_at, self.ddur = drain_at, float(spec.get("dur", 3.2))
        mf = font(resolve_font(cfg["fonts"]["marker"]), int(wh * 0.07))
        self.note = Writing(spec.get("note", "same fare"), mf, pal["red"])
        self.note_at = self.drain_at + self.ddur + 0.2
        self.pf = font(resolve_font(cfg["fonts"]["headline"]), int(bh * 0.55))
        self.bg = _paper_bg(W, H, pal, 5, 0.6) if self.portrait else None

    def frame(self, t):
        x0, y0, ww, wh = self.win
        pic = self.base.copy()
        q = min(1.0, max(0.0, (t - self.drain_at) / self.ddur))
        lv = self.lv0 + (self.lv1 - self.lv0) * ease(q)
        col = (90, 190, 120) if lv > 0.5 else ((232, 181, 58) if lv > 0.2 else (226, 70, 50))
        pad = 12
        x1 = int(self.bx + pad + (self.bw - 2 * pad) * lv)
        cv2.rectangle(pic, (self.bx + pad, self.by + pad), (max(self.bx + pad + 2, x1), self.by + self.bh - pad), col, -1)
        txt = f"{max(1, int(round(lv * 100)))}%"
        img = Image.fromarray(pic)
        ImageDraw.Draw(img).text((self.bx + self.bw / 2, self.by + self.bh + self.bh * 0.55), txt, font=self.pf, fill=(240, 232, 210), anchor="mm")
        pic = np.array(img)
        hand = None
        pad_ = pad

        def edge(tt):
            qq = min(1.0, max(0.0, (tt - self.drain_at) / self.ddur))
            l2 = self.lv0 + (self.lv1 - self.lv0) * ease(qq)
            return self.bx + pad_ + (self.bw - 2 * pad_) * l2, self.by + self.bh - pad_
        tip = hand_path(edge, self.drain_at, self.drain_at + self.ddur, t, ww, wh, False, from_below=True)
        if tip:
            hand = ("marker_under", tip[0], tip[1])
        nx, ny = int(self.tx + 10), int(self.ty + wh * 0.25)
        p = (t - self.note_at) / 0.8
        if p > 0:
            blend(pic, self.note.at(p), nx, ny)
        tip = hand_path(lambda tt: (nx + self.note.tip((tt - self.note_at) / 0.8)[0], ny + self.note.tip((tt - self.note_at) / 0.8)[1]),
                        self.note_at, self.note_at + 0.8, t, ww, wh, False, from_below=True)
        if tip:
            hand = ("ink_under", tip[0], tip[1])
        z = 1.0 + 0.04 * ease(t / max(self.duration, 1e-6))
        pic = _push(pic, z)
        if self.bg is not None:
            out = self.bg.copy()
            out[y0:y0 + wh, x0:x0 + ww] = pic
        else:
            out = pic
        if hand:
            kind, hx, hy = hand
            hx = (hx - ww / 2) * z + ww / 2
            hy = (hy - wh / 2) * z + wh / 2 + y0
            paste_hand(out, kind, hx, hy, False)
        return out

    def sfx(self, start_abs):
        out = [(start_abs + self.drain_at + k * 0.5, "tick") for k in range(int(self.ddur / 0.5))]
        out += [(start_abs + self.note_at, "marker"), (start_abs + self.note_at + 0.4, "marker")]
        return out
