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
    "c04": [ph("montecarlo_roulette_1900.jpg", "left", 0.2, 0.42, 0.3, "these", "Monte Carlo, c. 1900")],
    "b08": [ph("montecarlo_hall_1896.jpg", "right", 0.82, 0.4, 0.3, "swaps", "Gaming hall, Monte Carlo, 1896")],
    "n18": [ph("rowlandson_gaming_1791.jpg", "right", 0.8, 0.42, 0.32, "poker", "A Gaming Table, Thomas Rowlandson, 1791", kind="clipping",
               credit="Thomas Rowlandson, 1791 — The Metropolitan Museum of Art (Open Access, public domain)")],
    "b17": [ph("lv1940_wheel.jpg", "left", 0.2, 0.42, 0.3, "number", "Wheel of fortune, Las Vegas, 1940")],
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
    ("s1", 4): [ph("montecarlo_roulette_1900.jpg", "left", 0.3, 0.45, 0.48, "chip", "Monte Carlo, c. 1900")],
    ("s3", 4): [ph("lv1940_roulette.jpg", "left", 0.3, 0.45, 0.48, "more", "Las Vegas, 1940")],
    ("s6", 2): [ph("slot_abandoned_1937.jpg", "left", 0.3, 0.45, 0.48, "machine", "Slot machine, 1937")],
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

P.write_text(json.dumps(s, indent=2, ensure_ascii=False) + "\n")
print("ok", len(INS), "long inserts,", len(SHORT_INS), "short inserts,", len(STOCK), "stock films")
