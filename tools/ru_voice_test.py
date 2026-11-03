"""Ep.4 v2 RU voice test (Klot r8): four samples of the SAME passage (cold open + "Ларри — гений… Долго решать не
придётся" + the service-fee joke), each line synthesised on its own and joined with designed pauses (a longer beat after
every punchline), each line STT-checked in Russian (faster-whisper medium, no dropped words).
  A  Принц Нур · eleven_multilingual_v2
  B  Принц Нур · eleven_v3 (sparse [pause] / [dry] / [smiling] on the punchlines)
  C  Дмитрий  · the better of v2 / v3 (fewer STT differences; a tie goes to v2, the steadier model)
  D  Николай  · the better of v2 / v3
The key comes from ELEVENLABS_API_KEY and is never printed.
python tools/ru_voice_test.py <out dir>  -> ru_voice_test_[A-D].mp3, ru_voice_test.md, ru_voice_test_note.txt"""
from __future__ import annotations

import io
import json
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import voice_d as VD  # noqa: E402

SR = 24000
NUR = "gJEfHTTiifXEDmO687lC"
# the passage, re-read for spoken Russian: long sentences split, numbers in words, the punchlines short
# (text, punchline?, v3 text with sparse tags)
LINES = [
    ("Это история ограбления. Оно заняло семь минут.", False, None),
    ("Без масок. Без машины для побега. Никто даже не повысил голос.", False, None),
    ("Жертва сама ввела номер своей карты. Поставила галочку. И сказала: «Спасибо».", True, None),
    ("Его зовут Ларри. Ларри вы́думан. А сборы — нет.", True, "Его зовут Ларри. Ларри вы́думан. [pause] А сборы — нет."),
    ("И прежде чем его жалеть, знайте: вы тоже так делали.", False, None),
    ("Вы нашли билет подешевле. Выбрали место. Ввели карту.", False, None),
    ("А потом последний экран показал число, которого вы не ждали. И вы всё равно заплатили.", True, None),
    ("Почему? Кто-то потратил годы, чтобы это выяснить. И это были не вы.", True, None),
    ("Дело номер четыре. Ограбление за семь минут.", False, None),
    ("Ларри закрывает первую вкладку. Десять долларов сэкономлены. Ларри — гений.", True,
     "Ларри закрывает первую вкладку. Десять долларов сэкономлены. [dry] Ларри — гений."),
    ("Он уже решает, на что их потратить. Долго решать не придётся.", True,
     "Он уже решает, на что их потратить. [smiling] Долго решать не придётся."),
    ("Двадцать восемнадцать. Следующий экран. Сервисный сбор: восемь долларов. За услугу взимания с вас сбора.", True,
     "Двадцать восемнадцать. Следующий экран. Сервисный сбор: восемь долларов. [dry] За услугу взимания с вас сбора."),
    ("Сбор площадки: шесть. Обработка: четыре доллара. Чтобы обработать остальные сборы.", True,
     "Сбор площадки: шесть. Обработка: четыре доллара. [dry] Чтобы обработать остальные сборы."),
]
GAP, BEAT = 0.55, 1.05  # silence between lines; after a punchline
V2 = {"model_id": "eleven_multilingual_v2",
      "voice_settings": {"stability": 0.62, "similarity_boost": 0.8, "style": 0.12, "use_speaker_boost": True, "speed": 1.0}}
V3 = {"model_id": "eleven_v3", "voice_settings": {"stability": 0.5, "similarity_boost": 0.8, "speed": 1.0}}


def tts(text: str, voice_id: str, cfg: dict) -> np.ndarray:
    body = {"text": text, **json.loads(json.dumps(cfg))}
    for a in range(5):
        r = VD.post(f"/v1/text-to-speech/{voice_id}", body, output_format="pcm_24000")
        if r.status_code == 200:
            return np.frombuffer(r.content, np.int16).astype(np.float32) / 32768.0
        if r.status_code in (400, 422) and "speed" in r.text and "speed" in body["voice_settings"]:  # a model without the speed setting
            body["voice_settings"].pop("speed", None)
            continue
        if r.status_code in (429, 500, 502, 503):
            time.sleep(5 + 5 * a)
            continue
        raise RuntimeError(f"TTS {r.status_code} {r.text[:300]}")
    raise RuntimeError("TTS: gave up")


def trim(x: np.ndarray) -> np.ndarray:
    f = int(0.01 * SR)
    n = len(x) // f
    rms = np.sqrt(np.mean(x[: n * f].reshape(n, f) ** 2, axis=1) + 1e-12)
    on = np.where(20 * np.log10(rms) > -45)[0]
    if not len(on):
        return x
    return x[max(0, on[0] * f - int(0.04 * SR)): min(len(x), (on[-1] + 1) * f + int(0.06 * SR))]


_WM = None


def hear(x: np.ndarray) -> str:
    global _WM
    if _WM is None:
        from faster_whisper import WhisperModel
        _WM = WhisperModel("medium", device="cpu", compute_type="int8")
    y = np.interp(np.arange(0, len(x), SR / 16000), np.arange(len(x)), x).astype(np.float32)
    segs, _ = _WM.transcribe(y, language="ru", beam_size=5, condition_on_previous_text=False, vad_filter=False)
    return " ".join(s.text.strip() for s in segs)


def norm(t: str) -> list[str]:
    from num2words import num2words
    t = re.sub(r"\[[^\]]*\]", " ", t).replace("́", "").lower().replace("ё", "е")
    t = re.sub(r"(\d+)[:.](\d+)", r"\1 \2", t)
    t = re.sub(r"\d+", lambda m: " " + num2words(int(m.group()), lang="ru") + " ", t)
    return re.findall(r"[а-яa-z]+", t)


def diff(script: str, heard: str) -> list[str]:
    import difflib
    a, b = norm(script), norm(heard)
    out = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if op == "equal":
            continue
        sa, sb = " ".join(a[i1:i2]), " ".join(b[j1:j2])
        # the same word in another case form (восемь / восемью, сбор / сбора) is not a dropped word
        if op == "replace" and i2 - i1 == j2 - j1 and all(x[:4] == y[:4] for x, y in zip(a[i1:i2], b[j1:j2])):
            continue
        out.append(f"{op}: script '{sa}' | heard '{sb}'")
    return out


def sample(voice_id: str, model: str) -> tuple[np.ndarray, list[dict]]:
    cfg = V3 if model == "v3" else V2
    parts, rep = [], []
    for text, punch, t3 in LINES:
        say = (t3 or text) if model == "v3" else text
        x = trim(tts(say, voice_id, cfg))
        # one retake when the first one drops a word
        d = diff(text, hear(x))
        if d:
            x2 = trim(tts(say, voice_id, cfg))
            d2 = diff(text, hear(x2))
            if len(d2) < len(d):
                x, d = x2, d2
        parts += [x, np.zeros(int((BEAT if punch else GAP) * SR), np.float32)]
        rep.append({"line": text, "dur": round(len(x) / SR, 2), "diff": d})
    return np.concatenate([np.zeros(int(0.3 * SR), np.float32)] + parts), rep


ALIASES = {"Дмитрий": ["дмитрий", "dmitr", "дима"], "Николай": ["николай", "nikola", "nicola", "коля"]}


def all_voices() -> list[dict]:
    out, tok = [], None
    for _ in range(20):
        j = VD.get("/v2/voices", page_size=100, **({"next_page_token": tok} if tok else {}))
        out += j.get("voices", [])
        tok = j.get("next_page_token")
        if not j.get("has_more") or not tok:
            break
    return out


def find_voice(name: str, vs: list[dict]) -> dict:
    keys = ALIASES.get(name, [name.lower()])
    hit = [v for v in vs if any(k in (v.get("name") or "").lower() for k in keys)]
    if not hit:
        print("account voices (not premade):", [v.get("name") for v in vs if v.get("category") != "premade"], flush=True)
        raise SystemExit(f"no voice named like {name!r} in the account")
    return hit[0]


def mp3(x: np.ndarray, path: Path) -> None:
    pcm = (np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes()
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", str(SR), "-ac", "1", "-i", "-",
                    "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "44100", "-b:a", "160k", str(path)], input=pcm, check=True)


def main(out: str) -> int:
    O = Path(out)
    O.mkdir(parents=True, exist_ok=True)
    acc = VD.account()
    need = sum(len(t) for t, _p, _t3 in LINES) * 7
    print(f"account: {acc['characters_left']} characters left; this test needs up to ~{need}", flush=True)
    if acc["characters_left"] < need:
        raise SystemExit("not enough ElevenLabs characters for the test")
    vs = all_voices()
    dm, nk = find_voice("Дмитрий", vs), find_voice("Николай", vs)
    print("voices:", "Принц Нур", NUR, "|", dm["name"], dm["voice_id"], "|", nk["name"], nk["voice_id"], flush=True)
    res = {}
    res["A"] = ("Принц Нур", "eleven_multilingual_v2", *sample(NUR, "v2"))
    res["B"] = ("Принц Нур", "eleven_v3 (sparse tags)", *sample(NUR, "v3"))
    for key, v in (("C", dm), ("D", nk)):
        a2, r2 = sample(v["voice_id"], "v2")
        a3, r3 = sample(v["voice_id"], "v3")
        e2, e3 = sum(len(r["diff"]) for r in r2), sum(len(r["diff"]) for r in r3)
        pick = ("eleven_multilingual_v2", a2, r2, e2, e3) if e2 <= e3 else ("eleven_v3", a3, r3, e2, e3)
        res[key] = (v["name"], f"{pick[0]} (STT differences: v2 {pick[3]}, v3 {pick[4]})", pick[1], pick[2])
    md = ["# Ep.4 v2 · RU voice test", "", "Same passage for every voice: the cold open, «Ларри — гений… Долго решать не придётся», "
          "the service-fee joke. Lines voiced one by one, 0.55 s between lines, 1.05 s after each punchline, speed 1.0. "
          "Each line heard back by faster-whisper medium (ru); a line with a dropped word was retaken once.", ""]
    note = []
    for key, (name, model, x, rep) in res.items():
        mp3(x, O / f"ru_voice_test_{key}.mp3")
        errs = sum(len(r["diff"]) for r in rep)
        dur = len(x) / SR
        md += [f"## {key} · {name} · {model}", f"{dur:.1f} s · STT differences: {errs}", ""]
        md += [f"- {r['line']} ({r['dur']} s)" + ("" if not r["diff"] else " — " + "; ".join(r["diff"])) for r in rep] + [""]
        note.append(f"{key} · {name} · {model.split(' (')[0]} · {dur:.0f} s · STT: {'clean' if not errs else str(errs) + ' diff'}")
        print(note[-1], flush=True)
    md += ["## The passage (RU script, re-read for spoken flow)", ""] + [f"{i + 1}. {t}" for i, (t, _p, _t3) in enumerate(LINES)]
    (O / "ru_voice_test.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (O / "ru_voice_test_note.txt").write_text("\n".join(note) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
