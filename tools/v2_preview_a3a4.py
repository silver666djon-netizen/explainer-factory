"""Ep.4 v2 · Act 3 (The Gang) and Act 4 (The Cops and the Escape) shot specs for the Remotion preview layer — picture-first
(R41-R48), same vocabulary as v2_preview.py / v2_preview_a2.py. Every Ep.4 object on plain cream from the scene list (c4 bill,
m2 mugshot, l2 ticket, l13 form, x1 switch, sub, the d5 archive, next_tablet) is replaced by Klot's stills / a place
(plain_background); document cards mirror the narration only (no invented quotes); every lawsuit line carries ALLEGED.
Archive photos: none in Acts 3-4 (R48: no 1940s photo under a 2019-2026 event)."""
from v2_preview_a2 import (CARD, CARD_AT, GREEN, INK, L, P01_CARD, RED, SAFE, T, TAG, W_, card_sheet, dials, img_sheet,  # noqa: F401
                           opened)

CHALK = "#FBFAF5"
P04FS = {"os": 80, "row": 92, "big": 200, "sub": 80}
HOTEL = W_(head="HOTEL DOWNTOWN · 1 NIGHT", big="$99", sub="/ NIGHT")
X1_INSET = dict(video="x1", q=[[4110, 890], [4830, 890], [4830, 1335], [4110, 1335]], crop=[460, 110, 1880, 985], frame=True)
LINEUP_TAG = TAG("THE RESORT FEE", 2508, 420, 1100, 230, 150, col=RED)
RACE_INK = [T("HONEST", 795, 1050, 150, col=INK), T("$40", 795, 1310, 170, col=INK), T("$30", 2821, 1250, 150, col=INK)]
STICKER = [[578, 250], [1005, 250], [1005, 540], [578, 540]]  # the blank window sticker of Ep.4 l5 (px of the 1376 x 768 still)
MAP_TO_UK = "M 1300 1700 C 2200 900, 3300 700, 4150 900"
MAP_TO_US = "M 4150 980 C 3300 1300, 2300 1500, 1350 1780"


def static(items):
    return [dict(i, static=True) for i in items]


A3 = {
    # ---------------------------------------------------------------- the hotel
    "A3.1a": W_(base="c1clip", cam=[[0.5, 0.5, 1.02], [0.5, 0.48, 1.1]], title=["ACT 3", "THE GANG"]),
    "A3.1b": W_(base="c1", cam=[[0.16, 0.24, 2.1], [0.17, 0.23, 2.3]], cut_on="Downtown"),
    "A3.2a": W_(base="a1_glow", cam=[[0.45, 0.42, 1.08], [0.42, 0.4, 1.2]],
                overs=[W_(t="tags", items=["$99 A NIGHT"], at_on=["ninety-nine"], x=0.8, y=0.14, w=500, size=84, color=GREEN)]),
    "A3.2b": W_(base="s03", cam=[[0.511, 0.52, 1.5], [0.511, 0.53, 1.66]], cut_on="booking",
                screen=W_(mode="bill", **HOTEL, rows=[W_(name="TAXES AND FEES", amt="$50", at_on="line", hl=True, hl_on="Taxes")]),
                sfx=[{"kind": "pop", "on": "line"}]),
    "A3.3": W_(base="s03", cam=[[0.5, 0.56, 1.66], [0.5, 0.58, 1.86]],
               screen=W_(mode="bill", head="TAXES AND FEES · $50", fs={"row": 58}, rows_top=130,
                         rows=[W_(name="CITY TAX", amt="$9", at_on="real"), W_(name="STATE TAX", amt="$6", at_on="taxes"),
                               W_(name="RESORT FEE", amt="$35", at_on="second", dim=True)]),
               sfx=[{"kind": "pop", "on": "second"}]),
    "A3.4a": W_(base="m7", cam=[[0.5, 0.5, 1.0], [0.5, 0.5, 1.0]], track="ep04v2_m7_lineup",  # Klot r6 motion: m7 lineup lights (Grok)
                sheets=[img_sheet(5016, 2823, [dict(LINEUP_TAG, at_on="Name")])],
                overs=[W_(t="stamp", text="SUSPECT", at_on="resort", x=0.2, y=0.15, size=90, paper=True)], sfx=[{"kind": "stamp", "on": "resort"}]),
    "A3.4b": W_(base="a3_lineup", cam=[[0.5, 0.31, 1.5], [0.5, 0.3, 1.6]],
                sheets=[img_sheet(5016, 2823, [dict(LINEUP_TAG, static=True), T("AMENITY FEE", 1450, 610, 120, at_on="Aliases", col=INK),
                                               T("DESTINATION FEE", 3120, 780, 120, col=INK)])]),
    "A3.5a": W_(base="m2bclip", cam=[[0.5, 0.5, 1.02], [0.5, 0.52, 1.1]],
                overs=[W_(t="tags", items=["POOL"], at_on=["pool"], x=0.78, y=0.12, w=300, size=96)]),
    "A3.5b": W_(base="g02", cam=[[0.4, 0.5, 1.05], [0.42, 0.5, 1.15]],
                overs=[W_(t="tags", items=["GYM"], at_on=["gym"], x=0.78, y=0.14, w=260, size=96)]),
    "A3.5c": W_(base="s01", cam=[[0.42, 0.4, 1.3], [0.44, 0.4, 1.45]],
                sheets=[img_sheet(5016, 2823, [TAG("WI-FI", 2420, 980, 440, 190, 130, col=RED, at_on="Wi-Fi", arrow=[2440, 1330])])]),
    "A3.5d": W_(base="g03", cam=[[0.55, 0.62, 1.3], [0.55, 0.64, 1.42]],
                overs=[W_(t="tags", items=["NEWSPAPER", "UNREAD SINCE 1998"], at_on=["newspaper", "1998"], x=0.3, y=0.12, w=640, size=78)]),
    "A3.J6": W_(base="g02", cam=[[0.3, 0.36, 1.5], [0.28, 0.35, 1.65]],
                sheets=[img_sheet(5016, 2823, [TAG("MONDAY: GYM", 700, 820, 660, 210, 120, col=INK, at_on="Monday"),
                                               TAG("+ A FEE", 700, 1090, 420, 190, 120, col=RED, at_on="fee")])]),
    "A3.6": W_(base="m8", cam=[[0.5, 0.5, 1.0], [0.5, 0.5, 1.03]],  # Klot r6 motion: m8 lobby (Grok, from c1)
               overs=[W_(t="tags", items=["USES: NONE"], at_on=["none"], x=0.78, y=0.14, w=500, size=78, color=GREEN),
                      W_(t="tags", items=["PAYS: ALL OF IT"], at_on=["all"], x=0.78, y=0.32, w=560, size=78)]),
    # ---------------------------------------------------------------- Marriott (allegations; R48: our world + typeset cards)
    "A3.7a": W_(base="g03", cam=[[0.5, 0.45, 1.02], [0.48, 0.45, 1.12]],
                overs=[W_(t="card", lines=["D.C. ATTORNEY GENERAL", "v. MARRIOTT", "LAWSUIT · 2019"], x=0.32, y=0.34, w=760, size=50, at=0.2)]),
    "A3.7b": W_(base="g03", cardcam=True, sfx=[{"kind": "paper", "at": 0.1}],  # Klot r6: a clipping on the corridor carpet
                sheets=[card_sheet(CARD_AT["corridor"], ["D.C. ATTORNEY GENERAL v.", "MARRIOTT · JULY 2019", "at least 189 hotels"], hl="189", style="clip")]),
    "A3.7c": W_(base="g03", cam=[[0.62, 0.6, 1.6], [0.64, 0.62, 1.75]],
                overs=[W_(t="tags", items=["189 HOTELS"], at_on=["eighty-nine"], x=0.3, y=0.12, w=520, h=250, size=96,
                          stamp=W_(text="ALLEGED", at_on="charged", size=74))], sfx=[{"kind": "stamp", "on": "charged"}]),
    "A3.7d": W_(base="m2b", cam=[[0.5, 0.55, 1.1], [0.52, 0.56, 1.2]],
                overs=[W_(t="tags", items=["$9 TO $95", "PER ROOM, PER DAY"], at_on=["nine", "per"], x=0.72, y=0.12, w=640, size=80)]),
    "A3.8": W_(base="s03", cam=[[0.511, 0.55, 1.6], [0.5, 0.56, 1.76]],
               screen=W_(mode="bill", head="TAXES AND FEES · $50", fs={"row": 58}, rows_top=130,
                         rows=[W_(name="CITY TAX", amt="$9"), W_(name="STATE TAX", amt="$6"),
                               W_(name="RESORT FEE", amt="NOT A TAX", col="#8A2416", hl=True, hl_on="aren't")])),
    "A3.9a": W_(base="p01", cardcam=True, sfx=[{"kind": "paper", "at": 0.1}],
                sheets=[card_sheet(P01_CARD["front_left"], ["TEXAS ATTORNEY GENERAL", "& MARRIOTT · 2023", "show the total price", "most prominently"],
                                   hl="most prominently")]),
    "A3.9b": W_(base="g01", cam=[[0.5, 0.45, 1.1], [0.52, 0.44, 1.25]], grade="dusk", cut_on="Same", plan=W_(mode="static")),
    # ---------------------------------------------------------------- Ticketmaster (allegations)
    "A3.10": W_(base="p12", cam=[[0.5, 0.7, 1.25], [0.5, 0.42, 1.25]]),
    "A3.11a": W_(base="a3_courtroom", cam=[[0.2, 0.4, 1.7], [0.22, 0.4, 1.85]],
                 overs=[W_(t="card", lines=["FTC + 7 STATES", "v. LIVE NATION", "& TICKETMASTER", "SEPTEMBER 2025"], x=0.68, y=0.4, w=700, size=50, at=0.2)]),
    "A3.11b": W_(base="a3_courtroom", cardcam=True, sfx=[{"kind": "paper", "at": 0.1}, {"kind": "stamp", "on": "sued"}],  # Klot r6: a court document on the bench
                 sheets=[card_sheet(CARD_AT["bench"], style="court", lines= ["FTC + 7 STATES v.", "LIVE NATION / TICKETMASTER", "lawsuit · Sept 2025", "ALLEGED, not proven"],
                                    hl="ALLEGED", at_on="sued")],
                 overs=[W_(t="stamp", text="FILED", at_on="sued", x=0.76, y=0.68, size=90)]),
    "A3.12a": W_(base="p01", cardcam=True, sfx=[{"kind": "paper", "at": 0.1}],
                 sheets=[card_sheet(P01_CARD["right"], ["FTC COMPLAINT · ALLEGED", "fees run 24% to 44%", "of the total price"], hl="24% to 44%")]),
    "A3.12b": W_(base="key", key="$16.4BN", sub="MANDATORY FEES · ALLEGED", at=0.05, cut_on="sixteen"),
    "A3.J7": W_(base="p06", cam=[[0.5, 0.5, 1.02], [0.5, 0.52, 1.1]],
                sheets=[img_sheet(5016, 2823, [TAG("$18", int(5016 * x), y, 300, 190, 150, col=RED, at=0.25 + 0.3 * i)
                                               for i, (x, y) in enumerate([(0.16, 1420), (0.33, 1690), (0.5, 1420), (0.67, 1690), (0.84, 1420)])]
                                    + [TAG("ALLEGED", 2508, 2060, 520, 180, 120, col=INK, at=0.2)])]),
    "A3.13a": W_(base="o4", cam=[[0.45, 0.35, 1.2], [0.43, 0.33, 1.32]],
                 overs=[W_(t="tags", items=["$18 OF $48"], at_on=["eighteen"], x=0.8, y=0.14, w=520, size=84)]),
    "A3.13b": W_(base="p01", cardcam=True, sfx=[{"kind": "paper", "at": 0.1}],
                 sheets=[card_sheet(P01_CARD["front_left"], ["ALLEGED RANGE: 24% - 44%", "LARRY: $18 of $48", "= 37.5%, inside it"], hl="37.5%",
                                    at_on="Thirty-seven")]),
    "A3.14a": W_(base="a3_courtroom", cam=[[0.5, 0.5, 1.0], [0.5, 0.48, 1.08]]),
    "A3.14b": W_(base="a3_courtroom", cardcam=True, sfx=[{"kind": "paper", "at": 0.1}, {"kind": "stamp", "on": "goes"}],  # Klot r6: stamped court order
                 sheets=[card_sheet(CARD_AT["bench2"], ["COURT ORDER · SEPT 2026", "motion to dismiss:", "the case goes on"], style="court")],
                 overs=[W_(t="stamp", text="DENIED", at_on="goes", x=0.7, y=0.6, size=100),
                        W_(t="plate", text="ALLEGED · UNTIL A COURT DECIDES", at_on="Until", x=0.5, y=0.08)]),
    "A3.15": W_(base="m9", cam=[[0.5, 0.5, 1.0], [0.5, 0.5, 1.04]], title=["THE DEFENCE", "IN DEFENCE OF THE ACCUSED"], title_over=True,
                # Klot r6 motion: m9 gavel (Grok; its first frame held 1.9 s under the title, the strike at 4.0 s)
                sfx=[{"kind": "kachunk", "at": 0.05}, {"kind": "kachunk", "on": "defence"}, {"kind": "stamp", "at": 4.0}]),
    # ---------------------------------------------------------------- the race
    "A3.16a": W_(base="p01", cardcam=True, sfx=[{"kind": "paper", "at": 0.1}],
                 sheets=[card_sheet(P01_CARD["journal"], ["STUBHUB'S OWN ACCOUNT", "2014: switched to all-in", "prices, every fee upfront"], hl="all-in")]),
    "A3.16b": W_(base="s03", cam=[[0.511, 0.52, 1.5], [0.511, 0.52, 1.66]], cut_on="moved",
                 screen=W_(mode="allin", price="$40", sub="EVERY FEE SHOWN UPFRONT", head="ALL-IN PRICE")),
    "A3.17": W_(base="a3_race", cam=[[0.5, 0.5, 1.02], [0.52, 0.5, 1.1]]),
    "A3.18": W_(base="a3_race", cam=[[0.35, 0.42, 1.35], [0.34, 0.42, 1.45]],
                sheets=[img_sheet(5016, 2823, [dict(RACE_INK[0], at_on="honest"), RACE_INK[1], dict(RACE_INK[2], at_on="expensive")])]),
    "A3.J8a": W_(base="a3_race", cam=[[0.5, 0.5, 1.0], [0.5, 0.5, 1.04]], sheets=[img_sheet(5016, 2823, static(RACE_INK))]),
    "A3.J8b": W_(base="a3_race", cam=[[0.17, 0.45, 2.0], [0.18, 0.46, 2.15]], cut_on="Mystery", sheets=[img_sheet(5016, 2823, static(RACE_INK))],
                 overs=[W_(t="stamp", text="SOLVED", at_on="solved", x=0.7, y=0.3, size=120)], sfx=[{"kind": "stamp", "on": "solved"}]),
    "A3.19a": W_(base="k2", cam=[[0.5, 0.5, 1.0], [0.5, 0.5, 1.0]], track="ep04v2_k2_race", sheets=[img_sheet(5016, 2823, static(RACE_INK))]),
    "A3.19b": W_(base="a3_race", cam=[[0.31, 0.55, 1.6], [0.31, 0.56, 1.7]], sheets=[img_sheet(5016, 2823, static(RACE_INK))]),
    "A3.20": W_(base="a3_race", cam=[[0.38, 0.55, 1.35], [0.36, 0.58, 1.45]], sheets=[img_sheet(5016, 2823, static(RACE_INK))],
                pulse=W_(sweep=True, y=40, at=0.3, k=0.6), sfx=[{"kind": "whoosh", "at": 0.4}]),
}

A4 = {
    # ---------------------------------------------------------------- 1958
    "A4.1": W_(base="a4_police", cam=[[0.4, 0.5, 1.02], [0.36, 0.5, 1.14]], title=["ACT 4", "THE COPS AND THE ESCAPE"], pulse=W_(x=31, y=27, at=0.3, k=0.45)),
    "A4.2a": W_(base="l5", cam=[[0.56, 0.5, 1.45], [0.52, 0.5, 1.04]]),
    "A4.2b": W_(base="l5", cam=[[0.56, 0.55, 1.75], [0.56, 0.55, 1.9]],
                sheets=[W_(q=STICKER, W=500, H=340, color=INK, items=[T("PRICE", 250, 78, 54, at_on="price"), T("OPTIONS", 250, 152, 54, at_on="option"),
                                                                     T("DELIVERY", 250, 226, 54, at_on="delivery"), T("TOTAL", 250, 306, 62, col=RED)])]),
    "A4.3": W_(base="g07", cam=[[0.45, 0.5, 1.05], [0.45, 0.48, 1.15]],
               overs=[W_(t="tags", items=["1958 - 2025", "= 67 YEARS"], at_on=["Cars", "sixty-seven"], x=0.8, y=0.1, w=480, size=84)]),
    "A4.J9": W_(base="k6", cam=[[0.5, 0.5, 1.0], [0.5, 0.5, 1.06]]),
    # ---------------------------------------------------------------- the cops on both sides of the ocean
    "A4.4a": W_(base="a4_police", cam=[[0.3, 0.4, 1.6], [0.3, 0.38, 1.75]], pulse=W_(x=52, y=27, at=0.1, k=0.5)),
    "A4.4b": W_(base="k3", cut_on="cops", cam=[[0.5, 0.5, 1.0], [0.5, 0.5, 1.0]]),  # Klot r6: the first 2 s of k3 on "the cops finally showed up"
    "A4.4c": W_(base="p13", cam=[[0.5, 0.5, 1.02], [0.5, 0.5, 1.08]], cut_on="On",
                sheets=[img_sheet(5016, 2820, [TAG("USA", 1150, 1500, 380, 200, 150, col=INK, at_on="both"), TAG("UK", 4300, 470, 300, 200, 150, col=INK, at_on="ocean")])]),
    "A4.5a": W_(base="p13", cam=[[0.6, 0.4, 1.15], [0.64, 0.36, 1.35]],
                sheets=[img_sheet(5016, 2820, [TAG("UK", 4300, 470, 300, 200, 150, col=INK, static=True), {"k": "route", "d": MAP_TO_UK, "w": 16, "at_on": "Britain", "col": RED}])],
                overs=[W_(t="stamp", text="UK · APRIL 2025", at_on="April", x=0.55, y=0.56, size=80, paper=True)], sfx=[{"kind": "stamp", "on": "April"}]),
    "A4.5b": W_(base="p13", cardcam=True, sfx=[{"kind": "paper", "at": 0.1}],  # Klot r6: laid on the map, by Britain
                sheets=[card_sheet(CARD_AT["map"], ["UK · SINCE APRIL 2025", "the price must include", "every fee you can't avoid"], hl="every fee",
                                   at_on="price")]),
    "A4.6a": W_(base="l8", cam=[[0.5, 0.55, 1.05], [0.52, 0.56, 1.15]]),
    "A4.6b": W_(base="l8", cam=[[0.55, 0.55, 1.4], [0.57, 0.55, 1.52]],
                overs=[W_(t="tags", items=["£3 BOOKING FEE", "× 80,000 DRIVERS"], at_on=["three-pound", "eighty"], x=0.74, y=0.12, w=600, size=72)]),
    "A4.6c": W_(base="p01", cardcam=True, sfx=[{"kind": "paper", "at": 0.1}, {"kind": "stamp", "on": "fine"}],
                sheets=[card_sheet(P01_CARD["right"], ["CMA · UK", "£3 booking fee, hidden", "from 80,000+ learners", "fined £4.2m"], hl="fined £4.2m")],
                overs=[W_(t="stamp", text="£4.2M FINE", at_on="fine", x=0.75, y=0.31, size=80)]),
    "A4.J10": W_(base="g08", cam=[[0.4, 0.42, 1.1], [0.38, 0.42, 1.22]], pulse=W_(x=40, y=35, at=0.2, k=0.5)),
    "A4.6b/": W_(base="l8", cam=[[0.4, 0.5, 1.25], [0.38, 0.5, 1.36]],
                 overs=[W_(t="note", text="£3 = £4.2M", size=100, write_on="Three", x=0.58, y=0.24)]),
    "A4.7": W_(base="p13", start_on="StubHub's", cam=[[0.8, 0.3, 2.0], [0.82, 0.3, 2.15]], sheets=[img_sheet(5016, 2820, [TAG("UK", 4300, 470, 300, 200, 150, col=INK, static=True)])],
               overs=[W_(t="stamp", text="STUBHUB UK · FINED · JUNE 2026", at_on="StubHub's", x=0.4, y=0.62, size=62, paper=True)], sfx=[{"kind": "stamp", "on": "StubHub's"}]),
    "A4.8a": W_(base="p13", cam=[[0.5, 0.5, 1.04], [0.5, 0.5, 1.12]],
                sheets=[img_sheet(5016, 2820, [TAG("UK", 4300, 470, 300, 200, 150, col=INK, static=True), TAG("USA", 1150, 1500, 380, 200, 150, col=INK, static=True), {"k": "route", "d": MAP_TO_US, "w": 16, "at_on": "America", "col": RED}])],
                overs=[W_(t="stamp", text="USA · TOTAL UPFRONT · MAY 2025", at_on="May", x=0.5, y=0.72, size=60, paper=True)], sfx=[{"kind": "stamp", "on": "May"}]),
    "A4.8b": W_(base="s03", cam=[[0.511, 0.52, 1.36], [0.511, 0.53, 1.44]], cut_on="hotels",
                screen=W_(mode="bill", head="HOTEL DOWNTOWN · 1 NIGHT", big="$149", sub="TOTAL", sub2="TAXES AND FEES INCLUDED",
                          stamp=W_(text="TOTAL UPFRONT", at_on="total", x=800, y=500, size=84, rot=-8)), sfx=[{"kind": "stamp", "on": "total"}]),
    "A4.9a": W_(base="p01", cardcam=True, sfx=[{"kind": "paper", "at": 0.1}, {"kind": "stamp", "on": "million"}],
                sheets=[card_sheet(P01_CARD["front_centre"], ["FTC · APRIL 2026", "StubHub agrees to pay", "$10 million back to buyers"])],
                overs=[W_(t="stamp", text="$10M", at_on="million", x=0.74, y=0.72, size=110)]),
    "A4.9b": W_(base="a5", cam=[[0.5, 0.5, 1.02], [0.55, 0.5, 1.12]], cut_on="back"),
    "A4.10": W_(base="a5", cam=[[0.42, 0.45, 1.3], [0.4, 0.45, 1.4]], green_creep=True,
                overs=[W_(t="plate", text="AUG 2015 · THE REHEARSAL", at_on="rehearsal", x=0.5, y=0.08)]),
    "A4.11a": W_(base="s03", cam=[[0.511, 0.52, 1.62], [0.511, 0.53, 1.78]],
                 screen=W_(mode="fees", fees=[W_(name="SERVICE FEE", amt="$8"), W_(name="FACILITY FEE", amt="$6"), W_(name="PROCESSING", amt="$4")])),
    "A4.11b": W_(base="a10", cam=[[0.5, 0.55, 1.03], [0.5, 0.57, 1.12]], cut_on="Fees",
                 overs=[W_(t="tags", items=["CARD PAYMENTS", "STAFF", "THE VENUE"], at_on=["card", "staff", "venue"], x=0.5, y=0.1, w=560, size=78, color=GREEN)]),
    "A4.11c": W_(base="g01", cam=[[0.5, 0.46, 1.12], [0.5, 0.45, 1.24]], grade="dusk", cut_on="rules#2",
                 plan=W_(mode="static", extra=[T("TOTAL, UPFRONT", 500, 300, 64, at_on="only")])),
    # ---------------------------------------------------------------- the rewind: Tuesday, done right
    "A4.12a": W_(base="o4clip", cam=[[0.5, 0.48, 1.05], [0.52, 0.46, 1.12]], overs=[W_(t="plate", text="TUE · 8:19 PM", at=0.2, x=0.78, y=0.08)]),
    # Klot (Nov 7): the time jump 8:19 -> 8:12 is an iris (house transition 6) with the rewind sound: the iris closes on
    # 8:19 from "rewind", opens on the hands spinning back, landing on 8:12
    "A4.12b": W_(base="s04", cam=[[0.42, 0.42, 1.12], [0.42, 0.41, 1.3]], dial_time="8:12", cut_on="So",
                 iris=W_(at_on="rewind", dur=1.2), rewind={"from": "8:19", "at_on": "rewind", "delay": 0.5, "dur": 1.0},
                 sfx=[{"kind": "whoosh", "on": "rewind"}]),
    "A4.13a": W_(base="s01", cam=[[0.85, 0.41, 3.2], [0.85, 0.41, 3.35]],
                 insets=[dict(X1_INSET, from_on="switch", flip=3.95, plate=W_(box=[590, 112, 1300, 298], size=72, text="ALL-IN:\nOFF", text2="ALL-IN:\nON", swap_on="switch"))],
                 overs=[W_(t="plate", text="8:12 · CHECK 1", at=0.2, x=0.5, y=0.08)], sfx=[{"kind": "kachunk", "on": "switch", "lead": -0.25}]),
    "A4.13b": W_(base="s02", cam=[[0.511, 0.5, 1.45], [0.511, 0.5, 1.6]],
                 screen=W_(mode="bill", tabn=2, active=1, head="SATURDAY · 8 PM", big="$30", big_col=RED, sub="TICKET",
                           toggle=W_(label="SHOW PRICES\nWITH FEES", on_on="turns", y=40, size=50)), sfx=[{"kind": "tap", "on": "turns"}]),
    "A4.13c": W_(base="a1_glow", cam=[[0.45, 0.4, 1.15], [0.42, 0.38, 1.3]]),
    "A4.14": W_(base="s03", cam=[[0.511, 0.52, 1.35], [0.511, 0.5, 1.45]],
                screen=W_(mode="bill", tabn=2, active=1, head="SATURDAY · 8 PM", big="$30", big_col=RED, sub="TICKET", big2="$48", big2_col=GREEN,
                          sub2b="ALL-IN", big_on="forty-eight", toggle=W_(label="SHOW PRICES\nWITH FEES", state=1, y=40, size=54)),
                sfx=[{"kind": "pop", "on": "forty-eight"}]),
    "A4.15a": W_(base="s03", cam=[[0.511, 0.53, 1.55], [0.511, 0.55, 1.72]],
                 screen=W_(mode="bill", head="ORDER SUMMARY · LAST SCREEN", rows_top=120, pay=True,
                           rows=[W_(name="TICKET · ROW G, SEAT 12", amt="$30"), W_(name="FEES", amt="$18"),
                                 W_(name="TOTAL", amt="$48", hl=True, hl_on="last")])),
    "A4.15b": W_(base="s01", cam=[[0.38, 0.35, 1.5], [0.36, 0.33, 1.7]],
                 overs=[W_(t="plate", text="8:14 · CHECK 2", at=0.15, x=0.5, y=0.07), W_(t="note", text="LAST SCREEN", size=76, write_on="real", x=0.6, y=0.32)]),
    "A4.15c": W_(base="s04", cam=[[0.45, 0.45, 1.05], [0.42, 0.42, 1.2]], dial_time="8:14"),
    "A4.16a": W_(base="p04", cam=[[0.5, 0.42, 1.05], [0.5, 0.4, 1.14]], overs=[W_(t="plate", text="8:15 · CHECK 3", at=0.15, x=0.5, y=0.06)],
                 screen=W_(mode="bill", head="TICKET A", big="$40", sub="NO FEES", fs=P04FS),
                 screen2=W_(mode="bill", head="TICKET B", big="$30", big_col=RED, fs=P04FS, rows_top=330,
                            rows=[W_(name="+ FEES", amt="$18", col=RED, at_on="totals"), W_(name="= TOTAL", amt="$48", hl=True, at_on="headlines")])),
    "A4.16b": W_(base="p04", cam=[[0.3, 0.4, 1.7], [0.29, 0.39, 1.85]], cut_on="forty-dollar",
                 screen=W_(mode="bill", head="TICKET A", big="$40", sub="NO FEES", fs=P04FS),
                 screen2=W_(mode="bill", head="TICKET B", big="$30", big_col=RED, fs=P04FS, rows_top=330,
                            rows=[W_(name="+ FEES", amt="$18", col=RED), W_(name="= TOTAL", amt="$48", hl=True)])),
    "A4.17a": W_(base="s01", cam=[[0.42, 0.42, 1.3], [0.4, 0.4, 1.45]],
                 overs=[W_(t="tags", items=["$40 · DONE"], at_on=["Forty"], x=0.8, y=0.14, w=480, size=84, color=GREEN)], sfx=[{"kind": "tap", "on": "reopens"}]),
    "A4.17b": W_(base="a1_wallet", cam=[[0.5, 0.45, 1.15], [0.5, 0.43, 1.28]],
                 overs=[W_(t="note", text="$10 LEFT", sub="ON FRIDAY", size=104, write_on="ten", x=0.62, y=0.24)]),
    "A4.17c": W_(base="s06", cam=[[0.36, 0.38, 1.4], [0.34, 0.36, 1.55]],
                 overs=[W_(t="note", text="GENIUS!", sub="FOR REAL", size=100, write_on="really", x=0.66, y=0.3)]),
    # ---------------------------------------------------------------- Saturday
    "A4.18a": W_(base="k4", cam=[[0.5, 0.5, 1.0], [0.5, 0.5, 1.06]]),
    "A4.18b": W_(base="z0clip", cam=[[0.5, 0.5, 1.02], [0.5, 0.48, 1.1]], cut_on="band"),
    "A4.J11a": W_(base="k7", cam=[[0.5, 0.5, 1.0], [0.5, 0.5, 1.06]]),
    "A4.J11b": W_(base="g09", cam=[[0.45, 0.4, 1.35], [0.46, 0.38, 1.5]], cut_on="Best",
                  overs=[W_(t="tags", items=["ALL FEES INCLUDED"], at_on=["All"], x=0.74, y=0.24, w=640, size=78)], sfx=[{"kind": "pop", "on": "All"}]),
    # ---------------------------------------------------------------- the verdict
    "A4.19a": W_(base="a2_safe", cam=[[0.4, 0.45, 1.02], [0.4, 0.45, 1.1]], dur=3.4, dials=dials(opened(4))),
    "A4.19b": W_(base="s03", cam=[[0.511, 0.52, 1.5], [0.5, 0.5, 1.72]], screen=W_(mode="tabs", tabs=[W_(price="$30")], active=0)),
    "A4.19c": W_(base="p01", cardcam=True, sfx=[{"kind": "paper", "at": 0.1}, {"kind": "stamp", "on": "decision"}],
                 sheets=[card_sheet(P01_CARD["journal"], ["TUESDAY · 8:19 PM", "the fee arrived at", "a decision already"], at_on="fee")],
                 overs=[W_(t="stamp", text="MADE", at_on="decision", x=0.72, y=0.62, size=120)]),
    "A4.20": W_(base="p01", cam=[[0.42, 0.6, 1.3], [0.42, 0.6, 1.4]], sfx=[{"kind": "stamp", "at": 0.12}],
                overs=[W_(t="case_folder", number="004", title="THE SEVEN-MINUTE HEIST", slide_=-3.0, type_=[-9.0, -9.0]),
                       W_(t="stamp", text="CASE CLOSED", at_=0.12, x=0.5, y=0.66, size=140)]),
    "A4.21a": W_(base="p01", cardcam=True, sfx=[{"kind": "type", "on": "verdict"}],
                 sheets=[card_sheet(P01_CARD["front_left"], ["THE VERDICT · CASE 004", "GUILTY:", "the fee at the end"], hl="GUILTY:")]),
    "A4.21b": W_(base="a3_lineup", cam=[[0.5, 0.42, 1.04], [0.5, 0.41, 1.14]], cut_on="and",
                 sheets=[img_sheet(5016, 2823, [dict(LINEUP_TAG, static=True)])],
                 overs=[W_(t="stamp", text="GUILTY", at_on="cousin", x=0.2, y=0.15, size=90, paper=True)], sfx=[{"kind": "stamp", "on": "cousin"}]),
    "A4.21c": W_(base="s03", cam=[[0.511, 0.52, 1.5], [0.511, 0.53, 1.66]], cut_on="Accomplice",
                 screen=W_(mode="bill", head="CONCERT · 1 TICKET", big="$30", big_col=RED, sub="THE FIRST NUMBER",
                           stamp=W_(text="ACCOMPLICE", at_on="Accomplice", x=760, y=470, size=110, rot=-8)), sfx=[{"kind": "stamp", "on": "Accomplice"}]),
    # ---------------------------------------------------------------- next case
    "A4.22a": W_(base="a2_mug", cam=[[0.62, 0.5, 1.1], [0.66, 0.5, 1.25]],
                 insets=[W_(still="next_tablet", q=[[3150, 750], [4420, 750], [4420, 2250], [3150, 2250]], crop=[418, 66, 958, 704])]),
    "A4.22b": W_(base="a2_mug", cardcam=True, sfx=[{"kind": "paper", "at": 0.1}],  # Klot r6: on the table, by the tip tablet
                 sheets=[card_sheet(CARD_AT["mug_front"], ["PEW RESEARCH CENTER · 2023", "72% of Americans: tipping", "is expected in more places", "than five years ago"], hl="72%",
                                    at_on="Seventy-two")]),
    "A4.22c": W_(base="p01", cam=[[0.5, 0.6, 1.05], [0.5, 0.6, 1.15]], cut_on="We'll",
                 overs=[W_(t="case_folder", number="005", title="THE TIP SCREEN", slide_on="find", type_on=["find", "decided"])],
                 sfx=[{"kind": "paper", "on": "find", "lead": 0.45}, {"kind": "type", "on": "find"}]),
    "A4.23": W_(base="p01", cam=[[0.45, 0.5, 1.5], [0.45, 0.5, 1.6]],
                sheets=[W_(q=[[1000, 1020], [2300, 1000], [2460, 1720], [920, 1740]], W=612, H=662, color=INK,
                           items=[{"k": "prop", "src": "v2/props/sub_casefiles.png", "x": 306, "y": 331, "w": 612, "h": 662, "static": True}])],
                overs=[W_(t="note", text="SUBSCRIBE", size=96, write_on="Subscribe", x=0.12, y=0.22)]),
}

KLOT_A34 = {"a3_lineup": "ep04v2_a3_lineup", "g02": "ep04v2_g02_gym", "g03": "ep04v2_g03_newspaper", "a3_courtroom": "ep04v2_a3_courtroom",
            "a3_race": "ep04v2_a3_race", "a4_police": "ep04v2_a4_police", "g07": "ep04v2_g07_car", "g08": "ep04v2_g08_mirror", "g09": "ep04v2_g09_hotdog",
            "p12": "ep04v2_p12_ticket_stack", "p13": "ep04v2_p13_paper_map"}
EP4_A34 = {"c1": "c1", "m2b": "m2b", "l5": "l5", "l8": "l8"}
CLIPS_A34 = {"m5": "ep04v2_m5_dollars", "m1": "ep04v2_m1_gulp", "m4": "ep04v2_m4_smug", "m6": "ep04v2_m6_lookout", "m7": "ep04v2_m7_lineup", "m8": "ep04v2_m8_lobby",
             "m9": "ep04v2_m9_gavel", "k2": "ep04v2_k2_race", "k3": "ep04v2_k3_police", "k4": "ep04v2_k4_seat", "k7": "ep04v2_k7_hotdog", "c1clip": "c1", "m2bclip": "m2b", "z0clip": "z0"}
FACES_A34 = {"m1", "m4", "m8", "c1", "c1clip", "o4clip", "g09", "k4", "k7", "z0clip"}

# ---------------------------------------------------------------- the end screen (Klot, locked): the last 20-22 s, music only:
# the Subscribe line, a next-case sketch (~10 s), subscribe (~6-7 s); YouTube's zones stay free (right: the video element,
# bottom-left: the subscribe button) - our content lives left of x = 0.62 and above y = 0.75
END_SCREEN = [
    ("END.1a", 5.0, W_(base="g04", cam=[[0.5, 0.4, 1.2], [0.5, 0.38, 1.27]],
                       insets=[W_(still="next_tablet", q=[[2001, 93], [3141, 93], [3141, 1077], [2001, 1077]], crop=[300, 66, 1076, 736], round=True)],
                       overs=[W_(t="plate", text="NEXT CASE", at=0.3, x=0.3, y=0.08)])),
    ("END.1b", 5.5, W_(base="p01", cam=[[0.5, 0.55, 1.03], [0.48, 0.55, 1.09]],
                       overs=[W_(t="case_folder", number="005", title="THE TIP SCREEN", slide_=0.75, type_=[1.0, 1.7], cx=0.34, cy=0.42)],
                       sfx=[{"kind": "paper", "at": 0.3}])),
    ("END.2", 7.0, W_(base="p01", cam=[[0.4, 0.45, 1.45], [0.4, 0.45, 1.52]],
                      overs=[W_(t="note", text="SUBSCRIBE", sub="CASE FILE 005 IS NEXT", size=110, write_=0.6, x=0.1, y=0.26)])),
]
