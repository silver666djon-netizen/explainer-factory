"""Mark / stamp / ledger audit for an episode, on REAL narration timings (timings.json of a render).

python tools/qc/mark_audit.py episodes/<slug> path/to/timings.json [--shorts]

Checks (exceptions are listed with timecodes):
 1. every circle / underline / strike / cross mark carries a labelled target region ("target": [x0,y0,x1,y1],
    picture fractions) and actually lands on it: a circle encloses >= 85 % of its target and is not more than
    4x its area; an underline sits under the target's text line; a strike runs through it; a cross covers it.
 2. every small stamp (stamp hand) presses with its centre inside its target plate (photo, page, print).
 3. nothing (mark, stamp, insert, label) is drawn inside the ledger's safe zone (top-right 18 % x 22 %) while
    the ledger is on screen.
 4. a mark is never written while its target or the mark itself is outside the frame (sampled every frame
    of the writing at 12 fps).
 5. a mark is never written while a subtitle covers its target (or the mark itself), and the full stroke path of a
    visible circle / cross / underline (or a label's box) never runs under a subtitle.
Exit code 1 if anything is listed."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# offline: no image API is ever called. The provider name only makes the cache file names match the CI
# renders, so the audit lays marks out on the real pictures (not on square placeholders).
os.environ.setdefault("OPENROUTER_API_KEY", "audit-offline")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402

import factory.draw as D  # noqa: E402
from factory.build import SAMPLE_RATE, voice_beats  # noqa: E402
from factory.config import load_config  # noqa: E402
from factory.images import ensure_images  # noqa: E402
from factory.archive import ensure_archive, ensure_clips  # noqa: E402
from factory.render import build_plan  # noqa: E402
from factory.script import image_prompts, load_episode  # noqa: E402
from factory.tts import make_voice  # noqa: E402

SAFE = (0.82, 0.0, 1.0, 0.22)


def tc(t):
    return f"{int(t // 60)}:{t % 60:05.2f}"


def check_target(m: dict) -> str | None:
    tg = m.get("target")
    kind = m.get("role") or m.get("type")
    if tg is None:
        return "no target labelled"
    x0, y0, x1, y1 = tg
    mx, my, mw, mh = float(m["x"]), float(m["y"]), float(m.get("w", 0.2)), float(m.get("h", 0.1))
    bx0, by0, bx1, by1 = mx - mw / 2, my - mh / 2, mx + mw / 2, my + mh / 2
    ta = max(1e-9, (x1 - x0) * (y1 - y0))
    ix = max(0.0, min(x1, bx1) - max(x0, bx0))
    iy = max(0.0, min(y1, by1) - max(y0, by0))
    inter = ix * iy
    if kind == "circle":
        if inter / ta < 0.85:
            return f"circle encloses only {inter / ta:.0%} of its target"
        if mw * mh > 4 * ta:
            return f"circle {mw * mh / ta:.1f}x larger than its target"
    elif kind == "strike":
        if not (y0 <= my <= y1) or ix / max(1e-9, x1 - x0) < 0.8:
            return "strike does not run through its target"
    elif kind == "underline":
        if not (y1 - 0.01 <= my <= y1 + 0.05) or ix / max(1e-9, x1 - x0) < 0.6:
            return "underline is not under its target"
    elif kind == "cross":
        if inter / ta < 0.7:
            return f"cross covers only {inter / ta:.0%} of its target"
    return None


def script_marks(ep: dict, shorts: bool):
    beats = [(None, b) for b in ep["beats"]]
    if shorts:
        beats += [(sh["id"], b) for sh in ep.get("shorts") or [] for b in sh["beats"]]
    for sid, b in beats:
        v = b["visual"]
        groups = [("", v.get("marks") or [])]
        if v.get("closeup"):
            groups.append(("closeup", v["closeup"].get("marks") or []))
            groups.append(("after pull-back", v["closeup"].get("back_marks") or []))
        groups.append(("photo", v.get("photo_marks") or []))
        for where, ms in groups:
            for m in ms:
                if m.get("type") in ("circle", "underline", "cross"):
                    yield sid, b["id"], where, m


def build(ep, cfg, timings, shorts):
    T = {b["id"]: b for b in timings["beats"]}
    TXT = {b["text"]: b for b in timings["beats"]}
    cache = ROOT / ".cache" / "images" / ep["slug"]
    images = ensure_images(cfg, image_prompts(ep), cache, True, lambda *a: None)
    from PIL import Image
    fake = [k for k, p in images.items() if Image.open(p).size == (1024, 1024) and os.path.getsize(p) < 80_000]
    if fake and os.environ.get("MARK_AUDIT_ALLOW_PLACEHOLDERS"):  # hand-made stills not in yet: their beats are unchecked
        print(f"mark audit: WARNING placeholders for {', '.join(fake)} - marks on those pictures are NOT verified")
    elif fake:
        raise SystemExit(f"mark audit: no real picture for {', '.join(fake)} (placeholders) - fetch the image cache first")
    images.update(ensure_archive(ep, cfg, cache, lambda *a: None))
    ensure_clips(ep, cache, lambda *a: None)
    voice = make_voice(cfg, True, ep.get("voices"))

    def voiced(beats):
        out = []
        for b in beats:
            r = T.get(b["id"]) if T.get(b["id"], {}).get("text") == b["text"] else TXT.get(b["text"])
            if r:
                out.append({"audio": np.zeros(int(r["voice"] * SAMPLE_RATE), np.float32), "sr": SAMPLE_RATE, "duration": r["voice"],
                            "words": [tuple(w) for w in r["words"]], "speaker": "narrator"})
            else:
                out += voice_beats(voice, [b])
        return out
    lookup = {b["id"]: b for b in ep["beats"]}
    mus = ep.get("music") or {}
    for b in ep["beats"]:
        b["_music"] = b.get("music") or mus.get(b.get("section") or "", mus.get("_default"))
    plans = []
    vb = voiced(ep["beats"])
    W, H = 960, 540
    plan = build_plan(ep["beats"], vb, images, cfg, (W, H), "long", lookup)
    tgt = float(cfg["video"].get("long_min_seconds", 0))
    if tgt and plan.total < tgt:
        plan = build_plan(ep["beats"], vb, images, cfg, (W, H), "long", lookup, min(0.45, (tgt - plan.total) / len(ep["beats"]) + 0.01))
    plans.append(("long", plan))
    if shorts:
        for sh in ep.get("shorts") or []:
            plans.append((sh["id"], build_plan(sh["beats"], voiced(sh["beats"]), images, cfg, (540, 960), "short", lookup)))
    return plans


def main(argv):
    ep_dir, tj = argv[0], argv[1]
    shorts = "--shorts" in argv
    ep = load_episode(ep_dir)
    cfg = load_config(ep.get("config"))
    timings = json.load(open(tj))
    problems = []
    for sid, bid, where, m in script_marks(ep, shorts):
        err = check_target(m)
        if err:
            problems.append((sid or "long", bid, None, f"{m.get('role') or m['type']} {where}: {err}"))
    for name, plan in build(ep, cfg, timings, shorts):
        starts = sorted(plan.beat_starts.items(), key=lambda x: x[1])

        def beat_at(t):
            b = None
            for k, v in starts:
                if v <= t:
                    b = k
            return b
        # 2. stamps: render the frame at each press
        D.STAMP_LOG = []
        for sh in plan.shots:
            for tp in sorted(set(round(float(x), 3) for x in _press_times(sh))):
                if 0 <= tp < sh.duration:
                    sh.frame(tp + 0.01)
        for rec in D.STAMP_LOG:
            if rec["plate"] is None:
                continue
            (cx, cy), (x0, y0, x1, y1) = rec["c"], rec["plate"]
            if not (x0 <= cx <= x1 and y0 <= cy <= y1):
                problems.append((name, "?", None, f"stamp centre ({cx:.2f},{cy:.2f}) outside its plate"))
        print(f"  [{name}] stamp presses checked: {sum(1 for r in D.STAMP_LOG if r["plate"])}")
        D.STAMP_LOG = None
        # 4. writing in frame: the mark box and its target stay inside the frame while the hand writes
        # 5. ... and no subtitle sits on it meanwhile
        Wf, Hf = plan.size
        from factory.render import Overlay
        ov = Overlay(cfg, plan)
        cap_boxes = []
        for cap in plan.captions:
            ci = ov.caption_img(cap, 0)
            ch, cw = ci.shape[:2]
            cap_boxes.append((cap.start, cap.end, (Wf - cw) / 2, ov.cap_y - ch / 2, (Wf + cw) / 2, ov.cap_y + ch / 2))
        for sh in plan.shots:
            if not hasattr(sh, "_screen"):
                continue
            for m in getattr(sh, "marks", None) or []:
                at, dur = float(m.get("at", 0.6)), float(m.get("dur", 0.45))
                if dur <= 0.05 or not m.get("hand") or m.get("type") == "led":
                    continue
                if sh.base is None:
                    sh._prepare()
                boxes = [("mark", float(m.get("x", 0.5)) - float(m.get("w", 0.2)) / 2, float(m.get("y", 0.5)) - float(m.get("h", 0.1)) / 2,
                          float(m.get("x", 0.5)) + float(m.get("w", 0.2)) / 2, float(m.get("y", 0.5)) + float(m.get("h", 0.1)) / 2)]
                if m.get("target"):
                    boxes.append(("target", *m["target"]))
                fy0 = sh.y0 if getattr(sh, "full", None) else 0
                fy1 = fy0 + (sh.H if getattr(sh, "full", None) else Hf)
                tt = max(0.0, at)
                while tt <= min(sh.duration, at + dur):
                    for nm, x0, y0, x1, y1 in boxes:
                        ax, ay = sh._screen(x0 * sh.BW, y0 * sh.BH, tt)
                        bx2, by2 = sh._screen(x1 * sh.BW, y1 * sh.BH, tt)
                        tabs = sh.start + tt
                        for c0, c1, cx0, cy0, cx1, cy1 in cap_boxes:
                            if c0 <= tabs < c1 and ax < cx1 and bx2 > cx0 and ay < cy1 and by2 > cy0 and (nm == "target" or not m.get("target")):
                                problems.append((name, beat_at(tabs), tabs, f"{m.get('type')} '{m.get('text', '')}' written under a subtitle"))
                                break
                        over = max(-ax, fy0 - ay, bx2 - Wf, by2 - fy1)
                        if over > 1:
                            problems.append((name, beat_at(sh.start + tt), sh.start + tt,
                                             f"{m.get('type')} '{m.get('text', '')}' written while its {nm} is outside the frame "
                                             f"({over / Wf:.1%} of the width out)"))
                            tt = 1e9
                            break
                    tt += 1 / 12
        # 5b. the full stroke path of every visible circle / cross / underline (and the box of every written label)
        #     never runs under a subtitle - while it is drawn and while it stays on screen
        import math as _m
        for sh in plan.shots:
            if not hasattr(sh, "_screen"):
                continue
            for m in getattr(sh, "marks", None) or []:
                typ = m.get("type")
                if typ not in ("circle", "cross", "underline", "write") or not str(m.get("text", "x")).strip():
                    continue
                if sh.base is None:
                    sh._prepare()
                x, y = float(m.get("x", 0.5)), float(m.get("y", 0.5))
                w, h = float(m.get("w", 0.2)), float(m.get("h", 0.1))
                if typ == "circle":
                    pts = [(x + w / 2 * _m.cos(a), y + h / 2 * _m.sin(a)) for a in [k * _m.pi / 24 for k in range(48)]]
                elif typ == "cross":
                    pts = [(x - w / 2 + w * f, y - h / 2 + h * f) for f in [k / 12 for k in range(13)]] + \
                          [(x + w / 2 - w * f, y - h / 2 + h * f) for f in [k / 12 for k in range(13)]]
                elif typ == "underline":
                    pts = [(x - w / 2 + w * f, y) for f in [k / 12 for k in range(13)]]
                else:  # written label: its box
                    pts = [(x - w / 2 + w * f, y + dy) for f in [k / 8 for k in range(9)] for dy in (-h / 2, h / 2)]
                at = max(0.0, float(m.get("at", 0.6)))
                until = float(m["until"]) if m.get("until") is not None else sh.duration
                tt = at
                while tt < min(sh.duration, until):
                    tabs = sh.start + tt
                    hit = False
                    for c0, c1, cx0, cy0, cx1, cy1 in cap_boxes:
                        if not (c0 <= tabs < c1):
                            continue
                        for px, py in pts:
                            sx, sy = sh._screen(px * sh.BW, py * sh.BH, tt)
                            if cx0 <= sx <= cx1 and cy0 <= sy <= cy1:
                                hit = True
                                break
                        if hit:
                            break
                    if hit:
                        problems.append((name, beat_at(tabs), tabs, f"{typ} '{m.get('text', '')}' runs under a subtitle"))
                        break
                    tt += 0.25
        # 3. ledger safe zone
        led = plan.ledger
        if led is None:
            continue
        Wf, Hf = plan.size
        sx0, sy0 = SAFE[0] * Wf, SAFE[3] * Hf
        t = 0.0
        while t < plan.total:
            if led.visible(t):
                for sh in plan.shots:
                    if not (sh.start <= t < sh.start + sh.duration):
                        continue
                    for m in getattr(sh, "marks", None) or []:
                        at, dur = float(m.get("at", 0.6)), float(m.get("dur", 0.45))
                        if t - sh.start < at or (m.get("until") is not None and t - sh.start >= float(m["until"])):
                            continue
                        if not hasattr(sh, "_screen"):
                            continue
                        if sh.base is None:
                            sh._prepare()
                        bx, by = float(m.get("x", 0.5)) * sh.BW, float(m.get("y", 0.5)) * sh.BH
                        hw, hh = float(m.get("w", 0.2)) * sh.BW / 2, float(m.get("h", 0.1)) * sh.BH / 2
                        ax, ay = sh._screen(bx - hw, by - hh, t - sh.start)
                        bx2, by2 = sh._screen(bx + hw, by + hh, t - sh.start)
                        if bx2 > sx0 and ay < sy0:
                            problems.append((name, beat_at(t), t, f"{m.get('type')} '{m.get('text', '')}' inside the ledger safe zone"))
                for ins in plan.inserts:
                    if ins.start <= t <= ins.end:
                        x, y, w = float(ins.spec.get("x", 0.5)), float(ins.spec.get("y", 0.5)), float(ins.spec.get("w", 0.34))
                        if x + w / 2 > SAFE[0] and y - w * 0.4 < SAFE[3]:
                            problems.append((name, beat_at(t), t, f"insert {ins.spec.get('file')} inside the ledger safe zone"))
            t += 0.5
    seen, out = set(), []
    for name, bid, t, msg in problems:
        key = (name, bid, msg)
        if key in seen:
            continue
        seen.add(key)
        out.append(f"  {name} {bid}{' at ' + tc(t) if t is not None else ''}: {msg}")
    print(f"mark audit: {len(out)} exception(s)")
    print("\n".join(out))
    return 1 if out else 0


def _press_times(sh):
    """Shot-relative press times of stamp-hand stamps in this shot."""
    out = []
    if hasattr(sh, "tag_at"):  # mugshot
        out.append(sh.tag_at)
    if getattr(sh, "spec", None) and isinstance(sh.spec, dict) and sh.spec.get("open_stamp_at") is not None:
        out.append(float(sh.spec["open_stamp_at"]) + getattr(sh, "lead_in", 0.0))
    if type(sh).__name__ == "ExhibitShot":
        out.append(sh.TAG_AT)
    return out


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
