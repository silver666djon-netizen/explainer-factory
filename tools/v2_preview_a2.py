"""Ep.4 v2 · Act 2 (The Lab) shot specs for the Remotion preview layer — picture-first (R41-R48), same vocabulary as the
cold open + Act 1 specs in v2_preview.py. "sheets": ink and paper laid IN a picture's plane (q = the surface's 4 corners in px
of the original picture, W x H its own units; items: handwritten text / strokes (one hand, pen colour = item colour), cream
paper tags (pop in, no hand, optional printed arrow), typed paper cards, cut-out props)."""
W_ = lambda **k: k  # noqa: E731

LIB = "Library of Congress"
INK, RED, GREEN, CHALK = "#1E1B18", "#B23421", "#2E6B4F", "#FBFAF5"


def img_sheet(w, h, items, color=RED, **k):
    """a sheet that is the whole picture (units = px of the original)"""
    return W_(q=[[0, 0], [w, 0], [w, h], [0, h]], W=w, H=h, items=items, color=color, **k)


def T(text, x, y, size, **k):
    return {"k": "text", "text": text, "x": x, "y": y, "size": size, **k}


def L(d, **k):
    return {"k": "line", "d": d, **k}


def TAG(text, x, y, w, h, size, **k):
    return {"k": "tag", "text": text, "x": x, "y": y, "w": w, "h": h, "size": size, **k}


def CARD(lines, size=50, hl=None, **k):
    """a typed paper card lying in the picture (sheet units: 1000 x 120 + 66 per line)"""
    h = 120 + 66 * len(lines)
    return {"k": "paper", "lines": lines, "x": 500, "y": h / 2, "w": 1000, "h": h, "size": size, "hl": hl, **k}


def card_sheet(q, lines, hl=None, at=0.15, **k):  # the shot gets cardcam=True: the camera is fitted to the card
    c = CARD(lines, hl=hl, at=at)
    return W_(q=q, W=1000, H=c["h"], items=[c], color=INK, card=True, **k)


# the five desk framings of p01 for the paper cards (px of the picture; Klot: each card on the journal desk, a new framing)
P01_CARD = {
    "journal": [[1180, 1300], [3380, 1270], [3460, 1930], [1110, 1960]],
    "front_left": [[620, 1960], [2620, 1910], [2700, 2540], [560, 2590]],
    "right": [[2650, 1880], [4580, 1930], [4570, 2560], [2600, 2540]],
    "journal_tilt": [[1300, 1240], [3400, 1360], [3320, 2000], [1170, 1880]],
    "front_centre": [[1500, 1940], [3560, 1910], [3640, 2540], [1420, 2580]],
}
SAFE = [(1167, 1092), (1683, 1087), (2200, 1083), (2728, 1087)]  # the four dials of ep04v2_a2_safe (px), r ~ 188
DIAL_R = 186
P04FS = {"os": 80, "row": 92}  # two laptops side by side: the screens are small in the frame, so their type is bigger
DIAL, CLICK = 1.1, 1.0  # Klot: a dial turns in <= 1.5 s, never more than 2 s of dials in a row


def dial_cam(i, z0=2.4, z1=2.55):
    x, y = SAFE[i][0] / 5016, SAFE[i][1] / 2823
    return [[x, y, z0], [x, y, z1]]


def turn_tags(i, z=1.62):
    """the number tags that stand fully inside the medium shot of dial i (>= 6 % from its edges)"""
    hw = 5016 / (2 * z)
    cx = min(max(SAFE[i][0], hw), 5016 - hw)
    return [dict(t, static=True) for t in SAFE_TAGS if abs(t["x"] - cx) + t["w"] / 2 < hw * 0.86]


def turn_cam(i):
    """the lock's dial turning, in a medium shot (its neighbours and number tags in view): a dial close-up only for the click"""
    x, y = SAFE[i][0] / 5016, SAFE[i][1] / 2823 + 0.04
    return [[x, y, 1.5], [x, y, 1.62]]


def dials(per):
    return [{"c": list(SAFE[i]), "r": DIAL_R, **per.get(i, {})} for i in range(4)]


def opened(n, extra=None):
    d = {i: {"done": True} for i in range(n)}
    d.update(extra or {})
    return d


SAFE_TAGS = [TAG(str(i + 1), SAFE[i][0], 1470, 170, 170, 130, static=True) for i in range(4)]
G06 = [[1241, 715], [2370, 635], [2395, 1585], [1246, 1630]]  # the fridge calendar grid (5 x 4 cells)
P10 = [[772, 456], [2872, 456], [2872, 1763], [772, 1763]]  # the wall calendar grid (7 x 4 cells)
MUG_TAG = [[2270, 1292], [2538, 1121], [2930, 1655], [2558, 1881]]
S03_TABLE = [[3800, 2360], [4500, 2350], [4560, 2630], [3760, 2640]]  # Larry's kitchen table, right of the laptop (s03)
N1 = (1224, 643)  # the cut-out scissors + cut ticket (props/n1_scissors.png)
SCISSORS = W_(q=S03_TABLE, W=N1[0], H=N1[1], color=RED,
              items=[{"k": "prop", "src": "v2/props/n1_scissors.png", "x": 612, "y": 321, "w": N1[0], "h": N1[1], "static": True}])


def scissors(extra):
    return dict(SCISSORS, items=SCISSORS["items"] + extra)


A2 = {
    # ---------------------------------------------------------------- the blueprint
    "A2.1a": W_(base="g01", cam=[[0.5, 0.5, 1.02], [0.5, 0.48, 1.12]], grade="dusk", title=["ACT 2", "THE LAB"], plan=W_(mode="static")),
    "A2.1b": W_(base="g01", cam=[[0.46, 0.42, 1.45], [0.46, 0.4, 1.65]], grade="dusk", plan=W_(mode="static", extra=[T("1998", 500, 258, 60, at_on="1998")])),
    "A2.2a": W_(base="p01", cardcam=True, cam=[[0.46, 0.55, 1.45], [0.43, 0.52, 1.75]], sfx=[{"kind": "type", "on": "Three"}],
                sheets=[card_sheet(P01_CARD["journal"], ["MORWITZ · GREENLEAF · JOHNSON", "1998 · \"Divide and Prosper\"", "Journal of Marketing Research"],
                                   hl="Divide and Prosper", at_on="Three")]),
    "A2.2b": W_(base="s03", cam=[[0.83, 0.86, 3.3], [0.83, 0.86, 3.5]], cont=True, screen=W_(mode="tabs", tabs=[W_(price="$30")], active=0),
                sheets=[scissors([T("BASE", 520, 500, 96, at_on="base", col=INK), T("SURCHARGE", 230, 620, 74, at_on="surcharge", col=INK)])]),
    "A2.3": W_(base="s03", cam=[[0.83, 0.86, 3.5], [0.83, 0.86, 3.65]], screen=W_(mode="tabs", tabs=[W_(price="$30")], active=0),
               sheets=[scissors([T("BASE", 520, 500, 96, static=True, col=INK), T("SURCHARGE", 230, 620, 74, static=True, col=INK)])],
               overs=[W_(t="tags", items=["= SAME TOTAL"], at_on=["total"], x=0.3, y=0.14, w=560, size=86)]),
    "A2.4": W_(base="p03", cam=[[0.5, 0.5, 1.02], [0.52, 0.45, 1.15]],
               overs=[W_(t="tags", items=["BOUGHT MORE"], at_on=["bought"], x=0.5, y=0.68, w=480, size=70, color=GREEN)], sfx=[{"kind": "ding", "on": "bought"}]),
    "A2.5": W_(base="p01", cam=[[0.47, 0.2, 2.3], [0.47, 0.2, 2.55]],
               sheets=[img_sheet(5016, 2823, [TAG("$30", 2420, 470, 460, 280, 210, col=GREEN, at_on="first"),
                                              TAG("+$8", 2120, 790, 230, 140, 100, col=RED, at_on="Everything", to=0.55, t1_on="small"),
                                              TAG("+$6", 2400, 800, 230, 140, 100, col=RED, at_on="Everything", to=0.55, t1_on="small"),
                                              TAG("+$4", 2680, 790, 230, 140, 100, col=RED, at_on="Everything", to=0.55, t1_on="small")])]),
    "A2.6a": W_(base="a10clip", cam=[[0.5, 0.5, 1.0], [0.5, 0.52, 1.08]]),
    "A2.6b": W_(base="p06", cam=[[0.5, 0.5, 1.0], [0.5, 0.5, 1.1]]),
    "A2.7": W_(base="a5", cam=[[0.3, 0.39, 1.3], [0.32, 0.39, 1.4]], overs=[W_(t="plate", text="AUGUST 2015 · STUBHUB (OWNED BY EBAY)", at_on="August", x=0.5, y=0.08)]),
    # ---------------------------------------------------------------- the experiment
    "A2.8a": W_(base="s03", cam=[[0.511, 0.52, 1.5], [0.511, 0.52, 1.68]], screen=W_(mode="allin", price="$48", sub="FEES INCLUDED", head="CHECKOUT"),
                overs=[W_(t="tags", items=["= YOU PAY"], at_on=["paid"], x=0.5, y=0.08, w=420, size=80)]),
    "A2.8b": W_(base="a1_glow", cam=[[0.42, 0.42, 1.08], [0.4, 0.4, 1.22]]),
    "A2.9a": W_(base="a5", cam=[[0.5, 0.5, 1.0], [0.5, 0.5, 1.06]],
                sheets=[img_sheet(1376, 768, [TAG("A", 300, 160, 130, 110, 92, at_on="split"), TAG("B", 1076, 160, 130, 110, 92, at_on="split")])]),
    "A2.9b": W_(base="p04", cam=[[0.5, 0.42, 1.05], [0.5, 0.4, 1.14]],
                screen=W_(mode="allin", price="$48", sub="FEES INCLUDED", head="CHECKOUT A", fs=P04FS), screen2=W_(mode="split", late=True, head="CHECKOUT B", fs=P04FS),
                overs=[W_(t="tags", items=["12 DAYS"], at_on=["Two"], x=0.5, y=0.08, w=330, size=80)]),
    "A2.J4a": W_(base="g06", cam=[[0.4, 0.42, 1.25], [0.38, 0.4, 1.45]],
                 sheets=[W_(q=G06, W=500, H=400, color=INK, at=0.25,
                            items=[T(str(n + 1), 26 + (n % 5) * 100, 44 + (n // 5) * 100, 42, col=INK) for n in range(12)]
                            + [L("M 212 12 L 288 88", at_on="diet", w=9, col=RED), L("M 288 12 L 212 88", w=9, col=RED)])]),
    "A2.J4b": W_(base="p06", cam=[[0.78, 0.5, 1.45], [0.8, 0.5, 1.55]],
                 overs=[W_(t="tags", items=["12 DAYS", "MILLIONS OF BUYERS"], at_on=["experiment", "millions"], x=0.45, y=0.56, w=640, size=70)]),
    "A2.10a": W_(base="a5", cam=[[0.5, 0.45, 1.15], [0.5, 0.45, 1.28]],
                 sheets=[img_sheet(1376, 768, [TAG("A · FULL PRICE", 445, 160, 380, 96, 52, at_on="full"), TAG("B · TICKET ONLY", 925, 160, 400, 96, 52, at_on="other")])]),
    "A2.10b": W_(base="a12clip", cam=[[0.5, 0.5, 1.0], [0.5, 0.52, 1.08]]),
    "A2.11": W_(base="p04", cam=[[0.5, 0.42, 1.12], [0.5, 0.4, 1.22]],
                screen=W_(mode="allin", price="$48", sub="FEES INCLUDED", head="CHECKOUT A", fs=P04FS), screen2=W_(mode="split", late=True, fee_on="moment", head="CHECKOUT B", fs=P04FS)),
    "A2.12": W_(base="a5", cam=[[0.72, 0.5, 1.35], [0.78, 0.52, 1.45]],
                overs=[W_(t="tags", items=["+14%"], at_on=["fourteen"], x=0.5, y=0.78, w=300, size=110, color=GREEN),
                       ], sfx=[{"kind": "pop", "on": "fourteen"}]),
    "A2.13a": W_(base="s02", cam=[[0.511, 0.5, 1.45], [0.511, 0.5, 1.6]], screen=W_(mode="seat", seat="F12", light_=-1, jump_on="pricier"),
                 overs=[W_(t="tags", items=["+5%"], at_on=["five"], x=0.84, y=0.1, w=230, size=96)], sfx=[{"kind": "pop", "on": "five"}]),
    "A2.13b": W_(base="a12", cam=[[0.5, 0.5, 1.02], [0.45, 0.55, 1.15]]),
    "A2.14a": W_(base="s05", cam=[[0.45, 0.4, 1.05], [0.45, 0.38, 1.15]]),
    "A2.14b": W_(base="key", key="≈21%", sub="MORE SPENT", at=0.05, cut_on="twenty-one"),
    "A2.15": W_(base="p01", cardcam=True, cam=[[0.33, 0.8, 1.9], [0.3, 0.83, 2.25]], sfx=[{"kind": "paper", "at": 0.1}],
                sheets=[card_sheet(P01_CARD["front_left"], ["NBER w25186 · 2018", "Blake, Moshary, Sweeney", "& Tadelis: fees at the end,", "buyers spent ~21% more"], hl="~21% more")]),
    "A2.16": W_(base="p06", cam=[[0.5, 0.45, 1.02], [0.48, 0.42, 1.12]],
                sheets=[img_sheet(5016, 2823, [TAG("LARRY", 2400, 300, 520, 170, 120, at_on="Larry", arrow=[2440, 520], col=INK)])]),
    "A2.17a": W_(base="p06", cam=[[0.48, 0.42, 1.12], [0.5, 0.45, 1.0]],
                 sheets=[img_sheet(5016, 2823, [TAG("LARRY", 2400, 300, 520, 170, 120, static=True, arrow=[2440, 520], col=INK),
                                                TAG("YOU", 1980, 1700, 420, 170, 130, at_on="you're", arrow=[1980, 2200], col=RED)])]),
    "A2.17b": W_(base="arch_concert", cam=[[0.5, 0.5, 1.0], [0.5, 0.55, 1.1]], caption="Audience at a concert given by Marian Anderson, Chicago, Illinois, 1941 · " + LIB),
    # ---------------------------------------------------------------- the four locks (per lock: dial <= 1.5 s -> story -> click)
    "A2.18a": W_(base="a2_safe", cam=[[0.4, 0.45, 1.02], [0.38, 0.45, 1.1]], title=["THE SAFE IN YOUR HEAD", "HOW THE LOCK WAS PICKED"]),
    "A2.18b": W_(base="p07", cam=[[0.5, 0.5, 1.02], [0.6, 0.5, 1.14]]),
    "A2.19a": W_(base="a2_safe", cam=[[0.4, 0.45, 1.05], [0.39, 0.45, 1.12]], dur=3.0,
                 sheets=[img_sheet(5016, 2823, [dict(x, static=False, at=0.3 + 0.18 * i) for i, x in enumerate(SAFE_TAGS)])], sfx=[{"kind": "tick", "at": 1.0}]),
    "A2.19b": W_(base="s03", cam=[[0.5, 0.52, 1.55], [0.45, 0.5, 1.75]],
                 screen=W_(mode="fees", fees=[W_(name="SERVICE FEE", amt="$8"), W_(name="FACILITY FEE", amt="$6"), W_(name="PROCESSING", amt="$4")])),
    "A2.20a": W_(base="a2_safe", cam=turn_cam(0), dur=1.4, sheets=[img_sheet(5016, 2823, turn_tags(0))], dials=dials({0: {"turn_on": "one", "turn_dur": 0.8}}), sfx=[{"kind": "tick", "on": "one"}]),
    "A2.20b": W_(base="s03", cam=[[0.511, 0.52, 1.45], [0.511, 0.52, 1.6]], screen=W_(mode="anchor", shrink_on="treats", head="1 TICKET")),
    "A2.20c": W_(base="s06", cam=[[0.4, 0.42, 1.05], [0.36, 0.4, 1.18]]),
    "A2.20d": W_(base="a2_safe", cam=dial_cam(0, 2.55, 2.6), dur=CLICK, quick=True, dials=dials(opened(0, {0: {"turn_": -2.0, "open_on": "did"}})), sfx=[{"kind": "kachunk", "on": "did"}]),
    "A2.21a": W_(base="a2_safe", cam=turn_cam(1), dur=1.4, sheets=[img_sheet(5016, 2823, turn_tags(1))], dials=dials(opened(1, {1: {"turn_on": "two", "turn_dur": 0.8}})), sfx=[{"kind": "tick", "on": "two"}]),
    "A2.21b": W_(base="s02", cam=[[0.511, 0.5, 1.45], [0.511, 0.5, 1.58]], screen=W_(mode="seat", seat="G12", light_=-1),
                 overs=[W_(t="plate", text="TUE · 8:18 PM", at=0.2, x=0.5, y=0.08)]),
    "A2.21c": W_(base="s01", cam=[[0.36, 0.33, 2.0], [0.355, 0.31, 2.5]], grade="gray"),
    "A2.21d": W_(base="a1_wallet", cam=[[0.47, 0.5, 1.15], [0.47, 0.52, 1.3]]),
    "A2.22a": W_(base="p01", cardcam=True, cam=[[0.78, 0.82, 1.9], [0.8, 0.84, 2.25]], sfx=[{"kind": "paper", "at": 0.1}],
                 sheets=[card_sheet(P01_CARD["right"], ["KAHNEMAN · KNETSCH · THALER", "1990 · \"Experimental Tests of", "the Endowment Effect\""], hl="Endowment Effect")]),
    "A2.22b": W_(base="a2_mug", cam=[[0.45, 0.5, 1.02], [0.45, 0.48, 1.1]]),
    "A2.22c": W_(base="a2_mug", cam=[[0.55, 0.52, 1.25], [0.57, 0.52, 1.38]],
                 sheets=[W_(q=MUG_TAG, W=300, H=440, color=RED, items=[T("SELL", 150, 210, 70, at_on="sell"), T("$7.12", 150, 310, 70)]),
                         img_sheet(5016, 2823, [TAG("BUY $2.87", 3500, 1500, 640, 220, 130, col=GREEN, at_on="others")])]),
    "A2.22d": W_(base="a2_safe", cam=dial_cam(1, 2.55, 2.6), dur=CLICK, quick=True, dials=dials(opened(1, {1: {"turn_": -2.0, "open_on": "theirs"}})),
                 sfx=[{"kind": "kachunk", "on": "theirs"}]),
    "A2.23a": W_(base="a2_safe", cam=turn_cam(2), dur=1.4, sheets=[img_sheet(5016, 2823, turn_tags(2))], dials=dials(opened(2, {2: {"turn_on": "three", "turn_dur": 0.8}})), sfx=[{"kind": "tick", "on": "three"}]),
    "A2.23b": W_(base="s03", cam=[[0.511, 0.52, 1.4], [0.57, 0.56, 1.62]], screen=W_(mode="form", fill=[1, 1])),
    "A2.23c": W_(base="p08", cam=[[0.4, 0.42, 1.05], [0.36, 0.38, 1.2]]),
    "A2.23d": W_(base="a2_safe", cam=dial_cam(2, 2.55, 2.6), dur=CLICK, quick=True, dials=dials(opened(2, {2: {"turn_": -2.0, "open_on": "over"}})),
                 sfx=[{"kind": "kachunk", "on": "over"}]),
    "A2.24a": W_(base="a2_safe", cam=turn_cam(3), dur=1.4, sheets=[img_sheet(5016, 2823, turn_tags(3))], dials=dials(opened(3, {3: {"turn_on": "four", "turn_dur": 0.8}})), sfx=[{"kind": "tick", "on": "four"}]),
    "A2.24b": W_(base="p09", cam=[[0.5, 0.5, 1.02], [0.58, 0.55, 1.12]],
                 overs=[W_(t="tags", items=["$18"], at_on=["Eighteen"], x=0.76, y=0.3, w=230, size=100)]),
    "A2.24c": W_(base="s01", cam=[[0.4, 0.4, 1.4], [0.36, 0.34, 1.8]]),
    "A2.25a": W_(base="p01", cardcam=True, cam=[[0.45, 0.58, 1.6], [0.43, 0.57, 1.9]], sfx=[{"kind": "paper", "at": 0.1}],
                 sheets=[card_sheet(P01_CARD["journal_tilt"], ["TVERSKY & KAHNEMAN · 1981", "\"The Framing of Decisions and", "the Psychology of Choice\"", "Science 211"], hl="Science 211")]),
    "A2.25b": W_(base="a2_calculators", cam=[[0.5, 0.5, 1.0], [0.5, 0.5, 1.04]]),
    "A2.25c": W_(base="a2_calculators", cam=[[0.36, 0.5, 1.4], [0.35, 0.5, 1.5]],
                 sheets=[img_sheet(5016, 2823, [{"k": "route", "d": "M 500 1150 C 900 600, 1500 600, 1850 1000", "w": 14, "at_on": "drive", "col": INK}, T("20 MIN", 1180, 620, 110, col=INK),
                                                T("$15", 250, 2140, 120, at_on="fifteen", col=INK)])]),
    "A2.25d": W_(base="a2_calculators", cam=[[0.62, 0.5, 1.45], [0.6, 0.5, 1.35]],
                 sheets=[img_sheet(5016, 2823, [T("$15", 250, 2140, 120, static=True, col=INK), T("$125", 2200, 2120, 120, at_on="hundred", col=INK)])],
                 overs=[W_(t="tags", items=["68% DRIVE"], at=[0.3], x=0.22, y=0.12, w=420, size=70, color=GREEN),
                        W_(t="tags", items=["29% DRIVE"], at_on=["one"], x=0.75, y=0.12, w=420, size=70)]),
    "A2.25e": W_(base="a2_calculators", cam=[[0.42, 0.56, 1.2], [0.4, 0.58, 1.3]],
                 overs=[W_(t="note", text="$5 = $5", size=110, color=INK, write_on="Five#3", x=0.38, y=0.22)]),
    "A2.25f": W_(base="a2_safe", cam=dial_cam(3, 2.55, 2.6), dur=CLICK, quick=True, dials=dials(opened(3, {3: {"turn_": -2.0, "open_on": "so"}})),
                 sfx=[{"kind": "kachunk", "on": "so"}]),
    "A2.J5": W_(base="p10", cam=[[0.38, 0.4, 1.3], [0.36, 0.38, 1.5]],
                sheets=[W_(q=P10, W=700, H=400, color=INK, items=[T("MONDAY", 160, 62, 46, at_on="thinks", col=INK), T("GYM", 150, 175, 80, at_on="gym", col=INK),
                                                                 L("M 40 132 L 270 160", w=16, col=RED)])]),
    "A2.26a": W_(base="a2_lookout", cam=[[0.35, 0.5, 1.05], [0.32, 0.5, 1.2]]),
    "A2.26b": W_(base="s04", cam=[[0.42, 0.42, 1.05], [0.42, 0.41, 1.3]], dial_time="8:18"),
    "A2.27a": W_(base="a2_safe", cam=[[0.4, 0.5, 1.05], [0.42, 0.5, 1.22]], dur=3.4, door=W_(box=[790, 439, 3185, 2295], hinge="right", at_on="click", dur=1.2),
                 sfx=[{"kind": "kachunk", "on": "click"}]),
    "A2.27b": W_(base="s02", cam=[[0.516, 0.51, 1.74], [0.516, 0.51, 1.88]],
                 screen=W_(mode="fees", fees=[W_(name="SERVICE FEE", amt="$8"), W_(name="FACILITY FEE", amt="$6"), W_(name="PROCESSING", amt="$4")])),
    "A2.28a": W_(base="s01", cam=[[0.84, 0.36, 2.9], [0.84, 0.37, 3.05]],
                 insets=[W_(video="x1", q=[[4150, 880], [4730, 880], [4730, 1240], [4150, 1240]], crop=[460, 110, 1880, 985], frame=True)]),
    "A2.28b": W_(base="p01", cardcam=True, cam=[[0.5, 0.8, 1.9], [0.5, 0.84, 2.3]], sfx=[{"kind": "paper", "at": 0.1}],
                 sheets=[card_sheet(P01_CARD["front_centre"], ["NBER w25186 · p. 27", "1 SEPTEMBER 2015: the whole", "site switched to fees at", "the end, for everyone"], hl="fees at")]),
    "A2.29": W_(base="a12clip", cam=[[0.5, 0.5, 1.02], [0.5, 0.5, 1.1]]),
    "A2.30": W_(base="p01", cam=[[0.75, 0.75, 1.8], [0.76, 0.75, 2.0]],
                sheets=[W_(q=[[2980, 1980], [4320, 1960], [4500, 2700], [2900, 2720]], W=612, H=662, color=INK,
                           items=[{"k": "prop", "src": "v2/props/sub_casefiles.png", "x": 306, "y": 331, "w": 612, "h": 662, "static": True}])],
                overs=[W_(t="note", text="SUBSCRIBE", size=96, write_on="subscribe", x=0.12, y=0.22)]),
    "A2.31": W_(base="arch_coop", cam=[[0.75, 0.5, 1.0], [0.4, 0.5, 1.12]], caption="Hotel sign, Cooperstown, New York, 1937 · " + LIB),
}
KLOT_A2 = {"a2_safe": "ep04v2_a2_safe", "a2_mug": "ep04v2_a2_mug", "a2_calculators": "ep04v2_a2_calculators", "a2_lookout": "ep04v2_a2_lookout",
           "g06": "ep04v2_g06_diet", "p01": "ep04v2_p01_journal_desk", "p03": "ep04v2_p03_shoppers_bags", "p04": "ep04v2_p04_two_laptops",
           "p06": "ep04v2_p06_crowd_with_larry", "p07": "ep04v2_p07_dollars_walk_out", "p08": "ep04v2_p08_tired_larry", "p09": "ep04v2_p09_scale",
           "p10": "ep04v2_p10_wall_calendar", "arch_concert": "ep04v2_arch_concert_1941", "arch_coop": "ep04v2_arch_cooperstown_1937"}
EP4_A2 = {"a12": "a12", "a10": "a10"}
CLIPS_A2 = {"a12clip": "a12"}
# R48: archive pictures with their real year (the archive_era check compares it with the years spoken in the line)
ARCHIVE_YEAR = {"arch_loews": 1939, "arch_briggs": 1942, "arch_concert": 1941, "arch_coop": 1937, "arch_radiocrowd": 1942, "arch_a2": 1939, "arch_a2b": 1942}
