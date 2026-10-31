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
MISSING = {"ep04v2_a1_glow": "Klot's GPT still: dark room at night, a laptop's glow (Grok clip k1 comes from it)",
           "ep04v2_a1_wallet": "Klot's GPT still: an open wallet with $50 on a kitchen table at night"}
LOC_A2B = "Waiting to buy tickets, Radio City Music Hall, New York, 1942 · Library of Congress"

# ---------------------------------------------------------------------------------------------------------------- plan
# one entry per shot id of docs/ep04v2_scenes.md (COLD + Act 1). "*_on": a word of the shot's line (prefix match) whose
# spoken start becomes the matching key in seconds from the shot start. sfx: {kind, on|at}.
S: dict[str, dict] = {
    "COLD.1": {"kind": "missing", "file": "ep04v2_a1_glow"},
    "COLD.2": {"kind": "icons", "items": ["mask", "car", "megaphone"], "cross_on": ["masks", "car", "voice"],
               "sfx": [{"kind": "pop", "on": "masks"}, {"kind": "pop", "on": "getaway"}, {"kind": "pop", "on": "raised"}]},
    "COLD.3a": {"kind": "screen", "mode": "form", "fill": [0.1, 0.95], "sfx": [{"kind": "typing", "at": 0.3, "dur": 2.4}]},
    "COLD.3b": {"kind": "screen", "mode": "form", "fill": [1, 1], "tick_on": "ticked", "thanks_on": "thank",
                "sfx": [{"kind": "tap", "on": "ticked"}, {"kind": "tap", "on": "thank"}]},
    "COLD.4a": {"kind": "still", "src": "o4", "cam": [[0.5, 0.5, 1.03], [0.47, 0.42, 1.12]],
                "namecard": {"name": "LARRY", "box": [0.03, 0.08, 0.27, 0.36], "stamp": "FICTIONAL", "stamp_on": "made"},
                "sfx": [{"kind": "stamp", "on": "made"}]},
    "COLD.4b": {"kind": "feecard", "lines": ["SERVICE FEE", "FACILITY FEE", "PROCESSING"], "amounts": None,
                "stamp": "REAL", "stamp_on": "not", "sfx": [{"kind": "stamp", "on": "not"}]},
    "COLD.5": {"kind": "still", "src": "o4", "cam": [[0.55, 0.48, 1.05], [0.6, 0.45, 1.35]], "glow": True},
    "COLD.6": {"kind": "screen", "mode": "whip", "pages": ["list", "seat", "form"], "page_on": ["found", "picked", "typed"],
               "sfx": [{"kind": "whoosh", "on": "found"}, {"kind": "whoosh", "on": "picked"}, {"kind": "whoosh", "on": "typed"}]},
    "COLD.7": {"kind": "screen", "mode": "total", "total": "$48", "total_on": "number", "pay_on": "paid",
               "sfx": [{"kind": "stab", "on": "number"}]},
    "COLD.8": {"kind": "blueprint", "dark": True},
    "COLD.9": {"kind": "casefolder", "number": "004", "title": "THE SEVEN-MINUTE HEIST", "slide_on": "Case",
               "type_on": ["Case", "seven"], "sfx": [{"kind": "paper", "on": "Case", "lead": 0.45}, {"kind": "type", "on": "Case"},
                                                     {"kind": "type", "on": "seven"}]},
    "A1.1a": {"kind": "missing", "file": "ep04v2_a1_wallet", "title": ["ACT 1", "THE MARK"]},
    "A1.1b": {"kind": "calendar", "from": "$50", "to": "$50", "days": ["TUE", "WED", "THU", "FRI"]},
    "A1.2a": {"kind": "route", "from": "LARRY'S FLAT", "to": "THE CONCERT HALL", "label": "2 HOURS", "draw_on": "two",
              "day": "SATURDAY"},
    "A1.2b": {"kind": "still", "src": "o4", "cam": [[0.45, 0.33, 1.25], [0.43, 0.27, 1.6]]},
    "A1.3": {"kind": "screen", "mode": "tabs", "tabs": [{"price": "$40", "tag": "ALL-IN", "on": "forty"}], "hl_on": "Everything",
             "sfx": [{"kind": "tap", "on": "first"}]},
    "A1.4": {"kind": "screen", "mode": "tabs", "tabs": [{"price": "$40", "tag": "ALL-IN"}, {"price": "$30", "on": "thirty"}],
             "active": 1, "sfx": [{"kind": "tap", "on": "second"}]},
    "A1.5": {"kind": "screen", "mode": "tabs", "tabs": [{"price": "$40", "tag": "ALL-IN"}, {"price": "$30"}], "active": 1,
             "close_on": "closes", "saved_on": "Ten", "crown_on": "genius",
             "sfx": [{"kind": "tap", "on": "closes"}, {"kind": "ding", "on": "Ten"}, {"kind": "marker", "on": "genius", "dur": 0.7}]},
    "A1.6a": {"kind": "bignum", "text": "$30"},
    "A1.6b": {"kind": "bignum", "text": "$30", "slots_on": "three", "slots": 3, "sfx": [{"kind": "pop", "on": "three"}]},
    "A1.7a": {"kind": "screen", "mode": "seat", "seat": "G12", "fly_on": "Row", "light_on": "12",
              "sfx": [{"kind": "whoosh", "on": "Row"}, {"kind": "pop", "on": "12"}]},
    "A1.7b": {"kind": "clip", "src": "a10", "cam": [[0.5, 0.5, 1.0], [0.5, 0.55, 1.08]]},
    "A1.8a": {"kind": "screen", "mode": "timer", "timer_on": "clock", "from": 600, "note": "Your ticket is held for 10 minutes",
              "sfx": [{"kind": "pop", "on": "clock"}]},
    "A1.8b": {"kind": "timer", "from": 596},
    "A1.9": {"kind": "screen", "mode": "form", "fillat_on": ["Name", "Email", "Card"], "digits_on": "sixteen",
             "sfx": [{"kind": "typing", "on": "Name", "dur": 0.6}, {"kind": "typing", "on": "Email", "dur": 0.6},
                     {"kind": "typing", "on": "sixteen", "dur": 2.0}]},
    "A1.10a": {"kind": "fan", "pages": ["tabs", "seat", "timer", "form"]},
    "A1.10b": {"kind": "archive", "src": "archive-a2b", "caption": LOC_A2B, "cam": [[0.5, 0.5, 1.02], [0.5, 0.45, 1.12]]},
    "A1.11a": {"kind": "screen", "mode": "fees", "fees": [["SERVICE FEE", "$8", "Service"], ["FACILITY FEE", "$6", "Facility"],
                                                         ["PROCESSING", "$4", "Processing"]],
               "sfx": [{"kind": "kachunk", "on": "Service"}, {"kind": "kachunk", "on": "Facility"}, {"kind": "kachunk", "on": "Processing"}]},
    "A1.11b": {"kind": "bignum", "text": "$30", "slots": 3, "filled": ["+$8", "+$6", "+$4"], "fill_at": [0.02, 0.14, 0.26]},
    "A1.12": {"kind": "screen", "mode": "total", "total": "$48", "total_on": "Total", "fees_shown": True,
              "sfx": [{"kind": "stab", "on": "Total"}]},
    "A1.13": {"kind": "bars", "bars": [["FIRST SCREEN", 30, "$30"], ["LAST SCREEN", 48, "$48"]], "stamp": "+60%", "stamp_on": "sixty",
              "sfx": [{"kind": "stamp", "on": "sixty"}]},
    "A1.14a": {"kind": "versus", "left": "$40", "left_tag": "THE TAB HE CLOSED", "right": "$48", "right_tag": "WHAT HE PAYS",
               "badge": "+$8", "badge_on": "eight", "sfx": [{"kind": "pop", "on": "eight"}]},
    "A1.14b": {"kind": "missing", "file": "ep04v2_a1_wallet", "sub": "$2 LEFT UNTIL FRIDAY", "sub_on": "two"},
    "A1.15a": {"kind": "timer", "from": 360, "big": True},
    "A1.15b": {"kind": "still", "src": "a11", "cam": [[0.5, 0.55, 1.05], [0.5, 0.6, 1.18]], "dream": True},
    "A1.16": {"kind": "screen", "mode": "pay", "press_on": "presses", "sfx": [{"kind": "tap", "on": "presses"}]},
    "A1.17a": {"kind": "timeline", "steps": [["8:12", "TWO TABS"], ["8:13", "SEAT"], ["8:14", "CLOCK"], ["8:16", "CARD"],
                                             ["8:18", "FEES"], ["8:19", "PAY"]]},
    "A1.17b": {"kind": "timeline", "steps": [["8:12", "TWO TABS"], ["8:13", "SEAT"], ["8:14", "CLOCK"], ["8:16", "CARD"],
                                             ["8:18", "FEES"], ["8:19", "PAY"]], "drawn": True, "total": "$18", "circle_on": "number",
               "sfx": [{"kind": "marker", "on": "number", "dur": 0.6}]},
    "A1.18": {"kind": "versus", "left": "$40", "left_tag": "CLOSED", "left_cross": True, "right": "$48", "right_tag": "PAID",
              "badge": "?", "badge_on": "forty-eight", "sfx": [{"kind": "stamp", "on": "forty-eight"}]},
    "A1.19a": {"kind": "blueprint", "dark": True, "tint": "green"},
    "A1.19b": {"kind": "still", "src": "a5", "cam": [[0.5, 0.45, 1.5], [0.5, 0.5, 1.02]], "green_creep": True},
}
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
    return out


def word_time(beat: dict, prefix: str) -> float:
    p = _norm(prefix)
    for w, s, _e in beat["words"]:
        if _norm(w).startswith(p):
            return beat["start"] + s
    raise KeyError(f"{beat['id']}: no word '{prefix}' in {beat['text']!r}")


def build(T: dict, acts: tuple[str, ...], end_t: float) -> tuple[list[dict], list[dict]]:
    beats = [b for b in T["beats"] if b["act"] in acts]
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
                    elif key.endswith("_on"):
                        v = d.pop(key)
                        d[key[:-3] + "_"] = ([round(word_time(b, x) - s0, 3) for x in v] if isinstance(v, list)
                                             else round(word_time(b, v) - s0, 3))
            resolve(spec)
            for t in spec.get("tabs", []):
                if "on" in t:
                    t["at"] = round(word_time(b, t.pop("on")) - s0, 3)
            for f in spec.get("fees", []):
                if len(f) == 3:
                    f[2] = round(word_time(b, f[2]) - s0, 3)
            ev = []
            for x in spec.pop("sfx", []):
                at = (word_time(b, x["on"]) - x.get("lead", 0.0)) if "on" in x else s0 + x["at"]
                ev.append({**x, "t": round(at, 3)})
            key = b["id"]
            shots.append({"id": sid, "beat": b["id"], "act": b["act"], "start": round(s0, 3), "end": round(s1, 3),
                          "picture": b["shots"][k]["picture"], "source": b["shots"][k]["source"], **spec, "_sfx": ev,
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
        # pictures
        for s in shots:
            if s["kind"] in ("still", "archive"):
                src = s["src"]
                cand = [EP / "images" / f"{src}.png", R / "frames" / f"{src}.png"] + sorted((R / "frames").glob(f"{src}-*.png"))
                cand = [c for c in cand if c.exists() and not c.name.endswith(".depth.png")]
                if not cand:
                    raise SystemExit(f"{s['id']}: picture {src} not found")
                from PIL import Image
                im = Image.open(cand[0]).convert("RGB")
                if im.width > 2600:
                    im = im.resize((2600, round(im.height * 2600 / im.width)), Image.LANCZOS)
                im.save(P / "v2" / f"{src}.jpg", quality=92)
                s["img"], s["iw"], s["ih"] = f"v2/{src}.jpg", im.width, im.height
            if s["kind"] == "clip":
                shutil.copy(EP / "clips" / f"{s['src']}.mp4", P / "v2" / f"{s['src']}.mp4")
                s["video"] = f"v2/{s['src']}.mp4"
            if s["kind"] == "missing":
                s["what"] = MISSING[s["file"]]
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
    (P / "fonts").mkdir(exist_ok=True)
    for f in plans["long"]["data"]["fonts"]:
        if (ROOT / "assets" / "fonts" / f).exists():
            shutil.copy(ROOT / "assets" / "fonts" / f, P / "fonts" / f)
    (O / "plan.json").write_text(json.dumps({k: {"beats": v["beats"], "shots": v["shots"], "audio": v["audio"],
                                                 "data": v["data"]} for k, v in plans.items()}, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
