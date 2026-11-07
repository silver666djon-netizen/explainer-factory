"""Ep.4 v2 PREVIEW 1: master the Remotion renders (mix -> calibrated gain -> 4x oversampled limiter -> AAC, as the
Python engine's masters) and run the release checks that apply to the Remotion layer, each with its planted-bug
self-test (R40). Writes qc_preview2.md + contact sheets.
python tools/v2_qc.py <pv dir: plan.json, mix_*.wav, v2_*_silent.mp4> <timings dir>"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
from factory import render as R  # noqa: E402
from factory import sttdiff  # noqa: E402
from factory.config import load_config  # noqa: E402

class _Out(dict):
    def __missing__(self, k):  # a Short: cs_ep04v2_sh1.mp4 ...
        return f"cs_ep04v2_{k}.mp4"


OUT = _Out({"long": "cs_ep04v2_preview2_long.mp4", "short": "cs_ep04v2_preview2_cold_open_9x16.mp4", "a2": "cs_ep04v2_preview_a2.mp4", "a3": "cs_ep04v2_preview_a3.mp4", "a4": "cs_ep04v2_preview_a4.mp4", "full": "cs_ep04v2_full.mp4"})
class _Aud(dict):
    def __missing__(self, k):
        return "short" if k.startswith("sh") else "long"


AUD = _Aud({"long": "long", "short": "short", "a2": "long", "a3": "long", "a4": "long", "full": "long"})    # which master spec a preview file follows
class _Col(dict):
    def __missing__(self, k):
        return f"Short {k[2:]} · 9:16"


COL = _Col({"long": "16:9", "short": "9:16", "a2": "Act 2 · 16:9", "a3": "Act 3 · 16:9", "a4": "Act 4 · 16:9", "full": "full episode · 16:9", "full_ru": "RU review copy · 16:9"})
MIN_SHOT, MAX_SHOT = 1.4, 8.0
FONTS = ROOT / "assets" / "fonts"


def master(pv: Path, kind: str, cfg: dict) -> Path:
    wav, silent, out = pv / f"mix_{kind}.wav", pv / f"v2_{kind}_silent.mp4", pv / OUT[kind]
    lim0 = R.LIMIT0_LONG if AUD[kind] == "long" else R.LIMIT0
    loud = R._gain_filter(wav, cfg["audio"].get("target_lufs", -14), lim0)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(silent), "-i", str(wav), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-af", R._master_af(loud, lim0), *R.AAC_ARGS, "-shortest", "-movflags", "+faststart", str(out)], check=True)
    R._gate_with_remaster(out, wav, loud, cfg, kind=AUD[kind], lim0=lim0)
    # Klot r7: the encoded file lands on the target too (the wav calibration can read ~1 dB hot after AAC); one more
    # constant-gain pass when the file reads more than 0.3 LU under the target and the true peak has room for it
    target = (cfg.get("audio") or cfg).get("target_lufs", -14)
    i, tp = R.measure_audio(out)
    room = R._ceiling(cfg, AUD[kind]) - 0.3 - tp
    if target - i > 0.3 and room > 0.1 and loud.startswith("volume="):
        g = float(loud.split("=")[1].rstrip("dB")) + min(target - i, room)
        loud2 = f"volume={g:.2f}dB"
        tmp = out.with_suffix(".lufs.mp4")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(silent), "-i", str(wav), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                        "-af", R._master_af(loud2, lim0), *R.AAC_ARGS, "-shortest", "-movflags", "+faststart", str(tmp)], check=True)
        i2, tp2 = R.measure_audio(tmp)
        if tp2 <= R._ceiling(cfg, AUD[kind]) and abs(target - i2) < abs(target - i):
            tmp.replace(out)
        else:
            tmp.unlink()
    return out


def decode(path: Path, sr: int = 48000) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:a", "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)


def rms_db(x: np.ndarray) -> float:
    return 20 * np.log10(float(np.sqrt(np.mean(x ** 2))) + 1e-12) if len(x) else -200.0


# ------------------------------------------------------------------------------------------------------------ checks
def c_max_still(shots, **_):
    return [f"{s['id']}: {s['end'] - s['start']:.2f} s on one picture (max {MAX_SHOT})" for s in shots if s["end"] - s["start"] > MAX_SHOT + 1e-6]


def c_min_shot(shots, **_):
    # a dial close-up of the safe is a quick cut by design (Klot: a dial turns <= 1.5 s, clicks <= 1 s): >= 0.9 s
    return [f"{s['id']}: only {s['end'] - s['start']:.2f} s (min {0.9 if s.get('quick') else MIN_SHOT})" for s in shots
            if s["end"] - s["start"] < (0.9 if s.get("quick") else MIN_SHOT) - 1e-6]


def c_same_object(shots, **_):
    """R36: consecutive shots on the same picture continue the camera (no jump at the cut)."""
    out = []
    for a, b in zip(shots, shots[1:]):
        ka, kb = a.get("img") or a.get("src"), b.get("img") or b.get("src")
        if ka and ka == kb and a.get("cam") and b.get("cam") and a.get("cont"):
            if any(abs(x - y) > 0.01 for x, y in zip(a["cam"][1], b["cam"][0])):
                out.append(f"{a['id']} -> {b['id']}: {ka} jumps from {a['cam'][1]} to {b['cam'][0]}")
    return out


def c_stt_voice(beats, **_):
    """The voice run's own line-by-line diff (medium.en): every line of the preview clean."""
    return [f"{b['id']}: {d}" for b in beats for d in b.get("diff", [])]


def c_stt_mix(beats, audio=None, **_):
    """Line by line on the FINAL mix (music + sfx under the voice): every word still heard."""
    if audio is None or any(b.get("en") for b in beats):  # the RU review copy: the English line check does not apply
        return []
    sr = 48000
    # the episode's stt_known: transcription slips already confirmed against the voice's phonemes (and its voice-only scan)
    ep = json.loads((ROOT / "episodes" / "0005-drip-pricing" / "script.json").read_text())
    known = [("Live Nation", "Lyve Nation")] + [(k["script"], k["heard"]) for k in ep.get("stt_known") or []]
    lines = [(b["start"], b["end"], b["id"]) for b in beats]
    texts = {b["id"]: b["text"] for b in beats}
    fails, _notes = sttdiff.check_lines(audio, sr, lines, texts, known=known)
    if fails:
        # whisper's slips can depend on the 0.1 s cut window ("$50" / "50" for "fifty dollars"): a failed line is heard
        # once more with a wider window; it passes only if that second hearing has no difference at all
        bad = {f.split(": ", 1)[0].split(" ", 1)[1] for f in fails}
        again, _n2 = sttdiff.check_lines(audio, sr, [x for x in lines if x[2] in bad], texts, known=known, pad=0.3)
        still = {f.split(": ", 1)[0].split(" ", 1)[1] for f in again}
        fails = [f for f in fails if f.split(": ", 1)[0].split(" ", 1)[1] in still]
    return fails


def c_voice_cuts(beats, voice=None, **_):
    """R33: silence (RMS < -45 dBFS) in the 30 ms before every line start and after every line end of the voice track."""
    if voice is None:
        return []
    sr, w, out = 24000, int(0.03 * 24000), []
    for b in beats:
        i, j = int(b["start"] * sr), int(b["end"] * sr)
        for a, z, where in ((i - w, i, "before start"), (j, j + w, "after end")):
            d = rms_db(voice[max(0, a):max(0, z)])
            if d > -45:
                out.append(f"{b['id']} {where}: {d:.1f} dBFS")
    return out


def c_hit_silence(silences, audio=None, **_):
    """One real second of silence after each brass hit: the final mix below -60 dBFS (30 ms ramps excluded)."""
    if audio is None:
        return []
    out = []
    for a, b in silences:
        d = rms_db(audio[int((a + 0.04) * 48000): int((b - 0.04) * 48000)])
        if d > -60:
            out.append(f"silence {a:.2f}-{b:.2f} s: {d:.1f} dBFS")
    return out


def c_audio_gate(kind, path=None, cfg=None, **_):
    if path is None:
        return []
    i, tp = R.measure_audio(path)
    ceil = R._ceiling(cfg, kind)
    out = []
    if tp > ceil:
        out.append(f"true peak {tp:.1f} dBTP > {ceil:.1f}")
    if abs(i - cfg["audio"].get("target_lufs", -14)) > 1.0:
        out.append(f"loudness {i:.1f} LUFS (target {cfg['audio'].get('target_lufs', -14)})")
    return out


def _tw(text: str, font: str, size: float) -> float:
    from PIL import ImageFont
    return ImageFont.truetype(str(FONTS / font), max(1, int(round(size)))).getlength(text)


def plates(data, shots, captions):
    """Screen-fixed plates the layer draws, as boxes over time (the same arithmetic as V2.tsx)."""
    W, H = data["W"], data["H"]
    short = H > W
    out = []
    for s in shots:
        if s.get("clock"):
            fs = round(H * 0.03)
            w = fs * 0.6 * 2 + fs * 1.5 + fs * 0.5 + _tw(f"TUE · {s['clock']} PM", "ArchivoBlack-Regular.ttf", fs) + 4
            h = fs * 0.35 * 2 + max(fs * 1.5, fs * 1.2) + 4
            out.append(("clock", s["start"], s["end"], [W - 40 - w, 36, W - 40, 36 + h]))
        if s["kind"] == "archive" or s.get("caption"):
            fs = 30 if not short else 34
            maxw = W * (0.6 if not short else 0.88)
            tw = _tw(s["caption"], "PT_Serif-Web-Regular.ttf", fs)
            lines = 1 if tw <= maxw - 40 else 2
            w = min(maxw, tw + 40)
            h = lines * fs * 1.25 + 20
            box = [48, H * 0.8 - h, 48 + w, H * 0.8] if not short else [(W - maxw) / 2, 150, (W + maxw) / 2, 150 + h]
            out.append(("archive caption", s["start"], s["end"], box))
        ncs = ([s["namecard"]] if s.get("namecard") else []) + [o for o in s.get("overs", []) if o.get("t") == "namecard"]
        for nc in ncs:
            x0, y0, x1, y1 = nc["box_short"] if short and nc.get("box_short") else nc["box"]
            b = data.get("band") or [0, 0, W, H]
            out.append(("name card", s["start"], s["end"], [b[0] + x0 * b[2], b[1] + y0 * b[3], b[0] + x1 * b[2], b[1] + y1 * b[3]]))
    for c in captions:
        font = "Anton-Regular.ttf" if short else "ArchivoBlack-Regular.ttf"
        txt = " ".join(w[0].upper() if short else w[0] for w in c["words"])
        size = round(H * (0.042 if short else 0.05))
        tw = _tw(txt, font, size)
        if tw > W * 0.86:
            size *= W * 0.86 / tw
            tw = W * 0.86
        y = H * 0.82 if short else H * 0.865 - size * 0.62
        out.append(("subtitle", c["start"] - 0.05, c["end"] + 0.25, [(W - tw) / 2, y, (W + tw) / 2, y + size * 1.3]))
    return out


def c_plate_fit(data=None, shots=None, captions=None, **_):
    """R26: every plate inside the frame with >= 24 px margin, never overlapping another plate on screen at the same time."""
    W, H = data["W"], data["H"]
    P = plates(data, shots, captions)
    out = []
    for name, a, b, (x0, y0, x1, y1) in P:
        if x0 < 24 or y0 < 24 or x1 > W - 24 or y1 > H - 24:
            out.append(f"{name} {a:.1f}-{b:.1f} s: box {[round(v) for v in (x0, y0, x1, y1)]} closer than 24 px to the edge")
    for i in range(len(P)):
        for j in range(i + 1, len(P)):
            n1, a1, b1, r1 = P[i]
            n2, a2, b2, r2 = P[j]
            if n1 == n2 == "subtitle":
                continue
            if min(b1, b2) - max(a1, a2) > 0.05 and r1[0] < r2[2] and r2[0] < r1[2] and r1[1] < r2[3] and r2[1] < r1[3]:
                out.append(f"{n1} overlaps {n2} at {max(a1, a2):.1f} s")
    return out


def c_card_text_margin(shots=None, data=None, **_):
    """R30: typed card text starts right of the red margin line (>= 16 px)."""
    out = []
    for s in shots:
        if s.get("namecard") or any(o.get("t") == "namecard" for o in s.get("overs", [])):
            b = data.get("band") or [0, 0, data["W"], data["H"]]
            u = min(b[2] / 1920, b[3] / 1080)
            nc = s.get("namecard") or next(o for o in s["overs"] if o.get("t") == "namecard")
            gap = nc.get("text_dx_px", 22)  # V2.tsx NameCard: text 22 px right of the line, at any scale
            if gap < 16:
                out.append(f"{s['id']}: name text {gap:.0f} px from the margin line")
    return out


def c_text_lint(shots=None, **_):
    """Klot r89 text style on every on-screen string of the plan."""
    out, txt = [], []

    def walk(o, where):
        if isinstance(o, str):
            if re.search(r"[A-Za-z$£0-9]", o) and not o.startswith("v2/") and not o.endswith((".jpg", ".mp4", ".png")):
                txt.append((where, o))
        elif isinstance(o, dict):
            for k, v in o.items():
                if k not in ("id", "beat", "act", "kind", "mode", "src", "img", "video", "picture", "source", "file", "what", "clock"):
                    walk(v, f"{where}.{k}")
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, f"{where}[{i}]")
    for s in shots:
        walk(s, s["id"])
    for where, t in txt:
        if re.search(r"\d %", t):
            out.append(f"{where}: space before % in {t!r}")
        if re.search(r"(?<!·) {2,}(?!·)", t):
            out.append(f"{where}: double space in {t!r}")
    for s in shots:
        for k in ("text", "total", "badge", "stamp"):
            v = s.get(k)
            if isinstance(v, str) and re.search(r"(^|\s)[a-z]", v):
                out.append(f"{s['id']}.{k}: lowercase on a number card / stamp {v!r}")
    j = "\n".join(t for _, t in txt)
    if "'" in j and "’" in j:
        out.append("straight and curly apostrophes mixed")
    return out


def c_count_up(shots=None, **_):
    """R39: numbers appear whole (no count-up anywhere in the layer's plan)."""
    return [f"{s['id']}: count-up" for s in shots if s.get("countup")]


def c_captions(captions=None, **_):
    """R23: >= 2 words per card (a one-word sentence excepted), no card ends on a dangling word mid-sentence."""
    from factory.captions import _dangles
    out = []
    for c in captions:
        ws = [w[0] for w in c["words"]]
        if len(ws) == 1 and not re.search(r"[.!?…]$", ws[0]):
            out.append(f"{c['start']:.1f} s: lone word {ws[0]!r}")
        if not re.search(r"[.!?…,:;—-]$", ws[-1]) and _dangles(ws[-1]):
            out.append(f"{c['start']:.1f} s: card ends on {ws[-1]!r}")
    return out


def c_sfx_sync(sfx=None, ink=None, **_):
    """R34: marker scratch only while ink is being laid (every scribble inside a stroke span, none > 80 ms after pen lift)."""
    out = []
    for a, b, kind in sfx:
        if kind.startswith("scribble"):
            if not any(a >= x - 0.05 and b <= y + 0.08 for x, y in ink):
                out.append(f"scribble {a:.2f}-{b:.2f} s outside any stroke")
    return out


def c_shorts_band(data=None, **_):
    """R38: the Shorts picture band >= 50 % of the frame height."""
    if data["H"] <= data["W"]:
        return []
    return [] if data["band"][3] / data["H"] >= 0.5 else [f"band {data['band'][3] / data['H']:.0%} of the height"]


def _io(p):  # Remotion Easing.inOut(Easing.cubic)
    p = min(1.0, max(0.0, p))
    return 4 * p ** 3 if p < 0.5 else 1 - (-2 * p + 2) ** 3 / 2


def cam_track(s, SW, SH, fps=30, per_frame_clamp=False):
    """Screen position of four picture points, frame by frame, with V2.tsx's camera math (fitted ends, eased)."""
    iw, ih = (s.get("iw"), s.get("ih")) if s["kind"] != "clip" else (1920, 1094)
    iw, ih = iw or 1920, ih or 1094
    base = max(SW / iw, SH / ih)

    def fit(c):
        sc = base * c[2]
        hx, hy = SW / (iw * sc) / 2, SH / (ih * sc) / 2
        return [min(max(c[0], hx), 1 - hx), min(max(c[1], hy), 1 - hy), c[2]]
    a, b = (s["cam"] if per_frame_clamp else (fit(s["cam"][0]), fit(s["cam"][1])))
    dur = s["end"] - s["start"]
    pts = [(0.25, 0.25), (0.75, 0.25), (0.25, 0.75), (0.75, 0.75)]
    out = []
    for k in range(int(dur * fps) + 1):
        p = _io(k / fps / dur)
        cx, cy, z = (a[i] + (b[i] - a[i]) * p for i in range(3))
        sc = base * z
        tx, ty = SW / 2 - cx * iw * sc, SH / 2 - cy * ih * sc
        if per_frame_clamp:
            tx, ty = min(max(tx, SW - iw * sc), 0), min(max(ty, SH - ih * sc), 0)
        if s.get("_shake"):  # planted bug: a camera that shakes (integer crops, a wobbling track)
            tx += s["_shake"] * ((k * 7919) % 3 - 1)
        out.append([(tx + x * iw * sc, ty + y * ih * sc) for x, y in pts])
    return out


def c_jitter(shots=None, data=None, per_frame_clamp=False, **_):
    """R28 (as qc.jitter_check: from the plan, the exact camera the layer draws): on every picture shot, four picture
    points move monotonically per axis; no reversal > 0.25 px frame to frame. Remotion draws the transform in float."""
    b = data.get("band") or [0, 0, data["W"], data["H"]]
    SW, SH = b[2], b[3]
    out = []
    for s in shots:
        if not s.get("cam") or not (s["kind"] in ("still", "archive", "clip") or (s["kind"] == "pic" and s.get("iw"))):
            continue
        tr = cam_track(s, SW, SH, per_frame_clamp=per_frame_clamp)
        for j in range(4):
            for ax in (0, 1):
                v = [tr[k + 1][j][ax] - tr[k][j][ax] for k in range(len(tr) - 1)]
                sgn = 0
                for k, x in enumerate(v):
                    if abs(x) < 1e-6:
                        continue
                    if sgn and (x > 0) != (sgn > 0) and abs(x) > 0.25:
                        out.append(f"{s['id']}: point {j} {'xy'[ax]} reverses at {s['start'] + k / 30:.2f} s ({x:.2f} px)")
                        break
                    if abs(x) > 0.05:
                        sgn = 1 if x > 0 else -1
    return sorted(set(out))


def c_decode(path=None, **_):
    if path is None:
        return []
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "null", "-"], capture_output=True, text=True)
    return [r.stderr.strip()[:300]] if r.stderr.strip() else []


def c_shorts_length(data=None, **_):
    if data["H"] <= data["W"]:
        return []
    return [] if data["end"] <= 45.0 else [f"{data['end']:.1f} s > 45 s"]


def c_short_loop(shots=None, data=None, **_):
    """A Short loops: the file ends on its last picture (no empty tail before it starts again)."""
    if data["H"] <= data["W"]:
        return []
    tail = data["frames"] / data["fps"] - max(s["end"] for s in shots)
    return [] if tail <= 1.5 / data["fps"] else [f"{tail:.2f} s of empty frame after the last picture"]


def c_picture_first(shots=None, data=None, **_):
    """R41: >= 85% of screen time on a picture base (flat only: act titles and key numbers, <= 4 key numbers);
    a placeholder for a still not yet delivered counts as NOT a picture."""
    tot = sum(s["end"] - s["start"] for s in shots) or 1
    flat = sum(s["end"] - s["start"] for s in shots if s.get("base_kind") == "flat") + sum(1.9 for s in shots if s.get("title"))
    miss = sum(s["end"] - s["start"] for s in shots if s.get("base_kind") == "missing" or s["kind"] in ("missing",))
    old = sum(s["end"] - s["start"] for s in shots if s["kind"] not in ("pic", "missing", "still", "archive", "clip"))
    pic = 1 - (flat + miss + old) / tot
    keys = sum(1 for s in shots if s.get("base_kind") == "flat")
    out = []
    if pic < 0.85:
        out.append(f"picture base {pic:.0%} of screen time (placeholders {miss / tot:.0%}, flat {flat / tot:.0%}, old flat kinds {old / tot:.0%})")
    if keys > 4:
        out.append(f"{keys} flat key-number cards (max 4 per episode)")
    return out


CAP = {"os": 0.688, "row": 0.688, "fee": 0.688, "lab": 0.689, "tot": 0.688}  # cap height / em of the fonts used for them
READ_MIN = 0.028  # Klot note 5: any line we want read is >= 2.8 % of the frame tall (cap height)


def _frame_quad(s, SW, SH, end):
    """The screen quad in frame px at the start (end=0) or end (end=1) of the shot, with V2.tsx's camera math."""
    iw, ih = s["iw"], s["ih"]
    base = max(SW / iw, SH / ih)
    c = s["cam"][end]
    sc = base * c[2]
    hx, hy = SW / (iw * sc) / 2, SH / (ih * sc) / 2
    cx, cy = min(max(c[0], hx), 1 - hx), min(max(c[1], hy), 1 - hy)
    tx, ty = SW / 2 - cx * iw * sc, SH / 2 - cy * ih * sc
    return [(tx + x * sc, ty + y * sc) for x, y in s["quad"]], sc


def c_read_size(shots=None, data=None, **_):
    """R45 (Klot note 5): on checkout screens with lines we want read (order summary, fee lines, the joke lines), every such
    line's cap height >= 2.8 % of the frame height, at the shot's widest framing. Sizes come from the plan (screen.fs)."""
    if data["H"] > data["W"]:
        return []  # judged on the 16:9 film (the 9:16 file is a layout sample of the cold open)
    out = []
    for s in shots:
        sc_ = s.get("screen") or {}
        if sc_.get("mode") not in ("fees", "total", "pay") or not s.get("quad"):
            continue
        fs = sc_.get("fs") or {"os": 24, "row": 30, "fee": 34, "lab": 30, "tot": 38}
        keys = ["os", "row"] + (["fee"] if sc_["mode"] == "fees" else ["tot"]) + (["lab"] if any(f.get("label") for f in sc_.get("fees", [])) else [])
        cap_u = min(fs[k] * CAP[k] for k in keys)
        worst = None
        for e in (0, 1):
            q, _sc = _frame_quad(s, data["W"], data["H"], e)
            unit = (q[1][0] - q[0][0]) / 1240  # frame px per screen unit along the top edge (the narrowest)
            px = cap_u * unit
            worst = px if worst is None else min(worst, px)
        if worst < READ_MIN * data["H"]:
            out.append(f"{s['id']}: smallest read line {worst:.1f} px cap height < {READ_MIN * data['H']:.1f} px (2.8 %)")
    return out


def c_screen_marks(shots=None, data=None, **_):
    """R44 (Klot note 3): stamps and marks on a screen stay inside the screen: a stamp over a laptop screen is drawn in screen
    space and its box sits inside the page with >= 30 units of margin; no frame-space stamp may overlap a screen."""
    out = []
    W, H = data["W"], data["H"]
    for s in shots:
        sc_ = s.get("screen") or {}
        st = sc_.get("stamp")
        if st:
            size = st["size"]
            w = _tw(st["text"], "Anton-Regular.ttf", size) + 0.6 * size + 0.18 * size
            h = size * 1.28 + 0.18 * size
            import math
            a = math.radians(abs(st.get("rot", -8)))
            bw, bh = w * math.cos(a) + h * math.sin(a), w * math.sin(a) + h * math.cos(a)
            x0, x1, y0, y1 = st["x"] - bw * 0.55, st["x"] + bw * 0.55, st["y"] - bh * 0.55, st["y"] + bh * 0.55  # 1.1 x: the drop-in
            if x0 < 30 or y0 < 30 or x1 > 1240 - 30 or y1 > 642 - 30:
                out.append(f"{s['id']}: stamp {st['text']!r} box {x0:.0f}..{x1:.0f} x {y0:.0f}..{y1:.0f} leaves the screen (1240 x 642, margin 30)")
        if s.get("quad") and sc_:
            for o in s.get("overs", []):
                if o.get("t") != "stamp":
                    continue
                for e in (0, 1):
                    q, _ = _frame_quad(s, W, H, e)
                    xs, ys = [p[0] for p in q], [p[1] for p in q]
                    r = o["size"] * min(W / 1920, H / 1080)
                    if min(xs) - r * 2 < o["x"] * W < max(xs) + r * 2 and min(ys) - r < o["y"] * H < max(ys) + r:
                        out.append(f"{s['id']}: frame-space stamp {o['text']!r} over the laptop screen (draw it in screen space)")
                        break
    return out


def c_face_cut(shots=None, **_):
    """R46 (Klot note 8): no more than two laptop-screen shots without a cut to Larry's face in between (screens 10 s or
    more apart are not 'back to back')."""
    out, run, last = [], [], None
    for s in shots:
        if s.get("screen"):
            if last is not None and s["start"] - last >= 10.0:
                run = []
            run.append(s["id"])
            last = s["end"]
            if len(run) > 2:
                out.append(f"{', '.join(run)}: {len(run)} screens without a face cut")
        elif s.get("face"):
            run = []
    return out


def c_ink_hold(shots=None, **_):
    """R47 (Klot note 7): the hand leaves after writing and the finished mark is seen clean for >= 0.5 s before the cut."""
    out = []
    for k, s in enumerate(shots):
        ink = s.get("_ink") or []
        if not ink:
            continue
        nxt = shots[k + 1] if k + 1 < len(shots) else {}
        if s.get("cont") and nxt.get("img") == s.get("img"):
            continue  # the next shot continues on the same picture with the marks in place: the mark is seen there
        free = s["end"] - (max(b for _a, b in ink) + 0.4)
        if free < 0.5:
            out.append(f"{s['id']}: the mark is seen without the hand for {free:.2f} s before the cut (< 0.5 s)")
    return out


# ---------------------------------------------------------------- Klot's frame review (PREVIEW 2 + ACT 2): DOM checks
# They read dom.json (tools/v2_dom_qc.py: the real composition rendered in Chromium at a settled frame of every shot and
# every 0.1 s while a hand is on screen): the hand's tip, the faces of the picture (faces.json), every mark/tag, every text.
_HAND_ALPHA = None


def _hand_alpha():
    global _HAND_ALPHA
    if _HAND_ALPHA is None:
        from PIL import Image
        _HAND_ALPHA = np.asarray(Image.open(ROOT / "assets" / "hands" / "hand_ink_cuff.png").convert("RGBA"))[..., 3]
    return _HAND_ALPHA


def _frame(dom_k):
    b = dom_k.get("band")
    return (b[0], b[1], b[0] + b[2], b[1] + b[3]) if b else (0, 0, dom_k["W"], dom_k["H"])


def _inter(a, b):
    return max(0.0, min(a[2], b[2]) - max(a[0], b[0])) * max(0.0, min(a[3], b[3]) - max(a[1], b[1]))


def _covered(hand, box, fr):
    """fraction of the visible part of a face box under the opaque part of the hand (R37 hand image, turned 18 deg)"""
    al = _hand_alpha()
    s = 0.62 * hand["sh"] / 1024
    c, sn = np.cos(np.radians(18)), np.sin(np.radians(18))
    x0, y0, x1, y1 = max(box[0], fr[0]), max(box[1], fr[1]), min(box[2], fr[2]), min(box[3], fr[3])
    if x1 - x0 < 4 or y1 - y0 < 4:
        return 0.0
    xs, ys = np.meshgrid(np.linspace(x0, x1, 12), np.linspace(y0, y1, 12))
    dx, dy = xs - hand["tip"][0], ys - hand["tip"][1]
    u = (dx * c + dy * sn) / s + 188
    v = (-dx * sn + dy * c) / s + 456
    ok = (u >= 0) & (u < al.shape[1]) & (v >= 0) & (v < al.shape[0])
    hit = np.zeros_like(ok)
    hit[ok] = al[v[ok].astype(int), u[ok].astype(int)] > 128
    return float(hit.mean())


def c_hand_over_face(dom=None, **_):
    """Klot: the drawing hand never covers a face (or a stamp hand a face) — <= 12 % of any visible face for <= 0.1 s."""
    if not dom:
        return ["no dom.json (DOM sampling did not run)"]
    out, streak = [], {}
    fr = _frame(dom)
    for smp in dom["samples"]:
        hits = []
        for f in (x for x in smp.get("faces", []) if x["kind"] == "face"):
            if _inter(f["box"], fr) < 0.2 * max(1.0, (f["box"][2] - f["box"][0]) * (f["box"][3] - f["box"][1])):
                continue
            cov = max([_covered(h, f["box"], fr) for h in smp.get("hands", [])] + [
                _inter(b, f["box"]) / max(1.0, (f["box"][2] - f["box"][0]) * (f["box"][3] - f["box"][1])) for b in smp.get("stampHands", [])] + [0.0])
            if cov > 0.12:
                hits.append(cov)
        key = smp["shot"]
        if hits:
            streak[key] = streak.get(key, 0) + 1
            if streak[key] == 2:
                out.append(f"{key} at {smp['t']:.1f} s: the hand covers {max(hits):.0%} of a face")
        else:
            streak[key] = 0
    return out


def c_text_size_contrast(dom=None, **_):
    """Klot: any text we want read: cap height >= 2.8 % of the frame (9:16: of the picture band) and WCAG contrast >= 4.5:1
    against what is right behind it; measured on the settled frame of every shot."""
    if not dom:
        return ["no dom.json (DOM sampling did not run)"]
    fr = _frame(dom)
    need = 0.028 * (fr[3] - fr[1])
    out = []
    for smp in dom["samples"]:
        if not smp.get("shotpic"):
            continue
        for r in smp.get("reads", []):
            area = max(1.0, (r["box"][2] - r["box"][0]) * (r["box"][3] - r["box"][1]))
            if _inter(r["box"], fr) < 0.5 * area:
                continue
            if r.get("cap", 99) < need - 0.5:
                out.append(f"{smp['shot']}: '{r['text']}' cap height {r['cap']:.0f} px < {need:.0f} px")
            if r.get("contrast") is not None and r["contrast"] < 4.5:
                out.append(f"{smp['shot']}: '{r['text']}' contrast {r['contrast']:.1f}:1 < 4.5:1")
    return out


def c_edge_margin(dom=None, **_):
    """Klot: every mark, tag, plate and stamp sits >= 6 % inside the frame (9:16: the picture band), on the settled frame."""
    if not dom:
        return ["no dom.json (DOM sampling did not run)"]
    fr = _frame(dom)
    mx, my = 0.06 * (fr[2] - fr[0]), 0.06 * (fr[3] - fr[1])
    out = []
    for smp in dom["samples"]:
        if not smp.get("shotpic"):
            continue
        for m in smp.get("marks", []):
            b = m["box"]
            if b[2] - b[0] > 0.9 * (fr[2] - fr[0]):
                continue
            if b[0] < fr[0] + mx - 1 or b[1] < fr[1] + my - 1 or b[2] > fr[2] - mx + 1 or b[3] > fr[3] - my + 1:
                out.append(f"{smp['shot']}: {m['kind']} '{m['text']}' at {[round(v) for v in b]} is within 6 % of the edge")
    return out


def c_tag_face(dom=None, **_):
    """Klot: tags, plates and stamps never sit on a face or a hand of the picture (overlap <= 5 % of it)."""
    if not dom:
        return ["no dom.json (DOM sampling did not run)"]
    out = []
    for smp in dom["samples"]:
        if not smp.get("shotpic"):
            continue
        for f in smp.get("faces", []):
            fa = max(1.0, (f["box"][2] - f["box"][0]) * (f["box"][3] - f["box"][1]))
            for m in smp.get("marks", []):
                if _inter(m["box"], f["box"]) > 0.05 * fa:
                    out.append(f"{smp['shot']}: {m['kind']} '{m['text']}' sits on a {f['kind']}")
    return sorted(set(out))


# ---------------------------------------------------------------- plan checks
def c_stamp_hold(shots=None, **_):
    """Klot: a stamp's impression is seen >= 0.8 s before the cut (the stamp lands at t, presses 0.13 s)."""
    out = []
    for s in shots:
        ats = [o.get("at_") for o in s.get("overs", []) if o.get("t") == "stamp"] + [o.get("stamp_") for o in s.get("overs", []) if o.get("t") == "namecard"]
        st = (s.get("screen") or {}).get("stamp")
        if st:
            ats.append(st.get("at_"))
        for a in (x for x in ats if x is not None):
            seen = (s["end"] - s["start"]) - (a + 0.13)
            if seen < 0.8:
                out.append(f"{s['id']}: the stamp is seen {seen:.2f} s before the cut (< 0.8 s)")
    return out


def c_ui_state(shots=None, **_):
    """Klot: checkout A and checkout B show the same thing everywhere (A = $48 fees included, B = $30, fees at the end)."""
    seen, out = {}, []
    for s in shots:
        for sc in (s.get("screen"), s.get("screen2")):
            if not sc or not str(sc.get("head", "")).startswith("CHECKOUT "):
                continue
            sig = (sc.get("mode"), sc.get("price"), sc.get("late"), sc.get("sub"))
            k = sc["head"]
            if k in seen and seen[k][0] != sig:
                out.append(f"{s['id']}: {k} shows {sig}, but {seen[k][1]} showed {seen[k][0]}")
            seen.setdefault(k, (sig, s["id"]))
    return out


def c_card_not_empty(shots=None, **_):
    """Klot: a key-number card is never empty navy: its number is up within 0.3 s of the cut."""
    return [f"{s['id']}: {s.get('key')} appears {(s.get('at_') if s.get('at_') is not None else s.get('at', 0.15)):.2f} s into the card"
            for s in shots if s.get("base_kind") == "flat" and (s.get("at_") if s.get("at_") is not None else s.get("at", 0.15)) > 0.3]


def _framing(s):
    c = s.get("cam") or [[0.5, 0.5, 1], [0.5, 0.5, 1]]
    return c[1]


def c_repeat_shot(shots=None, **_):
    """Klot: the same picture with the same framing (centre within 0.1, zoom within 0.2) at most twice in any 60 s."""
    out = []
    pics = [s for s in shots if s.get("img") or s.get("video")]
    for i, s in enumerate(pics):
        same = [x for x in pics if (x.get("img") or x.get("video")) == (s.get("img") or s.get("video")) and 0 <= x["start"] - s["start"] < 60
                and abs(_framing(x)[0] - _framing(s)[0]) < 0.1 and abs(_framing(x)[1] - _framing(s)[1]) < 0.1 and abs(_framing(x)[2] - _framing(s)[2]) < 0.2]
        if len(same) > 2:
            out.append(f"{', '.join(x['id'] for x in same)}: the same picture and framing {len(same)}x within 60 s")
    return sorted(set(out))


PLAIN = {"n1", "n4", "a4", "l1", "l13", "sub", "x1", "x1clip"}  # Ep.4 objects drawn on plain cream


def c_plain_background(shots=None, **_):
    """Klot: no object on a plain background (act titles and <= 4 key numbers excepted): it sits in a picture of a place."""
    return [f"{s['id']}: {s.get('base')} is an object on plain cream" for s in shots if s.get("base") in PLAIN]


def c_dial_run(shots=None, **_):
    """Klot: per lock the dial turns <= 1.5 s and clicks <= 1 s, never more than 2 s of dial close-ups in a row; the wide
    safe <= 3.5 s."""
    out, run, ids = [], 0.0, []
    for s in shots:
        is_safe = "a2_safe" in str(s.get("img", ""))
        zoom = (s.get("cam") or [[0, 0, 1]])[0][2]
        d = s["end"] - s["start"]
        if is_safe and zoom >= 2.0:
            run += d
            ids.append(s["id"])
            if run > 2.05:
                out.append(f"{', '.join(ids)}: {run:.1f} s of dial close-ups in a row")
        else:
            run, ids = 0.0, []
            if is_safe and d > 3.55 and not s.get("title"):
                out.append(f"{s['id']}: the wide safe for {d:.1f} s")
    return sorted(set(out))


MODERN = re.compile(r"\b(online|website|web site|app|laptop|internet|click|tab|screen)s?\b", re.I)


def c_tool_touch(shots=None, **_):
    """R49 (Klot r8): an object that acts on another (scissors, stamp, pen) touches its target in the picture. A tool drawn
    by code over a still never touches anything (the old floating scissors over the bomb): it is not allowed."""
    return [f"{s['id']}: code-drawn {o['t']} over the picture (the tool must touch its target in the still)"
            for s in shots for o in (s.get("overs") or []) if o.get("t") in ("wires", "scissors")]


def c_archive_era(shots=None, beats=None, **_):
    """R48: an archive photo only under a line about general behaviour (no date) or within +-10 years of the year spoken;
    its caption shows its real year; never a date plate of 1970 or later on a photo from before 1970."""
    from v2_preview_a2 import ARCHIVE_YEAR
    import asset_license as AL
    rows = AL.load()
    text = {b["id"]: b["text"] for b in (beats or [])}
    out = []
    for s in shots:
        # tooling v2: the photo's year is the archive item's own date (docs/ASSET_LICENSES.md, from the fetcher's sidecar)
        reg = next((AL.find(s[k], rows) for k in ("img", "video") if s.get(k)), None)
        ry = AL.year_of_row(reg) if reg and reg.get("kind") == "archive" else None
        y = ry if ry is not None else ARCHIVE_YEAR.get(s.get("base"))
        if ry is not None and ARCHIVE_YEAR.get(s.get("base")) not in (None, ry):
            out.append(f"{s['id']}: the plan says {ARCHIVE_YEAR[s['base']]}, the archive item is dated {ry}")
        if y is None:
            m = re.search(r"\b(1[89]\d\d)\b[^·]*· Library of Congress", s.get("caption") or "")
            y = int(m.group(1)) if m else None
        if y is None:
            continue
        line = text.get(s["beat"], "")
        for yy in (int(v) for v in re.findall(r"\b(19\d\d|20\d\d)\b", line)):
            if abs(yy - y) > 10:
                out.append(f"{s['id']}: a {y} photo under a line about {yy}")
        if MODERN.search(line):
            out.append(f"{s['id']}: a {y} photo under '{MODERN.search(line).group(0)}' (a modern thing)")
        for o in s.get("overs", []):
            for yy in (int(v) for v in re.findall(r"\b(19\d\d|20\d\d)\b", str(o.get("text", "")))):
                if yy >= 1970 and y < 1970:
                    out.append(f"{s['id']}: date plate {yy} on a {y} photo")
        if s.get("caption") and str(y) not in s["caption"]:
            out.append(f"{s['id']}: the caption does not show the photo's year {y}")
    return out


def c_clip_native(shots=None, data=None, **_):
    """R51 (Klot, Nov 7): an AI clip plays at its native speed (no slow-motion stretch: rate 1.0); a beat that needs more
    time holds the last frame with a slow push-in or cuts to a still; a clip used for more than 5 s carries its reason
    ("long_reason") from the shot list. Applies to plans made under R51 (data["r51"]); Ep.4 v2 predates it."""
    if not (data or {}).get("r51"):
        return []
    out = []
    for s in shots or []:
        if not s.get("video"):
            continue
        r = float(s.get("rate", 1.0))
        if abs(r - 1.0) > 0.005:
            out.append(f"{s['id']}: {s['video']} slowed to {r:.2f}x (R51: native speed only)")
        used = (s["end"] - s["start"]) * r
        if used > 5.05 and not s.get("long_reason"):
            out.append(f"{s['id']}: {used:.1f} s of AI clip with no reason in the shot list (R51: > 5 s only where needed)")
    return out


def c_asset_license(plan_kind=None, **_):
    """Tooling v2 / R50: every asset the render uses (pictures, clips, fonts, music, SFX, voice, overlays, Lottie) has a
    row in docs/ASSET_LICENSES.md. Release-blocking. Rows without the AI model / licence / item date are reported as
    incomplete (asset_license_incomplete, not blocking)."""
    import asset_license as AL
    if not plan_kind:
        return ["no plan to read the assets from"]
    miss, _inc = AL.check(AL.used_assets(plan_kind))
    return [f"{m}: no row in docs/ASSET_LICENSES.md" for m in miss]


END_MIN, END_MAX = 20.0, 22.0


def c_end_screen(shots=None, beats=None, data=None, dom=None, **_):
    """Klot (locked): a file that ends the episode carries a 20-22 s end screen: the last line ('Subscribe ...') then music
    only (next-case sketch, subscribe); during those seconds YouTube's zones stay free of our marks and text
    (right third: the video element; bottom-left: the subscribe button)."""
    if not shots or not any(s.get("endscreen") for s in shots):
        return []
    out = []
    end = data["end"] if data else shots[-1]["end"]
    last = max(beats, key=lambda b: b["start"])
    t0 = max(s["start"] for s in shots if s.get("beat") == last["id"])
    if not END_MIN <= end - t0 <= END_MAX:
        out.append(f"end screen {end - t0:.1f} s (from the last line's shot to the end; wants {END_MIN:.0f}-{END_MAX:.0f} s)")
    if end - last["end"] < END_MIN - 7.0:
        out.append(f"only {end - last['end']:.1f} s of music after the last word")
    if dom:
        W, H = dom["W"], dom["H"]
        zones = {"right (video element)": (0.62 * W, 0, W, H), "bottom-left (subscribe)": (0, 0.75 * H, 0.35 * W, H)}
        for smp in dom["samples"]:
            if smp["t"] < end - END_MAX or not smp.get("shotpic"):
                continue
            for m in smp.get("marks", []) + smp.get("reads", []):
                for zn, z in zones.items():
                    if _inter(m["box"], z) > 0.15 * max(1.0, (m["box"][2] - m["box"][0]) * (m["box"][3] - m["box"][1])):
                        out.append(f"{smp['shot']}: '{m.get('text', '')}' in the YouTube {zn} zone")
    return sorted(set(out))


CHECKS = [
    ("picture_first (R41)", c_picture_first, "picture base >= 85% of screen time, <= 4 key numbers"),
    ("decode", c_decode, "file decodes end to end without an error"),
    ("max_still", c_max_still, "no picture longer than 8 s"),
    ("min_shot", c_min_shot, "no shot shorter than 1.4 s"),
    ("same_object (R36)", c_same_object, "same picture keeps its camera across a cut"),
    ("stt_voice (r89)", c_stt_voice, "voice run: every line diffed, zero differences"),
    ("stt_mix (r89)", c_stt_mix, "final mix, line by line: zero differences"),
    ("voice_cuts (R33)", c_voice_cuts, "silence on both sides of every line edge"),
    ("hit_silence", c_hit_silence, "one real second of silence after each brass hit"),
    ("audio_gate (14)", c_audio_gate, "-14 LUFS, true peak <= -1.5 (long) / -1.0 dBTP (9:16)"),
    ("plate_fit (R26)", c_plate_fit, "plates inside the frame (>= 24 px), no overlaps"),
    ("card_text_margin (R30)", c_card_text_margin, "typed text right of the red margin line"),
    ("text_lint (r89)", c_text_lint, "on-screen text style"),
    ("count_up (R39)", c_count_up, "numbers appear whole"),
    ("captions (R23)", c_captions, "subtitle cards: no lone words, no dangling ends"),
    ("sfx_sync (R34)", c_sfx_sync, "scratch only while ink is laid"),
    ("jitter (R28)", c_jitter, "camera path: no reversal > 0.25 px (plan, as drawn)"),
    ("shorts_band (R38)", c_shorts_band, "9:16 picture band >= 50 %"),
    ("short_loop", c_short_loop, "a Short ends on its last picture (loops cleanly)"),
    ("read_size (R45)", c_read_size, "checkout lines we want read: cap height >= 2.8 % of the frame (16:9)"),
    ("screen_marks (R44)", c_screen_marks, "stamps on a screen stay inside the screen (screen space, 30-unit margin)"),
    ("face_cut (R46)", c_face_cut, "no more than 2 laptop screens in a row without Larry's face"),
    ("ink_hold (R47)", c_ink_hold, "the hand leaves; the finished mark is seen >= 0.5 s before the cut"),
    ("hand_over_face", c_hand_over_face, "the drawing / stamp hand covers no face (<= 12 % for <= 0.1 s)"),
    ("text_size_contrast", c_text_size_contrast, "text we want read: cap >= 2.8 % of the frame (9:16: band), contrast >= 4.5:1"),
    ("edge_margin", c_edge_margin, "marks, tags, plates, stamps >= 6 % inside the frame"),
    ("tag_face", c_tag_face, "no tag, plate or stamp on a face or a hand"),
    ("stamp_hold", c_stamp_hold, "a stamp is seen >= 0.8 s before the cut"),
    ("ui_state_consistency", c_ui_state, "checkout A / B identical in every shot"),
    ("card_not_empty", c_card_not_empty, "a key-number card shows its number within 0.3 s"),
    ("repeat_shot", c_repeat_shot, "same picture + framing <= 2x per 60 s"),
    ("plain_background", c_plain_background, "no object on a plain background"),
    ("dial_run", c_dial_run, "<= 2 s of dial close-ups in a row; wide safe <= 3.5 s"),
    ("end_screen", c_end_screen, "end screen 20-22 s, music only after the last line, YouTube zones free"),
    ("tool_touch (R49)", c_tool_touch, "a tool acting on an object touches it in the still (no code-drawn scissors)"),
    ("archive_era (R48)", c_archive_era, "archive photo year (the item's own date) within +-10 y of the line (or no date); real year in the caption; no modern plate"),
    ("asset_license (R50)", c_asset_license, "every asset used has a row in docs/ASSET_LICENSES.md (release-blocking)"),
    ("clip_native (R51)", c_clip_native, "AI clips at native speed (no slow-mo stretch); > 5 s of clip only with a stated reason"),
]
NOT_APPLICABLE = {
    "hand_over_ink (R37), one hand at a time (rules 1-5)": "by construction (ink only behind the nib, one hand at a time, pen colour = ink colour); the hand's position against the faces is checked (hand_over_face, from the rendered DOM)",
    "mark_on_object (R29), mark_in_frame (R32), mark audit (rules 11, 15, 16, 25)": "Act 1 ink sits on our paper strips, tags and notes laid over the pictures (and the crown above Larry's hat); the mark audit is not ported yet: checked by eye",
    "Larry's tab / ledger (rule 31)": "not used in v2",
    "text_stability (R31)": "by construction: kinetic and typed text is laid out in its final place and only fades/types in place",
}


def ink_spans(plan_shots):
    sp = [tuple(x) for s in plan_shots for x in s.get("_ink", [])]
    for s in plan_shots:
        for k, d in (("crown_", 0.7), ("circle_", 0.6)):
            if s.get(k) is not None:
                sp.append((s["start"] + s[k], s["start"] + s[k] + d))
    return sp


def run(kind, P, pv, tdir, cfg, audio_ok=True):
    pl = P[kind]
    beats, shots, data = pl["beats"], pl["shots"], pl["data"]
    path = pv / OUT[kind]
    audio = decode(path) if path.exists() else None
    import soundfile as sf
    ru = any(b.get("en") for b in beats)  # the RU review copy: its own Russian narration
    voice, _ = sf.read(tdir / ("voice_24k_ru.flac" if ru else "voice_24k.flac"), dtype="float32")
    voice = voice[int(round(pl.get("offset", 0.0) * 24000)):]  # a segment preview starts at its ad break
    if pl.get("voice_file"):  # a Short: its own re-spaced narration
        voice, _ = sf.read(pv / pl["voice_file"], dtype="float32")
    dom_all = json.loads((pv / "dom.json").read_text()) if (pv / "dom.json").exists() else {}
    ctx = dict(beats=beats, shots=data["shots"], data=data, captions=data["captions"], audio=audio, voice=voice,
               silences=pl["audio"]["silences"], sfx=pl["audio"]["sfx"], ink=ink_spans(data["shots"]), path=path, cfg=cfg, kind=AUD[kind],
               dom=dom_all.get(kind), plan_kind=pl)
    res = {}
    for name, fn, _desc in CHECKS:
        if kind == "short" and name.startswith("stt_mix"):
            res[name] = None  # the same lines as the long video's cold open
            continue
        try:
            res[name] = fn(**ctx)
        except Exception as e:  # noqa: BLE001
            res[name] = [f"check crashed: {e}"]
    res["shorts_length"] = c_shorts_length(data=data)
    return res, ctx


def selftest(ctx):
    """R40: each check must FAIL on a planted bug."""
    import copy
    rows = []

    def plant(name, mut, call):
        c = copy.deepcopy({k: v for k, v in ctx.items() if k not in ("audio", "voice", "cfg", "path")})
        c.update({k: ctx[k] for k in ("audio", "voice", "cfg", "path")})
        c.setdefault("dom", None)
        desc = mut(c)
        try:
            got = call(**c)
        except Exception as e:  # noqa: BLE001
            got = [f"crash {e}"]
        rows.append((name, desc, "FAIL" if got else "PASS"))
    sh = lambda c: c["shots"]
    def m_pf(c):
        c["shots"] = [{"id": "p", "kind": "pic", "base_kind": "missing", "start": 0.0, "end": 10.0},
                      {"id": "q", "kind": "pic", "base_kind": "picture", "start": 10.0, "end": 12.0}]
        return "83% of the time on placeholder cards"
    plant("picture_first (R41)", m_pf, c_picture_first)
    def m_long(c):
        c["shots"][0]["end"] = c["shots"][0]["start"] + 9.0
        return "a 9 s shot"
    plant("max_still", m_long, c_max_still)
    def m_short(c):
        c["shots"][1]["end"] = c["shots"][1]["start"] + 0.6
        return "a 0.6 s shot"
    plant("min_shot", m_short, c_min_shot)
    def m_jump(c):
        c["shots"] = [{"id": "x1", "src": "o4", "cont": True, "cam": [[0.5, 0.5, 1], [0.5, 0.5, 1.1]]}, {"id": "x2", "src": "o4", "cam": [[0.7, 0.5, 1.4], [0.7, 0.5, 1.5]]}]
        return "o4 meant to continue into o4, with a camera jump"
    plant("same_object (R36)", m_jump, c_same_object)
    def m_diff(c):
        c["beats"][0]["diff"] = ["replace: script 'robbery' | heard 'rubbery'"]
        return "a line with a word difference"
    plant("stt_voice (r89)", m_diff, c_stt_voice)
    def m_mix(c):
        b = c["beats"][0]
        a = c["audio"].copy()
        a[int(b["start"] * 48000):int(b["end"] * 48000)] = 0
        c["audio"] = a
        return "first line muted in the mix"
    if ctx.get("audio") is not None and ctx["kind"] == "long" and not any(b.get("en") for b in ctx["beats"]):
        plant("stt_mix (r89)", m_mix, c_stt_mix)  # (the RU review copy has no English STT check to plant into)
    def m_cut(c):
        v = c["voice"].copy()
        i = int(c["beats"][1]["start"] * 24000)
        v[i - 600:i] = 0.2 * np.sin(np.arange(600) / 3)
        c["voice"] = v
        return "voice cut inside a word (tone in the 30 ms before a line)"
    plant("voice_cuts (R33)", m_cut, c_voice_cuts)
    def m_sil(c):
        if c["audio"] is None:
            c["audio"] = np.zeros(48000 * 80, np.float32)
        a = c["audio"].copy()
        s0, s1 = c["silences"][0] if c["silences"] else (10.0, 11.0)
        c["silences"] = [(s0, s1)]
        a[int(s0 * 48000):int(s1 * 48000)] += 0.05
        c["audio"] = a
        return "music left under the silence"
    plant("hit_silence", m_sil, c_hit_silence)
    def m_gate(c):
        cc = json.loads(json.dumps(c["cfg"]))
        cc["audio"]["true_peak_max"] = -40.0
        cc["audio"]["true_peak_max_long"] = -40.0
        c["cfg"] = cc
        return "ceiling set to -40 dBTP"
    if ctx.get("path") is not None and Path(ctx["path"]).exists():
        plant("audio_gate (14)", m_gate, c_audio_gate)
    def m_plate(c):
        s = next(x for x in c["shots"] if x["kind"] in ("still", "pic"))
        s["namecard"] = {"box": [-0.01, 0.1, 0.2, 0.3], "name": "X", "stamp": "X"}
        return "name card off the left edge"
    plant("plate_fit (R26)", m_plate, c_plate_fit)
    def m_margin(c):
        s = next(x for x in c["shots"] if x["kind"] in ("still", "pic"))
        s["namecard"] = {"box": [0.1, 0.1, 0.3, 0.3], "name": "X", "text_dx_px": 8}
        return "typed text 8 px from the margin line"
    plant("card_text_margin (R30)", m_margin, c_card_text_margin)
    def m_lint(c):
        c["shots"][0]["badge"] = "+5 %"
        return "'+5 %' on a card"
    plant("text_lint (r89)", m_lint, c_text_lint)
    def m_count(c):
        c["shots"][0]["countup"] = True
        return "a number card that counts up"
    plant("count_up (R39)", m_count, c_count_up)
    def m_cap(c):
        c["captions"] = c["captions"] + [{"start": 1.0, "end": 2.0, "words": [["and", 1.0, 1.2], ["the", 1.2, 1.4]]}]
        return "a card ending on 'the'"
    plant("captions (R23)", m_cap, c_captions)
    def m_sfx(c):
        c["sfx"] = c["sfx"] + [(5.0, 5.6, "scribble:0.6")]
        c["ink"] = []
        return "scratch with no ink on screen"
    plant("sfx_sync (R34)", m_sfx, c_sfx_sync)
    def m_band(c):
        c["data"] = {**c["data"], "W": 1080, "H": 1920, "band": [0, 600, 1080, 576]}
        return "30 % picture band"
    plant("shorts_band (R38)", m_band, c_shorts_band)
    def m_len(c):
        c["data"] = {**c["data"], "W": 1080, "H": 1920, "end": 50.0}
        return "a 50 s Short"
    plant("shorts_length", m_len, lambda **k: c_shorts_length(data=k["data"]))
    def m_tail(c):
        c["data"] = {**c["data"], "W": 1080, "H": 1920, "frames": int(round(max(x["end"] for x in c["shots"]) * c["data"]["fps"])) + 18}
        return "a Short with 0.6 s of empty frame at the end"
    plant("short_loop", m_tail, c_short_loop)
    def m_dec(c):
        bad = Path("/tmp/_broken.mp4")
        bad.write_bytes(Path(c["path"]).read_bytes()[:200000] if Path(c["path"]).exists() else b"0" * 1000)
        c["path"] = bad
        return "truncated file"
    plant("decode", m_dec, c_decode)
    def m_jit(c):
        c["shots"] = [{"id": "planted", "kind": "still", "iw": 2600, "ih": 1463, "start": 0.0, "end": 6.0,
                       "cam": [[0.5, 0.5, 1.05], [0.6, 0.45, 1.35]], "_shake": 0.6}]
        return "a push that shakes by 0.6 px frame to frame"
    plant("jitter (R28)", m_jit, c_jitter)

    def scr(c):
        s = next((s for s in c["shots"] if (s.get("screen") or {}).get("mode") in ("fees", "total", "pay")), None)
        if s is None:  # a segment without a checkout page: plant one (a laptop screen 40 % of the picture wide)
            s = {"id": "planted", "kind": "pic", "start": 0.0, "end": 4.0, "iw": 2600, "ih": 1463, "cam": [[0.5, 0.5, 1.0], [0.5, 0.5, 1.05]],
                 "quad": [[780, 400], [1820, 400], [1820, 990], [780, 990]], "screen": {"mode": "fees", "fees": [], "fs": None}}
            c["shots"] = c["shots"] + [s]
        return s
    def m_read(c):
        s = scr(c)
        s["screen"]["fs"] = {"os": 24, "row": 30, "fee": 34, "lab": 30, "tot": 38}
        c["data"] = dict(c["data"], W=1920, H=1080)  # the check judges the 16:9 film; a Shorts run plants it there too
        return f"{s['id']} with PREVIEW 2's old checkout sizes (24 / 30 / 34)"
    plant("read_size (R45)", m_read, c_read_size)
    def m_mark(c):
        s = scr(c)
        s["screen"]["stamp"] = {"text": "REAL", "x": 1180, "y": 300, "size": 150, "rot": -9}
        return "the REAL stamp at the screen's right edge (over the bezel)"
    plant("screen_marks (R44)", m_mark, c_screen_marks)
    def m_face(c):
        c["shots"] = [{"id": f"scr{i}", "screen": {"mode": "tabs"}, "face": False, "start": i * 4.0, "end": i * 4.0 + 4.0} for i in range(3)]
        return "three screen shots back to back"
    plant("face_cut (R46)", m_face, c_face_cut)
    def m_hold(c):
        s = next(x for x in c["shots"] if x.get("_ink"))
        s["end"] = max(b for _a, b in s["_ink"]) + 0.2
        return f"{s['id']} cut 0.2 s after the last stroke (hand still on it)"
    plant("ink_hold (R47)", m_hold, c_ink_hold)

    face = {"kind": "face", "box": [900, 400, 1100, 600]}
    def smp(**k):
        return {"t": 0.0, "shot": "planted", "shotpic": True, "faces": [face], "hands": [], "stampHands": [], "marks": [], "reads": [], **k}
    def m_hof(c):
        c["dom"] = {"W": 1920, "H": 1080, "band": None, "samples": [dict(smp(hands=[{"tip": [860, 360], "sh": 1080}]), t=t) for t in (0.0, 0.1, 0.2)]}
        return "the hand's palm parked on a face for 0.3 s"
    plant("hand_over_face", m_hof, c_hand_over_face)
    def m_txt(c):
        c["dom"] = {"W": 1920, "H": 1080, "band": None, "samples": [smp(reads=[{"text": "SMALL", "box": [300, 300, 500, 330], "cap": 14.0, "contrast": 1.6}])]}
        return "a 14 px cap line, contrast 1.6:1 (red on green)"
    plant("text_size_contrast", m_txt, c_text_size_contrast)
    def m_edge(c):
        c["dom"] = {"W": 1920, "H": 1080, "band": None, "samples": [smp(marks=[{"kind": "tag", "text": "A", "box": [10, 300, 200, 400]}])]}
        return "a tag 10 px from the left edge"
    plant("edge_margin", m_edge, c_edge_margin)
    def m_tf(c):
        c["dom"] = {"W": 1920, "H": 1080, "band": None, "samples": [smp(marks=[{"kind": "tag", "text": "$18", "box": [950, 450, 1150, 560]}])]}
        return "the $18 tag on Larry's face"
    plant("tag_face", m_tf, c_tag_face)
    def m_sh(c):
        c["shots"] = [{"id": "planted", "start": 0.0, "end": 3.0, "overs": [{"t": "stamp", "at_": 2.6}]}]
        return "FICTIONAL lands 0.4 s before the cut"
    plant("stamp_hold", m_sh, c_stamp_hold)
    def m_ui(c):
        c["shots"] = [{"id": "x1", "screen": {"head": "CHECKOUT A", "mode": "allin", "price": "$48"}},
                      {"id": "x2", "screen": {"head": "CHECKOUT A", "mode": "split", "price": None}}]
        return "checkout A all-in in one shot, '$30 + fees' in the next"
    plant("ui_state_consistency", m_ui, c_ui_state)
    def m_card(c):
        c["shots"] = [{"id": "planted", "base_kind": "flat", "key": "21%", "at_": 1.0, "start": 0, "end": 3}]
        return "1 s of empty navy before the number"
    plant("card_not_empty", m_card, c_card_not_empty)
    def m_rep(c):
        c["shots"] = [{"id": f"r{i}", "img": "v2/a5.jpg", "start": i * 15.0, "end": i * 15.0 + 4, "cam": [[0.5, 0.5, 1], [0.5, 0.5, 1.1]]} for i in range(3)]
        return "the queue, same framing, 3x in 34 s"
    plant("repeat_shot", m_rep, c_repeat_shot)
    def m_plain(c):
        c["shots"] = [{"id": "planted", "base": "n4"}]
        return "the filing drawer on plain cream"
    plant("plain_background", m_plain, c_plain_background)
    def m_dial(c):
        c["shots"] = [{"id": f"d{i}", "img": "v2/ep04v2_a2_safe.jpg", "start": i * 1.5, "end": i * 1.5 + 1.5, "cam": [[0.3, 0.4, 2.4], [0.3, 0.4, 2.5]]} for i in range(3)]
        return "4.5 s of dial close-ups"
    plant("dial_run", m_dial, c_dial_run)
    def m_era(c):
        c["shots"] = [{"id": "planted", "beat": "X", "base": "arch_loews", "caption": "Ticket line, Washington, 1939 · Library of Congress",
                       "overs": [{"t": "plate", "text": "AUGUST 2015 · STUBHUB"}]}]
        c["beats"] = [{"id": "X", "text": "August 2015. StubHub, the ticket resale site."}]
        return "Loew's 1939 under AUGUST 2015"
    plant("archive_era (R48)", m_era, lambda **k: c_archive_era(shots=k["shots"], beats=k["beats"]))
    def m_tool(c):
        c["shots"] = c["shots"] + [{"id": "planted", "overs": [{"t": "wires", "snip_": 0.5}]}]
        return "code-drawn scissors floating over the bomb"
    plant("tool_touch (R49)", m_tool, c_tool_touch)
    def m_end(c):
        c["beats"] = [{"id": "L", "start": 100.0, "end": 103.0, "text": "Subscribe."}]
        c["shots"] = [{"id": "L", "beat": "L", "start": 99.8, "end": 103.4}, {"id": "E", "beat": "END", "endscreen": True, "start": 103.4, "end": 109.0}]
        c["data"] = dict(c["data"], end=109.0)
        c["dom"] = {"W": 1920, "H": 1080, "band": None, "samples": [smp(t=105.0, marks=[{"kind": "tag", "text": "SUBSCRIBE", "box": [1500, 300, 1800, 420]}])]}
        return "a 9 s end screen with a tag in the video-element zone"
    plant("end_screen", m_end, c_end_screen)
    def m_lic(c):
        pk = copy.deepcopy(c.get("plan_kind") or {"data": {"shots": []}, "audio": {}, "beats": []})
        pk.setdefault("data", {}).setdefault("shots", []).append({"id": "planted", "img": "v2/planted_unlicensed_still.jpg"})
        c["plan_kind"] = pk
        return "a still with no row in ASSET_LICENSES.md"
    plant("asset_license (R50)", m_lic, c_asset_license)
    def m_era_item(c):
        c["shots"] = [{"id": "planted", "beat": "X", "base": "arch_cooperstown_x", "img": "v2/ep04v2_arch_cooperstown_1937.jpg",
                       "caption": "Hotel sign, Cooperstown, New York, 1937 · Library of Congress"}]
        c["beats"] = [{"id": "X", "text": "In 1958 the law changed."}]
        return "the register's 1937 item under a line about 1958 (no plan year)"
    def m_r51(c):
        c["data"] = dict(c["data"], r51=True)
        c["shots"] = [{"id": "planted", "video": "v2/planted_clip.mp4", "start": 0.0, "end": 4.0, "rate": 0.85}]
        return "a 3.4 s clip stretched to 4 s (0.85x)"
    plant("clip_native (R51)", m_r51, lambda **k: c_clip_native(shots=k["shots"], data=k["data"]))
    plant("archive_era (R48) item date", m_era_item, lambda **k: c_archive_era(shots=k["shots"], beats=k["beats"]))
    return rows


def sheet(path: Path, out: Path, every: float = 1.5):
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                               capture_output=True, text=True).stdout or 0)
    every = max(every, dur / 240)  # the full episode: <= 240 tiles
    n = int(dur / every) + 1
    rows = (n + 5) // 6
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(path), "-vf", f"fps=1/{every},scale=480:-1,tile=6x{rows}", "-frames:v", "1", str(out)], check=True)


def main(pvd: str, tdir: str) -> int:
    pv, td = Path(pvd), Path(tdir)
    cfg = load_config({})
    P = json.loads((pv / "plan.json").read_text())
    kinds = list(P)
    for kind in kinds:
        if (pv / f"v2_{kind}_silent.mp4").exists():
            master(pv, kind, cfg)
    seg = next((k for k in ("a2", "a3", "a4", "full", "full_ru") if k in P), "shorts" if any(k.startswith("sh") for k in P) else "p2")
    title = {"p2": "PREVIEW 2", "a2": "PREVIEW · ACT 2", "a3": "PREVIEW · ACT 3", "a4": "PREVIEW · ACT 4", "full": "FULL EPISODE", "full_ru": "RU REVIEW COPY (NOT FOR UPLOAD)", "shorts": "SHORTS"}[seg]
    what = {"p2": "Cold open + Act 1 (to the first ad break), 16:9, and a 9:16 sample of the cold open.",
            "a2": "Act 2 (first ad break to the second), 16:9.", "a3": "Act 3 (second ad break to the third), 16:9.",
            "a4": "Act 4 (third ad break to the end), 16:9.", "full": "The whole episode in one file (16:9), end screen included.",
            "full_ru": "The whole episode on the Russian review narration (ElevenLabs v3), every on-screen word in Russian; the English line-by-line STT check does not apply.",
            "shorts": "Seven Shorts, 9:16, <= 45 s each, looping, cut from the episode's own narration."}[seg]
    md = [f"# Ep.4 v2 · {title} · QC (picture-first)", "",
          what + " Remotion layer; Klot's stills, Ep.4 pictures and archive prints; any still not in yet is held on a labelled "
          "placeholder card or a tagged stand-in.", ""]
    allres, ctxs = {}, {}
    for kind in kinds:
        res, ctx = run(kind, P, pv, td, cfg)
        allres[kind], ctxs[kind] = res, ctx
    md += ["| check | what | " + " | ".join(COL[k] for k in kinds) + " |", "|---|---|" + "---|" * len(kinds)]
    desc = {n: d for n, _f, d in CHECKS}
    desc["shorts_length"] = "a Short is <= 45 s"
    for name in [n for n, *_ in CHECKS] + (["shorts_length"] if any(k == "short" or k.startswith("sh") for k in kinds) else []):
        cells = []
        for kind in kinds:
            r = allres[kind].get(name)
            if name == "read_size (R45)" and kind == "short":
                cells.append("n/a: judged on the 16:9 film; the 9:16 file is a layout sample")
            elif name == "read_size (R45)" and kind.startswith("sh"):
                cells.append("n/a: 16:9 rule; 9:16 text is judged by text_size_contrast")
            elif name == "shorts_length" and kind == "short" and r:
                cells.append("n/a: this is the full cold open as a 9:16 layout sample, not a Short")
            elif name in ("shorts_band (R38)", "shorts_length", "short_loop") and not (kind == "short" or kind.startswith("sh")):
                cells.append("n/a (16:9)" if name in ("shorts_length", "short_loop") else ("PASS" if not r else f"FAIL ({len(r)})"))
            elif name == "clip_native (R51)" and not (P[kind].get("data") or {}).get("r51"):
                cells.append("n/a: this plan predates R51 (Nov 7)")
            elif name.startswith("stt_") and kind == "full_ru":
                cells.append("n/a: the STT check is English-only (the RU copy is checked by ear)")
            elif r is None:
                cells.append("same as 16:9")
            else:
                cells.append("PASS" if not r else f"FAIL ({len(r)})")
        md.append(f"| {name} | {desc[name]} | " + " | ".join(cells) + " |")
    det = [f"- {k} · {n}: {x}" for k in allres for n, r in allres[k].items() if r and not (n == "shorts_length")
           for x in r[:30]]
    if det:
        md += ["", "Details:"] + det
    md += ["", "| not applicable in this preview | why |", "|---|---|"] + [f"| {k} | {v} |" for k, v in NOT_APPLICABLE.items()]
    st = selftest(ctxs[kinds[0]])
    md += ["", "Self-test (R40: each check must FAIL on its planted bug):", "", "| check | planted bug | result |", "|---|---|---|"]
    md += [f"| {a} | {b} | {c}{'' if c == 'FAIL' else ' - BLIND'} |" for a, b, c in st]
    shots0 = P[kinds[0]]["data"]["shots"]
    miss = sorted({s.get("missing") or s.get("file") for s in shots0 if s.get("base_kind") == "missing" or s["kind"] == "missing"})
    sti = sorted({f"{s['standin']['for']} -> {('Klot ' if s['standin']['src'].startswith('s0') else 'Ep.4 ') + s['standin']['src']}" for s in shots0 if s.get("standin")})
    import asset_license as AL
    inc = sorted({x for k in kinds for x in AL.check(AL.used_assets(P[k]))[1]})
    md += ["", f"Asset register (docs/ASSET_LICENSES.md): {len(inc)} rows incomplete (not blocking): " + ("; ".join(inc) or "none")]
    md += ["", "Stand-ins (tagged on screen): " + ("; ".join(sti) or "none")]
    md += ["", "Placeholders (Klot's stills not in yet): " + (", ".join(f"{m}.png" for m in miss) or "none")]
    for kind in kinds:
        p = pv / OUT[kind]
        if p.exists():
            i, tp = R.measure_audio(p)
            dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                                       capture_output=True, text=True).stdout)
            md.append(f"- {p.name}: {dur:.1f} s, {i:.1f} LUFS, true peak {tp:.1f} dBTP")
            sheet(p, pv / f"sheet_{kind}.png")
    (pv / ("qc_preview2.md" if seg == "p2" else f"qc_preview_{seg}.md")).write_text("\n".join(md) + "\n")
    print("\n".join(md))
    bad = any(r for k in allres for n, r in allres[k].items() if r and n != "shorts_length") or any(c != "FAIL" for *_x, c in st)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
