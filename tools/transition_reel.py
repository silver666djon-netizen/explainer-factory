"""Transition sample reel (Klot, after tooling test 2), run on GitHub Actions:

  python tools/transition_reel.py <audio dir with theme_noir_jazz_20s.mp3> <out dir>

Renders the TransitionReel composition (8 samples x 2.2 s, A: the archive photo card -> B: the split-flap board, a big
number 1-8 in the corner), checks every sample, lays the ElevenLabs theme underneath (-14 LUFS, true peak <= -1.5 dBTP)
and makes a contact sheet (one row per option). Writes transition_reel.mp4, transition_reel_sheet.png,
transition_reel.md, transition_reel_note.txt."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import tooling_test as T  # noqa: E402  (sh, bundle, loud, the Remotion flags)

LABELS = ["HALFTONE DISSOLVE", "TORN PAPER", "PAGE TURN", "PAPER COLLAGE", "INK BLEED", "IRIS", "FILM BURN", "CASE FOLDER"]
BLOCK = ["HyperFrames halftone-dissolve (port)", "HyperFrames torn-paper-rip (port)", "@remotion/transitions bookFlip",
         "HyperFrames paper-collage-reveal (port)", "HyperFrames ink-bleed-reveal (port, cover-and-reveal)",
         "iris to black (old cinema)", "@remotion/transitions filmBurn", "case folder slide (drawn in code)"]
HOLD_A, TRANS, HOLD_B = 12, 36, 18
SAMPLE = HOLD_A + TRANS + HOLD_B
N = 8


def frames(video: Path, idx: list[int], d: Path) -> dict[int, np.ndarray]:
    d.mkdir(parents=True, exist_ok=True)
    sel = "+".join(f"eq(n\\,{i})" for i in idx)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-vf", f"select='{sel}'", "-vsync", "0", str(d / "f_%04d.png")], check=True)
    got = sorted(d.glob("f_*.png"))
    out = {i: np.asarray(Image.open(p).convert("RGB")).astype(np.float32) for i, p in zip(sorted(idx), got)}
    for p in got:
        p.unlink()
    return out


def mad(a, b) -> float:
    m = np.ones(a.shape[:2], bool)
    m[:300, 1400:] = False  # the number badge is the same in both
    return float(np.abs(a - b)[m].mean())


def main(audio_dir: str, outdir: str) -> int:
    O = Path(outdir).resolve()
    O.mkdir(parents=True, exist_ok=True)
    log = O / "reel.log"
    T.PUB.mkdir(parents=True, exist_ok=True)
    keep = ROOT / "assets/tooling/loc_2017745251_loews_1939.jpg"
    shutil.copy(keep, T.PUB / "photo.jpg")
    if not (T.PUB / "test.json").exists():
        (T.PUB / "test.json").write_text(json.dumps({"lottie": None}))
    T.bundle(log)
    t0 = time.time()
    code, sec, out = T.remotion(["render", "src/index.ts", "TransitionReel", str(O / "reel_silent.mp4"), "--muted", "--concurrency=4", "--crf=18"], O, log)
    res: dict = {"render_ok": code == 0, "render_seconds": sec, "errors": [l for l in out.splitlines() if re.search(r"(?i)error|fail", l)][:8]}
    if code:
        (O / "reel.json").write_text(json.dumps(res, indent=1))
        print(out[-4000:])
        return 1
    # per sample: A before, B after, and the transition really happens (most transition frames are neither A nor B)
    idx = []
    for k in range(N):
        b = k * SAMPLE
        idx += [b + HOLD_A - 1, b + SAMPLE - 1] + [b + HOLD_A + j for j in range(2, TRANS - 1, 3)]
    F = frames(O / "reel_silent.mp4", sorted(set(idx)), O / "_frames")
    samples = []
    for k in range(N):
        b = k * SAMPLE
        A, B = F[b + HOLD_A - 1], F[b + SAMPLE - 1]
        mids = [F[b + HOLD_A + j] for j in range(2, TRANS - 1, 3)]
        between = sum(1 for m in mids if mad(m, A) > 3 and mad(m, B) > 3)
        badge = float(((A[60:240, 1660:1860, 0] > 120) & (A[60:240, 1660:1860, 1] < 80)).mean())
        ok = mad(A, B) > 10 and between >= len(mids) // 2 and badge > 0.2
        samples.append({"n": k + 1, "label": LABELS[k], "block": BLOCK[k], "ok": ok, "frames_in_between": f"{between}/{len(mids)}",
                        "a_vs_b": round(mad(A, B), 1), "badge_red": round(badge, 2)})
    res["samples"] = samples
    # the theme underneath, the length of the reel
    th = Path(audio_dir) / "theme_noir_jazz_20s.mp3"
    dur = N * SAMPLE / 30.0
    if th.exists():
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(O / "reel_silent.mp4"), "-i", str(th), "-filter_complex",
                        f"[1:a]atrim=0:{dur:.2f},asetpts=PTS-STARTPTS,afade=t=in:d=0.3,afade=t=out:st={dur - 1.2:.2f}:d=1.2,"
                        f"loudnorm=I=-14:TP=-2.0:LRA=11[a]", "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                        "-ar", "48000", "-t", f"{dur:.2f}", "-movflags", "+faststart", str(O / "transition_reel.mp4")], check=True)
        L = T.loud(O / "transition_reel.mp4")
        res["audio"] = {"ok": L["lufs"] is not None and abs(L["lufs"] + 14) <= 1 and L["true_peak"] <= -1.5, **L}
    else:
        shutil.copy(O / "reel_silent.mp4", O / "transition_reel.mp4")
        res["audio"] = {"ok": False, "why": "theme missing"}
    sheet(O / "transition_reel.mp4", O / "transition_reel_sheet.png")
    (O / "reel.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
    a = res["audio"]
    md = ["# Transition sample reel", "", f"8 options x 2.2 s ({dur:.1f} s), 1080p, A = the archive photo card, B = the split-flap board. "
          f"Rendered on GitHub Actions without a GPU in {sec} s. Theme underneath: {a.get('lufs')} LUFS, true peak {a.get('true_peak')} dBTP.", "",
          "| # | option | block | check |", "|---|---|---|---|"]
    md += [f"| {s['n']} | {s['label']} | {s['block']} | {'OK' if s['ok'] else 'FAIL'} (in-between frames {s['frames_in_between']}) |" for s in samples]
    (O / "transition_reel.md").write_text("\n".join(md) + "\n")
    note = ["8 transition options, about 2 s each, the number is in the top-right corner. Same two scenes as the test. Pick the house transitions by number.", ""]
    note += [f"{s['n']}. {s['label'].lower()} — {s['block']}" for s in samples]
    note += ["", f"Theme underneath: {a.get('lufs')} LUFS, true peak {a.get('true_peak')} dBTP. The theme is also attached on its own (20 s)."]
    (O / "transition_reel_note.txt").write_text("\n".join(note) + "\n")
    print("\n".join(md))
    return 0 if all(s["ok"] for s in samples) and a.get("ok") else 1


def sheet(video: Path, out: Path) -> None:
    cols = [5, HOLD_A + 9, HOLD_A + 18, HOLD_A + 27, SAMPLE - 4]
    idx = [k * SAMPLE + c for k in range(N) for c in cols]
    F = frames(video, idx, out.parent / "_sheet")
    tw, th = 384, 216
    S = Image.new("RGB", (len(cols) * (tw + 8) + 330, N * (th + 8) + 70), (22, 20, 18))
    d = ImageDraw.Draw(S)
    try:
        f1 = ImageFont.truetype(str(ROOT / "assets/fonts/SpecialElite-Regular.ttf"), 30)
        f2 = ImageFont.truetype(str(ROOT / "assets/fonts/SpecialElite-Regular.ttf"), 24)
    except Exception:  # noqa: BLE001
        f1 = f2 = ImageFont.load_default()
    d.text((12, 16), "CoinSense · transition options 1-8 (each row: before · 25 % · 50 % · 75 % · after)", fill=(240, 228, 200), font=f1)
    for k in range(N):
        y = 64 + k * (th + 8)
        d.text((14, y + th // 2 - 30), f"{k + 1}", fill=(200, 60, 50), font=f1)
        d.text((54, y + th // 2 - 26), LABELS[k], fill=(235, 225, 200), font=f2)
        for j, c in enumerate(cols):
            im = Image.fromarray(F[k * SAMPLE + c].astype(np.uint8)).resize((tw, th))
            S.paste(im, (330 + j * (tw + 8), y))
    S.save(out)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
