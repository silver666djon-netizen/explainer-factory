"""Ep.4 v2 cold open read by three expressive voices, same direction, same pauses, same music bed (Klot, Stage 1).
Each line is voiced on its own with its acting note; the pauses and the silence before the reveal are placed here, so the
three samples differ only in the voice.
  A  Gemini TTS, voice Charon   (API key GEMINI_API_KEY, already a repo secret)
  B  Gemini TTS, voice Algenib  (same key)
  C  Chatterbox (Resemble AI, MIT, runs on the runner), timbre from Kokoro bm_george, emotion "exaggeration" per line
python tools/voice_samples.py <out dir>"""
from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SR = 24000
# line, acting note, pause after (s), Chatterbox exaggeration
LINES = [
    ("This is the story of a robbery that took seven minutes.", "low and unhurried, drawing the listener in, a storyteller at night", 0.8, 0.55),
    ("No masks. No getaway car. Nobody even raised their voice.", "dry, three short beats with a small pause between them", 0.7, 0.5),
    ("The victim typed in his own card number, ticked the box, and said thank you.", "deadpan, a faint smile on 'and said thank you'", 1.0, 0.65),
    ("His name is Larry. Larry is made up. The fees are not.", "light and wry, then firm and serious on 'The fees are not'", 0.9, 0.6),
    ("And before you feel sorry for him, know this... you've done it too.", "leaning in, quieter, confidential", 0.6, 0.6),
    ("You found the cheaper ticket. You picked a seat. You typed in your card.", "steady rhythm, each sentence a step", 0.4, 0.5),
    ("Then the last screen showed a number you didn't expect... and you paid anyway.", "growing tension, slow and heavy on 'and you paid anyway'", 0.8, 0.75),
    ("Why? Somebody spent years finding out exactly why. And it wasn't you.", "low, conspiratorial, a hint of menace on the last sentence", 0.0, 0.8),
    ("Case file number four. The seven-minute heist.", "a firm title read, measured, with weight", 1.6, 0.55),
]
HIT_AFTER = 7          # the brass hit + one second of silence come after this line (index)
GEMINI_MODELS = ["gemini-3.8-flash-tts", "gemini-3.1-flash-tts-preview", "gemini-2.5-pro-preview-tts", "gemini-2.5-flash-preview-tts"]


def gemini(text: str, note: str, voice: str, log: dict) -> np.ndarray:
    import requests
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("GEMINI_API_KEY is empty in this run")
    prompt = (f"You are a British documentary narrator (Received Pronunciation, male, low voice). "
              f"Read the line below {note}. Read only the line.\n\n{text}")
    last = None
    for model in ([log["model"]] if log.get("model") else GEMINI_MODELS):
        for attempt in range(4):
            r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                              headers={"x-goog-api-key": key}, timeout=180, json={
                                  "contents": [{"parts": [{"text": prompt}]}],
                                  "generationConfig": {"responseModalities": ["AUDIO"],
                                                       "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}}}})
            if r.status_code == 200:
                part = r.json()["candidates"][0]["content"]["parts"][0]["inlineData"]
                log["model"] = model
                log.setdefault("mime", part.get("mimeType"))
                x = np.frombuffer(base64.b64decode(part["data"]), np.int16).astype(np.float32) / 32768.0
                import re
                m = re.search(r"rate=(\d+)", part.get("mimeType", ""))
                rate = int(m.group(1)) if m else SR
                if rate != SR:
                    x = np.interp(np.linspace(0, len(x) - 1, int(len(x) * SR / rate)), np.arange(len(x)), x).astype(np.float32)
                return x
            last = f"{model}: {r.status_code} {r.text[:200]}"
            if r.status_code in (404, 400):
                break
            time.sleep(4 + 4 * attempt)
    raise RuntimeError(f"Gemini TTS failed: {last}")


OR_PREFS = ["google/gemini-2.5-pro-preview-tts", "google/gemini-2.5-flash-preview-tts", "openai/gpt-4o-audio-preview",
            "openai/gpt-audio", "openai/gpt-audio-mini"]


def openrouter_models() -> list[str]:
    """Models on OpenRouter that output audio (public list, no key)."""
    import requests
    d = requests.get("https://openrouter.ai/api/v1/models", timeout=60).json()["data"]
    have = [m["id"] for m in d if "audio" in (m.get("architecture") or {}).get("output_modalities", [])]
    print("openrouter audio models:", have, flush=True)
    return [m for m in OR_PREFS if m in have] + [m for m in have if m not in OR_PREFS]


def _words(t: str) -> list[str]:
    import re
    return re.findall(r"[a-z0-9]+", t.lower())


def openrouter(text: str, note: str, voice: str, log: dict) -> np.ndarray:
    """Audio out through OpenRouter chat completions (streamed pcm16, 24 kHz). The transcript must match the line."""
    import requests
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY is empty in this run")
    models = [log["model"]] if log.get("model") else log.setdefault("_models", openrouter_models())
    last = None
    for model in models:
        for attempt in range(4):
            body = {"model": model, "stream": True, "modalities": ["text", "audio"],
                    "audio": {"voice": voice, "format": "pcm16"},
                    "messages": [{"role": "system", "content":
                                  "You are a voice actor: a British documentary narrator, male, Received Pronunciation, low voice. "
                                  "Speak the user's line exactly as written, word for word, nothing before or after it. "
                                  f"Direction for this line: {note}."},
                                 {"role": "user", "content": text}]}
            try:
                r = requests.post("https://openrouter.ai/api/v1/chat/completions", stream=True, timeout=240,
                                  headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, json=body)
            except Exception as e:  # noqa: BLE001
                last = f"{model}: {e}"
                time.sleep(5)
                continue
            if r.status_code != 200:
                last = f"{model}: {r.status_code} {r.text[:200]}"
                if r.status_code in (400, 404):
                    break
                time.sleep(5 + 5 * attempt)
                continue
            pcm, said = [], []
            for raw in r.iter_lines():
                if not raw or not raw.startswith(b"data: ") or raw == b"data: [DONE]":
                    continue
                try:
                    ch = json.loads(raw[6:])["choices"][0]["delta"].get("audio") or {}
                except Exception:  # noqa: BLE001
                    continue
                if ch.get("data"):
                    pcm.append(base64.b64decode(ch["data"]))
                if ch.get("transcript"):
                    said.append(ch["transcript"])
            a, b = _words(text), _words("".join(said))
            ok = bool(pcm) and (not b or (len(set(a) & set(b)) / max(1, len(set(a))) > 0.9 and len(b) <= len(a) + 2))
            if not ok:
                last = f"{model}: transcript mismatch {''.join(said)[:120]!r}"
                continue
            log["model"] = model
            return np.frombuffer(b"".join(pcm), np.int16).astype(np.float32) / 32768.0
    raise RuntimeError(f"OpenRouter audio failed: {last}")


_CB = None


def chatterbox(text: str, exaggeration: float, ref: Path) -> np.ndarray:
    global _CB
    import torch
    from chatterbox.tts import ChatterboxTTS
    if _CB is None:
        _CB = ChatterboxTTS.from_pretrained(device="cpu")
    torch.manual_seed(7)  # the same take every run
    wav = _CB.generate(text, audio_prompt_path=str(ref), exaggeration=exaggeration, cfg_weight=0.35)
    x = wav.squeeze().cpu().numpy().astype(np.float32)
    if _CB.sr != SR:
        x = np.interp(np.linspace(0, len(x) - 1, int(len(x) * SR / _CB.sr)), np.arange(len(x)), x).astype(np.float32)
    return x


def kokoro_reference(path: Path) -> None:
    """A neutral 12-second read by Kokoro's British male voice bm_george (Apache-2.0): the timbre Chatterbox copies."""
    from kokoro import KPipeline
    pipe = KPipeline(lang_code="b")
    text = ("Every case file starts with a receipt. This one was printed on a Tuesday night, "
            "in a quiet flat, by a man who thought he had found a bargain. He had not.")
    audio = np.concatenate([np.asarray(a, np.float32) for _, _, a in pipe(text, voice="bm_george")])
    write_wav(path, audio)


def trim(x: np.ndarray, thr: float = 0.01) -> np.ndarray:
    idx = np.where(np.abs(x) > thr)[0]
    if not len(idx):
        return x
    a, b = max(0, idx[0] - int(0.02 * SR)), min(len(x), idx[-1] + int(0.06 * SR))
    return x[a:b]


def write_wav(path: Path, x: np.ndarray, sr: int = SR) -> None:
    import wave
    y = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(y.tobytes())


def assemble(clips: list[np.ndarray], out: Path, name: str) -> dict:
    """Voice track with the designed pauses; music bed under it; brass hit + 1 s silence before the title line."""
    t, parts, marks = 0.6, [], {}
    for i, (c, (_, _, pause, _)) in enumerate(zip(clips, LINES)):
        parts.append((t, c))
        t += len(c) / SR + pause
        if i == HIT_AFTER:
            t += 0.35
            marks["hit"] = t
            t += 1.0  # one second of silence, then the case folder
    total = t + 3.5  # the title line rides out on the returning bed
    voice = np.zeros(int(total * SR) + SR, np.float32)
    for at, c in parts:
        i = int(at * SR)
        voice[i:i + len(c)] += c / max(1e-6, float(np.abs(c).max())) * 0.89
    vpath = out / f"_{name}_voice.wav"
    write_wav(vpath, voice)
    hit = marks["hit"]
    music = ROOT / "assets" / "music" / "ub_ticking_tension.mp3"
    sting = ROOT / "assets" / "music" / "ub_sting_brass.mp3"
    # bed: in under the first line, -20 dB, out on the hit (the silence is silence); the stab lands on the hit
    # bed: in under the first line, -20 dB, out on the hit; one second of silence; bed back under the title, faded out
    back = hit + 1.0
    fc = (f"[1:a]asplit=2[m1][m2];"
          f"[m1]atrim=0:{hit:.2f},asetpts=N/SR/TB,volume=-20dB,afade=t=in:d=1.5,afade=t=out:st={hit - 0.25:.2f}:d=0.25[bed];"
          f"[m2]atrim={hit:.2f}:{total:.2f},asetpts=N/SR/TB,volume=-20dB,afade=t=in:d=0.8,afade=t=out:st={total - back - 1.8:.2f}:d=1.8,"
          f"adelay={int(back * 1000)}|{int(back * 1000)}[bed2];"
          f"[2:a]atrim=0:2.4,asetpts=N/SR/TB,volume=-7dB,afade=t=out:st=1.2:d=1.2,adelay={int(hit * 1000)}|{int(hit * 1000)}[hit];"
          f"[0:a]aformat=channel_layouts=stereo[v];[bed]aformat=channel_layouts=stereo[b];[bed2]aformat=channel_layouts=stereo[b2];"
          f"[hit]aformat=channel_layouts=stereo[h];"
          f"[v][b][b2][h]amix=inputs=4:normalize=0:duration=first,loudnorm=I=-16:TP=-1.5:LRA=11[o]")
    mp3 = out / f"cs_ep04v2_cold_open_{name}.mp3"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(vpath), "-i", str(music), "-i", str(sting), "-filter_complex", fc,
                    "-map", "[o]", "-ar", "48000", "-c:a", "libmp3lame", "-b:a", "192k", str(mp3)], check=True)
    vpath.unlink()
    return {"file": mp3.name, "seconds": round(total, 1), "hit_at": round(hit, 2)}


def main(out_dir: str) -> int:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    only = os.environ.get("ONLY", "ABC")
    old = out / "voice_samples.json"
    report = json.loads(old.read_text()) if old.exists() else {}
    gem = bool(os.environ.get("GEMINI_API_KEY", "").strip())
    # Gemini TTS straight from Google when the key is set; otherwise the same idea through OpenRouter (key already a secret)
    pairs = ((("A_gemini_charon", "Charon"), ("B_gemini_algenib", "Algenib")) if gem else
             (("A_openrouter_fable", "fable"), ("B_openrouter_ballad", "ballad")))
    if not gem:
        print("GEMINI_API_KEY is empty: A and B go through OpenRouter", flush=True)
    for name, voice in pairs:
        if name[0] not in only:
            continue
        log = {}
        try:
            fn = gemini if gem else openrouter
            clips = [trim(fn(t, n, voice, log)) for t, n, _, _ in LINES]
            report[name] = {**assemble(clips, out, name), "engine": f"{'Gemini TTS' if gem else 'OpenRouter'} {log.get('model')}",
                            "voice": voice, "characters": sum(len(t) for t, *_ in LINES)}
        except Exception as e:  # noqa: BLE001
            report[name] = {"error": str(e)[:400]}
        print(name, report[name], flush=True)
    if "C" not in only:
        (out / "voice_samples.json").write_text(json.dumps(report, indent=1))
        return 0 if all("file" in v for k, v in report.items() if k[0] in only) else 1
    try:
        ref = out / "_ref_bm_george.wav"
        kokoro_reference(ref)
        clips = [trim(chatterbox(t, ex, ref)) for t, _, _, ex in LINES]
        report["C_chatterbox"] = {**assemble(clips, out, "C_chatterbox"), "engine": "Chatterbox 0.1.x (MIT), CPU",
                                  "voice": "timbre of Kokoro bm_george (Apache-2.0)"}
        ref.unlink()
    except Exception as e:  # noqa: BLE001
        report["C_chatterbox"] = {"error": str(e)[:400]}
    print("C_chatterbox", report["C_chatterbox"], flush=True)
    (out / "voice_samples.json").write_text(json.dumps(report, indent=1))
    return 0 if all("file" in v for v in report.values()) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
