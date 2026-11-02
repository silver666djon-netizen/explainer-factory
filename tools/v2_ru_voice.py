"""Ep.4 v2 RU review copy, step 1: the Russian narration (ElevenLabs eleven_v3, a deep calm Russian male narrator from the
voice library) for every line of timings.json ("ru"), and timings_ru.json in the same format: the lines placed in the same
order with the same designed pauses, hits, ad breaks and act starts; word times from ElevenLabs' character alignment; each
RU beat also carries its English original ("en": start, end, words) so the picture's English word anchors can be mapped
onto the Russian line (tools/v2_preview.py, RU mode). The key comes from ELEVENLABS_API_KEY and is never printed.
python tools/v2_ru_voice.py <dir with timings.json> <out dir>  -> timings_ru.json, voice_24k_ru.flac, ru_voice_report.md"""
from __future__ import annotations

import base64
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import voice_d as VD  # noqa: E402  (ElevenLabs helpers: get/post/account)

SR = 24000
KEYS = {"deep": 3, "calm": 2, "narrat": 3, "documentary": 3, "low": 2, "storytell": 2, "audiobook": 2, "mature": 1, "warm": 1,
        "глубок": 3, "спокойн": 2, "диктор": 3, "рассказ": 2, "низк": 2, "бархат": 1}


def score(t: str) -> float:
    t = t.lower()
    return sum(w for k, w in KEYS.items() if k in t)


def pick_voice() -> dict:
    cands = []
    for uc in ("narrative_story", "informative_educational", None):
        params = dict(page_size=50, gender="male", language="ru", sort="trending")
        if uc:
            params["use_cases"] = uc
        try:
            got = VD.get("/v1/shared-voices", **params).get("voices", [])
        except RuntimeError as e:
            print("library search:", e, flush=True)
            got = []
        for v in got:
            txt = " ".join(str(v.get(k) or "") for k in ("name", "description", "descriptive", "use_case", "age", "accent"))
            if v.get("age") == "young":
                continue
            cands.append({"voice_id": v["voice_id"], "owner": v.get("public_owner_id"), "name": v.get("name"),
                          "about": (v.get("description") or "")[:200], "uses": v.get("cloned_by_count") or 0,
                          "score": score(txt) + math.log10(1 + (v.get("cloned_by_count") or 0))})
    best = {}
    for c in cands:
        if c["voice_id"] not in best or c["score"] > best[c["voice_id"]]["score"]:
            best[c["voice_id"]] = c
    ranked = sorted(best.values(), key=lambda c: -c["score"])
    print("RU candidates:", [(c["name"], round(c["score"], 1)) for c in ranked[:8]], flush=True)
    mine = {m["voice_id"]: m for m in VD.get("/v2/voices", page_size=100).get("voices", [])}
    for c in ranked[:6]:
        if c["voice_id"] in mine:
            return c
        r = VD.post(f"/v1/voices/add/{c['owner']}/{c['voice_id']}", {"new_name": f"CS RU {c['name']}"[:40]})
        if r.status_code == 200:
            c["voice_id"] = r.json().get("voice_id", c["voice_id"])
            return c
        print("could not add", c["name"], r.status_code, r.text[:160], flush=True)
    raise SystemExit("no Russian narrator voice could be added")


def tts_aligned(text: str, voice_id: str) -> tuple[np.ndarray, list[list]]:
    """(audio, words [[word, start, end]]) — the character alignment when the model gives it, else even spacing."""
    body = {"text": text, "model_id": VD.MODEL, "voice_settings": {"stability": 0.5}}
    for a in range(5):
        r = VD.post(f"/v1/text-to-speech/{voice_id}/with-timestamps", body, output_format="pcm_24000")
        if r.status_code == 200:
            j = r.json()
            x = np.frombuffer(base64.b64decode(j["audio_base64"]), np.int16).astype(np.float32) / 32768.0
            al = j.get("alignment") or j.get("normalized_alignment")
            return x, words_from(text, al, len(x) / SR)
        if r.status_code in (429, 500, 502, 503):
            time.sleep(5 + 5 * a)
            continue
        if r.status_code in (400, 404, 422):  # no timestamps for this model: plain synthesis, even word spacing
            r2 = VD.post(f"/v1/text-to-speech/{voice_id}", body, output_format="pcm_24000")
            if r2.status_code == 200:
                x = np.frombuffer(r2.content, np.int16).astype(np.float32) / 32768.0
                return x, words_from(text, None, len(x) / SR)
        raise RuntimeError(f"TTS {r.status_code} {r.text[:300]}")
    raise RuntimeError("TTS: gave up")


def words_from(text: str, al: dict | None, dur: float) -> list[list]:
    toks = text.split()
    if al and al.get("characters"):
        ch, st, en = al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]
        out, cur, s0 = [], "", None
        for c, a, b in zip(ch, st, en):
            if c.isspace():
                if cur:
                    out.append([cur, round(s0, 3), round(prev_e, 3)])
                cur, s0 = "", None
                continue
            if s0 is None:
                s0 = a
            cur += c
            prev_e = b
        if cur:
            out.append([cur, round(s0, 3), round(prev_e, 3)])
        if len(out) == len(toks):
            return [[t, s, e] for t, (_w, s, e) in zip(toks, out)]
    n = sum(len(t) + 1 for t in toks) or 1
    out, c = [], 0.0
    for t in toks:
        a = c / n * dur
        c += len(t) + 1
        out.append([t, round(a, 3), round(c / n * dur, 3)])
    return out


def trim(x: np.ndarray, words: list[list]) -> tuple[np.ndarray, list[list]]:
    """Cut the silence before the first and after the last sound (-45 dBFS, 10 ms frames), keep 40 ms each side."""
    f = int(0.01 * SR)
    n = len(x) // f
    rms = np.sqrt(np.mean(x[: n * f].reshape(n, f) ** 2, axis=1) + 1e-12)
    on = np.where(20 * np.log10(rms) > -45)[0]
    if not len(on):
        return x, words
    a, b = max(0, on[0] * f - int(0.04 * SR)), min(len(x), (on[-1] + 1) * f + int(0.04 * SR))
    sh = a / SR
    return x[a:b], [[w, round(max(0.0, s - sh), 3), round(max(0.0, e - sh), 3)] for w, s, e in words]


def main(src: str, out: str) -> int:
    import soundfile as sf
    T = json.loads((Path(src) / "timings.json").read_text())
    O = Path(out)
    O.mkdir(parents=True, exist_ok=True)
    acc = VD.account()
    need = sum(len(b["ru"]) for b in T["beats"])
    print(f"account: plan {acc['plan']}, {acc['characters_left']} characters left; this run needs {need}", flush=True)
    if acc["characters_left"] < need * 1.05:
        raise SystemExit(f"not enough ElevenLabs characters: {acc['characters_left']} left, {need} needed")
    v = pick_voice()
    print("voice:", v["name"], "|", v["about"][:120], flush=True)
    lines = []
    for b in T["beats"]:
        x, ws = tts_aligned(b["ru"], v["voice_id"])
        x, ws = trim(x, ws)
        lines.append((b, x, ws))
        print(f"{b['id']}: {len(x) / SR:.2f} s (en {b['end'] - b['start']:.2f} s)", flush=True)
    # place the lines with the English file's own pauses (designed silences, hits, act cards, ad breaks)
    R = json.loads(json.dumps(T))
    beats, cur, pos = [], T["beats"][0]["start"], {}
    for i, (b, x, ws) in enumerate(lines):
        s, e = cur, cur + len(x) / SR
        pos[b["id"]] = (s, e)
        nb = dict(b, start=round(s, 3), end=round(e, 3), words=ws, text=b["ru"], en={"start": b["start"], "end": b["end"], "words": b["words"],
                                                                                     "text": b["text"]})
        for k in ("heard", "diff", "takes"):
            nb.pop(k, None)
        beats.append(nb)
        gap = (T["beats"][i + 1]["start"] - b["end"]) if i + 1 < len(T["beats"]) else (T.get("total", b["end"] + 3) - b["end"])
        cur = e + gap
    R["beats"] = beats
    R["total"] = round(cur, 3)
    en = {b["id"]: b for b in T["beats"]}

    def remap(t, bid):
        b, (s, e) = en[bid], pos[bid]
        if t <= b["end"]:
            return s + (t - b["start"]) * (e - s) / max(0.01, b["end"] - b["start"])
        return e + (t - b["end"])
    for h in R["hits"]:
        h["at"] = round(remap(h["at"], h["line"]), 3)
        if "silence_from" in h:
            h["silence_from"] = round(remap(h["silence_from"], h["line"]), 3)
    order = [b["id"] for b in T["beats"]]
    for a in R["acts"]:
        first = next(b for b in T["beats"] if b["act"] == a["act"])
        a["start"] = round(pos[first["id"]][0] - (first["start"] - a["start"]), 3)
    for k in R["breaks"]:
        p = k["after"]
        k["at"] = round(pos[p][1] + (k["at"] - en[p]["end"]), 3)
    R["voice"] = {"engine": "ElevenLabs " + VD.MODEL, "voice": v["name"], "language": "ru", "review_copy": True}
    voice = np.zeros(int((R["total"] + 1) * SR), np.float32)
    for b, x, _ws in lines:
        i = int(round(pos[b["id"]][0] * SR))
        voice[i:i + len(x)] += x[: len(voice) - i]
    sf.write(O / "voice_24k_ru.flac", voice, SR)
    (O / "timings_ru.json").write_text(json.dumps(R, ensure_ascii=False))
    ratio = sum(len(x) for _b, x, _w in lines) / SR / sum(b["end"] - b["start"] for b in T["beats"])
    (O / "ru_voice_report.md").write_text(
        f"# Ep.4 v2 · RU review copy · narration\n\nVoice: {v['name']} (ElevenLabs voice library) — {v['about']}\n\n"
        f"Model: {VD.MODEL}. Lines: {len(lines)}. Narration {ratio:.2f}x the English length; total {R['total'] / 60:.0f}:{R['total'] % 60:04.1f}.\n"
        f"Characters used: {need}.\n", encoding="utf-8")
    print(f"done: total {R['total']:.1f} s, RU/EN length {ratio:.2f}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:3]))
