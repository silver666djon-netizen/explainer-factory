"""Documentary layer for case 001 (inserts, stock film). Re-runnable: python episodes/0002-casino-chips/doc_layer.py"""
import json
from pathlib import Path

P = Path(__file__).parent / "script.json"
s = json.loads((Path(__file__).parent / "script.base.json").read_text())  # layer always applied to the base script
by = {b["id"]: b for b in s["beats"]}
LOC = "Library of Congress, Prints & Photographs Division (no known restrictions)"


def ph(file, side, x, y, w, on, caption=None, kind="photo", **kw):
    d = {"file": file, "kind": kind, "from": side, "x": x, "y": y, "w": w, "on": on}
    if caption:
        d["caption"] = caption
    d.update(kw)
    return d


PICKS = {'cash money stack hand': ('hundred dollar bill', 6771234), 'paying cash wallet': (None, 4843535), 'board game money': (None, 1538331), 'poker chips vintage': (None, 9815260), 'empty wallet': (None, 3548021), 'hundred dollar bill': (None, 6771234), 'brain scan mri': (None, 254866), 'exit sign': (None, 1773916), 'casino chips stacks': (None, 875287), 'mobile game smartphone': (None, 1869655), 'gift cards': (None, 421600), 'las vegas night casino': (None, 932708)}


def st(q, side, x, y, w, on, **kw):
    q2, pick = PICKS.get(q, (None, None))
    d = {"stock_photo": q2 or q, "kind": "photo", "from": side, "x": x, "y": y, "w": w, "on": on}
    if pick:
        d["pick"] = pick
    d.update(kw)
    return d


INS = {
    "c03": [st("cash money stack hand", "right", 0.82, 0.4, 0.28, "cash")],
    "c04": [ph("montecarlo_roulette_1900.jpg", "left", 0.2, 0.42, 0.3, "these", "Monte Carlo, c. 1900")],
    "b08": [ph("montecarlo_hall_1896.jpg", "right", 0.82, 0.4, 0.3, "swaps", "Gaming hall, Monte Carlo, 1896")],
    "b12": [st("paying cash wallet", "left", 0.2, 0.42, 0.28, "hurts")],
    "b16": [st("board game money", "right", 0.82, 0.42, 0.28, "Monopoly")],
    "n18": [ph("rowlandson_gaming_1791.jpg", "right", 0.8, 0.42, 0.32, "poker", "A Gaming Table, Thomas Rowlandson, 1791", kind="clipping",
               credit="Thomas Rowlandson, 1791 — The Metropolitan Museum of Art (Open Access, public domain)")],
    "n19": [st("poker chips vintage", "left", 0.2, 0.42, 0.28, "clay")],
    "b17": [ph("lv1940_wheel.jpg", "left", 0.2, 0.42, 0.3, "number", "Wheel of fortune, Las Vegas, 1940")],
    "b23": [st("empty wallet", "right", 0.82, 0.42, 0.26, "gone")],
    "r27": [ph("human_roulette_1908.jpg", "right", 0.84, 0.4, 0.26, "business", "Human roulette wheel, 1908", kind="clipping")],
    "b29": [st("hundred dollar bill", "right", 0.82, 0.4, 0.28, "hundred")],
    "b33": [ph("lv1940_roulette.jpg", "left", 0.18, 0.42, 0.28, "behind", "Roulette, Las Vegas, 1940")],
    "a03": [ph("slot_girl_1938.jpg", "right", 0.84, 0.42, 0.26, "close", "Slot machine, Louisiana, 1938")],
    "a07": [st("brain scan mri", "right", 0.84, 0.42, 0.26, "brain")],
    "a13": [ph("slot_abandoned_1937.jpg", "left", 0.18, 0.42, 0.28, "profitable", "Old slot machine, Michigan, 1937")],
    "e36": [ph("lv1940_mainstreet.jpg", "right", 0.84, 0.42, 0.24, "clocks", "Main street, Las Vegas, 1940")],
    "e40": [ph("dude_slot_1939.jpg", "left", 0.18, 0.42, 0.28, "gamblers", "Slot machine, Montana, 1939")],
    "e43": [st("exit sign", "right", 0.84, 0.4, 0.24, "leaving")],
    "f44": [st("casino chips stacks", "left", 0.18, 0.42, 0.28, "count")],
    "p47": [ph("c02", "left", 0.14, 0.62, 0.26, "phone", kind="cutout")],
    "p48": [st("mobile game smartphone", "right", 0.84, 0.42, 0.26, "game")],
    "p49": [st("gift cards", "left", 0.18, 0.4, 0.26, "Gift")],
    "p51": [st("las vegas night casino", "left", 0.18, 0.42, 0.28, "building")],
    "v54": [ph("c02", "right", 0.86, 0.62, 0.26, "real", kind="cutout")],
    "v55": [ph("lv1940_corner.jpg", "left", 0.18, 0.42, 0.28, "house", "Las Vegas, 1940")],
}
for k, v in INS.items():
    by[k]["inserts"] = v

STOCK = {  # full-frame stock film (keeps the illustration as a fallback)
    "e36": ("casino interior slot machines", 136685, 14),
    "p50": ("contactless payment phone", 202987, 10),
}
for k, (q, pick, out) in STOCK.items():
    v = by[k]["visual"]
    if v.get("type") == "image":
        by[k]["visual"] = {"type": "clip", "stock": q, "pick": pick, "in": 0, "out": out,
                           "fallback_prompt": v.get("prompt") or (v.get("prompts") or [""])[0], "credit": "Stock footage / Pixabay"}

SHORT_INS = {
    ("s1", 1): [st("paying cash wallet", "right", 0.72, 0.45, 0.46, "hurts")],
    ("s1", 4): [ph("montecarlo_roulette_1900.jpg", "left", 0.3, 0.45, 0.48, "chip", "Monte Carlo, c. 1900")],
    ("s3", 3): [st("hundred dollar bill", "right", 0.7, 0.45, 0.46, "hundred")],
    ("s3", 4): [ph("lv1940_roulette.jpg", "left", 0.3, 0.45, 0.48, "more", "Las Vegas, 1940")],
    ("s5", 3): [st("brain scan mri", "right", 0.7, 0.45, 0.46, "brain")],
    ("s6", 2): [ph("slot_abandoned_1937.jpg", "left", 0.3, 0.45, 0.48, "machine", "Slot machine, 1937")],
    ("s7", 2): [st("mobile game smartphone", "right", 0.7, 0.45, 0.46, "gems")],
    ("s7", 3): [st("gift cards", "left", 0.3, 0.45, 0.46, "Gift")],
    ("s8", 0): [ph("lv1940_mainstreet.jpg", "right", 0.72, 0.45, 0.42, "clocks", "Las Vegas, 1940")],
    ("s8", 4): [ph("dude_slot_1939.jpg", "left", 0.3, 0.45, 0.48, "past", "Slot machine, 1939")],
}
for sh in s["shorts"]:
    for i, b in enumerate(sh["beats"]):
        if (sh["id"], i) in SHORT_INS:
            b["inserts"] = SHORT_INS[(sh["id"], i)]
# hand drawing in the Shorts: the phone-casino picture is drawn on screen at the start of s7
s["shorts"][4]["beats"][0]["visual"].update({"motion": "static", "draw": {"at": 0.1, "dur": 2.8, "box": [0.15, 0.0, 0.85, 1.0]}})
# Shorts open with the hand drawing Larry where he is the first picture
s["shorts"][0]["beats"][0]  # (s1 starts on c03 banknotes: stays)

# ============================================================== REVISION BRIEF (round 1 + 2, Oct 2026)
# research cards -> EVIDENCE clippings (<= 6.5 s, the hand underlines/circles the key phrase on the word)
MM = by["d15"]["visual"]["doc"]
HM = by["d20"]["visual"]["doc"]
NM = by["d06"]["visual"]["doc"]
VR = by["d10"]["visual"]["doc"]
by["d14"]["visual"] = {"type": "reuse", "beat": "b12", "index": 1, "motion": "zoom_in"}
by["d15"]["visual"] = {"type": "doc", "doc": {**MM, "highlight": "spent a $50 gift certificate more freely than $50 in cash",
                       "mark": "underline", "on": "certificate", "pre": "c03"}}
by["d19"]["visual"] = {"type": "reuse", "beat": "b18", "motion": "zoom_in"}
by["d20"]["visual"] = {"type": "doc", "doc": {**HM, "highlight": "as if the winnings were not really their own", "mark": "underline",
                       "on": "winnings", "pre": "b18", "post": "b17"}}
by["d34"]["visual"] = {"type": "doc", "doc": {**HM, "highlight": "bets that offered a chance to break even became especially attractive",
                       "mark": "underline", "flash": True, "post": "b33"}}
by["d05"]["visual"] = {"type": "reuse", "beat": "a07", "motion": "zoom_in"}
by["d06"]["visual"] = {"type": "doc", "doc": {**NM, "highlight": "increased the desire to keep playing", "mark": "circle", "on": "keep", "pre": "a03"}}
by["d09"]["visual"] = {"type": "reuse", "beat": "a13", "motion": "zoom_in"}
by["d10"]["visual"] = {"type": "doc", "doc": {**VR, "highlight": "mapped onto a hidden 64-stop virtual reel", "mark": "underline", "on": "hidden", "pre": "a08"}}
for k in ("d15", "d20", "d34", "d06", "d10"):
    by[k]["visual"]["doc"].pop("at", None)
FTC_Q = ("For instance, if a hypothetical customer who visits a sports betting website demonstrates hesitation by lingering on the "
         "homepage longer than expected or moves their cursor towards the button to close out their browser tab, the website may "
         "trigger a pop-up showing popular sporting events to incentivize the visitor to remain on the website and place a bet.")
by["p51b"]["visual"] = {"type": "doc", "doc": {"source": "FTC staff report · Jan 2025", "kicker": "STAFF REPORT  ·  QUOTED, P. 6",
                        "headline": "Targeting Reluctant Gamblers", "body": FTC_Q,
                        "highlight": "the website may trigger a pop-up showing popular sporting events", "mark": "underline",
                        "on": "pops", "pre": "p51", "seed": 505}}
s["sources"].append("US Federal Trade Commission staff (Jan 2025). Surveillance Pricing 6(b) study: research summaries, p. 6 (quoted).")

# naming: the chip is SUSPECT No. 1 everywhere
for m in by["b10"]["visual"].get("marks") or []:
    if m.get("text"):
        m["text"] = "suspect no. 1"

# House Edge: 1950s infographic on green felt, two chip stacks drawn by the hands, numbers written on the words
HE = {"title": "House edge", "sub": "what the house keeps from every $100 bet",
      "bars": [{"name": "American wheel", "note": "0 and 00", "value": 5.26, "color": "red"},
               {"name": "European wheel", "note": "single 0", "value": 2.70, "color": "ink"}],
      "draw_at": [0.25, 1.5], "draw_dur": 1.8}
by["s28"]["visual"] = {"type": "houseedge", "houseedge": {**HE, "write_on": ["five", None]}}
by["k32"]["visual"] = {"type": "houseedge", "houseedge": {**HE, "predrawn": True, "prewritten": [True, False], "write_on": [None, "two"]}}

# pauses: every chapter title gets a musical hit + 1 s before the line; key numbers land in silence, then a hit
for t in ("t01", "t02", "t03", "t04", "t05", "t06"):
    by[t].update({"pause_before": 1.0, "sting": "ub_sting_trumpet", "sting_at": -1.0})
by["s28"]["pause_at"] = {"word": "five", "sec": 1.2, "hit": "stamp"}
by["b23"]["pause_at"] = {"word": "So is a chunk", "sec": 1.0, "hit": "hit"}
by["a04"]["pause_at"] = {"word": "It's a loss", "sec": 1.2, "hit": "stamp"}
by["a11"]["pause_at"] = {"word": "four", "sec": 1.2, "hit": "stamp"}
by["a11"]["counter"]["on"] = "four"
by["a11"]["counter"].pop("at", None)
by["v54"]["pause_at"] = {"word": "how many", "sec": 1.3, "hit": "stamp"}

# Larry's tab (top-right ledger); inserts that came in from the right now come from the left
for k in ("b08", "b23", "e43"):
    for ins in by[k].get("inserts") or []:
        ins.update({"from": "left", "x": 0.18})
by["b08"]["ledger"] = [{"label": "CASH IN", "amount": "$500", "on": "five"}, {"label": "CHIPS", "amount": "500", "on": "stack"}]
by["b18"]["ledger"] = [{"label": "WIN", "amount": "+100", "on": "files"}]
by["b23"]["ledger"] = [{"label": "TILT BET", "amount": "-360", "loss": True, "on": "chunk"}]
by["b35"]["ledger"] = [{"label": "house keeps 5.26% of every bet", "note": True, "on": "arithmetic"}]
by["a04"]["ledger"] = [{"label": "SLOTS", "amount": "-240", "loss": True, "on": "ordinary"}]
by["e43"]["ledger"] = [{"label": "HOME", "amount": "$0", "loss": True, "circle": True, "on": "leaving"}]

# foley pass: every on-screen action gets a sound
SFX = {"c04": [("these", "chips")], "b08": [("plastic", "chips")], "b13": [("clicks", "chips")], "b17": [("profit", "cash")],
       "b21": [("pushed", "chips")], "b35": [("bigger", "chips")], "f44": [("stack", "chips")], "r24b": [("wheel", "whirr")],
       "n19": [("clay", "chips")], "b29": [("hundred", "cash")], "p48": [("gems", "chips")]}
for k, evs in SFX.items():
    by[k]["sfx_at"] = [{"on": w, "kind": kd} for w, kd in evs]

# live action as evidence
by["e36"]["visual"]["exhibit"] = {"label": "Evidence · slot floor · present day · reconstruction", "tag": "Slot floor · 2020s"}
by["p50"]["visual"]["exhibit"] = {"label": "Evidence · tap to pay · present day · reconstruction", "tag": "Tap to pay · 2020s"}
by["e36"].pop("sfx", None)  # no projector clatter on modern footage
for ins in by["e36"].get("inserts") or []:  # then-vs-now photo comes in from the left, clear of the EXHIBIT tag
    ins.update({"from": "left", "x": 0.15, "y": 0.40, "w": 0.22})

# CASE CLOSED: the stamped folder only (the verdict is written once, at the end), with the stamp hit
cf = by["v52"]["visual"]["casefile"]
cf.pop("lines", None)
cf["stamp_at"] = -0.9
by["v52"].update({"pause_before": 1.0, "sting": "ub_sting_brass", "sting_at": -1.0})

# 20 s end sequence replaces k2 + k3
ES = {"number": "001", "title": "The casino", "stamp": "Case closed",
      "verdict": ["Guilty: your brain.", "Accomplice: plastic."],
      "next": {"number": "002", "title": "Same basket", "tagline": "Same basket. Different price.",
               "image_file": "next_basket.png", "copies": 2, "prices": ["$114.34", "$123.93"]}}
end = [
    {"id": "e1", "section": "Case closed", "text": "Case closed. Guilty: your brain. Accomplice: plastic.", "block_start": True,
     "visual": {"type": "endscreen", "endscreen": ES}},
    {"id": "e2", "section": "Case closed", "text": "Next case: same basket, same shop — two different prices.", "block_at": 7.0,
     "visual": {"type": "continue"}},
    {"id": "e3", "section": "Case closed", "text": "Subscribe, so the next case file finds you. And your next case is right here.",
     "block_at": 14.8, "block_end": 20.0, "visual": {"type": "continue"}},
]
s["beats"] = [b for b in s["beats"] if b["id"] not in ("k2", "k3")] + end
by = {b["id"]: b for b in s["beats"]}

# music: one Uppbeat track per chapter (round-2 selection 1C 2A 3B 4A 5C 6A 7B 8C)
s["music"] = {"_default": "ub_private_detective", "_shorts": "ub_wells_street",
              "The case": "ub_private_detective", "7 PM: The exchange": "ub_wells_street", "9 PM: The win": "ub_wells_street",
              "11 PM: The maths": "ub_clock_is_ticking", "1 AM: Almost": "ub_mechanisms_of_action",
              "2 AM: The building": "ub_tunnel_vision", "In defence of the accused": "ub_usual_suspects",
              "The twist: your phone": "ub_secret_report", "Case closed": "ub_jazz_rumble"}

# ---------------------------------------------------------------- 7 Shorts re-cut from the fixed master
import copy as _copy
LONG = {b["id"]: b for b in s["beats"]}


def L(bid, text=None, visual=None, keep=("punch", "on_screen", "counter", "pause_at", "sfx_at", "sfx", "say"), **kw):
    """A Short beat taken from the long video: same narration (unless given), same picture."""
    src = LONG[bid]
    v = src["visual"]
    if visual is None:
        if v["type"] in ("image", "archive", "clip"):
            visual = {"type": "reuse", "beat": bid, "motion": "zoom_in"}
            if v.get("exhibit"):
                visual["exhibit"] = _copy.deepcopy(v["exhibit"])
        elif v["type"] == "reuse":
            visual = {k: v[k] for k in ("type", "beat", "index") if k in v}
        else:
            visual = _copy.deepcopy(v)
    b = {"text": text or src["text"], "visual": visual}
    if text is None:
        for k in keep:
            if k in src:
                b[k] = _copy.deepcopy(src[k])
    b.update(kw)
    return b


HE_DONE = {**HE, "predrawn": True, "prewritten": [True, False], "write_on": [None, None]}
s["shorts"] = [
    {"id": "s1", "title": "A chip has no pain #shorts", "hook": "A chip has no pain",
     "beats": [L("b13", sfx_at=[{"on": "clicks", "kind": "chips"}]), L("b12"),
               L("d15", visual=_copy.deepcopy(by["d15"]["visual"])),
               L("b08", text="So the casino swaps your cash for something that doesn't hurt.")]},
    {"id": "s2", "title": "5.26% is the whole business model #shorts", "hook": "5.26%",
     "beats": [L("s28", text="Five point two six percent. That's the casino's entire business model.",
                 visual={"type": "houseedge", "houseedge": {**HE, "predrawn": True, "prewritten": [True, False], "write_on": [None, None]}}),
               L("r25"), L("r26"), L("r27"), L("b29"), L("b30"), L("b31"),
               L("b33", text="And it all comes down to one number.")]},
    {"id": "s3", "title": "A near miss is a loss #shorts", "hook": "So close…",
     "beats": [L("a03", keep=("pause_at",)), L("a02"), L("a04"),
               L("d06", visual=_copy.deepcopy(by["d06"]["visual"])), L("a07", keep=("on_screen",)),
               L("h12", text="And Larry? He's sure the next one is a win.")]},
    {"id": "s4", "title": "No clocks, no windows? The real casino trick #shorts", "hook": "The no-clock myth",
     "beats": [L("e36", visual={"type": "reuse", "beat": "e39", "motion": "zoom_in"}), L("e38"), L("e39", visual={"type": "reuse", "beat": "e38"}),
               L("e40", keep=()), L("e41"), L("e42"), L("e43", keep=()),
               L("e37", text="So the next time someone tells you there are no clocks in casinos…", visual={"type": "reuse", "beat": "e36"})]},
    {"id": "s5", "title": "Your phone is a casino chip #shorts", "hook": "Your phone is a chip",
     "beats": [L("p51", text="Your phone is a casino chip."), L("p48"), L("p49"), L("p50", keep=("sfx",)),
               L("p51b", visual=_copy.deepcopy(by["p51b"]["visual"])),
               L("p47", text="Take a look at your screen.", keep=())]},
    {"id": "s6", "title": "One question before you tap #shorts", "hook": "How many real dollars?",
     "beats": [L("v54", text="How many real dollars is this?", visual={"type": "reuse", "beat": "c04", "motion": "zoom_in"}),
               L("v54", keep=("sfx_at",)), L("v55"),
               L("h09", text="So before you tap, ask yourself.")]},
    {"id": "s7", "title": "Larry's tab: $500 to $0 in one night #shorts", "hook": "$500 → $0",
     "beats": [L("c02", text="Tonight, Larry walks into a casino with five hundred dollars.", keep=(),
                 ledger=[{"label": "CASH IN", "amount": "$500", "on": "five"}]),
               L("b08", text="He swaps it for a neat little stack of plastic.", ledger=[{"label": "CHIPS", "amount": "500", "on": "stack"}]),
               L("b17", text="His number comes up. One hundred dollars, profit.", keep=(), ledger=[{"label": "WIN", "amount": "+100", "on": "hundred"}]),
               L("b23", text="Then he bets bigger to win it back. Gone.", ledger=[{"label": "TILT BET", "amount": "-360", "loss": True, "on": "Gone"}]),
               L("a03", text="The slots take the rest.", keep=(), ledger=[{"label": "SLOTS", "amount": "-240", "loss": True, "on": "rest"}]),
               L("b31", text="He goes home with nothing.", ledger=[{"label": "HOME", "amount": "$0", "loss": True, "circle": True, "on": "nothing"}]),
               L("h09", text="Tomorrow night? He'll be back.")]},
]

P.write_text(json.dumps(s, indent=2, ensure_ascii=False) + "\n")
print("ok", len(INS), "long inserts,", len(SHORT_INS), "short inserts,", len(STOCK), "stock films")
