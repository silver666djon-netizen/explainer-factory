"""Ep.4 v2 RU voice, plan B (Klot r9): Klot's own reading of the RU cold open -> Принц Нур with the ElevenLabs Voice
Changer (speech-to-speech, eleven_multilingual_sts_v2). His timing and pauses are kept: the file goes through in chunks
of <= 4.5 min cut in his silences, nothing is re-timed. Light denoise only (ffmpeg afftdn, -12 dB floor), ElevenLabs'
own background removal off. The result is heard back (faster-whisper medium, ru) against his text.
python tools/ru_plan_b.py <recording> <out dir>   (ELEVENLABS_API_KEY, never printed)"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import voice_d as VD  # noqa: E402
from ru_voice_test import diff, mp3  # noqa: E402
from ru_voice_test2 import hear  # noqa: E402

SR = 24000
NUR = "gJEfHTTiifXEDmO687lC"
# Klot's RU cold open, as he read it (r9)
TEXT = """Это история ограбления длиной в семь минут.
Без масок. Без машины у входа. Никто даже не повысил голос.
Жертва сама ввела номер карты, поставила галочку… и сказала СПАСИБО.
Его зовут Ларри. Ларри выдуман. А сборы… НЕТ.
И прежде чем его жалеть, знайте — вы тоже так делали.
Вы нашли билет подешевле. Выбрали место. Ввели карту.
А на последнем экране было число, которого вы не ждали… и вы всё равно заплатили.
Почему? Кто-то потратил годы, чтобы выяснить это точно. И это были… не вы.
Дело номер четыре. Ограбление за семь минут."""


def load(path: str, sr: int) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(sr), "-af", "highpass=f=70,afftdn=nf=-40:nr=12",
                          "-f", "s16le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0


def chunks(x: np.ndarray, sr: int, most: float = 270.0) -> list[np.ndarray]:
    """<= 4.5 min pieces, each cut in the quietest 50 ms near the limit (in a pause, never in a word)."""
    out, i, n = [], 0, int(most * sr)
    while len(x) - i > n:
        win = x[i + n - 10 * sr: i + n]
        f = int(0.05 * sr)
        e = [float(np.mean(win[k:k + f] ** 2)) for k in range(0, len(win) - f, f)]
        cut = i + n - 10 * sr + int(np.argmin(e)) * f + f // 2
        out.append(x[i:cut])
        i = cut
    out.append(x[i:])
    return out


def sts(x: np.ndarray, sr: int, tmp: Path) -> np.ndarray:
    import requests
    wav = tmp / "_in.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", str(sr), "-ac", "1", "-i", "-", str(wav)],
                   input=(np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes(), check=True)
    for a in range(5):
        with open(wav, "rb") as fh:
            r = requests.post(f"{VD.API}/v1/speech-to-speech/{NUR}", headers=VD.H(), params={"output_format": "pcm_24000"},
                              data={"model_id": "eleven_multilingual_sts_v2", "remove_background_noise": "false",
                                    "voice_settings": '{"stability": 0.5, "similarity_boost": 0.85, "style": 0.0, "use_speaker_boost": true}'},
                              files={"audio": ("in.wav", fh, "audio/wav")}, timeout=600)
        if r.status_code == 200:
            wav.unlink()
            return np.frombuffer(r.content, np.int16).astype(np.float32) / 32768.0
        if r.status_code in (429, 500, 502, 503):
            time.sleep(10 + 10 * a)
            continue
        raise RuntimeError(f"Voice Changer HTTP {r.status_code}: {r.text[:300]}")
    raise RuntimeError("Voice Changer: gave up")


def main(rec: str, out: str) -> int:
    O = Path(out)
    O.mkdir(parents=True, exist_ok=True)
    x = load(rec, SR)  # 24 kHz: the source copy and the hearing
    x44 = load(rec, 44100)  # what the Voice Changer gets
    dur = len(x) / SR
    acc = VD.account()
    print(f"recording: {dur:.1f} s; account {acc['characters_left']} characters left; this needs ~{int(dur / 60 * 1000) + 1000}", flush=True)
    y = np.concatenate([sts(c, 44100, O) for c in chunks(x44, 44100)])
    mp3(y, O / "ru_plan_b_nur.mp3")
    mp3(x, O / "ru_plan_b_klot_source.mp3")
    d = diff(TEXT, hear(y, "ru"))
    d0 = diff(TEXT, hear(x, "ru"))
    note = [f"PLAN B · Klot's reading -> Принц Нур (Voice Changer, eleven_multilingual_sts_v2) · {len(y) / SR:.0f} s (source {dur:.0f} s) · "
            f"STT: {'clean' if not d else str(len(d)) + ' diff'} (the source itself: {'clean' if not d0 else str(len(d0)) + ' diff'})"]
    md = ["# Ep.4 v2 · RU VOICE · PLAN B", "", note[0], "", "Light denoise only (highpass 70 Hz, afftdn -12 dB); ElevenLabs "
          "background removal off; timing untouched.", "", "Differences (converted):"] + [f"- {s}" for s in d] + \
         ["", "Differences (source):"] + [f"- {s}" for s in d0] + ["", "Text:", "", TEXT]
    (O / "ru_plan_b.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (O / "ru_plan_b_note.txt").write_text("\n".join(note) + "\n", encoding="utf-8")
    print(note[0], flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
