"""Ep.4 v2 PREVIEW 1: cold open + Act 1 (0:00 to the first ad break) for the Remotion layer (composition "V2"),
16:9, plus a 9:16 sample of the cold open. Plan = scenes.py (approved scene list) + timings.json (the fable voice).
Uses only assets already in the repo / Ep.4 releases; each of Klot's new stills that is still missing is held on a neutral
act-palette card labelled with its file name. Writes pilot/remotion/public/v2/{preview_long,preview_short}.json, the
pictures it needs, and the audio mixes (factory.audio.Timeline: voice, beds, sfx, brass hits, real silences).
python tools/v2_preview.py <dir with timings.json + voice_24k.flac> <remotion public dir> <out dir>"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from factory import audio as A  # noqa: E402

EP = ROOT / "episodes" / "0005-drip-pricing"
FPS = 30
LEAD = 0.15            # a picture arrives this much before its line
PAL = {"night": "#0E1A2B", "glow": "#9FD8FF", "paper": "#F3E9D2", "ink": "#1E1B18", "red": "#B23421", "accent": "#E8B53A",
       "green": "#2E6B4F"}
MISSING_OLD = {"ep04v2_a1_glow": "Klot's GPT still: dark room at night, a laptop's glow (Grok clip k1 comes from it)",
           "ep04v2_a1_wallet": "Klot's GPT still: an open wallet with $50 on a kitchen table at night",
           "ep04v2_g04_daydream": "Klot's GPT still: Larry daydreaming of a hot dog in a thought bubble (the bubble pops on 'won't')",
           "ep04v2_g05_bomb": "Klot's GPT still: a cartoon bomb clock with a blank face (Grok clip k5: its fuse sparks)"}
MISSING = {"ep04v2_a1_wallet": "an open wallet with $50 on a kitchen table at night", "ep04v2_g01_blueprint": "a blank blueprint on a drafting table",
           "ep04v2_g04_daydream": "Larry daydreaming of a hot dog in a thought bubble", "ep04v2_g05_bomb": "a cartoon bomb clock with red and blue wires",
           "ep04v2_s04_wall_clock": "a 1950s kitchen wall clock"}
LOC_A2B = "Waiting to buy tickets, Radio City Music Hall, New York, 1942 · Library of Congress"

# ---------------------------------------------------------------------------------------------------------------- plan
# one entry per shot id of docs/ep04v2_scenes.md (COLD + Act 1). "*_on": a word of the shot's line (prefix match) whose
# spoken start becomes the matching key in seconds from the shot start. sfx: {kind, on|at}.
# The picture-first plan (Klot R41-R43, episodes/.../v2/picture_first.py): every shot has a picture base ("base", a
# logical name resolved in BASES: Klot's still when it is in the repo, else a tagged Ep.4 stand-in, else a labelled
# placeholder), a camera ("cam", fractions of the logical still), the checkout screen-replaced into a blank laptop screen
# ("screen", a page spec) and overlays in frame space ("overs"). "*_on": a spoken word -> seconds from the shot start.
W_ = lambda **k: k  # noqa: E731
S: dict[str, dict] = {
    "COLD.1": W_(base="k1", cam=[[0.5, 0.5, 1.02], [0.6, 0.52, 1.25]]),
    "COLD.2": W_(base="s01", cam=[[0.45, 0.5, 1.04], [0.52, 0.5, 1.1]],
                 overs=[W_(t="icons_strip", items=["mask", "car", "megaphone"], cross_on=["masks", "car", "raised"], y=0.58)],
                 sfx=[{"kind": "pop", "on": "masks"}, {"kind": "pop", "on": "getaway"}, {"kind": "pop", "on": "raised"}]),
    "COLD.3a": W_(base="s02", cam=[[0.5, 0.45, 1.0], [0.52, 0.42, 1.12]], screen=W_(mode="form", fill=[0.1, 0.95]),
                  sfx=[{"kind": "typing", "at": 0.3, "dur": 2.4}]),
    "COLD.3b": W_(base="s03", cam=[[0.5, 0.45, 1.05], [0.58, 0.55, 1.35]], screen=W_(mode="form", fill=[1, 1], tick_on="ticked", thanks_on="thank"),
                  sfx=[{"kind": "tap", "on": "ticked"}, {"kind": "tap", "on": "thank"}]),
    "COLD.4a": W_(base="o4", cam=[[0.5, 0.5, 1.03], [0.47, 0.42, 1.12]],
                  overs=[W_(t="namecard", name="LARRY", box=[0.66, 0.08, 0.92, 0.36], box_short=[0.62, 0.08, 0.93, 0.36], stamp="FICTIONAL", stamp_on="made")],
                  sfx=[{"kind": "kachunk", "on": "made"}]),
    "COLD.4b": W_(base="s03", cam=[[0.511, 0.52, 1.66], [0.511, 0.53, 1.8]],
                  screen=W_(mode="fees", fees=[W_(name="SERVICE FEE", amt=""), W_(name="FACILITY FEE", amt=""), W_(name="PROCESSING", amt="")],
                            stamp=W_(text="REAL", at_on="not", x=800, y=300, size=120, rot=-8)), sfx=[{"kind": "stamp", "on": "not"}]),
    "COLD.5": W_(base="o4clip", cam=[[0.55, 0.48, 1.05], [0.6, 0.45, 1.3]]),
    "COLD.6": W_(base="s02", cam=[[0.5, 0.45, 1.02], [0.5, 0.42, 1.1]], screen=W_(mode="whip", pages=["list", "seat", "form"], page_on=["found", "picked", "typed"]),
                 sfx=[{"kind": "whoosh", "on": "found"}, {"kind": "whoosh", "on": "picked"}, {"kind": "whoosh", "on": "typed"}]),
    "COLD.7": W_(base="s03", cam=[[0.5, 0.52, 1.6], [0.45, 0.5, 1.75]], screen=W_(mode="total", total="$48", total_on="number", pay_on="paid"),
                 sfx=[{"kind": "stab", "on": "number"}]),
    "COLD.8": W_(base="g01", cam=[[0.5, 0.5, 1.05], [0.5, 0.5, 1.15]], dark=True, plan=W_(mode="walls", at=0.2)),
    "COLD.9": W_(base="p01", cam=[[0.5, 0.6, 1.05], [0.5, 0.6, 1.15]],
                 overs=[W_(t="case_folder", number="004", title="THE SEVEN-MINUTE HEIST", slide_on="Case", type_on=["Case", "seven"])],
                 sfx=[{"kind": "paper", "on": "Case", "lead": 0.45}, {"kind": "type", "on": "Case"}, {"kind": "type", "on": "seven"}]),
    "A1.1a": W_(base="a1_wallet", cam=[[0.5, 0.5, 1.02], [0.5, 0.5, 1.12]], title=["ACT 1", "THE MARK"]),
    "A1.1b": W_(base="a1_wallet", cam=[[0.5, 0.5, 1.15], [0.5, 0.48, 1.3]],
                overs=[W_(t="calendar_strip", days=["TUE", "WED", "THU", "FRI"], amount="$50", write_on="fifty", cx=0.7, cy=0.27, s=0.85)]),
    "A1.2a": W_(base="a10", cam=[[0.5, 0.55, 1.03], [0.5, 0.58, 1.15]], dream=True,
                overs=[W_(t="plate", text="SATURDAY · 2 HOURS AWAY", at_on="Saturday", x=0.5, y=0.12)]),
    "A1.2b": W_(base="s06", cam=[[0.42, 0.45, 1.02], [0.36, 0.42, 1.14]]),
    "A1.3": W_(base="s02", cam=[[0.511, 0.5, 1.2], [0.511, 0.5, 1.6]],
               screen=W_(mode="tabs", tabs=[W_(price="$40", tag="ALL-IN", on="forty")], hl_on="Everything"), sfx=[{"kind": "tap", "on": "first"}]),
    "A1.4": W_(base="s03", cam=[[0.511, 0.52, 1.2], [0.56, 0.5, 1.55]],
               screen=W_(mode="tabs", tabs=[W_(price="$40", tag="ALL-IN"), W_(price="$30", on="thirty")], active=1), sfx=[{"kind": "tap", "on": "second"}]),
    "A1.5a": W_(base="s01", cam=[[0.42, 0.4, 1.4], [0.38, 0.34, 1.9]],  # a face between screens (Klot note 8): push in on Larry
                overs=[W_(t="tags", items=["+$10 SAVED"], at_on=["Ten"], x=0.78, y=0.12, w=440, size=76, color="#2E6B4F")],
                sfx=[{"kind": "tap", "on": "closes"}, {"kind": "ding", "on": "Ten"}]),
    "A1.5b": W_(base="s06", cam=[[0.36, 0.38, 1.5], [0.34, 0.36, 1.65]],  # Klot: the hand never covers a face -> the word goes beside him
                overs=[W_(t="note", text="GENIUS!", size=100, write_on="Larry#2", x=0.68, y=0.3)]),
    "A1.J1a": W_(base="g04", cam=[[0.5, 0.5, 1.02], [0.5, 0.48, 1.12]]),
    "A1.J1b": W_(base="g04", cam=[[0.52, 0.4, 1.3], [0.52, 0.36, 1.5]], overs=[W_(t="pop", at_on="won't", x=0.63, y=0.47)],
                 sfx=[{"kind": "pop", "on": "won't"}]),
    "A1.6a": W_(base="s03", cam=[[0.511, 0.52, 1.2], [0.42, 0.45, 1.7]], screen=W_(mode="tabs", tabs=[W_(price="$40", tag="ALL-IN"), W_(price="$30")], active=1, single=True)),
    "A1.6b": W_(base="a1_glow", cam=[[0.5, 0.45, 1.0], [0.46, 0.42, 1.14]],  # a face between screens (note 8)
                overs=[W_(t="slots", slots_on="three", x=0.8, y=0.22)], sfx=[{"kind": "pop", "on": "three"}]),
    "A1.7a": W_(base="s02", cam=[[0.511, 0.5, 1.3], [0.511, 0.5, 1.6]], screen=W_(mode="seat", seat="G12", fly_on="Row", light_on="12"),
                sfx=[{"kind": "whoosh", "on": "Row"}, {"kind": "pop", "on": "12"}]),
    "A1.7b": W_(base="a10clip", cam=[[0.5, 0.5, 1.0], [0.5, 0.55, 1.08]]),
    "A1.8a": W_(base="s03", cam=[[0.511, 0.5, 1.5], [0.6, 0.4, 1.9]], screen=W_(mode="timer", timer_on="clock", secs=600), sfx=[{"kind": "pop", "on": "clock"}]),
    "A1.8b": W_(base="s04", cam=[[0.45, 0.45, 1.02], [0.36, 0.33, 1.3]]),
    "A1.J2a": W_(base="k5", cam=[[0.5, 0.5, 1.02], [0.5, 0.48, 1.15]]),
    "A1.J2b": W_(base="g05", cam=[[0.4, 0.55, 1.25], [0.4, 0.55, 1.32]], overs=[W_(t="wires", snip_on="wires", xa=0.12, xb=0.6, y=0.5)],
                 sfx=[{"kind": "snip", "on": "wires", "lead": -0.6}]),
    "A1.9a": W_(base="s01", cam=[[0.45, 0.5, 1.15], [0.4, 0.42, 1.5]],  # a face between screens (note 8): Larry typing

                sfx=[{"kind": "typing", "on": "Name", "dur": 0.6}, {"kind": "typing", "on": "Email", "dur": 0.6}, {"kind": "typing", "on": "Card", "dur": 0.9}]),
    "A1.9b": W_(base="s03", cam=[[0.5, 0.5, 1.25], [0.5, 0.52, 1.45]], screen=W_(mode="form", fill=[0.67, 1.0], digits_on="sixteen"),
                sfx=[{"kind": "typing", "on": "sixteen", "dur": 1.9}]),
    # archive photos fill the frame (note 6): the original prints, cropped to the picture, a slow push
    # R48: no 1939/1942 photos under "if you've ever bought a ticket online": the screens themselves, then Larry's face
    "A1.10a": W_(base="s02", cam=[[0.511, 0.5, 1.35], [0.511, 0.5, 1.6]], screen=W_(mode="whip", pages=["list", "seat", "form"], page_on=["bought", "know", "been"])),
    "A1.10b": W_(base="s06", cam=[[0.42, 0.45, 1.02], [0.38, 0.42, 1.14]]),
    "A1.11a": W_(base="a1_glow", cam=[[0.45, 0.42, 1.1], [0.4, 0.38, 1.35]],  # a face between screens (note 8)
                 overs=[W_(t="tags", items=["+$8"], at_on=["Service"], x=0.78, y=0.2)], sfx=[{"kind": "kachunk", "on": "Service"}]),
    "A1.11b": W_(base="s03", cam=[[0.511, 0.52, 1.8], [0.5, 0.55, 2.1]],  # push in on the screen while the joke is spoken (note 5)
                 screen=W_(mode="fees", fees=[W_(name="SERVICE FEE", amt="$8", label="FOR THE SERVICE OF CHARGING YOU A FEE", label_on="service#2")]),
                 sfx=[{"kind": "typing", "on": "service#2", "dur": 1.4}]),
    "A1.J3a": W_(base="s03", cam=[[0.511, 0.52, 1.72], [0.5, 0.57, 2.1]], hold_on="fees",  # the screen stays until the joke ends
                 screen=W_(mode="fees", fees=[W_(name="SERVICE FEE", amt="$8", label="FOR THE SERVICE OF CHARGING YOU A FEE"),
                                              W_(name="FACILITY FEE", amt="$6", at_on="Facility"),
                                              W_(name="PROCESSING", amt="$4", at_on="Processing", label="TO PROCESS THE OTHER FEES", label_on="process#2")]),
                 sfx=[{"kind": "kachunk", "on": "Facility"}, {"kind": "kachunk", "on": "Processing"}, {"kind": "typing", "on": "process#2", "dur": 1.1}]),
    "A1.J3b": W_(base="s05", cam=[[0.5, 0.45, 1.02], [0.5, 0.42, 1.12]], overs=[W_(t="tags", items=["+$8", "+$6", "+$4"], at=[0.05, 0.25, 0.45], x=0.84, y=0.2)]),
    "A1.12": W_(base="key", key="$48", sub="TOTAL", at=0.15, sfx=[{"kind": "stab", "on": "Total"}]),
    "A1.13": W_(base="s05", cam=[[0.5, 0.42, 1.15], [0.5, 0.38, 1.35]],
                overs=[W_(t="bars_card", bars=[["FIRST", 30, "$30"], ["LAST", 48, "$48"]], x=0.8, y=0.62),
                       W_(t="stamp", text="+60%", at_on="sixty", x=0.78, y=0.25, size=120)], sfx=[{"kind": "stamp", "on": "sixty"}]),
    "A1.14a": W_(base="s03", cam=[[0.511, 0.52, 1.5], [0.511, 0.52, 1.66]], screen=W_(mode="versus", left="$40", right="$48", badge="+$8", badge_on="eight"),
                 sfx=[{"kind": "pop", "on": "eight"}]),
    "A1.14b": W_(base="a1_wallet", cam=[[0.5, 0.5, 1.2], [0.5, 0.5, 1.35]],
                 overs=[W_(t="note", text="$2 LEFT", sub="UNTIL FRIDAY", size=104, write_on="two", x=0.6, y=0.24)]),
    "A1.15a": W_(base="s02", cam=[[0.511, 0.5, 1.5], [0.56, 0.45, 1.68]], screen=W_(mode="timer", timer_=0.0, secs=360)),
    "A1.15b": W_(base="a4_seat", cam=[[0.5, 0.55, 1.08], [0.5, 0.58, 1.2]], dream=True),
    "A1.16": W_(base="s03", cam=[[0.511, 0.52, 1.62], [0.56, 0.58, 1.85]], screen=W_(mode="pay", press_on="presses"), sfx=[{"kind": "tap", "on": "presses"}]),
    "A1.17a": W_(base="s04", cam=[[0.42, 0.5, 1.1], [0.41, 0.48, 1.18]],
                 overs=[W_(t="timeline_strip", steps=[["8:12", "TABS"], ["8:13", "SEAT"], ["8:14", "CLOCK"], ["8:16", "CARD"], ["8:18", "FEES"], ["8:19", "PAY"]], at=0.2, y=0.58)]),
    "A1.17b": W_(base="o4", cam=[[0.5, 0.5, 1.0], [0.52, 0.48, 1.08]], overs=[W_(t="tag_circle", text="$18", x=0.8, y=0.25, scale=1.5, circle_on="saw")]),
    "A1.18": W_(base="s01", cam=[[0.5, 0.5, 1.05], [0.5, 0.48, 1.15]],
                overs=[W_(t="price_pair", left="$40", right="$48", cross_at=0.4, q_on="forty-eight", qx=0.68, qy=0.5)], sfx=[{"kind": "stamp", "on": "forty-eight"}]),
    "A1.19a": W_(base="g01", cam=[[0.5, 0.5, 1.02], [0.5, 0.48, 1.12]], grade="dusk", plan=W_(mode="route", at=0.35)),
    "A1.19b": W_(base="a5", cam=[[0.5, 0.45, 1.5], [0.5, 0.5, 1.02]], green_creep=True),
}
from v2_preview_a2 import A2 as _A2, KLOT_A2, EP4_A2, CLIPS_A2  # noqa: E402  (Act 2 specs)
from v2_preview_a3a4 import A3 as _A3, A4 as _A4, KLOT_A34, EP4_A34, CLIPS_A34, FACES_A34, END_SCREEN  # noqa: E402  (Acts 3-4)
S.update(_A2)
S.update(_A3)
S.update(_A4)
for _k, _v in list(S.items()):  # sfx inside a shot spec is the mixer's, not the layer's
    _v.setdefault("kind", "pic")
# logical stills -> Klot's file when it is in the repo, else an Ep.4 stand-in window (x0, y0, x1, y1 of the stand-in) or a placeholder
KLOT = {"arch_loews": "ep04v2_arch_loews_1939", "arch_briggs": "ep04v2_arch_briggs_1942", "a1_glow": "ep04v2_a1_glow", "a1_wallet": "ep04v2_a1_wallet", "a4_seat": "ep04v2_a4_seat", "g01": "ep04v2_g01_blueprint",
        "g04": "ep04v2_g04_daydream", "g05": "ep04v2_g05_bomb", "s01": "ep04v2_s01_flat_wide", "s02": "ep04v2_s02_over_shoulder",
        "s03": "ep04v2_s03_laptop_close", "s04": "ep04v2_s04_wall_clock", "s05": "ep04v2_s05_gulp", "s06": "ep04v2_s06_smug"}
STANDIN = {"a1_glow": ("ep04v2_s01_flat_wide", [0.16, 0.14, 0.6, 0.6], "dark"), "s01": ("o4", [0.0, 0.0, 1.0, 1.0], "night"),
           "s02": ("m1b-blank", [0.08, 0.04, 0.92, 0.886], ""), "s03": ("m1b-blank", [0.275, 0.128, 0.726, 0.582], ""),
           "s05": ("b1", [0.2, 0.02, 0.56, 0.38], ""), "s06": ("o4", [0.23, 0.02, 0.63, 0.42], ""), "a4_seat": ("a11", [0.0, 0.0, 1.0, 1.0], "")}
EP4 = {"o4": "o4", "l1": "l1", "a5": "a5", "a10": "a10", "arch_a2": "archive-a2", "arch_a2b": "archive-a2b", "m1b-blank": "m1b", "b1": "b1", "a11": "a11"}
CLIPS = {"o4clip": "o4", "a10clip": "a10", "k1": "ep04v2_k1_glow", "k5": "ep04v2_k5_bomb", "k6": "ep04v2_k6_car", **CLIPS_A2}
KLOT.update(KLOT_A2)
KLOT.update(KLOT_A34)
EP4.update(EP4_A2)
EP4.update(EP4_A34)
CLIPS.update(CLIPS_A34)
SCREEN_PX = {"m1b-blank": [[440, 122], [938, 122], [938, 422], [440, 422]]}  # the blank screen (px of the 1376x768 still)
CLOCK = {"A1.1": "8:12", "A1.7": "8:13", "A1.8": "8:14", "A1.9": "8:16", "A1.11": "8:18", "A1.16": "8:19"}
TICKS = ("A1.8", "A1.16")
DIP_LINES = {"A3.5": -7.0, "A1.1": -10.0}  # extra dip (dB) of music + foley (the pen scratch) under lines the final-mix STT check heard unclean      # the hold clock ticks from 8:14 until Pay
HEART = ("A1.11", "A1.16")     # heartbeat from 8:18 until Pay (stops before the silence)


# Larry's face (or Larry in the room): a cut to one of these breaks a run of laptop screens (Klot note 8: <= 2 screens in a row)
FACES = {"s01", "s05", "s06", "a1_glow", "a1_wallet", "a4_seat", "g04", "o4", "o4clip", "p06", "p08"}
FACES |= FACES_A34
# checkout text we want read on a phone (Klot note 5): sizes in screen units (the screen box is 1240 wide); the QC checks the cap
# height against 2.8 % of the frame from these same numbers (ArchivoBlack / SpecialElite cap height = 0.688 / 0.689 em)
READ_FS = {"os": 46, "row": 50, "fee": 54, "lab": 44, "tot": 52, "big": 140}
CAP = {"os": 0.688, "row": 0.688, "fee": 0.688, "lab": 0.689, "tot": 0.688}

# the heist floor plan on the blueprint (Klot note 1), in sheet units (1000 x 600): walls, rooms in checkout order,
# a dashed route PRICE -> SEAT -> TIMER -> CARD -> FEES -> PAY and an X on PAY; white chalk
PLAN_W, PLAN_H = 1000, 600
PLAN_WALLS = ["M 60 60 L 940 60 L 940 540 L 60 540 Z", "M 60 300 L 760 300", "M 830 300 L 940 300",
              "M 353 60 L 353 150", "M 353 210 L 353 390", "M 353 450 L 353 540",
              "M 646 60 L 646 150", "M 646 210 L 646 390", "M 646 450 L 646 540"]
PLAN_ROOMS = [("PRICE", 206, 122), ("SEAT", 500, 122), ("TIMER", 793, 122), ("CARD", 793, 512), ("FEES", 500, 512), ("PAY", 206, 512)]
PLAN_ROUTE = "M 20 180 L 795 180 L 795 420 L 266 420"
PLAN_ARROW = "M 292 400 L 266 420 L 292 440"
PLAN_X = ["M 176 388 L 236 452", "M 236 388 L 176 452"]
LABEL_SIZE = 46


def _plen(d: str) -> float:
    import re as _re
    v = [float(x) for x in _re.findall(r"-?\d+(?:\.\d+)?", d)]
    pts = list(zip(v[0::2], v[1::2]))
    if d.strip().endswith("Z"):
        pts.append(pts[0])
    return sum(((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5 for a, b in zip(pts, pts[1:]))


def plan_items(spec: dict, shot_dur: float) -> list[dict]:
    """Strokes with their times (seconds from the shot start). 'walls': walls + room names drawn; 'route': the plan is
    already there, the route, the arrow and the X are drawn. Room names are written at 0.075 s per letter (rule 1)."""
    gap, at = 0.08, spec.get("at", 0.2)
    walls = [{"k": "line", "d": d} for d in PLAN_WALLS]
    rooms = [{"k": "text", "text": n, "x": x, "y": y, "size": LABEL_SIZE} for n, x, y in PLAN_ROOMS]
    route = [{"k": "route", "d": PLAN_ROUTE}, {"k": "line", "d": PLAN_ARROW}] + [{"k": "line", "d": d, "w": 9} for d in PLAN_X]
    if spec["mode"] == "walls":
        anim, still = walls + rooms, []
    elif spec["mode"] == "static":  # the finished plan (route included); optional extra ink
        anim, still = [dict(i) for i in spec.get("extra", [])], walls + rooms + route
        at = min([i.get("at_", at) for i in anim] or [at])
    else:
        anim, still = route, walls + rooms
    budget = shot_dur - at - 0.35 - 1.3  # the hand leaves (0.4 s) and the plan holds ~0.8 s before the cut
    fixed = sum(len(i["text"]) * 0.075 for i in anim if i["k"] == "text") + gap * (len(anim) - 1)
    lens = [_plen(i["d"]) for i in anim if i["k"] != "text"]
    v = 900.0  # sheet units per second: the slowest pen that still fits the shot
    while v < 8000 and fixed + sum(max(0.14, x / v) for x in lens) > budget:
        v *= 1.05
    t = at + 0.35
    for i in anim:
        t = max(t, i.get("at_", t))
        i["dur"] = round(len(i["text"]) * 0.075 if i["k"] == "text" else max(0.14, _plen(i["d"]) / v), 3)
        i["t0"] = round(t, 3)
        t += i["dur"] + gap
    for i in still:
        i["static"] = True
    return still + anim


def sheet_times(sh: dict, shot_dur: float) -> None:
    """Times the items of an ink sheet in order: each starts at its word (or 'at', or right after the previous one);
    text at 0.075 s per letter (rule 1), strokes at ~1600 units/s of the sheet's width scale."""
    unit = sh["W"] / 1000
    t = sh.get("at_", sh.get("at", 0.3))
    for i in sh["items"]:
        if i.get("static"):
            continue
        if i["k"] in ("tag", "paper", "prop"):  # pops in at its own time; laid by no hand
            i["t0"] = round(i.get("at_", i.get("at", sh.get("at_", sh.get("at", 0.3)))), 3)
            i["dur"] = 0.25
            continue
        t0 = max(t, i.get("at_", i.get("at", t)))
        i["dur"] = round(len(i["text"]) * 0.075 if i["k"] == "text" else max(0.18, _plen(i["d"]) / (1600 * unit)), 3)
        i["t0"] = round(t0, 3)
        t = t0 + i["dur"] + 0.1


def _norm(w: str) -> str:
    return "".join(c for c in w.lower() if c.isalnum() or c in "-$:")


MIN_SHOT = 1.4


def _has_stamp(spec) -> bool:
    return any(o.get("t") in ("stamp", "namecard") for o in spec.get("overs", [])) or bool((spec.get("screen") or {}).get("stamp"))


def anchors(spec) -> list[str]:
    out = []
    for k, v in spec.items():
        if isinstance(v, dict):
            out += anchors(v)
        elif isinstance(v, list) and v and all(isinstance(x, dict) for x in v) and k != "sfx":
            for x in v:
                out += anchors(x)
        elif k.endswith("_on") and k != "cut_on":
            out += v if isinstance(v, list) else [v]
        elif k == "sfx":
            out += [x["on"] for x in v if "on" in x]
        elif k == "tabs":
            out += [t["on"] for t in v if "on" in t]
        elif isinstance(v, list) and v and all(isinstance(x, dict) for x in v):
            for x in v:
                out += anchors(x)
    return out


def word_time(beat: dict, prefix: str) -> float:
    """Spoken start of the first word starting with prefix ("service#2": the second such word)."""
    nth = int(prefix.split("#")[1]) if "#" in prefix else 1
    p = _norm(prefix.split("#")[0])
    for w, s, _e in beat["words"]:
        if _norm(w).startswith(p):
            nth -= 1
            if nth == 0:
                return beat["start"] + s
    raise KeyError(f"{beat['id']}: no word '{prefix}' in {beat['text']!r}")


def build(T: dict, acts: tuple[str, ...], end_t: float) -> tuple[list[dict], list[dict]]:
    sys.path.insert(0, str(EP / "v2"))
    import scenes  # the shots come from today's scene list (timings.json only carries the voice)
    cur = {bid: [{"picture": p, "tech": t, "source": s} for p, t, s in bb[4]] for _k, bid, bb in scenes.beat_ids()}
    beats = [{**b, "shots": cur[b["id"]]} for b in T["beats"] if b["act"] in acts]
    hit = {h["line"]: h for h in T["hits"]}
    vis = []
    for i, b in enumerate(beats):
        s = 0.0 if i == 0 else b["start"] - LEAD
        if i > 0 and beats[i - 1]["id"] in hit and hit[beats[i - 1]["id"]]["at"] >= beats[i - 1]["end"] - 0.05:
            s = hit[beats[i - 1]["id"]]["at"]  # the picture cuts on the brass hit; the silence holds the next card
        if i > 0 and b["act"] != beats[i - 1]["act"]:  # a new act (the full file): its title arrives on the ad break
            brk = [k["at"] for k in T.get("breaks", []) if beats[i - 1]["end"] - 0.5 <= k["at"] <= b["start"]]
            if brk:
                s = brk[0]
        vis.append(s)
    shots, clock = [], None
    for i, b in enumerate(beats):
        clock = CLOCK.get(b["id"], clock)
        a, z = vis[i], (vis[i + 1] if i + 1 < len(beats) else end_t)
        n = len(b["shots"])
        sids = [b["id"] + (chr(97 + k) if n > 1 else "") for k in range(n)]
        if n == 1 and b["id"] + "/" in S:  # a one-shot beat whose id is another beat's shot id (A4.6b): its spec is "<id>/"
            sids = [b["id"] + "/"]
        # lengths: a spec may ask for its own length ("dur", e.g. a dial close-up <= 1.5 s); the rest share the remainder
        fixed = {k: S[sid]["dur"] for k, sid in enumerate(sids) if "dur" in S[sid]}
        free = [k for k in range(n) if k not in fixed]
        rest = ((z - a) - sum(fixed.values())) / max(1, len(free))
        lens = [fixed.get(k, rest) for k in range(n)]
        cuts = [a + sum(lens[:k]) for k in range(n + 1)]
        cuts[-1] = z
        for k, sid in enumerate(sids):  # "cut_on": this shot starts on that word (a key number lands with its word)
            if k > 0 and "cut_on" in S[sid]:
                cuts[k] = word_time(b, S[sid]["cut_on"]) - 0.05
        # a shot's word anchors must fall inside it: move the cuts (never under MIN_SHOT on either side). A stamp is seen
        # >= 0.8 s after it lands (stamp_hold); ink: the shot runs on until the hand has left (R47, checked)
        for k in range(n):
            sid = sids[k]
            ws = [word_time(b, w) for w in anchors(S[sid])]
            if not ws:
                continue
            after = 1.05 if _has_stamp(S[sid]) else 0.6
            if k > 0 and min(ws) - 0.35 < cuts[k] and "cut_on" not in S[sid]:
                cuts[k] = max(cuts[k - 1] + MIN_SHOT, min(ws) - 0.35)
            if k < n - 1 and max(ws) + after > cuts[k + 1] and "dur" not in S[sids[k + 1]]:
                cuts[k + 1] = min(cuts[k + 2] - MIN_SHOT, max(ws) + after)
            elif k < n - 1 and max(ws) + after > cuts[k + 1]:  # the next shot has a fixed length: it moves as a whole
                d = max(ws) + after - cuts[k + 1]
                cuts[k + 1] += d
                if k + 2 <= n - 1 and "dur" in S[sids[k + 1]]:
                    cuts[k + 2] = min(z if k + 2 == n else cuts[k + 3] - MIN_SHOT, cuts[k + 2] + d)
        for k in range(n):
            sid = sids[k]
            spec = json.loads(json.dumps(S[sid]))
            s0, s1 = cuts[k], cuts[k + 1]
            def resolve(d):  # "<key>_on": word(s) -> "<key>_": seconds from the shot start (nested dicts too)
                for key in list(d):
                    if isinstance(d[key], dict):
                        resolve(d[key])
                    elif isinstance(d[key], list) and d[key] and all(isinstance(x, dict) for x in d[key]):
                        for x in d[key]:
                            resolve(x)
                    elif key == "cut_on":
                        d.pop(key)
                    elif key.endswith("_on"):
                        v = d.pop(key)
                        d[key[:-3] + "_"] = ([round(word_time(b, x) - s0, 3) for x in v] if isinstance(v, list)
                                             else round(word_time(b, v) - s0, 3))
            resolve(spec)
            for t in spec.get("tabs", []):
                if "on" in t:
                    t["at"] = round(word_time(b, t.pop("on")) - s0, 3)
            ink = []  # (t0, t1) absolute: the hand lays ink (scratch sound exactly then, R34)
            for sh in spec.get("sheets", []):
                sheet_times(sh, s1 - s0)
                ink += [(s0 + i["t0"], s0 + i["t0"] + i["dur"]) for i in sh["items"] if not i.get("static") and i["k"] in ("text", "line", "route")]
            if "plan" in spec:
                spec["plan"] = {"W": PLAN_W, "H": PLAN_H, "items": plan_items(spec["plan"], s1 - s0), "color": "#FBFAF5"}
                ink += [(s0 + i["t0"], s0 + i["t0"] + i["dur"]) for i in spec["plan"]["items"] if not i.get("static")]
            if spec.get("screen", {}).get("mode") in ("fees", "total", "pay"):
                spec["screen"]["fs"] = dict(READ_FS)
            spec["face"] = spec.get("base") in FACES
            for o in spec.get("overs", []):
                if o.get("t") == "icons_strip":
                    ink += [(s0 + c, s0 + c + 0.32) for c in o.get("cross_", [])]
                elif o.get("t") == "crown" and "draw_" in o:
                    ink.append((s0 + o["draw_"], s0 + o["draw_"] + 0.7))
                elif o.get("t") == "tag_circle" and "circle_" in o:
                    ink.append((s0 + o["circle_"], s0 + o["circle_"] + 0.6))
                elif o.get("t") == "price_pair":
                    ink.append((s0 + o["cross_at"], s0 + o["cross_at"] + 0.35))
                elif o.get("t") == "timeline_strip":
                    ink.append((s0 + o["at"] + 0.4, s0 + o["at"] + 0.4 + 1.8))
                elif o.get("t") == "plan_lines":
                    step = max(0.7, ((s1 - s0) - o["at"] - 0.6) / 3)
                    ink += [(s0 + o["at"] + 0.35 + i * step, s0 + o["at"] + 0.35 + i * step + step * 0.8) for i in range(3)]
                elif o.get("t") == "calendar_strip" and "write_" in o:
                    ink.append((s0 + o["write_"], s0 + o["write_"] + len(f"{o['amount']} UNTIL FRIDAY") * 0.075))
                elif o.get("t") == "note" and "write_" in o:
                    ink.append((s0 + o["write_"], s0 + o["write_"] + len(o["text"]) * 0.075))
            ev = [{"kind": "marker", "t": round(a, 3), "dur": round(b - a, 3)} for a, b in ink]
            for x in spec.pop("sfx", []):
                at = (word_time(b, x["on"]) - x.get("lead", 0.0)) if "on" in x else s0 + x["at"]
                ev.append({**x, "t": round(at, 3)})
            key = b["id"]
            shots.append({"id": sid, "beat": b["id"], "act": b["act"], "start": round(s0, 3), "end": round(s1, 3),
                          "picture": b["shots"][k]["picture"], "source": b["shots"][k]["source"], **spec, "_sfx": ev,
                          "_ink": [[round(a, 3), round(b, 3)] for a, b in ink],
                          "clock": clock if b["act"] == "A1" else None})
    return beats, shots


def captions(beats: list[dict], kind: str) -> list[dict]:
    from factory.render import group_captions
    mc, mw = (26, 5) if kind == "long" else (16, 3)
    out = []
    import re as _re
    from factory.captions import _dangles
    for b in beats:
        cards = [[[w, round(s, 3), round(e, 3)] for w, (s, e) in zip(c.words, c.word_times)] for c in group_captions(b["words"], b["start"], mc, mw)]
        # R23: a card never ends on a dangling word ("the", "to", "was" ...) mid-sentence: hand it to the next card
        def dangling(c):
            return c and not _re.search(r"[.!?…,:;—-]$", c[-1][0]) and _dangles(c[-1][0])
        for i in range(len(cards) - 1):
            while len(cards[i]) > 1 and dangling(cards[i]):
                cards[i + 1].insert(0, cards[i].pop())
            if len(cards[i]) == 1 and not _re.search(r"[.!?…]$", cards[i][0][0]):  # a lone word goes on with the next card
                cards[i + 1].insert(0, cards[i].pop())
        if len(cards) > 1 and len(cards[-1]) == 1 and not _re.search(r"[.!?…]$", cards[-1][0][0]) and not dangling(cards[-2] + cards[-1]):
            cards[-2].append(cards[-1].pop())
        for ws in [c for c in cards if c]:
            out.append({"start": ws[0][1], "end": ws[-1][2], "words": ws})
    return out


def heartbeat(n: int = 1) -> np.ndarray:
    sr = A.SR
    t = np.arange(int(0.16 * sr)) / sr
    thump = np.sin(2 * np.pi * 52 * t) * np.exp(-t * 26)
    out = np.zeros(int(0.85 * sr), np.float32)
    out[: len(t)] += thump
    out[int(0.24 * sr): int(0.24 * sr) + len(t)] += 0.7 * thump
    return out.astype(np.float32)


def mix(T: dict, beats: list[dict], shots: list[dict], end_t: float, voice: np.ndarray, out: Path, cfg: dict) -> dict:
    tl = A.Timeline(end_t + 0.6, cfg)
    for b in beats:
        i, j = int(b["start"] * 24000), int(b["end"] * 24000)
        tl.add_voice(b["start"], voice[i:j], 24000, tag=b["id"])
    hits = [h for h in T["hits"] if any(h["line"] == b["id"] for b in beats)]
    acts = {a["act"]: a["start"] for a in T["acts"]}
    beds = {"COLD": "ub_ticking_tension", "A1": "ub_night_spot", "A2": "ub_mechanisms_of_action", "A3": "ub_usual_suspects", "A4": "ub_clock_is_ticking"}
    act_at = sorted((a["start"], a["act"]) for a in T["acts"])

    def bed_at(t):  # the bed of the act playing at t (a preview segment or the full episode)
        cur = beats[0]["act"] if beats else "COLD"
        for a0, act in act_at:
            if a0 <= t + 1e-3 and any(bb["act"] == act for bb in beats):
                cur = act
        return beds.get(cur, "ub_ticking_tension")
    bed = bed_at(0.0)
    tl.music_cue(0.0, bed)
    for a0, act in act_at:
        if 0 < a0 < end_t and any(bb["act"] == act for bb in beats) and act != "A1":
            tl.music_cue(a0, beds.get(act, bed))
    # Klot r4: the music dips under a line the final-mix STT check could not hear cleanly (A3.5 "swim in")
    for bb in beats:
        if bb["id"] in DIP_LINES:
            tl.dips.append((bb["start"] - 0.2, bb["end"] + 0.2, DIP_LINES[bb["id"]]))
    silences = []
    for h in hits:
        tl.add_stab(h["at"], "ub_sting_brass", dur=T["hit_len"])
        s0 = max(h["at"] + T["hit_len"], h.get("silence_from", 0.0))  # the second of silence comes after the line
        silences.append((s0, s0 + 1.0))
        tl.music_cue(h["at"] + 0.2, "none")
        tl.music_cue(s0 + 1.0, bed_at(s0 + 1.0))
    if "A1" in acts and 0.0 <= acts["A1"] < end_t:  # only when Act 1 starts inside this file
        tl.music_cue(acts["A1"], "ub_night_spot")
    for sh in shots:
        for e in sh["_sfx"]:
            k = e["kind"]
            if k == "stab":
                tl.add_stab(e["t"], "ub_sting_brass", dur=0.55)
            elif k == "typing":
                t = e["t"]
                while t < e["t"] + e.get("dur", 1.0):
                    tl.add_sfx(t, "tap", seed=int(t * 100))
                    t += 0.11 + 0.05 * ((int(t * 100) * 7919) % 5) / 5
            elif k == "marker":
                tl.add_sfx(e["t"], f"scribble:{e.get('dur', 0.6)}")
                tl.log.append((e["t"], e["t"] + e.get("dur", 0.6), "ink"))
            else:
                tl.add_sfx(e["t"], k, seed=int(e["t"] * 10))
    # the hold clock ticks; the heartbeat from 8:18 until Pay
    bt = {b["id"]: b for b in beats}
    if all(x in bt for x in TICKS):
        t = bt[TICKS[0]]["start"]
        while t < bt[TICKS[1]]["start"] - 1.0:
            tl._add(tl.fx, t, A.sfx("tick") * A.db(-24))
            t += 1.0
    if all(x in bt for x in HEART):
        t = bt[HEART[0]]["start"]
        while t < bt[HEART[1]]["start"] - 1.2:
            tl._add(tl.fx, t, heartbeat() * A.db(-12))
            t += 0.92
    x = tl.mix()
    # designed silences: nothing at all (voice, music, foley) for the second after each brass hit
    for a, b in silences:
        i, j = int(a * A.SR), int(b * A.SR)
        r = int(0.03 * A.SR)
        x[i - r:i] *= np.linspace(1, 0, r)
        x[i:j] = 0.0
        x[j:j + r] *= np.linspace(0, 1, r)
    fade = int(1.0 * A.SR)
    x[-fade:] *= np.linspace(1, 0, fade)
    A.write_wav(out, x)
    return {"silences": silences, "voice_lines": tl.voice_lines, "voice_edits": tl.voice_edits, "sfx": tl.log}


def short_from(shots: list[dict]) -> list[dict]:
    return [dict(s) for s in shots]


def _find(name: str, R: Path) -> Path | None:
    if name == "m1b":  # the BLANK laptop (frames release), not the composited images/m1b.png
        cand = sorted((R / "frames").glob("m1b-*.png"))
    elif name.startswith("ep04v2_"):
        cand = [EP / "v2" / "manual_assets" / f"{name}.png", EP / "images" / f"{name}.png"]
    else:
        # the raw generation (frames release) first: some images/*.png are composited (l1 carries the ticket)
        cand = sorted((R / "frames").glob(f"{name}-*.png")) + [R / "frames" / f"{name}.png", EP / "images" / f"{name}.png"]
    cand = [c for c in cand if c.exists() and not c.name.endswith(".depth.png")]
    return cand[0] if cand else None


def _load(path: Path, key: str, P: Path) -> tuple[str, int, int, float]:
    from PIL import Image
    im = Image.open(path).convert("RGB")
    f = 1.0
    if im.width > 2600:
        f = 2600 / im.width
        im = im.resize((2600, round(im.height * f)), Image.LANCZOS)
    im.save(P / "v2" / f"{key}.jpg", quality=92)
    return f"v2/{key}.jpg", im.width, im.height, f


FACE_BOXES = json.loads((EP / "v2" / "faces.json").read_text()) if (EP / "v2" / "faces.json").exists() else {}


def _world(s: dict, f: float, key: str = "", P: Path | None = None) -> None:
    """Ink sheets, safe dials, the safe door and media insets are given in px of the original picture: scale them with it.
    Faces (faces.json, fractions of the picture) go along as invisible boxes for the hand_over_face / tag checks."""
    iw, ih = s["iw"], s["ih"]
    s["faces"] = [[a * iw, b * ih, c * iw, d * ih, k] for a, b, c, d, k in FACE_BOXES.get(key, [])]
    for sh in s.get("sheets", []):
        sh["quad"] = [[x * f, y * f] for x, y in sh.pop("q")]
        for it in sh["items"]:
            if it.get("k") == "prop" and P is not None:
                src = EP / "v2" / "manual_assets" / "props" / Path(it["src"]).name
                (P / "v2" / "props").mkdir(parents=True, exist_ok=True)
                shutil.copy(src, P / "v2" / "props" / src.name)
    for m in s.get("insets", []):
        m["quad"] = [[x * f, y * f] for x, y in m.pop("q")]
        if m.get("still") and P is not None:  # a still inside the picture (a thought bubble, a tablet): crop in px of its original
            st = m.pop("still")
            path = EP / "v2" / "manual_assets" / f"{KLOT[st]}.png" if st in KLOT else EP / "images" / f"{st}.png"
            src, m["vw"], m["vh"], fi = _load(path, KLOT.get(st, st), P)
            m["img"], m["crop"] = src, [c * fi for c in m["crop"]]
        x0, y0, x1, y1 = m["crop"]
        m["W"], m["H"] = x1 - x0, y1 - y0
        if m.get("video"):
            shutil.copy(EP / "clips" / f"{m['video']}.mp4", P / "v2" / f"{m['video']}.mp4")
            m["video"], m["vw"], m["vh"] = f"v2/{m['video']}.mp4", 1920, 1094
    for d in s.get("dials", []):
        d["c"], d["r"] = [d["c"][0] * f, d["c"][1] * f], d["r"] * f
    if s.get("door"):
        s["door"]["box"] = [v * f for v in s["door"]["box"]]


def card_cam(s: dict, SW: int = 1920, SH: int = 1080) -> None:
    """A paper card lying in the picture: the camera frames the whole card with >= 7 % to spare and pushes in a little
    (Klot: text >= 2.8 % cap height, push in; R: every tag >= 6 % inside the frame)."""
    q = [p for sh in s.get("sheets", []) if sh.get("card") for p in sh["quad"]]
    if not q:
        return
    xs, ys = [p[0] for p in q], [p[1] for p in q]
    bw, bh = max(xs) - min(xs), max(ys) - min(ys)
    base = max(SW / s["iw"], SH / s["ih"])
    z = min(SW / (base * bw / 0.84), SH / (base * bh / 0.84), 2.6)
    cx, cy = (min(xs) + max(xs)) / 2 / s["iw"], (min(ys) + max(ys)) / 2 / s["ih"]
    s["cam"] = [[cx, cy, z * 0.88], [cx, cy, z]]


def resolve_base(s: dict, R: Path, P: Path) -> None:
    """Fills img/iw/ih (or video, or missing), maps the camera into a stand-in window, and places the screen quad."""
    b = s.get("base")
    s["base_kind"] = "picture"
    if b == "key":
        s["base_kind"] = "flat"
        return
    if b in CLIPS:
        src = EP / "clips" / f"{CLIPS[b]}.mp4"
        shutil.copy(src, P / "v2" / f"{CLIPS[b]}.mp4")
        s.update(video=f"v2/{CLIPS[b]}.mp4", iw=1920, ih=1094)
        try:  # a clip shorter than its shot plays a little slower (never below 0.85 x) instead of freezing
            d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(src)],
                                     capture_output=True, text=True).stdout)
            s["rate"] = round(max(0.85, min(1.0, (d - 0.05) / max(0.1, s["end"] - s["start"]))), 3)
        except Exception:  # noqa: BLE001
            pass
        try:  # the QC page's stand-in for the clip (it cannot decode H.264): the frame at the shot's settled moment
            (P / "v2" / "posters").mkdir(parents=True, exist_ok=True)
            tc = min(d - 0.05, max(0.0, (s["end"] - s["start"] - 0.3) * s.get("rate", 1.0)))
            pf = P / "v2" / "posters" / f"{s['id'].replace('/', '_')}.jpg"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{tc:.3f}", "-i", str(src), "-frames:v", "1", "-vf", "scale=1920:1094", "-q:v", "3", str(pf)], check=True)
            s["poster"] = f"v2/posters/{pf.name}"
        except Exception:  # noqa: BLE001
            pass
        if s.get("track"):  # ink laid on the still the clip was made from, carried by the clip's camera (tools/track_clip.py)
            s["track"] = json.loads((EP / "v2" / "tracks" / f"{s['track']}.json").read_text())
            for sh in s.get("sheets", []):
                sh["quad"] = [[x, y] for x, y in sh.pop("q")]
                assert all(i.get("static") for i in sh["items"]), f"{s['id']}: ink on a clip must be static (no hand on a moving picture)"
        return
    screens = json.loads((EP / "v2" / "screens.json").read_text()) if (EP / "v2" / "screens.json").exists() else {}
    kp = _find(KLOT[b], R) if b in KLOT else None
    if kp is not None:
        s["img"], s["iw"], s["ih"], f = _load(kp, KLOT[b], P)
        _world(s, f, KLOT[b], P)
        if s.get("screen"):
            q = screens.get(KLOT[b])
            if not q:
                raise SystemExit(f"{s['id']}: {KLOT[b]} has no screen quad in v2/screens.json (measure it first)")
            if isinstance(q[0][0], list):  # a picture with two screens (p04): screen -> the left one, screen2 -> the right one
                s["quad"] = [[x * f, y * f] for x, y in q[0]]
                if s.get("screen2"):
                    s["quad2"] = [[x * f, y * f] for x, y in q[1]]
            else:
                s["quad"] = [[x * f, y * f] for x, y in q]
        sq = screens.get("sheets", {}).get(KLOT[b])
        if s.get("plan"):
            if not sq:
                raise SystemExit(f"{s['id']}: {KLOT[b]} has no sheet quad in v2/screens.json")
            s["plan"]["quad"] = [[x * f, y * f] for x, y in sq]
        d = screens.get("clocks", {}).get(KLOT[b])
        if d:  # blank clock face: we paint the hands (the in-world time)
            s["dial"] = {"c": [d["c"][0] * f, d["c"][1] * f], "r": d["r"] * f, "time": s.get("dial_time")}
        return
    if b in STANDIN:
        src, (x0, y0, x1, y1), grade = STANDIN[b]
        path = _find(EP4.get(src, src), R)
        if path is None:
            raise SystemExit(f"{s['id']}: stand-in {src} not found")
        s["img"], s["iw"], s["ih"], f = _load(path, src, P)
        if src.startswith("ep04v2_"):
            src = src[len("ep04v2_"):]
        ww, wh = x1 - x0, y1 - y0
        s["cam"] = [[x0 + c[0] * ww, y0 + c[1] * wh, c[2] / ww] for c in s["cam"]]
        s["standin"] = {"for": KLOT[b], "src": src}
        s["grade"] = grade
        if s.get("screen") and src in SCREEN_PX:
            s["quad"] = [[x * f, y * f] for x, y in SCREEN_PX[src]]
        return
    if b in KLOT:
        s["base_kind"] = "missing"
        s["missing"], s["what"] = KLOT[b], MISSING.get(KLOT[b], "")
        return
    path = _find(EP4.get(b, b), R)
    if path is None:
        raise SystemExit(f"{s['id']}: picture {b} not found")
    s["img"], s["iw"], s["ih"], _f = _load(path, EP4.get(b, b), P)
    _world(s, _f, EP4.get(b, b), P)


BAND_9x16 = [0, 250, 1080, 1350]  # the 9:16 picture band: 4:5, 70 % of the height (R38 >= 50 %), captions under it
SHORT_FS = {"os": 70, "row": 70, "fee": 72, "lab": 60, "tot": 72, "big": 170}


def _projq(q, u, v):
    (x0, y0), (x1, y1), (x2, y2), (x3, y3) = q
    dx1, dx2, dy1, dy2 = x1 - x2, x3 - x2, y1 - y2, y3 - y2
    sx, sy = x0 - x1 + x2 - x3, y0 - y1 + y2 - y3
    den = dx1 * dy2 - dx2 * dy1
    g, h = (sx * dy2 - dx2 * sy) / den, (dx1 * sy - sx * dy1) / den
    a, b, d, e = x1 - x0 + g * x1, x3 - x0 + h * x3, y1 - y0 + g * y1, y3 - y0 + h * y3
    w = g * u + h * v + 1
    return (a * u + b * v + x0) / w, (d * u + e * v + y0) / w


def short_frame(s: dict, k: int = 0, compact: bool = False) -> None:
    """The 9:16 band (1080 x 1350): a laptop page fills the band's width (text big enough to read on a phone), a sheet
    plan is laid only on the part of the sheet the band shows; the picture always covers the band (never letterboxed)."""
    if s.get("base_kind") != "picture" or not s.get("iw"):
        return
    bw, bh = BAND_9x16[2], BAND_9x16[3]
    base = max(bw / s["iw"], bh / s["ih"])
    if s.get("quad") and s.get("screen"):
        qx = [p[0] for p in s["quad"]]
        qy = [p[1] for p in s["quad"]]
        # Klot (round 3): the page fits the band's width (never cut at the sides); the push is a slow settle onto that fit.
        # Repeated screen shots of one picture differ in height (repeat_shot), never in width.
        z = max(1.0, bw / (base * (max(qx) - min(qx))))
        cx, cy = (min(qx) + max(qx)) / 2 / s["iw"], (min(qy) + max(qy)) / 2 / s["ih"]
        cy += (0.0, 0.11, -0.11, 0.06)[k % 4]
        s["cam"] = [[cx, cy, z * 0.96], [cx, cy, z]]
        if s["screen"].get("mode") in ("fees", "total", "pay"):
            s["screen"]["fs"] = dict(SHORT_FS)
        if s["screen"].get("mode") == "fees" and compact:  # a Short: fee lines + the joke label in two lines
            s["screen"]["compact"] = True
            for fe in s["screen"].get("fees", []):
                lab = fe.get("label")
                if lab and len(lab) > 20 and "\n" not in lab:
                    sp = [i for i, c in enumerate(lab) if c == " "]
                    i = min(sp, key=lambda i: abs(i - len(lab) / 2))
                    fe["label"] = lab[:i] + "\n" + lab[i + 1:]
        if compact:  # a Short: every line we want read >= 2.8 % of the band (cap height): bigger page type, the switch under the price
            m = s["screen"].get("mode")
            fs = dict(s["screen"].get("fs") or {})
            if m == "bill":
                s["screen"]["fs"] = {**fs, "os": max(fs.get("os", 0), 72), "row": max(fs.get("row", 0), 72), "sub": max(fs.get("sub", 0), 72), "big": fs.get("big", 200)}
                if s["screen"].get("toggle"):
                    s["screen"]["toggle"] = dict(s["screen"]["toggle"], y=330, size=72)
            elif m in ("allin", "split", "anchor"):
                s["screen"]["fs"] = {**fs, "os": max(fs.get("os", 0), 72), "row": max(fs.get("row", 0), 72)}
            elif m == "seat":
                s["screen"]["fs"] = {**fs, "seat": 72}
            elif m == "versus":
                s["screen"]["fs"] = {**fs, "lab": 72}
            elif m == "fees":
                s["screen"]["fs"] = {**s["screen"].get("fs", {}), "lab": 72}
        s["screen"]["ts"] = 1.25
    if s.get("plan"):
        # the visible part of the sheet at the camera's start (the push only narrows it): plan drawn there, 4 % inside
        cx, cy, z = s["cam"][0]
        hw = bw / (s["iw"] * base * z) / 2
        vx0, vx1 = (cx - hw) * s["iw"], (cx + hw) * s["iw"]
        q = s["plan"]["quad"]
        def u_at(xt):
            lo, hi = 0.0, 1.0
            for _ in range(40):
                m = (lo + hi) / 2
                if _projq(q, m, 0.5)[0] < xt:
                    lo = m
                else:
                    hi = m
            return lo
        pad = 0.04 * (vx1 - vx0)
        u0, u1 = max(0.0, u_at(vx0 + pad)), min(1.0, u_at(vx1 - pad))
        s["plan"]["quad"] = [list(_projq(q, u0, 0.03)), list(_projq(q, u1, 0.03)), list(_projq(q, u1, 0.97)), list(_projq(q, u0, 0.97))]


def shift_T(T: dict, off: float) -> dict:
    """The timings with every absolute time moved by -off (a preview that starts at an ad break starts at 0)."""
    T = json.loads(json.dumps(T))
    for b in T["beats"]:
        b["start"], b["end"] = b["start"] - off, b["end"] - off
    for h in T["hits"]:
        h["at"] -= off
        if "silence_from" in h:
            h["silence_from"] -= off
    for a in T["acts"]:
        a["start"] -= off
    for k in T["breaks"]:
        k["at"] -= off
    return T


# preview segments: (kind, acts, start, end) — p2 = cold open + Act 1 (16:9 + the 9:16 sample), a2 = Act 2 (break 1 -> break 2)
def segments(T: dict, seg: str) -> list[tuple[str, tuple[str, ...], float, float]]:
    b = [k["at"] for k in T["breaks"]]
    if seg == "a2":
        return [("a2", ("A2",), b[0], b[1])]
    if seg == "a3":
        return [("a3", ("A3",), b[1], b[2])]
    if seg == "shorts":  # Klot's 7 Shorts (tools/v2_shorts.py)
        from v2_shorts import SHORTS
        return [(x["key"], tuple(sorted({b["act"] for b in T["beats"] if b["id"] in x["beats"]})), 0.0, 0.0) for x in SHORTS]
    if seg == "full":  # the whole episode in one file + the end screen (music only)
        return [("full", ("COLD", "A1", "A2", "A3", "A4"), 0.0, float(T.get("total") or max(x["end"] for x in T["beats"]) + 1.5))]
    if seg == "a4":
        return [("a4", ("A4",), b[2], float(T.get("total") or max(x["end"] for x in T["beats"]) + 1.5))]
    a1 = next(a["start"] for a in T["acts"] if a["act"] == "A1")
    return [("long", ("COLD", "A1"), 0.0, b[0]), ("short", ("COLD",), 0.0, a1)]


def main(rel: str, pub: str, outd: str, seg: str = "p2") -> int:
    import soundfile as sf
    from factory.config import load_config
    R, P, O = Path(rel), Path(pub), Path(outd)
    (P / "v2").mkdir(parents=True, exist_ok=True)
    O.mkdir(parents=True, exist_ok=True)
    T = json.loads((R / "timings.json").read_text())
    voice, sr = sf.read(R / "voice_24k.flac", dtype="float32")
    assert sr == 24000
    cfg = load_config({})
    T0, voice0 = T, voice
    plans = {}
    for kind, acts, t_in, t_out in segments(T0, seg):
        T = shift_T(T0, t_in) if t_in else T0
        voice = voice0[int(round(t_in * 24000)):]
        end = t_out - t_in
        vfile = None
        if kind.startswith("sh"):  # a Short: its lines re-spaced, its opener, its 9:16 overrides
            from v2_shorts import SHORTS, short_T
            sh = next(x for x in SHORTS if x["key"] == kind)
            T, voice = short_T(T0, voice0, sh["beats"])
            end = T["total"]
            vfile = f"voice_{kind}.flac"
            sf.write(O / vfile, voice, 24000)
            first = next(k for k in S if k == sh["beats"][0] or k == sh["beats"][0] + "a")
            patch = {first: sh["opener"], **sh.get("overrides", {})}
            saved = {k: S[k] for k in patch}
            S.update({k: dict(v, kind="pic") for k, v in patch.items()})
            try:
                beats, shots = build(T, acts, end)
            finally:
                S.update(saved)
        else:
            beats, shots = build(T, acts, end)
        if kind == "full":
            # Klot (locked): the end screen is the last 20-22 s: the Subscribe line, then music only. The last line's shot
            # ends 0.4 s after the voice; the next-case sketch and subscribe follow.
            last = shots[-1]
            last["end"] = round(max(b["end"] for b in beats) + 0.4, 3)
            t = last["end"]
            for sid, dur, spec in END_SCREEN:
                spec = json.loads(json.dumps(spec))
                spec.setdefault("kind", "pic")
                shots.append({"id": sid, "beat": "END", "act": "A4", "start": round(t, 3), "end": round(t + dur, 3), "picture": spec["base"],
                              "source": "end screen", **spec, "_sfx": [{**x, "t": round(t + x["at"], 3)} for x in spec.pop("sfx", [])],
                              "_ink": [], "clock": None, "face": spec.get("base") in FACES, "endscreen": True})
                t += dur
            end = round(t, 3)
        vertical = kind == "short" or kind.startswith("sh")
        W, H = (1080, 1920) if vertical else (1920, 1080)
        # pictures: Klot's still if it is in the repo, else an Ep.4 stand-in (tagged on screen), else a labelled placeholder
        for s in shots:
            if s["kind"] != "pic":
                continue
            resolve_base(s, R, P)
            if s.get("cardcam"):
                card_cam(s)
            if vertical:
                seen = sum(1 for x in shots[:shots.index(s)] if x.get("img") == s.get("img") and x.get("screen"))
                short_frame(s, seen, compact=kind != "short")
        stats = mix(T, beats, shots, end, voice, O / f"mix_{kind}.wav", cfg)
        data = {"W": W, "H": H, "fps": FPS, "frames": int(round(end * FPS)) + 18, "end": round(end, 3), "pal": PAL,
                "band": BAND_9x16 if vertical else None,
                "shots": [{k: v for k, v in s.items() if k != "_sfx"} for s in shots], "captions": captions(beats, kind),
                "acts": [a for a in T["acts"] if a["act"] in acts], "wipes": [s["start"] for s in shots if s["id"] in ("A1.1a", "A2.1a", "A3.1a", "A4.1")],
                "fonts": {"Anton-Regular.ttf": "Anton-Regular", "ArchivoBlack-Regular.ttf": "ArchivoBlack-Regular",
                          "SpecialElite-Regular.ttf": "SpecialElite-Regular", "PermanentMarker-Regular.ttf": "PermanentMarker-Regular",
                          "PT_Serif-Web-Regular.ttf": "PT-Serif-Web-Regular"}}
        (P / f"v2_{kind}.json").write_text(json.dumps(data, ensure_ascii=False))
        plans[kind] = {"data": data, "beats": beats, "shots": shots, "audio": {k: v for k, v in stats.items()}, "offset": t_in, "voice_file": vfile}
        print(kind, len(shots), "shots,", round(end, 2), "s", flush=True)
    (P / "hands").mkdir(exist_ok=True)
    for f in ("hand_ink_cuff.png", "hand_marker_cuff.png", "hand_stamp_cuff.png", "hand_white_cuff.png", "hand_yellow_cuff.png"):
        shutil.copy(ROOT / "assets" / "hands" / f, P / "hands" / f)
    (P / "fonts").mkdir(exist_ok=True)
    for f in next(iter(plans.values()))["data"]["fonts"]:
        if (ROOT / "assets" / "fonts" / f).exists():
            shutil.copy(ROOT / "assets" / "fonts" / f, P / "fonts" / f)
    (O / "plan.json").write_text(json.dumps({k: {"beats": v["beats"], "shots": v["shots"], "audio": v["audio"], "offset": v["offset"],
                                                 "data": v["data"]} for k, v in plans.items()}, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:5]))
