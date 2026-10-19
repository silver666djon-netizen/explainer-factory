"""Case 002 revision (Oct 2026 brief): new cold open, battery rumour moved after the evidence and cut to ~50 s,
case-file format restored (verdict, In defence, Larry's Tab), real numbers on blank labels, EVIDENCE cards,
EXHIBIT frames, basket infographic, 20 s end screen, chapter music, 7 re-cut Shorts.
Run: python episodes/0003-same-basket/gen_script.py && python episodes/0003-same-basket/rev_layer.py"""
import copy
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
s = json.loads((HERE / "script.base.json").read_text())
B = {b["id"]: b for b in s["beats"]}


def font(name, size):
    for p in (ROOT / "assets" / "fonts" / name, Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")):
        if p.exists():
            return ImageFont.truetype(str(p), size)


# ---------------------------------------------------------------- the Ep.3 teaser subject: a shop tag with a "WAS" price
def make_tag(path):
    W, H = 1376, 768
    im = Image.new("RGB", (W, H), (243, 233, 210))
    d = ImageDraw.Draw(im)
    x0, y0, x1, y1 = 330, 150, 1050, 640
    c = 120
    poly = [(x0 + c, y0), (x1, y0), (x1, y1), (x0 + c, y1), (x0, y1 - c), (x0, y0 + c)]
    d.polygon(poly, fill=(252, 247, 233))
    d.line(poly + [poly[0]], fill=(30, 27, 24), width=10)
    d.line([(x0 + 26, y0 + 26 + c - 26)], fill=(30, 27, 24))
    d.rectangle((x0 + 160, y0 + 40, x1 - 40, y1 - 40), outline=(210, 69, 47), width=12)
    d.ellipse((x0 + 50, (y0 + y1) // 2 - 30, x0 + 110, (y0 + y1) // 2 + 30), outline=(30, 27, 24), width=9)
    d.line((x0 + 80, (y0 + y1) // 2 - 30, x0 - 160, y0 - 120), fill=(30, 27, 24), width=8)
    f1 = font("Anton-Regular.ttf", 120)
    f2 = font("Anton-Regular.ttf", 210)
    d.text(((x0 + 160 + x1 - 40) / 2, y0 + 130), "WAS $6.69", font=f1, fill=(30, 27, 24), anchor="mm")
    d.text(((x0 + 160 + x1 - 40) / 2, y0 + 340), "SALE", font=f2, fill=(210, 69, 47), anchor="mm")
    im.save(path)


make_tag(HERE / "next_tag.png")

S_OPEN, S_BASKET, S_BATT, S_LOT, S_MACH, S_DEF, S_TWIST, S_CLOSE = (
    "The case", "10:15 AM: Same basket", "11:47 PM: 3% battery", "8:02 AM: The parking lot",
    "1:30 PM: The machine", "In defence of the accused", "The twist", "Case closed")

ITEMS = [("WHOLE MILK 1 GAL", 4.9), ("EGGS LARGE x12", 5.6), ("SOURDOUGH LOAF", 6.5), ("COFFEE 12 OZ", 11.9), ("CHEDDAR 8 OZ", 5.4),
         ("BANANAS 2 LB", 1.6), ("CHICKEN THIGHS", 11.8), ("OLIVE OIL 500ML", 12.5), ("CEREAL", 6.2), ("PASTA x3", 5.7),
         ("APPLES 3 LB", 6.4), ("BUTTER", 5.9), ("TOMATOES", 4.8), ("SALMON FILLET", 19.0)]


def items_for(total, seed, scale=1.0):
    import numpy as np
    rnd = np.random.default_rng(seed)
    raw = np.array([p * scale * rnd.uniform(0.97, 1.03) for _n, p in ITEMS])
    raw = raw / raw.sum() * total
    cents = np.round(raw * 100).astype(int)
    cents[-1] += int(round(total * 100)) - cents.sum()
    return [[n, f"{c / 100:.2f}"] for (n, _p), c in zip(ITEMS, cents)]


RECEIPTS = {"store": "SAME STORE · SEATTLE", "when": "10:15 AM", "stamp": "Real totals",
            "receipts": [{"name": "LARRY", "total": "$123.93", "items": items_for(123.93, 2, 1.05)},
                         {"name": "LINDA", "total": "$114.34", "items": items_for(114.34, 3)}]}


def nb(id, section, text, visual, **kw):
    b = {"id": id, "section": section, "text": text, "visual": visual}
    b.update(kw)
    return b


def doc(source, headline, body, highlight, on, mark="underline", kicker=None, seed=1, pre=None, post=None, **kw):
    d = {"source": source, "headline": headline, "body": body, "highlight": highlight, "on": on, "mark": mark, "seed": seed}
    if kicker:
        d["kicker"] = kicker
    if pre:
        d["pre"] = pre
    if post:
        d["post"] = post
    d.update(kw)
    return {"type": "doc", "doc": d}


def write(text, x, y, w, h, on=None, angle=0, color="red", fnt="marker", **kw):
    m = {"type": "write", "text": text, "x": x, "y": y, "w": w, "h": h, "angle": angle, "color": color, "font": fnt, "on": on, "dur": 0.7}
    m.update(kw)
    if m.get("on") is None:
        m.pop("on")
    if m.get("at") == 0.0 and "on" not in m:  # already there when the shot starts: no pen, no reveal
        m.update({"hand": False, "dur": 0.01})
    return m


def title_beat(b):
    b.update({"pause_before": 1.0, "sting": "ub_sting_trumpet", "sting_at": -1.0})
    return b


# ---------------------------------------------------------------- cold open (first 12 s)
cold = [
    nb("o1", S_OPEN, "Same store. Same basket. Same minute.",
       {"type": "split", "split": {"left": "s30", "right": "s30.1", "names": ["LARRY", "LINDA"], "clock": "10:15", "clock_sub": "SAME MINUTE",
                                "light_on": "store", "tap_on": "basket", "stamp_on": "minute",
                                "screens": [{"quad": [[0.3436, 0.627], [0.3855, 0.630], [0.4364, 0.7734], [0.3927, 0.786]], "mode": "dark"},
                                            {"quad": [[0.630, 0.640], [0.667, 0.638], [0.643, 0.702], [0.599, 0.751]], "mode": "light"}]}},
       sfx_at=[{"on": "Same", "kind": "tap"}, {"on": "minute", "kind": "tap"}]),
    nb("o2", S_OPEN, "Two prices. Larry is made up. His receipt is not.",
       {"type": "receipts", "receipts": {**RECEIPTS, "circle_on": "Two", "stamp_on": "receipt"}}),
    nb("cf1", S_OPEN, "Case file number two. Same basket, different price.",
       {"type": "casefile", "casefile": {"mode": "open", "number": "002", "title": "Same basket", "typed": False, "open_stamp_on": "price",
                                          "inside": ["SUBJECT: Larry (fictional)", "WITNESS: Linda, his sister", "SUSPECTS: 2", "STATUS: open"]}}),
]

# ---------------------------------------------------------------- 10:15 AM — the evidence first
basket = []
t03 = title_beat(copy.deepcopy(B["t03"]))
basket.append(t03)
s30 = copy.deepcopy(B["s30"])
s30["sfx_at"] = [{"on": "orders", "kind": "tap"}, {"on": "exact", "kind": "tap"}]
basket.append(s30)
s31 = copy.deepcopy(B["s31"])
s31["text"] = "Then they compare receipts."
s31["bubble"]["at"] = 0.6
s31["sfx_at"] = [{"on": "receipts", "kind": "printer"}]
basket.append(s31)
s32 = copy.deepcopy(B["s32"])
s32.pop("inserts", None)
CR = B["s32"]["visual"]["doc"]
s32["visual"] = doc(CR["source"], CR["headline"], CR["body"], "offered at different prices", on="same basket", seed=41, pre="s30")
basket.append(s32)
s33 = copy.deepcopy(B["s33"])
s33["visual"] = {"type": "baskets", "baskets": {"image": "d53", "title": "Same Safeway basket · Seattle",
                                                 "sub": "cheapest vs most expensive total · same store, same minute",
                                                 "labels": ["Cheapest basket", "Most expensive"], "values": [114.34, 123.93],
                                                 "write_on": ["114", "123"], "gap": "+$9.59"}}
s33["pause_at"] = {"word": "114", "sec": 1.2, "hit": "stamp"}
basket.append(s33)
s33b = copy.deepcopy(B["s33b"])
s33b["ledger"] = [{"label": "LARRY", "amount": "$123.93", "on": "Nearly"},
                  {"label": "LINDA", "amount": "$114.34", "on": "ordinary"},
                  {"label": "DIFFERENCE", "amount": "-$9.59", "loss": True, "on": "luck"}]
s33b["sfx_at"] = [{"on": "grocery", "kind": "cart"}]
basket.append(s33b)
s34 = copy.deepcopy(B["s34"])
s34["pause_at"] = {"word": "eight", "sec": 1.2, "hit": "stamp"}
basket.append(s34)
basket.append(copy.deepcopy(B["s35"]))
s36 = copy.deepcopy(B["s36"])
s36["ledger"] = [{"label": "up to 23% per item", "note": True, "on": "five"}]
basket.append(s36)
# crackers: the ribbon shows the real "was" prices as they're spoken, then the marker writes the sale price
RIB = dict(x=0.52, y=0.505, w=0.27, h=0.10, angle=10, color="paper", fnt="headline")
s37 = copy.deepcopy(B["s37"])
s37.pop("on_screen", None)
s37["visual"].update({"motion": "static", "marks": [
    write("WAS $5.93", on="five ninety-three", until_on="five ninety-nine", **RIB),
    write("WAS $5.99", on="five ninety-nine", until_on="six", **RIB),
    write("WAS $6.69", on="six", **RIB)]})
basket.append(s37)
s38 = copy.deepcopy(B["s38"])
s38["visual"] = {"type": "reuse", "beat": "s37", "index": 0, "motion": "static", "hand_marks": True,
                 "marks": [write("WAS $6.69", at=0.0, until_on="three", **RIB),
                           write("EVERYONE: $3.99", on="three", x=0.52, y=0.505, w=0.30, h=0.11, angle=10, color="paper"),
                           {"type": "circle", "x": 0.5, "y": 0.5, "w": 0.6, "h": 0.74, "on": "sale"}]}
basket.append(s38)
basket.append(copy.deepcopy(B["s39"]))
s39b = copy.deepcopy(B["s39b"])
s39b["visual"] = {"type": "kinetic", "kinetic": {"bg": "paper"}, "text": "The bigger the fake 'was', the better the deal felt. Economists call it *anchoring.*"}
basket.append(s39b)
basket.append(copy.deepcopy(B["s39c"]))
s3a = copy.deepcopy(B["s3a"])
basket.append(s3a)
s3b = copy.deepcopy(B["s3b"])
s3b.pop("counter", None)
s3b["pause_at"] = {"word": "twelve", "sec": 1.2, "hit": "stamp"}
s3b["ledger"] = [{"label": "PER YEAR (CR est.)", "amount": "-$1,200", "loss": True, "circle": True, "on": "twelve"}]
s3b.pop("inserts", None)
basket.append(s3b)
basket.append(copy.deepcopy(B["s3c"]))

# ---------------------------------------------------------------- 11:47 PM — Suspect No. 1, alibi confirmed (~50 s)
batt = [title_beat(copy.deepcopy(B["t01"]))]
b11 = copy.deepcopy(B["b11"])
b11["text"] = "Larry opens a ride app. The fare looks high. Is it the rain? The hour? Or the battery?"
b11["visual"] = {"type": "battery", "battery": {"fare": "$24.80", "tag_label": "RIDE FARE", "from": 0.42, "to": 0.03, "dur": 3.6,
                                                 "drain_on": "opens", "note": "same fare"}}
b11.pop("punch", None)
b11["sfx_at"] = [{"on": "opens", "kind": "tap"}]
batt.append(b11)
batt.append(copy.deepcopy(B["m12"]))
d13 = copy.deepcopy(B["d13"])
NPR = B["d13"]["visual"]["doc"]
d13["visual"] = doc(NPR["source"], NPR["headline"], NPR["body"], "more willing to accept surge pricing", on="willing", seed=31, pre="w60")
batt.append(d13)
d14 = copy.deepcopy(B["d14"])
d14["visual"] = {"type": "reuse", "beat": "m12", "motion": "zoom_in"}
batt.append(d14)
b15 = copy.deepcopy(B["b15"])
b15["visual"] = {"type": "reuse", "beat": "m12", "motion": "static"}
b15["text"] = "Verdict: not proven."
b15["stamp"] = {"text": "Not proven", "on": "not"}
b15.pop("sfx", None)
batt.append(b15)
batt.append(copy.deepcopy(B["b16"]))
batt.append(copy.deepcopy(B["b17"]))

# ---------------------------------------------------------------- 8:02 AM — Exhibit A
lot = [title_beat(copy.deepcopy(B["t02"]))]
lot.append(copy.deepcopy(B["a20"]))
a21 = copy.deepcopy(B["a21"])
a21.pop("on_screen", None)
a21["visual"].update({"motion": "static", "hand_marks": True, "marks": [
    {"type": "circle", "x": 0.465, "y": 0.43, "w": 0.30, "h": 0.42, "on": "TV"},
    write("$499.99", on="499", x=0.465, y=0.43, w=0.19, h=0.11)]})
lot.append(a21)
a22 = copy.deepcopy(B["a22"])
a22["visual"]["exhibit"] = {"label": "Evidence · store parking lot · present day · reconstruction", "tag": "Parking lot · 2020s"}
lot.append(a22)
for k in ("a23", "a24", "a25", "a26"):
    lot.append(copy.deepcopy(B[k]))
lot[-4]["inserts"] = [{"file": "grocery_sign_painter_1937.jpg", "kind": "photo", "from": "right", "x": 0.80, "y": 0.55, "w": 0.30,
                       "on": "switched", "crop": [0.09, 0.03, 0.97, 0.96], "caption": "Painting the prices on a grocery window, 1937"}]  # a23
k1 = copy.deepcopy(B["k1"])
k1["visual"] = {"type": "reuse", "beat": "s30", "index": 0, "motion": "zoom_in"}
lot.append(k1)

# ---------------------------------------------------------------- 1:30 PM — the machine
mach = [title_beat(copy.deepcopy(B["t04"]))]
mach.append(copy.deepcopy(B["h40"]))
mach.append(copy.deepcopy(B["h41a"]))
h41 = copy.deepcopy(B["h41"])
h41["visual"]["motion"] = "static"
h41["visual"]["hand_marks"] = True
h41["visual"]["marks"] = [write("$1.25", on="written", x=0.605, y=0.665, w=0.09, h=0.07, angle=-28, color="ink")]
h41["visual"].pop("ad", None)
mach.append(h41)
h42 = copy.deepcopy(B["h42"])
h42["visual"]["marks"] = [write("$1.25", at=0.0, x=0.605, y=0.665, w=0.09, h=0.07, angle=-28, color="ink")] + h42["visual"]["marks"]
h42["inserts"] = [{"file": "sears_catalogue_pietown_1940.jpg", "kind": "photo", "from": "left", "x": 0.21, "y": 0.45, "w": 0.30,
                   "on": "rich", "crop": [0.04, 0.04, 0.96, 0.93], "caption": "Ordering from the Sears catalogue, 1940"}]
mach.append(h42)
h43 = copy.deepcopy(B["h43"])
h43["visual"] = {"type": "archive", "file": "grocery_prices_savannah_1939.jpg", "look": "print", "motion": "zoom_in",
                 "credit": "Library of Congress, Prints & Photographs Division (no known restrictions)",
                 "caption": "Prices chalked outside a grocery, Savannah, 1939"}
mach.append(h43)
mach.append(copy.deepcopy(B["h43b"]))
p40 = copy.deepcopy(B["p40"])
p40["visual"]["draw"]["on"] = "who"
p40["sfx_at"] = [{"on": "Meet", "kind": "servo"}, {"on": "Price", "kind": "servo"}]
mach.append(p40)
p41 = copy.deepcopy(B["p41"])
p41["inserts"] = [{"file": "s30", "kind": "cutout", "from": "left", "x": 0.14, "y": 0.62, "w": 0.24, "on": "Shopping"}]
p41["sfx_at"] = [{"on": "Good", "kind": "servo"}]
mach.append(p41)
FTC_Q = ("There are a number of variables that can impact what products a consumer is shown or what prices (including promotions "
         "or discounts) a consumer might be offered. These include where the consumer is, who the consumer is, what the consumer is "
         "doing, and prior actions a consumer has taken.")
p42 = copy.deepcopy(B["p42"])
p42["visual"] = doc("FTC staff report · Jan 2025", "Surveillance pricing", FTC_Q,
                    "where the consumer is, who the consumer is, what the consumer is doing", on="personalise",
                    kicker="STAFF REPORT  ·  QUOTED, P. 6", seed=51, pre="p40", lead=1.2)
mach.append(p42)
p42b = copy.deepcopy(B["p42b"])
p42b["visual"] = {"type": "continue"}
mach.append(p42b)
for k in ("p43", "p44", "p45", "p46"):
    mach.append(copy.deepcopy(B[k]))

# ---------------------------------------------------------------- In defence of the accused (~20 s)
dfn = [title_beat(copy.deepcopy(B["t05"]))]
d50 = copy.deepcopy(B["d50"])
d50.pop("inserts", None)
dfn.append(d50)
d51 = copy.deepcopy(B["d51"])
d51["inserts"] = [{"file": "register_babbitt_1937.jpg", "kind": "photo", "from": "right", "x": 0.85, "y": 0.80, "w": 0.24,
                   "on": "always", "crop": [0.11, 0.05, 0.97, 0.90], "caption": "Store counter and cash register, 1937"}]
dfn.append(d51)
d52 = copy.deepcopy(B["d52"])
d52["visual"] = doc("Instacart statement · Dec 2025 · as reported", "Random test groups",
                    "Instacart said shoppers were put into test groups at random, by product and location, and not by personal or demographic data.",
                    "at random", on="random", mark="circle", kicker="COMPANY STATEMENT  ·  PARAPHRASED", seed=71, pre="p40")
dfn.append(d52)
dfn.append(copy.deepcopy(B["d53"]))

# ---------------------------------------------------------------- the twist
tw = [title_beat(copy.deepcopy(B["t06"]))]
tw.append(copy.deepcopy(B["w60"]))
tw.append(copy.deepcopy(B["w61"]))
w61b = copy.deepcopy(B["w61b"])
SIGN = dict(w=0.26, h=0.12, color="paper", fnt="headline")
w61b["visual"]["marks"] = [
    {"type": "circle", "x": 0.27, "y": 0.7, "w": 0.4, "h": 0.5, "on": "Group"},
    write("GROUP A · $4.19", on="Group", x=0.27, y=0.22, **SIGN),
    {"type": "circle", "x": 0.74, "y": 0.7, "w": 0.4, "h": 0.5, "on": "B"},
    write("GROUP B · $4.79", on="B", x=0.73, y=0.22, **SIGN)]
w61b["ledger_hide"] = True  # the tab would cover the GROUP B sign
w61b["label"] = "Illustration"  # the A/B prices are illustrative, not from the study
tw.append(w61b)
w62 = copy.deepcopy(B["w62"])
w62["sfx_at"] = [{"on": "running", "kind": "cart"}]
tw.append(w62)
w63 = copy.deepcopy(B["w63"])
IM = B["w63"]["visual"]["doc"]
w63["visual"] = doc(IM["source"], IM["headline"], IM["body"], IM["highlight"], on="aware", kicker="COMPANY MATERIAL  ·  QUOTED", seed=61, pre="w62")
tw.append(w63)
w64 = copy.deepcopy(B["w64"])
w64["pause_before"] = 1.2
w64["sfx"] = "stamp"
tw.append(w64)

# ---------------------------------------------------------------- case closed (verdict stamped once, written in the end screen)
close = []
v70 = copy.deepcopy(B["v70"])
cf = v70["visual"]["casefile"]
cf.pop("lines", None)
cf["stamp_at"] = -0.9
v70.update({"pause_before": 1.0, "sting": "ub_sting_brass", "sting_at": -1.0, "hold": 0.8})
close.append(v70)
v71 = copy.deepcopy(B["v71"])
v71["visual"] = {"type": "kinetic", "kinetic": {"bg": "ink"}, "text": "And the *ten-second* defence."}
v71["music"] = "ub_secret_report"
close.append(v71)
for k in ("v72", "v73", "v74b", "v75", "v76"):
    b = copy.deepcopy(B[k])
    b["music"] = "ub_secret_report"
    if k == "v73":
        b["visual"]["marks"] = [{"type": "cross", "x": 0.47, "y": 0.17, "w": 0.22, "h": 0.36, "on": "off"}]
        b["visual"]["hand_marks"] = True
    if k == "v74b":
        b["visual"]["marks"] = [write("$1.25", at=0.0, x=0.605, y=0.665, w=0.09, h=0.07, angle=-28, color="ink")] + b["visual"]["marks"]
    close.append(b)
close[-3]["inserts"] = [{"file": "supermarket_1957_a.jpg", "kind": "photo", "from": "right", "x": 0.82, "y": 0.42, "w": 0.3, "on": "fact.",
                         "caption": "Shopping in a supermarket, 1957"}]
close[-2].pop("inserts", None)  # v75: no archive photo over Larry's selfie gag
close[-1]["visual"]["marks"] = [write("WAS $6.69", at=0.0, x=0.52, y=0.505, w=0.27, h=0.10, angle=10, color="paper", fnt="headline", on=None),
                                {"type": "circle", "x": 0.48, "y": 0.5, "w": 0.6, "h": 0.74, "on": "own"}]
ES = {"number": "002", "title": "Same basket", "stamp": "Case closed",
      "verdict": ["Guilty: the algorithm.", "Accomplice: your location."],
      "next": {"number": "003", "title": "The fake sale", "tagline": "The sale that never was.", "image_file": "next_tag.png",
               "copies": 1, "prices": ["$3.99"], "strike": [0.40, 0.40, 0.88, 0.37]}}
end = [
    nb("e1", S_CLOSE, "Case closed. Guilty: the algorithm. Accomplice: your location.", {"type": "endscreen", "endscreen": ES},
       block_start=True, sting="ub_sting_brass", sting_at=0.1),
    nb("e2", S_CLOSE, "Next case: the sale that never was.", {"type": "continue"}, block_at=7.0),
    nb("e3", S_CLOSE, "Subscribe, so the next case file finds you. And your next case is right here.", {"type": "continue"},
       block_at=14.3, block_end=20.0),
]

# sections follow the new order
for b in basket:
    b["section"] = S_BASKET
for b in batt:
    b["section"] = S_BATT
s["beats"] = cold + basket + batt + lot + mach + dfn + tw + close + end
by = {b["id"]: b for b in s["beats"]}

# write-mark timing helper: "until_on" ends a mark when another word is spoken (resolved at render via 'on')
for b in s["beats"]:
    for m in (b["visual"].get("marks") or []):
        if m.get("on") is None:
            m.pop("on", None)

s["music"] = {"_default": "ub_private_detective", "_shorts": "ub_wells_street",
              S_OPEN: "ub_private_detective", S_BASKET: "ub_wells_street", S_BATT: "ub_mechanisms_of_action",
              S_LOT: "ub_tunnel_vision", S_MACH: "ub_clock_is_ticking", S_DEF: "ub_usual_suspects",
              S_TWIST: "ub_clock_is_ticking", S_CLOSE: "ub_jazz_rumble"}
s["sources"] = [x for x in s["sources"] if "Larry" not in x] + [
    "US Federal Trade Commission staff (Jan 2025). Surveillance Pricing 6(b) study research summaries, p. 6 (quoted).",
    "Receipts in the opening are a reconstruction; the totals ($114.34 / $123.93) are from the Consumer Reports test at one Seattle Safeway.",
    "Larry, Linda and Mister Price are fictional characters. Scenes marked 'Reconstruction' are illustrations."]

# ---------------------------------------------------------------- 7 Shorts re-cut from the fixed master
LONG = {b["id"]: b for b in s["beats"]}


def L(bid, text=None, visual=None, keep=("punch", "pause_at", "sfx_at", "sfx", "say", "stamp", "label", "ledger_hide"), **kw):
    src = LONG[bid]
    v = src["visual"]
    if visual is None:
        if v["type"] in ("image", "archive", "clip"):
            visual = {"type": "reuse", "beat": bid, "motion": "zoom_in"}
            if v.get("exhibit"):
                visual["exhibit"] = copy.deepcopy(v["exhibit"])
            if v.get("marks"):
                visual["marks"] = copy.deepcopy(v["marks"])
                visual["motion"] = "static"
                if v.get("hand_marks"):
                    visual["hand_marks"] = True
        elif v["type"] == "reuse":
            visual = copy.deepcopy(v)
        else:
            visual = copy.deepcopy(v)
    b = {"text": text or src["text"], "visual": visual}
    if text is None:
        for k in keep:
            if k in src:
                b[k] = copy.deepcopy(src[k])
    b.update(kw)
    return b


SPLIT = copy.deepcopy(LONG["o1"]["visual"])
REC = copy.deepcopy(LONG["o2"]["visual"])
BASK = copy.deepcopy(LONG["s33"]["visual"])
s["shorts"] = [
    {"id": "s1", "title": "Same basket. Two receipts. #shorts", "hook": "Same basket. 2 receipts.",
     "beats": [L("o1"), L("o2"),
               L("s32", text="In 2025, hundreds of volunteers tested it. Same basket, same store, same moment.",
                 say="In twenty twenty-five, hundreds of volunteers tested it. Same basket, same store, same moment.",
                 visual={"type": "reuse", "beat": "s31", "motion": "zoom_in"}),
               L("s34"),
               L("s31", text="So next time, compare. Same store. Same basket. Same minute.", keep=())]},
    {"id": "s2", "title": "$114.34 vs $123.93 — same store, same minute #shorts", "hook": "$114.34 vs $123.93",
     "beats": [L("o2", text="One Seattle Safeway. One basket. Two receipts.", visual=copy.deepcopy(REC)),
               L("s33", ledger=[{"label": "LARRY", "amount": "$123.93", "on": "123"}, {"label": "LINDA", "amount": "$114.34", "on": "114"}]),
               L("s33b", ledger=[{"label": "DIFFERENCE", "amount": "-$9.59", "loss": True, "on": "luck"}]),
               L("s3b", ledger=[{"label": "PER YEAR (CR est.)", "amount": "-$1,200", "loss": True, "circle": True, "on": "twelve"}]),
               L("s3c"),
               L("s31", text="So check your receipt: one hundred and fourteen, or one hundred and twenty-three?", keep=())]},
    {"id": "s3", "title": "The 3% battery rumour: alibi confirmed #shorts", "hook": "3% battery = higher fare?",
     "beats": [L("b11", text="Does your ride cost more when your phone is at three percent?", keep=("sfx_at",)),
               L("d13"), L("d14"), L("b15"), L("b16"),
               L("b11", text="So, the next time you're down to three percent… does your ride cost more?", keep=())]},
    {"id": "s4", "title": "Meet the machine: location, device, cart #shorts", "hook": "Location · Device · Cart",
     "beats": [L("p43", keep=()), L("p41", voice="price"),
               L("p42", text="The FTC's own staff wrote it down: where you are, who you are, what you're doing.",
                 visual=copy.deepcopy(LONG["p42"]["visual"]) | {"doc": {**LONG["p42"]["visual"]["doc"], "on": "where", "pre": None}}),
               L("p44", keep=()), L("p45"),
               L("p46", voice="price", text="Nothing personal. Just your location, your device, your cart.")]},
    {"id": "s5", "title": "You weren't targeted. You were tested. #shorts", "hook": "You're the test",
     "beats": [L("w62", keep=("sfx_at",)), L("w61b"), L("w63"), L("w64"),
               L("w62", text="So the next time a price looks odd… remember the mice.", keep=())]},
    {"id": "s6", "title": "The 'was' price that never was #shorts", "hook": "WAS $6.69?",
     "beats": [L("s37"), L("s38"), L("s39"), L("s39b"), L("s39c"),
               L("v76", text="Next case: the sale that never was. Like these three 'was' prices.")]},
    {"id": "s7", "title": "Three things to do before you tap #shorts", "hook": "3 checks before you pay",
     "beats": [L("v75", text="Three things to do before you tap pay.", keep=()), L("v72"), L("v73"), L("v74b"),
               L("v75", text="Larry does all three now. Twice.", keep=())]},
]
for sh in s["shorts"]:
    for k, b in enumerate(sh["beats"]):
        b["id"] = f"{sh['id']}_{k}"
        if b["visual"].get("type") == "doc" and b["visual"]["doc"].get("pre") is None:
            b["visual"]["doc"].pop("pre", None)
        b.pop("inserts", None)

(HERE / "script.json").write_text(json.dumps(s, indent=2, ensure_ascii=False) + "\n")
print("beats:", len(s["beats"]), "words:", sum(len(b["text"].split()) for b in s["beats"]))
