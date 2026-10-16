"""Narration: Kokoro TTS (Apache-2.0, runs on CPU) with word timings, plus an offline stand-in."""
from __future__ import annotations

import re

import numpy as np

SAMPLE_RATE = 24000


def spoken_text(beat: dict) -> str:
    """'say' overrides what the narrator pronounces (e.g. "nine ninety-nine" for "$9.99")."""
    return str(beat.get("say") or beat["text"]).strip()


def _proportional_words(text: str, duration: float) -> list[tuple[str, float, float]]:
    words = text.split()
    if not words:
        return []
    weights = np.array([len(w) + 2 for w in words], dtype=float)
    edges = np.concatenate([[0.0], np.cumsum(weights) / weights.sum() * duration])
    return [(w, float(edges[i]), float(edges[i + 1])) for i, w in enumerate(words)]


class OfflineVoice:
    """Silent-ish stand-in: correct pacing (~155 words/min), soft tick per word."""

    def synth(self, text: str):
        words = text.split()
        duration = max(1.0, len(words) / 2.6)
        audio = np.zeros(int(duration * SAMPLE_RATE), dtype=np.float32)
        timings = _proportional_words(text, duration)
        t = np.arange(int(0.05 * SAMPLE_RATE)) / SAMPLE_RATE
        tick = (0.08 * np.sin(2 * np.pi * 440 * t) * np.exp(-t * 60)).astype(np.float32)
        for _w, start, _end in timings:
            i = int(start * SAMPLE_RATE)
            audio[i : i + len(tick)] += tick[: len(audio) - i]
        return audio, timings


class KokoroVoice:
    def __init__(self, cfg: dict):
        from kokoro import KPipeline  # imported lazily: heavy dependency

        vcfg = cfg["voice"]
        self.pipe = KPipeline(lang_code=vcfg.get("lang_code", "a"), repo_id="hexgrad/Kokoro-82M")
        self.voice = vcfg.get("voice", "am_michael")
        self.speed = float(vcfg.get("speed", 1.0))

    def synth(self, text: str):
        chunks: list[np.ndarray] = []
        timings: list[tuple[str, float, float]] = []
        offset = 0.0
        for result in self.pipe(text, voice=self.voice, speed=self.speed, split_pattern=r"\n+"):
            audio = getattr(result, "audio", None)
            if audio is None and isinstance(result, tuple):  # older tuple form (graphemes, phonemes, audio)
                audio = result[2]
            if audio is None:
                continue
            audio = audio.detach().cpu().numpy() if hasattr(audio, "detach") else np.asarray(audio)
            audio = audio.astype(np.float32).reshape(-1)
            seg_dur = len(audio) / SAMPLE_RATE
            tokens = getattr(result, "tokens", None) or []
            seg_words = [
                (tok.text, offset + float(tok.start_ts), offset + float(tok.end_ts))
                for tok in tokens
                if getattr(tok, "start_ts", None) is not None
                and getattr(tok, "end_ts", None) is not None
                and re.search(r"\w", tok.text or "")
            ]
            if not seg_words:
                graphemes = getattr(result, "graphemes", None) or (result[0] if isinstance(result, tuple) else "")
                seg_words = [(w, offset + s, offset + e) for w, s, e in _proportional_words(graphemes, seg_dur)]
            timings.extend(seg_words)
            chunks.append(audio)
            offset += seg_dur
        if not chunks:
            raise RuntimeError(f"Kokoro produced no audio for: {text[:80]!r}")
        return np.concatenate(chunks), timings


def make_voice(cfg: dict, offline: bool):
    return OfflineVoice() if offline else KokoroVoice(cfg)


def caption_words(beat: dict, timings: list[tuple[str, float, float]], duration: float):
    """Captions show the written text; if 'say' differs, spread written words over the spoken time."""
    if beat.get("say") and beat["say"] != beat["text"]:
        return _proportional_words(beat["text"], duration)
    return timings or _proportional_words(beat["text"], duration)
