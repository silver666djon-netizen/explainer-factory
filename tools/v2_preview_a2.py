"""Ep.4 v2 · Act 2 (The Lab) shot specs for the Remotion preview layer — picture-first (R41-R43), same vocabulary as the
cold open + Act 1 specs in v2_preview.py. "sheets": ink laid IN a picture's plane (q = the surface's 4 corners in px of
the original picture, W x H its own units; items: handwritten text and strokes, timed in order, one hand at a time)."""
W_ = lambda **k: k  # noqa: E731

LIB = "Library of Congress"


def img_sheet(w, h, items, color="#D2452F", **k):
    """a sheet that is the whole picture (units = px of the original)"""
    return W_(q=[[0, 0], [w, 0], [w, h], [0, h]], W=w, H=h, items=items, color=color, **k)


def T(text, x, y, size, **k):
    return {"k": "text", "text": text, "x": x, "y": y, "size": size, **k}


def L(d, **k):
    return {"k": "line", "d": d, **k}


SAFE = [(1167, 1092), (1683, 1087), (2200, 1083), (2728, 1087)]  # the four dials of ep04v2_a2_safe (px), r ~ 188
DIAL_R = 186


def dial_cam(i, z0=2.4, z1=2.7):
    x, y = SAFE[i][0] / 5016, SAFE[i][1] / 2823
    return [[x, y, z0], [x, y, z1]]


def dials(per):
    """dial specs: per = {i: {turn_on/open_on/done}}"""
    return [{"c": list(SAFE[i]), "r": DIAL_R, **per.get(i, {})} for i in range(4)]


SAFE_NUMS = [T(str(i + 1), SAFE[i][0], 1460, 150) for i in range(4)]
BELL = "M 300 640 C 1500 640, 1800 90, 2400 90 C 3000 90, 3300 640, 4700 640"
LARRY_DOT = "M 2470 610 C 2470 560, 2350 560, 2350 610 C 2350 660, 2470 660, 2470 610"
YOU_DOT = "M 3890 900 C 3890 850, 3770 850, 3770 900 C 3770 950, 3890 950, 3890 900"
G06 = [[1241, 715], [2370, 635], [2395, 1585], [1246, 1630]]  # the fridge calendar grid (5 x 4 cells)
P10 = [[772, 456], [2872, 456], [2872, 1763], [772, 1763]]  # the wall calendar grid (7 x 4 cells)
A4_BOARD = [[425, 80], [965, 80], [965, 195], [425, 195]]  # the blank price board of Ep.4 a4 (1376 x 768)
MUG_TAG = [[2270, 1292], [2538, 1121], [2930, 1655], [2558, 1881]]
REST = "+$8 +$6 +$4".split()

A2 = {
    # ---------------------------------------------------------------- the blueprint
    "A2.1a": W_(base="g01", cam=[[0.5, 0.5, 1.02], [0.5, 0.48, 1.12]], title=["ACT 2", "THE LAB"], plan=W_(mode="static")),
    "A2.1b": W_(base="g01", cam=[[0.62, 0.62, 1.35], [0.68, 0.66, 1.6]], plan=W_(mode="static", extra=[T("1998", 860, 585, 60, at_on="1998")])),
    "A2.2a": W_(base="p01", cam=[[0.5, 0.55, 1.02], [0.48, 0.55, 1.12]],
                overs=[W_(t="card", lines=["MORWITZ · GREENLEAF · JOHNSON · 1998", "\"Divide and Prosper\"", "Journal of Marketing Research"],
                          at_on="Three", x=0.5, y=0.5, w=1100, size=44)], sfx=[{"kind": "type", "on": "Three"}]),
    "A2.2b": W_(base="n1", cam=[[0.45, 0.5, 1.05], [0.42, 0.52, 1.2]], cont=True,
                sheets=[img_sheet(1376, 768, [T("BASE", 440, 400, 64, at_on="base"), T("SURCHARGE", 250, 525, 36, at_on="surcharge")])]),
    "A2.3": W_(base="n1", cam=[[0.42, 0.52, 1.2], [0.4, 0.55, 1.35]],
               sheets=[img_sheet(1376, 768, [T("BASE", 440, 400, 64, static=True), T("SURCHARGE", 250, 525, 36, static=True),
                                             L("M 380 640 L 470 640", at=0.3, w=9), L("M 380 672 L 470 672", w=9),
                                             T("SAME TOTAL", 430, 740, 46, at_on="total")])]),
    "A2.4": W_(base="p03", cam=[[0.5, 0.5, 1.02], [0.52, 0.45, 1.15]],
               overs=[W_(t="tags", items=["BOUGHT MORE"], at_on=["bought"], x=0.8, y=0.12, w=480, size=70, color="#2E6B4F")], sfx=[{"kind": "ding", "on": "bought"}]),
    "A2.5": W_(base="n4", cam=[[0.5, 0.5, 1.02], [0.5, 0.5, 1.12]], overs=[W_(t="smallprint", first="$30", rest=REST, at_on="small", x=0.3, y=0.35)]),
    "A2.6a": W_(base="a10clip", cam=[[0.5, 0.5, 1.0], [0.5, 0.52, 1.08]]),
    "A2.6b": W_(base="arch_radiocrowd", cam=[[0.5, 0.5, 1.0], [0.48, 0.55, 1.12]], caption="Crowd waiting to buy tickets, Radio City Music Hall, New York, 1942 · " + LIB),
    "A2.7": W_(base="arch_loews", cam=[[0.6, 0.5, 1.05], [0.5, 0.5, 1.14]], caption="Ticket line, Loew's Capitol, Washington, D.C., 1939 · " + LIB,
               overs=[W_(t="plate", text="AUGUST 2015 · STUBHUB (OWNED BY EBAY)", at_on="August", x=0.5, y=0.1)]),
    # ---------------------------------------------------------------- the experiment
    "A2.8a": W_(base="a4", cam=[[0.5, 0.45, 1.02], [0.5, 0.3, 1.5]], cont=True,
                sheets=[W_(q=A4_BOARD, W=540, H=115, color="#1E1B18", items=[T("$48 ALL-IN", 270, 88, 70, at_on="upfront")])]),
    "A2.8b": W_(base="a4", cam=[[0.5, 0.3, 1.5], [0.5, 0.26, 1.75]],
                sheets=[W_(q=A4_BOARD, W=540, H=115, color="#1E1B18", items=[T("$48 ALL-IN", 270, 88, 70, static=True), L("M 90 104 L 450 104", at_on="screen", w=6)])],
                overs=[W_(t="tags", items=["= YOU PAY"], at_on=["paid"], x=0.5, y=0.66, w=440, size=72)]),
    "A2.9a": W_(base="a5", cam=[[0.5, 0.5, 1.02], [0.5, 0.48, 1.1]],
                sheets=[img_sheet(1376, 768, [T("A", 300, 170, 110, at_on="Then"), T("B", 1080, 170, 110)])]),
    "A2.9b": W_(base="p04", cam=[[0.5, 0.42, 1.05], [0.5, 0.4, 1.14]],
                screen=W_(mode="allin", price="$48", sub="FEES INCLUDED", head="CHECKOUT A"), screen2=W_(mode="split", late=True, head="CHECKOUT B"),
                overs=[W_(t="tags", items=["12 DAYS"], at_on=["Two"], x=0.5, y=0.04, w=330, size=80)]),
    "A2.J4a": W_(base="g06", cam=[[0.4, 0.42, 1.25], [0.38, 0.4, 1.45]],
                 sheets=[W_(q=G06, W=500, H=400, color="#1E1B18", at=0.3, items=[T(str(n + 1), 18 + (n % 5) * 100, 30 + (n // 5) * 100, 26) for n in range(12)]),
                         W_(q=G06, W=500, H=400, color="#D2452F", items=[L("M 212 12 L 288 88", at_on="diet", w=9), L("M 288 12 L 212 88", w=9)])]),
    "A2.J4b": W_(base="a5", cam=[[0.5, 0.48, 1.1], [0.52, 0.45, 1.2]],
                 overs=[W_(t="tags", items=["12 DAYS", "MILLIONS OF BUYERS"], at_on=["experiment", "millions"], x=0.5, y=0.08, w=640, size=70)]),
    "A2.10a": W_(base="a5", cam=[[0.5, 0.45, 1.02], [0.5, 0.43, 1.1]],
                 sheets=[img_sheet(1376, 768, [T("A", 300, 170, 110, static=True), T("B", 1080, 170, 110, static=True),
                                               T("FULL PRICE", 330, 265, 52, at_on="full"), T("TICKET ONLY", 1050, 265, 52)])]),
    "A2.10b": W_(base="a12clip", cam=[[0.5, 0.5, 1.0], [0.5, 0.52, 1.08]]),
    "A2.11": W_(base="p04", cam=[[0.5, 0.42, 1.08], [0.5, 0.4, 1.18]],
                screen=W_(mode="split", late=False, head="CHECKOUT A"), screen2=W_(mode="split", late=True, fee_on="moment", head="CHECKOUT B")),
    "A2.12": W_(base="a5", cam=[[0.6, 0.5, 1.1], [0.7, 0.5, 1.3]],
                overs=[W_(t="tags", items=["+14%"], at_on=["fourteen"], x=0.25, y=0.15, w=300, size=110, color="#2E6B4F"),
                       W_(t="plate", text="NBER WORKING PAPER 25186", at_on="Here's", x=0.5, y=0.06)], sfx=[{"kind": "pop", "on": "fourteen"}]),
    "A2.13a": W_(base="s02", cam=[[0.5, 0.45, 1.05], [0.52, 0.42, 1.15]], screen=W_(mode="seat", seat="F12", light_=-1, jump_on="pricier"),
                 overs=[W_(t="tags", items=["+5%"], at_on=["five"], x=0.88, y=0.12, w=230, size=96)], sfx=[{"kind": "pop", "on": "five"}]),
    "A2.13b": W_(base="a12", cam=[[0.5, 0.5, 1.02], [0.45, 0.55, 1.15]]),
    "A2.14a": W_(base="a5", cam=[[0.55, 0.5, 1.2], [0.62, 0.5, 1.35]]),
    "A2.14b": W_(base="key", key="≈21%", sub="MORE SPENT", at_on="twenty-one"),
    "A2.15": W_(base="l1", cam=[[0.5, 0.55, 1.05], [0.5, 0.55, 1.15]],
                overs=[W_(t="card", lines=["NBER w25186 · 2018", "Blake, Moshary, Sweeney & Tadelis", "\"Price Salience and Product Choice\"",
                                           "fees at the end: spent ~21% more"], hl="21%", at=0.15, x=0.5, y=0.48, w=1120, size=44)],
                sfx=[{"kind": "paper", "at": 0.1}]),
    "A2.16": W_(base="p06", cam=[[0.5, 0.45, 1.02], [0.48, 0.4, 1.12]], cont=True,
                sheets=[img_sheet(5016, 2823, [L(BELL, at=0.4, w=26), L(LARRY_DOT, at_on="average", w=22)])]),
    "A2.17a": W_(base="p06", cam=[[0.48, 0.4, 1.12], [0.55, 0.42, 1.0]],
                 sheets=[img_sheet(5016, 2823, [L(BELL, w=26, static=True), L(LARRY_DOT, w=22, static=True), L(YOU_DOT, at_on="part", w=22),
                                                T("YOU", 3830, 800, 190)])]),
    "A2.17b": W_(base="arch_concert", cam=[[0.5, 0.5, 1.0], [0.5, 0.55, 1.1]], caption="Audience at a concert given by Marian Anderson, Chicago, Illinois, 1941 · " + LIB),
    # ---------------------------------------------------------------- the four locks
    "A2.18a": W_(base="a2_safe", cam=[[0.4, 0.45, 1.02], [0.38, 0.45, 1.1]],
                 overs=[W_(t="plate", text="HOW THE LOCK WAS PICKED", at=0.3, x=0.5, y=0.08)]),
    "A2.18b": W_(base="p07", cam=[[0.5, 0.5, 1.02], [0.6, 0.5, 1.14]]),
    "A2.19a": W_(base="a2_safe", cam=[[0.4, 0.45, 1.05], [0.39, 0.45, 1.14]], sheets=[img_sheet(5016, 2823, [dict(x, at=0.4) if i == 0 else x for i, x in enumerate(SAFE_NUMS)], color="#F3F1EA")],
                 sfx=[{"kind": "tick", "on": "four"}]),
    "A2.19b": W_(base="a2_safe", cam=[[0.3, 0.42, 1.6], [0.25, 0.4, 1.9]], sheets=[img_sheet(5016, 2823, [dict(x, static=True) for x in SAFE_NUMS], color="#F3F1EA")]),
    "A2.20a": W_(base="a2_safe", cam=dial_cam(0), dials=dials({0: {"turn_on": "first"}}), sfx=[{"kind": "tick", "on": "first"}]),
    "A2.20b": W_(base="s03", cam=[[0.511, 0.52, 1.5], [0.511, 0.52, 1.7]], screen=W_(mode="anchor", shrink_on="footnote", head="1 TICKET")),
    "A2.20c": W_(base="a2_safe", cam=dial_cam(0, 2.7, 2.75), dials=dials({0: {"turn_": -2.0, "open_on": "less"}}), sfx=[{"kind": "kachunk", "on": "less"}]),
    "A2.21a": W_(base="a2_safe", cam=dial_cam(1), dials=dials({0: {"done": True}, 1: {"turn_on": "two"}}), sfx=[{"kind": "tick", "on": "two"}]),
    "A2.21b": W_(base="a4_seat", cam=[[0.4, 0.42, 1.05], [0.38, 0.4, 1.18]], grade="gray"),
    "A2.22a": W_(base="l1", cam=[[0.5, 0.55, 1.05], [0.5, 0.55, 1.15]],
                 overs=[W_(t="card", lines=["KAHNEMAN · KNETSCH · THALER · 1990", "\"Experimental Tests of the", "Endowment Effect\"", "Journal of Political Economy"],
                           at=0.15, x=0.5, y=0.48, w=1100, size=44)], sfx=[{"kind": "paper", "at": 0.1}]),
    "A2.22b": W_(base="a2_mug", cam=[[0.45, 0.5, 1.02], [0.45, 0.48, 1.1]]),
    "A2.22c": W_(base="a2_mug", cam=[[0.55, 0.52, 1.35], [0.56, 0.52, 1.5]],
                 sheets=[W_(q=MUG_TAG, W=300, H=440, color="#D2452F", items=[T("SELL", 150, 230, 64, at_on="sell"), T("$7.12", 150, 320, 70)])],
                 overs=[W_(t="tags", items=["BUY $2.87"], at_on=["buy"], x=0.2, y=0.12, w=420, size=76, color="#2E6B4F")]),
    "A2.22d": W_(base="a2_safe", cam=dial_cam(1, 2.7, 2.75), dials=dials({0: {"done": True}, 1: {"turn_": -2.0, "open_on": "theirs"}}),
                 sfx=[{"kind": "kachunk", "on": "theirs"}]),
    "A2.23a": W_(base="a2_safe", cam=dial_cam(2), dials=dials({0: {"done": True}, 1: {"done": True}, 2: {"turn_on": "three"}}), sfx=[{"kind": "tick", "on": "three"}]),
    "A2.23b": W_(base="p08", cam=[[0.4, 0.42, 1.05], [0.36, 0.38, 1.2]]),
    "A2.23c": W_(base="a2_safe", cam=dial_cam(2, 2.7, 2.75), dials=dials({0: {"done": True}, 1: {"done": True}, 2: {"turn_": -2.0, "open_on": "cheaper"}}),
                 sfx=[{"kind": "kachunk", "on": "cheaper"}]),
    "A2.24a": W_(base="a2_safe", cam=dial_cam(3), dials=dials({0: {"done": True}, 1: {"done": True}, 2: {"done": True}, 3: {"turn_on": "four"}}),
                 sfx=[{"kind": "tick", "on": "four"}]),
    "A2.24b": W_(base="p09", cam=[[0.5, 0.5, 1.02], [0.58, 0.55, 1.12]],
                 overs=[W_(t="tags", items=["$18"], at_on=["Eighteen"], x=0.76, y=0.3, w=230, size=100)]),
    "A2.25a": W_(base="l1", cam=[[0.5, 0.55, 1.05], [0.5, 0.55, 1.15]],
                 overs=[W_(t="card", lines=["TVERSKY & KAHNEMAN · 1981", "\"The Framing of Decisions and", "the Psychology of Choice\"", "Science 211"],
                           at=0.15, x=0.5, y=0.48, w=1100, size=44)], sfx=[{"kind": "paper", "at": 0.1}]),
    "A2.25b": W_(base="a2_calculators", cam=[[0.5, 0.5, 1.02], [0.5, 0.48, 1.1]]),
    "A2.25c": W_(base="a2_calculators", cam=[[0.42, 0.55, 1.05], [0.42, 0.55, 1.12]],
                 sheets=[img_sheet(5016, 2823, [{"k": "route", "d": "M 500 1150 C 900 600, 1500 600, 1850 1000", "w": 14, "at_on": "drive"}, T("20 MIN", 1180, 620, 110),
                                                T("$15", 250, 2140, 120, at_on="fifteen")])]),
    "A2.25d": W_(base="a2_calculators", cam=[[0.55, 0.45, 1.3], [0.5, 0.45, 1.2]],
                 sheets=[img_sheet(5016, 2823, [T("$15", 250, 2140, 120, static=True), T("$125", 2200, 2120, 120, at_on="hundred")])],
                 overs=[W_(t="tags", items=["68% DRIVE"], at=[0.3], x=0.2, y=0.14, w=420, size=70, color="#2E6B4F"),
                        W_(t="tags", items=["29% DRIVE"], at_on=["one"], x=0.72, y=0.14, w=420, size=70)]),
    "A2.25e": W_(base="a2_safe", cam=dial_cam(3, 2.7, 2.75), dials=dials({0: {"done": True}, 1: {"done": True}, 2: {"done": True}, 3: {"turn_": -2.0, "open_on": "doesn't"}}),
                 overs=[W_(t="note", text="$5 = $5", size=96, write_on="five#3", x=0.06, y=0.2)], sfx=[{"kind": "kachunk", "on": "doesn't"}]),
    "A2.J5": W_(base="p10", cam=[[0.38, 0.4, 1.3], [0.36, 0.38, 1.5]],
                sheets=[W_(q=P10, W=700, H=400, color="#D2452F", items=[T("MONDAY", 160, 62, 46, at_on="thinks"), T("GYM", 150, 175, 80, at_on="gym"),
                                                                       L("M 40 132 L 270 160", w=16)])]),
    "A2.26a": W_(base="a2_lookout", cam=[[0.35, 0.5, 1.05], [0.32, 0.5, 1.2]]),
    "A2.26b": W_(base="s04", cam=[[0.42, 0.42, 1.05], [0.42, 0.41, 1.3]], dial_time="8:18"),
    "A2.27a": W_(base="a2_safe", cam=[[0.4, 0.5, 1.05], [0.42, 0.5, 1.18]], door=W_(box=[790, 439, 3185, 2295], hinge="right", at_on="click", dur=1.4),
                 sfx=[{"kind": "kachunk", "on": "click"}]),
    "A2.27b": W_(base="s02", cam=[[0.516, 0.51, 1.74], [0.516, 0.51, 1.88]],
                 screen=W_(mode="fees", fees=[W_(name="SERVICE FEE", amt="$8"), W_(name="FACILITY FEE", amt="$6"), W_(name="PROCESSING", amt="$4")]),
),
    "A2.28a": W_(base="x1clip", cam=[[0.5, 0.5, 1.0], [0.5, 0.5, 1.06]]),
    "A2.28b": W_(base="l1", cam=[[0.5, 0.55, 1.05], [0.5, 0.55, 1.15]],
                 overs=[W_(t="card", lines=["NBER w25186 · p. 27", "1 SEPTEMBER 2015:", "the whole site switched", "to fees at the end"], hl="fees at the end",
                           at=0.15, x=0.5, y=0.48, w=1000, size=46)], sfx=[{"kind": "paper", "at": 0.1}]),
    "A2.29": W_(base="a12clip", cam=[[0.5, 0.5, 1.02], [0.5, 0.5, 1.1]]),
    "A2.30": W_(base="sub", cam=[[0.45, 0.5, 1.05], [0.42, 0.5, 1.2]], overs=[W_(t="note", text="SUBSCRIBE", size=96, write_on="subscribe", x=0.6, y=0.62)]),
    "A2.31": W_(base="arch_coop", cam=[[0.75, 0.5, 1.0], [0.4, 0.5, 1.12]], caption="Hotel sign, Cooperstown, New York, 1937 · " + LIB),
}
KLOT_A2 = {"a2_safe": "ep04v2_a2_safe", "a2_mug": "ep04v2_a2_mug", "a2_calculators": "ep04v2_a2_calculators", "a2_lookout": "ep04v2_a2_lookout",
           "g06": "ep04v2_g06_diet", "p01": "ep04v2_p01_journal_desk", "p03": "ep04v2_p03_shoppers_bags", "p04": "ep04v2_p04_two_laptops",
           "p06": "ep04v2_p06_crowd_with_larry", "p07": "ep04v2_p07_dollars_walk_out", "p08": "ep04v2_p08_tired_larry", "p09": "ep04v2_p09_scale",
           "p10": "ep04v2_p10_wall_calendar", "arch_radiocrowd": "ep04v2_arch_radiocity_crowd_1942", "arch_concert": "ep04v2_arch_concert_1941",
           "arch_coop": "ep04v2_arch_cooperstown_1937"}
EP4_A2 = {"n1": "n1", "n4": "n4", "a4": "a4", "a12": "a12", "sub": "sub"}
CLIPS_A2 = {"a12clip": "a12", "x1clip": "x1"}
