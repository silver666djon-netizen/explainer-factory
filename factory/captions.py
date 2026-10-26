"""Subtitle cards for the burned-in karaoke and the .srt (production rule 23).

- A name, a number or a fixed phrase never splits across two cards: "J.C. Penney", "High Court", "Black Friday",
  "Fair and Square", "four eighty-nine ninety-nine", "nine hundred and eighty-five million dollars",
  "two fifty-nine fifty-nine", "zero point zero two percent", "four weeks", "July 2026". Detected automatically
  (number words + units, runs of capitalised words, month + year) plus the episode's own "caption_keep" phrases.
- At least two words per card. A one-word sentence ("Twice.", "One.") is a deliberate beat and keeps its own card.
- A card ends at a sentence end; inside a sentence the split is balanced and prefers commas, colons and dashes.
  A colon or a question mark followed by more of the same sentence ("Name: the countdown clock",
  "Britain's Which? checked") does not end a card."""
from __future__ import annotations

import re

NUM = set("""zero oh one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen
seventeen eighteen nineteen twenty thirty forty fifty sixty seventy eighty ninety hundred thousand million billion
trillion point""".split())
UNITS = set("""percent per cent dollars dollar pounds pound pence cents euros euro days day weeks week months month years
year hours hour minutes minute seconds second a.m. p.m. o'clock""".split())
MONTHS = set("january february march april may june july august september october november december".split())
STOP = set("""the a an in on at of to for and or but so if as by with from into it its this that these those he she they
we you i his her their our your my no not yes then when while after before every each all""".split())
DANGLE = set("""the a an of to in on at for and or but with by from his her their our your my its that this
is was are were be without when than if as how what who which where why so because while he she they we i can could would will must may might should""".split())
PARTICLE = set("down up out off back away".split())
ARTICLE = set("the a an his her their our your my its every".split())  # always on the card of the word they introduce
PREP = set("at in of for to by from within over under about after before just only nearly almost around roughly".split())  # stays with a number it introduces
CONNECT = {"and", "of", "&", "de", "la", "van", "von", "da"}
ABBR = re.compile(r"^(?:[A-Za-z]\.){2,}$|^(?:No|Mr|Mrs|Ms|Dr|St|vs|Inc|Ltd|Co|Jr|Sr)\.$")
OPEN = "\"'“‘«(["
CLOSE = "\"'”’»)]"


def core(w: str) -> str:
    return w.strip(OPEN).rstrip(CLOSE + ".,!?;:…").rstrip(CLOSE)


def _bare(w: str) -> str:  # without closing quotes
    return w.rstrip(CLOSE)


def is_num(w: str) -> bool:
    c = core(w).lower()
    if not c:
        return False
    if re.match(r"^[$£€]?\d[\d.,:]*%?$", c):
        return True
    return all(p in NUM for p in c.split("-"))


def is_unit(w: str) -> bool:
    return core(w).lower() in UNITS or w.lower().rstrip(",.;:!?") in UNITS


def is_cap(w: str) -> bool:
    c = core(w)
    return bool(c) and c[0].isupper()


def _soft_end(w: str) -> bool:  # list separator / clause break after this word
    return bool(re.search(r"[,;:—–…]$", _bare(w))) or w in ("—", "–")


def _dangles(w: str) -> bool:  # a card should not end on this word (mid-sentence)
    c = core(w).lower()
    return c in DANGLE or bool(re.search(r"(?:'d|'ll|'ve|n't)$", c))


def sentence_end(words: list[str], i: int) -> bool:
    w = _bare(words[i])
    if not re.search(r"[.!?…]$", w):
        return False
    if i == len(words) - 1:
        return True
    if ABBR.match(w):  # J.C. Penney, nine a.m. ...
        return False
    nxt = words[i + 1].lstrip(OPEN)
    return bool(nxt) and (nxt[0].isupper() or nxt[0].isdigit() or nxt[0] in "$£€")


def glue(words: list[str], keep: list[str] = ()) -> list[bool]:
    """glue[i] = word i and word i+1 must sit on the same card."""
    n = len(words)
    g = [False] * max(0, n - 1)
    starts = {0} | {i + 1 for i in range(n - 1) if sentence_end(words, i)}
    for i in range(n - 1):
        a, b = words[i], words[i + 1]
        if sentence_end(words, i):
            continue
        sep = bool(re.search(r"[,;:]$", _bare(a)))
        if is_num(a) and not sep and (is_num(b) or is_unit(b)):
            g[i] = True
        if is_unit(a) and core(a).lower() == "per" and core(b).lower() == "cent":
            g[i] = True
        if is_num(a) and not sep and core(b).lower() == "and" and i + 2 < n and is_num(words[i + 2]):
            g[i] = g[i + 1] = True
        if not sep and ((core(a).lower() in MONTHS and is_num(b) and core(b)[:1].isdigit())
                        or (core(a)[:1].isdigit() and core(b).lower() in MONTHS)):
            g[i] = True
        if is_cap(a) and not sep and not (i in starts and core(a).lower() in STOP):
            if is_cap(b):
                g[i] = True
            elif core(b).lower() in CONNECT and not re.search(r"[,;:]$", _bare(b)) and i + 2 < n and is_cap(words[i + 2]):
                g[i] = g[i + 1] = True
        if core(a).lower() in ARTICLE and a == core(a) and re.search(r"\w", b):
            g[i] = True
        if core(a).lower() in PREP and a == core(a):  # "at four eighty-nine…", "for a hundred…", "in Britain", "in the US"
            nxt2 = words[i + 2] if i + 2 < n else ""
            if is_num(b) or is_cap(b) or (core(b).lower() in ARTICLE and b == core(b) and nxt2 and (is_num(nxt2) or is_cap(nxt2))):
                g[i] = True
        if not sep and not is_num(a) and re.match(r"^[a-z]+(?:-[a-z]+)+$", a) and re.search(r"\w", b):
            g[i] = True  # a hyphenated adjective stays with its noun: "made-up number", "struck-through was price"
        if not sep and core(b).lower() in PARTICLE and re.match(r"^[a-z]+$", a) and a not in STOP | DANGLE | PREP:
            g[i] = True  # phrasal verbs: "wrote down", "marked down", "walked out", "shows up"
        if core(a).lower() in ("so", "and", "but", "because", "if", "when", "while", "that") and a == core(a) \
                and core(b).lower() in ("it", "he", "she", "they", "we", "you", "i"):
            g[i] = True  # "so it could be…": a clause starts on one card (conjunction, subject and verb)
            if i + 2 < n and not re.search(r"[,;:]$", _bare(b)) and re.search(r"\w", words[i + 2]):
                g[i + 1] = True
    for i in range(n - 1):  # a subject pronoun stays with its verb: "it sold", "you trust"
        a, b = words[i], words[i + 1]
        if core(a).lower() in ("it", "he", "she", "they", "we", "i", "you") and not re.search(r"[,;:.!?]$", _bare(a)) \
                and re.match(r"^[a-z][a-z']*$", b) and core(b).lower() not in STOP | DANGLE | PREP | PARTICLE:
            g[i] = True
    low = [core(w).lower() for w in words]
    for ph in keep or []:
        pw = [core(x).lower() for x in str(ph).split()]
        k = len(pw)
        for i in range(n - k + 1):
            if k > 1 and low[i:i + k] == pw:
                for j in range(i, i + k - 1):
                    g[j] = True
    return g


def _cards(atoms: list[list[int]], words: list[str], max_words: int, max_chars: int) -> list[list[int]]:
    """Balanced split of one sentence (a list of atoms = word-index groups) into cards."""
    n = len(atoms)
    total = sum(len(a) for a in atoms)
    INF = float("inf")
    best, prev = [0.0] + [INF] * n, [0] * (n + 1)
    for j in range(1, n + 1):
        for i in range(j - 1, -1, -1):
            idx = [k for a in atoms[i:j] for k in a]
            nw = sum(1 for k in idx if re.search(r"\w", words[k]))
            chars = len(" ".join(words[k] for k in idx))
            single = j - i == 1
            if j - i > 2 and (nw > max_words + 3 or chars > max_chars * 2.5):
                break  # (two atoms are always tried: a long number may take its last word rather than leave it alone)
            c = 1.0  # one more card
            if not single:  # over the size (a longer card wraps to a second line)
                c += 2.0 * max(0, nw - max_words) + 0.25 * max(0, chars - max_chars)
            if nw < 2 and total > 1:  # a lone word
                c += 20.0
            c += 0.6 * ((max_chars - min(chars, max_chars)) / max_chars) ** 2  # balanced cards
            if j < n:  # a break inside the sentence: free after a comma, colon or dash
                last = words[idx[-1]]
                if not (_soft_end(last) or words[atoms[j][0]] in ("—", "–")):
                    c += 1.0
                if _dangles(last) and not _soft_end(last):
                    c += 2.0
                if core(words[atoms[j][0]]).lower() == "of":
                    c += 0.6  # "the lack | of integrity"
                nxt = atoms[j]
                if len(nxt) == 1 and _soft_end(words[nxt[0]]) and words[nxt[0]] not in ("—", "–"):
                    c += 1.2  # the next card would open with the last word of this clause ("test | period,")
            if best[i] + c < best[j]:
                best[j], prev[j] = best[i] + c, i
    out, j = [], n
    while j > 0:
        i = prev[j]
        out.append([k for a in atoms[i:j] for k in a])
        j = i
    return out[::-1]


def chunk(words: list[str], max_words: int, max_chars: int, keep: list[str] = ()) -> list[list[int]]:
    """Word-index groups, one per card."""
    words = [w.strip() for w in words]
    n = len(words)
    if not n:
        return []
    g = glue(words, keep)
    cards, s0 = [], 0
    for i in range(n):
        if i == n - 1 or sentence_end(words, i):
            atoms, cur = [], [s0]
            for k in range(s0 + 1, i + 1):
                if g[k - 1]:
                    cur.append(k)
                else:
                    atoms.append(cur)
                    cur = [k]
            atoms.append(cur)
            cards += _cards(atoms, words, max_words, max_chars)
            s0 = i + 1
    out: list[list[int]] = []  # one-word sentences in a row share a card: "Eight. Six. Four."
    for c in cards:
        if out and len(c) == 1 and len(out[-1]) >= 1 and all(len(re.findall(r"\w+", words[k])) == 1 for k in out[-1]) \
                and all(sentence_end(words, k) for k in out[-1]) and sentence_end(words, c[0]) \
                and len(out[-1]) < max_words and len(" ".join(words[k] for k in out[-1] + c)) <= max_chars * 1.25:
            out[-1] = out[-1] + c
        else:
            out.append(c)
    return out
