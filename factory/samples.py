"""Voice samples -> Telegram: python -m factory.samples [--set narrator|house|all]

Each sample is sent as an audio message titled with its number and voice id, so the choice is easy.
"""
from __future__ import annotations

import argparse
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from .audio import write_wav
from .audio import to_sr
from .notify import _api
from .tts import SAMPLE_RATE, KokoroVoice

SETS = {
    "narrator": {
        "text": "Case file number two. The casino. Tonight, Larry walks in with five hundred dollars. "
                "And by the end of this case, you'll find the exact same trick hiding in your own pocket.",
        "voices": [("b", "bm_george"), ("b", "bm_fable"), ("b", "bm_lewis"), ("b", "bm_daniel")],
        "speed": 0.98,
    },
    "house": {
        "text": "Relax, Larry. It's just plastic. The house doesn't need luck. It has arithmetic.",
        "voices": [("a", "am_onyx"), ("a", "am_michael"), ("a", "am_adam"), ("a", "am_eric"),
                   ("a", "am_fenrir"), ("a", "am_liam"), ("a", "am_echo"), ("a", "am_puck")],
        "speed": 0.92,
    },
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", default="all", choices=["all", *SETS])
    args = ap.parse_args()
    names = list(SETS) if args.set == "all" else [args.set]
    tmp = Path(tempfile.mkdtemp())
    for name in names:
        spec = SETS[name]
        _api("sendMessage", data={"text": f"🎙 Образцы голоса: {'рассказчик (Инспектор)' if name == 'narrator' else 'крупье The House'}. Ответь номером."})
        for i, (lang, voice) in enumerate(spec["voices"], 1):
            audio, _ = KokoroVoice({"lang_code": lang, "voice": voice, "speed": spec["speed"]}).synth(spec["text"])
            wav = tmp / f"{name}_{i}.wav"
            mp3 = tmp / f"{i:02d}_{voice}.mp3"
            write_wav(wav, to_sr(audio.astype(np.float32), SAMPLE_RATE))
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(wav), "-af", "loudnorm=I=-16", "-b:a", "128k", str(mp3)], check=True)
            with open(mp3, "rb") as fh:
                resp = _api("sendAudio", data={"title": f"{i}. {voice}", "performer": "CoinSense"}, files={"audio": (mp3.name, fh, "audio/mpeg")})
            if resp is None or resp.status_code != 200:
                raise SystemExit(f"Telegram did not accept sample {voice}")
            print(f"sent {name} {i} {voice}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
