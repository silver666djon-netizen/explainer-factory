"""Tracks a Grok clip against the still it was made from, so ink laid on the still (a sign, a tag) stays on its object
while the clip's camera moves (Klot round 4: the written signs must be on every shot of k2).
python tools/track_clip.py <clip.mp4> <still.png> <out.json>
-> {"fps", "W": 1920, "H": 1094, "m": [[a, b, c, d, e, f] per clip frame]}: still px -> display px (the clip drawn 1920 x 1094):
   x' = a*x + b*y + e, y' = c*x + d*y + f  (similarity, ORB + RANSAC per frame, lightly smoothed)."""
import json
import sys

import cv2
import numpy as np


def main(clip, still, out):
    cap = cv2.VideoCapture(clip)
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    frames = []
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        frames.append(cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY))
    h, w = frames[0].shape
    st = cv2.imread(still, cv2.IMREAD_GRAYSCALE)
    sh, sw = st.shape
    ref = cv2.resize(st, (w, h), interpolation=cv2.INTER_AREA)
    orb = cv2.ORB_create(4000)
    kr, dr = orb.detectAndCompute(ref, None)
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    ms = []
    prev = np.array([[1, 0, 0], [0, 1, 0]], float)
    for fr in frames:
        kf, df = orb.detectAndCompute(fr, None)
        M = None
        if df is not None:
            mt = sorted(bf.match(dr, df), key=lambda m: m.distance)[:800]
            if len(mt) >= 12:
                a = np.float32([kr[m.queryIdx].pt for m in mt])
                b = np.float32([kf[m.trainIdx].pt for m in mt])
                M, inl = cv2.estimateAffinePartial2D(a, b, method=cv2.RANSAC, ransacReprojThreshold=3.0, maxIters=5000)
        if M is None:
            M = prev
        ms.append(M)
        prev = M
    ms = np.array(ms)
    # light smoothing (3-frame) so the ink does not shimmer
    sm = ms.copy()
    for i in range(1, len(ms) - 1):
        sm[i] = (ms[i - 1] + 2 * ms[i] + ms[i + 1]) / 4
    sr, sf = w / sw, 1920.0 / w
    rows = []
    for M in sm:
        A = M[:, :2] * sr * sf
        t = M[:, 2] * sf
        rows.append([round(float(A[0, 0]), 6), round(float(A[0, 1]), 6), round(float(A[1, 0]), 6), round(float(A[1, 1]), 6), round(float(t[0]), 2), round(float(t[1]), 2)])
    json.dump({"fps": fps, "W": 1920, "H": round(1920 * h / w), "m": rows}, open(out, "w"))
    s0, s1 = np.hypot(sm[0][0, 0], sm[0][0, 1]), np.hypot(sm[-1][0, 0], sm[-1][0, 1])
    print(f"{len(rows)} frames; scale {s0:.3f} -> {s1:.3f}; shift {sm[0][:, 2].round(1)} -> {sm[-1][:, 2].round(1)}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
