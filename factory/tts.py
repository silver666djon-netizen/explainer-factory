"""Narration: Kokoro TTS (Apache-2.0, runs on CPU) with word timings, plus an offline stand-in."""
from __future__ import annotations

import re

import numpy as np

SAMPLE_RATE = 24000


def spoken_text(beat: dict) -> str:
    """'say' overrides what the narrator pronounces (e.g. "nine ninety-nine" for "$9.99").
    A reveal pause ('pause_at': {"word": ...}) is spoken by the voice itself (rule 33): the line is synthesised with a
    break ("...") before that word, so the silence comes from the voice model at a real word boundary - the audio is
    never cut or spliced."""
    text = str(beat.get("say") or beat["text"]).strip()
    pa = beat.get("pause_at")
    if pa and not beat.get("say") and not pa.get("splice"):
        words = text.split()
        target = [w for w in str(pa["word"]).split()]
        norm = lambda w: re.sub(r"[^\w'-]", "", w).lower()
        for i in range(1, len(words) - len(target) + 1):
            if [norm(w) for w in words[i:i + len(target)]] == [norm(w) for w in target]:
                if re.search(r"[.!?]['\"]?$", words[i - 1]):
                    return text  # a sentence end: the voice already stops there
                words[i - 1] = words[i - 1].rstrip(",;:") + "..."
                return " ".join(words)
    return text


def _proportional_words(text: str, duration: float) -> list[tuple[str, float, float]]:
    words = text.split()
    if not words:
        return []
    weights = np.array([len(w) + 2 for w in words], dtype=float)
    edges = np.concatenate([[0.0], np.cumsum(weights) / weights.sum() * duration])
    return [(w, float(edges[i]), float(edges[i + 1])) for i, w in enumerate(words)]


class OfflineVoice:
    """Silent-ish stand-in: correct pacing (~155 words/min), soft tick per word."""

    def __init__(self, pitch: float = 440.0):
        self.pitch = pitch

    def synth(self, text: str):
        words = text.split()
        duration = max(1.0, len(words) / 2.6)
        audio = np.zeros(int(duration * SAMPLE_RATE), dtype=np.float32)
        timings = _proportional_words(text, duration)
        t = np.arange(int(0.05 * SAMPLE_RATE)) / SAMPLE_RATE
        tick = (0.08 * np.sin(2 * np.pi * self.pitch * t) * np.exp(-t * 60)).astype(np.float32)
        for _w, start, _end in timings:
            i = int(start * SAMPLE_RATE)
            audio[i : i + len(tick)] += tick[: len(audio) - i]
        return audio, timings


_PIPELINES: dict = {}


def _pipeline(lang_code: str):
    if lang_code not in _PIPELINES:
        from kokoro import KPipeline  # imported lazily: heavy dependency

        _PIPELINES[lang_code] = KPipeline(lang_code=lang_code, repo_id="hexgrad/Kokoro-82M")
    return _PIPELINES[lang_code]


class KokoroVoice:
    def __init__(self, vcfg: dict):
        self.pipe = _pipeline(vcfg.get("lang_code", "a"))
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


class EdgeVoice:
    """Microsoft Edge online TTS (free, no key; e.g. ru-RU-DmitryNeural) with word timings — language versions."""

    def __init__(self, vcfg: dict):
        self.voice = vcfg.get("voice", "ru-RU-DmitryNeural")
        self.rate = vcfg.get("rate", "+0%")
        self.pitch = vcfg.get("pitch", "+0Hz")

    async def _run(self, text: str, pitch: str | None = None, boundary: str = "WordBoundary"):
        import edge_tts
        pitch = pitch or self.pitch
        try:
            com = edge_tts.Communicate(text, self.voice, rate=self.rate, pitch=pitch, boundary=boundary)
        except TypeError:  # edge-tts < 7: word boundaries are the default
            com = edge_tts.Communicate(text, self.voice, rate=self.rate, pitch=pitch)
        audio, words = bytearray(), []
        async for ch in com.stream():
            if ch["type"] == "audio":
                audio += ch["data"]
            elif ch["type"] == "WordBoundary":
                s0 = ch["offset"] / 1e7
                words.append((ch["text"], s0, s0 + ch["duration"] / 1e7))
        return bytes(audio), words

    def synth(self, text: str):
        import asyncio
        import subprocess
        import time
        last = None
        # attempts: the configured voice, retried with growing pauses; last, sentence boundaries (words spread)
        # (the pitch never changes: every line must sound like the same narrator)
        plans = [(None, "WordBoundary")] * 9 + [(None, "SentenceBoundary")] * 3
        for attempt, (pitch, bnd) in enumerate(plans):
            try:
                time.sleep(0.8)  # the free service drops requests that come too fast
                mp3, words = asyncio.run(self._run(text, pitch, bnd))
                if attempt:
                    print(f"::warning::edge-tts: {text[:40]!r} voiced on attempt {attempt + 1} (pitch {pitch or self.pitch}, {bnd})")
                if not mp3:
                    raise RuntimeError("no audio")
                pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", "pipe:0", "-f", "f32le", "-ac", "1", "-ar", str(SAMPLE_RATE), "pipe:1"],
                                     input=mp3, capture_output=True, check=True).stdout
                audio = np.frombuffer(pcm, dtype=np.float32).copy()
                words = [w for w in words if re.search(r"\w", w[0] or "")]
                if bnd != "WordBoundary":  # sentence timings: words spread over their sentence
                    words = [(w_, s0 + a_, s0 + b_) for st, s0, e0 in words for w_, a_, b_ in _proportional_words(st, e0 - s0)]
                if not words:
                    words = _proportional_words(text, len(audio) / SAMPLE_RATE)
                return audio, words
            except Exception as exc:  # noqa: BLE001 - network hiccups: retry
                last = exc
                print(f"edge-tts attempt {attempt + 1} failed for {text[:40]!r}: {exc}")
                time.sleep(min(30, 3 + 4 * attempt))
        raise RuntimeError(f"edge-tts failed for {text[:60]!r}: {last}")


class VoiceBank:
    """Narrator + any extra character voices ('voices' in the channel config or the episode)."""

    def __init__(self, cfg: dict, extra: dict | None, offline: bool):
        self.specs = {"narrator": cfg["voice"]}
        self.specs.update(cfg.get("voices") or {})
        self.specs.update(extra or {})
        self.offline = offline
        self.cache: dict = {}

    def get(self, key: str | None):
        key = key or "narrator"
        if key not in self.cache:
            spec = self.specs[key]
            if self.offline:
                self.cache[key] = OfflineVoice(440.0 if key == "narrator" else 260.0)
            elif spec.get("engine") == "edge":
                self.cache[key] = EdgeVoice(spec)
            else:
                self.cache[key] = KokoroVoice(spec)
        return self.cache[key]

    def synth(self, text: str, key: str | None = None):
        return self.get(key).synth(text)


def make_voice(cfg: dict, offline: bool, extra: dict | None = None) -> VoiceBank:
    return VoiceBank(cfg, extra, offline)


def caption_words(beat: dict, timings: list[tuple[str, float, float]], duration: float):
    """Captions always show the *written* words (with punctuation), timed by the spoken audio.

    If the spoken tokens line up one-to-one with the written words, their exact timings are used;
    otherwise the written words are spread over the actual speech span.
    """
    written = beat["text"].split()
    if not written:
        return []
    spoken = [t for t in timings if re.search(r"\w", t[0] or "")]
    if spoken and not beat.get("say") and len(spoken) == len(written):
        return [(w, s, e) for w, (_t, s, e) in zip(written, spoken)]
    if spoken and beat.get("_lang"):  # language versions: word for word, a dash has no time of its own, and a 'say'
        wi = [i for i, w in enumerate(written) if re.search(r"\w", w)]  # spelling with the same word count still counts
        if len(wi) == len(spoken):
            out, k, last = [], 0, spoken[0][1]
            for i, w in enumerate(written):
                if k < len(wi) and wi[k] == i:
                    _t, s, e = spoken[k]
                    out.append((w, s, e))
                    last, k = e, k + 1
                else:
                    nxt = spoken[k][1] if k < len(spoken) else last
                    out.append((w, last, max(last, nxt)))
            return out
    if spoken:
        start, end = spoken[0][1], spoken[-1][2]
    else:
        start, end = 0.0, duration
    return [(w, start + s, start + e) for w, s, e in _proportional_words(" ".join(written), max(0.3, end - start))]
