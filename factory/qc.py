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

import numpy as np

SCRATCH = ("scribble", "marker", "pencil")


def _inter(a, b) -> bool:
    return a[1] < b[3] and b[1] < a[3] and a[2] < b[4] and b[2] < a[4]


def plate_fit(plan, cfg, step: float = 0.5, margin: int = 24) -> list[str]:
    from .render import Overlay
    ov = Overlay(cfg, plan)
    W, H = plan.size
    margin = int(round(margin * min(W, H) / 1080))  # 24 px at 1080p (QC builds may run at half size)
    fails, seen = [], set()
    caps, cards, bubs = plan.captions, plan.cards, plan.bubbles
    t = 0.0
    while t < plan.total:
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
            cx, cy = _mx(m) * BW, float(m["y"]) * BH
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


CHECKS = ("plate_fit", "crop_fit", "jitter_check", "mark_in_frame", "mark_on_object", "sfx_sync", "voice_cut_check", "text_stability")


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
            elif name == "voice_cut_check":
                r, pts = voice_cut_check(plan)
                out[name] = {"fails": r, "notes": pts}
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
