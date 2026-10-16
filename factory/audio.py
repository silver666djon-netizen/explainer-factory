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
