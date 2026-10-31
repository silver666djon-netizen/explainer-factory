"""Ep.4 v2 "The Seven-Minute Heist": the whole English narration in Klot's chosen voice (sample A: OpenAI gpt-audio
"fable" through OpenRouter), voiced line by line with an acting note per line, checked line by line against the script
(factory.sttdiff, faster-whisper medium.en) and retaken on any difference. Writes:
  cs_ep04v2_voice_en.mp3   the voice track (narration only, designed pauses, silences after the brass hits)
  timings.json             every line: start/end, words (script words with their spoken times), shots, hits, ad breaks
  voice_stt.md             heard text + diff per line
  ad_breaks.md             the YouTube Studio mid-roll table, printed from timings.json
python tools/v2_voice.py <out dir>      (OPENROUTER_API_KEY; lines are cached in .cache/v2voice)"""
from __future__ import annotations

import base64
import concurrent.futures as cf
import hashlib
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "episodes" / "0005-drip-pricing" / "v2"))
import scenes  # noqa: E402
from factory import sttdiff  # noqa: E402

SR = 24000
MODEL, VOICE = "openai/gpt-audio", "fable"
CACHE = ROOT / ".cache" / "v2voice"
RESPELL = {"Live Nation": "Lyve Nation"}          # TTS input only: read /laɪv/
# transcription slips waived with their reason (the voice says the script's words):
KNOWN = [("Live Nation", "Lyve Nation"),          # the TTS respelling is what the transcriber may write back
         ("all together", "altogether")]          # same sounds; whisper spells the adverb
HIT_LEN = 0.9                                      # brass hit length; then one real second of silence
ACT_CARD = 3.0                                     # after each ad break: the act title card (music, no voice)
SYSTEM = ("You are a voice actor: a British documentary narrator, male, Received Pronunciation, low voice. "
          "Speak the user's line exactly as written, word for word, nothing before or after it. Direction for this line: {note}.")
ACT_NOTE = {
    "COLD": "low and unhurried, drawing the listener in, a storyteller at night",
    "A1": "low and unhurried, a story told at night, gently wry about Larry, never mocking",
    "A2": "measured and curious, a detective laying out evidence, clear on every number",
    "A3": "warm and dry, a touch of mock-formality, like reading a charge sheet",
    "A4": "firm and steady, then warmer and lighter as the story resolves",
}
# per-line direction (matched on the start of the line); everything else gets its act's note
NOTES = [
    ("Larry closes the first tab", "light and wry, a faint smile on 'Larry is a genius'"),
    ("Remember that number", "slower, leaning in, a quiet warning"),
    ("8:14. A little clock", "calm, then a small dry pause before 'there'"),
    ("8:18. Next screen", "slower, each fee placed like a card on a table"),
    ("Total: forty-eight", "slow and heavy, after a held breath"),
    ("He looks at the clock", "quieter, tense, unhurried"),
    ("8:19. Larry presses Pay", "very quiet and flat, after the silence"),
    ("Seven minutes. Eighteen dollars", "low, wondering"),
    ("So why would a man", "puzzled, a slight smile"),
    ("To answer that", "low, conspiratorial, leaving it hanging"),
    ("Same total. Just served", "dry"),
    ("Your brain files the first", "plain and certain"),
    ("That was the blueprint", "building anticipation"),
    ("Here's what happened", "steady, letting each number land"),
    ("And all together", "slow and heavy on 'twenty-one percent', after a silence"),
    ("Twenty-one percent. For the same", "quiet, emphatic"),
    ("So Larry isn't foolish", "warm, reassuring, a smile on 'Larry is the average'"),
    ("And here's the part you might", "leaning in, a wry smile"),
    ("But why does it work", "curious, slower"),
    ("Because the safe in your head", "intriguing, a little theatrical"),
    ("Five dollars is five dollars", "dry"),
    ("And that little clock", "conspiratorial, a smile on 'It's the lookout'"),
    ("Four locks. One click", "firm and clear"),
    ("The rehearsal was over", "theatrical, quiet"),
    ("If you like catching prices", "friendly, light, quick"),
    ("Because when a trick", "low, conspiratorial, leaving it hanging"),
    ("Name: the resort fee", "mock-formal, reading a charge sheet"),
    ("Known associates", "mock-formal, dry, a smile on 'a newspaper nobody has opened since 1998'"),
    ("Larry will use none", "dry, a faint smile"),
    ("Resort fees aren't taxes", "dry, a smile on 'They just like to sit next to them'"),
    ("Then there's the biggest name", "low, a slight menace"),
    ("In September 2026, a judge", "careful and neutral, precise on 'allegation'"),
    ("Now, the defence", "fair, measured, a courtroom tone"),
    ("Think about that", "quieter, thoughtful"),
    ("So who stops a race", "low, conspiratorial, leaving it hanging"),
    ("Funny thing is", "light, wry"),
    ("Cars got the total", "dry, a smile"),
    ("Because in 2025, the cops", "a little lift, energetic"),
    ("A driving-school group", "steady, then dry and amused on 'Three pounds. Very expensive pounds'"),
    ("The same company that ran", "pointed, quiet"),
    ("But no law sits next to you", "warm, encouraging, a lift on 'and do it right'"),
    ("Suddenly,", "a small surprise"),
    ("Larry reopens the first tab", "warm, a real smile on 'This time, Larry really is a genius'"),
    ("Saturday night", "warm and glowing"),
    ("So — why did Larry press Pay", "slow, reflective, the answer to the whole case"),
    ("Case closed", "firm, final, measured"),
    ("The verdict", "measured, like a judge reading a verdict"),
    ("Next case", "intriguing, a little playful"),
    ("Subscribe, so the next", "friendly, warm"),
]
# designed silences before a line (reveals); hits: (line start, where) with one real second of silence after
PRE = {"8:19. Larry presses Pay": 1.0, "And all together": 1.0, "Total: forty-eight": 0.5, "Case closed": 0.6}
HITS = {"Why? Somebody spent years": "after", "And all together": "number", "Case closed": "start"}


def _first(d, text):
    for k, v in (d.items() if isinstance(d, dict) else d):
        if text.startswith(k):
            return v
    return None


def plan() -> list[dict]:
    import voice_samples as vs  # the cold open's own notes, exactly as sample A
    rows = []
    cold = 0
    for key, bid, b in scenes.beat_ids():
        en, ru, pause, sound, shots = b[:5]
        extra = b[5] if len(b) > 5 else {}
        if key == "COLD":
            cold += 1
        note = extra.get("note") or (vs.LINES[cold - 1][1] if key == "COLD" else (_first(NOTES, en) or ACT_NOTE[key]))
        tts = en
        for a, r in RESPELL.items():
            tts = tts.replace(a, r)
        rows.append({"id": bid, "act": key, "text": en, "ru": ru, "tts": tts, "note": note, "pause": pause,
                     "pre": _first(PRE, en) or 0.0, "hit": _first(HITS, en), "sound": sound,
                     "shots": [{"picture": p, "tech": t, "source": s} for p, t, s in shots],
                     "cliff": key in scenes.CLIFF and en.startswith(scenes.CLIFF[key])})
    return rows


def _key(r):
    return hashlib.sha1(json.dumps([MODEL, VOICE, r["tts"], r["note"], SYSTEM]).encode()).hexdigest()[:16]


def take(text: str, note: str) -> np.ndarray:
    import requests
    key = os.environ["OPENROUTER_API_KEY"].strip()
    body = {"model": MODEL, "stream": True, "modalities": ["text", "audio"], "audio": {"voice": VOICE, "format": "pcm16"},
            "messages": [{"role": "system", "content": SYSTEM.format(note=note)}, {"role": "user", "content": text}]}
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


def trim(x: np.ndarray) -> np.ndarray:
    """Cut leading/trailing silence at word boundaries only (R33): 25 ms of the quiet kept on each side."""
    hop = int(0.01 * SR)
    n = len(x) // hop
    if n < 3:
        return x
    rms = np.sqrt(np.mean(x[: n * hop].reshape(n, hop) ** 2, axis=1))
    on = np.where(rms > 10 ** (-45 / 20))[0]
    if not len(on):
        return x
    a = max(0, on[0] * hop - int(0.025 * SR))
    b = min(len(x), (on[-1] + 1) * hop + int(0.06 * SR))
    y = x[a:b].copy()
    f = int(0.006 * SR)
    y[:f] *= np.linspace(0, 1, f)
    y[-f:] *= np.linspace(1, 0, f)
    return y


def level(x: np.ndarray, target_db: float = -20.0) -> np.ndarray:
    hop = int(0.02 * SR)
    n = len(x) // hop
    rms = np.sqrt(np.mean(x[: n * hop].reshape(n, hop) ** 2, axis=1)) if n else np.array([1e-4])
    act = rms[rms > 10 ** (-40 / 20)]
    cur = float(np.sqrt(np.mean(act ** 2))) if len(act) else 1e-4
    y = x * (10 ** (target_db / 20) / cur)
    pk = float(np.abs(y).max())
    return y * (0.9 / pk) if pk > 0.9 else y


_LOCK = threading.Lock()
_WM = None


def hear_words(x: np.ndarray):
    """faster-whisper medium.en on one line: (text, [(word, start, end)])."""
    global _WM
    from faster_whisper import WhisperModel
    with _LOCK:
        if _WM is None:
            _WM = WhisperModel("medium.en", device="cpu", compute_type="int8")
        y = np.interp(np.linspace(0, len(x) - 1, int(len(x) * 16000 / SR)), np.arange(len(x)), x).astype(np.float32)
        y = np.concatenate([np.zeros(1600, np.float32), y, np.zeros(3200, np.float32)])
        segs, _ = _WM.transcribe(y, language="en", beam_size=5, condition_on_previous_text=False, vad_filter=False,
                                 word_timestamps=True)
        segs = list(segs)
    text = " ".join(s.text.strip() for s in segs)
    ws = [(w.word.strip(), max(0.0, w.start - 0.1), max(0.0, w.end - 0.1)) for s in segs for w in (s.words or [])]
    return text, ws


def voice_line(r: dict) -> dict:
    CACHE.mkdir(parents=True, exist_ok=True)
    k = _key(r)
    wav, meta = CACHE / f"{k}.npy", CACHE / f"{k}.json"
    if wav.exists() and meta.exists():
        m = json.loads(meta.read_text())
        m["diff"] = sttdiff.diff(r["text"], m["heard"], KNOWN)  # re-checked with today's normaliser
        if not m["diff"]:
            return {**m, "audio": np.load(wav), "cached": True}
    best = None
    for n in range(1, 7):
        x = level(trim(take(r["tts"], r["note"])))
        heard, ws = hear_words(x)
        d = sttdiff.diff(r["text"], heard, KNOWN)
        print(f"  {r['id']} take {n}: {'ok' if not d else '; '.join(d)[:200]}", flush=True)
        if best is None or len(d) < len(best[1]):
            best = (x, d, heard, ws, n)
        total = n
        if not d:
            break
    x, d, heard, ws, n = best
    m = {"heard": heard, "diff": d, "hwords": ws, "takes": total, "kept": n}
    np.save(wav, x)
    meta.write_text(json.dumps(m))
    return {**m, "audio": x, "cached": False}


def align(text: str, ws: list, dur: float) -> list:
    """Script words (as displayed) with spoken times: each display word is normalised like the STT diff and matched to
    the heard words; unmatched words are spread between their matched neighbours."""
    import difflib
    toks = text.split()
    sn, owner = [], []
    for i, t in enumerate(toks):
        for w in sttdiff.words(t) or [t.lower()]:
            sn.append(w.replace(sttdiff.SYM, ""))
            owner.append(i)
    hn, hidx = [], []
    for j, (w, s, e) in enumerate(ws):
        for x in sttdiff.words(w) or []:
            hn.append(x.replace(sttdiff.SYM, ""))
            hidx.append(j)
    span = [[None, None] for _ in toks]
    for a, b, size in difflib.SequenceMatcher(a=sn, b=hn, autojunk=False).get_matching_blocks():
        for o in range(size):
            ti, (_, s, e) = owner[a + o], ws[hidx[b + o]]
            span[ti][0] = s if span[ti][0] is None else min(span[ti][0], s)
            span[ti][1] = e if span[ti][1] is None else max(span[ti][1], e)
    # fill gaps: an unmatched run between two matched words shares the time between them evenly
    if not any(sp[0] is not None for sp in span):
        step = dur / max(1, len(toks))
        return [[t, round(i * step, 3), round((i + 1) * step, 3)] for i, t in enumerate(toks)]
    i = 0
    while i < len(toks):
        if span[i][0] is not None:
            i += 1
            continue
        j = i
        while j < len(toks) and span[j][0] is None:
            j += 1
        a = span[i - 1][1] if i > 0 else 0.0
        b = span[j][0] if j < len(toks) else dur
        b = max(a, b)
        m = j - i
        for k in range(m):
            span[i + k] = [a + (b - a) * k / m, a + (b - a) * (k + 1) / m]
        i = j
    out = [[t, round(float(sp[0]), 3), round(float(min(sp[1], dur)), 3)] for t, sp in zip(toks, span)]
    for i in range(1, len(out)):  # monotone
        out[i][1] = max(out[i][1], out[i - 1][1])
        out[i][2] = max(out[i][2], out[i][1])
    return out


def tc(s: float) -> str:
    return f"{int(s // 60)}:{s % 60:05.2f}"


def main(out_dir: str) -> int:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rows = plan()
    with cf.ThreadPoolExecutor(4) as ex:
        res = list(ex.map(voice_line, rows))
    t = 0.6
    beats, hits, breaks, acts, stt = [], [], [], [], []
    clips = []
    cur_act = None
    for r, v in zip(rows, res):
        if r["act"] != cur_act:
            if cur_act is not None and breaks and breaks[-1]["after"] == beats[-1]["id"]:
                t += ACT_CARD
            acts.append({"act": r["act"], "start": round(t, 3), "name": scenes.PALETTE[r["act"]][0],
                         "palette": scenes.PALETTE[r["act"]][1]})
            cur_act = r["act"]
        t += r["pre"]
        x = v["audio"]
        dur = len(x) / SR
        words = align(r["text"], v["hwords"], dur)
        start = t
        clips.append((start, x))
        end = start + dur
        after = r["pause"]
        if r["hit"]:
            if r["hit"] == "after":
                h = end + 0.35
            elif r["hit"] == "start":
                h = start
            else:  # on the first number word of the line
                nums = [w for w in words if w[0].lower().startswith("twenty")]
                h = start + (nums[0][1] if nums else 0.0)
            hits.append({"at": round(h, 3), "len": HIT_LEN, "line": r["id"], "silence_from": round(max(end, h + HIT_LEN), 3)})
            after = max(after, (max(end, h + HIT_LEN) + 1.0) - end)  # one real second of silence after the hit
        t = end + after
        beats.append({"id": r["id"], "act": r["act"], "start": round(start, 3), "end": round(end, 3),
                      "next": None, "text": r["text"], "ru": r["ru"], "note": r["note"], "sound": r["sound"],
                      "words": words, "shots": r["shots"], "takes": v["takes"], "heard": v["heard"], "diff": v["diff"]})
        stt.append(f"| {r['id']} | {tc(start)} | {v['takes']} | {'OK' if not v['diff'] else 'DIFF: ' + '; '.join(v['diff'])} | {v['heard']} |")
        if r["cliff"]:
            breaks.append({"n": len(breaks) + 1, "at": round(t, 3), "after": r["id"], "line": r["text"], "ru": r["ru"]})
    total = t + 1.5
    for i, b in enumerate(beats):
        b["next"] = beats[i + 1]["start"] if i + 1 < len(beats) else round(total, 3)
    voice = np.zeros(int(total * SR) + SR, np.float32)
    for s, x in clips:
        i = int(round(s * SR))
        voice[i:i + len(x)] += x
    wav = out / "_voice.wav"
    import wave
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(voice, -1, 1) * 32767).astype(np.int16).tobytes())
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(wav), "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "48000",
                    "-c:a", "libmp3lame", "-b:a", "192k", str(out / "cs_ep04v2_voice_en.mp3")], check=True)
    np.save(out / "_voice.npy", voice)
    T = {"episode": "0005-drip-pricing", "version": "v2", "voice": {"provider": "OpenRouter", "model": MODEL, "voice": VOICE,
                                                                     "respell": RESPELL},
         "sr": SR, "total": round(total, 3), "acts": acts, "beats": beats, "hits": hits, "breaks": breaks,
         "act_card": ACT_CARD, "hit_len": HIT_LEN}
    (out / "timings.json").write_text(json.dumps(T, indent=1, ensure_ascii=False))
    bad = [b for b in beats if b["diff"]]
    (out / "voice_stt.md").write_text("# Ep.4 v2 voice · line-by-line STT diff (faster-whisper medium.en)\n\n"
                                      f"{len(beats)} lines, {sum(b['takes'] for b in beats)} takes, {len(bad)} with a difference.\n\n"
                                      "| Line | Starts | Takes | Diff | Heard |\n|---|---|---|---|---|\n" + "\n".join(stt) + "\n")
    L = ["# Ep.4 v2 · ad breaks (YouTube Studio → Content → the video → Monetization → Ad breaks → place manually)", "",
         f"From timings.json (voice: {VOICE}, total {tc(total)}). Each break sits in the silence after the cliffhanger,"
         f" before the {ACT_CARD:.0f} s act title card.", "", "| Break | Timecode | After the line (EN / RU) |", "|---|---|---|"]
    for b in breaks:
        m, s = divmod(b["at"], 60)
        L.append(f"| {b['n']} | **{int(m)}:{int(s):02d}** ({tc(b['at'])}) | {b['line']}<br>*{b['ru']}* |")
    L += ["", "| Act | Starts |", "|---|---|"] + [f"| {a['name']} | {tc(a['start'])} |" for a in acts]
    (out / "ad_breaks.md").write_text("\n".join(L) + "\n")
    print(f"total {tc(total)}, {len(beats)} lines, {sum(b['takes'] for b in beats)} takes, diffs {len(bad)}; breaks",
          [tc(b['at']) for b in breaks], flush=True)
    for b in bad:
        print("DIFF", b["id"], b["diff"], flush=True)
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
