"""Episode 0005 — code-made frames for Klot's r78 list (no generations):
  clips/l1.mp4   the hand flips Larry's ticket on the customs desk (front -> back), 2.0 s, 1920 x 1072
  images/l2.png  the ticket's back on the desk: plain cream, faint BORDER CONTROL header, stub on the left
  images/z0b.png the z0 clip at 1.9 s (z0 holds there; z0b goes on from the same frame)
Run from the repo root after the storyboard is downloaded (needs the l1 desk in .cache/images/0005-drip-pricing):
  python episodes/0005-drip-pricing/make_l1_flip.py"""
import math
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
CACHE = ROOT / ".cache" / "images" / "0005-drip-pricing"
OUT = HERE / "images"
INK, PAPER, BG = (30, 27, 24), (252, 247, 233), (243, 233, 210)
FPS, DUR = 24, 2.0
HAND_IN, FLIP0, FLIP1, HAND_OUT = 0.0, 0.30, 1.10, 1.40
OW, OH = 1920, 1072


def fnt(name, size):
    for q in (ROOT / "assets" / "fonts" / name, Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")):
        if q.exists():
            return ImageFont.truetype(str(q), size)


def ticket_faces():
    """Front (as in images/l1.png: the o1 ticket with $30 written in ink) and back, both 880 x 400 RGBA."""
    DX = -167
    tx0, ty0, tx1, ty1 = 250 + DX, 190, 1130 + DX, 590
    front = Image.open(OUT / "o1.png").convert("RGB").crop((tx0, ty0, tx1, ty1))
    ImageDraw.Draw(front).text(((410 + 740) / 2 + DX - tx0, (460 + 550) / 2 - ty0), "$30", font=fnt("PermanentMarker-Regular.ttf", 74),
                               fill=INK, anchor="mm")
    w, h = front.size
    back = Image.new("RGB", (w, h), BG)
    d = ImageDraw.Draw(back)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=26, fill=PAPER, outline=INK, width=10)
    sx = 230  # the stub is on the left now
    for yy in range(24, h - 20, 34):
        d.ellipse((sx - 7, yy - 7, sx + 7, yy + 7), fill=BG, outline=INK, width=3)
    d.text(((sx + w) / 2, 58), "BORDER CONTROL", font=fnt("ArchivoBlack-Regular.ttf", 30), fill=(196, 186, 166), anchor="mm")
    d.line((sx + 60, 86, w - 60, 86), fill=(214, 205, 186), width=3)
    alpha = Image.new("L", (w, h), 0)
    ImageDraw.Draw(alpha).rounded_rectangle((0, 0, w - 1, h - 1), radius=26, fill=255)
    out = []
    for face in (front, back):
        f = face.convert("RGBA")
        f.putalpha(alpha)
        out.append(f)
    return out


def main():
    desk = Image.open(CACHE / "l1-8b76d60501.png").convert("RGB")
    W, H = desk.size
    front, back = ticket_faces()
    TW = int(W * 0.50)
    TH = int(front.height * TW / front.width)
    ANG = -4
    cx, cy = int(W * 0.47), int(H * 0.43)
    front, back = front.resize((TW, TH), Image.LANCZOS), back.resize((TW, TH), Image.LANCZOS)

    def compose(theta, lift):
        """theta 0 = front, pi = back; the card turns about its own vertical axis, the free edge lifts."""
        c = math.cos(theta)
        face = front if c >= 0 else back
        w = max(2, int(TW * abs(c)))
        f = face.resize((w, TH), Image.LANCZOS)
        if abs(c) < 0.999:  # a little shading while it turns
            arr = np.array(f).astype(np.float32)
            arr[..., :3] *= 0.82 + 0.18 * abs(c)
            f = Image.fromarray(arr.astype(np.uint8))
        s = 1.0 + 0.06 * lift
        f = f.resize((max(2, int(f.width * s)), max(2, int(f.height * s))), Image.LANCZOS)
        f = f.rotate(ANG, resample=Image.BICUBIC, expand=True)
        im = desk.copy()
        sa = np.array(f)[..., 3]
        sh = Image.new("RGBA", f.size, (0, 0, 0, 0))
        sh.putalpha(Image.fromarray((sa * 0.35).astype(np.uint8)).filter(ImageFilter.GaussianBlur(8 + 10 * lift)))
        off = int(14 + 26 * lift)
        im.paste(sh, (cx - f.width // 2 + 10 + off // 2, cy - f.height // 2 + off), sh)
        im.paste(f, (cx - f.width // 2, cy - f.height // 2), f)
        return im

    compose(math.pi, 0).save(OUT / "l2.png")
    from factory.draw import paste_hand, set_hand_style
    set_hand_style({"hands": {"sleeve": False}})
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OW}x{OH}", "-r", str(FPS), "-i", "-",
                          "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "14", "-preset", "slow", str(HERE / "clips" / "l1.mp4")],
                         stdin=subprocess.PIPE)
    a = math.radians(-ANG)  # the ticket's own axes on screen (it is turned 4 degrees)
    ux, uy = math.cos(a), math.sin(a)
    for i in range(int(FPS * DUR)):
        t = i / FPS
        q = min(1.0, max(0.0, (t - FLIP0) / (FLIP1 - FLIP0)))
        q = q * q * (3 - 2 * q)
        theta, lift = math.pi * q, math.sin(math.pi * q)
        frame = np.array(compose(theta, lift).resize((OW, OH), Image.LANCZOS))
        # the hand: comes in from the right to the ticket's right edge, carries that edge over, leaves to the right
        sx_, sy_ = OW / W, OH / H
        half = TW / 2 * (1 + 0.06 * lift)
        edge = half * math.cos(theta)  # x of the moving edge along the ticket's axis, from the centre
        ex, ey = cx + edge * ux, cy + edge * uy - 0.06 * TH * lift - 0.10 * TH
        if t < FLIP0:
            k = (t - HAND_IN) / (FLIP0 - HAND_IN)
            k = k * k * (3 - 2 * k)
            hx, hy = (W * 1.25) + (ex - W * 1.25) * k, (H * 0.95) + (ey - H * 0.95) * k
        elif t <= FLIP1:
            hx, hy = ex, ey
        else:
            k = min(1.0, (t - FLIP1) / (HAND_OUT - FLIP1))
            k = k * k * (3 - 2 * k)
            hx, hy = ex + (W * 1.25 - ex) * k, ey + (H * 0.95 - ey) * k
        if t <= HAND_OUT:
            paste_hand(frame, "pencil", hx * sx_, hy * sy_, mirrored=False, scale=0.8)
        p.stdin.write(frame.tobytes())
    p.stdin.close()
    p.wait()
    # z0b = the z0 clip at 1.9 s
    cap = cv2.VideoCapture(str(HERE / "clips" / "z0.mp4"))
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(1.9 * (cap.get(cv2.CAP_PROP_FPS) or 24)))  # the frame ClipImageShot holds
    ok, fr = cap.read()
    assert ok
    cv2.imwrite(str(OUT / "z0b.png"), fr)
    print("wrote clips/l1.mp4, images/l2.png, images/z0b.png")


if __name__ == "__main__":
    main()
