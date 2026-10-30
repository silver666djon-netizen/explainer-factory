"""CoinSense motion study: data for the demo reel (Remotion composition "Reel"), long 16:9 + Shorts 9:16.
Run after export_pilot.py (it reuses the pilot's exported beats: handwriting, number card, chart, kinetic card, archive
photo). Each reel segment = one window of the r90 timeline (same narration + music) shown with one technique.
python tools/remotion/export_reel.py <r90 release dir> <public dir>"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
EP = ROOT / "episodes" / "0005-drip-pricing"
FPS = 30


def main(rel: str, pub: str) -> int:
    rel_p, P = Path(rel), Path(pub)
    T = json.load(open(rel_p / "timings.json"))
    beats = T["beats"]
    ids = [b["id"] for b in beats]
    script = {b["id"]: b for b in json.loads((EP / "script.json").read_text())["beats"]}
    long_mp4 = sorted(rel_p.glob("cs_*_long.mp4"))[0]
    (P / "reel").mkdir(parents=True, exist_ok=True)

    def win(bid, pad0=0.0, pad1=0.0):
        i = ids.index(bid)
        return beats[i]["start"] - pad0, (beats[i + 1]["start"] if i + 1 < len(beats) else T["total"]) + pad1

    def words(bid):
        b = beats[ids.index(bid)]
        return [[w, round(b["start"] + s, 3), round(b["start"] + e, 3)] for w, s, e in b["words"]]

    def audio(name, a, b, src=long_mp4):
        rel_ = f"reel/{name}.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", str(src), "-vn", "-ac", "2",
                        "-ar", "48000", str(P / rel_)], check=True)
        return rel_

    def img(key, src: Path, max_w=2400):
        im = Image.open(src).convert("RGB")
        if im.width > max_w:
            im = im.resize((max_w, round(im.height * max_w / im.width)), Image.LANCZOS)
        out = P / "reel" / f"{key}.jpg"
        im.save(out, quality=93)
        return f"reel/{key}.jpg", im.size

    pieces = {n: json.loads((P / f"{n}.json").read_text()) for n in ("beat1_long", "beat2_long", "beat3_long",
                                                                     "beat1_short", "beat2_short", "beat3_short")}
    # ---- parallax layers from one still (c1): depth -> foreground (Larry) + inpainted background
    c1 = Image.open(EP / "images" / "c1.png").convert("RGB")
    c1 = c1.resize((2400, round(c1.height * 2400 / c1.width)), Image.LANCZOS)
    from transformers import pipeline
    depth = pipeline("depth-estimation", model="depth-anything/Depth-Anything-V2-Small-hf", device=-1)(c1)["depth"]
    d = np.array(depth.resize(c1.size, Image.BILINEAR)).astype(np.float32) / 255.0
    d = cv2.GaussianBlur(d, (0, 0), 3)
    thr = max(0.55, float(np.percentile(d, 82)))
    fg = (d > thr).astype(np.uint8)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(fg)
    keep = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA])) if n > 1 else 0
    fg = (lab == keep).astype(np.uint8)
    fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, np.ones((25, 25), np.uint8))
    fg = cv2.dilate(fg, np.ones((9, 9), np.uint8))
    ys_, xs_ = np.nonzero(fg)
    feet = [round(float(np.median(xs_[ys_ > np.percentile(ys_, 97)])) / fg.shape[1], 4), round(float(ys_.max()) / fg.shape[0], 4)]
    a = cv2.GaussianBlur(fg.astype(np.float32), (0, 0), 2.0)
    arr = np.array(c1)
    Image.fromarray(np.dstack([arr, (a * 255).astype(np.uint8)])).save(P / "reel" / "c1_fg.png")
    small = cv2.resize(arr, (arr.shape[1] // 3, arr.shape[0] // 3), interpolation=cv2.INTER_AREA)
    m_small = cv2.resize(cv2.dilate(fg, np.ones((31, 31), np.uint8)) * 255, (small.shape[1], small.shape[0]))
    bg = cv2.inpaint(small, m_small, 9, cv2.INPAINT_TELEA)
    bg_full = cv2.resize(bg, (arr.shape[1], arr.shape[0]), interpolation=cv2.INTER_CUBIC)
    m3 = cv2.GaussianBlur(cv2.dilate(fg, np.ones((31, 31), np.uint8)).astype(np.float32), (0, 0), 6)[..., None]
    Image.fromarray((arr * (1 - m3) + bg_full * m3).astype(np.uint8)).save(P / "reel" / "c1_bg.jpg", quality=93)
    Image.fromarray((fg * 255).astype(np.uint8)).save(P / "reel" / "c1_mask.png")
    print("parallax: feet", feet, "foreground", round(float(fg.mean()) * 100, 1), "% of the picture, depth threshold", round(thr, 2))

    o1, o1sz = img("o1", EP / "images" / "o1.png")
    b1, b1sz = img("b1", EP / "images" / "b1.png")
    l1, l1sz = img("l1desk", EP / "images" / "l1.png")
    d3 = script["d3"]["visual"]["doc"]
    c1w, c1h = c1.size

    def reel(kind):
        long = kind == "long"
        pk = (lambda n: pieces[f"{n}_long"]) if long else (lambda n: pieces[f"{n}_short"])
        segs = []

        def add(tag, k, frames, aud, **kw):
            segs.append({"tag": tag, "kind": k, "frames": frames, "audio": aud, **kw})
        # 01 handwriting: the pilot's cold open
        s = pk("beat1")["segments"][0]
        add("TRUE-STROKE HANDWRITING · @remotion/paths", "piece", s["frames"], s["audio"], seg=s)
        # 02 number card: spring stamp, synced hit, breathing vignette
        s = pk("beat2")["segments"][0]
        add("SPRING STAMP + SYNCED HIT · spring()", "stat", s["frames"], s["audio"], seg=s)
        # 03 chart: eased build, staggered, gridlines drawn
        s = pk("beat2")["segments"][1]
        add("EASED CHART BUILD · spring() + @remotion/paths", "chart", s["frames"], s["audio"], seg=s)
        # 04 kinetic chapter title (t5)
        a, b = win("t5")
        add("KINETIC TITLE · @remotion/layout-utils fitText", "title", round((b - a) * FPS), audio(f"t5_{kind}", a, b),
            kicker="FRIDAY 9:00 AM", title="ONE FEE, THREE LAWS", t0=a, words=words("t5"), sun=pk("beat2")["segments"][0]["shots"][-1]["bg"])
        # 05 route map (l1): three borders
        a, b = win("l1")
        add("ANIMATED ROUTE · @remotion/paths evolvePath", "route", round((b - a) * FPS), audio(f"l1_{kind}", a, b),
            t0=a, words=words("l1"), ticket=o1, ticketSize=o1sz, desk=l1, deskSize=l1sz)
        # 06 parallax from one still (c1)
        a, b = win("c1")
        add("PARALLAX FROM ONE STILL · depth split", "parallax", round((b - a) * FPS), audio(f"c1_{kind}", a, b),
            t0=a, fg="reel/c1_fg.png", bg="reel/c1_bg.jpg", size=[c1w, c1h], feet=feet, words=words("c1"))
        # 07 evidence card on paper: noise wobble, ink texture, highlighter
        a, b = win("d3")
        add("PAPER, INK + NOISE WOBBLE · @remotion/noise", "evidence", round((b - a) * FPS), audio(f"d3_{kind}", a, b),
            t0=a, doc=d3, words=words("d3"))
        # 08 karaoke subtitles from word timing (b1)
        a, b = win("b1")
        add("WORD-ACCURATE KARAOKE · @remotion/captions", "karaoke", round((b - a) * FPS), audio(f"b1_{kind}", a, b),
            t0=a, pic=b1, picSize=b1sz, words=words("b1"))
        # 09 + 10 kinetic card -> print-style ink wipe -> archive push-in with camera motion blur
        sk = pk("beat3")["segments"][0]
        sl = pk("beat3")["segments"][1]
        add("PRINT-STYLE INK WIPE · @remotion/transitions", "piece", sk["frames"], sk["audio"], seg=sk, wipeOut=True)
        add("CAMERA MOTION BLUR · @remotion/motion-blur", "blurpush", sl["frames"], sl["audio"], seg=sl)
        W, H = (1920, 1080) if long else (1080, 1920)
        out = {"W": W, "H": H, "fps": FPS, "segments": segs, "vignette": pk("beat1")["vignette"],
               "fonts": {**pk("beat1")["fonts"], **pk("beat2")["fonts"], **pk("beat3")["fonts"],
                         "PT_Serif-Web-Regular.ttf": "PT-Serif-Web-Regular", "OldStandard-Bold.ttf": "OldStandard-Bold"}}
        (P / f"reel_{kind}.json").write_text(json.dumps(out))
        print(kind, len(segs), "segments", round(sum(s_["frames"] for s_ in segs) / FPS, 1), "s")
    reel("long")
    reel("short")
    for f in ("PT_Serif-Web-Regular.ttf", "OldStandard-Bold.ttf"):
        src = ROOT / "assets" / "fonts" / f
        if src.exists():
            (P / "fonts" / f).write_bytes(src.read_bytes())
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:3]))
