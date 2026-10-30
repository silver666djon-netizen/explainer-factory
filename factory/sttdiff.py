"""Narration vs script (Klot r89, rule: every render's narration is transcribed and diffed against the script).
The narration track (voice only) is transcribed with faster-whisper; both texts are normalised the same way (numbers,
money, percent and years to words, punctuation and hyphens out) and diffed word by word. A replace whose letters are
the same ("up front" / "upfront", "Stub Hub" / "StubHub") is not a difference."""
from __future__ import annotations

import difflib
import re

ONES = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
        "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]


def _lt100(n: int) -> str:
    if n < 20:
        return ONES[n]
    return TENS[n // 10] + ("-" + ONES[n % 10] if n % 10 else "")


def _lt1000(n: int) -> str:
    if n < 100:
        return _lt100(n)
    return ONES[n // 100] + " hundred" + (" and " + _lt100(n % 100) if n % 100 else "")


def cardinal(n: int) -> str:
    if n == 0:
        return "zero"
    out = []
    for val, name in ((10 ** 9, "billion"), (10 ** 6, "million"), (1000, "thousand")):
        if n >= val:
            out.append(_lt1000(n // val) + " " + name)
            n %= val
    if n:
        out.append(("and " if out and n < 100 else "") + _lt1000(n))
    return " ".join(out)


def year(n: int) -> str:
    if 2000 <= n <= 2009:
        return "two thousand" + (" and " + ONES[n - 2000] if n > 2000 else "")
    hi, lo = divmod(n, 100)
    return _lt100(hi) + " " + ("hundred" if lo == 0 else ("oh " + ONES[lo] if lo < 10 else _lt100(lo)))


def number(tok: str) -> str:
    t = tok.replace(",", "")
    if re.fullmatch(r"\d+\.\d+", t):
        a, b = t.split(".")
        if b == "5":
            return f"{cardinal(int(a))} and a half"
        return f"{cardinal(int(a))} point " + " ".join(ONES[int(c)] for c in b)
    n = int(t)
    if 1900 <= n <= 2099 and "," not in tok and "." not in tok:
        return year(n)
    return cardinal(n)


ORD = {1: "first", 2: "second", 3: "third", 5: "fifth", 8: "eighth", 9: "ninth", 12: "twelfth"}
SPELLING = {"defence": "defense", "licence": "license", "colour": "color", "favourite": "favorite", "centre": "center",
            "okay": "ok"}  # British / American spellings of the same spoken word


def ordinal(n: int) -> str:
    if n in ORD:
        return ORD[n]
    if n > 20 and n % 10 and n % 10 in ORD:
        return TENS[n // 10] + " " + ORD[n % 10]
    w = _lt100(n)
    return (w[:-1] + "ieth") if w.endswith("y") else w + "th"


SCALE = {"k": "thousand", "m": "million", "bn": "billion", "million": "million", "billion": "billion", "thousand": "thousand"}
CUR = {"$": "dollar", "£": "pound", "€": "euro"}
MONTHS = {"january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
          "november", "december"}
ORD_WORDS = {"first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth", "eleventh",
             "twelfth", "thirteenth", "fourteenth", "fifteenth", "sixteenth", "seventeenth", "eighteenth", "nineteenth",
             "twentieth", "twenty", "thirtieth", "thirty"}
SYM = "qqsym"  # marks a currency word whisper wrote as a symbol ("$18"): its "dollars" may not have been spoken


def words(text: str) -> list[str]:
    t = text.replace("’", "'").replace("—", " ").replace("–", " ")
    t = re.sub(r"(\d)\s+\.(\d)", r"\1.\2", t)  # whisper's "14 .1"
    t = re.sub(r"(\d)\s+,(\d{3})", r"\1,\2", t)  # whisper's "80 ,000"
    t = re.sub(r"\b(\d{1,2})[.:]?(\d{2})\s?(a\.?m\.?|p\.?m\.?)", lambda m: f"{_lt100(int(m.group(1)))} {_lt100(int(m.group(2)))} "
               f"{m.group(3).replace('.', '')}", t, flags=re.I)  # times: "11.40pm"
    t = re.sub(r"\b(\d{1,2})(st|nd|rd|th)\b", lambda m: ordinal(int(m.group(1))), t)
    t = re.sub(r"(?<=\d)\s*%", " " + SYM + "percent", t)  # "24% to 44%": whisper may write % for an unspoken one

    def money(m):
        cur, num, scale = m.group(1), m.group(2), (m.group(3) or "").lower()
        s = number(num) + (" " + SCALE[scale] if scale else "")
        return s + " " + SYM + CUR[cur]
    NUM = r"(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?"
    t = re.sub(r"([$£€])\s?(" + NUM + r")(?:\s?(bn|million|billion|thousand|k|m)\b)?", money, t, flags=re.I)
    t = re.sub(NUM, lambda m: number(m.group(0)), t)
    t = t.lower()
    t = re.sub(r"[^a-z' ]+", " ", t.replace("-", " ").replace(".", ""))
    out = []
    for w in t.split():
        w = w.strip("'")
        if not w:
            continue
        if w in ("dollars", "pounds", "euros", "percents"):
            w = w[:-1]
        w = SPELLING.get(w, w)
        out.append(w)
    # "September the first" / "September first" (whisper writes both "September 1st"): the date's "the" is dropped
    return [w for k, w in enumerate(out) if not (w == "the" and 0 < k < len(out) - 1 and out[k - 1] in MONTHS
                                                  and (out[k + 1] in ORD_WORDS))]


def _digit_runs(script_words: list[str], heard: str) -> str:
    """'Eight. Six. Four.' is read as three numbers; whisper may write them as one ('$864'). A heard digit string
    whose digits are, one by one, consecutive words of the script is written back as those single digits."""
    sw = " " + " ".join(script_words) + " "

    def sub(m):
        d = m.group(2)
        if len(d) < 2:
            return m.group(0)
        spoken = " ".join(ONES[int(c)] for c in d)
        return " " + spoken + " " if " " + spoken + " " in sw else m.group(0)
    return re.sub(r"([$£€]?)(?<![\d.,])(\d{2,4})(?![\d.,]\d)", sub, heard)


def diff(script: str, heard: str, known=()) -> list[str]:
    """known: [(script words, heard words)] - transcription slips already confirmed against the voice's phonemes
    (episode "stt_known", each with its reason); everything else is a difference.
    A currency word that exists only because whisper wrote a symbol ("Total, $48" for "Total: forty-eight") is not a
    difference; a currency word the script has and the voice drops still is."""
    a = words(script)
    a = [w[len(SYM):] if w.startswith(SYM) else w for w in a]
    b0 = words(_digit_runs(a, heard))
    sym = [w.startswith(SYM) for w in b0]
    b = [w[len(SYM):] if w.startswith(SYM) else w for w in b0]
    kn = {(" ".join(words(k[0])), " ".join(words(k[1]))) for k in known}
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    out = []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            continue
        if "".join(a[i1:i2]) == "".join(b[j1:j2]):
            continue  # split / merged compound
        if (" ".join(a[i1:i2]), " ".join(b[j1:j2])) in kn:
            continue
        if op == "insert" and all(sym[j1:j2]):
            continue  # "$" written by whisper, not a spoken "dollars"
        ctx = " ".join(a[max(0, i1 - 3):i1])
        out.append(f"{op}: script '{' '.join(a[i1:i2]) or '-'}' | heard '{' '.join(b[j1:j2]) or '-'}' (after '…{ctx}')")
    return out


def check_lines(voice, sr: int, lines, texts: dict, known=(), tc=lambda t: f"{t:.1f}s", pad: float = 0.12):
    """Each narration line (start, end, beat id) transcribed on its own and diffed against that beat's text.
    Returns (failures, notes: one 'id: heard' per line)."""
    fails, notes = [], []
    for t0, t1, bid in lines:
        text = texts.get(bid, "")
        if not text.strip():
            continue
        i, j = max(0, int((t0 - pad) * sr)), min(len(voice), int((t1 + pad) * sr))
        heard = transcribe(voice[i:j], sr)
        notes.append(f"{tc(t0)} {bid}: {heard}")
        fails += [f"{tc(t0)} {bid}: {d}" for d in diff(text, heard, known)]
    return fails, notes


_MODEL = None


def transcribe(audio, sr: int, model: str = "medium.en") -> str:
    global _MODEL
    import numpy as np
    from faster_whisper import WhisperModel
    if _MODEL is None:
        _MODEL = WhisperModel(model, device="cpu", compute_type="int8")
    x = np.asarray(audio, np.float32)
    if sr != 16000:
        n = int(len(x) * 16000 / sr)
        x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
    segs, _ = _MODEL.transcribe(x, language="en", beam_size=5, condition_on_previous_text=False, vad_filter=False)
    return " ".join(s.text.strip() for s in segs)
