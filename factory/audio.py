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
    if kind == "tick":
        n = int(0.035 * SR)
        t = np.arange(n) / SR
        return (np.sin(2 * np.pi * 2200 * t) * np.exp(-t * 180) * 0.7).astype(np.float32)
    if kind == "scribble":  # marker on paper
        n = int(0.45 * SR)
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
    if kind == "scratch":  # record scratch for comic stops
        n = int(0.35 * SR)
        t = np.arange(n) / SR
        noise = rnd.standard_normal(n)
        sos = butter(2, [700, 3500], btype="band", fs=SR, output="sos")
        out = sosfilt(sos, noise) * (0.6 + 0.4 * np.sin(2 * np.pi * 18 * t))
        return (out / (np.abs(out).max() + 1e-9) * np.exp(-t * 4) * 0.7).astype(np.float32)
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


def _load_music(total: float) -> np.ndarray | None:
    folder = ROOT / "assets" / "music"
    files = sorted(p for p in folder.glob("*") if p.suffix.lower() in {".mp3", ".wav", ".ogg", ".m4a", ".flac"}) if folder.exists() else []
    if not files:
        return None
    track = random.Random(int(total)).choice(files)
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(track), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
        check=True, capture_output=True,
    ).stdout
    music = np.frombuffer(raw, dtype=np.float32)
    n = int(total * SR)
    reps = int(np.ceil(n / max(1, len(music))))
    music = np.tile(music, reps)[:n]
    return music * _env(n, 1.5, 3.0)


class Timeline:
    def __init__(self, total_seconds: float, cfg: dict):
        self.cfg = cfg["audio"]
        self.n = int(np.ceil(total_seconds * SR)) + SR // 2
        self.voice = np.zeros(self.n, dtype=np.float32)
        self.fx = np.zeros(self.n, dtype=np.float32)

    def _add(self, track: np.ndarray, at: float, clip: np.ndarray) -> None:
        i = max(0, int(at * SR))
        j = min(self.n, i + len(clip))
        if j > i:
            track[i:j] += clip[: j - i]

    def add_voice(self, at: float, audio24k: np.ndarray, src_sr: int) -> None:
        self._add(self.voice, at, to_sr(audio24k, src_sr) * db(self.cfg.get("narration_db", 0)))

    def add_sfx(self, at: float, kind: str, seed: int = 0) -> None:
        if kind and kind != "none":
            self._add(self.fx, at, sfx(kind, seed) * db(self.cfg.get("sfx_db", -16)))

    def mix(self) -> np.ndarray:
        total = self.n / SR
        out = self.voice + self.fx
        music = _load_music(total)
        if music is not None:
            # duck music under narration: smoothed envelope of voice energy
            energy = np.abs(self.voice)
            win = int(0.3 * SR)
            kernel = np.ones(win, dtype=np.float32) / win
            smooth = np.convolve(energy, kernel, mode="same")
            speaking = np.clip(smooth / (smooth.max() * 0.05 + 1e-9), 0, 1)
            gain = db(self.cfg.get("music_db", -24)) * (1 - speaking * (1 - db(self.cfg.get("duck_db", -8))))
            out = out + music[: self.n] * gain
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
