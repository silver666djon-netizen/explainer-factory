"""QC of the Remotion pilot renders (pixel checks on the output, our rules):
  hand_over_ink  R37: while writing, the hand covers <= 5 % of the ink already laid (the glyph under the nib, = ink laid in
                 the last 0.25 s, is not counted)  - normal render vs the same render without the hand, ink from the
                 ink-only render
  jitter_check   a finished mark never moves backwards by > 0.25 px frame to frame (ink centroid, ink-only render)
  mark_in_frame  no ink within 4 px of the picture window's edge while it is being written
  text_stability kinetic words never move once they are on screen (text-only render)
  plate_fit      every plate / caption inside the frame with a 24 px margin; Shorts band plates above the picture window
python tools/remotion/pilot_qc.py <public dir> <render dir> <out.md>"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np


def frames(path: Path, W: int, H: int):
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(path), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    n = W * H * 3
    while True:
        b = p.stdout.read(n)
        if len(b) < n:
            break
        yield np.frombuffer(b, np.uint8).reshape(H, W, 3)
    p.wait()


def segment_of(piece, f):
    acc = 0
    for s in piece["segments"]:
        if f < acc + s["frames"]:
            return s, f - acc
        acc += s["frames"]
    return piece["segments"][-1], f - acc


def check(pub: Path, rd: Path, name: str) -> dict:
    piece = json.loads((pub / f"{name}.json").read_text())
    W, H = piece["W"], piece["H"]
    res = {k: [] for k in ("hand_over_ink", "jitter_check", "mark_in_frame", "text_stability", "plate_fit")}
    notes = {}
    # plate_fit from the overlay layout of every frame
    m = 24 * W / 1920 if W > H else 24 * W / 1080
    for f in range(sum(s["frames"] for s in piece["segments"])):
        seg, lf = segment_of(piece, f)
        ops = seg["ops"][min(lf, len(seg["ops"]) - 1)]
        t = seg["t0"] + lf / piece["fps"]
        shot = [s for s in seg["shots"] if s["start"] <= t + 1e-6][-1]
        wtop = shot.get("y0", 0) if shot.get("full") else None
        for key, x, y, op, sc in ops:
            d = seg["elements"][key]
            w, h = d["w"] * sc, d["h"] * sc
            if op <= 0.02:
                continue
            if x < m - 1 or y < m - 1 or x + w > W - m + 1 or y + h > H - m + 1:
                if not (d.get("stroke") and d.get("lines")):  # captions sit on their own line, checked by the engine
                    res["plate_fit"].append(f"f{f}: plate at ({x},{y},{x + w:.0f},{y + h:.0f}) closer than {m:.0f} px to the edge")
            if wtop and not d.get("stroke") and y < wtop and y + h > wtop + 1:
                res["plate_fit"].append(f"f{f}: band plate reaches {y + h - wtop:.0f} px into the picture")
    # pixel checks
    nf = sum(s["frames"] for s in piece["segments"])
    vid, noh, ink, txt = (rd / f"{name}.mp4", rd / f"{name}_nohand.mp4", rd / f"{name}_ink.mp4", rd / f"{name}_text.mp4")
    inks = [(fr.max(2) > 60) for fr in frames(ink, W, H)] if ink.exists() else []
    if inks:
        lag = 8  # 0.25 s
        worst = 0.0
        for f, (a, b) in enumerate(zip(frames(vid, W, H), frames(noh, W, H))):
            if f >= len(inks):
                break
            old = inks[f] & inks[max(0, f - lag)]
            n_old = int(old.sum())
            diff = np.abs(a.astype(np.int16) - b.astype(np.int16)).max(2) > 40
            if n_old < 200 or not diff.any():
                continue
            cov = float((diff & old).sum()) / n_old
            worst = max(worst, cov)
            if cov > 0.05:
                res["hand_over_ink"].append(f"f{f}: hand covers {cov:.0%} of the ink already laid")
        notes["hand_over_ink"] = f"worst {worst:.1%} of the laid ink under the hand"
        # jitter: centroid of the ink while no new ink is laid (finished marks riding with the camera)
        cs, prev = [], None
        for f, mk in enumerate(inks):
            n = int(mk.sum())
            if prev is not None and n > 50 and abs(n - prev) <= max(3, n * 0.002):
                ys, xs = np.nonzero(mk)
                cs.append((f, xs.mean(), ys.mean()))
            else:
                cs.append(None)
            prev = n
        rev = 0.0
        for i in range(2, len(cs)):
            a, b, c = cs[i - 2], cs[i - 1], cs[i]
            if not (a and b and c) or c[0] - a[0] != 2:
                continue
            for k in (1, 2):
                v1, v2 = b[k] - a[k], c[k] - b[k]
                if v1 * v2 < 0 and min(abs(v1), abs(v2)) > 0.25:
                    rev = max(rev, min(abs(v1), abs(v2)))
                    res["jitter_check"].append(f"f{c[0]}: a finished mark reverses by {min(abs(v1), abs(v2)):.2f} px")
        notes["jitter_check"] = f"largest reversal {rev:.3f} px (tolerance 0.25)"
        # mark_in_frame: no ink at the window edge
        for f, mk in enumerate(inks):
            seg, lf = segment_of(piece, f)
            t = seg["t0"] + lf / piece["fps"]
            shot = [s for s in seg["shots"] if s["start"] <= t + 1e-6][-1]
            if shot.get("type") != "image":
                continue
            y0 = shot.get("y0", 0) if shot.get("full") else 0
            win = mk[y0:y0 + shot["H"], :shot["W"]]
            e = 4
            if win[:e].any() or win[-e:].any() or win[:, :e].any() or win[:, -e:].any():
                res["mark_in_frame"].append(f"f{f}: ink at the picture edge")
    if txt.exists():
        tf = [fr.max(2) for fr in frames(txt, W, H)]
        last = None
        for f in range(len(tf)):
            seg, lf = segment_of(piece, f)
            if lf == 0:
                ends = sum(s["frames"] for s in piece["segments"][: piece["segments"].index(seg) + 1]) - 1
                last = tf[min(ends, len(tf) - 1)] > 100
            on = tf[f] > 200
            if on.sum() < 50:
                continue
            moved = float((on & ~last).sum()) / on.sum()
            if moved > 0.005:
                res["text_stability"].append(f"f{f}: {moved:.1%} of the words' pixels are not where they end")
    return {"name": name, "res": res, "notes": notes, "frames": nf}


def main(pub: str, rd: str, out: str) -> int:
    pub_p, rd_p = Path(pub), Path(rd)
    rows = [check(pub_p, rd_p, n) for n in json.loads((pub_p / "pieces.json").read_text())]
    md = ["| check | " + " | ".join(r["name"] for r in rows) + " |", "|---|" + "---|" * len(rows)]
    for c in ("plate_fit", "mark_in_frame", "jitter_check", "hand_over_ink", "text_stability"):
        md.append(f"| {c} | " + " | ".join("PASS" if not r["res"][c] else f"FAIL ({len(r['res'][c])})" for r in rows) + " |")
    md += ["", "Notes:"] + [f"- {r['name']} {k}: {v}" for r in rows for k, v in r["notes"].items()]
    md += ["", "First failures:"] + [f"- {r['name']} {c}: {r['res'][c][:3]}" for r in rows for c in r["res"] if r["res"][c]]
    Path(out).write_text("\n".join(md) + "\n")
    print("\n".join(md))
    return 1 if any(r["res"][c] for r in rows for c in r["res"]) else 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
