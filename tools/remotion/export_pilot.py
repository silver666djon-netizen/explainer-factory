"""Remotion pilot (Klot, Ep.4 r90): export 3 beats of the r90 plan as data for the Remotion overlay renderer.

The Python plan of the released r90 (same timings, same marks, same plates) is rebuilt offline; everything the
overlay layer draws is exported as DATA, not pixels: text (lines, font, size, colours, plate fill, padding, stroke) with
its position per frame, the handwritten marks as glyph outlines + centre-line strokes (for a true stroke reveal), the
camera of every picture as parameters, number card / bar chart / kinetic card specs, Larry's Tab rows.
Pictures (the prepared picture, its Shorts backdrop, the card paper) and the r90 audio are exported as files.

python tools/remotion/export_pilot.py <r90 release dir: cs_ep04_r90_*.mp4 + timings.json> <out: pilot/remotion/public>"""
from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools" / "qc"))
os.environ.setdefault("OPENROUTER_API_KEY", "audit-offline")

import cv2  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

FPS = 30
EP = "episodes/0005-drip-pricing"
REG: dict[int, dict] = {}  # id(array) -> description of the text plate it came from
KEEP: list = []  # keep the arrays alive (ids stay unique)
PUB: Path = Path(".")
FONTS: dict[str, str] = {}  # font file -> family name used in the page


def fam(path: str) -> str:
    name = Path(path).stem.replace("_", "-")
    FONTS[Path(path).name] = name
    return name


def col(c):
    if c is None:
        return None
    c = tuple(int(v) for v in c)
    return f"rgba({c[0]},{c[1]},{c[2]},{(c[3] / 255) if len(c) > 3 else 1:.3f})"


def save_png(arr: np.ndarray, prefix: str) -> str:
    h = hashlib.sha1(arr.tobytes()).hexdigest()[:12]
    rel = f"img/{prefix}-{h}.png"
    p = PUB / rel
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(arr).save(p)
    return rel


# ------------------------------------------------------------------ recorder: text plates drawn by the Overlay
def install_recorder():
    import factory.render as R
    import factory.text as T
    tb0 = T.text_block

    def text_block(lines, fnt, fill, stroke_fill=None, stroke=0, box_fill=None, pad=0, line_gap=1.12, align="center", colors=None):
        arr = tb0(lines, fnt, fill, stroke_fill, stroke, box_fill, pad, line_gap, align, colors)
        size = fnt.size
        widths = [fnt.getlength(l) for l in lines]
        h, w = arr.shape[:2]
        asc = fnt.getmetrics()[0]
        out = []
        for i, line in enumerate(lines):
            y = pad + stroke + i * int(size * line_gap)
            x0 = (w - widths[i]) / 2 if align == "center" else pad + stroke
            words = []
            if colors and colors[i]:
                x = x0
                for word, c in zip(line.split(" "), colors[i]):
                    words.append({"t": word, "x": round(x, 2), "c": col(c)})
                    x += fnt.getlength(word + " ")
            out.append({"t": line, "x": round(x0, 2), "base": round(y + asc, 2), "words": words or None})
        d = {"type": "text", "w": w, "h": h, "font": fam(fnt.path), "size": size, "fill": col(fill), "lines": out,
             "stroke": stroke, "strokeFill": col(stroke_fill), "box": col(box_fill), "radius": max(6, size // 5)}
        REG[id(arr)] = d
        KEEP.append(arr)
        return arr
    R.text_block = text_block
    import factory.shots as S
    S.text_block = text_block
    rs0 = cv2.resize

    def resize(src, dsize, *a, **kw):
        out = rs0(src, dsize, *a, **kw)
        if id(src) in REG:
            REG[id(out)] = {"type": "scaled", "of": id(src), "sx": out.shape[1] / src.shape[1], "sy": out.shape[0] / src.shape[0]}
            KEEP.append(out)
        return out
    cv2.resize = resize
    ci0 = R.Overlay.card_img

    def card_img(self, card):
        key = ("k", id(card))
        fresh = key not in self.cache
        arr = ci0(self, card)
        if fresh:
            inner = next(d for k, d in reversed(list(REG.items())) if d.get("type") == "text")
            fw = max(6, inner["size"] // 9)
            REG[id(arr)] = {"type": "card", "inner": inner, "frame": fw, "angle": -2.0, "w": arr.shape[1], "h": arr.shape[0],
                            "paper": col(self.pal["paper"] + (255,)), "red": col(self.pal["red"] + (255,))}
            KEEP.append(arr)
        return arr
    R.Overlay.card_img = card_img


def record_ops(plan, cfg, times):
    """Overlay ops per frame: [(element key, x, y, opacity, scale)] - the same layout code as the r90 render."""
    import factory.render as R
    ov = R.Overlay(cfg, plan)
    W, H = plan.size
    blank = np.zeros((H, W, 3), np.uint8)
    elements, frames = {}, []
    b0 = R.blend
    cur = []

    def blend(frame, rgba, x, y, opacity=1.0):
        d = REG.get(id(rgba))
        sc = 1.0
        while d is not None and d.get("type") == "scaled":
            sc *= d["sx"]
            d = REG.get(d["of"])
        if d is None:
            key = "raw:" + save_png(np.ascontiguousarray(rgba), "raw")
            elements[key] = {"type": "raw", "src": key[4:], "w": rgba.shape[1], "h": rgba.shape[0]}
            cur.append([key, int(x), int(y), round(float(opacity), 3), 1.0])
            return
        key = hashlib.sha1(json.dumps(d, sort_keys=True).encode()).hexdigest()[:10]
        elements[key] = d
        cur.append([key, int(x), int(y), round(float(opacity), 3), round(sc, 4)])
    R.blend = blend
    ledger = plan.ledger
    plan.ledger = None  # Larry's Tab is exported on its own (export_ledger)
    caps = plan.captions
    try:
        for t in times:
            cur = []
            ci = next((i for i, c in enumerate(caps) if c.start <= t < c.end), len(caps))
            cards = plan.cards
            ki = next((i for i, c in enumerate(cards) if c.start <= t < c.end), len(cards))
            ov.apply(blank, t, ci, ki, len(plan.bubbles))
            frames.append(cur)
    finally:
        R.blend = b0
        plan.ledger = ledger
    return elements, frames


# ------------------------------------------------------------------ handwriting: glyph outlines + centre lines
def glyph_outline(text: str, font_path: str, size: int):
    """SVG path (y down, origin = pen start on the baseline) and the advance width of the text."""
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.transformPen import TransformPen
    from fontTools.ttLib import TTFont
    ft = TTFont(font_path)
    gs = ft.getGlyphSet()
    cmap = ft.getBestCmap()
    upm = ft["head"].unitsPerEm
    s = size / upm
    pen = SVGPathPen(gs)
    x = 0.0
    for ch in text:
        g = cmap.get(ord(ch))
        if g is None:
            continue
        tp = TransformPen(pen, (s, 0, 0, -s, x, 0))
        gs[g].draw(tp)
        x += gs[g].width * s
    return pen.getCommands(), x


def raster_path(d: str, w: int, h: int, ox: float, oy: float, k: int = 4) -> np.ndarray:
    """Even-odd raster of an SVG path made of M/L/Q/C/Z commands (fontTools output) at k x scale."""
    import re
    toks = re.findall(r"[MLQCZHV]|-?\d*\.?\d+(?:e-?\d+)?", d)
    polys, cur, i, last = [], [], 0, (0.0, 0.0)
    cmd = None

    def P(a, b):
        return ((a + ox) * k, (b + oy) * k)
    while i < len(toks):
        tk = toks[i]
        if tk in "MLQCZHV":
            cmd = tk
            i += 1
            if cmd == "Z":
                if cur:
                    polys.append(cur)
                cur = []
            continue
        if cmd == "M":
            if cur:
                polys.append(cur)
            last = (float(toks[i]), float(toks[i + 1]))
            cur = [P(*last)]
            i += 2
            cmd = "L"
        elif cmd == "L":
            last = (float(toks[i]), float(toks[i + 1]))
            cur.append(P(*last))
            i += 2
        elif cmd == "H":
            last = (float(toks[i]), last[1])
            cur.append(P(*last))
            i += 1
        elif cmd == "V":
            last = (last[0], float(toks[i]))
            cur.append(P(*last))
            i += 1
        elif cmd == "Q":
            c1 = (float(toks[i]), float(toks[i + 1]))
            e = (float(toks[i + 2]), float(toks[i + 3]))
            for u in np.linspace(0, 1, 9)[1:]:
                q = ((1 - u) ** 2 * last[0] + 2 * (1 - u) * u * c1[0] + u * u * e[0],
                     (1 - u) ** 2 * last[1] + 2 * (1 - u) * u * c1[1] + u * u * e[1])
                cur.append(P(*q))
            last = e
            i += 4
        elif cmd == "C":
            c1 = (float(toks[i]), float(toks[i + 1]))
            c2 = (float(toks[i + 2]), float(toks[i + 3]))
            e = (float(toks[i + 4]), float(toks[i + 5]))
            for u in np.linspace(0, 1, 11)[1:]:
                q = tuple((1 - u) ** 3 * last[j] + 3 * (1 - u) ** 2 * u * c1[j] + 3 * (1 - u) * u * u * c2[j] + u ** 3 * e[j] for j in (0, 1))
                cur.append(P(*q))
            last = e
            i += 6
        else:
            i += 1
    if cur:
        polys.append(cur)
    acc = np.zeros((h * k, w * k), np.uint8)
    for poly in polys:
        if len(poly) < 3:
            continue
        m = Image.new("L", (w * k, h * k), 0)
        ImageDraw.Draw(m).polygon(poly, fill=1)
        acc ^= np.array(m)
    return acc


def centre_lines(mask: np.ndarray, k: int) -> tuple[list[list[list[float]]], float]:
    """Pen strokes along the middle of the ink (pixel coords / k), in writing order: glyph by glyph left to right.
    The skeleton is turned into a graph (junction clusters = nodes), spurs shorter than the pen are pruned, and each
    stroke runs on through a junction along the straightest way - the way a pen goes through a letter."""
    from skimage.morphology import skeletonize
    m = cv2.GaussianBlur(mask.astype(np.float32), (0, 0), k * 1.2) > 0.5  # ragged marker edges make spurs
    dist = cv2.distanceTransform(m.astype(np.uint8), cv2.DIST_L2, 5)
    width = float(np.percentile(dist[m], 95) * 2) if m.any() else 4.0
    sk = skeletonize(m)
    P = set(zip(*[a.tolist() for a in np.nonzero(sk)]))
    N8 = [(a, b) for a in (-1, 0, 1) for b in (-1, 0, 1) if a or b]
    nb = lambda p: [(p[0] + a, p[1] + b) for a, b in N8 if (p[0] + a, p[1] + b) in P]
    deg = {p: len(nb(p)) for p in P}
    junc = {p for p in P if deg[p] >= 3}
    # junction clusters -> one node each
    node_of, nodes = {}, []
    for p in junc:
        if p in node_of:
            continue
        stack, cl = [p], []
        node_of[p] = len(nodes)
        while stack:
            q = stack.pop()
            cl.append(q)
            for r in nb(q):
                if r in junc and r not in node_of:
                    node_of[r] = len(nodes)
                    stack.append(r)
        nodes.append(cl)
    for p in P:
        if deg[p] <= 1 and p not in node_of:
            node_of[p] = len(nodes)
            nodes.append([p])
    # edges: pixel chains between nodes
    edges, seen = [], set()
    for ni, cl in enumerate(nodes):
        for q in cl:
            for r in nb(q):
                if r in node_of or (q, r) in seen:
                    continue
                chain, prev, cur = [q, r], q, r
                seen.add((q, r))
                while cur not in node_of:
                    nxt = [x for x in nb(cur) if x != prev and x not in chain[-3:]]
                    if not nxt:
                        break
                    prev, cur = cur, nxt[0]
                    chain.append(cur)
                if cur in node_of:
                    seen.add((cur, chain[-2]))
                edges.append([ni, node_of.get(cur, -1), chain])
    # closed loops with no node ("0", "O")
    covered = {p for e in edges for p in e[2]} | set(node_of)
    for p in sorted(P - covered):
        if p in covered:
            continue
        chain, prev, cur = [p], None, p
        while True:
            nxt = [x for x in nb(cur) if x != prev and x not in covered]
            covered.add(cur)
            if not nxt:
                break
            prev, cur = cur, nxt[0]
            chain.append(cur)
        chain.append(chain[0])
        edges.append([-2, -2, chain])
    L = lambda c: float(np.sum(np.hypot(*np.diff(np.array(c, np.float32), axis=0).T))) if len(c) > 1 else 0.0
    ndeg = lambda: {i: sum((e[0] == i) + (e[1] == i) for e in edges) for i in range(len(nodes))}
    for _ in range(3):  # prune spurs
        d_ = ndeg()
        keep = []
        for e in edges:
            spur = e[0] >= 0 and e[1] >= 0 and (d_.get(e[0], 0) == 1 or d_.get(e[1], 0) == 1) and not (d_.get(e[0], 0) == 1 and d_.get(e[1], 0) == 1)
            if spur and L(e[2]) < width * 0.75:
                continue
            keep.append(e)
        if len(keep) == len(edges):
            break
        edges = keep
    # glyph = connected component of the ink
    n, lab = cv2.connectedComponents(m.astype(np.uint8))
    comp = lambda c: lab[c[len(c) // 2][0], c[len(c) // 2][1]]
    by_comp = {}
    for e in edges:
        by_comp.setdefault(comp(e[2]), []).append(e)
    left = {c: min(p[1] for e in es for p in e[2]) for c, es in by_comp.items()}
    strokes = []
    for c in sorted(by_comp, key=lambda c: left[c]):
        es = by_comp[c]
        used = [False] * len(es)
        d_ = {}
        for e in es:
            for x in e[:2]:
                if x >= 0:
                    d_[x] = d_.get(x, 0) + 1
        while not all(used):
            # start: an unused edge end at a free end (degree 1) if any, top-left first
            cands = []
            for i, e in enumerate(es):
                if used[i]:
                    continue
                for end, node in ((0, e[0]), (1, e[1])):
                    pt = e[2][0] if end == 0 else e[2][-1]
                    free = 0 if (node >= 0 and d_.get(node, 0) == 1) or node == -1 else 1
                    cands.append((free, pt[0] + pt[1] * 0.5, i, end))  # top first, then left
            _, _, i, end = min(cands)
            path = list(es[i][2] if end == 0 else es[i][2][::-1])
            node = es[i][1] if end == 0 else es[i][0]
            used[i] = True
            while node >= 0:
                v_in = np.array(path[-1], np.float32) - np.array(path[max(0, len(path) - 6)], np.float32)
                best = None
                for j, e in enumerate(es):
                    if used[j] or node not in e[:2]:
                        continue
                    c2 = e[2] if e[0] == node else e[2][::-1]
                    v_out = np.array(c2[min(5, len(c2) - 1)], np.float32) - np.array(c2[0], np.float32)
                    cosv = float(np.dot(v_in, v_out) / (np.linalg.norm(v_in) * np.linalg.norm(v_out) + 1e-6))
                    if best is None or cosv > best[0]:
                        best = (cosv, j, c2, e[1] if e[0] == node else e[0])
                if best is None or best[0] < -0.2:  # a sharp turn back: the pen lifts
                    break
                used[best[1]] = True
                path += best[2]
                node = best[3]
            arr = np.array([[q[1], q[0]] for q in path], np.float32) / k
            if len(arr) > 3:
                arr = cv2.approxPolyDP(arr.reshape(-1, 1, 2), 0.3, False).reshape(-1, 2)
            strokes.append([[round(float(x), 2), round(float(y), 2)] for x, y in arr])
    return strokes, width / k


def export_write(m: dict, BW: int, BH: int, cfg: dict) -> dict:
    """A handwritten mark: glyph path + centre lines, in its box (box px), with the box's place on the picture."""
    from factory.config import hex_to_rgb, resolve_font
    from factory.shots import write_layout
    from factory.text import font
    pal = {k: hex_to_rgb(v) for k, v in cfg["style"]["palette"].items()}
    red = pal["red"]
    lay = write_layout(m, BW, BH, red, cfg)
    bw, bh = lay["bw"], lay["bh"]
    path = resolve_font(cfg["fonts"].get(m.get("font", "marker")) or cfg["fonts"]["marker"])
    txt = str(m["text"])
    if m.get("fs"):
        size = max(8, int(float(m["fs"]) * BH))
    else:
        size = int(bh * 0.92)
        while size > 8 and font(path, size).getlength(txt) > bw * 0.94:
            size -= 1
    fnt = font(path, size)
    tw = fnt.getlength(txt)
    tx = bw * 0.03 if m.get("align") == "left" else (bw - tw) / 2
    asc, desc = fnt.getmetrics()
    base = bh / 2 + (asc - desc) / 2  # PIL anchor "lm": the middle of ascender..descender sits at bh/2
    d, adv = glyph_outline(txt, path, size)
    k = 4
    mask = raster_path(d, bw, bh, tx, base, k)
    strokes, width = centre_lines(mask, k)
    c = m.get("color", "red")
    c = pal.get(c) or (hex_to_rgb(c) if str(c).startswith("#") else red)
    return {"text": txt, "x": float(m.get("x", 0.5)) * BW, "y": float(m.get("y", 0.5)) * BH, "bw": bw, "bh": bh,
            "angle": float(m.get("angle", 0)), "path": d, "ox": round(tx, 2), "oy": round(base, 2), "strokes": strokes,
            "pen": round(max(2.0, width * 1.35), 2), "color": col(tuple(c) + (255,)), "at": float(m.get("at", 0.6)),
            "dur": float(m.get("dur", 0.45)), "hand": bool(m.get("hand")), "chain": bool(m.get("chain")),
            "handScale": float(m.get("hand_scale", 1.0)), "kind": m.get("type")}


def hand_sprite(kind: str, height: int) -> dict:
    import factory.draw as D
    img, (tx, ty) = D._hand(D.hand_kind(kind), height, False)
    return {"src": save_png(img, f"hand-{kind}"), "w": img.shape[1], "h": img.shape[0], "tx": tx, "ty": ty}


# ------------------------------------------------------------------ shots
def export_shot(sh, cfg, size):
    from factory.shots import ChartShot, ImageShot, KineticShot, StatShot
    import factory.draw as D
    W, H = size
    base = {"start": sh.start, "duration": sh.duration}
    if isinstance(sh, ImageShot):
        if sh.base is None:
            sh._prepare()
        o = {**base, "type": "image", "img": save_png(sh.base, "pic"), "BW": sh.BW, "BH": sh.BH, "W": sh.W, "H": sh.H,
             "y0": int(getattr(sh, "y0", 0)) if sh.full else 0, "full": bool(sh.full), "motion": sh.motion, "zmax": sh.zmax,
             "zoomLin": list(getattr(sh, "zoom_lin", None) or []) or None, "camDy": float(getattr(sh, "cam_dy", 0.0)),
             "bg": save_png(sh.bg, "bg") if sh.full and getattr(sh, "bg", None) is not None else None, "marks": [], "hands": {}}
        Hh = min(W, H)
        from factory.shots import mark_strokes
        for i, m in enumerate(sh.marks or []):
            if m.get("type") == "write":
                e = export_write(m, sh.BW, sh.BH, cfg)
            elif m.get("type") in ("circle", "underline", "strike", "cross", "arrow"):
                st = mark_strokes(m, sh.BW, sh.BH, seed=17 + i)
                e = {"kind": m["type"], "strokes": [[[round(float(x), 2), round(float(y), 2)] for x, y in s_] for s_ in st],
                     "pen": max(4, int(min(sh.BW, sh.BH) * 0.007)), "color": col(tuple(sh.red) + (255,)),
                     "at": float(m.get("at", 0.6)), "dur": float(m.get("dur", 0.45)), "hand": bool(m.get("hand")),
                     "chain": bool(m.get("chain")), "handScale": float(m.get("hand_scale", 1.0))}
            else:
                raise SystemExit(f"pilot: mark type {m.get('type')} not ported")
            e["penKind"] = D.pen_for(m)
            e["until"] = m.get("until")
            e["fadeAfter"] = m.get("fade_after")
            o["marks"].append(e)
            if e["hand"]:
                kind = D.pen_for(m)
                if kind not in o["hands"]:
                    o["hands"][kind] = hand_sprite(kind, int(Hh * D.HAND_HEIGHT * e["handScale"]))
        return o
    if isinstance(sh, StatShot):
        lab = sh.label
        return {**base, "type": "stat", "bg": save_png(sh.bg, "sun"), "num": sh.final, "numEl": REG[id(sh._num_img(sh.final))], "numFont": fam(sh.head),
                "numSize": int(sh.H * (0.26 if sh.W > sh.H else 0.14)), "numStroke": max(4, sh.H // 160),
                "red": col(sh.pal["red"] + (255,)), "ink": col(sh.pal["ink"] + (255,)), "pop": sh.POP,
                "label": REG.get(id(lab)) if lab is not None else None, "numH": sh._num_h}
    if isinstance(sh, ChartShot):
        from factory.text import fit_font
        title = sh.spec.get("title", "")
        paper = np.full((sh.H, sh.W, 3), sh.pal["paper"], np.uint8)
        from factory.shots import add_grain
        tf, tl = fit_font(title.upper(), sh.head, int(sh.W * 0.86), int(sh.H * 0.16), start=int(sh.H * 0.09))
        import factory.shots as S_
        from factory.text import font as _font
        tblk = S_.text_block(tl, tf, fill=sh.pal["ink"])
        lf_ = _font(sh.body, max(18, int(min(sh.W, sh.H) * 0.04)))
        vf_ = _font(sh.head, max(22, int(min(sh.W, sh.H) * 0.06)))
        return {**base, "type": "chart", "bg": save_png(add_grain(paper, float(cfg["style"].get("grain", 0)), 11), "paper"),
                "title": {**REG[id(tblk)], "x": (sh.W - tblk.shape[1]) // 2, "y": int(sh.H * 0.05)},
                "labAsc": lf_.getmetrics()[0], "valDesc": vf_.getmetrics()[1],
                "area": list(sh.area), "grow": sh.grow_time, "labels": sh.spec["labels"], "values": sh.spec["values"],
                "fmt": [sh._fmt(float(v)) for v in sh.spec["values"]], "highlight": sh.spec.get("highlight"),
                "labFont": fam(sh.body), "labSize": max(18, int(min(sh.W, sh.H) * 0.04)), "valFont": fam(sh.head),
                "valSize": max(22, int(min(sh.W, sh.H) * 0.06)), "axisW": max(3, sh.H // 300),
                "pal": {k: col(v + (255,)) for k, v in sh.pal.items()}}
    if isinstance(sh, KineticShot):
        items = []
        for img, x, y, appear in sh.items:
            items.append({**REG[id(img)], "x": x, "y": y, "appear": appear})
        return {**base, "type": "kinetic", "bg": save_png(sh.bg, "kin"), "items": items}
    raise SystemExit(f"pilot: shot {type(sh).__name__} not ported")


def export_ledger(lg, cfg, times):
    """Larry's Tab: the card's texture + rows, its place / size / opacity per frame (same state machine as r90)."""
    from factory.devices import _aged_paper, _typew
    from factory.config import resolve_font
    from factory.draw import ease
    import factory.draw as D
    if lg is None or not lg.rows:
        return None
    from factory.text import font as _font
    rows = []
    rh = lg.row_h
    lf = _font(_typew(cfg), int(rh * 0.44))
    tf = _font(_typew(cfg), int(rh * 0.52))
    head_h = int(rh * 1.45)
    for k, r in enumerate(lg.rows):
        lab, wr, x, y = lg.items[k]
        mf = resolve_font(cfg["fonts"]["marker"])
        size = int(rh * 0.70)
        d, adv = glyph_outline(r["amount"], mf, size)
        bw, bh = wr.w, wr.h
        ox, oy = size * 0.2, size * 0.1 + __import__("factory.text", fromlist=["font"]).font(mf, size).getmetrics()[0]
        mask = raster_path(d, bw, bh, ox, oy, 4)
        strokes, width = centre_lines(mask, 4)
        rows.append({"label": r["label"], "amount": r["amount"], "at": r["at"], "dur": lg._wd(r), "chain": bool(r.get("chain")),
                     "loss": bool(r.get("loss")), "ax": x, "ay": y, "bw": bw, "bh": bh, "path": d, "ox": ox, "oy": oy,
                     "strokes": strokes, "pen": round(max(2.0, width * 1.35), 2), "labY": y + int(rh * 0.12) + int(rh * 0.30) + lf.getmetrics()[0], "labX": int(lg.cw * 0.06),
                     "labSize": int(rh * 0.44), "boldSize": int(rh * 0.62),
                     "boldBase": y + int(rh * 0.62) * 0.1 + _font(resolve_font(cfg["fonts"]["body"]), int(rh * 0.62)).getmetrics()[0],
                     "boldX": x + int(rh * 0.62) * 0.2, "color": col((lg.pal["red"] if r.get("loss") else lg.pal["ink"]) + (255,))})
    states = []
    for t in times:
        if not lg.visible(t):
            states.append(None)
            continue
        g, cur = lg._state(t)
        a = min(1.0, (t - lg.rows[0]["at"] + 0.3) / 0.3)
        w = lg.small_w + (lg.cw - lg.small_w) * g  # float: the card scales smoothly
        kk = w / lg.cw
        x = lg.W - lg.margin - w
        y = lg.margin + (1 - ease(a)) * -lg.ch * kk * 0.5
        states.append([round(x, 3), round(y, 3), round(kk, 5), round(ease(a), 4), round(g, 4), cur])
    pal = {k: col(v + (255,)) for k, v in lg.pal.items()}
    paper = _aged_paper(lg.cw, lg.ch, 31)
    tape = lg.tape
    return {"cw": lg.cw, "ch": lg.ch, "rowH": rh, "headH": head_h, "paper": save_png(np.ascontiguousarray(paper), "tabpaper"),
            "tape": save_png(tape, "tape"), "title": lg.items and __import__("factory.i18n", fromlist=["ui"]).ui("LARRY'S TAB"),
            "titleSize": int(rh * 0.52), "titleX": int(lg.cw * 0.06), "titleBase": int(rh * 0.36) + tf.getmetrics()[0], "typew": fam(_typew(cfg)), "marker": fam(resolve_font(cfg["fonts"]["marker"])),
            "body": fam(resolve_font(cfg["fonts"]["body"])), "pal": pal, "rows": rows, "states": states,
            "hand": hand_sprite(lg.hand_kind, int(min(lg.W, lg.H) * D.HAND_HEIGHT * lg.hand_scale)), "from": lg.hand_from}


# ------------------------------------------------------------------ pieces
def build_plans(rel: Path):
    import mark_audit as MA
    import factory.render as R
    from factory.config import load_config
    from factory.script import load_episode
    _bp = R.build_plan

    def big(beats, vb, images, cfg_, size, kind, lookup, *r):
        return _bp(beats, vb, images, cfg_, (1920, 1080) if kind == "long" else (1080, 1920), kind, lookup, *r)
    MA.build_plan = big
    os.chdir(ROOT)
    ep = load_episode(EP)
    cfg = load_config(ep.get("config"))
    import factory.draw as D
    D.set_hand_style(cfg)
    for sh in ep.get("shorts") or []:
        if sh.get("hook"):
            sh["beats"][0]["on_screen"] = sh["hook"]
            sh["beats"][0]["_hook"] = True
    T = json.load(open(rel / "timings.json"))
    plans = dict(MA.build(ep, cfg, T, True))
    # x5 has no Short: a one-beat Short of it, voiced from the r90 timings (its audio comes from the long video)
    lookup = {b["id"]: b for b in ep["beats"]}
    x5 = [lookup["x5"]]
    tb = next(b for b in T["beats"] if b["id"] == "x5")
    from factory.build import SAMPLE_RATE
    vb = [{"audio": np.zeros(int(tb["voice"] * SAMPLE_RATE), np.float32), "sr": SAMPLE_RATE, "duration": tb["voice"],
           "words": [tuple(w) for w in tb["words"]], "speaker": "narrator"}]
    images = MA.ensure_images(cfg, MA.image_prompts(ep), ROOT / ".cache" / "images" / ep["slug"], True, lambda *a: None)
    plans["x5short"] = _bp(x5, vb, images, cfg, (1080, 1920), "short", lookup)
    return ep, cfg, plans


def beat_window(plan, bid):
    st = sorted(plan.beat_starts.items(), key=lambda x: x[1])
    i = [k for k, _ in st].index(bid)
    t0 = st[i][1]
    t1 = st[i + 1][1] if i + 1 < len(st) else plan.total
    return t0, t1


def main(rel: str, out: str) -> int:
    global PUB
    rel_p, PUB = Path(rel).resolve(), Path(out).resolve()
    PUB.mkdir(parents=True, exist_ok=True)
    install_recorder()
    ep, cfg, plans = build_plans(rel_p)
    L = plans["long"]
    ts = lambda a, b: (a, b)
    pieces = {
        "beat1_long": ("long", "long", [ts(0.0, L.beat_starts["o4"])]),
        "beat2_long": ("long", "long", [beat_window(L, "b2"), beat_window(L, "b6")]),
        "beat3_long": ("long", "long", [beat_window(L, "x5"), beat_window(L, "l4")]),
        "beat1_short": ("s1", "s1", [ts(0.0, plans["s1"].beat_starts["s1_3"])]),
        "beat2_short": ("s3", "s3", [beat_window(plans["s3"], "s3_1"), beat_window(plans["s3"], "s3_6")]),
        "beat3_short": (None, None, None),
    }
    xs0, xs1 = beat_window(plans["x5short"], "x5")
    lx0, _ = beat_window(L, "x5")
    pieces["beat3_short"] = [("x5short", "long", [(xs0, xs1)], lx0 - xs0), ("s6", "s6", [beat_window(plans["s6"], "s6_2")], 0.0)]
    index = {}
    for name, spec in pieces.items():
        parts = spec if isinstance(spec, list) else [(spec[0], spec[1], spec[2], 0.0)]
        segs = []
        for pname, video, wins, audio_shift in parts:
            plan = plans[pname]
            W, H = plan.size
            for k, (a, b) in enumerate(wins):
                n = int(round((b - a) * FPS))
                times = [a + f / FPS for f in range(n)]
                shots = [s for s in plan.shots if s.start < b and s.start + s.duration > a]
                elements, ops = record_ops(plan, cfg, times)
                seg = {"plan": pname, "t0": a, "t1": b, "frames": n, "shots": [export_shot(s, cfg, plan.size) for s in shots],
                       "elements": elements, "ops": ops, "punches": [p for p in plan.punches if a - 1 <= p <= b],
                       "ledger": export_ledger(plan.ledger, cfg, times)}
                src = sorted(rel_p.glob(f"cs_*_{video}.mp4"))[0]
                wav = f"audio/{name}_{len(segs)}.wav"
                (PUB / "audio").mkdir(exist_ok=True)
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{a + audio_shift:.3f}", "-t", f"{n / FPS:.3f}", "-i", str(src),
                                "-vn", "-ac", "2", "-ar", "48000", str(PUB / wav)], check=True)
                seg["audio"] = wav
                seg["video"] = src.name
                seg["videoT0"] = a + audio_shift
                seg["letterbox"] = pname == "x5short"  # no r90 Short of x5: the side by side shows the long video
                segs.append(seg)
        W, H = plans[parts[0][0]].size
        v = float(cfg["style"].get("vignette", 0.18))
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        rr = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) / math.sqrt(2)
        va = np.zeros((H, W, 4), np.uint8)
        va[..., 3] = np.round(255 - (255 * (1 - v * np.clip(rr, 0, 1) ** 2.2)).astype(np.uint16)).astype(np.uint8)
        piece = {"name": name, "W": W, "H": H, "fps": FPS, "vignette": save_png(va, "vig"),
                 "segments": segs, "fonts": FONTS}
        (PUB / f"{name}.json").write_text(json.dumps(piece))
        index[name] = {"W": W, "H": H, "frames": sum(s["frames"] for s in segs),
                       "segments": [[s["video"], s["videoT0"], s["frames"], s["letterbox"]] for s in segs]}
        print(name, W, H, index[name]["frames"], "frames", sum(len(s["elements"]) for s in segs), "text elements")
    (PUB / "pieces.json").write_text(json.dumps(index, indent=1))
    (PUB / "fonts").mkdir(exist_ok=True)
    for f in FONTS:
        src = ROOT / "assets" / "fonts" / f
        if src.exists():
            (PUB / "fonts" / f).write_bytes(src.read_bytes())
    print("fonts:", FONTS)
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:3]))
