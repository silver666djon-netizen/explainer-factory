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
SHORT_VIEW_TOP = 0.17  # Shorts: top of the square picture window (title band above, captions below)
SHORT_MIN_BAND = 0.5  # R38 (Klot r86): the Shorts picture band is at least half the frame height (960 of 1920 px)


def ease(p: float) -> float:
    p = min(1.0, max(0.0, p))
    return p * p * (3 - 2 * p)


def cover_geometry(src_w: int, src_h: int, w: int, h: int, fx: float = 0.5, fy: float = 0.5):
    """Scaled size and crop offset of a 'cover' fit; (fx, fy) = picture point to keep in the middle."""
    scale = max(w / src_w, h / src_h)
    nw, nh = math.ceil(src_w * scale), math.ceil(src_h * scale)
    left = int(min(max(fx * nw - w / 2, 0), nw - w))
    top = int(min(max(fy * nh - h / 2, 0), nh - h))
    return nw, nh, left, top


def cover(img: Image.Image, w: int, h: int, fx: float = 0.5, fy: float = 0.5) -> np.ndarray:
    src_w, src_h = img.size
    nw, nh, left, top = cover_geometry(src_w, src_h, w, h, fx, fy)
    resized = img.resize((nw, nh), Image.LANCZOS)
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


def archival_print(img: Image.Image, cfg: dict, w: int, h: int, seed: int = 0, fit: float = 0.80, dy: float = 0.0) -> Image.Image:
    """Real archive photo -> warm halftone print with a white border, laid on paper, slightly rotated."""
    pal = {k: hex_to_rgb(v) for k, v in cfg["style"]["palette"].items()}
    gray = ImageOps.autocontrast(img.convert("L"), cutoff=1)
    # coarse halftone feel: posterize lightly + soft blur, then tint ink/paper
    gray = gray.filter(ImageFilter.UnsharpMask(radius=2, percent=80))
    tinted = ImageOps.colorize(gray, black=pal["ink"], white=tuple(min(255, c + 8) for c in pal["paper"]))
    # fit inside the canvas with a border
    max_w, max_h = int(w * 0.78), int(h * fit)
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
    x, y = (w - printed.width) // 2, (h - printed.height) // 2 + int(h * dy)
    canvas.paste(shadow, (x + border // 2, y + border), shadow)
    canvas.paste(printed, (x, y), printed)
    canvas.info["bottom"] = y + printed.height
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


def pen_travel(strokes: list, W: int, H: int) -> list[int]:
    """Points the lifted pen spends travelling between two strokes (none for a short hop, e.g. dash to dash)."""
    out = []
    for a, b in zip(strokes, strokes[1:]):
        d = float(np.hypot(*(np.asarray(b[0]) - np.asarray(a[-1]))))
        out.append(int(min(24, d / (min(W, H) * 0.01))) if d > min(W, H) * 0.03 else 0)
    return out


def pen_path(strokes: list, W: int, H: int) -> np.ndarray:
    """The tip's whole path: the strokes, with the lifted travel between them (same point count as draw_marks)."""
    tr = pen_travel(strokes, W, H)
    parts = [np.asarray(strokes[0], np.float64)]
    for k, s in enumerate(strokes[1:]):
        if tr[k]:
            a, b = np.asarray(strokes[k][-1], np.float64), np.asarray(s[0], np.float64)
            u = np.linspace(0, 1, tr[k] + 2)[1:-1, None]
            arc = a + (b - a) * u
            arc[:, 1] -= np.sin(u[:, 0] * math.pi) * min(W, H) * 0.02  # a little lift
            parts.append(arc)
        parts.append(np.asarray(s, np.float64))
    return np.concatenate(parts)


def mark_strokes(mark: dict, W: int, H: int, seed: int) -> list[np.ndarray]:
    """Hand-drawn stroke polylines (pixel coords) for one mark. Coordinates are 0..1 of the picture."""
    kind = mark.get("type", "circle")
    x, y = float(mark.get("x", 0.5)) * W, float(mark.get("y", 0.5)) * H
    w, h = float(mark.get("w", 0.22)) * W, float(mark.get("h", 0.18)) * H
    amp = min(W, H) * 0.006
    if kind == "circle":  # R37: one stroke from just left of the bottom, clockwise on screen (left side, top, right
        # side) - tuned with qc.hand_over_ink so the right hand (turned 32 deg for rings) sits off the ink it has laid
        n = 140
        a0 = 0.62 * math.pi
        ang = a0 + np.linspace(0, 2 * math.pi, n)
        r = 1 + _jitter(n, 0.05, seed)
        return [np.stack([x + w / 2 * r * np.cos(ang), y + h / 2 * r * np.sin(ang)], 1)]
    if kind == "underline":
        n = 60
        xs = np.linspace(x - w / 2, x + w / 2, n)
        ys = y + _jitter(n, amp * 1.2, seed) + np.linspace(0, h * 0.08, n) + np.linspace(-0.5, 0.5, n) * float(mark.get("slant", 0)) * H
        return [np.stack([xs, ys], 1)]
    if kind == "write" and mark.get("_lay") is not None and mark["_lay"].get("WH") == (W, H):
        return [write_path(mark, mark["_lay"], W, H)]
    if kind == "write":  # fallback before the text is laid out (not cached by mark_pen)
        n = 50
        xs = np.linspace(x - w / 2, x + w / 2, n)
        ang = math.radians(-float(mark.get("angle", 0)))
        ys = y + (xs - x) * math.tan(ang) + np.sin(np.linspace(0, 18, n)) * h * 0.18
        return [np.stack([xs, ys], 1)]
    if kind == "dash" and mark.get("horizontal"):  # the portrait ticket's perforation: left to right
        n_d = max(3, int(w / (min(W, H) * 0.045)))
        out = []
        for k in range(n_d):
            a, b = k / n_d, (k + 0.6) / n_d
            ts = np.linspace(a, b, 8)
            out.append(np.stack([x - w / 2 + w * ts, y + _jitter(8, amp * 0.3, seed + k)], 1))
        return out
    if kind == "dash":  # a dashed cut line from (x, y - h/2) to (x + slant, y + h/2), drawn dash by dash
        n_d = max(3, int(h / (min(W, H) * 0.045)))
        sl = float(mark.get("slant", 0.0)) * W
        out = []
        for k in range(n_d):
            a, b = k / n_d, (k + 0.6) / n_d
            ts = np.linspace(a, b, 8)
            out.append(np.stack([x + sl * (ts - 0.5) + _jitter(8, amp * 0.3, seed + k), y - h / 2 + h * ts], 1))
        return out
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
        if mark.get("type") == "write":
            write_layout(mark, W, H, red, cfg)
        at, dur = float(mark.get("at", 0.6)), float(mark.get("dur", 0.45))
        p = (t - at) / max(dur, 1e-3)
        if dur <= 0.05 and t >= at - 1e-6:  # an "already written" mark is whole from its first frame (no 1-frame flicker)
            p = 1.0
        if p <= 0 and mark.get("type") == "write" and mark.get("note_pre") and mark.get("plate") and \
                not (mark.get("until") is not None and t >= float(mark["until"])):
            if out is None:
                out = base.copy()
            write_layout(mark, W, H, red, cfg)
            _draw_write(out, mark, 0.0, W, H, red, cfg, plate_only=True)  # the pinned note is there before the pen
            continue
        if p <= 0 or (mark.get("until") is not None and t >= float(mark["until"])):
            continue
        if out is None:
            out = base.copy()
        p = min(1.0, p)
        if mark.get("type") == "write":
            fa = mark.get("fade_after")  # seconds after the writing ends: the note fades out over 0.3 s
            f = 1.0 if fa is None else 1.0 - min(1.0, max(0.0, (t - at - dur - float(fa)) / 0.3))
            if f <= 0:
                continue
            if f < 1.0:
                lay = out.copy()
                _draw_write(lay, mark, p, W, H, red, cfg)
                out[:] = (out.astype(np.float32) * (1 - f) + lay.astype(np.float32) * f).astype(out.dtype)
            else:
                _draw_write(out, mark, p, W, H, red, cfg)
            continue
        if mark.get("type") == "stamp":  # small rubber stamp on the picture: the impression appears on the press frame
            imp = mark.get("_imp")
            if imp is None or mark.get("_imp_W") != W:
                from .endscreen import _stamp
                pal = {k: hex_to_rgb(v) for k, v in cfg["style"]["palette"].items()}
                imp = _stamp(str(mark.get("text", "")), cfg, max(40, int(float(mark.get("w", 0.30)) * W)), pal["red"],
                             float(mark.get("angle", -6)), int(mark.get("seed", 11)))
                mark["_imp"], mark["_imp_W"] = imp, W
            cx, cy = float(mark.get("x", 0.5)) * W, float(mark.get("y", 0.5)) * H
            blend(out, imp, int(cx - imp.shape[1] / 2), int(cy - imp.shape[0] / 2))
            continue
        if mark.get("type") == "dot":  # a filled marker dot (e.g. a place on a map), pressed on
            cx, cy = float(mark.get("x", 0.5)) * W, float(mark.get("y", 0.5)) * H
            r = max(3, int(float(mark.get("w", 0.02)) * W / 2 * (0.6 + 0.4 * ease(p))))
            col = tuple(int(c) for c in red)
            layer = out.copy()
            cv2.circle(layer, (int(cx), int(cy)), r, col, -1, cv2.LINE_AA)
            cv2.circle(layer, (int(cx), int(cy)), r, (30, 27, 24), max(2, r // 4), cv2.LINE_AA)
            a = min(1.0, p * 3)
            out[:] = (out * (1 - a) + layer * a).astype(out.dtype)
            continue
        if mark.get("type") == "led":  # digital countdown panel (factory.led), pops on
            from .led import led_panel
            key = ("_led", mark.get("text"), mark.get("label"), W)
            img = mark.get("_img")
            if img is None or mark.get("_key") != key:
                pan = led_panel(str(mark.get("text", "02:59:59")), mark.get("label"))
                tw = max(8, int(float(mark.get("w", 0.3)) * W))
                img = cv2.resize(pan, (tw, max(4, int(pan.shape[0] * tw / pan.shape[1]))), interpolation=cv2.INTER_AREA)
                mark["_img"], mark["_key"] = img, key
            s_ = 1.25 - 0.25 * ease(p)
            im = cv2.resize(img, (max(2, int(img.shape[1] * s_)), max(2, int(img.shape[0] * s_))))
            cx, cy = float(mark.get("x", 0.5)) * W, float(mark.get("y", 0.5)) * H
            blend(out, im, int(cx - im.shape[1] / 2), int(cy - im.shape[0] / 2), opacity=min(1.0, p * 2))
            continue
        strokes = mark.get("_strokes")
        if strokes is None:
            strokes = mark_strokes(mark, W, H, seed=17 + i)
            mark["_strokes"] = strokes
        travel = pen_travel(strokes, W, H)
        total = sum(len(s) for s in strokes) + sum(travel)
        budget = int(total * p)
        scol = red
        if mark.get("color") and mark.get("color") != "red":  # e.g. an ink sum rule
            pal_ = {k: hex_to_rgb(v) for k, v in cfg["style"]["palette"].items()}
            scol = tuple(int(c) for c in (pal_.get(mark["color"]) or hex_to_rgb(mark["color"])))
        for k_, s in enumerate(strokes):
            if k_ > 0:
                budget -= travel[k_ - 1]  # the pen lifted, travelling to the next stroke
            if budget <= 1:
                break
            seg = s[: min(len(s), budget)]
            budget -= len(seg)
            cv2.polylines(out, [seg.astype(np.int32).reshape(-1, 1, 2)], False, scol, thick, cv2.LINE_AA)
        if mark.get("text") and p >= 1.0:
            note = mark.get("_note")
            if note is None:
                fpath = resolve_font(cfg["fonts"]["marker"])
                fnt = font(fpath, max(24, int(min(W, H) * 0.055)))
                paper = tuple(int(c) for c in hex_to_rgb(cfg["style"]["palette"]["paper"]))
                note = text_block([str(mark["text"])], fnt, fill=red, stroke=max(3, fnt.size // 12), stroke_fill=paper)
                angle = float(mark.get("angle", -4))
                pil = Image.fromarray(note).rotate(angle, resample=Image.BICUBIC, expand=True)
                note = np.array(pil)
                mark["_note"] = note
            age = (t - at - dur) / 0.25
            nx = float(mark.get("text_x", mark.get("x", 0.5))) * W - note.shape[1] / 2
            ny = float(mark.get("text_y", float(mark.get("y", 0.5)) + float(mark.get("h", 0.18)) * 0.75)) * H
            ny = min(ny, H * 0.72 - note.shape[0])  # never down in the caption zone
            nx = min(max(nx, W * 0.1), W * 0.9 - note.shape[1])
            blend(out, note, int(nx), int(ny), opacity=min(1.0, max(0.0, age)))
    return base if out is None else out


def write_layout(mark: dict, W: int, H: int, red, cfg: dict) -> dict:
    """Render a written mark once: text image in its box, the ink's left/right edge and the pen height per column."""
    lay = mark.get("_lay")
    if lay is not None and lay.get("WH") == (W, H):
        return lay
    pal = {k: hex_to_rgb(v) for k, v in cfg["style"]["palette"].items()}
    col = mark.get("color", "red")
    col = pal.get(col) or (hex_to_rgb(col) if str(col).startswith("#") else red)
    bw, bh = max(8, int(float(mark.get("w", 0.2)) * W)), max(8, int(float(mark.get("h", 0.08)) * H))
    fkey = mark.get("font", "marker")
    path = resolve_font(cfg["fonts"].get(fkey) or cfg["fonts"]["marker"])
    txt = str(mark["text"])
    if mark.get("fs"):  # a fixed letter size (fraction of the picture height): labels in different boxes match
        size = max(8, int(float(mark["fs"]) * H))
        bw = max(bw, int(font(path, size).getlength(txt) / 0.94) + 2)
        bh = max(bh, int(size * 1.15))
    else:
        size = int(bh * 0.92)
        while size > 8 and font(path, size).getlength(txt) > bw * 0.94:
            size -= 1
    fnt = font(path, size)
    pil = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    d = ImageDraw.Draw(pil)
    if mark.get("bg"):
        bgc = pal.get(mark["bg"]) or hex_to_rgb(mark["bg"])
        d.rounded_rectangle((0, 0, bw - 1, bh - 1), radius=bh // 6, fill=tuple(bgc) + (255,))
    tw = fnt.getlength(txt)
    tx = bw * 0.03 if mark.get("align") == "left" else (bw - tw) / 2  # "left": lines in one box column start together
    ink = Image.new("L", (bw, bh), 0)
    ImageDraw.Draw(ink).text((tx, bh / 2), txt, font=fnt, fill=255, anchor="lm")
    d.text((tx, bh / 2), txt, font=fnt, fill=tuple(col) + (255,), anchor="lm")
    a = np.array(ink)
    cols = np.where(a.max(0) > 40)[0]
    x0, x1 = (int(cols.min()), int(cols.max()) + 1) if len(cols) else (0, bw)
    ys = np.arange(bh, dtype=np.float32)[:, None]
    wsum = a.astype(np.float32).sum(0)
    cy = np.where(wsum > 0, (a * ys).sum(0) / np.maximum(wsum, 1), bh * 0.5)
    peny = np.convolve(cy, np.ones(7) / 7, mode="same")
    lay = {"img": np.array(pil), "x0": x0, "x1": x1, "peny": peny, "bw": bw, "bh": bh, "WH": (W, H)}
    mark["_lay"] = lay
    return lay


def write_reveal_x(lay: dict, p: float) -> float:
    """Box x of the pen tip (= the revealed edge) at progress p. Reveal speed = pen speed."""
    return lay["x0"] + (lay["x1"] - lay["x0"]) * min(1.0, max(0.0, p))


def write_path(mark: dict, lay: dict, W: int, H: int, n: int = 60) -> np.ndarray:
    """Pen tip path in picture px: along the ink, left to right, rotated exactly like the text image."""
    xs = np.linspace(lay["x0"], lay["x1"], n)
    ys = lay["peny"][np.clip(xs.astype(int), 0, lay["bw"] - 1)]
    u, v = xs - lay["bw"] / 2, ys - lay["bh"] / 2
    a = math.radians(float(mark.get("angle", 0)))
    cx, cy = float(mark.get("x", 0.5)) * W, float(mark.get("y", 0.5)) * H
    return np.stack([cx + u * math.cos(a) + v * math.sin(a), cy - u * math.sin(a) + v * math.cos(a)], 1)


def _draw_write(out: np.ndarray, mark: dict, p: float, W: int, H: int, red, cfg: dict, plate_only: bool = False) -> None:
    """Handwritten (or printed) text in a box of the picture. The text is revealed by a mask that follows the
    pen tip exactly: nothing to the right of the tip exists yet.
    mark: text, x, y, w, h (box centre/size, picture fractions), angle (deg), color ('red'|'ink'|'paper'|hex),
          font ('marker'|'headline'|'body'|'typewriter'), bg (fill colour painted under the text, e.g. a ribbon)."""
    lay = write_layout(mark, W, H, red, cfg)
    img = lay["img"]
    h, w = img.shape[:2]
    if mark.get("plate"):  # a cream plate that appears with the pen's first stroke (never before the hand)
        sx, sy = mark["plate"]
        pw, ph = int(w * float(sx)), int(h * float(sy))
        key = (pw, ph)
        if mark.get("_plate_key") != key:
            pal = {k: hex_to_rgb(v) for k, v in cfg["style"]["palette"].items()}
            note = bool(mark.get("note"))  # a small paper note pinned to the wall: edge, shadow and a red pin
            m_ = max(6, ph // 8) if note else 0
            pl = Image.new("RGBA", (pw + 2 * m_, ph + 2 * m_), (0, 0, 0, 0))
            dd = ImageDraw.Draw(pl)
            if note:
                sh_ = Image.new("RGBA", pl.size, (0, 0, 0, 0))
                ImageDraw.Draw(sh_).rectangle((m_ + 5, m_ + 7, m_ + pw + 3, m_ + ph + 5), fill=(0, 0, 0, 70))
                pl.alpha_composite(sh_.filter(ImageFilter.GaussianBlur(4)))
                dd.rectangle((m_, m_, m_ + pw - 1, m_ + ph - 1), fill=(253, 250, 240, 255), outline=(170, 160, 140, 255), width=2)
                r = max(5, ph // 9)
                cxp = m_ + pw // 2
                dd.ellipse((cxp - r, m_ + r // 2, cxp + r, m_ + r // 2 + 2 * r), fill=tuple(pal["red"]) + (255,), outline=(90, 30, 20, 255), width=2)
            else:
                dd.rounded_rectangle((0, 0, pw - 1, ph - 1), radius=max(4, ph // 6), fill=tuple(pal["paper"]) + (255,))
            mark["_plate_img"] = np.array(pl.rotate(float(mark.get("angle", 0)), resample=Image.BICUBIC, expand=True))
            mark["_plate_key"] = key
        q = 1.0 if mark.get("note_pre") else min(1.0, p / 0.06)
        pim = mark["_plate_img"]
        cx, cy = float(mark.get("x", 0.5)) * W, float(mark.get("y", 0.5)) * H
        blend(out, pim, int(cx - pim.shape[1] / 2 - (1 - ease(q)) * pw * 0.12), int(cy - pim.shape[0] / 2), opacity=q)
    if plate_only:
        return
    sub = img.copy()
    if not mark.get("bg"):
        if p < 1 and mark.get("font") == "typewriter" and not mark.get("hand"):
            n = max(1, len(str(mark.get("text", ""))))
            p = math.floor(p * n) / n  # typed: letter by letter, no pen
        if p < 1:
            xr = write_reveal_x(lay, p)
            xs = np.arange(w, dtype=np.float32)
            a = np.clip((xr - xs) / 3.0, 0, 1)  # soft only BEHIND the tip
            sub[..., 3] = (sub[..., 3] * a[None, :]).astype(np.uint8)
    else:  # a label flips in at once (the pen then signs over it)
        sub[..., 3] = (sub[..., 3] * min(1.0, p * 4)).astype(np.uint8)
    rot = Image.fromarray(sub).rotate(float(mark.get("angle", 0)), resample=Image.BICUBIC, expand=True)
    cx, cy = float(mark.get("x", 0.5)) * W, float(mark.get("y", 0.5)) * H
    blend(out, np.array(rot), int(cx - rot.width / 2), int(cy - rot.height / 2))


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


_GRIDS: dict = {}
PARALLAX_MOTIONS = ("zoom_in", "zoom_out", "static")


def _pixel_grid(W: int, H: int):
    if (W, H) not in _GRIDS:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        _GRIDS[(W, H)] = (xx, yy)
    return _GRIDS[(W, H)]


class ImageShot(Shot):
    def __init__(self, start, duration, image: Image.Image, motion: str, size, cfg: dict,
                 marks: list[dict] | None = None, photo: bool = False, seed: int = 0, ad: dict | None = None,
                 depth: np.ndarray | None = None, draw: dict | None = None, fit: list | None = None):
        super().__init__(start, duration)
        self.draw = dict(draw) if draw else None  # {"at": s, "dur": s} hand draws the picture on screen
        self.W, self.H = size
        # Shorts: a vertical slice of a wide picture is too macro, so the picture plays in a square window
        # (most of the scene stays readable) over a blurred, darkened copy of itself.
        self.full = None
        self.zmax = MARGIN
        fit_x = None
        if self.H > self.W:
            self.full = (self.W, self.H)
            self.y0 = int(self.H * SHORT_VIEW_TOP)
            self.H = self.W
            self.zmax = 1.12
            if fit:  # "short_fit": [x0, x1] of the picture always in view; the window gets wider than tall
                sw0, sh0 = image.size
                c = min(1.0, (float(fit[1]) - float(fit[0])) * 1.10)  # + the static camera's 8 % push
                hwin = int(round(self.W * sh0 / (c * sw0)))
                hwin = max(hwin, int(round(self.full[1] * SHORT_MIN_BAND)))  # R38: the picture band never under half the frame
                if hwin < self.W:
                    self.y0 += (self.W - hwin) // 2  # same centre as the square window
                    self.H = hwin
                fit_x = (float(fit[0]) + float(fit[1])) / 2
        self.BW, self.BH = int(self.W * MARGIN), int(self.H * MARGIN)
        self.motion = motion
        # marks and bubbles are given in fractions of the ORIGINAL picture; the shot may show a crop of it
        # (Shorts show a vertical slice), so they are mapped into the cropped base here and follow the camera.
        marks = [dict(m) for m in (marks or [])]
        sw, sh = image.size
        focus_x = float(np.mean([float(m.get("x", 0.5)) for m in marks])) if marks else 0.5
        self.focus = (focus_x, 0.5)
        self._geo = cover_geometry(sw, sh, self.BW, self.BH, *self.focus)
        if fit_x is not None:  # the fitted window is centred on the fitted part, marks are inside it
            self.focus = (fit_x, 0.5)
            self._geo = cover_geometry(sw, sh, self.BW, self.BH, *self.focus)
        elif marks:  # a window that cuts a mark: centre it on the marks' bounding box instead
            lo = min(float(m.get("x", 0.5)) - float(m.get("w", 0.0)) / 2 for m in marks)
            hi = max(float(m.get("x", 0.5)) + float(m.get("w", 0.0)) / 2 for m in marks)
            nw0, _nh0, left0, _t0 = self._geo
            if lo < left0 / nw0 or hi > (left0 + self.BW) / nw0:
                if (hi - lo) * nw0 > self.BW:  # not all fit: the marks with a labelled target (the action) win
                    key = [m for m in marks if m.get("target")] or marks
                    lo = min(min(float(m["target"][0]), float(m.get("x", 0.5)) - float(m.get("w", 0.0)) / 2) if m.get("target")
                             else float(m.get("x", 0.5)) - float(m.get("w", 0.0)) / 2 for m in key)
                    hi = max(max(float(m["target"][2]), float(m.get("x", 0.5)) + float(m.get("w", 0.0)) / 2) if m.get("target")
                             else float(m.get("x", 0.5)) + float(m.get("w", 0.0)) / 2 for m in key)
                self.focus = ((lo + hi) / 2, 0.5)
                self._geo = cover_geometry(sw, sh, self.BW, self.BH, *self.focus)
        nw, nh, left, top = self._geo
        for m in marks:
            for k in ("x", "text_x", "from_x"):
                if k in m:
                    m[k] = (float(m[k]) * nw - left) / self.BW
            for k in ("y", "text_y", "from_y"):
                if k in m:
                    m[k] = (float(m[k]) * nh - top) / self.BH
            if "w" in m:
                m["w"] = float(m["w"]) * nw / self.BW
            if "h" in m:
                m["h"] = float(m["h"]) * nh / self.BH
            if m.get("fs"):
                m["fs"] = float(m["fs"]) * nh / self.BH
            if m.get("target"):
                tx0, ty0, tx1, ty1 = m["target"]
                m["target"] = [(tx0 * nw - left) / self.BW, (ty0 * nh - top) / self.BH, (tx1 * nw - left) / self.BW, (ty1 * nh - top) / self.BH]
            for k in ("obj", "printed"):  # QC mark_on_object boxes travel with the mark
                if m.get(k):
                    bs = [m[k]] if k == "obj" else m[k]
                    bs = [[(b[0] * nw - left) / self.BW, (b[1] * nh - top) / self.BH, (b[2] * nw - left) / self.BW,
                           (b[3] * nh - top) / self.BH] + list(b[4:]) for b in bs]
                    m[k] = bs[0] if k == "obj" else bs
        self.marks = marks
        self.red = tuple(int(c) for c in hex_to_rgb(cfg["style"]["palette"]["red"]))
        self.cfg = cfg
        # heavy pixel buffers are built on the first frame and freed by release() (keeps RAM flat on long videos)
        self._src = (image, photo, seed, ad, depth)
        self.base = None
        self.depth = None

    def _prepare(self) -> None:
        image, photo, seed, ad, depth = self._src
        cfg = self.cfg
        # 2.5D parallax: depth map in the same crop as the picture (white = near)
        self.depth = None
        strength = float(cfg["style"].get("parallax", 0.035))
        # sideways moves + depth tear the picture apart at depth edges, so parallax is used only on push-ins
        if depth is not None and not photo and strength > 0 and self.motion in PARALLAX_MOTIONS:
            dimg = Image.fromarray((np.clip(depth, 0, 1) * 255).astype(np.uint8)).resize(image.size, Image.BILINEAR)
            d = cover(dimg.convert("RGB"), self.BW, self.BH, *self.focus)[..., 0].astype(np.float32) / 255.0
            self.depth = cv2.GaussianBlur(d, (0, 0), 3) - 0.5
            self.par = strength * self.W
            self._grid = _pixel_grid(self.W, self.H)
        if photo:
            base = np.array(archival_print(image, cfg, self.BW, self.BH, seed))
        else:
            base = cover(image, self.BW, self.BH, *self.focus)
        if ad:
            base = draw_ad_overlay(base, ad, cfg)
        self.base = add_grain(base, float(cfg["style"].get("grain", 0)), seed)
        if self.draw:
            from .draw import LineDrawing
            paper = hex_to_rgb(cfg["style"]["palette"]["paper"])
            from .draw import subject_mask
            mask = None
            if self.draw.get("subject", True):
                dcrop = None
                if depth is not None:
                    dimg = Image.fromarray((np.clip(depth, 0, 1) * 255).astype(np.uint8)).resize(image.size, Image.BILINEAR)
                    dcrop = cover(dimg.convert("RGB"), self.BW, self.BH, *self.focus)[..., 0].astype(np.float32) / 255.0
                nw, nh, left, top = self._geo
                bx = self.draw.get("box", [0, 0, 1, 1])  # fractions of the original picture
                box = ((bx[0] * nw - left) / self.BW, (bx[1] * nh - top) / self.BH,
                       (bx[2] * nw - left) / self.BW, (bx[3] * nh - top) / self.BH)
                box = tuple(min(1.0, max(0.0, v)) for v in box)
                mask = subject_mask(self.base, dcrop, box, self.draw.get("mode", "shape"))
            self._ld = LineDrawing(self.base, paper, mask)
            self.depth = None  # no parallax while a picture is being drawn
        if self.marks:
            self.depth = None  # marks and the pen live on the flat picture: parallax would slide the ink off the pen
            self._clamp_writes()
        if self.full:
            fw, fh = self.full
            src_bg = Image.new("RGB", image.size, hex_to_rgb(cfg["style"]["palette"]["paper"])) if self.draw else image
            small = cover(src_bg, max(8, fw // 10), max(8, fh // 10))  # drawn pictures: plain backdrop, no spoiler
            small = cv2.GaussianBlur(small, (0, 0), 2.5)
            self.bg = (cv2.resize(small, (fw, fh), interpolation=cv2.INTER_LINEAR) * 0.45).astype(np.uint8)

    def _clamp_writes(self, pad: float = 0.012) -> None:
        """Rule: a mark is never written while it is outside the frame. A written label is moved (never resized)
        just inside the part of the picture the camera shows during its writing."""
        if getattr(self, "_clamped", False):
            return
        self._clamped = True
        for m in self.marks:
            if m.get("type") not in ("write", "circle", "cross"):
                continue
            at = max(0.0, float(m.get("at", 0.6)))
            dur = max(0.0, float(m.get("dur", 0.45)))
            x0, y0, x1, y1 = 0.0, 0.0, 1.0, 1.0
            for tt in np.linspace(at, min(self.duration, at + dur), 6):
                _p, s, M = self._matrix(float(tt))
                x0 = max(x0, (-M[0, 2]) / s / self.BW)
                x1 = min(x1, (self.W - M[0, 2]) / s / self.BW)
                y0 = max(y0, (-M[1, 2]) / s / self.BH)
                y1 = min(y1, (self.H - M[1, 2]) / s / self.BH)
            if m["type"] != "write":  # circle / cross: shrink to the visible part, if its target still fits inside
                x, y, w, h = float(m.get("x", 0.5)), float(m.get("y", 0.5)), float(m.get("w", 0.2)), float(m.get("h", 0.1))
                a0, b0 = max(x - w / 2, x0 + pad), max(y - h / 2, y0 + pad)
                a1, b1 = min(x + w / 2, x1 - pad), min(y + h / 2, y1 - pad)
                if (a0, b0, a1, b1) == (x - w / 2, y - h / 2, x + w / 2, y + h / 2) or a1 - a0 < 0.02 or b1 - b0 < 0.02:
                    continue
                tg = m.get("target")
                if tg and m["type"] == "cross":  # a cross over the whole picture strikes what is visible
                    tg = [max(tg[0], a0), max(tg[1], b0), min(tg[2], a1), min(tg[3], b1)]
                    m["target"] = tg
                if tg and not (a0 <= tg[0] + 1e-3 and b0 <= tg[1] + 1e-3 and tg[2] - 1e-3 <= a1 and tg[3] - 1e-3 <= b1):
                    continue
                m["x"], m["y"], m["w"], m["h"] = (a0 + a1) / 2, (b0 + b1) / 2, a1 - a0, b1 - b0
                continue
            hw, hh = float(m.get("w", 0.2)) / 2 + pad, float(m.get("h", 0.08)) / 2 + pad
            x, y = float(m.get("x", 0.5)), float(m.get("y", 0.5))
            nx = (x0 + x1) / 2 if x1 - x0 < 2 * hw else min(max(x, x0 + hw), x1 - hw)
            ny = (y0 + y1) / 2 if y1 - y0 < 2 * hh else min(max(y, y0 + hh), y1 - hh)
            if abs(nx - x) > 1e-4 or abs(ny - y) > 1e-4:
                m["x"], m["y"] = nx, ny
                m.pop("_lay", None)

    def release(self) -> None:
        self.base = None
        self.depth = None
        self.bg = None

    def _camera(self, p: float):
        zl = getattr(self, "zoom_lin", None)
        if zl:  # a slow, even push that can run on across two shots of one held picture: (z at start, z per second)
            return zl[0] + zl[1] * p * self.duration, 0.0, 0.0
        e = ease(p)
        zmax = self.zmax
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

    def _matrix(self, t: float):
        p = t / max(self.duration, 1e-6)
        z, dx, dy = self._camera(p)
        dy += getattr(self, "cam_dy", 0.0)  # push aimed a little lower: the picture rides up (clear of subtitles)
        win_w, win_h = self.BW / z, self.BH / z
        free_x, free_y = (self.BW - win_w) / 2, (self.BH - win_h) / 2
        cx = self.BW / 2 + dx * free_x * 0.95
        cy = self.BH / 2 + dy * free_y * 0.95
        s = self.W / win_w
        return p, s, np.float32([[s, 0, self.W / 2 - s * cx], [0, s, self.H / 2 - s * cy]])

    def to_screen(self, xf: float, yf: float, t: float) -> tuple[float, float]:
        """Screen position (px) of a point given in fractions of the original picture, at shot time t."""
        nw, nh, left, top = self._geo
        _p, _s, M = self._matrix(t)
        bx, by = xf * nw - left, yf * nh - top
        return float(M[0, 0] * bx + M[0, 2]), float(M[1, 1] * by + M[1, 2]) + (self.y0 if self.full else 0)

    def frame(self, t: float) -> np.ndarray:
        if self.base is None:
            self._prepare()
        if not self.full:
            out = self._view(t)
        else:
            out = self.bg.copy()
            out[self.y0 : self.y0 + self.H] = self._view(t)
        self._hands(out, t)
        return out

    def _screen(self, bx: float, by: float, t: float) -> tuple[float, float]:
        _p, _s, M = self._matrix(t)
        return float(M[0, 0] * bx + M[0, 2]), float(M[1, 1] * by + M[1, 2]) + (self.y0 if self.full else 0)

    def _hands(self, out: np.ndarray, t: float) -> None:
        from .draw import hand_path, mark_pen, paste_hand
        FW, FH = out.shape[1], out.shape[0]
        if self.draw:
            from .draw import COLOR_START, LINES_END
            at, dur = float(self.draw.get("at", 0.0)), float(self.draw.get("dur", 3.4))
            tip = lambda tt: self._screen(*self._ld.tip((tt - at) / dur), tt)
            pos = hand_path(tip, at, at + dur * LINES_END, t, FW, FH, mirrored=False)
            if pos:  # black-and-white newspaper hand with a pencil: the draft
                paste_hand(out, "pencil", pos[0], pos[1], mirrored=False)
            pos = hand_path(tip, at + dur * COLOR_START, at + dur, t, FW, FH, mirrored=False)
            if pos:  # colour hand with a marker: colouring in
                paste_hand(out, "colour", pos[0], pos[1], mirrored=False)
        if self.marks:
            pen = mark_pen(self.marks, t, self.BW, self.BH)
            if pen:
                ftip, t0, t1, kind = pen
                hs = 1.0
                if isinstance(kind, tuple):
                    kind, hs = kind
                mirrored = False  # R37: always a right hand, right of and below the tip - every letter appears left of the
                # pen and stays visible; near the right edge the frame crops the hand, never the mark
                pos = hand_path(lambda tt: self._screen(*ftip(tt), tt), t0, t1, t, FW, FH, mirrored)
                if pos:
                    paste_hand(out, kind, pos[0], pos[1], mirrored, scale=hs)
            from .draw import stamp_press, stamp_window
            for m in self.marks:  # the stamp hand presses small stamps (never a pen hand, never a drop-in)
                if m.get("type") != "stamp" or not m.get("hand"):
                    continue
                at = float(m.get("at", 0.6))
                w0, w1 = stamp_window(at)
                if not (w0 <= t <= w1) or m.get("_imp") is None:
                    continue
                _p, s_, _M = self._matrix(t)
                ih, iw = m["_imp"].shape[:2]
                ghost = np.zeros((max(2, int(ih * s_)), max(2, int(iw * s_)), 4), np.uint8)
                sx, sy = self._screen(float(m.get("x", 0.5)) * self.BW, float(m.get("y", 0.5)) * self.BH, t)
                stamp_press(out, ghost, sx, sy, t, at)

    def split_dx(self, t: float) -> float:
        """Picture split (visual "split"): how far (base px) the second piece has slid at shot time t (to the right,
        or down for "axis": "y" - the Shorts' portrait ticket has its stub under a horizontal perforation)."""
        sp = getattr(self, "split", None)
        if not sp:
            return 0.0
        q = (t - float(sp["t0"])) / max(1e-3, float(sp.get("dur", 0.7)))
        q = min(1.0, max(0.0, q))
        f = 1 - (1 - q) ** 3  # ease-out: quick start, soft settle
        if sp.get("t_back") is not None and t > float(sp["t_back"]):  # the halves slide back together
            qb = min(1.0, (t - float(sp["t_back"])) / max(1e-3, float(sp.get("back_dur", 0.6))))
            f *= 1 - qb * qb * (3 - 2 * qb)
        return f * float(sp["dx"]) * (self._geo[1] if sp.get("axis") == "y" else self._geo[0])

    def _split_src(self, src: np.ndarray, t: float) -> np.ndarray:
        d = int(round(self.split_dx(t)))
        nw, nh, left, top = self._geo
        sp = self.split
        if sp.get("axis") == "y":  # same cut on the transposed picture: rows become columns
            nw, nh, left, top = nh, nw, top, left
            src_, base_ = src.transpose(1, 0, 2), self.base.transpose(1, 0, 2)
        else:
            src_, base_ = src, self.base
        BW = src_.shape[1]
        xc = int(round(float(sp["x"]) * nw - left))
        xc = min(max(xc, 0), BW - 1)
        col = tuple(int(c) for c in sp.get("edge_rgb", (30, 27, 24)))
        out = None
        if d <= 0:
            if sp.get("t_back") is not None and t >= float(sp["t_back"]) and sp.get("y0") is not None:
                out = np.ascontiguousarray(src_).copy()  # back together: the cut stays visible as a seam
                y0, y1 = int(float(sp["y0"]) * nh - top), int(float(sp["y1"]) * nh - top)
                th = max(2, int(float(sp.get("edge_w", 0.0075)) * nh * 0.6))
                cv2.rectangle(out, (xc - th // 2, y0), (xc + th // 2, y1), col, -1)
        else:
            out = np.ascontiguousarray(src_).copy()
            if xc + d < BW:
                out[:, xc + d:] = src_[:, xc:BW - d]
            fill = base_[:, BW - min(d, BW - xc):]  # the plain backdrop at the far edge
            out[:, xc:xc + fill.shape[1]] = fill
            if sp.get("y0") is not None:  # a clean straight cut: both cut edges get the ticket's dark outline
                y0 = int(float(sp["y0"]) * nh - top)
                y1 = int(float(sp["y1"]) * nh - top)
                th = max(3, int(float(sp.get("edge_w", 0.0075)) * nh))
                cv2.rectangle(out, (xc - th, y0), (xc - 1, y1), col, -1)
                cv2.rectangle(out, (xc + d, y0), (xc + d + th - 1, y1), col, -1)
        if out is None:
            return src
        return np.ascontiguousarray(out.transpose(1, 0, 2)) if sp.get("axis") == "y" else out

    def _view(self, t: float) -> np.ndarray:
        p, s, M = self._matrix(t)
        src = self.base
        if self.draw:
            at, dur = float(self.draw.get("at", 0.0)), float(self.draw.get("dur", 3.4))
            src = self._ld.state((t - at) / dur)
        if getattr(self, "split", None):
            src = self._split_src(src, t)
            ax = "y" if self.split.get("axis") == "y" else "x"
            dxf = self.split_dx(t) / (self.BH if ax == "y" else self.BW)
            for m in self.marks:  # marks written on the moving piece ride with it
                if m.get("follow"):
                    m.setdefault(f"_f{ax}0", float(m[ax]))
                    m[ax] = m[f"_f{ax}0"] + dxf
        src = draw_marks(src, self.marks, t, self.red, self.cfg) if self.marks else src
        if self.depth is None:
            return cv2.warpAffine(src, M, (self.W, self.H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        # inverse mapping: output pixel -> source pixel, then shift near pixels more than far ones
        xx, yy = self._grid
        sx = (xx - M[0, 2]) / s
        sy = (yy - M[1, 2]) / s
        d = cv2.warpAffine(self.depth, M, (self.W, self.H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        k = ease(p) - 0.5  # -0.5 .. 0.5 over the shot
        m = self.motion
        if m in ("zoom_in", "zoom_out", "static"):
            sign = 1 if m != "zoom_out" else -1
            ox = -(xx - self.W / 2) / (self.W / 2) * d * self.par * k * sign
            oy = -(yy - self.H / 2) / (self.H / 2) * d * self.par * k * sign
        else:
            ux = 1.0 if m in ("pan_right", "drift") else (-1.0 if m == "pan_left" else 0.0)
            uy = 1.0 if m == "pan_down" else (-1.0 if m == "pan_up" else (0.3 if m == "drift" else 0.0))
            ox = d * self.par * k * ux * 2
            oy = d * self.par * k * uy * 2
        return cv2.remap(src, (sx + ox / s).astype(np.float32), (sy + oy / s).astype(np.float32),
                         cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


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
    """Big number card: value, prefix, suffix, label, decimals.
    R39 (Klot r89): no count-up - the final number appears whole with a short pop (110 % -> 100 % over 0.2 s) on the
    first word of its sentence (the card itself starts there), its subline with it. A wrong number is a factual error."""

    POP = 0.2

    def __init__(self, start, duration, spec: dict, cfg: dict, size, land_at: float | None = None):
        super().__init__(start, duration)
        self.W, self.H = size
        self.spec = spec
        self.ramp = 0.0  # the number is final from the first frame
        self.count = 0.0
        self.t0 = 0.0
        self.legacy_count = None  # (QC self-test only) a planted old-style count-up of this many seconds
        self.pal = {k: hex_to_rgb(v) for k, v in cfg["style"]["palette"].items()}
        self.bg = _sunburst(size, self.pal, cfg, seed=9)
        self.head = resolve_font(cfg["fonts"]["headline"])
        self.body = resolve_font(cfg["fonts"]["body"])
        label = str(spec.get("label", ""))
        self.label = None
        if label:
            fnt, lines = fit_font(label.upper(), self.body, int(self.W * 0.8), int(self.H * 0.16), start=int(self.H * 0.06),
                                  caption=True)  # a name or a source never splits across lines
            self.label = text_block(lines, fnt, fill=self.pal["ink"])
        self.cache: dict[str, np.ndarray] = {}
        self.final = self._num(float(spec["value"]))
        self._num_h = self._num_img(self.final).shape[0]

    def _num_img(self, txt: str) -> np.ndarray:
        if txt not in self.cache:
            fnt = font(self.head, int(self.H * (0.26 if self.W > self.H else 0.14)))
            self.cache[txt] = text_block([txt], fnt, fill=self.pal["red"], stroke=max(4, self.H // 160), stroke_fill=self.pal["ink"])
        return self.cache[txt]

    def has_text(self, t: float) -> bool:
        return True

    def shown(self, t: float) -> str:
        """The value on screen at shot time t (QC count_up: only ever the final one)."""
        if self.legacy_count:
            p = ease(min(1.0, max(0.0, t / self.legacy_count)))
            return self._num(float(self.spec["value"]) * p)
        return self.final

    def _num(self, v: float) -> str:
        dec = int(self.spec.get("decimals", 0))
        txt = f"{v:,.{dec}f}"
        return f"{self.spec.get('prefix', '')}{txt}{self.spec.get('suffix', '')}"

    def frame(self, t: float) -> np.ndarray:
        out = self.bg.copy()
        y_num = int(self.H * 0.42) - self._num_h // 2
        if self.label is not None:
            blend(out, self.label, (self.W - self.label.shape[1]) // 2, y_num + self._num_h + int(self.H * 0.02))
        num = self._num_img(self.shown(t))
        q = min(1.0, max(0.0, t / self.POP))
        sc = 1.10 - 0.10 * (1 - (1 - q) ** 2)  # the stamp: 110 % -> 100 %
        if sc > 1.0005:
            num = cv2.resize(num, (max(1, int(num.shape[1] * sc)), max(1, int(num.shape[0] * sc))), interpolation=cv2.INTER_LINEAR)
        blend(out, num, (self.W - num.shape[1]) // 2, int(self.H * 0.42) - num.shape[0] // 2)
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
        if dec is None:  # as few decimals as the value has: 37.5 % (never 37.50 %)
            txt = f"{v:,.2f}".rstrip("0").rstrip(".") if not float(v).is_integer() else f"{v:,.0f}"
        else:
            txt = f"{v:,.{int(dec)}f}"
        return f"{unit}{txt}" if unit in ("$", "€", "£") else f"{txt}{unit}"

    def reveal_times(self) -> list[float]:
        n = len(self.spec["values"])
        g = self.grow_time
        if self.spec["kind"] == "bar":
            return [g]  # all bars land together
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
                p = ease(t / g)  # rule 35: every bar grows from zero to its height, all together, never shrinking
                bx = x0 + slot * i + (slot - bw) / 2
                top = y1 - (y1 - y0) * (v / vmax) * p
                color = self.pal["red"] if (highlight is not None and i == highlight) else self.pal["green"]
                if p > 0:
                    draw.rectangle((bx, top, bx + bw, y1), fill=color, outline=self.pal["ink"], width=3)
                draw.text((bx + bw / 2, y1 + 12), str(lab), font=lab_font, fill=self.pal["ink"], anchor="ma")
                if p >= 0.999:
                    vls = self.spec.get("value_labels")
                    vl = vls[i] if isinstance(vls, (list, tuple)) and i < len(vls) else None  # True = the plain values
                    draw.text((bx + bw / 2, top - 8), vl or self._fmt(v), font=val_font, fill=self.pal["ink"], anchor="md")
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
        self.desk = add_grain(desk, 0.05, int(spec.get("seed", seed)))
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
        seed = int(spec.get("seed", seed))
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
        # keep the whole card inside the top ~80% of what the camera shows at the end of its push-in,
        # so captions at the bottom never cover it
        win_h = self.BH / 1.12
        top_v = (self.BH - win_h) / 2
        top_ok, max_h = top_v + win_h * 0.04, win_h * 0.76
        if rgba.height > max_h:
            k = max_h / rgba.height
            rgba = rgba.resize((int(rgba.width * k), int(rgba.height * k)), Image.LANCZOS)
        base = Image.fromarray(self.desk.copy())
        shadow = Image.new("RGBA", rgba.size, (0, 0, 0, 0))
        shadow.paste((0, 0, 0, 80), mask=rgba.split()[3])
        shadow = shadow.filter(ImageFilter.GaussianBlur(14))
        x, y = (self.BW - rgba.width) // 2, int(top_ok + (max_h - rgba.height) / 2)
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
        space = fnt.getlength(" ")
        block_w = max(sum(fnt.getlength(w) for w in ln.split(" ")) + space * (len(ln.split(" ")) - 1) for ln in lines)
        for line in lines:
            ws = line.split(" ")
            widths = [fnt.getlength(w) for w in ws]
            # Klot r86: lines flush left in a centred block - a line being revealed word by word reads as typing, never
            # as a block that re-centres when its last word lands
            x = (self.W - block_w) / 2
            for w, ww in zip(ws, widths):
                color = pal["red"] if (wi < len(accent) and accent[wi]) else fg
                img = text_block([w], fnt, fill=color)
                appear = (times[wi] if wi < len(times) else wi * 0.25) + lead_in
                self.items.append((img, int(x), int(y), appear))
                x += ww + space
                wi += 1
            y += lh
        for k_ in range(min(2, len(self.items))):  # no lone word on the cut: the first two words are already there
            img0, x0_, y0_, _a = self.items[k_]
            self.items[k_] = (img0, x0_, y0_, 0.0)

    def frame(self, t: float) -> np.ndarray:
        # rule 31: the whole text is laid out first and every word appears in its final place (a quick fade, no
        # scale pop); rule 26: only the paper behind it moves (a slow push), so nothing already written ever moves
        z = 1.0 + 0.045 * min(1.0, max(0.0, t) / max(4.0, self.duration))
        M = np.float32([[z, 0, (1 - z) * self.W / 2], [0, z, (1 - z) * self.H / 2]])
        out = cv2.warpAffine(self.bg, M, (self.W, self.H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        for img, x, y, appear in self.items:
            age = t - appear
            if age < 0:
                continue
            blend(out, img, x, y, opacity=min(1.0, age / 0.10))
        return out

    def word_boxes(self, t: float) -> list[tuple[int, int, int, int]]:
        """Boxes of the words on screen at t (QC text_stability)."""
        return [(x, y, x + img.shape[1], y + img.shape[0]) for img, x, y, appear in self.items if t >= appear]


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



# ---------------------------------------------------------------- video clip (Grok Imagine, Veo, …)

class ClipShot(Shot):
    """Plays a short video file (muted) scaled to cover the frame; holds the last frame with a slow push
    if the narration runs longer than the clip."""

    def __init__(self, start, duration, path, size, cfg: dict, speed: float = 1.0):
        super().__init__(start, duration)
        self.W, self.H = size
        self.path = str(path)
        self.cap = cv2.VideoCapture(self.path)
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 24.0
        self.n = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        self.speed = speed
        self.idx = -1
        self.last = None
        g = float(cfg["style"].get("grain", 0)) * 0.6
        self._g = paper_grain(self.H, self.W, g, 5) if g > 0 else None

    def _read(self, i: int):
        if i < self.idx:
            self.cap.release()
            self.cap = cv2.VideoCapture(self.path)
            self.idx = -1
        while self.idx < i:
            ok, fr = self.cap.read()
            if not ok:
                break
            self.idx += 1
            self.last = fr
        return self.last

    def frame(self, t: float) -> np.ndarray:
        i = int(t * self.fps * self.speed)
        hold = 0.0
        if self.n and i >= self.n:
            hold = (i - self.n + 1) / (self.fps * self.speed)
            i = self.n - 1
        fr = self._read(i)
        if fr is None:
            return np.zeros((self.H, self.W, 3), np.uint8)
        rgb = cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)
        h, w = rgb.shape[:2]
        z = 1.0 + 0.04 * min(1.0, hold / 3)
        scale = max(self.W / w, self.H / h) * z
        nw, nh = int(np.ceil(w * scale)), int(np.ceil(h * scale))
        big = cv2.resize(rgb, (nw, nh), interpolation=cv2.INTER_LINEAR)
        x0, y0 = (nw - self.W) // 2, (nh - self.H) // 2
        out = big[y0 : y0 + self.H, x0 : x0 + self.W]
        if self._g is not None:
            return np.clip(out.astype(np.int16) + self._g, 0, 255).astype(np.uint8)
        return np.ascontiguousarray(out)


_TRACK_CACHE: dict = {}


_EVENT_CACHE: dict = {}


def clip_event(clip: str, which: str = "end") -> float:
    """Clip seconds where its main movement starts or ends ("end" = the click of a switch, a stop): frame-to-frame
    change on a small grey copy, smoothed; the movement is where it exceeds 20 % of its peak."""
    key = (clip, which)
    if key in _EVENT_CACHE:
        return _EVENT_CACHE[key]
    cap = cv2.VideoCapture(clip)
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    prev, e = None, []
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        g = cv2.GaussianBlur(cv2.cvtColor(cv2.resize(fr, (320, int(320 * fr.shape[0] / fr.shape[1]))), cv2.COLOR_BGR2GRAY), (0, 0), 1.5)
        e.append(0.0 if prev is None else float(np.abs(g.astype(np.float32) - prev).mean()))
        prev = g.astype(np.float32)
    cap.release()
    if not e:
        return 0.0
    s = np.convolve(np.array(e), np.ones(5) / 5, mode="same")
    pk = int(np.argmax(s))
    on = s > 0.2 * s[pk]
    if which == "start":
        i = pk
        while i > 0 and on[i - 1]:
            i -= 1
    else:
        i = pk
        while i < len(s) - 1 and on[i + 1]:
            i += 1
    t = i / fps
    _EVENT_CACHE[key] = t
    return t


def _smooth_tracks(arr: np.ndarray) -> np.ndarray:
    """Rule 28 (no jitter): a clip's camera is a smooth move, so the per-frame feature fits (noisy by a few px) are
    reduced to scale / angle / shift, cleaned of outliers (running median) and fitted with a wide Savitzky-Golay curve;
    marks carried by the result move with the picture without shaking."""
    from scipy.ndimage import median_filter
    from scipy.signal import savgol_filter
    a, b = arr[:, 0, 0].astype(np.float64), arr[:, 1, 0].astype(np.float64)
    sc, an = np.hypot(a, b), np.arctan2(b, a)
    tx, ty = arr[:, 0, 2].astype(np.float64), arr[:, 1, 2].astype(np.float64)
    n = len(arr)
    out = []
    for v in (sc, an, tx, ty):
        if n >= 9:
            v = median_filter(v, size=9, mode="nearest")
        win = min(61, n if n % 2 else n - 1)
        if win >= 7:
            v = savgol_filter(v, win, 2, mode="interp")
        out.append(v)
    sc, an, tx, ty = out
    res = np.zeros_like(arr, dtype=np.float32)
    res[:, 0, 0], res[:, 0, 1], res[:, 0, 2] = sc * np.cos(an), -sc * np.sin(an), tx
    res[:, 1, 0], res[:, 1, 1], res[:, 1, 2] = sc * np.sin(an), sc * np.cos(an), ty
    return res


_MED_CACHE: dict = {}


def clip_median(clip: str, A: list, BW: int, BH: int, focus) -> np.ndarray:
    """The clip's scene without its moving parts, in still-picture px: every 2nd frame carried back onto the still with
    the inverse of its track, per-pixel median."""
    key = (clip, BW, BH, tuple(focus))
    if key in _MED_CACHE:
        return _MED_CACHE[key]
    cap = cv2.VideoCapture(clip)
    st, i = [], 0
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        if i % 2 == 0 and i < len(A):  # half size: the median is a mask source, not a picture
            rgb = cover(Image.fromarray(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)), BW, BH, *focus)
            w_ = cv2.warpAffine(rgb, cv2.invertAffineTransform(np.float32(A[i])), (BW, BH), flags=cv2.INTER_LINEAR,
                                borderMode=cv2.BORDER_REPLICATE)
            st.append(cv2.resize(w_, (BW // 2, BH // 2), interpolation=cv2.INTER_AREA))
        i += 1
    cap.release()
    med = cv2.resize(np.median(np.stack(st), axis=0).astype(np.uint8), (BW, BH), interpolation=cv2.INTER_LINEAR)
    _MED_CACHE[key] = med
    return med


def clip_tracks(clip: str, still_base: np.ndarray, BW: int, BH: int, focus) -> list:
    """Per clip frame: 2x3 similarity mapping still-picture px (the covered still) -> clip-frame px (same cover).
    ORB features on the static background, RANSAC (moving subjects are outliers), then a 7-frame moving average."""
    key = (clip, BW, BH, tuple(focus))
    if key in _TRACK_CACHE:
        return _TRACK_CACHE[key]
    sc = 960.0 / BW
    small = lambda im: cv2.cvtColor(cv2.resize(im, (int(BW * sc), int(BH * sc)), interpolation=cv2.INTER_AREA), cv2.COLOR_RGB2GRAY)
    orb = cv2.ORB_create(3000)
    k0, d0 = orb.detectAndCompute(small(still_base), None)
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    cap = cv2.VideoCapture(clip)
    raw, prev = [], np.float32([[1, 0, 0], [0, 1, 0]])
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        rgb = cover(Image.fromarray(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)), BW, BH, *focus)
        k1, d1 = orb.detectAndCompute(small(rgb), None)
        A = None
        if d0 is not None and d1 is not None and len(k1) > 20:
            ms = sorted(bf.match(d0, d1), key=lambda m: m.distance)[:800]
            if len(ms) >= 12:
                p0 = np.float32([k0[m.queryIdx].pt for m in ms])
                p1 = np.float32([k1[m.trainIdx].pt for m in ms])
                A, inl = cv2.estimateAffinePartial2D(p0, p1, method=cv2.RANSAC, ransacReprojThreshold=3.0, maxIters=4000)
                if A is not None and (inl is None or int(inl.sum()) < 12):
                    A = None
        if A is None:
            A = prev
        prev = A
        raw.append(A.astype(np.float32))
    cap.release()
    if not raw:
        _TRACK_CACHE[key] = []
        return []
    arr = np.stack(raw)
    sm = _smooth_tracks(arr)
    S, Si = np.diag([sc, sc, 1.0]), np.diag([1 / sc, 1 / sc, 1.0])
    out = []
    for A in sm:  # back to full-size px: A_full = S^-1 . A_small . S
        A3 = np.vstack([A, [0, 0, 1]])
        out.append((Si @ A3 @ S)[:2].astype(np.float32))
    _TRACK_CACHE[key] = out
    return out


class ClipImageShot(ImageShot):
    """A hand-made live clip (episodes/<slug>/clips/<beat id>.mp4, e.g. Grok image-to-video from the approved still)
    played muted under the same marks, drawing hand and plates as the still it replaces. The clip's own camera
    (a Grok push-in, a drift) is tracked against the still (ORB + RANSAC similarity per frame, smoothed): the ink is
    drawn in the still's coordinates and carried with the picture, and the pen hand follows it. Holds the last frame
    if the beat is longer than the clip."""

    def __init__(self, start, duration, image, motion, size, cfg, marks=None, seed=0, clip=None, until=None, fit=None):
        super().__init__(start, duration, image, motion, size, cfg, marks=marks, photo=False, seed=seed, fit=fit)
        self.clip = str(clip)
        self.until = until  # clip seconds: the picture freezes on this frame (e.g. walking slips stop before we write)
        self.sync = None  # (t0, c0, c1, speed): first frame until shot t0, then clip c0..c1 at `speed`, then normal speed
        self._cap = None
        self._idx = -1
        self._last = None
        self._A = None
        self._cur = np.float32([[1, 0, 0], [0, 1, 0]])

    def _prepare(self) -> None:
        super()._prepare()
        self.depth = None
        self._cap = cv2.VideoCapture(self.clip)
        self._fps = self._cap.get(cv2.CAP_PROP_FPS) or 24.0
        self._n = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        self._grain = float(self.cfg["style"].get("grain", 0))
        if self._A is None:
            self._A = clip_tracks(self.clip, self.base, self.BW, self.BH, self.focus)
        self._bg_med = None
        if any(m.get("behind_moving") for m in self.marks) and self._A:
            self._bg_med = clip_median(self.clip, self._A, self.BW, self.BH, self.focus)

    def clip_time(self, t: float) -> float:
        if self.sync is None:
            return t
        t0, c0, c1, sp = self.sync
        if sp == 0:
            return c0  # frozen on one frame
        if t < t0:
            return 0.0  # the clip's first frame, held
        t1 = t0 + (c1 - c0) / sp
        return c0 + (t - t0) * sp if t < t1 else c1 + (t - t1)

    def _clip_frame(self, t: float):
        i = int(self.clip_time(t) * self._fps)
        if self.until is not None:
            i = min(i, int(float(self.until) * self._fps))
        if self._n:
            i = min(i, self._n - 1)
        if i < self._idx:
            self._cap.release()
            self._cap = cv2.VideoCapture(self.clip)
            self._idx = -1
        while self._idx < i:
            ok, fr = self._cap.read()
            if not ok:
                break
            self._idx += 1
            self._last = fr
        return self._last

    def frame(self, t: float) -> np.ndarray:
        if self.base is None:
            self._prepare()
        fr = self._clip_frame(t)
        if fr is not None:
            rgb = Image.fromarray(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB))
            self.base = add_grain(cover(rgb, self.BW, self.BH, *self.focus), self._grain, 0)
            if self._A:
                self._cur = self._A[min(max(self._idx, 0), len(self._A) - 1)]
        return super().frame(t)

    def _screen(self, bx: float, by: float, t: float) -> tuple[float, float]:
        A = self._cur
        return super()._screen(float(A[0, 0] * bx + A[0, 1] * by + A[0, 2]), float(A[1, 0] * bx + A[1, 1] * by + A[1, 2]), t)

    def _view(self, t: float) -> np.ndarray:
        p, s, M = self._matrix(t)
        src = self.base
        if self.marks:
            z = np.zeros_like(src)
            b = draw_marks(z, self.marks, t, self.red, self.cfg)
            if b is not z:  # ink on screen: matte it (drawn on black and on white) and carry it with the picture
                w = draw_marks(np.full_like(src, 255), self.marks, t, self.red, self.cfg)
                a = np.clip(1.0 - (w.astype(np.float32) - b.astype(np.float32)).mean(2, keepdims=True) / 255.0, 0, 1)
                A = self._cur
                bw = cv2.warpAffine(b, A, (self.BW, self.BH), flags=cv2.INTER_LINEAR)
                aw = cv2.warpAffine(a, A, (self.BW, self.BH), flags=cv2.INTER_LINEAR)[..., None]
                if getattr(self, "_bg_med", None) is not None:  # "behind_moving": a part of the clip that moves
                    # (the lever) passes IN FRONT of the ink - the ink is hidden where the frame differs from the
                    # scene without its moving parts
                    bgc = cv2.warpAffine(self._bg_med, A, (self.BW, self.BH), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
                    mov = (np.abs(src.astype(np.int16) - bgc.astype(np.int16)).max(2) > 34).astype(np.uint8)
                    mov = cv2.morphologyEx(mov, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
                    mov = cv2.GaussianBlur(cv2.dilate(mov, np.ones((7, 7), np.uint8)).astype(np.float32), (0, 0), 2.0)
                    keep = (1.0 - np.clip(mov, 0, 1))[..., None]
                    aw = aw * keep
                    bw = (bw.astype(np.float32) * keep).astype(np.float32)
                src = (src.astype(np.float32) * (1 - aw) + bw.astype(np.float32)).clip(0, 255).astype(np.uint8)
        return cv2.warpAffine(src, M, (self.W, self.H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

    def release(self) -> None:
        super().release()
        if self._cap is not None:
            self._cap.release()
            self._cap = None
