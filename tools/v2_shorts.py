"""Ep.4 v2 Shorts (Klot picked 1, 2, 3, 5, 6, 7, 10): 9:16, <= 45 s, the strongest frame first, the last line leading back to
the first (a loop), the 4:5 picture band (70 % of the height), every R-rule of the long video.
Each Short: lines of the episode (voice cut from the episode's own narration, re-spaced), the opener (the first shot's
picture replaced by the Short's strongest frame) and 9:16 overrides for shots whose 16:9 layout cannot live in the band
(two laptops side by side, wide desk cards, both calculators at once)."""
from v2_preview_a2 import GREEN, INK, P10, RED, TAG, L, T, W_, dials, img_sheet, opened  # noqa: F401

GAP = 0.35  # between two lines that were not next to each other in the episode


def MUG_TAGS(static):
    a = {"static": True} if static else {}
    return [TAG("SELL $7.12", 3250, 1050, 560, 200, 110, col=RED, arrow=[2760, 1420], **(a or {"at": 0.1})),
            TAG("BUY $2.87", 3250, 1450, 560, 200, 110, col=GREEN, **(a or {"at_on": "others"}))]


DIALS_TURN1 = dials(opened(1, {1: {"turn_on": "two", "turn_dur": 0.8}}))


def card(lines, hl=None, at=0.15, y=0.42):
    """a typed card big enough for a phone (cap height >= 2.8 % of the band), lines <= 24 characters"""
    return W_(t="card", lines=lines, hl=hl, x=0.5, y=y, w=1660, size=110, at=at, rot=-1.0, read=True)


SHORTS = [
    W_(key="sh1", title="The $18 heist", ru="Ограбление на $18",
       beats=["COLD.1", "COLD.2", "COLD.3", "COLD.4", "COLD.5", "COLD.6", "COLD.7"],
       opener=W_(base="s03", cam=[[0.511, 0.52, 1.6], [0.511, 0.52, 1.7]], screen=W_(mode="total", total="$48", total_=-1.0))),
    W_(key="sh2", title="A fee for charging you a fee", ru="Плата за то, что с вас берут плату",
       # Klot r7: opens on "Service fee: eight dollars — for the service of charging you a fee." ("8:18. Next screen." cut);
       # the first frame shows Larry's whole face; the +60% stamp >= 6 % inside the frame
       beats=["A1.11>Service", "A1.J3", "A1.12", "A1.13", "A1.14"],
       opener=W_(base="s05", cam=[[0.36, 0.45, 1.04], [0.36, 0.45, 1.0]],
                 # Klot r7: the whole face, the three fee tags in a row on the jacket below it (Nov 7: bigger)
                 overs=[W_(t="tags", items=[x], at=[0.0], x=cx, y=0.72, w=300, size=140, big=True) for x, cx in (("+$8", 0.2), ("+$6", 0.5), ("+$4", 0.8))]),
       overrides={
           # Klot (Nov 7): the gulp's fee tags bigger (they were small in the top-right)
           "A1.J3b": W_(base="s05", cut_on="process#2", cam=[[0.5, 0.45, 1.02], [0.5, 0.42, 1.14]],
                        overs=[W_(t="tags", items=["+$8", "+$6", "+$4"], at=[0.0, 0.0, 0.0], x=0.83, y=0.1, w=340, size=150, big=True)]),
           # Klot (Nov 7): the 4 s navy $48 card becomes the split-flap board $30 -> $48, on screen <= 1.5 s; it lands on
           # "forty-eight" and the gulp takes over (the rest of the line runs under it)
           "A1.12": W_(base="key", key="$48", sub="TOTAL", at=0.0, flap=W_(frm="$30", at=0.3), start_on="forty-eight", start_lead=0.2, max_len=1.5,
                       sfx=[{"kind": "kachunk", "at": 0.3}, {"kind": "stab", "on": "forty-eight"}]),
           # the gulp clip fills the band with his face: the +60% stamp lands in the space beside the face (Nov 7: off the hat);
           # the camera drifts right with the face so that space stays clear
           "A1.13": W_(base="m1", cam=[[0.5, 0.5, 1.0], [0.62, 0.5, 1.0]],
                       overs=[W_(t="stamp", text="+60%", at_on="sixty", x=0.825, y=0.6, size=105, paper=True)], sfx=[{"kind": "stamp", "on": "sixty"}])}),
    W_(key="sh3", title="StubHub's 12-day experiment", ru="12-дневный эксперимент StubHub",
       beats=["A2.7", "A2.9", "A2.10", "A2.12", "A2.14"],
       opener=W_(base="a5", cam=[[0.3, 0.45, 1.25], [0.3, 0.45, 1.32]],
                 overs=[W_(t="tags", items=["≈21% MORE SPENT"], at=[0.0], x=0.5, y=0.64, w=900, size=104, color=GREEN),
                        W_(t="plate", text="AUGUST 2015 · STUBHUB", at_on="August", x=0.5, y=0.07)]),
       overrides={"A2.9a": W_(base="a5", cam=[[0.5, 0.5, 1.0], [0.5, 0.5, 1.06]],
                              sheets=[img_sheet(1376, 768, [TAG("A", 560, 160, 130, 110, 92, at_on="split"), TAG("B", 820, 160, 130, 110, 92, at_on="split")])]),
                  "A2.10a": W_(base="a5", cam=[[0.5, 0.45, 1.15], [0.5, 0.45, 1.28]],
                               sheets=[img_sheet(1376, 768, [TAG("A · FULL PRICE", 688, 150, 300, 70, 40, at_on="full"),
                                                             TAG("B · TICKET ONLY", 688, 240, 320, 70, 40, at_on="other")])]),
                  "A2.14b": W_(base="a5", cam=[[0.3, 0.45, 1.25], [0.3, 0.45, 1.32]], cut_on="twenty-one",
                               overs=[W_(t="tags", items=["≈21% MORE SPENT"], at_on=["twenty-one"], x=0.5, y=0.64, w=900, size=104, color=GREEN)]),
                  "A2.12": W_(base="a5", cam=[[0.72, 0.5, 1.35], [0.78, 0.52, 1.45]],
                              overs=[W_(t="tags", items=["+14%"], at_on=["fourteen"], x=0.5, y=0.08, w=300, size=110, color=GREEN)],
                              sfx=[{"kind": "pop", "on": "fourteen"}]),"A2.9b": W_(base="s02", cam=[[0.511, 0.5, 1.45], [0.511, 0.5, 1.6]],
                              screen=W_(mode="allin", price="$48", sub="FEES INCLUDED", head="CHECKOUT A"))}),
    W_(key="sh5", title="Same mug, twice the price", ru="Та же кружка — вдвое дороже",
       beats=["A2.22"],  # Klot r7: opens on "In a famous 1990 experiment…" ("Lock two:" and its line cut); ends "It was just theirs."
       opener=W_(base="a2_mug", cam=[[0.57, 0.52, 1.3], [0.58, 0.52, 1.38]], sheets=[img_sheet(5016, 2823, MUG_TAGS(True))]),
       overrides={"A2.22c": W_(base="a2_mug", cam=[[0.56, 0.52, 1.25], [0.58, 0.52, 1.38]], sheets=[img_sheet(5016, 2823, MUG_TAGS(False))]),
                  # Klot r7: it ends close on the mug's two prices, so the loop back to the opening frame is seamless
                  "A2.22d": W_(base="a2_mug", cam=[[0.63, 0.42, 1.6], [0.63, 0.42, 1.7]], sheets=[img_sheet(5016, 2823, MUG_TAGS(True))])}),
    W_(key="sh6", title="$5 is $5. Your brain disagrees", ru="$5 — это $5. Мозг не согласен",
       beats=["A2.25"],  # Klot r7: opens on "Psychologists showed this back in 1981…"; ends "Your brain doesn't think so." (Lock four and the DECIDED shot cut)
       opener=W_(base="a2_calculators", cam=[[0.2, 0.55, 1.2], [0.2, 0.55, 1.28]],
                 sheets=[img_sheet(5016, 2823, [TAG("$15", 840, 1350, 330, 210, 150, col=INK, static=True),
                                                TAG("68% DRIVE", 840, 1650, 620, 190, 110, col=GREEN, static=True)])]),
       overrides={
           "A2.25c": W_(base="a2_calculators", cam=[[0.2, 0.52, 1.1], [0.18, 0.52, 1.18]],
                        sheets=[img_sheet(5016, 2823, [TAG("$15", 840, 1350, 330, 210, 150, col=INK, at_on="fifteen"),
                                                       TAG("68% DRIVE", 840, 1650, 620, 190, 110, col=GREEN, at_on="calculator")])]),
           "A2.25d": W_(base="a2_calculators", cam=[[0.65, 0.48, 1.1], [0.66, 0.47, 1.2]],
                        sheets=[img_sheet(5016, 2823, [TAG("$125", 3250, 900, 420, 210, 150, col=INK, at_on="hundred"),
                                                       TAG("29% DRIVE", 3250, 1230, 620, 190, 110, col=RED, at_on="hundred")])]),
           "A2.J5": W_(base="p10", cam=[[0.27, 0.4, 1.3], [0.26, 0.38, 1.45]],
                       sheets=[W_(q=P10, W=700, H=400, color=INK, items=[T("MONDAY", 160, 62, 46, at_on="thinks", col=INK), T("GYM", 150, 175, 80, at_on="gym", col=INK),
                                                                        L("M 40 132 L 270 160", w=16, col=RED)])]),
           # Klot r7: it ends on the $125 calculator and its tags, then loops to the $15 one
           "A2.25f": W_(base="a2_calculators", dur=1.6, cam=[[0.64, 0.5, 1.0], [0.64, 0.5, 1.05]],
                        sheets=[img_sheet(5016, 2823, [TAG("$125", 3250, 900, 420, 210, 150, col=INK, static=True),
                                                       TAG("29% DRIVE", 3250, 1230, 620, 190, 110, col=RED, static=True)])]),
           "A2.25e": W_(base="a2_calculators", cam=[[0.42, 0.62, 1.05], [0.42, 0.64, 1.1]],
                        overs=[W_(t="note", text="$5 = $5", size=130, color=INK, write_on="Five#3", x=0.3, y=0.24)]),
       }),
    W_(key="sh7", title="The resort fee lineup", ru="Опознание курортного сбора",
       beats=["A3.4", "A3.5", "A3.6"],  # Klot r7: opens on "Name: the resort fee."; ends "Larry will pay for all of it."
       opener=W_(base="a3_lineup", cam=[[0.5, 0.42, 1.02], [0.5, 0.41, 1.1]],
                 sheets=[img_sheet(5016, 2823, [TAG("THE RESORT FEE", 2508, 420, 1100, 230, 150, col=RED, static=True)])],
                 overs=[W_(t="stamp", text="SUSPECT", at_on="resort", x=0.5, y=0.3, size=90, paper=True)], sfx=[{"kind": "stamp", "on": "resort"}]),
       overrides={"A3.2b": W_(base="s03", cam=[[0.511, 0.52, 1.5], [0.511, 0.53, 1.66]], cut_on="booking",
                              screen=W_(mode="bill", head="HOTEL · 1 NIGHT", big="$99", sub="/ NIGHT",
                                        rows=[W_(name="TAXES AND FEES", amt="$50", at_on="line", hl=True, hl_on="Taxes")]),
                              sfx=[{"kind": "pop", "on": "line"}]),
                  # 9:16: the lobby clip ends close on Larry; the two tags sit left of him, clear of his face
                  "A3.6": W_(base="m8", cam=[[0.5, 0.5, 1.0], [0.5, 0.5, 1.03]],
                             overs=[W_(t="tags", items=["USES: NONE"], at_on=["none"], x=0.27, y=0.46, w=440, size=74, color=GREEN),
                                    W_(t="tags", items=["PAYS: ALL OF IT"], at_on=["all"], x=0.29, y=0.56, w=480, size=74)]),
                  "A3.4b": W_(base="a3_lineup", cam=[[0.5, 0.31, 1.5], [0.5, 0.3, 1.6]],
                              sheets=[img_sheet(5016, 2823, [TAG("THE RESORT FEE", 2508, 420, 1100, 230, 150, col=RED, static=True),
                                                             T("AMENITY FEE", 2508, 640, 105, at_on="Aliases", col=INK), T("DESTINATION FEE", 2508, 755, 105, col=INK)])])}),
    W_(key="sh10", title="Three checks before you press Pay", ru="Три проверки перед кнопкой «Оплатить»",
       beats=["A4.13", "A4.14", "A4.15", "A4.16"],
       opener=W_(base="s03", cam=[[0.511, 0.52, 1.5], [0.511, 0.5, 1.6]],
                 screen=W_(mode="bill", tabn=2, active=1, head="SATURDAY · 8 PM", big="$48", big_col=GREEN, sub="ALL-IN",
                           toggle=W_(label="SHOW PRICES\nWITH FEES", state=1, y=40, size=54))),
       overrides={"A4.15a": W_(base="s03", cam=[[0.511, 0.53, 1.55], [0.511, 0.55, 1.72]],
                               screen=W_(mode="bill", head="LAST SCREEN", rows_top=120, pay=True,
                                         rows=[W_(name="TICKET · ROW G", amt="$30"), W_(name="FEES", amt="$18"), W_(name="TOTAL", amt="$48", hl=True, hl_on="last")])),
                  "A4.15b": W_(base="s01", cam=[[0.38, 0.35, 1.5], [0.36, 0.33, 1.7]],
                               overs=[W_(t="plate", text="8:14 · CHECK 2", at=0.15, x=0.5, y=0.07), W_(t="note", text="LAST SCREEN", size=92, write_on="real", x=0.55, y=0.24)]),
                  "A4.16a": W_(base="p04", cam=[[0.25, 0.4, 1.3], [0.25, 0.4, 1.38]], overs=[W_(t="plate", text="8:15 · CHECK 3", at=0.15, x=0.5, y=0.06)],
                               screen=W_(mode="bill", head="TICKET A", big="$40", sub="NO FEES", fs={"os": 80, "row": 92, "big": 200, "sub": 80})),
                  "A4.16b": W_(base="p04", cam=[[0.75, 0.4, 1.3], [0.75, 0.4, 1.38]],
                               screen=W_(mode="bill", head="TICKET B", big="$30", big_col=RED, fs={"os": 80, "row": 92, "big": 200, "sub": 80}, rows_top=345,
                                         rows=[W_(name="+ FEES", amt="$18", col=RED), W_(name="= TOTAL", amt="$48", hl=True, at_on="eighteen")]))}),
]


def short_T(T: dict, voice, ids: list[str], sr: int = 24000):
    """A Short's own timeline: its lines placed back to back (their own pauses kept when they were neighbours in the
    episode), the voice cut from the episode's narration accordingly. Returns (T, voice)."""
    import json

    import numpy as np
    order = [b["id"] for b in T["beats"]]
    src = {b["id"]: b for b in T["beats"]}
    # Klot r7: "A1.11>Service" = that line from its word "Service" on (an existing take, cut in the pause before the word)
    trimmed = [x for x in ids if ">" in x]
    ids = [x.split(">")[0] for x in ids]
    for x in trimmed:
        bid, w0 = x.split(">")
        b = json.loads(json.dumps(src[bid]))
        ws = b["words"]
        i = next(j for j, w in enumerate(ws) if w[0].startswith(w0))
        cut = (ws[i - 1][2] + ws[i][1]) / 2 if i and ws[i][1] - ws[i - 1][2] > 0.1 else max(0.0, ws[i][1] - 0.03)
        b["words"] = [[w, round(a - cut, 3), round(z - cut, 3)] for w, a, z in ws[i:]]
        b["start"] = round(b["start"] + cut, 3)
        b["text"] = " ".join(w[0] for w in b["words"])
        for k in ("heard", "diff", "takes"):
            b.pop(k, None)
        src[bid] = b
    R = json.loads(json.dumps(T))
    beats, t, pos = [], 0.45, {}
    for k, bid in enumerate(ids):
        b = src[bid]
        s = t
        e = s + (b["end"] - b["start"])
        pos[bid] = (s, b["start"])
        beats.append(dict(json.loads(json.dumps(b)), start=round(s, 3), end=round(e, 3)))
        if k + 1 < len(ids):
            nxt = ids[k + 1]
            t = e + ((src[nxt]["start"] - b["end"]) if order.index(nxt) == order.index(bid) + 1 else GAP)
    total = beats[-1]["end"] + 0.4
    out = np.zeros(int((total + 0.5) * sr), np.float32)
    for b in beats:
        s_new, s_old = pos[b["id"]]
        i0, n = int(round(s_old * sr)), int(round((b["end"] - b["start"]) * sr))
        j0 = int(round(s_new * sr))
        out[j0:j0 + n] = voice[i0:i0 + n][: len(out) - j0]
    R["beats"] = beats
    R["hits"] = [dict(h, at=round(h["at"] - pos[h["line"]][1] + pos[h["line"]][0], 3),
                      **({"silence_from": round(h["silence_from"] - pos[h["line"]][1] + pos[h["line"]][0], 3)} if "silence_from" in h else {}))
                 for h in T["hits"] if h["line"] in pos]
    for h in R["hits"]:  # a brass hit keeps its full second of silence (the last picture holds through it, then the loop)
        s0 = max(h["at"] + T.get("hit_len", 0.0), h.get("silence_from", 0.0))
        total = max(total, s0 + 1.0 + 0.05)
    R["total"] = round(total, 3)
    out = np.pad(out, (0, max(0, int((total + 0.5) * sr) - len(out))))
    act = beats[0]["act"]
    R["acts"] = [dict(next(a for a in T["acts"] if a["act"] == act), start=0.0)]
    R["breaks"] = []
    return R, out
