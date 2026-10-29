"""Sound design: synthesized SFX (no licensing issues), optional music with ducking, final mix."""
from __future__ import annotations

import random
import subprocess
import wave
from pathlib import Path

import numpy as np
from scipy.signal import butter, resample_poly, sosfilt

from .config import ROOT

SR = 48000


def db(value: float) -> float:
    return float(10 ** (value / 20))


def _env(n: int, attack: float, release: float) -> np.ndarray:
    a, r = max(1, int(attack * SR)), max(1, int(release * SR))
    env = np.ones(n, dtype=np.float32)
    env[:a] = np.linspace(0, 1, a)
    env[-r:] *= np.linspace(1, 0, r)
    return env


def sfx(kind: str, seed: int = 0) -> np.ndarray:
    rnd = np.random.default_rng(seed)
    if kind == "whoosh":
        n = int(0.5 * SR)
        noise = rnd.standard_normal(n).astype(np.float32)
        out = np.zeros(n, dtype=np.float32)
        # sweep a band-pass upward by processing short blocks
        block = 2400
        for i in range(0, n, block):
            frac = i / n
            low = 300 + 2500 * frac
            sos = butter(2, [low, low * 2.2], btype="band", fs=SR, output="sos")
            out[i : i + block] = sosfilt(sos, noise[i : i + block])
        t = np.linspace(0, 1, n)
        shape = np.sin(np.pi * t) ** 2
        return (out * shape / (np.abs(out).max() + 1e-9) * 0.9).astype(np.float32)
    if kind == "pop":
        n = int(0.12 * SR)
        t = np.arange(n) / SR
        freq = np.linspace(900, 250, n)
        return (np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-t * 35) * 0.9).astype(np.float32)
    if kind == "snip":  # scissors: metallic shear as the blades close, a small click at the end
        n = int(0.22 * SR)
        t = np.arange(n) / SR
        noise = rnd.standard_normal(n).astype(np.float32)
        sos = butter(2, [3500, 9000], btype="band", fs=SR, output="sos")
        shear = sosfilt(sos, noise) * np.clip(t / 0.09, 0, 1) * np.exp(-np.clip(t - 0.09, 0, None) * 60)
        click = np.zeros(n, np.float32)
        k0 = int(0.1 * SR)
        tc = t[: n - k0]
        click[k0:] = np.sin(2 * np.pi * 3100 * tc) * np.exp(-tc * 160)
        out = shear / (np.abs(shear).max() + 1e-9) * 0.45 + click * 0.8
        return out.astype(np.float32)
    if kind == "tick":
        n = int(0.035 * SR)
        t = np.arange(n) / SR
        return (np.sin(2 * np.pi * 2200 * t) * np.exp(-t * 180) * 0.7).astype(np.float32)
    if kind.startswith("scribble"):  # marker on paper; "scribble:0.62" = exactly as long as the pen writes (rule 34)
        n = int((float(kind.split(":")[1]) if ":" in kind else 0.45) * SR)
        noise = rnd.standard_normal(n).astype(np.float32)
        sos = butter(2, [1800, 6000], btype="band", fs=SR, output="sos")
        out = sosfilt(sos, noise)
        t = np.arange(n) / SR
        strokes = 0.55 + 0.45 * np.sin(2 * np.pi * 9 * t + rnd.uniform(0, 6))
        return (out / (np.abs(out).max() + 1e-9) * strokes * _env(n, 0.03, 0.12) * 0.5).astype(np.float32)
    if kind == "shutter":  # camera flash: click + whine
        n = int(0.35 * SR)
        t = np.arange(n) / SR
        click = rnd.standard_normal(n) * np.exp(-t * 90) * 0.7
        click[int(0.06 * SR):] += rnd.standard_normal(n - int(0.06 * SR)) * np.exp(-t[: n - int(0.06 * SR)] * 120) * 0.6
        whine = np.sin(2 * np.pi * (2500 + 3000 * t) * t) * np.exp(-t * 8) * 0.08
        return (click + whine).astype(np.float32)
    if kind == "type":  # three typewriter strikes
        n = int(0.45 * SR)
        out = np.zeros(n, dtype=np.float32)
        for k in range(3):
            i = int((0.02 + k * 0.13 + rnd.uniform(0, 0.03)) * SR)
            m = int(0.04 * SR)
            tt = np.arange(m) / SR
            hit = (rnd.standard_normal(m) * np.exp(-tt * 140) + np.sin(2 * np.pi * 1800 * tt) * np.exp(-tt * 200)) * 0.55
            out[i : i + m] += hit[: n - i]
        return out
    if kind == "whirr":  # roulette spin: ball rattle slowing down
        n = int(2.6 * SR)
        out = np.zeros(n, dtype=np.float32)
        t_ = 0.0
        gap = 0.035
        while t_ < 2.5:
            i = int(t_ * SR)
            m = int(0.012 * SR)
            tt = np.arange(m) / SR
            out[i : i + m] += (rnd.standard_normal(m) * np.exp(-tt * 300) * 0.35)[: n - i]
            t_ += gap
            gap *= 1.045
        sos = butter(2, [800, 6000], btype="band", fs=SR, output="sos")
        return sosfilt(sos, out).astype(np.float32) * 2.2
    if kind == "projector":  # film projector clatter (~3 s)
        n = int(3.0 * SR)
        t = np.arange(n) / SR
        clatter = rnd.standard_normal(n) * (0.5 + 0.5 * (np.sin(2 * np.pi * 24 * t) > 0.6)) * 0.12
        sos = butter(2, [300, 3000], btype="band", fs=SR, output="sos")
        return (sosfilt(sos, clatter) * _env(n, 0.2, 0.3)).astype(np.float32)
    if kind == "hit":  # short punchy accent
        n = int(0.18 * SR)
        t = np.arange(n) / SR
        body = np.sin(2 * np.pi * (110 - 50 * t / t[-1]) * t) * np.exp(-t * 22)
        click = rnd.standard_normal(n) * np.exp(-t * 160) * 0.4
        return ((body + click) * 0.8).astype(np.float32)
    if kind == "riser":  # tension before a reveal
        n = int(1.2 * SR)
        noise = rnd.standard_normal(n).astype(np.float32)
        sos = butter(2, [400, 5000], btype="band", fs=SR, output="sos")
        out = sosfilt(sos, noise)
        t = np.linspace(0, 1, n)
        tone = np.sin(2 * np.pi * np.cumsum(200 + 600 * t ** 2) / SR) * 0.3
        return ((out / (np.abs(out).max() + 1e-9) * 0.5 + tone) * t ** 2 * 0.8).astype(np.float32)
    if kind in ("ding", "cash"):  # bell; 'cash' = register ka-ching (drawer clunk + two bells)
        n = int(1.0 * SR)
        t = np.arange(n) / SR
        bell = (np.sin(2 * np.pi * 1318 * t) + 0.5 * np.sin(2 * np.pi * 2637 * t)) * np.exp(-t * 5)
        if kind == "ding":
            return (bell * 0.5).astype(np.float32)
        out = np.zeros(n, dtype=np.float32)
        clunk = rnd.standard_normal(int(0.08 * SR)) * np.exp(-np.arange(int(0.08 * SR)) / SR * 50)
        out[: len(clunk)] += clunk * 0.6
        d = int(0.12 * SR)
        out[d:] += (bell[: n - d] * 0.5).astype(np.float32)
        return out
    if kind == "pencil":  # graphite on paper: short rough stroke (several in a row = fast drawing)
        n = int(rnd.uniform(0.12, 0.22) * SR)
        noise = rnd.standard_normal(n).astype(np.float32)
        sos = butter(2, [2500, 9000], btype="band", fs=SR, output="sos")
        out = sosfilt(sos, noise)
        grain = sosfilt(butter(2, [300, 900], btype="band", fs=SR, output="sos"), rnd.standard_normal(n)) * 0.5
        t = np.arange(n) / SR
        env = np.clip(np.sin(np.pi * t / t[-1]), 0, 1) ** 0.6 * (0.7 + 0.3 * np.sin(2 * np.pi * rnd.uniform(14, 22) * t))
        out = (out + grain) * env
        return (out / (np.abs(out).max() + 1e-9) * 0.55).astype(np.float32)
    if kind == "marker":  # felt-tip on paper: softer, squeakier stroke
        n = int(rnd.uniform(0.16, 0.26) * SR)
        t = np.arange(n) / SR
        noise = rnd.standard_normal(n).astype(np.float32)
        out = sosfilt(butter(2, [1200, 4500], btype="band", fs=SR, output="sos"), noise)
        squeak = np.sin(2 * np.pi * rnd.uniform(1800, 2600) * t + 3 * np.sin(2 * np.pi * 7 * t)) * 0.15
        env = np.clip(np.sin(np.pi * t / t[-1]), 0, 1) ** 0.8
        out = (out + squeak) * env
        return (out / (np.abs(out).max() + 1e-9) * 0.45).astype(np.float32)
    if kind == "scratch":  # record scratch for comic stops
        n = int(0.35 * SR)
        t = np.arange(n) / SR
        noise = rnd.standard_normal(n)
        sos = butter(2, [700, 3500], btype="band", fs=SR, output="sos")
        out = sosfilt(sos, noise) * (0.6 + 0.4 * np.sin(2 * np.pi * 18 * t))
        return (out / (np.abs(out).max() + 1e-9) * np.exp(-t * 4) * 0.7).astype(np.float32)
    if kind == "paper":  # a clipping slides and lands on the desk: soft swish + papery flap
        n = int(0.42 * SR)
        t = np.arange(n) / SR
        noise = rnd.standard_normal(n).astype(np.float32)
        swish = sosfilt(butter(2, [900, 5200], btype="band", fs=SR, output="sos"), noise)
        swish *= np.clip(np.sin(np.pi * t / 0.30), 0, 1) ** 1.5 * (t < 0.30)
        k = int(0.30 * SR)
        flap = sosfilt(butter(2, [150, 1400], btype="band", fs=SR, output="sos"), rnd.standard_normal(n - k)) * np.exp(-np.arange(n - k) / SR * 28)
        out = swish * 0.6
        out[k:] += flap * 1.4
        return (out / (np.abs(out).max() + 1e-9) * 0.7).astype(np.float32)
    if kind == "kachunk":  # small rubber stamp pressed on paper by hand: same sample every time
        rnd = np.random.default_rng(4242)
        n = int(0.32 * SR)
        t = np.arange(n) / SR
        ka = sosfilt(butter(2, [1500, 5000], btype="band", fs=SR, output="sos"), rnd.standard_normal(n)) * np.exp(-t * 140)
        k2 = int(0.055 * SR)
        chunk = np.zeros(n)
        tt = t[: n - k2]
        chunk[k2:] = np.sin(2 * np.pi * (140 - 60 * tt) * tt) * np.exp(-tt * 30) + \
            sosfilt(butter(2, [250, 1800], btype="band", fs=SR, output="sos"), rnd.standard_normal(n - k2)) * np.exp(-tt * 70) * 0.6
        out = ka * 0.5 + chunk
        return (out / (np.abs(out).max() + 1e-9) * 0.85).astype(np.float32)
    if kind == "stamp":  # rubber stamp slammed on a folder: low thump + papery slap
        n = int(0.4 * SR)
        t = np.arange(n) / SR
        body = np.sin(2 * np.pi * (95 - 40 * t) * t) * np.exp(-t * 18)
        slap = sosfilt(butter(2, [400, 3000], btype="band", fs=SR, output="sos"), rnd.standard_normal(n)) * np.exp(-t * 60)
        return ((body * 0.9 + slap * 0.8) / 1.3).astype(np.float32)
    if kind == "chips":  # a few clay chips clacking onto a stack
        n = int(0.5 * SR)
        out = np.zeros(n, dtype=np.float32)
        t0 = 0.0
        for k in range(int(rnd.integers(3, 6))):
            m = int(0.03 * SR)
            tt = np.arange(m) / SR
            f = rnd.uniform(2600, 4200)
            click = (np.sin(2 * np.pi * f * tt) + 0.6 * np.sin(2 * np.pi * f * 1.51 * tt)) * np.exp(-tt * 170)
            click += sosfilt(butter(2, [2000, 8000], btype="band", fs=SR, output="sos"), rnd.standard_normal(m)) * np.exp(-tt * 300) * 0.5
            i = int(t0 * SR)
            out[i:i + m] += click[: max(0, min(m, n - i))] * rnd.uniform(0.5, 1.0)
            t0 += rnd.uniform(0.04, 0.09)
        return (out / (np.abs(out).max() + 1e-9) * 0.6).astype(np.float32)
    if kind == "printer":  # receipt printer: fast dot-matrix buzz with paper feed
        n = int(0.7 * SR)
        t = np.arange(n) / SR
        buzz = np.sign(np.sin(2 * np.pi * 180 * t)) * 0.5 + sosfilt(butter(2, [1500, 6000], btype="band", fs=SR, output="sos"), rnd.standard_normal(n)) * 0.6
        gate = (np.sin(2 * np.pi * 9 * t) > -0.2).astype(np.float32)
        env = np.clip(np.sin(np.pi * t / t[-1]), 0, 1) ** 0.4
        out = sosfilt(butter(2, [300, 7000], btype="band", fs=SR, output="sos"), buzz * gate * env)
        return (out / (np.abs(out).max() + 1e-9) * 0.5).astype(np.float32)
    if kind == "servo":  # little robot servo whirr + click
        n = int(0.35 * SR)
        t = np.arange(n) / SR
        whirr = np.sin(2 * np.pi * (900 + 500 * t / t[-1]) * t) * np.exp(-((t - 0.15) ** 2) / 0.006)
        click = np.zeros(n)
        k = int(0.3 * SR)
        click[k:k + 300] = rnd.standard_normal(300) * np.exp(-np.arange(300) / 40)
        return ((whirr * 0.4 + click * 0.6)).astype(np.float32)
    if kind == "tap":  # finger tap on a phone screen
        n = int(0.06 * SR)
        t = np.arange(n) / SR
        return (sosfilt(butter(2, [800, 3000], btype="band", fs=SR, output="sos"), rnd.standard_normal(n)) * np.exp(-t * 120) * 0.8).astype(np.float32)
    if kind == "cart":  # shopping-cart wheels rattling past
        n = int(0.8 * SR)
        t = np.arange(n) / SR
        rattle = sosfilt(butter(2, [400, 2500], btype="band", fs=SR, output="sos"), rnd.standard_normal(n)) * (0.6 + 0.4 * np.sin(2 * np.pi * 23 * t))
        env = np.sin(np.pi * t / t[-1]) ** 1.5
        return (rattle * env / (np.abs(rattle).max() + 1e-9) * 0.5).astype(np.float32)
    if kind == "thud":
        n = int(0.35 * SR)
        t = np.arange(n) / SR
        return (np.sin(2 * np.pi * 70 * t) * np.exp(-t * 12) * 1.0).astype(np.float32)
    return np.zeros(1, dtype=np.float32)


def to_sr(audio: np.ndarray, src_sr: int) -> np.ndarray:
    if src_sr == SR:
        return audio.astype(np.float32)
    from math import gcd

    g = gcd(SR, src_sr)
    return resample_poly(audio, SR // g, src_sr // g).astype(np.float32)


MUSIC_DIR = ROOT / "assets" / "music"
_MUSIC_CACHE: dict = {}


def _decode(path: Path) -> np.ndarray:
    if path not in _MUSIC_CACHE:
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                             check=True, capture_output=True).stdout
        a = _even_out(_trim_quiet_ends(np.frombuffer(raw, dtype=np.float32).copy()))
        rms = float(np.sqrt(np.mean(a.astype(np.float64) ** 2))) if a.size else 0.0
        a = a * (db(-20) / rms) if rms > 0 else a  # every cue at the same loudness (RMS -20 dBFS)
        _MUSIC_CACHE[path] = np.clip(a, -0.99, 0.99)
    return _MUSIC_CACHE[path]


def _rms_db(a: np.ndarray, win: int) -> np.ndarray:
    n = max(1, len(a) // win)
    blocks = a[: n * win].reshape(n, win).astype(np.float64)
    return 10 * np.log10(np.mean(blocks ** 2, axis=1) + 1e-12)


def _trim_quiet_ends(a: np.ndarray) -> np.ndarray:
    """Cuts a quiet intro / fade-out tail (15 dB below the track's typical level), so loops don't leave holes."""
    win = SR // 2
    if len(a) < win * 8:
        return a
    lv = _rms_db(a, win)
    typical = np.median(lv)
    loud = np.where(lv > typical - 15)[0]
    if loud.size == 0:
        return a
    return a[loud[0] * win : (loud[-1] + 1) * win]


def _even_out(a: np.ndarray, target_span_db: float = 6.0) -> np.ndarray:
    """Gentle slow compression for background use: lifts quiet passages and tames loud ones (max ±8 dB),
    with a 1.5 s smoothed envelope, so the bed sits at a steady level under the voice."""
    win = int(0.25 * SR)
    if len(a) < win * 8:
        return a
    lv = _rms_db(a, win)
    ref = np.median(lv)
    k = int(1.5 / 0.25)
    sm = np.convolve(np.pad(lv, (k, k), mode="edge"), np.ones(2 * k + 1) / (2 * k + 1), mode="same")[k:-k]
    gain_db = np.clip(-(sm - ref) * 0.6, -8, 8)
    gain_db = np.where(np.abs(sm - ref) < target_span_db / 2, gain_db * 0.3, gain_db)
    g = np.repeat(10 ** (gain_db / 20), win).astype(np.float32)
    g = np.concatenate([g, np.full(len(a) - len(g), g[-1], dtype=np.float32)])
    return a * g


def music_file(cue: str) -> Path | None:
    for ext in (".mp3", ".wav", ".ogg", ".m4a", ".flac"):
        f = MUSIC_DIR / f"{cue}{ext}"
        if f.exists():
            return f
    return None


def _load_music(total: float) -> np.ndarray | None:
    """Legacy: one random track for the whole video (used when no cues are given)."""
    files = sorted(p for p in MUSIC_DIR.glob("*") if p.suffix.lower() in {".mp3", ".wav", ".ogg", ".m4a", ".flac"}) if MUSIC_DIR.exists() else []
    if not files:
        return None
    music = _decode(random.Random(int(total)).choice(files))
    n = int(total * SR)
    music = np.tile(music, int(np.ceil(n / max(1, len(music)))))[:n]
    return music * _env(n, 1.5, 3.0)


def _looped(src: np.ndarray, n: int, xfade: float = 2.0) -> np.ndarray:
    """Repeats a track to length n; each repeat crossfades 2 s of the end into the start (no click, no jump)."""
    if len(src) >= n:
        return src[:n]
    f = min(int(xfade * SR), len(src) // 4)
    out = src.copy()
    ramp = np.linspace(0, 1, f, dtype=np.float32)
    while len(out) < n:
        head = src[:f] * ramp + out[-f:] * (1 - ramp)
        out = np.concatenate([out[:-f], head, src[f:]])
    return out[:n]


def _cue_track(n: int, cues: list[tuple[float, str]], fade: float = 1.6, align_end: bool = False) -> np.ndarray | None:
    """Music bed that changes mood at each cue (crossfaded); each cue resumes where it last stopped."""
    cues = [(t, c) for t, c in sorted(cues) if c]
    if not cues or not any(music_file(c) for _t, c in cues):
        return None
    out = np.zeros(n, dtype=np.float32)
    pos: dict[str, int] = {}
    f = int(fade * SR)
    for k, (t, cue) in enumerate(cues):
        path = music_file(cue)
        if path is None or cue == "none":
            continue
        a = max(0, int(t * SR) - f // 2)
        b = n if k + 1 >= len(cues) else min(n, int(cues[k + 1][0] * SR) + f // 2)
        if b <= a:
            continue
        src = _decode(path)
        start = pos.get(cue, 0)
        need = b - a
        last = k + 1 >= len(cues)
        if last and align_end and cue not in pos and len(src) >= need:
            start = len(src) - need  # the track's own ending lands on the last frame
        seg = _looped(src, start + need)[start : start + need]
        pos[cue] = (start + need) % max(1, len(src))
        env = np.ones(need, dtype=np.float32)
        fi = min(f, need // 2)
        if fi > 0:
            env[:fi] = np.linspace(0, 1, fi)
            if b < n:
                env[-fi:] = np.linspace(1, 0, fi)
        out[a:b] += seg * env
    tail = int((0.25 if align_end else 2.5) * SR)
    out[-tail:] *= np.linspace(1, 0, tail)
    return out


class Timeline:
    def __init__(self, total_seconds: float, cfg: dict):
        self.cfg = cfg["audio"]
        self.n = int(np.ceil(total_seconds * SR)) + SR // 2
        self.voice = np.zeros(self.n, dtype=np.float32)
        self.fx = np.zeros(self.n, dtype=np.float32)
        self.hits = np.zeros(self.n, dtype=np.float32)    # impacts (stamp, hit, cash…): set to -6 dB under voice peaks
        self.stings = np.zeros(self.n, dtype=np.float32)
        self.cues: list[tuple[float, str]] = []
        self.log: list[tuple[float, float, str]] = []  # (start, end, kind) of every sfx: QC sfx_sync reads it
        self.voice_edits: list[tuple[float, str]] = []  # (time, what): every point where narration audio starts/ends
        self.align_end = False  # last music cue ends exactly on the last frame (music resolves on the end card)

    def music_cue(self, at: float, cue: str) -> None:
        if not self.cues or self.cues[-1][1] != cue:
            self.cues.append((max(0.0, at), cue))

    def add_sting(self, at: float, name: str) -> None:
        path = music_file(name)
        if path is None:
            return
        # a sting is the opening of the generated clip (the model starts on the hit), faded out after ~3 s
        clip = _decode(path)[: int(3.2 * SR)].copy()
        clip = clip * _env(len(clip), 0.005, 0.9)
        clip = clip / (np.abs(clip).max() + 1e-9)  # peak 1.0: scaled against the voice in mix()
        self._add(self.stings, max(0.0, at), clip)

    def _add(self, track: np.ndarray, at: float, clip: np.ndarray) -> None:
        i = max(0, int(at * SR))
        j = min(self.n, i + len(clip))
        if j > i:
            track[i:j] += clip[: j - i]

    def add_voice(self, at: float, audio24k: np.ndarray, src_sr: int) -> None:
        self._add(self.voice, at, to_sr(audio24k, src_sr) * db(self.cfg.get("narration_db", 0)))
        self.voice_edits += [(at, "line start"), (at + len(audio24k) / src_sr, "line end")]

    HIT_KINDS = ("stamp", "kachunk", "hit", "thud", "cash", "ding", "chips", "whirr", "shutter", "snip")

    def add_sfx(self, at: float, kind: str, seed: int = 0) -> None:
        if not kind or kind == "none":
            return
        self.log.append((at, at + len(sfx(kind, seed)) / SR, kind))
        if kind in self.HIT_KINDS:
            c = sfx(kind, seed)
            self._add(self.hits, at, c / (np.abs(c).max() + 1e-9))
        else:
            self._add(self.fx, at, sfx(kind, seed) * db(self.cfg.get("sfx_db", -16)))

    def _speaking(self) -> np.ndarray:
        """0..1 'narrator is talking' curve: on within ~0.15 s, holds through the gaps between words and
        sentences (0.6 s), releases over ~0.8 s — so the music never pumps word by word."""
        hop = int(0.02 * SR)
        frames = len(self.voice) // hop + 1
        pad = np.zeros(frames * hop, dtype=np.float32)
        pad[: len(self.voice)] = self.voice
        rms = np.sqrt(np.mean(pad.reshape(frames, hop) ** 2, axis=1))
        ref = np.percentile(rms[rms > 0], 95) if np.any(rms > 0) else 1.0
        active = (rms > ref * 0.08).astype(np.float32)
        hold = int(0.6 / 0.02)
        held = np.convolve(active, np.ones(hold), mode="full")[: len(active)] > 0  # stays on 0.6 s after speech
        env = np.zeros(frames, dtype=np.float32)
        up, down = 0.02 / 0.15, 0.02 / 0.8
        v = 0.0
        for i, h in enumerate(held):
            v = min(1.0, v + up) if h else max(0.0, v - down)
            env[i] = v
        return np.repeat(env, hop)[: self.n]

    def mix(self) -> np.ndarray:
        total = self.n / SR
        speaking = self._speaking()
        # levels relative to the narration: music -8 dB in the gaps and -14 dB under the voice,
        # impacts and musical hits peaking 6 dB under the voice peaks
        act = speaking > 0.5
        v_rms = float(np.sqrt(np.mean(self.voice[act] ** 2))) if act.any() else 0.05
        v_peak = float(np.percentile(np.abs(self.voice[act]), 99.9)) if act.any() else 0.5
        out = self.voice + self.fx + self.hits * v_peak * db(self.cfg.get("hit_db", -6))
        music = _cue_track(self.n, self.cues, align_end=self.align_end) if self.cues else _load_music(total)
        if music is not None:
            music = music[: self.n]
            sos = butter(2, [1200, 4000], btype="band", fs=SR, output="sos")
            music = music - 0.37 * sosfilt(sos, music).astype(np.float32)  # pocket for the voice
            m_rms = float(np.sqrt(np.mean(music[np.abs(music) > 1e-4] ** 2))) if np.any(np.abs(music) > 1e-4) else 1.0
            gap = v_rms * db(self.cfg.get("music_gap_db", -8)) / max(m_rms, 1e-6)
            duck = db(self.cfg.get("music_under_voice_db", -14) - self.cfg.get("music_gap_db", -8))
            gain = gap * (1 - speaking * (1 - duck))
            out = out + music * gain
        out = out + self.stings * v_peak * db(self.cfg.get("sting_db", -6)) * (1 - speaking * (1 - db(-4)))
        peak = np.abs(out).max()
        if peak > 0.98:
            out = out / peak * 0.98
        return out.astype(np.float32)


def write_wav(path: Path, audio: np.ndarray) -> None:
    pcm = (np.clip(audio, -1, 1) * 32767).astype(np.int16)
    stereo = np.repeat(pcm[:, None], 2, axis=1)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(stereo.tobytes())
