"""Where a live clip moves (rule 25): python tools/qc/clip_zones.py <clip.mp4> <out.jpg> [x0,y0,x1,y1 ...]

Prints the clip's movement window (start / end = the click), the bounding box of everything that moves (lever travel,
its shadow) in picture fractions, and for each given box (a planned label, fractions of the picture) the share of it a
moving part ever covers. Writes an overlay: magenta = covered at some frame, grid every 5 %. The scene without its
moving parts is the per-pixel median of the frames (the camera of a Grok clip is near-steady; frames are aligned to
the first one by ORB similarity first)."""
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from factory.shots import clip_event  # noqa: E402


def main(argv):
    clip, out = argv[0], argv[1]
    boxes = [tuple(float(v) for v in b.split(",")) for b in argv[2:]]
    cap = cv2.VideoCapture(clip)
    frames = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        frames.append(f)
    cap.release()
    H, W = frames[0].shape[:2]
    g0 = cv2.cvtColor(frames[0], cv2.COLOR_BGR2GRAY)
    orb = cv2.ORB_create(3000)
    k0, d0 = orb.detectAndCompute(g0, None)
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    al = []
    for f in frames[::2]:
        k1, d1 = orb.detectAndCompute(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY), None)
        m = bf.match(d0, d1)
        src = np.float32([k0[x.queryIdx].pt for x in m])
        dst = np.float32([k1[x.trainIdx].pt for x in m])
        M, _ = cv2.estimateAffinePartial2D(dst, src, method=cv2.RANSAC)
        al.append(cv2.warpAffine(f, M if M is not None else np.float32([[1, 0, 0], [0, 1, 0]]), (W, H), borderMode=cv2.BORDER_REPLICATE))
    st = np.stack(al).astype(np.int16)
    bg = np.median(st, axis=0)
    union = np.zeros((H, W), np.uint8)
    for a in st:
        d = cv2.GaussianBlur(np.abs(a - bg).max(axis=2).astype(np.float32), (0, 0), 3)
        m = cv2.morphologyEx((d > 35).astype(np.uint8), cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))
        union |= m
    t0, t1 = clip_event(clip, "start"), clip_event(clip, "end")
    print(f"clip {len(frames)} frames, movement {t0:.2f}-{t1:.2f} s (click = {t1:.2f} s)")
    ys, xs = np.nonzero(union)
    if len(xs):
        print(f"moving parts ever cover x {xs.min() / W:.3f}-{xs.max() / W:.3f}, y {ys.min() / H:.3f}-{ys.max() / H:.3f}")
    for b in boxes:
        x0, y0, x1, y1 = (int(b[0] * W), int(b[1] * H), int(b[2] * W), int(b[3] * H))
        cov = union[y0:y1, x0:x1].mean() if x1 > x0 and y1 > y0 else 0
        print(f"box {b}: covered {cov:.1%} - {'CLEAR' if cov < 0.005 else 'NOT CLEAR'}")
    ov = bg.astype(np.uint8).copy()
    ov[union > 0] = (ov[union > 0] * 0.4 + np.array([255, 0, 255]) * 0.6).astype(np.uint8)
    for k in range(1, 20):
        c = (0, 0, 255) if k % 2 == 0 else (200, 200, 0)
        cv2.line(ov, (int(W * k / 20), 0), (int(W * k / 20), H), c, 1)
        cv2.line(ov, (0, int(H * k / 20)), (W, int(H * k / 20)), c, 1)
        if k % 2 == 0:
            cv2.putText(ov, f"{k / 20:.1f}", (int(W * k / 20) + 2, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            cv2.putText(ov, f"{k / 20:.1f}", (2, int(H * k / 20) - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
    for b in boxes:
        cv2.rectangle(ov, (int(b[0] * W), int(b[1] * H)), (int(b[2] * W), int(b[3] * H)), (0, 200, 0), 3)
    cv2.imwrite(out, ov, [cv2.IMWRITE_JPEG_QUALITY, 85])


if __name__ == "__main__":
    main(sys.argv[1:])
