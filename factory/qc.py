"""Release-blocking QC checks on a built plan (Klot r84, part C). Every check returns a list of failures (empty = PASS).

plate_fit        every plate / caption / card box inside the frame with >= 24 px margin, no plate overlapping another
crop_fit         Shorts: one picture window per beat (constant), every mark of the beat inside it
jitter_check     every mark carried by the camera moves smoothly: no reversal > 0.25 px between frames
mark_in_frame    a picture-attached mark never leaves the frame while it is on screen (camera or clip push-in)
mark_on_object   a mark with an "obj" box sits inside it (6 % margin), off its printed text, within 2 deg of its angle
sfx_sync         every scratch sound lies inside a span where a hand lays ink (start, and end + 80 ms)
voice_cut_check  every edit point of the narration (line start / end) is quiet: RMS < -45 dBFS in 30 ms each side
text_stability   kinetic cards: a word, once shown, never moves
"""
from __future__ import annotations

import math

import cv2
import numpy as np

SCRATCH = ("scribble", "marker", "pencil")


def _inter(a, b) -> bool:
    return a[1] < b[3] and b[1] < a[3] and a[2] < b[4] and b[2] < a[4]


def plate_fit(plan, cfg, step: float = 0.25, margin: int = 24, t_from: float = 0.0, t_to: float | None = None) -> list[str]:
    from .render import Overlay
    ov = Overlay(cfg, plan)
    W, H = plan.size
    margin = int(round(margin * min(W, H) / 1080))  # 24 px at 1080p (QC builds may run at half size)
    fails, seen = [], set()
    caps, cards, bubs = plan.captions, plan.cards, plan.bubbles
    t = t_from
    while t < (plan.total if t_to is None else min(plan.total, t_to)):
        ci = next((i for i, c in enumerate(caps) if c.end > t), len(caps))
        ki = next((i for i, c in enumerate(cards) if c.end > t), len(cards))
        bi = next((i for i, c in enumerate(bubs) if c.end > t), len(bubs))
        frame = np.zeros((H, W, 3), np.uint8)
        ov.apply(frame, t, ci, ki, bi)
        boxes = [b for b in ov.boxes if b[0] in ("plate", "label", "alleged", "card", "hook", "caption", "ledger")]
        for b in boxes:
            if b[0] in ("caption", "ledger"):
                continue  # (the caption block includes its stroke; its own bounds are set by the caption layout)
            if b[1] < margin or b[2] < margin or b[3] > W - margin or b[4] > H - margin:
                key = ("edge", b[0], b[1], b[2])
                if key not in seen:
                    seen.add(key)
                    fails.append(f"{_tc(t)} {b[0]} box {b[1:]} closer than {margin} px to the frame edge")
        plates = [b for b in boxes if b[0] in ("plate", "label", "alleged", "card", "hook", "ledger")]
        for i in range(len(plates)):
            for j in range(i + 1, len(plates)):
                a, c = plates[i], plates[j]
                if {a[0], c[0]} == {"label", "alleged"} and abs(a[2] - c[2]) < 40:
                    if a[3] <= c[1] + 2 or c[3] <= a[1] + 2:
                        continue  # ALLEGED is the prefix of the source plate (same row, side by side)
                if _inter(a, c):
                    key = ("ov", a[0], c[0], a[1], c[1])
                    if key not in seen:
                        seen.add(key)
                        fails.append(f"{_tc(t)} {a[0]} overlaps {c[0]}")
        if plan.kind == "short":  # R27: band plates stay in the band above the picture
            wt = ov._window_top(t)
            for b in boxes:
                if b[0] in ("plate", "label", "alleged", "hook", "card") and b[4] > wt + 2:
                    key = ("band", b[0], b[1], b[2])
                    if key not in seen:
                        seen.add(key)
                        fails.append(f"{_tc(t)} {b[0]} reaches {b[4] - wt} px into the picture")
        for b in boxes:  # plates never sit on the burned-in captions either
            if b[0] in ("plate", "label", "alleged"):
                for c in boxes:
                    if c[0] == "caption" and _inter(b, c):
                        key = ("cap", b[0], b[1])
                        if key not in seen:
                            seen.add(key)
                            fails.append(f"{_tc(t)} {b[0]} overlaps the caption")
        t += step
    return fails


def _set_clip(sh, t: float) -> None:
    """A live clip shot: put its camera track on the frame shown at shot time t (the render leaves it on its last frame)."""
    from .shots import ClipImageShot
    if isinstance(sh, ClipImageShot):
        if sh.base is None:
            sh._prepare()
        A = sh._A or []
        if A:
            i = int(sh.clip_time(t) * sh._fps)
            if sh.until is not None:
                i = min(i, int(float(sh.until) * sh._fps))
            sh._cur = A[min(max(i, 0), len(A) - 1)]


def _on_screen(m: dict, dur: float) -> tuple[float, float]:
    """(from, to) shot seconds a mark is on screen: written / pressed .. until / faded out / shot end."""
    a0 = max(0.0, float(m.get("at", 0.0)))
    a1 = float(m["until"]) if m.get("until") is not None else dur
    if m.get("fade_after") is not None:
        a1 = min(a1, a0 + float(m.get("dur", 0.0)) + float(m["fade_after"]) + 0.3)
    return a0, min(a1, dur)


def _mx(m: dict) -> float:
    return float(m.get("_fx0", m["x"]))  # a "follow" mark's own place (the render moves it with the split)


def _tc(t: float) -> str:
    return f"{int(t // 60)}:{t % 60:04.1f}"


def crop_fit(plan, beats: list[dict]) -> list[str]:
    """Shorts: the window of every image shot of a beat is the same, and every mark is inside it during the beat."""
    from .shots import ImageShot
    if plan.kind != "short":
        return []
    fails = []
    starts = sorted(plan.beat_starts.items(), key=lambda kv: kv[1])
    ends = {bid: (starts[k + 1][1] if k + 1 < len(starts) else plan.total) for k, (bid, _s) in enumerate(starts)}
    for bid, s0 in starts:
        e0 = ends[bid]
        shots = [sh for sh in plan.shots if isinstance(sh, ImageShot) and s0 - 0.3 <= sh.start < e0 - 0.05 and getattr(sh, "full", None)]
        if not shots:
            continue
        wins = {(round(sh.y0), round(sh.H), tuple(round(v, 3) for v in sh.focus)) for sh in shots}
        if len(wins) > 1:
            fails.append(f"{bid}: the picture window changes within the beat ({len(wins)} windows)")
        for sh in shots:
            if sh.base is None:
                sh._prepare()
            for m in sh.marks:
                if m.get("type") not in ("write", "stamp", "circle"):
                    continue
                if m.get("follow"):
                    continue  # rides the split stub (checked by mark_on_object on the stub)
                a0, a1 = _on_screen(m, sh.duration)
                for tt in np.linspace(a0, max(a0, a1 - 1e-3), 4):
                    _set_clip(sh, tt)
                    x0 = (float(m["x"]) - float(m.get("w", 0.1)) / 2) * sh.BW
                    x1 = (float(m["x"]) + float(m.get("w", 0.1)) / 2) * sh.BW
                    y_ = float(m["y"]) * sh.BH
                    a = sh._screen(x0, y_, tt)
                    b = sh._screen(x1, y_, tt)
                    if a[0] < -1 or b[0] > sh.W + 1 or a[1] < sh.y0 - 1 or a[1] > sh.y0 + sh.H + 1:
                        fails.append(f"{bid}: mark '{m.get('text', m['type'])}' leaves the window at {sh.start + tt:.1f}s")
                        break
    return fails


def jitter_check(plan, fps: float = 24.0, tol: float = 0.25) -> list[str]:
    """Screen position of every mark centre, frame by frame: it may speed up or slow down, never reverse by > tol px."""
    from .shots import ClipImageShot, ImageShot
    fails = []
    for sh in plan.shots:
        if not isinstance(sh, ImageShot) or not sh.marks:
            continue
        if isinstance(sh, ClipImageShot):
            if sh.base is None:
                sh._prepare()
            A = sh._A or []
        n = max(2, int(sh.duration * fps))
        for m in sh.marks:
            if m.get("type") not in ("write", "stamp", "circle") or m.get("follow"):
                continue
            bx, by = float(m["x"]) * sh.BW, float(m["y"]) * sh.BH
            xs, ys = [], []
            for k in range(n):
                t = k / fps
                if isinstance(sh, ClipImageShot) and A:
                    i = int(sh.clip_time(t) * sh._fps)
                    if sh.until is not None:
                        i = min(i, int(float(sh.until) * sh._fps))
                    sh._cur = A[min(max(i, 0), len(A) - 1)]
                x, y = sh._screen(bx, by, t)
                xs.append(x)
                ys.append(y)
            for arr, ax in ((np.array(xs), "x"), (np.array(ys), "y")):
                v = np.diff(arr)
                bad = [k for k in range(1, len(v)) if v[k] * v[k - 1] < 0 and min(abs(v[k]), abs(v[k - 1])) > tol]
                if bad:
                    fails.append(f"{_tc(sh.start + bad[0] / fps)} mark '{m.get('text', m['type'])}' shakes ({len(bad)} reversals in {ax})")
                    break
    return fails


def mark_in_frame(plan, fps: float = 6.0) -> list[str]:
    """R32: a picture-attached mark (write / stamp) never leaves the frame while it is on screen (the camera or the
    clip's own move would crop it). Sampled at 6 fps over the mark's whole time on screen."""
    from .shots import ClipImageShot, ImageShot
    fails, seen = [], set()
    for sh in plan.shots:
        if not isinstance(sh, ImageShot) or not sh.marks:
            continue
        if isinstance(sh, ClipImageShot):
            if sh.base is None:
                sh._prepare()
            A = sh._A or []
        y_lo = sh.y0 if sh.full else 0
        y_hi = y_lo + sh.H
        for m in sh.marks:
            if m.get("type") not in ("write", "stamp") or m.get("follow"):
                continue
            a0 = max(0.0, float(m.get("at", 0.0)) + float(m.get("dur", 0.0)))
            a1 = min(sh.duration, float(m["until"]) if m.get("until") is not None else sh.duration)
            if m.get("fade_after") is not None:  # a note that fades out is gone 0.3 s after its fade starts
                a1 = min(a1, float(m.get("at", 0.0)) + float(m.get("dur", 0.0)) + float(m["fade_after"]) + 0.3)
            pw = float((m.get("plate") or [1.0])[0]) if m.get("type") == "write" else 1.0
            hw = float(m.get("w", 0.1)) * sh.BW / 2 * pw
            hh = (float(m.get("h", 0)) or float(m.get("w", 0.1)) * 0.3) * sh.BH / 2
            bx, by = float(m["x"]) * sh.BW, float(m["y"]) * sh.BH
            k = 0
            while a0 + k / fps < a1 - 0.05:
                t = a0 + k / fps
                k += 1
                if isinstance(sh, ClipImageShot) and A:
                    i = int(sh.clip_time(t) * sh._fps)
                    if sh.until is not None:
                        i = min(i, int(float(sh.until) * sh._fps))
                    sh._cur = A[min(max(i, 0), len(A) - 1)]
                pts = [sh._screen(bx + dx, by + dy, t) for dx in (-hw, hw) for dy in (-hh, hh)]
                if any(px < -2 or px > sh.W + 2 or py < y_lo - 2 or py > y_hi + 2 for px, py in pts):
                    key = (m.get("text"), round(sh.start, 1))
                    if key not in seen:
                        seen.add(key)
                        fails.append(f"{_tc(sh.start + t)} mark '{m.get('text', m['type'])}' is cropped by the frame edge")
                    break
    return fails


def mark_on_object(plan) -> list[str]:
    """Marks given an "obj": [x0, y0, x1, y1, angle] (picture fractions + the object's angle in degrees) and optional
    "printed": [[x0, y0, x1, y1], ...] (printed text on it): the ink box sits inside the object box with a 6 % margin,
    off the printed text, and handwriting is level with the object (within 2 deg; stamps are pressed at an angle)."""
    from .shots import ImageShot, write_layout
    fails, seen = [], set()
    for sh in plan.shots:
        if not isinstance(sh, ImageShot):
            continue
        for m in sh.marks:
            ob = m.get("obj")
            if not ob or m.get("type") not in ("write", "stamp"):
                continue
            key = (m.get("text"), round(_mx(m), 3), round(float(m["y"]), 3))
            if key in seen:
                continue
            seen.add(key)
            BW, BH = sh.BW, sh.BH
            a = math.radians(float(m.get("angle", 0)))
            cx, cy = _mx(m) * BW, float(m.get("_fy0", m["y"])) * BH
            if m["type"] == "write":
                lay = write_layout(dict(m, x=_mx(m)), BW, BH, (210, 69, 47), sh.cfg)
                hw = (lay["x1"] - lay["x0"]) / 2
                hh = lay["bh"] * 0.42
                off = (lay["x0"] + lay["x1"]) / 2 - lay["bw"] / 2
                cx, cy = cx + off * math.cos(a), cy - off * math.sin(a)
            else:
                hw = float(m.get("w", 0.3)) * BW / 2
                hh = float(m.get("h", 0)) * BH / 2 or hw * 0.30
            pts = [(cx + dx * math.cos(a) + dy * math.sin(a), cy - dx * math.sin(a) + dy * math.cos(a))
                   for dx in (-hw, hw) for dy in (-hh, hh)]
            x0, y0, x1, y1 = ob[0] * BW, ob[1] * BH, ob[2] * BW, ob[3] * BH
            oang = float(ob[4]) if len(ob) > 4 else 0.0
            mx, my = 0.06 * (x1 - x0), 0.06 * (y1 - y0)
            name = m.get("text")
            if any(px < x0 + mx - 1 or px > x1 - mx + 1 or py < y0 + my - 1 or py > y1 - my + 1 for px, py in pts):
                fails.append(f"'{name}' is not inside its object with a 6 % margin")
            if m["type"] == "write" and abs(float(m.get("angle", 0)) - oang) > 2.0:
                fails.append(f"'{name}' is at {float(m.get('angle', 0)):.1f} deg, its object at {oang:.1f} deg")
            ix0, iy0 = min(p[0] for p in pts), min(p[1] for p in pts)
            ix1, iy1 = max(p[0] for p in pts), max(p[1] for p in pts)
            for pb in m.get("printed") or []:
                if ix0 < pb[2] * BW and pb[0] * BW < ix1 and iy0 < pb[3] * BH and pb[1] * BH < iy1:
                    fails.append(f"'{name}' crosses printed text")
                    break
    return fails


DEBUG_DIR = None


def hand_over_ink(plan, limit: float = 0.05, mirror: bool = False) -> list[str]:
    """R37: while a hand writes a mark, the hand sprite covers <= 5 % of the ink already laid for that mark (sampled at
    35 / 60 / 85 % of the stroke; the letter under the nib - one glyph, at least 2.5 % of the frame, around the tip - is not counted). mirror=True renders the left hand the engine used before r87 (self-test)."""
    from .draw import HAND_HEIGHT, _hand, hand_kind, hand_path, mark_pen
    from .shots import ImageShot, draw_marks
    fails, seen = [], set()
    red = (210, 69, 47)
    for sh in plan.shots:
        if not isinstance(sh, ImageShot) or not sh.marks:
            continue
        if sh.base is None:
            sh._prepare()
        FW, FH = (sh.full if sh.full else (sh.W, sh.H))
        y_off = sh.y0 if sh.full else 0
        # the marks as they were when written: a "follow" mark sits at its own place (the render may have left it moved
        # with the split), and no stroke / layout cache from the render's last frame
        clean = [{**{k: v for k, v in mm.items() if k not in ("_strokes", "_strokes_WH", "_lay", "_note")},
                  "x": float(mm.get("_fx0", mm.get("x", 0.5))), "y": float(mm.get("_fy0", mm.get("y", 0.5)))}
                 for mm in sh.marks]
        for m in clean:
            if not m.get("hand") or m.get("type") not in ("write", "circle", "underline", "cross", "dash"):
                continue
            at, dur = float(m.get("at", 0.6)), float(m.get("dur", 0.45))
            if dur <= 0.05:
                continue
            worst = 0.0
            for q in (0.35, 0.6, 0.85):
                tt = at + dur * q
                if tt >= sh.duration or tt < 0:
                    continue  # (a mark carried over from the previous shot is checked there)
                pen = mark_pen(clean, tt, sh.BW, sh.BH)
                if not pen:
                    continue
                ftip, t0, t1, kind = pen
                if not (t0 - 1e-3 <= tt <= t1 + 1e-3):
                    continue
                hs = 1.0
                if isinstance(kind, tuple):
                    kind, hs = kind
                _set_clip(sh, tt)
                pos = hand_path(lambda u: sh._screen(*ftip(u), u), t0, t1, tt, FW, FH, mirror)
                if not pos:
                    continue
                z = np.zeros((sh.BH, sh.BW, 3), np.uint8)
                mi = {k: v for k, v in m.items() if k not in ("plate", "note", "note_pre", "_lay")}  # the ink, not its plate
                b = draw_marks(z, [dict(mi)], tt, red, sh.cfg)
                w = draw_marks(np.full_like(z, 255), [dict(mi)], tt, red, sh.cfg)
                ink = (1.0 - (w.astype(np.float32) - b.astype(np.float32)).mean(2) / 255.0) > 0.35
                if ink.sum() < 30:
                    continue
                _p, _s, M = sh._matrix(tt)
                A = getattr(sh, "_cur", None)
                M3 = np.vstack([M, [0, 0, 1]]).astype(np.float64)
                if A is not None and hasattr(sh, "_A"):
                    M3 = M3 @ np.vstack([np.float64(A), [0, 0, 1]])
                scr = cv2.warpAffine(ink.astype(np.uint8), M3[:2].astype(np.float32), (sh.W, sh.H), flags=cv2.INTER_NEAREST)
                frame_ink = np.zeros((FH, FW), np.uint8)
                frame_ink[y_off:y_off + sh.H] = scr
                img, (tx, ty) = _hand(hand_kind(kind), int(min(FW, FH) * HAND_HEIGHT * hs), False)
                if mirror:
                    img = img[:, ::-1]
                    tx = img.shape[1] - 1 - tx
                hx, hy = int(pos[0] - tx), int(pos[1] - ty)
                ha = np.zeros((FH, FW), bool)
                x0, y0 = max(0, hx), max(0, hy)
                x1, y1 = min(FW, hx + img.shape[1]), min(FH, hy + img.shape[0])
                if x1 > x0 and y1 > y0:
                    ha[y0:y1, x0:x1] = img[y0 - hy:y1 - hy, x0 - hx:x1 - hx, 3] > 128
                r_nib = int(0.025 * min(FW, FH))  # the nib on the letter it is forming: not counted
                if m.get("type") == "write":  # (about one glyph of this mark's size)
                    from .shots import write_layout
                    bh_ = float(write_layout(dict(m), sh.BW, sh.BH, red, sh.cfg).get("bh", 0))
                    r_nib = max(r_nib, int(0.6 * bh_ * float(M[0, 0])))
                cv2.circle(frame_ink, (int(pos[0]), int(pos[1])), r_nib, 0, -1)
                n = int(frame_ink.sum())
                if n >= 200:  # (less than 200 px of ink outside the nib zone: nothing readable has been laid yet)
                    cov = float((ha & (frame_ink > 0)).sum()) / n
                    if DEBUG_DIR and cov > limit:
                        dbg = np.zeros((FH, FW, 3), np.uint8)
                        dbg[..., 2] = frame_ink * 255
                        dbg[..., 0] = ha * 160
                        cv2.imwrite(f"{DEBUG_DIR}/hoi_{plan.kind}_{sh.start + tt:.2f}.png", dbg)
                    worst = max(worst, cov)
            if worst > limit:
                key = (m.get("text", m.get("type")), round(sh.start + at, 1))
                if key not in seen:
                    seen.add(key)
                    fails.append(f"{_tc(sh.start + at)} hand covers {worst:.0%} of the ink of '{m.get('text', m.get('type'))}'")
    return fails


def shorts_picture_size(plan, step: float = 0.25) -> list[str]:
    """R38: on every Short frame showing a picture, the picture band is >= 50 % of the frame height."""
    if plan.kind != "short":
        return []
    fails = []
    for sh in plan.shots:
        full = getattr(sh, "full", None)
        if not full:
            continue  # full-frame cards
        if sh.H < 0.5 * full[1] - 1:
            fails.append(f"{_tc(sh.start)} picture band {sh.H} px < {0.5 * full[1]:.0f} px")
    return fails


def shorts_length(plan, limit: float = 45.0) -> list[str]:
    if plan.kind != "short":
        return []
    return [f"Short is {plan.total:.1f} s > {limit:.0f} s"] if plan.total > limit + 1e-6 else []


def count_up(plan, fps: float = 24.0) -> list[str]:
    """R39 (Klot r89): no count-ups - every frame of a number card shows the final value (a wrong number on screen is
    a factual error)."""
    from .shots import StatShot
    fails = []
    for sh in plan.shots:
        if isinstance(sh, StatShot):
            for k in range(max(1, int(sh.duration * fps))):
                v = sh.shown(k / fps)
                if v != sh.final:
                    fails.append(f"{_tc(sh.start + k / fps)} number card shows {v!r}, not {sh.final!r}")
                    break
    return fails


def card_not_empty(plan, fps: float = 12.0) -> list[str]:
    """r87: no frame of a card shows only its background - a stat card has its subline (or its number) from the first
    frame (pixels checked against the bare background), a kinetic card has its first words up."""
    from .shots import KineticShot, StatShot
    fails = []
    for sh in plan.shots:
        if isinstance(sh, StatShot):
            n = max(2, int(sh.duration * fps))
            for k in [0] + list(range(1, n)):
                t = min(sh.duration - 1e-3, k / fps)
                f = sh.frame(t)
                if int((np.abs(f.astype(np.int16) - sh.bg.astype(np.int16)).max(2) > 60).sum()) < 400:
                    fails.append(f"{_tc(sh.start + t)} stat card shows only its background")
                    break
        elif isinstance(sh, KineticShot):
            if not sh.word_boxes(0.0):
                fails.append(f"{_tc(sh.start)} kinetic card opens empty")
    return fails


def _texts(obj, path=""):
    """Every on-screen string of a beat list (i18n.TEXT_KEYS / LIST_KEYS), with where it sits."""
    from .i18n import LIST_KEYS, SKIP_KEYS, TEXT_KEYS
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in SKIP_KEYS or k.startswith("_"):
                continue
            if k in TEXT_KEYS and isinstance(v, str):
                yield f"{path}.{k}", v
            elif k in TEXT_KEYS and isinstance(v, list) and all(isinstance(x, str) for x in v):
                for i, x in enumerate(v):
                    yield f"{path}.{k}[{i}]", x
            elif k in LIST_KEYS and isinstance(v, list):
                for i, x in enumerate(v):
                    if isinstance(x, str):
                        yield f"{path}.{k}[{i}]", x
                    else:
                        yield from _texts(x, f"{path}.{k}[{i}]")
            else:
                yield from _texts(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, x in enumerate(obj):
            yield from _texts(x, f"{path}[{i}]")


def text_lint(beats) -> list[str]:
    """Klot r89: render text style - no space before % ("+5 %"), no lowercase word start on a number card (cards are all
    caps: "over £760k"), no double spaces (the "  ·  " kicker separators excepted), no mix of straight and curly quotes."""
    import re
    fails, all_txt = [], []
    for b in beats or []:
        bid = b.get("id", "?")
        for where, t in _texts(b, bid):
            all_txt.append(t)
            if re.search(r"\d %", t):
                fails.append(f"{where}: space before % in {t!r}")
            if re.search(r"(?<!·) {2,}(?!·)", t):
                fails.append(f"{where}: double space in {t!r}")
        st = (b.get("visual") or {}).get("stat")
        if st:
            dec = int(st.get("decimals", 0))
            final = f"{st.get('prefix', '')}{float(st['value']):,.{dec}f}{st.get('suffix', '')}"
            if re.search(r"(^|\s)[a-z]", final):
                fails.append(f"{bid}: lowercase on the number card {final!r}")
    joined = "\n".join(all_txt)
    if "'" in joined and "\u2019" in joined:
        fails.append("straight (') and curly (\u2019) apostrophes mixed")
    if '"' in joined and ("\u201c" in joined or "\u201d" in joined):
        fails.append('straight (") and curly quotes mixed')
    return fails


def stt_diff(plan, beats) -> tuple[list[str], list[str]]:
    """Klot r89: the narration (voice track) transcribed with faster-whisper and diffed against the script, word by
    word after normalising both (numbers / money / years to words). Any difference blocks the release."""
    from .audio import SR
    from . import sttdiff
    v = plan.timeline.voice
    if not np.any(v):
        return [], ["(no narration audio in this build: transcribed in the CI build)"]
    script = " ".join(str(b.get("text", "")) for b in beats or [])
    heard = sttdiff.transcribe(v, SR)
    return sttdiff.diff(script, heard, STT_KNOWN), [heard]


STT_KNOWN: list = []  # the episode's "stt_known" (set by the build / release checks)


def sfx_sync(plan, lead: float = 0.05, tail: float = 0.08) -> list[str]:
    fails = []
    ink = sorted(plan.ink)
    for a, b, kind in plan.timeline.log:
        if not kind.startswith(SCRATCH):
            continue
        if not any(i0 - lead <= a and b <= i1 + tail for i0, i1 in ink):
            fails.append(f"{_tc(a)} {kind.split(':')[0]} sound {b - a:.2f}s with no ink being laid")
    return fails


def voice_cut_check(plan, sr: int | None = None, win: float = 0.03, thr: float = -45.0) -> tuple[list[str], list[str]]:
    """Returns (failures, every edit point with its levels)."""
    from .audio import SR
    sr = sr or SR
    v = plan.timeline.voice
    n = int(win * sr)
    if not np.any(v):
        return [], ["(no narration audio in this build: checked in the CI build, qc_checks.json)"]
    fails, points = [], []
    for t, what in sorted(plan.timeline.voice_edits):
        i = int(t * sr)
        pre, post = v[max(0, i - n):i], v[i:i + n]
        db = lambda x: 20 * math.log10(float(np.sqrt(np.mean(x.astype(np.float64) ** 2))) + 1e-9) if len(x) else -120.0
        a, b = db(pre), db(post)
        points.append(f"{_tc(t)} {what}: {a:.0f} / {b:.0f} dBFS")
        if a >= thr or b >= thr:
            fails.append(f"{_tc(t)} {what}: {a:.0f} / {b:.0f} dBFS (>= {thr:.0f})")
    return fails, points


def text_stability(plan, fps: float = 24.0) -> list[str]:
    from .shots import KineticShot
    fails = []
    for sh in plan.shots:
        if not isinstance(sh, KineticShot):
            continue
        final = sh.word_boxes(sh.duration + 1)
        for k in range(int(sh.duration * fps)):
            for b in sh.word_boxes(k / fps):
                if b not in final:
                    fails.append(f"{_tc(sh.start + k / fps)} a kinetic word moved")
                    break
    return fails


CHECKS = ("plate_fit", "crop_fit", "jitter_check", "mark_in_frame", "mark_on_object", "hand_over_ink", "shorts_picture_size",
          "shorts_length", "count_up", "card_not_empty", "text_lint", "sfx_sync", "voice_cut_check", "stt_diff",
          "text_stability")


def run_all(plan, cfg, beats, skip=()) -> dict:
    """{check: {"fails": [...], "notes": [...]}} for one video."""
    out = {}
    for name in CHECKS:
        if name in skip:
            out[name] = {"fails": [], "notes": ["skipped"], "skipped": True}
            continue
        try:
            if name == "plate_fit":
                r = plate_fit(plan, cfg)
            elif name == "crop_fit":
                r = crop_fit(plan, beats)
            elif name == "text_lint":
                r = text_lint(beats)
            elif name == "voice_cut_check":
                r, pts = voice_cut_check(plan)
                out[name] = {"fails": r, "notes": pts}
                continue
            elif name == "stt_diff":
                r, heard = stt_diff(plan, beats)
                out[name] = {"fails": r, "notes": heard}
                continue
            else:
                r = globals()[name](plan)
            out[name] = {"fails": r, "notes": []}
        except Exception as e:  # a check that cannot run is a failure, never a silent pass
            out[name] = {"fails": [f"check crashed: {type(e).__name__}: {e}"], "notes": []}
    return out


def table(results: dict) -> str:
    """results: {video: run_all(...)} -> markdown pass/fail table (rows = checks, columns = videos)."""
    vids = list(results)
    md = ["| check | " + " | ".join(vids) + " |", "|---|" + "---|" * len(vids)]
    for c in CHECKS:
        row = []
        for v in vids:
            r = results[v].get(c, {})
            row.append("skip" if r.get("skipped") else ("PASS" if not r.get("fails") else f"FAIL ({len(r['fails'])})"))
        md.append(f"| {c} | " + " | ".join(row) + " |")
    det = []
    for v in vids:
        for c in CHECKS:
            for f in results[v].get(c, {}).get("fails", [])[:40]:
                det.append(f"- {v} · {c}: {f}")
    return "\n".join(md + ([""] + det if det else []))


def failed(results: dict) -> bool:
    return any(r.get("fails") for v in results.values() for r in v.values())


# ---------------------------------------------------------------- R40: every check must catch its planted bug
def selftest(plans: dict, cfg: dict, beats: dict) -> list[dict]:
    """Plant one known bug per check (on a copy of the state, restored after) and run the check on it: each must FAIL.
    Returns [{"check", "planted", "result": "FAIL" (good) | "PASS" (the check is blind) | "ERROR"}]."""
    from types import SimpleNamespace as NS
    from .shots import ClipImageShot, ImageShot, KineticShot, StatShot
    long_ = plans.get("long") or next(iter(plans.values()))
    short = next((p for k, p in plans.items() if k != "long"), None)
    rows = []

    def img_mark(plan, need=lambda m: m.get("type") == "write", clip=False):
        for sh in plan.shots:
            if isinstance(sh, ImageShot) and (clip or not isinstance(sh, ClipImageShot)):
                for m in sh.marks:
                    if need(m):
                        return sh, m
        return None, None

    def run(name, planted, fn):
        try:
            r = fn()
            rows.append({"check": name, "planted": planted, "result": "FAIL" if r else "PASS", "detail": (r or [""])[0]})
        except Exception as e:  # noqa: BLE001
            rows.append({"check": name, "planted": planted, "result": "ERROR", "detail": f"{type(e).__name__}: {e}"})

    def t_plate():
        long_.labels.append((1.0, 2.0, "THIS SOURCE PLATE IS FAR TOO LONG " * 6))
        try:
            return plate_fit(long_, cfg, t_from=1.0, t_to=2.0)
        finally:
            long_.labels.pop()
    run("plate_fit", "source plate wider than the frame (runs off both edges)", t_plate)

    def t_crop():
        sh, m = img_mark(short) if short else (None, None)
        if sh is None:
            return []
        x0 = m["x"]
        m["x"] = 1.35
        try:
            return crop_fit(short, [])
        finally:
            m["x"] = x0
    run("crop_fit", "Short: a mark moved out of the beat's window", t_crop)

    def t_jitter():
        sh, m = img_mark(long_, lambda m: m.get("type") in ("write", "stamp", "circle") and not m.get("follow"))
        orig = sh._screen
        sh._screen = lambda bx, by, t, o=orig: (o(bx, by, t)[0] + 1.5 * math.sin(t * 60.0), o(bx, by, t)[1])
        try:
            return jitter_check(NS(shots=[sh]))
        finally:
            del sh._screen
    run("jitter_check", "a mark shaking +-1.5 px frame to frame", t_jitter)

    def t_inframe():
        sh, m = img_mark(long_)
        x0 = m["x"]
        m["x"] = 1.15
        try:
            return mark_in_frame(NS(shots=[sh]))
        finally:
            m["x"] = x0
    run("mark_in_frame", "a picture mark pushed off the right edge", t_inframe)

    def t_obj():
        sh, m = img_mark(long_, lambda m: bool(m.get("obj")) and m.get("type") == "write")
        x0 = m["x"]
        m["x"] = x0 + 0.25
        m.pop("_fx0", None)
        try:
            return mark_on_object(NS(shots=[sh]))
        finally:
            m["x"] = x0
    run("mark_on_object", "a stub mark moved off the ticket", t_obj)

    def t_hand():
        sh, m = img_mark(long_, lambda m: m.get("type") == "write" and m.get("hand") and float(m.get("dur", 0)) > 0.3
                         and float(m.get("at", 0)) > 0.2)
        return hand_over_ink(NS(shots=[sh], kind=long_.kind), mirror=True)
    run("hand_over_ink", "the left (mirrored) hand of r86 over the letters it wrote", t_hand)

    def t_size():
        sh = next((s for s in (short.shots if short else []) if getattr(s, "full", None)), None)
        if sh is None:
            return []
        h0 = sh.H
        sh.H = int(sh.full[1] * 0.3)
        try:
            return shorts_picture_size(NS(kind="short", shots=[sh]))
        finally:
            sh.H = h0
    run("shorts_picture_size", "Short picture band at 30 % of the frame height", t_size)
    run("shorts_length", "a 50 s Short", lambda: shorts_length(NS(kind="short", total=50.0)))

    def t_count():
        st = next((s for s in long_.shots if isinstance(s, StatShot)), None)
        st.legacy_count = 1.4
        try:
            return count_up(NS(shots=[st]))
        finally:
            st.legacy_count = None
    run("count_up", "an old-style 1.4 s count-up (wrong values on screen)", t_count)

    def t_empty():
        st = next((s for s in long_.shots if isinstance(s, StatShot)), None)
        orig = st.frame
        st.frame = lambda t, o=orig, b=st.bg: b.copy() if t < 1.0 else o(t)
        try:
            return card_not_empty(NS(shots=[st]))
        finally:
            del st.frame
    run("card_not_empty", "a number card blank for its first second", t_empty)

    def t_stt():
        from . import sttdiff
        return sttdiff.diff("Larry pays thirty dollars for the ticket, from hotels to vacation rentals.",
                            "Larry pays $30 for the ticket, from hotels to holiday rentals.")
    run("stt_diff", "the narration says 'holiday' where the script says 'vacation'", t_stt)
    run("text_lint", "\"+5 %\", \"over £760k\", a double space, straight + curly apostrophes",
        lambda: text_lint([{"id": "x", "text": "it's", "visual": {"type": "image", "marks": [{"text": "+5 %"}, {"text": "a  b"},
                                                                                        {"text": "isn\u2019t"}]}},
                           {"id": "y", "text": "", "visual": {"type": "stat", "stat": {"value": 760, "prefix": "over £", "suffix": "k"}}}]))
    run("sfx_sync", "a 0.5 s scratch with no ink being laid",
        lambda: sfx_sync(NS(ink=[], timeline=NS(log=[(1.0, 1.5, "scribble:0.500")]))))

    def t_voice():
        from .audio import SR
        v = np.zeros(int(2 * SR), np.float32)
        v[int(0.9 * SR):int(1.1 * SR)] = 0.3 * np.sin(np.arange(int(0.2 * SR)) * 0.07)
        return voice_cut_check(NS(timeline=NS(voice=v, voice_edits=[(1.0, "planted cut inside a word")])))[0]
    run("voice_cut_check", "an edit point in the middle of a word", t_voice)

    def t_text():
        k = next((s for s in long_.shots if isinstance(s, KineticShot)), None)
        orig = k.word_boxes
        k.word_boxes = lambda t, o=orig: [(b[0] + (40 if t < k.duration / 2 else 0), b[1], b[2] + (40 if t < k.duration / 2 else 0), b[3])
                                          for b in o(t)]
        try:
            return text_stability(NS(shots=[k]))
        finally:
            del k.word_boxes
    run("text_stability", "kinetic words re-centring halfway through the card", t_text)
    return rows


def selftest_table(rows: list[dict]) -> str:
    md = ["| check_selftest | planted bug | result |", "|---|---|---|"]
    for r in rows:
        md.append(f"| {r['check']} | {r['planted']} | {r['result']}{'' if r['result'] == 'FAIL' else ' - BLIND, release blocked'} |")
    missing = [c for c in CHECKS if c not in {r["check"] for r in rows}]
    for c in missing:
        md.append(f"| {c} | (no planted bug) | MISSING - release blocked |")
    return "\n".join(md)


def selftest_ok(rows: list[dict]) -> bool:
    return all(r["result"] == "FAIL" for r in rows) and all(c in {r["check"] for r in rows} for c in CHECKS)
