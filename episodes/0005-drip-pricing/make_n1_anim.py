"""n1 in code (Klot, 2026-10-28; Grok redraws the tag, so no generated clip): the existing n1 still split into layers -
background with the left piece of the tag, the right piece, the scissors (upper blade on its own) - and animated:
a quick snip (upper blade closes ~6 deg about the pivot and back, 0.25 s), then the right piece slides ~8 % right and
2 deg down, eased, and settles. Writes clips/n1.mp4 (24 fps, 1920x1072, muted) and images/n2_end.png (last frame) and
prints the settled right-piece transform for the labels.   python episodes/0005-drip-pricing/make_n1_anim.py"""
from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
SRC = sorted((ROOT / ".cache" / "images" / "0005-drip-pricing").glob("n1-*.png"))[0]

FPS, DUR = 24, 2.0
SNIP0, SNIP1 = 0.30, 0.55      # blade closes and opens
SLIDE0, SLIDE1 = 0.62, 1.30    # the right piece slides and settles
DX, DROT = 0.08, -2.0          # 8 % of the width to the right, 2 deg clockwise ("down")
SNIP_DEG = 6.0
OUT_W, OUT_H = 1920, 1072

# geometry in fractions of the still (1376x768), measured on a 2 % grid
PIVOT = (0.628, 0.506)
LEFT_EDGE = [(0.174, 0.449), (0.182, 0.498), (0.187, 0.521), (0.196, 0.550), (0.204, 0.570), (0.209, 0.596),
             (0.220, 0.622), (0.226, 0.654), (0.233, 0.680), (0.240, 0.706), (0.246, 0.736), (0.251, 0.762)]
RIGHT_PIECE_LEFT = [(0.207, 0.425), (0.215, 0.478), (0.222, 0.524), (0.229, 0.563), (0.237, 0.602), (0.239, 0.635),
                    (0.244, 0.661), (0.249, 0.687), (0.255, 0.720), (0.260, 0.742)]
RIGHT_PIECE = [(0.624, 0.222), (0.668, 0.436), (0.674, 0.542), (0.525, 0.577), (0.522, 0.600), (0.262, 0.748)] \
    + RIGHT_PIECE_LEFT[::-1] + [(0.206, 0.423)]
TOP_EDGE = [(0.206, 0.423), (0.624, 0.222)]  # redrawn where the blade hid it
EDGES = [TOP_EDGE, [(0.624, 0.222), (0.674, 0.542)], [(0.674, 0.542), (0.525, 0.577)]]  # + the right / lower edge under the shank
UPPER_BLADE = [(0.298, 0.318), (0.318, 0.298), (0.345, 0.290), (0.378, 0.295), (0.412, 0.306), (0.648, 0.443),
               (0.648, 0.470), (0.506, 0.484), (0.298, 0.334)]
SHANK = [(0.498, 0.466), (0.600, 0.452), (0.668, 0.430), (0.700, 0.428), (0.700, 0.580), (0.600, 0.556), (0.520, 0.540)]
SHADOW = [(0.305, 0.372), (0.400, 0.380), (0.500, 0.430), (0.510, 0.485), (0.440, 0.470), (0.330, 0.420)]


def poly_mask(pts, W, H, dil=0):
    m = np.zeros((H, W), np.uint8)
    cv2.fillPoly(m, [np.int32([(x * W, y * H) for x, y in pts])], 1)
    if dil:
        m = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * dil + 1, 2 * dil + 1)))
    return m


def cream_fill(img, mask, seed=3):
    """Fill `mask` with the page's own paper: its colour from the clean paper around (normalised blur, ink and colour
    left out, so no smear of lines comes in) plus the grain of a clean patch."""
    H, W = mask.shape
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    paper = ((hsv[..., 2] > 200) & (hsv[..., 1] < 90) & (mask == 0)).astype(np.float32)
    paper = cv2.erode(paper, np.ones((9, 9), np.uint8))
    num = cv2.GaussianBlur(img.astype(np.float32) * paper[..., None], (0, 0), 40)
    den = cv2.GaussianBlur(paper, (0, 0), 40)[..., None]
    med = np.median(img[paper > 0], axis=0).astype(np.float32)
    lo = np.where(den > 0.05, num / np.maximum(den, 1e-3), med)  # deep inside a big hole: the page colour
    patch = img[int(0.03 * H):int(0.22 * H), int(0.02 * W):int(0.45 * W)].astype(np.float32)
    grain = patch - cv2.GaussianBlur(patch, (0, 0), 6)
    reps = (H // grain.shape[0] + 2, W // grain.shape[1] + 2, 1)
    rnd = np.random.default_rng(seed)
    tile = np.tile(grain, reps)
    oy, ox = rnd.integers(0, grain.shape[0]), rnd.integers(0, grain.shape[1])
    tile = tile[oy:oy + H, ox:ox + W]
    fill = np.clip(lo + tile, 0, 255)
    m = cv2.GaussianBlur(mask.astype(np.float32), (0, 0), 1.0)[..., None]
    return (img * (1 - m) + fill * m).astype(np.uint8)


def ease(p):
    p = min(1.0, max(0.0, p))
    return 1 - (1 - p) ** 3  # ease-out: quick start, soft settle


def main():
    im = cv2.imread(str(SRC))
    H, W = im.shape[:2]
    S = 2  # work at 2x for clean edges
    im = cv2.resize(im, (W * S, H * S), interpolation=cv2.INTER_LANCZOS4)
    H, W = im.shape[:2]
    hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)
    h, s, v = [hsv[..., i].astype(int) for i in range(3)]
    colour = (((h < 12) | (h > 165)) & (s > 90) & (v > 60)) | ((h > 30) & (h < 90) & (s > 25) & (v > 60))
    shadow = poly_mask(SHADOW, W, H)
    colour = colour.astype(np.uint8) * (1 - shadow)
    n, lab, st, _ = cv2.connectedComponentsWithStats(colour)  # colour fringes along ink lines are not scissors
    keep = np.zeros(n, np.uint8)
    keep[1:] = st[1:, cv2.CC_STAT_AREA] > 4000
    colour = keep[lab]
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31))
    sc = cv2.morphologyEx(colour, cv2.MORPH_CLOSE, k)
    sc = cv2.dilate(sc, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (17, 17)))
    # the upper blade: its green, its outline (a tight ring round the green) and its polygon - nothing beyond, so no
    # bit of the tag's lines next to it is carried along (rule: a moving layer holds only the moving object)
    ell = lambda r: cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
    green = (((h > 30) & (h < 90) & (s > 25) & (v > 60)).astype(np.uint8)) * poly_mask(UPPER_BLADE, W, H, dil=6)
    green = cv2.morphologyEx(green, cv2.MORPH_OPEN, ell(10))  # solid fill only: the shadow's halftone dots drop out
    green = cv2.morphologyEx(green, cv2.MORPH_CLOSE, ell(9))
    up = cv2.dilate(green, np.ones((31, 1), np.uint8), anchor=(0, 0))  # the bevel: a second line ~26 px above the green
    blade = np.clip(cv2.dilate(green, ell(11)) + up, 0, 1)
    tip = poly_mask(UPPER_BLADE, W, H, dil=4) * cv2.dilate(green, ell(30))
    tip[:, int(0.33 * W):] = 0  # the pointed tip, thinner than the opening keeps
    blade = np.clip(blade + tip, 0, 1)
    shank = poly_mask(SHANK, W, H)
    scissors = np.clip(sc + shank + blade, 0, 1)
    others = np.clip(colour.astype(np.int16) - cv2.dilate(green, ell(3)), 0, 1).astype(np.uint8)  # handles, lower blade
    sc_static = cv2.dilate(cv2.morphologyEx(others, cv2.MORPH_CLOSE, k), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (17, 17)))
    static_sc = np.clip(sc_static + shank, 0, 1) * (1 - blade)
    rp = poly_mask(RIGHT_PIECE, W, H, dil=14)
    # clean plate: no right piece, no scissors (the left piece stays)
    bg = cream_fill(im, np.clip(rp + scissors, 0, 1))
    # the scissors layers must not carry the tag's own lines (they would stay behind when the piece moves):
    # tag lines inside the scissors' margin become paper, except the scissors' outline right next to their colour
    band = np.zeros((H, W), np.uint8)
    for (x0, y0), (x1, y1) in EDGES:
        cv2.line(band, (int(x0 * W), int(y0 * H)), (int(x1 * W), int(y1 * H)), 1, 16)
    cv2.polylines(band, [np.int32([(x * W, y * H) for x, y in RIGHT_PIECE])], True, 1, 16)
    protect = cv2.dilate(np.clip(colour + poly_mask(SHANK, W, H), 0, 1), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (13, 13)))
    repl = (band > 0) & (protect == 0)
    im_sc = im.copy()
    im_sc[repl] = bg[repl]
    # the right piece on its own: paper under the scissors and under the blade shadow filled in, top edge redrawn
    piece = cream_fill(im, np.clip(scissors + shadow, 0, 1) * rp, seed=5)
    ink = tuple(int(c) for c in np.median(im[(v < 60) & (rp > 0)], axis=0)) if np.any((v < 60) & (rp > 0)) else (30, 28, 26)
    for (x0, y0), (x1, y1) in EDGES:
        cv2.line(piece, (int(x0 * W), int(y0 * H)), (int(x1 * W), int(y1 * H)), ink, 7, cv2.LINE_AA)
    rp_alpha = cv2.GaussianBlur(poly_mask(RIGHT_PIECE, W, H, dil=10).astype(np.float32), (0, 0), 1.2)
    # blade shadow: how much darker the paper is there (multiplied over whatever paper is below)
    clean = cream_fill(im, shadow, seed=7).astype(np.float32)
    shade = np.where((shadow[..., None] > 0) & (v[..., None] > 80),  # (black ink lines in it belong to the tag, not the shadow)
                      np.clip(im.astype(np.float32) / np.maximum(clean, 1), 0.3, 1.0), 1.0)
    sc_a = cv2.GaussianBlur(static_sc.astype(np.float32), (0, 0), 1.0)[..., None]
    bl_a = cv2.GaussianBlur(blade.astype(np.float32), (0, 0), 1.0)[..., None]
    px, py = PIVOT[0] * W, PIVOT[1] * H
    cx, cy = (np.mean([p[0] for p in RIGHT_PIECE]) * W, np.mean([p[1] for p in RIGHT_PIECE]) * H)

    def frame(t):
        # right piece transform
        q = ease((t - SLIDE0) / (SLIDE1 - SLIDE0)) if t > SLIDE0 else 0.0
        M = cv2.getRotationMatrix2D((cx, cy), DROT * q, 1.0)
        M[0, 2] += DX * W * q
        out = bg.astype(np.float32)
        pw = cv2.warpAffine(piece, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE).astype(np.float32)
        pa = cv2.warpAffine(rp_alpha, M, (W, H), flags=cv2.INTER_LINEAR)[..., None]
        out = out * (1 - pa) + pw * pa
        out = out * shade  # the blade's shadow stays with the blade
        # scissors: the static part, then the upper blade rotated about the pivot
        out = out * (1 - sc_a) + im_sc.astype(np.float32) * sc_a
        a = 0.0
        if SNIP0 <= t <= SNIP1:
            u = (t - SNIP0) / (SNIP1 - SNIP0)
            a = SNIP_DEG * math.sin(math.pi * u)  # close (tip down: counter-clockwise in cv2) and open again
        R = cv2.getRotationMatrix2D((px, py), a, 1.0)
        bw = cv2.warpAffine(im, R, (W, H), flags=cv2.INTER_LINEAR).astype(np.float32)
        ba = cv2.warpAffine(bl_a, R, (W, H), flags=cv2.INTER_LINEAR)[..., None]
        out = out * (1 - ba) + bw * ba
        return np.clip(out, 0, 255).astype(np.uint8), M

    clip = HERE / "clips" / "n1.mp4"
    clip.parent.mkdir(exist_ok=True)
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{OUT_W}x{OUT_H}",
                          "-r", str(FPS), "-i", "-", "-an", "-c:v", "libx264", "-crf", "14", "-preset", "slow",
                          "-pix_fmt", "yuv420p", str(clip)], stdin=subprocess.PIPE)
    last, Mlast = None, None
    for i in range(int(DUR * FPS)):
        f, Mlast = frame(i / FPS)
        last = cv2.resize(f, (OUT_W, OUT_H), interpolation=cv2.INTER_AREA)
        p.stdin.write(last.tobytes())
    p.stdin.close()
    p.wait()
    cv2.imwrite(str(HERE / "images" / "n2_end.png"), cv2.resize(frame(DUR)[0], (W // S, H // S), interpolation=cv2.INTER_AREA))
    # settled transform in picture fractions: a point (x, y) of the right piece goes to (x', y')
    A = np.vstack([Mlast, [0, 0, 1]])
    Sm = np.diag([W, H, 1.0])
    Af = np.linalg.inv(Sm) @ A @ Sm
    json.dump({"right_piece": Af[:2].tolist(), "rot_deg": DROT, "slide": [SLIDE0, SLIDE1], "snip": [SNIP0, SNIP1]},
              open(HERE / "images" / "n1_anim.json", "w"), indent=1)
    print("wrote", clip, "and images/n2_end.png; right piece settles with", np.round(Af[:2], 4).tolist())


if __name__ == "__main__":
    sys.exit(main())
