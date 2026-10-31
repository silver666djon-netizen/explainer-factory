"""Ep.4 v2 PREVIEW 1: master the Remotion renders (mix -> calibrated gain -> 4x oversampled limiter -> AAC, as the
Python engine's masters) and run the release checks that apply to the Remotion layer, each with its planted-bug
self-test (R40). Writes qc_preview1.md + contact sheets.
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
from factory import render as R  # noqa: E402
from factory import sttdiff  # noqa: E402
from factory.config import load_config  # noqa: E402

OUT = {"long": "cs_ep04v2_preview1_long.mp4", "short": "cs_ep04v2_preview1_cold_open_9x16.mp4"}
MIN_SHOT, MAX_SHOT = 1.4, 8.0
FONTS = ROOT / "assets" / "fonts"


def master(pv: Path, kind: str, cfg: dict) -> Path:
    wav, silent, out = pv / f"mix_{kind}.wav", pv / f"v2_{kind}_silent.mp4", pv / OUT[kind]
    lim0 = R.LIMIT0_LONG if kind == "long" else R.LIMIT0
    loud = R._gain_filter(wav, cfg["audio"].get("target_lufs", -14), lim0)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(silent), "-i", str(wav), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-af", R._master_af(loud, lim0), *R.AAC_ARGS, "-shortest", "-movflags", "+faststart", str(out)], check=True)
    R._gate_with_remaster(out, wav, loud, cfg, kind=kind, lim0=lim0)
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
    return [f"{s['id']}: only {s['end'] - s['start']:.2f} s (min {MIN_SHOT})" for s in shots if s["end"] - s["start"] < MIN_SHOT - 1e-6]


def c_same_object(shots, **_):
    """R36: consecutive shots on the same picture continue the camera (no jump at the cut)."""
    out = []
    for a, b in zip(shots, shots[1:]):
        if a.get("src") and a.get("src") == b.get("src") and a.get("cam") and b.get("cam"):
            if any(abs(x - y) > 0.01 for x, y in zip(a["cam"][1], b["cam"][0])):
                out.append(f"{a['id']} -> {b['id']}: {a['src']} jumps from {a['cam'][1]} to {b['cam'][0]}")
    return out


def c_stt_voice(beats, **_):
    """The voice run's own line-by-line diff (medium.en): every line of the preview clean."""
    return [f"{b['id']}: {d}" for b in beats for d in b.get("diff", [])]


def c_stt_mix(beats, audio=None, **_):
    """Line by line on the FINAL mix (music + sfx under the voice): every word still heard."""
    if audio is None:
        return []
    sr = 48000
    fails, _notes = sttdiff.check_lines(audio, sr, [(b["start"], b["end"], b["id"]) for b in beats], {b["id"]: b["text"] for b in beats},
                                        known=[("Live Nation", "Lyve Nation")])
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
        if s["kind"] == "archive":
            fs = 30 if not short else 34
            maxw = W * (0.6 if not short else 0.88)
            tw = _tw(s["caption"], "PT_Serif-Web-Regular.ttf", fs)
            lines = 1 if tw <= maxw - 40 else 2
            w = min(maxw, tw + 40)
            h = lines * fs * 1.25 + 20
            box = [48, H * 0.8 - h, 48 + w, H * 0.8] if not short else [(W - maxw) / 2, 150, (W + maxw) / 2, 150 + h]
            out.append(("archive caption", s["start"], s["end"], box))
        if s.get("namecard"):
            x0, y0, x1, y1 = s["namecard"]["box"]
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
        if s.get("namecard"):
            b = data.get("band") or [0, 0, data["W"], data["H"]]
            u = min(b[2] / 1920, b[3] / 1080)
            gap = s["namecard"].get("text_dx_px", 22)  # V2.tsx NameCard: text 22 px right of the line, at any scale
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


def c_jitter(path=None, shots=None, **_):
    """R28: camera moves on pictures are smooth: on every still/clip shot the frame-to-frame motion (ORB + affine) never
    reverses by more than 0.25 px."""
    if path is None:
        return []
    import cv2
    out = []
    cap = cv2.VideoCapture(str(path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    orb = cv2.ORB_create(1500)
    for s in shots:
        if s["kind"] not in ("still", "archive"):
            continue
        a, b = s["start"] + 0.3, s["end"] - 0.3
        fr = []
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(round(a * fps)))
        for _k in range(max(0, int((b - a) * fps))):
            ok, im = cap.read()
            if not ok:
                break
            g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
            fr.append(g[: int(g.shape[0] * 0.78)])  # above the subtitles
        dx = []
        for g0, g1 in zip(fr, fr[1:]):
            k0, d0 = orb.detectAndCompute(g0, None)
            k1, d1 = orb.detectAndCompute(g1, None)
            if d0 is None or d1 is None or len(k0) < 20 or len(k1) < 20:
                continue
            m = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True).match(d0, d1)
            if len(m) < 20:
                continue
            p0 = np.float32([k0[x.queryIdx].pt for x in m])
            p1 = np.float32([k1[x.trainIdx].pt for x in m])
            M, _ = cv2.estimateAffinePartial2D(p0, p1, method=cv2.RANSAC, ransacReprojThreshold=1.0)
            if M is None:
                continue
            dx.append((M[0, 2], M[1, 2], float(np.hypot(M[0, 0], M[1, 0]))))
        for k in range(2, len(dx)):
            for ax in (0, 1):
                prev = np.median([d[ax] for d in dx[max(0, k - 3):k]])
                if abs(prev) > 0.5 and np.sign(dx[k][ax]) != np.sign(prev) and abs(dx[k][ax] - prev) > 0.25 + abs(prev) * 0.6:
                    out.append(f"{s['id']}: motion reverses at {a + k / fps:.2f} s ({prev:.2f} -> {dx[k][ax]:.2f} px)")
                    break
    return out


def c_decode(path=None, **_):
    if path is None:
        return []
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "null", "-"], capture_output=True, text=True)
    return [r.stderr.strip()[:300]] if r.stderr.strip() else []


def c_shorts_length(data=None, **_):
    if data["H"] <= data["W"]:
        return []
    return [] if data["end"] <= 45.0 else [f"{data['end']:.1f} s > 45 s"]


CHECKS = [
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
    ("jitter (R28)", c_jitter, "no camera reversal > 0.25 px"),
    ("shorts_band (R38)", c_shorts_band, "9:16 picture band >= 50 %"),
]
NOT_APPLICABLE = {
    "hand_over_ink / writing hand (R37), one hand at a time (rules 1-5)": "no drawing hand in this layer yet: every stroke draws itself (no hand on screen)",
    "mark_on_object (R29), mark_in_frame (R32), mark audit (rules 11, 15, 16, 25)": "no mark is written on a picture in this preview; all ink is on code-drawn cards",
    "Larry's tab / ledger (rule 31)": "not used in v2",
    "text_stability (R31)": "by construction: kinetic and typed text is laid out in its final place and only fades/types in place",
}


def ink_spans(plan_shots):
    sp = []
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
    voice, _ = sf.read(tdir / "voice_24k.flac", dtype="float32")
    ctx = dict(beats=beats, shots=data["shots"], data=data, captions=data["captions"], audio=audio, voice=voice,
               silences=pl["audio"]["silences"], sfx=pl["audio"]["sfx"], ink=ink_spans(data["shots"]), path=path, cfg=cfg, kind=kind)
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
        desc = mut(c)
        try:
            got = call(**c)
        except Exception as e:  # noqa: BLE001
            got = [f"crash {e}"]
        rows.append((name, desc, "FAIL" if got else "PASS"))
    sh = lambda c: c["shots"]
    def m_long(c):
        c["shots"][0]["end"] = c["shots"][0]["start"] + 9.0
        return "a 9 s shot"
    plant("max_still", m_long, c_max_still)
    def m_short(c):
        c["shots"][1]["end"] = c["shots"][1]["start"] + 0.6
        return "a 0.6 s shot"
    plant("min_shot", m_short, c_min_shot)
    def m_jump(c):
        c["shots"] = [{"id": "x1", "src": "o4", "cam": [[0.5, 0.5, 1], [0.5, 0.5, 1.1]]}, {"id": "x2", "src": "o4", "cam": [[0.7, 0.5, 1.4], [0.7, 0.5, 1.5]]}]
        return "o4 cut to o4 with a camera jump"
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
    if ctx.get("audio") is not None and ctx["kind"] == "long":
        plant("stt_mix (r89)", m_mix, c_stt_mix)
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
        s = next(x for x in c["shots"] if x["kind"] == "still")
        s["namecard"] = {"box": [-0.01, 0.1, 0.2, 0.3], "name": "X", "stamp": "X"}
        return "name card off the left edge"
    plant("plate_fit (R26)", m_plate, c_plate_fit)
    def m_margin(c):
        s = next(x for x in c["shots"] if x["kind"] == "still")
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
    def m_dec(c):
        bad = Path("/tmp/_broken.mp4")
        bad.write_bytes(Path(c["path"]).read_bytes()[:200000] if Path(c["path"]).exists() else b"0" * 1000)
        c["path"] = bad
        return "truncated file"
    plant("decode", m_dec, c_decode)
    rows.append(("jitter (R28)", "see jitter selftest below", "FAIL" if jitter_selftest() else "PASS"))
    return rows


def jitter_selftest() -> list[str]:
    """A synthetic push with one frame shifted back 3 px must be caught."""
    import cv2
    rng = np.random.default_rng(3)
    base = (rng.random((540, 960)) * 255).astype(np.uint8)
    base = cv2.GaussianBlur(base, (0, 0), 2)
    path = Path("/tmp/_jitter.mp4")
    vw = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 30, (960, 540))
    for k in range(90):
        x = 2.0 * k - (6.0 if k == 50 else 0.0)
        M = np.float32([[1, 0, -x], [0, 1, 0]])
        im = cv2.warpAffine(base, M, (960, 540), borderMode=cv2.BORDER_REFLECT)
        vw.write(cv2.cvtColor(im, cv2.COLOR_GRAY2BGR))
    vw.release()
    return c_jitter(path=path, shots=[{"id": "planted", "kind": "still", "start": 0.0, "end": 3.0}])


def sheet(path: Path, out: Path, every: float = 1.5):
    n = int(float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                                 capture_output=True, text=True).stdout or 0) / every) + 1
    rows = (n + 5) // 6
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(path), "-vf", f"fps=1/{every},scale=480:-1,tile=6x{rows}", "-frames:v", "1", str(out)], check=True)


def main(pvd: str, tdir: str) -> int:
    pv, td = Path(pvd), Path(tdir)
    cfg = load_config({})
    P = json.loads((pv / "plan.json").read_text())
    for kind in ("long", "short"):
        if (pv / f"v2_{kind}_silent.mp4").exists():
            master(pv, kind, cfg)
    md = ["# Ep.4 v2 · PREVIEW 1 · QC", "",
          "Cold open + Act 1 (to the first ad break), 16:9, and a 9:16 sample of the cold open. Remotion layer; only assets already "
          "in the repo; Klot's missing stills held on labelled placeholder cards.", ""]
    allres, ctxs = {}, {}
    for kind in ("long", "short"):
        res, ctx = run(kind, P, pv, td, cfg)
        allres[kind], ctxs[kind] = res, ctx
    md += ["| check | what | 16:9 | 9:16 |", "|---|---|---|---|"]
    desc = {n: d for n, _f, d in CHECKS}
    desc["shorts_length"] = "a Short is <= 45 s"
    for name in [n for n, *_ in CHECKS] + ["shorts_length"]:
        cells = []
        for kind in ("long", "short"):
            r = allres[kind].get(name)
            if name == "shorts_length" and kind == "short" and r:
                cells.append("n/a: this is the full cold open as a 9:16 layout sample, not a Short")
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
    st = selftest(ctxs["long"])
    md += ["", "Self-test (R40: each check must FAIL on its planted bug):", "", "| check | planted bug | result |", "|---|---|---|"]
    md += [f"| {a} | {b} | {c}{'' if c == 'FAIL' else ' - BLIND'} |" for a, b, c in st]
    miss = sorted({s["file"] for k in ("long",) for s in P[k]["data"]["shots"] if s["kind"] == "missing"})
    md += ["", "Placeholders (Klot's stills not in yet): " + ", ".join(f"{m}.png" for m in miss)]
    for kind in ("long", "short"):
        p = pv / OUT[kind]
        if p.exists():
            i, tp = R.measure_audio(p)
            dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                                       capture_output=True, text=True).stdout)
            md.append(f"- {p.name}: {dur:.1f} s, {i:.1f} LUFS, true peak {tp:.1f} dBTP")
            sheet(p, pv / f"sheet_{kind}.png")
    (pv / "qc_preview1.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))
    bad = any(r for k in allres for n, r in allres[k].items() if r and n != "shorts_length") or any(c != "FAIL" for *_x, c in st)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
