"""Ep.4 v2 PREVIEW 1: cold open + Act 1 (0:00 to the first ad break) for the Remotion layer (composition "V2"),
16:9, plus a 9:16 sample of the cold open. Plan = scenes.py (approved scene list) + timings.json (the fable voice).
Uses only assets already in the repo / Ep.4 releases; each of Klot's new stills that is still missing is held on a neutral
act-palette card labelled with its file name. Writes pilot/remotion/public/v2/{preview_long,preview_short}.json, the
pictures it needs, and the audio mixes (factory.audio.Timeline: voice, beds, sfx, brass hits, real silences).
python tools/v2_preview.py <dir with timings.json + voice_24k.flac> <remotion public dir> <out dir>"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from factory import audio as A  # noqa: E402

EP = ROOT / "episodes" / "0005-drip-pricing"
FPS = 30
LEAD = 0.15            # a picture arrives this much before its line
PAL = {"night": "#0E1A2B", "glow": "#9FD8FF", "paper": "#F3E9D2", "ink": "#1E1B18", "red": "#D2452F", "accent": "#E8B53A",
       "green": "#2E6B4F"}
MISSING_OLD = {"ep04v2_a1_glow": "Klot's GPT still: dark room at night, a laptop's glow (Grok clip k1 comes from it)",
           "ep04v2_a1_wallet": "Klot's GPT still: an open wallet with $50 on a kitchen table at night",
           "ep04v2_g04_daydream": "Klot's GPT still: Larry daydreaming of a hot dog in a thought bubble (the bubble pops on 'won't')",
           "ep04v2_g05_bomb": "Klot's GPT still: a cartoon bomb clock with a blank face (Grok clip k5: its fuse sparks)"}
MISSING = {"ep04v2_a1_wallet": "an open wallet with $50 on a kitchen table at night", "ep04v2_g01_blueprint": "a blank blueprint on a drafting table",
           "ep04v2_g04_daydream": "Larry daydreaming of a hot dog in a thought bubble", "ep04v2_g05_bomb": "a cartoon bomb clock with a blank face",
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
    "COLD.1": W_(base="a1_glow", cam=[[0.5, 0.5, 1.02], [0.6, 0.52, 1.25]]),
    "COLD.2": W_(base="s01", cam=[[0.45, 0.5, 1.04], [0.52, 0.5, 1.1]],
                 overs=[W_(t="icons_strip", items=["mask", "car", "megaphone"], cross_on=["masks", "car", "voice"])],
                 sfx=[{"kind": "pop", "on": "masks"}, {"kind": "pop", "on": "getaway"}, {"kind": "pop", "on": "raised"}]),
    "COLD.3a": W_(base="s02", cam=[[0.5, 0.45, 1.0], [0.52, 0.42, 1.12]], screen=W_(mode="form", fill=[0.1, 0.95]),
                  sfx=[{"kind": "typing", "at": 0.3, "dur": 2.4}]),
    "COLD.3b": W_(base="s03", cam=[[0.5, 0.45, 1.05], [0.58, 0.55, 1.35]], screen=W_(mode="form", fill=[1, 1], tick_on="ticked", thanks_on="thank"),
                  sfx=[{"kind": "tap", "on": "ticked"}, {"kind": "tap", "on": "thank"}]),
    "COLD.4a": W_(base="o4", cam=[[0.5, 0.5, 1.03], [0.47, 0.42, 1.12]],
                  overs=[W_(t="namecard", name="LARRY", box=[0.03, 0.08, 0.27, 0.36], box_short=[0.7, 0.04, 0.97, 0.3], stamp="FICTIONAL", stamp_on="made")],
                  sfx=[{"kind": "kachunk", "on": "made"}]),
    "COLD.4b": W_(base="s03", cam=[[0.5, 0.42, 1.1], [0.5, 0.4, 1.25]],
                  screen=W_(mode="fees", fees=[W_(name="SERVICE FEE", amt=""), W_(name="FACILITY FEE", amt=""), W_(name="PROCESSING", amt="")]),
                  overs=[W_(t="stamp", text="REAL", at_on="not", x=0.62, y=0.42, size=150)], sfx=[{"kind": "stamp", "on": "not"}]),
    "COLD.5": W_(base="o4clip", cam=[[0.55, 0.48, 1.05], [0.6, 0.45, 1.3]]),
    "COLD.6": W_(base="s02", cam=[[0.5, 0.45, 1.02], [0.5, 0.42, 1.1]], screen=W_(mode="whip", pages=["list", "seat", "form"], page_on=["found", "picked", "typed"]),
                 sfx=[{"kind": "whoosh", "on": "found"}, {"kind": "whoosh", "on": "picked"}, {"kind": "whoosh", "on": "typed"}]),
    "COLD.7": W_(base="s03", cam=[[0.5, 0.45, 1.05], [0.45, 0.4, 1.3]], screen=W_(mode="total", total="$48", total_on="number", pay_on="paid"),
                 sfx=[{"kind": "stab", "on": "number"}]),
    "COLD.8": W_(base="g01", cam=[[0.5, 0.5, 1.05], [0.5, 0.5, 1.15]], dark=True,
                 overs=[W_(t="plan_lines", color="#FFFFFF", at=0.2)]),
    "COLD.9": W_(base="l1", cam=[[0.5, 0.55, 1.05], [0.5, 0.55, 1.15]],
                 overs=[W_(t="case_folder", number="004", title="THE SEVEN-MINUTE HEIST", slide_on="Case", type_on=["Case", "seven"])],
                 sfx=[{"kind": "paper", "on": "Case", "lead": 0.45}, {"kind": "type", "on": "Case"}, {"kind": "type", "on": "seven"}]),
    "A1.1a": W_(base="a1_wallet", cam=[[0.5, 0.5, 1.02], [0.5, 0.5, 1.12]], title=["ACT 1", "THE MARK"]),
    "A1.1b": W_(base="a1_wallet", cam=[[0.5, 0.5, 1.15], [0.5, 0.48, 1.3]],
                overs=[W_(t="calendar_strip", days=["TUE", "WED", "THU", "FRI"], amount="$50", write_on="fifty")]),
    "A1.2a": W_(base="a4_seat", cam=[[0.5, 0.55, 1.03], [0.5, 0.58, 1.15]], dream=True,
                overs=[W_(t="plate", text="SATURDAY · 2 HOURS AWAY", at_on="Saturday", x=0.5, y=0.12)]),
    "A1.2b": W_(base="s06", cam=[[0.42, 0.45, 1.02], [0.36, 0.42, 1.14]]),
    "A1.3": W_(base="s02", cam=[[0.5, 0.45, 1.0], [0.52, 0.42, 1.1]],
               screen=W_(mode="tabs", tabs=[W_(price="$40", tag="ALL-IN", on="forty")], hl_on="Everything"), sfx=[{"kind": "tap", "on": "first"}]),
    "A1.4": W_(base="s03", cam=[[0.5, 0.45, 1.05], [0.42, 0.4, 1.3]],
               screen=W_(mode="tabs", tabs=[W_(price="$40", tag="ALL-IN"), W_(price="$30", on="thirty")], active=1), sfx=[{"kind": "tap", "on": "second"}]),
    "A1.5a": W_(base="s03", cam=[[0.5, 0.45, 1.1], [0.5, 0.45, 1.2]],
                screen=W_(mode="tabs", tabs=[W_(price="$40", tag="ALL-IN"), W_(price="$30")], active=1, close_on="closes", saved_on="Ten"),
                sfx=[{"kind": "tap", "on": "closes"}, {"kind": "ding", "on": "Ten"}]),
    "A1.5b": W_(base="s06", cam=[[0.32, 0.36, 1.6], [0.32, 0.33, 1.8]], overs=[W_(t="crown", draw_on="genius", x=0.47, y=0.11, w=0.16)]),
    "A1.J1a": W_(base="g04", cam=[[0.5, 0.5, 1.02], [0.5, 0.48, 1.12]]),
    "A1.J1b": W_(base="g04", cam=[[0.6, 0.35, 1.3], [0.62, 0.3, 1.5]], overs=[W_(t="pop", at_on="won't", x=0.5, y=0.35)],
                 sfx=[{"kind": "pop", "on": "won't"}]),
    "A1.6a": W_(base="s03", cam=[[0.5, 0.45, 1.05], [0.38, 0.42, 1.45]], screen=W_(mode="tabs", tabs=[W_(price="$40", tag="ALL-IN"), W_(price="$30")], active=1, single=True)),
    "A1.6b": W_(base="s02", cam=[[0.45, 0.45, 1.05], [0.45, 0.45, 1.12]], screen=W_(mode="tabs", tabs=[W_(price="$30")], active=0),
                overs=[W_(t="slots", slots_on="three", x=0.82, y=0.3)], sfx=[{"kind": "pop", "on": "three"}]),
    "A1.7a": W_(base="s02", cam=[[0.5, 0.45, 1.02], [0.5, 0.42, 1.12]], screen=W_(mode="seat", seat="G12", fly_on="Row", light_on="12"),
                sfx=[{"kind": "whoosh", "on": "Row"}, {"kind": "pop", "on": "12"}]),
    "A1.7b": W_(base="a10clip", cam=[[0.5, 0.5, 1.0], [0.5, 0.55, 1.08]]),
    "A1.8a": W_(base="s03", cam=[[0.5, 0.45, 1.05], [0.65, 0.3, 1.4]], screen=W_(mode="timer", timer_on="clock", secs=600), sfx=[{"kind": "pop", "on": "clock"}]),
    "A1.8b": W_(base="s04", cam=[[0.45, 0.45, 1.02], [0.36, 0.33, 1.3]]),
    "A1.J2a": W_(base="g05", cam=[[0.5, 0.5, 1.02], [0.5, 0.48, 1.15]]),
    "A1.J2b": W_(base="g05", cam=[[0.5, 0.55, 1.25], [0.5, 0.55, 1.35]], overs=[W_(t="wires", snip_on="wires")],
                 sfx=[{"kind": "snip", "on": "wires", "lead": -0.6}]),
    "A1.9a": W_(base="s02", cam=[[0.5, 0.45, 1.02], [0.52, 0.42, 1.12]], screen=W_(mode="form", fillat_on=["Name", "Email", "Card"]),
                sfx=[{"kind": "typing", "on": "Name", "dur": 0.6}, {"kind": "typing", "on": "Email", "dur": 0.6}, {"kind": "typing", "on": "Card", "dur": 0.9}]),
    "A1.9b": W_(base="s03", cam=[[0.5, 0.5, 1.25], [0.5, 0.52, 1.45]], screen=W_(mode="form", fill=[0.67, 1.0], digits_on="sixteen"),
                sfx=[{"kind": "typing", "on": "sixteen", "dur": 1.9}]),
    "A1.10a": W_(base="arch_a2", cam=[[0.5, 0.5, 1.02], [0.5, 0.46, 1.12]], caption="Waiting in line at Loew's Capitol, Washington, 1939 · Library of Congress"),
    "A1.10b": W_(base="arch_a2b", cam=[[0.5, 0.5, 1.02], [0.5, 0.45, 1.12]], caption=LOC_A2B),
    "A1.11a": W_(base="s02", cam=[[0.5, 0.45, 1.02], [0.52, 0.42, 1.1]], screen=W_(mode="fees", fees=[W_(name="SERVICE FEE", amt="$8", at_on="Service")]),
                 sfx=[{"kind": "kachunk", "on": "Service"}]),
    "A1.11b": W_(base="s03", cam=[[0.45, 0.4, 1.3], [0.45, 0.38, 1.45]],
                 screen=W_(mode="fees", fees=[W_(name="SERVICE FEE", amt="$8", label="FOR THE SERVICE OF CHARGING YOU A FEE", label_on="service#2")]),
                 sfx=[{"kind": "typing", "on": "service#2", "dur": 1.4}]),
    "A1.J3a": W_(base="s03", cam=[[0.5, 0.55, 1.2], [0.5, 0.58, 1.35]],
                 screen=W_(mode="fees", fees=[W_(name="SERVICE FEE", amt="$8", label="FOR THE SERVICE OF CHARGING YOU A FEE"),
                                              W_(name="FACILITY FEE", amt="$6", at_on="Facility"),
                                              W_(name="PROCESSING", amt="$4", at_on="Processing", label="TO PROCESS THE OTHER FEES", label_on="process#2")]),
                 sfx=[{"kind": "kachunk", "on": "Facility"}, {"kind": "kachunk", "on": "Processing"}, {"kind": "typing", "on": "process#2", "dur": 1.1}]),
    "A1.J3b": W_(base="s05", cam=[[0.5, 0.45, 1.02], [0.5, 0.42, 1.12]], overs=[W_(t="tags", items=["+$8", "+$6", "+$4"], at=[0.05, 0.25, 0.45], x=0.84, y=0.2)]),
    "A1.12": W_(base="key", key="$48", sub="TOTAL", at=0.15, sfx=[{"kind": "stab", "on": "Total"}]),
    "A1.13": W_(base="s05", cam=[[0.5, 0.42, 1.15], [0.5, 0.38, 1.35]],
                overs=[W_(t="bars_card", bars=[["FIRST", 30, "$30"], ["LAST", 48, "$48"]], x=0.8, y=0.62),
                       W_(t="stamp", text="+60%", at_on="sixty", x=0.78, y=0.25, size=120)], sfx=[{"kind": "stamp", "on": "sixty"}]),
    "A1.14a": W_(base="s03", cam=[[0.5, 0.45, 1.08], [0.5, 0.42, 1.2]], screen=W_(mode="versus", left="$40", right="$48", badge="+$8", badge_on="eight"),
                 sfx=[{"kind": "pop", "on": "eight"}]),
    "A1.14b": W_(base="a1_wallet", cam=[[0.5, 0.5, 1.2], [0.5, 0.5, 1.35]], overs=[W_(t="note", text="$2 LEFT UNTIL FRIDAY", write_on="two", x=0.62, y=0.2)]),
    "A1.15a": W_(base="s02", cam=[[0.5, 0.45, 1.02], [0.55, 0.42, 1.12]], screen=W_(mode="timer", timer_=0.0, secs=360)),
    "A1.15b": W_(base="a4_seat", cam=[[0.5, 0.55, 1.08], [0.5, 0.58, 1.2]], dream=True),
    "A1.16": W_(base="s03", cam=[[0.5, 0.45, 1.1], [0.55, 0.55, 1.25]], screen=W_(mode="pay", press_on="presses"), sfx=[{"kind": "tap", "on": "presses"}]),
    "A1.17a": W_(base="s04", cam=[[0.42, 0.42, 1.1], [0.38, 0.38, 1.22]],
                 overs=[W_(t="timeline_strip", steps=[["8:12", "TABS"], ["8:13", "SEAT"], ["8:14", "CLOCK"], ["8:16", "CARD"], ["8:18", "FEES"], ["8:19", "PAY"]], at=0.2)]),
    "A1.17b": W_(base="o4", cam=[[0.45, 0.35, 1.25], [0.45, 0.32, 1.4]], overs=[W_(t="tag_circle", text="$18", x=0.78, y=0.3, circle_on="number")]),
    "A1.18": W_(base="s01", cam=[[0.5, 0.5, 1.05], [0.5, 0.48, 1.15]],
                overs=[W_(t="price_pair", left="$40", right="$48", cross_at=0.4, q_on="forty-eight")], sfx=[{"kind": "stamp", "on": "forty-eight"}]),
    "A1.19a": W_(base="g01", cam=[[0.5, 0.5, 1.02], [0.5, 0.48, 1.12]], overs=[W_(t="plan_lines", color="#FFFFFF", at=0.2)]),
    "A1.19b": W_(base="a5", cam=[[0.5, 0.45, 1.5], [0.5, 0.5, 1.02]], green_creep=True),
}
for _k, _v in list(S.items()):  # sfx inside a shot spec is the mixer's, not the layer's
    _v.setdefault("kind", "pic")
# logical stills -> Klot's file when it is in the repo, else an Ep.4 stand-in window (x0, y0, x1, y1 of the stand-in) or a placeholder
KLOT = {"a1_glow": "ep04v2_a1_glow", "a1_wallet": "ep04v2_a1_wallet", "a4_seat": "ep04v2_a4_seat", "g01": "ep04v2_g01_blueprint",
        "g04": "ep04v2_g04_daydream", "g05": "ep04v2_g05_bomb", "s01": "ep04v2_s01_flat_wide", "s02": "ep04v2_s02_over_shoulder",
        "s03": "ep04v2_s03_laptop_close", "s04": "ep04v2_s04_wall_clock", "s05": "ep04v2_s05_gulp", "s06": "ep04v2_s06_smug"}
STANDIN = {"a1_glow": ("ep04v2_s01_flat_wide", [0.16, 0.14, 0.6, 0.6], "dark"), "s01": ("o4", [0.0, 0.0, 1.0, 1.0], "night"),
           "s02": ("m1b-blank", [0.08, 0.04, 0.92, 0.886], ""), "s03": ("m1b-blank", [0.275, 0.128, 0.726, 0.582], ""),
           "s05": ("b1", [0.2, 0.02, 0.56, 0.38], ""), "s06": ("o4", [0.23, 0.02, 0.63, 0.42], ""), "a4_seat": ("a11", [0.0, 0.0, 1.0, 1.0], "")}
EP4 = {"o4": "o4", "l1": "l1", "a5": "a5", "arch_a2": "archive-a2", "arch_a2b": "archive-a2b", "m1b-blank": "m1b", "b1": "b1", "a11": "a11"}
CLIPS = {"o4clip": "o4", "a10clip": "a10"}
SCREEN_PX = {"m1b-blank": [[440, 122], [938, 122], [938, 422], [440, 422]]}  # the blank screen (px of the 1376x768 still)
CLOCK = {"A1.1": "8:12", "A1.7": "8:13", "A1.8": "8:14", "A1.9": "8:16", "A1.11": "8:18", "A1.16": "8:19"}
TICKS = ("A1.8", "A1.16")      # the hold clock ticks from 8:14 until Pay
HEART = ("A1.11", "A1.16")     # heartbeat from 8:18 until Pay (stops before the silence)


def _norm(w: str) -> str:
    return "".join(c for c in w.lower() if c.isalnum() or c in "-$:")


MIN_SHOT = 1.4


def anchors(spec) -> list[str]:
    out = []
    for k, v in spec.items():
        if isinstance(v, dict):
            out += anchors(v)
        elif k.endswith("_on"):
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
        if beats[i - 1]["id"] in hit and i > 0:
            s = hit[beats[i - 1]["id"]]["at"]  # the picture cuts on the brass hit; the silence holds the next card
        vis.append(s)
    shots, clock = [], None
    for i, b in enumerate(beats):
        clock = CLOCK.get(b["id"], clock)
        a, z = vis[i], (vis[i + 1] if i + 1 < len(beats) else end_t)
        n = len(b["shots"])
        cuts = [a + (z - a) * k / n for k in range(n + 1)]
        # a shot's word anchors must fall inside it: move the cuts (never under MIN_SHOT on either side)
        for k in range(n):
            sid = b["id"] + (chr(97 + k) if n > 1 else "")
            ws = [word_time(b, w) for w in anchors(S[sid])]
            if not ws:
                continue
            if k > 0 and min(ws) - 0.35 < cuts[k]:
                cuts[k] = max(cuts[k - 1] + MIN_SHOT, min(ws) - 0.35)
            if k < n - 1 and max(ws) + 0.6 > cuts[k + 1]:
                cuts[k + 1] = min(cuts[k + 2] - MIN_SHOT, max(ws) + 0.6)
        for k in range(n):
            sid = b["id"] + (chr(97 + k) if n > 1 else "")
            spec = json.loads(json.dumps(S[sid]))
            s0, s1 = cuts[k], cuts[k + 1]
            def resolve(d):  # "<key>_on": word(s) -> "<key>_": seconds from the shot start (nested dicts too)
                for key in list(d):
                    if isinstance(d[key], dict):
                        resolve(d[key])
                    elif isinstance(d[key], list) and d[key] and all(isinstance(x, dict) for x in d[key]):
                        for x in d[key]:
                            resolve(x)
                    elif key.endswith("_on"):
                        v = d.pop(key)
                        d[key[:-3] + "_"] = ([round(word_time(b, x) - s0, 3) for x in v] if isinstance(v, list)
                                             else round(word_time(b, v) - s0, 3))
            resolve(spec)
            for t in spec.get("tabs", []):
                if "on" in t:
                    t["at"] = round(word_time(b, t.pop("on")) - s0, 3)
            ink = []  # (t0, t1) absolute: the hand lays ink (scratch sound exactly then, R34)
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
    for b in beats:
        for c in group_captions(b["words"], b["start"], mc, mw):
            out.append({"start": round(c.start, 3), "end": round(c.end, 3),
                        "words": [[w, round(s, 3), round(e, 3)] for w, (s, e) in zip(c.words, c.word_times)]})
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
    tl.music_cue(0.0, "ub_ticking_tension")
    silences = []
    for h in hits:
        tl.add_stab(h["at"], "ub_sting_brass", dur=T["hit_len"])
        s0 = h["at"] + T["hit_len"]
        silences.append((s0, s0 + 1.0))
        tl.music_cue(h["at"] + 0.2, "none")
        tl.music_cue(s0 + 1.0, "ub_ticking_tension")
    if "A1" in acts and acts["A1"] < end_t:
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


def resolve_base(s: dict, R: Path, P: Path) -> None:
    """Fills img/iw/ih (or video, or missing), maps the camera into a stand-in window, and places the screen quad."""
    b = s.get("base")
    s["base_kind"] = "picture"
    if b == "key":
        s["base_kind"] = "flat"
        return
    if b in CLIPS:
        shutil.copy(EP / "clips" / f"{CLIPS[b]}.mp4", P / "v2" / f"{CLIPS[b]}.mp4")
        s.update(video=f"v2/{CLIPS[b]}.mp4", iw=1920, ih=1094)
        return
    screens = json.loads((EP / "v2" / "screens.json").read_text()) if (EP / "v2" / "screens.json").exists() else {}
    kp = _find(KLOT[b], R) if b in KLOT else None
    if kp is not None:
        s["img"], s["iw"], s["ih"], f = _load(kp, KLOT[b], P)
        if s.get("screen"):
            q = screens.get(KLOT[b])
            if not q:
                raise SystemExit(f"{s['id']}: {KLOT[b]} has no screen quad in v2/screens.json (measure it first)")
            s["quad"] = [[x * f, y * f] for x, y in q]
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


def main(rel: str, pub: str, outd: str) -> int:
    import soundfile as sf
    from factory.config import load_config
    R, P, O = Path(rel), Path(pub), Path(outd)
    (P / "v2").mkdir(parents=True, exist_ok=True)
    O.mkdir(parents=True, exist_ok=True)
    T = json.loads((R / "timings.json").read_text())
    voice, sr = sf.read(R / "voice_24k.flac", dtype="float32")
    assert sr == 24000
    cfg = load_config({})
    end_long = T["breaks"][0]["at"]
    a1 = next(a["start"] for a in T["acts"] if a["act"] == "A1")
    plans = {}
    for kind, acts, end in (("long", ("COLD", "A1"), end_long), ("short", ("COLD",), a1)):
        beats, shots = build(T, acts, end)
        W, H = (1920, 1080) if kind == "long" else (1080, 1920)
        # pictures: Klot's still if it is in the repo, else an Ep.4 stand-in (tagged on screen), else a labelled placeholder
        for s in shots:
            if s["kind"] != "pic":
                continue
            resolve_base(s, R, P)
        stats = mix(T, beats, shots, end, voice, O / f"mix_{kind}.wav", cfg)
        data = {"W": W, "H": H, "fps": FPS, "frames": int(round(end * FPS)) + 18, "end": round(end, 3), "pal": PAL,
                "band": None if kind == "long" else [0, 380, 1080, 1080],
                "shots": [{k: v for k, v in s.items() if k != "_sfx"} for s in shots], "captions": captions(beats, kind),
                "acts": [a for a in T["acts"] if a["act"] in acts], "wipes": [s["start"] for s in shots if s["id"] == "A1.1a"],
                "fonts": {"Anton-Regular.ttf": "Anton-Regular", "ArchivoBlack-Regular.ttf": "ArchivoBlack-Regular",
                          "SpecialElite-Regular.ttf": "SpecialElite-Regular", "PermanentMarker-Regular.ttf": "PermanentMarker-Regular",
                          "PT_Serif-Web-Regular.ttf": "PT-Serif-Web-Regular"}}
        (P / f"v2_{kind}.json").write_text(json.dumps(data, ensure_ascii=False))
        plans[kind] = {"data": data, "beats": beats, "shots": shots, "audio": {k: v for k, v in stats.items()}}
        print(kind, len(shots), "shots,", round(end, 2), "s", flush=True)
    (P / "hands").mkdir(exist_ok=True)
    for f in ("hand_ink_cuff.png", "hand_marker_cuff.png", "hand_stamp_cuff.png"):
        shutil.copy(ROOT / "assets" / "hands" / f, P / "hands" / f)
    (P / "fonts").mkdir(exist_ok=True)
    for f in plans["long"]["data"]["fonts"]:
        if (ROOT / "assets" / "fonts" / f).exists():
            shutil.copy(ROOT / "assets" / "fonts" / f, P / "fonts" / f)
    (O / "plan.json").write_text(json.dumps({k: {"beats": v["beats"], "shots": v["shots"], "audio": v["audio"],
                                                 "data": v["data"]} for k, v in plans.items()}, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
