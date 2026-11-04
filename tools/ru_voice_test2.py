"""Ep.4 v2 voice test 2 (Klot r9): the same passage directed line by line, so the jokes act.
- every sentence is its own clip (never a paragraph); every punchline is its own clip
- RU · Принц Нур · eleven_v3: setup lines [deadpan] / [conspiratorial] at "Natural" stability; punchlines [short pause] +
  [sarcastic] / [smirking], an ellipsis before the key word, the key word in CAPS, at "Creative" stability; speed 0.95
- 0.8–1.0 s of real silence after each punchline in the edit
- two takes of every punchline -> two versions of the passage (Take 1 / Take 2: the other tag + a soft [chuckles])
- Take E: the same direction in English, OpenAI gpt-audio "fable" (the EN episode voice), via OpenRouter
- every clip heard back (faster-whisper medium; ru / en); a clip with a dropped word is retaken once
- a Voice Changer (speech-to-speech) probe: 3 s of Take 1 sent to Принц Нур, to see whether the plan allows it by API
Keys: ELEVENLABS_API_KEY, OPENROUTER_API_KEY (never printed).
python tools/ru_voice_test2.py <out dir>"""
from __future__ import annotations

import base64
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import voice_d as VD  # noqa: E402
from ru_voice_test import diff as diff_ru, mp3, trim  # noqa: E402

SR = 24000
NUR = "gJEfHTTiifXEDmO687lC"
NATURAL, CREATIVE = 0.5, 0.0
P = "p"  # a punchline
# (kind, text). kind: "d" deadpan setup, "c" conspiratorial setup, ("p", tag1) punchline; "/" ends a paragraph (a longer gap)
RU = [
    ("d", "Это история ограбления."), ("c", "Оно заняло семь минут."), "/",
    ("d", "Без масок."), ("d", "Без машины для побега."), ("c", "Никто даже не повысил голос."), "/",
    ("d", "Жертва сама ввела номер своей карты."), ("d", "Поставила галочку."), (P, "sarcastic", "И сказала… «СПАСИБО»."), "/",
    ("d", "Его зовут Ларри."), ("d", "Ларри вы́думан."), (P, "sarcastic", "А сборы… НЕТ."), "/",
    ("c", "И прежде чем его жалеть, знайте:"), (P, "smirking", "вы тоже так… ДЕЛАЛИ."), "/",
    ("d", "Вы нашли билет подешевле."), ("d", "Выбрали место."), ("d", "Ввели карту."), "/",
    ("c", "А потом последний экран показал число, которого вы не ждали."), (P, "sarcastic", "И вы всё равно… ЗАПЛАТИЛИ."), "/",
    ("d", "Почему?"), ("c", "Кто-то потратил годы, чтобы это выяснить."), (P, "smirking", "И это были… НЕ ВЫ."), "/",
    ("d", "Дело номер четыре."), ("c", "Ограбление за семь минут."), "/",
    ("d", "Ларри закрывает первую вкладку."), ("d", "Десять долларов сэкономлены."), (P, "sarcastic", "Ларри… ГЕНИЙ."), "/",
    ("c", "Он уже решает, на что их потратить."), (P, "smirking", "Долго решать… НЕ ПРИДЁТСЯ."), "/",
    ("d", "Двадцать восемнадцать. Следующий экран."), ("d", "Сервисный сбор: восемь долларов."),
    (P, "sarcastic", "За услугу… ВЗИМАНИЯ с вас сбора."), "/",
    ("d", "Сбор площадки: шесть."), ("d", "Обработка: четыре доллара."), (P, "sarcastic", "Чтобы обработать… ОСТАЛЬНЫЕ СБОРЫ."),
]
EN = [
    ("d", "This is the story of a robbery that took seven minutes."), "/",
    ("d", "No masks."), ("d", "No getaway car."), ("c", "Nobody even raised their voice."), "/",
    ("d", "The victim typed in his own card number, ticked the box,"), (P, "sarcastic", "and said... THANK you."), "/",
    ("d", "His name is Larry."), ("d", "Larry is made up."), (P, "sarcastic", "The fees... are NOT."), "/",
    ("c", "And before you feel sorry for him, know this..."), (P, "smirking", "you've done it TOO."), "/",
    ("d", "You found the cheaper ticket."), ("d", "You picked a seat."), ("d", "You typed in your card."), "/",
    ("c", "Then the last screen showed a number you didn't expect..."), (P, "sarcastic", "and you paid... ANYWAY."), "/",
    ("d", "Why?"), ("c", "Somebody spent years finding out exactly why."), (P, "smirking", "And it... wasn't YOU."), "/",
    ("d", "Case file number four."), ("c", "The seven-minute heist."), "/",
    ("d", "Larry closes the first tab."), ("d", "Ten dollars saved."), (P, "sarcastic", "Larry is a... GENIUS."), "/",
    ("c", "He's already deciding what to spend the ten dollars on."), (P, "smirking", "He won't have to decide... for LONG."), "/",
    ("d", "8:18. Next screen."), ("d", "Service fee: eight dollars —"), (P, "sarcastic", "for the service of... CHARGING you a fee."), "/",
    ("d", "Facility fee: six."), ("d", "Processing: four dollars —"), (P, "sarcastic", "to process... the OTHER fees."),
]
SETUP_TAG = {"d": "[deadpan]", "c": "[conspiratorial]"}
OTHER = {"sarcastic": "smirking", "smirking": "sarcastic"}
GAP_IN, GAP_PARA, PRE_PUNCH, POST_PUNCH = 0.3, 0.6, 0.25, 0.9
EN_NOTE = {"d": "deadpan: flat, dry, unhurried, a straight face",
           "c": "conspiratorial: lower, leaning in, as if sharing a secret",
           "sarcastic": "sarcastic punchline: a beat of silence first, then dry and pointed; hit the CAPS word, a tiny pause at the dots",
           "smirking": "smirking punchline: a beat first, then a half-smile in the voice; hit the CAPS word, a tiny pause at the dots"}
EN_SYSTEM = ("You are a voice actor: a British documentary narrator, male, Received Pronunciation, low voice, a dry comic "
             "timing. Speak the user's line exactly as written, word for word, nothing before or after it. Direction: {note}.")


# ----------------------------------------------------------------------------------------------------------- engines
def el_v3(text: str, stability: float) -> np.ndarray:
    body = {"text": text, "model_id": "eleven_v3", "voice_settings": {"stability": stability, "similarity_boost": 0.8, "speed": 0.95}}
    for a in range(6):
        r = VD.post(f"/v1/text-to-speech/{NUR}", body, output_format="pcm_24000")
        if r.status_code == 200:
            return np.frombuffer(r.content, np.int16).astype(np.float32) / 32768.0
        if r.status_code in (400, 422) and "speed" in r.text and "speed" in body["voice_settings"]:
            body["voice_settings"].pop("speed")
            print("  (eleven_v3 takes no speed setting: default speed)", flush=True)
            continue
        if r.status_code in (429, 500, 502, 503):
            time.sleep(5 + 5 * a)
            continue
        raise RuntimeError(f"TTS {r.status_code} {r.text[:300]}")
    raise RuntimeError("TTS: gave up")


def fable(text: str, note: str) -> np.ndarray:
    import requests
    key = os.environ["OPENROUTER_API_KEY"].strip()
    body = {"model": "openai/gpt-audio", "stream": True, "modalities": ["text", "audio"], "audio": {"voice": "fable", "format": "pcm16"},
            "messages": [{"role": "system", "content": EN_SYSTEM.format(note=note)}, {"role": "user", "content": text}]}
    for a in range(5):
        try:
            r = requests.post("https://openrouter.ai/api/v1/chat/completions", stream=True, timeout=300,
                              headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, json=body)
        except Exception as e:  # noqa: BLE001
            print("  request:", e, flush=True)
            time.sleep(5 + 5 * a)
            continue
        if r.status_code != 200:
            print("  http", r.status_code, r.text[:160], flush=True)
            time.sleep(5 + 5 * a)
            continue
        pcm = []
        for raw in r.iter_lines():
            if not raw or not raw.startswith(b"data: ") or raw == b"data: [DONE]":
                continue
            try:
                ch = json.loads(raw[6:])["choices"][0]["delta"].get("audio") or {}
            except Exception:  # noqa: BLE001
                continue
            if ch.get("data"):
                pcm.append(base64.b64decode(ch["data"]))
        if pcm:
            return np.frombuffer(b"".join(pcm), np.int16).astype(np.float32) / 32768.0
    raise RuntimeError("no audio")


# ----------------------------------------------------------------------------------------------------------- hearing
_WM = None


def hear(x: np.ndarray, lang: str) -> str:
    global _WM
    if _WM is None:
        from faster_whisper import WhisperModel
        _WM = WhisperModel("medium", device="cpu", compute_type="int8")
    y = np.interp(np.arange(0, len(x), SR / 16000), np.arange(len(x)), x).astype(np.float32)
    segs, _ = _WM.transcribe(y, language=lang, beam_size=5, condition_on_previous_text=False, vad_filter=False)
    return " ".join(s.text.strip() for s in segs)


def diff_en(script: str, heard: str) -> list[str]:
    import difflib
    from num2words import num2words

    def n(t):
        t = t.lower().replace("8:18", "eight eighteen")
        t = re.sub(r"\d+", lambda m: " " + num2words(int(m.group())) + " ", t)
        return re.findall(r"[a-z']+", t.replace("-", " "))
    a, b = n(script), n(heard)
    return [f"{op}: script '{' '.join(a[i1:i2])}' | heard '{' '.join(b[j1:j2])}'"
            for op, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes() if op != "equal"]


def clip(make, text: str, lang: str) -> tuple[np.ndarray, list[str]]:
    """One clip, heard back; one retake when the first drops or changes a word."""
    df = diff_ru if lang == "ru" else diff_en
    x = trim(make())
    d = df(text, hear(x, lang))
    if d:
        x2 = trim(make())
        d2 = df(text, hear(x2, lang))
        if len(d2) < len(d):
            x, d = x2, d2
    return x, d


# ----------------------------------------------------------------------------------------------------------- passages
def build(lines: list, lang: str) -> tuple[list[np.ndarray], list[dict]]:
    """-> [take1 audio, take2 audio] (RU) or [take E] (EN), and the report rows. Setup clips are shared by both takes."""
    takes = [[np.zeros(int(0.3 * SR), np.float32)] for _ in range(2 if lang == "ru" else 1)]
    rep = []
    for item in lines:
        if item == "/":
            for t in takes:
                t.append(np.zeros(int(GAP_PARA * SR), np.float32))
            continue
        if item[0] == P:
            _p, tag, text = item
            for k, t in enumerate(takes):
                if lang == "ru":
                    tg = tag if k == 0 else OTHER[tag]
                    say = f"[short pause] [{tg}] {text}" + (" [chuckles]" if k == 1 else "")
                    x, d = clip(lambda: el_v3(say, CREATIVE), text, "ru")
                else:
                    tg = tag
                    x, d = clip(lambda: fable(text, EN_NOTE[tag]), text, "en")
                t += [np.zeros(int(PRE_PUNCH * SR), np.float32), x, np.zeros(int(POST_PUNCH * SR), np.float32)]
                rep.append({"take": "E" if lang == "en" else k + 1, "kind": f"punchline [{tg}]", "line": text, "dur": round(len(x) / SR, 2), "diff": d})
        else:
            kind, text = item
            if lang == "ru":
                x, d = clip(lambda: el_v3(f"{SETUP_TAG[kind]} {text}", NATURAL), text, "ru")
            else:
                x, d = clip(lambda: fable(text, EN_NOTE[kind]), text, "en")
            for t in takes:
                t += [x, np.zeros(int(GAP_IN * SR), np.float32)]
            rep.append({"take": "E" if lang == "en" else "1+2", "kind": SETUP_TAG[kind], "line": text, "dur": round(len(x) / SR, 2), "diff": d})
    return [np.concatenate(t) for t in takes], rep


def sts_probe(x: np.ndarray, out: Path) -> str:
    """Voice Changer (speech-to-speech) by API: 3 s of audio to Принц Нур. 200 = the plan allows it."""
    import requests
    seg = x[int(1.0 * SR): int(4.0 * SR)]
    wav = out / "_sts_in.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", str(SR), "-ac", "1", "-i", "-", str(wav)],
                   input=(np.clip(seg, -1, 1) * 32767).astype(np.int16).tobytes(), check=True)
    with open(wav, "rb") as fh:
        r = requests.post(f"{VD.API}/v1/speech-to-speech/{NUR}", headers=VD.H(), params={"output_format": "mp3_44100_128"},
                          data={"model_id": "eleven_multilingual_sts_v2", "remove_background_noise": "false"},
                          files={"audio": ("in.wav", fh, "audio/wav")}, timeout=180)
    wav.unlink()
    if r.status_code == 200:
        (out / "voice_changer_probe.mp3").write_bytes(r.content)
        return "Voice Changer by API: available on this plan (HTTP 200, eleven_multilingual_sts_v2; probe file voice_changer_probe.mp3)"
    return f"Voice Changer by API: HTTP {r.status_code} — {r.text[:200]}"


def main(out: str) -> int:
    O = Path(out)
    O.mkdir(parents=True, exist_ok=True)
    acc = VD.account()
    n_ru = sum(len(i[-1]) for i in RU if i != "/")
    print(f"account: plan {acc['plan']}, {acc['characters_left']} characters left; RU test ~{n_ru * 3} characters", flush=True)
    ru, rep_ru = build(RU, "ru")
    en, rep_en = build(EN, "en")
    files = {"1": ru[0], "2": ru[1], "E": en[0]}
    note = []
    md = ["# Ep.4 v2 · VOICE TEST 2 — directed line by line", "",
          "Every sentence is its own clip; every punchline its own clip with [short pause] + [sarcastic]/[smirking], an "
          "ellipsis before the key word, the key word in CAPS. RU: Принц Нур, eleven_v3, setup at Natural stability, "
          "punchlines at Creative, speed 0.95. Take 2 = a second take of each punchline with the other tag + a soft "
          "[chuckles]. Take E: the same direction in English (OpenAI gpt-audio, fable). 0.9 s of silence after every "
          "punchline. Every clip heard back (faster-whisper medium); a clip with a dropped word was retaken once.", ""]
    for key, x in files.items():
        name = {"1": "Принц Нур · eleven_v3 · Take 1", "2": "Принц Нур · eleven_v3 · Take 2 (other tag + [chuckles])",
                "E": "EN · fable (gpt-audio) · Take E"}[key]
        mp3(x, O / f"voice_test2_{key}.mp3")
        rows = [r for r in (rep_ru if key != "E" else rep_en) if str(r["take"]) in (key, "1+2")]
        errs = sum(len(r["diff"]) for r in rows)
        note.append(f"Take {key} · {name} · {len(x) / SR:.0f} s · STT: {'clean' if not errs else str(errs) + ' diff'}")
        md += [f"## {name}", f"{len(x) / SR:.1f} s · STT differences: {errs}", ""]
        md += [f"- {r['kind']} {r['line']} ({r['dur']} s)" + ("" if not r["diff"] else " — " + "; ".join(r["diff"])) for r in rows] + [""]
        print(note[-1], flush=True)
    try:
        probe = sts_probe(ru[0], O)
    except Exception as e:  # noqa: BLE001
        probe = f"Voice Changer probe failed: {e}"
    print(probe, flush=True)
    note.append(probe)
    md += ["## Voice Changer (plan B)", probe, ""]
    (O / "voice_test2.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (O / "voice_test2_note.txt").write_text("\n".join(note) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
