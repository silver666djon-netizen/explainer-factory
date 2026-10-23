"""Language versions of an episode (lang=ru etc.): one translation file per episode, one render.

episodes/<slug>/lang/<code>.json
  {"voice": {"engine": "edge", "voice": "ru-RU-DmitryNeural", "rate": "+0%"},
   "title": "...", "description": "...",
   "beats":   {"<beat id>": {"text": "narration", "say": "optional TTS spelling", "anchors": {"English word": "русское"},
                             "patch": {"visual.endscreen.times.v1": 1.2}}},   # optional retiming for the new voice
   "anchors": {"English word": "русское слово"},          # shared anchors (any beat)
   "strings": {"English on-screen string": "Русская строка"},   # every plate, mark, card, chart label ... (identity allowed)
   "assets":  {"next_ticket.png": "lang/ru/next_ticket.png"}}  # files referenced by the script
Per-language pictures with baked-in words go to episodes/<slug>/lang/<code>/images/<key>.png (they win over images/).

The switch: FACTORY_LANG=<code> (build --lang sets it). load_episode() then returns the translated episode, and
ui() translates the engine's own fixed words. A missing narration, on-screen string or anchor stops the build with a
list of what is missing (no half-English renders)."""
from __future__ import annotations

import copy
import json
import os
import re
from pathlib import Path

UI = {
    "ru": {
        "LARRY'S TAB": "СЧЁТ ЛАРРИ",
        "EVIDENCE": "УЛИКА",
        "EXHIBIT": "ВЕЩДОК",
        "CASE FILE #": "ДЕЛО №",
        "NEXT: CASE FILE #": "ДАЛЕЕ: ДЕЛО №",
        "CONFIDENTIAL": "СЕКРЕТНО",
        "NEXT CASE  >": "СЛЕДУЮЩЕЕ ДЕЛО  >",
        "SUBSCRIBE": "ПОДПИСАТЬСЯ",
        "SUBSCRIBED": "ВЫ ПОДПИСАНЫ",
        "ALLEGED": "ПО ВЕРСИИ ИСТЦА",
        "SUSPECT No.": "ПОДОЗРЕВАЕМЫЙ №",
        "NAME": "ИМЯ",
        "ALIAS": "ОН ЖЕ",
        "LAST SEEN": "ЗАМЕЧЕН",
        "NOTES": "ЗАМЕТКИ",
        "Open": "Открыто",
        "Archive film": "Архивная плёнка",
        "Reconstruction": "Реконструкция",
        "STUDY SUMMARY  ·  PARAPHRASED": "ИССЛЕДОВАНИЕ  ·  ПЕРЕСКАЗ",
        "TOTAL": "ИТОГО",
        "EXIT": "ВЫХОД",
    },
}

# Cyrillic-capable fonts of the same character (OFL, release "fonts-cyr", downloaded by the render workflow)
FONTS = {
    "ru": {
        "headline": ["assets/fonts/Oswald-Bold.ttf"],
        "body": ["assets/fonts/Montserrat-Black.ttf"],
        "comic": ["assets/fonts/Pangolin-Regular.ttf"],
        "marker": ["assets/fonts/ShantellSans-ExtraBold.ttf", "assets/fonts/Pangolin-Regular.ttf"],
        "typewriter": ["assets/fonts/CourierPrime-Regular.ttf", "assets/fonts/PTM55FT.ttf"],
    },
}

# words that make a number land (stat "land before the spoken number")
NUM_WORDS = {
    "ru": ("ноль", "один", "одна", "одно", "два", "две", "три", "четыре", "пять", "шесть", "семь", "восемь", "девять",
           "десять", "одиннадцать", "двенадцать", "тринадцать", "четырнадцать", "пятнадцать", "шестнадцать",
           "семнадцать", "восемнадцать", "девятнадцать", "двадцать", "тридцать", "сорок", "пятьдесят", "шестьдесят",
           "семьдесят", "восемьдесят", "девяносто", "сто", "двести", "триста", "четыреста", "пятьсот", "шестьсот",
           "семьсот", "восемьсот", "девятьсот", "тысяча", "тысячи", "миллион", "миллиона", "миллиард", "ноль",
           "полтора", "половина"),
}

ANCHOR_KEYS = ("on", "word", "label_on", "sting_on", "click_on", "open_stamp_on", "until_on", "circle_on", "stamp_on",
               "push_on", "hook_on")
ANCHOR_LISTS = ("type_on",)
TEXT_KEYS = {"text", "label", "caption", "title", "headline", "body", "highlight", "kicker", "source", "name", "alias",
             "tag", "stamp", "tagline", "newsreel", "prefix", "suffix", "quote", "open_stamp", "amount"}
LIST_KEYS = {"inside", "verdict", "labels", "fees", "value_labels", "lines"}
SKIP_KEYS = {"prompt", "note", "credit", "file", "pre", "post", "font", "color", "role", "align", "look", "motion", "mode",
             "type", "kind", "unit", "mark", "bg", "beat", "say", "id", "section", "music", "sting", "hit", "sfx", "image"}


def lang() -> str | None:
    code = (os.environ.get("FACTORY_LANG") or "").strip().lower()
    return None if code in ("", "en") else code


def ui(s: str) -> str:
    code = lang()
    return UI.get(code, {}).get(s, s) if code else s


def num_words() -> tuple:
    return NUM_WORDS.get(lang() or "", ())


def fonts() -> dict:
    return FONTS.get(lang() or "", {})


def _norm(w: str) -> str:
    return "".join(c for c in w.lower() if c.isalnum())


def _in_text(phrase: str, text: str) -> bool:
    toks = [_norm(w) for w in text.split() if _norm(w)]
    target = [_norm(w) for w in str(phrase).split() if _norm(w)]
    return bool(target) and any(toks[i:i + len(target)] == target for i in range(len(toks) - len(target) + 1))


def _needs(s: str) -> bool:
    return bool(re.search(r"[A-Za-z]", s))


def apply(ep: dict, ep_dir: str | Path, code: str) -> dict:
    """Translated deep copy of an episode. Raises ValueError listing everything untranslated."""
    path = Path(ep_dir) / "lang" / f"{code}.json"
    tr = json.loads(path.read_text(encoding="utf-8"))
    ep = copy.deepcopy(ep)
    strings, assets = tr.get("strings") or {}, tr.get("assets") or {}
    shared_anchors = tr.get("anchors") or {}
    missing: list[str] = []

    def tstr(s, where):
        if s in strings:
            return strings[s]
        if _needs(s):
            missing.append(f"string  {where}: {s!r}")
        return s

    def walk(o, where, anchors, narration, ctx=""):
        if isinstance(o, dict):
            for k in list(o.keys()):
                x = o[k]
                w = f"{where}.{k}"
                if k in ANCHOR_KEYS and isinstance(x, str):
                    o[k] = anchors.get(x, shared_anchors.get(x, x))
                    if not _in_text(o[k], narration) and k != "hook_on":
                        missing.append(f"anchor  {w}: {x!r} -> {o[k]!r} not in the translated narration")
                elif k in ANCHOR_LISTS and isinstance(x, list):
                    o[k] = [anchors.get(a, shared_anchors.get(a, a)) for a in x]
                    for a, b in zip(x, o[k]):
                        if not _in_text(b, narration):
                            missing.append(f"anchor  {w}: {a!r} -> {b!r} not in the translated narration")
                elif k == "image_file" and isinstance(x, str):
                    o[k] = assets.get(x, x)
                elif k == "note" and ctx == "chart" and isinstance(x, str):
                    o[k] = tstr(x, w)
                elif k in SKIP_KEYS:
                    continue
                elif isinstance(x, str) and k in TEXT_KEYS:
                    o[k] = tstr(x, w)
                elif isinstance(x, list) and k in LIST_KEYS:
                    o[k] = [tstr(i, f"{w}[{n}]") if isinstance(i, str) else i for n, i in enumerate(x)]
                elif isinstance(x, (dict, list)):
                    walk(x, w, anchors, narration, k if k in ("chart", "stat", "doc", "suspect", "casefile", "endscreen") else ctx)
        elif isinstance(o, list):
            for n, it in enumerate(o):
                walk(it, f"{where}[{n}]", anchors, narration, ctx)

    for beat in ep["beats"]:
        bt = (tr.get("beats") or {}).get(beat["id"])
        if not bt or not str(bt.get("text", "")).strip():
            missing.append(f"narration  {beat['id']}: {beat['text']!r}")
            continue
        beat["text"] = bt["text"]
        if bt.get("say"):
            beat["say"] = bt["say"]
        else:
            beat.pop("say", None)
        anchors = bt.get("anchors") or {}
        for dotted, val in (bt.get("patch") or {}).items():  # retiming for the new voice, e.g. "visual.endscreen.times.v1"
            o, keys = beat, dotted.split(".")
            for k in keys[:-1]:
                o = o.setdefault(k, {})
            o[keys[-1]] = val
        vis = beat.get("visual") or {}
        for k in [k for k in beat if k not in ("id", "text", "say", "section", "music", "sting")]:
            if isinstance(beat[k], (dict, list)):
                walk(beat[k], f"{beat['id']}.{k}", anchors, beat["text"])
            elif k in TEXT_KEYS and isinstance(beat[k], str):
                beat[k] = tstr(beat[k], f"{beat['id']}.{k}")
            elif k in ANCHOR_KEYS and isinstance(beat[k], str):
                beat[k] = anchors.get(beat[k], shared_anchors.get(beat[k], beat[k]))
                if not _in_text(beat[k], beat["text"]):
                    missing.append(f"anchor  {beat['id']}.{k}: -> {beat[k]!r} not in the translated narration")
        doc = vis.get("doc") if isinstance(vis.get("doc"), dict) else None
        if doc and doc.get("highlight") and doc["highlight"] not in doc.get("body", ""):
            missing.append(f"highlight  {beat['id']}: {doc['highlight']!r} is not a part of the translated body")
    for k in ("title", "description"):
        if tr.get(k):
            ep[k] = tr[k]
    ep["shorts"] = []  # language versions: long video only
    ep["lang"] = code
    if tr.get("voice"):
        ep["_voice"] = tr["voice"]
    if missing:
        raise ValueError(f"{path}: {len(missing)} untranslated item(s):\n  " + "\n  ".join(missing))
    return ep
