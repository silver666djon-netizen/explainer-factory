"""Turns beats + narration + images into a timed plan and streams frames into FFmpeg."""
from __future__ import annotations

import math
import re
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

from . import audio as A
from .config import hex_to_rgb, resolve_font
from .images import is_archive_photo
from .props import CaseFileShot, MazeShot, MugshotShot, NewsreelShot, RouletteShot, SlotShot, projector_sfx_times
from .depth import load_depth
from .shots import ChartShot, ClipShot, DocShot, ImageShot, KineticShot, Shot, StatShot, TitleShot
from .text import blend, fit_font, font, text_block, wrap

MOTION_CYCLE = ["zoom_in", "pan_right", "zoom_out", "pan_left", "drift", "pan_up", "zoom_in", "pan_down"]


@dataclass
class Caption:
    start: float
    end: float
    words: list[str]
    word_times: list[tuple[float, float]]
    speaker: str = "narrator"


@dataclass
class Counter:
    start: float
    end: float
    frm: float
    to: float
    dur: float
    prefix: str
    suffix: str
    decimals: int
    label: str


@dataclass
class Card:
    start: float
    end: float
    text: str
    corner: bool = False  # top-left instead of top-centre (keeps faces/subjects of pictures clear)
    hook: bool = False  # Shorts opener: fully visible from the first frame


@dataclass
class Bubble:
    start: float
    end: float
    text: str
    x: float
    y: float
    tail: str
    cur: tuple | None = None  # live screen centre (px), anchored to the picture under it


@dataclass
class Cta:
    start: float
    end: float
    click: float  # moment the button gets "pressed" (turns to SUBSCRIBED + bell rings)


@dataclass
class Plan:
    size: tuple[int, int]
    kind: str  # "long" or "short"
    total: float
    shots: list[Shot] = field(default_factory=list)
    captions: list[Caption] = field(default_factory=list)
    cards: list[Card] = field(default_factory=list)
    bubbles: list[Bubble] = field(default_factory=list)
    counters: list[Counter] = field(default_factory=list)
    ctas: list[Cta] = field(default_factory=list)
    inserts: list = field(default_factory=list)  # cut-out / clipping / photo overlays (factory.inserts)
    punches: list[float] = field(default_factory=list)
    beat_starts: dict[str, float] = field(default_factory=dict)
    timeline: A.Timeline | None = None
    ledger: object | None = None  # factory.devices.Ledger (Larry's tab, top-right)
    stamps: list = field(default_factory=list)  # (start, end, text) rubber stamps over the picture
    labels: list = field(default_factory=list)  # (start, end, text) small RECONSTRUCTION-style labels, bottom-right
    ledger_hide: list = field(default_factory=list)
    hand_cuts: list = field(default_factory=list)  # times a drawing hand acts on a picture (counts as a picture change)


def group_captions(words, offset: float, max_chars: int, max_words: int, speaker: str = "narrator") -> list[Caption]:
    out: list[Caption] = []
    cur: list[tuple[str, float, float]] = []

    def flush():
        if cur:
            out.append(Caption(offset + cur[0][1], offset + cur[-1][2], [w for w, _, _ in cur],
                               [(offset + s, offset + e) for _, s, e in cur], speaker))

    for w, s, e in words:
        w = w.strip()
        if not w:
            continue
        chars = sum(len(x) + 1 for x, _, _ in cur) + len(w)
        if cur and (len(cur) >= max_words or chars > max_chars):
            flush()
            cur = []
        cur.append((w, s, e))
        if re.search(r"[.!?;:…]$", w):
            flush()
            cur = []
    flush()
    for a, b in zip(out, out[1:]):  # stay until the next chunk (no flicker)
        if b.start - a.end < 0.6:
            a.end = b.start
    return out


def _clip_path(beat: dict, visual: dict, beat_lookup: dict[str, dict]):
    """episodes/<slug>/clips/<beat id>.mp4 (or the reused beat's clip)."""
    from pathlib import Path as _P
    if visual.get("_clip"):
        return _P(visual["_clip"])
    if visual.get("type") == "reuse":
        srcv = beat_lookup[visual["beat"]]["visual"]
        if srcv.get("_clip"):
            return _P(srcv["_clip"])
    ep_dir = beat.get("_episode_dir") or visual.get("_episode_dir")
    keys = [beat["id"]]
    if visual.get("type") == "reuse":
        keys.insert(0, visual["beat"])
    for key in keys:
        for ext in (".mp4", ".mov", ".webm"):
            if ep_dir and (_P(ep_dir) / "clips" / f"{key}{ext}").exists():
                return _P(ep_dir) / "clips" / f"{key}{ext}"
    return None


def _image_keys(visual: dict, beat_lookup: dict[str, dict]) -> list[str]:
    if visual["type"] in ("image", "clip"):
        n = len(visual.get("prompts") or [visual["prompt"]])
        return [visual["_beat"] if i == 0 else f"{visual['_beat']}.{i}" for i in range(n)]
    if visual["type"] in ("photo", "mugshot", "archive"):
        return [visual["_beat"]]
    if visual["type"] == "clip" and (visual.get("file") or visual.get("stock")):
        return []
    if visual["type"] == "reuse":
        src = beat_lookup[visual["beat"]]["visual"]
        if src["type"] in ("photo", "mugshot", "archive"):
            return [visual["beat"]]
        if src["type"] == "clip" and not (src.get("prompts") or src.get("prompt")):
            return [visual["beat"]]  # stock clip: its illustration fallback lives under the beat id
        n = len(src.get("prompts") or [src["prompt"]])
        idx = int(visual.get("index", 0)) % n
        return [visual["beat"] if idx == 0 else f"{visual['beat']}.{idx}"]
    return []


def _norm_word(w: str) -> str:
    return "".join(c for c in w.lower() if c.isalnum())


def word_time(words, phrase: str) -> float | None:
    """Start time (s from the beat's narration start) of the first occurrence of a word/phrase in the narration."""
    target = [_norm_word(x) for x in str(phrase).split() if _norm_word(x)]
    if not target or not words:
        return None
    toks = [_norm_word(w[0]) for w in words]
    for i in range(len(toks) - len(target) + 1):
        if toks[i : i + len(target)] == target:
            return float(words[i][1])
    return None


def _timed(spec: dict, words, default: float, key: str = "at") -> float:
    """'on': 'word' syncs an event to the moment that word is spoken; otherwise the fixed 'at' seconds."""
    if spec.get("on"):
        wt = word_time(words, spec["on"])
        if wt is not None:
            return wt + float(spec.get("delay", 0.0))
    return float(spec.get(key, default))


def _with_pause(v: dict, word: str, sec: float) -> tuple[dict, float | None]:
    """Insert `sec` of silence right before `word` (a reveal lands in silence). Returns the new voiced beat and
    the (shifted) start of that word."""
    wt = word_time(v["words"], word)
    if wt is None or sec <= 0:
        return v, None
    sr = v["sr"]
    cut = max(0, int((wt - 0.03) * sr))
    audio = np.concatenate([v["audio"][:cut], np.zeros(int(sec * sr), dtype=v["audio"].dtype), v["audio"][cut:]])
    words = [(w, s0 + (sec if s0 >= wt - 0.03 else 0.0), e0 + (sec if s0 >= wt - 0.03 else 0.0)) for w, s0, e0 in v["words"]]
    return {**v, "audio": audio, "words": words, "duration": v["duration"] + sec}, wt + sec


def _crop_pic(im: Image.Image, c: dict):
    """A push-in on a detail: {"center": [x, y], "zoom": z} in fractions of the picture -> (picture, box)."""
    W0, H0 = im.size
    z = max(1.05, float(c.get("zoom", 2.0)))
    cx, cy = c.get("center", [0.5, 0.5])
    w, h = W0 / z, H0 / z
    x0 = min(max(0.0, cx * W0 - w / 2), W0 - w)
    y0 = min(max(0.0, cy * H0 - h / 2), H0 - h)
    out = im.crop((int(x0), int(y0), int(x0 + w), int(y0 + h))).resize((W0, H0), Image.LANCZOS)
    return out, (x0 / W0, y0 / H0, (x0 + w) / W0, (y0 + h) / H0)


def _remap_mark(m: dict, box) -> dict:
    bx0, by0, bx1, by1 = box
    sx, sy = bx1 - bx0, by1 - by0
    m = dict(m)
    for k in ("x", "text_x", "from_x"):
        if k in m:
            m[k] = (float(m[k]) - bx0) / sx
    for k in ("y", "text_y", "from_y"):
        if k in m:
            m[k] = (float(m[k]) - by0) / sy
    if "w" in m:
        m["w"] = float(m["w"]) / sx
    if "h" in m:
        m["h"] = float(m["h"]) / sy
    return m


def still_runs(plan: Plan, limit: float = 8.0) -> list[tuple[float, float, str]]:
    """Stretches where ONE illustration stays on screen longer than `limit` s with nothing cutting in
    (a new picture, an archive photo, a card, or an insert sliding over it). Channel rule from Ep. 3 on."""
    runs, cur = [], None
    cuts = sorted([ins.start for ins in plan.inserts] + list(plan.hand_cuts))
    shots = sorted(plan.shots, key=lambda x: x.start)
    for k, sh in enumerate(shots):
        src = getattr(sh, "_still_src", None)
        nxt = shots[k + 1].start if k + 1 < len(shots) else plan.total  # a gap keeps the last frame on screen
        if src is None or getattr(sh, "_archive", False) or is_archive_photo(src):
            if cur:
                runs.append(cur)
            cur = None
            continue
        end = max(sh.start + sh.duration, nxt)
        if cur and cur[2] == src and abs(cur[1] - sh.start) < 0.05:
            cur = (cur[0], end, src)
        else:
            if cur:
                runs.append(cur)
            cur = (sh.start, end, src)
    if cur:
        runs.append(cur)
    out = []
    for a, b, src in runs:  # an insert landing on the picture splits the run
        pts = [a] + [c for c in cuts if a + 0.05 < c < b - 0.05] + [b]
        longest = max(pts[k + 1] - pts[k] for k in range(len(pts) - 1))
        if longest > limit + 1e-3:
            k = max(range(len(pts) - 1), key=lambda k: pts[k + 1] - pts[k])
            out.append((pts[k], pts[k + 1], Path(src).stem))
    return out


def build_plan(beats, voiced, images, cfg, size, kind, beat_lookup, extra_pause: float = 0.0) -> Plan:
    vcfg = cfg["video"]
    reveal_hits = []  # (beat index, word time, sfx) after inserted pauses
    voiced = list(voiced)
    for i, b in enumerate(beats):
        pa = b.get("pause_at")
        if pa:
            voiced[i], wt = _with_pause(voiced[i], pa["word"], float(pa.get("sec", 1.2)))
            if wt is not None and pa.get("hit", "stamp"):
                reveal_hits.append((i, wt, pa.get("hit", "stamp")))
    pause = float(vcfg.get("pause_after_beat", 0.18)) + extra_pause
    max_shot = float(vcfg.get("max_shot_seconds", 3.2))
    min_shot = float(vcfg.get("min_shot_seconds", 1.4))
    lead = 0.25 if kind == "long" else 0.05
    tail = 0.8 if kind == "long" else 0.15

    t = lead
    starts, durations, shot_starts = [], [], []
    block0 = None
    for v, b in zip(voiced, beats):
        shot_starts.append(t)
        if b.get("block_start"):  # a fixed-length sequence (end screen): later beats sit at fixed offsets
            block0 = t
        if b.get("block_at") is not None and block0 is not None:
            t = max(t, block0 + float(b["block_at"]))
        t += float(b.get("pause_before", 0))  # silence before the line (chapter titles: hit, then 1 s)
        starts.append(t)
        d = v["duration"] + pause + float(b.get("hold", 0))
        if b.get("block_end") is not None and block0 is not None:
            d = max(d, block0 + float(b["block_end"]) - t)
        durations.append(d)
        t += d
    total = t + tail
    plan = Plan(size=size, kind=kind, total=total)
    plan.timeline = A.Timeline(total, cfg)

    pil_cache: dict[Path, Image.Image] = {}

    def pil(path: Path) -> Image.Image:
        if path not in pil_cache:
            pil_cache[path] = Image.open(path).convert("RGB")
        return pil_cache[path]

    depth_cache: dict = {}

    def depth_of(path):
        if path not in depth_cache:
            depth_cache[path] = load_depth(path)
        return depth_cache[path]

    hook_max_shot = float(vcfg.get("hook_max_shot_seconds", 1.8))
    hook_seconds = float(vcfg.get("hook_seconds", 30))
    max_chars, max_words = (26, 5) if kind == "long" else (16, 3)
    last_section = None
    cycle_i = 0
    ledger_rows: list[dict] = []
    for i, (beat, v, start, dur) in enumerate(zip(beats, voiced, starts, durations)):
        plan.beat_starts[beat["id"]] = start
        shot_start = 0.0 if i == 0 else shot_starts[i]
        j = i
        while j + 1 < len(beats) and beats[j + 1]["visual"]["type"] == "continue":
            j += 1  # following beats keep this shot running (one continuous device)
        shot_end = total if j == len(beats) - 1 else starts[j] + durations[j]
        span = shot_end - shot_start
        visual = dict(beat["visual"])
        visual["_beat"] = beat["id"]
        vtype = visual["type"]
        lead_in = start - shot_start  # marks are timed from the narration start

        clip_file = None
        if vtype == "continue":
            pass
        elif vtype == "clip" or visual.get("clip") or (vtype == "reuse" and beat_lookup.get(visual.get("beat"), {}).get("visual", {}).get("_clip")):
            clip_file = _clip_path(beat, visual, beat_lookup)
        if clip_file is not None:
            cshot = ClipShot(shot_start, span, clip_file, size, cfg, float(visual.get("clip_speed", 1.0)))
            if visual.get("newsreel"):
                label = visual.get("newsreel") if isinstance(visual.get("newsreel"), str) else "Archive film"
                cshot = NewsreelShot(cshot, cfg, label, seed=i)
                for at in projector_sfx_times(shot_start, span):
                    plan.timeline.add_sfx(at, "projector", seed=i)
            if visual.get("newsreel"):
                plan.ledger_hide.append((shot_start, shot_end))  # archive film: Larry's tab steps aside
            if visual.get("exhibit"):  # live action presented as evidence (paper print, tag, grain)
                from .devices import ExhibitShot
                ex = visual["exhibit"]
                cshot = ExhibitShot(cshot, cfg, size, ex.get("label", "Evidence"), ex.get("tag", ""), seed=i)
                for at, k_ in cshot.sfx(shot_start):
                    plan.timeline.add_sfx(at, k_, seed=i)
                plan.ledger_hide.append((shot_start, shot_end))
            plan.shots.append(cshot)
        elif vtype in ("image", "reuse", "photo", "clip", "archive"):
            keys = _image_keys(visual, beat_lookup)
            if vtype == "archive" or (vtype == "reuse" and beat_lookup.get(visual.get("beat"), {}).get("visual", {}).get("type") == "archive"):
                visual["motion"] = "static"  # captioned archive prints: a big push would slide the caption into the subtitles
            marks = [dict(m, at=_timed(m, v["words"], 0.6) + lead_in) for m in (visual.get("marks") or [])]
            for m in marks:  # a label that is replaced when another word is spoken
                if m.get("until_on"):
                    wt = word_time(v["words"], m["until_on"])
                    if wt is not None:
                        m["until"] = wt + lead_in
            beat_max_shot = hook_max_shot if (start < hook_seconds or kind == "short") else max_shot
            cu, cr = visual.get("closeup"), visual.get("push")  # "push": whole shot on a detail {"center", "zoom"}
            if (cu or cr) and len(keys) == 1:
                # one generated picture, two framings: the full frame, then a push-in on a detail where a hand acts
                # (or the whole shot on a detail: "push"). Marks are given in fractions of the ORIGINAL picture.
                path = images[keys[0]]
                base, box0 = (_crop_pic(pil(path), cr) if cr else (pil(path), (0.0, 0.0, 1.0, 1.0)))
                tc = span
                if cu:
                    tc = min(max(1.2, _timed(cu, v["words"], span / 2) + lead_in), max(1.2, span - 1.2))
                hand_default = bool(visual.get("hand_marks"))
                segs = [(0.0, tc, base, box0, [m for m in marks if m["at"] < tc], visual.get("motion") or "static",
                         f"#push{box0[0]:.2f},{box0[1]:.2f},{box0[2]:.2f}" if cr else "")]
                if cu:
                    full = pil(path)
                    cimg, cbox = _crop_pic(full, cu)
                    cm = [dict(m, at=_timed(m, v["words"], 0.6) + lead_in - tc) for m in (cu.get("marks") or [])]
                    segs.append((tc, span - tc, cimg, cbox, cm, cu.get("motion", "zoom_in"), f"#push{cbox[0]:.2f},{cbox[1]:.2f},{cbox[2]:.2f}"))
                for k, (a0, dur0, im0, bx, mk, mot, tag) in enumerate(segs):
                    mk = [_remap_mark(m, bx) for m in mk] if bx != (0.0, 0.0, 1.0, 1.0) else mk
                    for m in mk:
                        if m.get("hand") is None:
                            m["hand"] = hand_default
                        if m["hand"] and m.get("at", 0) > 0.05 and float(m.get("dur", 0.7)) > 0.05:
                            plan.hand_cuts.append(shot_start + a0 + m["at"])
                        plan.timeline.add_sfx(shot_start + a0 + m["at"], "scribble", seed=i + k)
                    shot = ImageShot(shot_start + a0, dur0, im0, mot, size, cfg, marks=mk, photo=is_archive_photo(path),
                                     seed=i * 7 + k, depth=depth_of(path) if (k == 0 and not cr) else None)
                    shot._archive = False
                    shot._still_src = str(path) + tag
                    plan.shots.append(shot)
                marks = []
                pieces = 0
            elif marks or beat.get("bubble") or visual.get("draw"):
                pieces = len(keys)  # marks / bubbles / hand drawing need a steady picture: no extra cuts
            else:
                pieces = max(len(keys), int(np.ceil(span / beat_max_shot)))
                while pieces > len(keys) and span / pieces < min_shot:
                    pieces -= 1
            seg = span / max(1, pieces)
            for k in range(pieces):
                key = keys[k % len(keys)]
                path = images[key]
                if k == 0 and visual.get("motion"):
                    motion = visual["motion"]
                    if beat.get("bubble") and motion not in ("zoom_in", "zoom_out", "static"):
                        motion = "static"  # a speech bubble is fixed on screen: the picture under it must not slide
                elif marks or beat.get("bubble"):
                    motion = "static"
                else:
                    motion = MOTION_CYCLE[cycle_i % len(MOTION_CYCLE)]
                    cycle_i += 1
                shot_marks = [dict(m, at=m["at"] - k * seg) for m in marks] if k == 0 else []
                shot_draw = None
                if visual.get("draw") and k == 0:  # channel signature: the hand draws the subject on screen
                    dr = dict(visual["draw"]) if isinstance(visual["draw"], dict) else {}
                    dr["at"] = _timed(dr, v["words"], 0.0) + lead_in
                    dr.setdefault("dur", 3.4)
                    shot_draw = dr
                    from .draw import COLOR_START, LINES_END
                    t0, d0 = shot_start + dr["at"], float(dr["dur"])
                    rng = np.random.default_rng(i)
                    tt = t0
                    while tt < t0 + d0 * LINES_END:  # pencil strokes
                        plan.timeline.add_sfx(tt, "pencil", seed=int(tt * 100))
                        tt += float(rng.uniform(0.12, 0.22))
                    tt = t0 + d0 * COLOR_START
                    while tt < t0 + d0:  # marker squeaks while colouring
                        plan.timeline.add_sfx(tt, "marker", seed=int(tt * 100))
                        tt += float(rng.uniform(0.18, 0.3))
                for m in shot_marks:
                    if m.get("hand") is None:
                        m["hand"] = bool(visual.get("hand_marks"))
                    if m["hand"] and m.get("at", 0) > 0.05 and float(m.get("dur", 0.7)) > 0.05:
                        plan.hand_cuts.append(shot_start + k * seg + m["at"])
                shot = ImageShot(shot_start + k * seg, seg, pil(path), motion, size, cfg,
                                 marks=shot_marks, photo=is_archive_photo(path), seed=i * 7 + k,
                                 ad=visual.get("ad") if k == 0 else None, depth=depth_of(path),
                                 draw=shot_draw if k == 0 else None)
                if visual.get("newsreel"):
                    label = visual.get("newsreel") if isinstance(visual.get("newsreel"), str) else "Reconstruction"
                    shot = NewsreelShot(shot, cfg, label, seed=i * 7 + k)
                shot._archive = vtype == "archive" or (vtype == "reuse" and beat_lookup.get(visual.get("beat"), {}).get("visual", {}).get("type") == "archive")
                shot._still_src = str(path)  # for the max-still check (one illustration on screen too long)
                plan.shots.append(shot)
            if visual.get("newsreel"):
                plan.ledger_hide.append((shot_start, shot_end))
            if visual.get("newsreel"):
                for at in projector_sfx_times(shot_start, span):
                    plan.timeline.add_sfx(at, "projector", seed=i)
            for m in marks:
                plan.timeline.add_sfx(shot_start + m["at"], "scribble", seed=i)
        elif vtype == "title":
            plan.shots.append(TitleShot(shot_start, span, visual["text"], cfg, size))
        elif vtype in ("split", "receipts", "baskets", "battery"):
            from . import scenes as SC
            sp = dict(visual.get(vtype) or {})
            if vtype == "split":
                tm = lambda key, d: (_timed({"on": sp.get(key)}, v["words"], d) + lead_in) if sp.get(key) else None
                shot = SC.SplitShot(shot_start, span, pil(images[sp["left"]]), pil(images[sp["right"]]), sp, cfg, size, seed=i,
                                    light_at=tm("light_on", 0.3), tap_at=tm("tap_on", 1.2), stamp_at=tm("stamp_on", 0.25) or 0.25)
            elif vtype == "receipts":
                ca = _timed({"on": sp.get("circle_on"), "at": sp.get("circle_at", 1.0)}, v["words"], 1.0) + lead_in
                sa = (_timed({"on": sp.get("stamp_on"), "at": sp.get("stamp_at", 2.5)}, v["words"], 2.5) + lead_in) if sp.get("stamp") else None
                shot = SC.ReceiptsShot(shot_start, span, sp, cfg, size, circle_at=ca, stamp_at=sa, seed=i)
            elif vtype == "baskets":
                fp = Path(beat.get("_episode_dir") or ".") / sp["image_file"] if sp.get("image_file") else None
                subj = Image.open(fp).convert("RGB") if fp and fp.exists() else pil(images[sp["image"]])
                wa = tuple(_timed({"on": w}, v["words"], 2.0 + k) + lead_in for k, w in enumerate(sp.get("write_on") or [None, None]))
                ga = (_timed({"on": sp["gap_on"]}, v["words"], 4.0) + lead_in) if sp.get("gap_on") else \
                    ((wa[-1] + 1.0) if sp.get("gap") else None)  # the gap is drawn once both totals are written
                shot = SC.BasketsShot(shot_start, span, sp, subj, cfg, size, draw_at=float(sp.get("draw_at", 0.2)) + lead_in,
                                      write_at=wa, gap_at=ga, seed=i)
            else:
                da = _timed({"on": sp.get("drain_on"), "at": sp.get("drain_at", 0.4)}, v["words"], 0.4) + lead_in
                shot = SC.BatteryShot(shot_start, span, sp, cfg, size, drain_at=da, seed=i)
            plan.shots.append(shot)
            for at, k_ in shot.sfx(shot_start):
                plan.timeline.add_sfx(at, k_, seed=i)
            if vtype in ("baskets",):
                plan.ledger_hide.append((shot_start, shot_end))
        elif vtype in ("mugshot", "roulette", "maze", "casefile", "slot"):
            if vtype == "mugshot":
                sus = dict(visual["suspect"])
                sus["photo_marks"] = [dict(m, at=_timed(m, v["words"], 0.6) + lead_in) for m in (visual.get("photo_marks") or [])]
                for m in sus["photo_marks"]:
                    m.setdefault("hand", True)
                    plan.timeline.add_sfx(shot_start + m["at"], "scribble", seed=i)
                    plan.hand_cuts.append(shot_start + m["at"])
                prop = MugshotShot(shot_start, span, pil(images[beat["id"]]), sus, cfg, size, lead_in, seed=i)
            elif vtype == "roulette":
                prop = RouletteShot(shot_start, span, visual.get("roulette") or {}, cfg, size, lead_in)
            elif vtype == "maze":
                prop = MazeShot(shot_start, span, visual.get("maze") or {}, cfg, size, lead_in)
            elif vtype == "slot":
                prop = SlotShot(shot_start, span, visual.get("slot") or {}, cfg, size, lead_in)
            else:
                cfs = dict(visual["casefile"])
                if cfs.get("open_stamp_on"):
                    cfs["open_stamp_at"] = _timed({"on": cfs["open_stamp_on"]}, v["words"], 2.5)
                for wr_ in cfs.get("writes") or []:  # handwritten additions on the open page
                    wr_["at"] = _timed(wr_, v["words"], 2.5)
                prop = CaseFileShot(shot_start, span, cfs, cfg, size, lead_in)
            plan.shots.append(prop)
            for at, kind_sfx in prop.sfx(shot_start):
                plan.timeline.add_sfx(at, kind_sfx, seed=i)
        elif vtype == "doc":
            from .evidence import EvidenceShot
            doc = visual["doc"]
            cap = float(doc.get("max", 6.5))
            if doc.get("flash"):
                c0, c1 = shot_start, min(shot_end, shot_start + float(doc.get("flash_dur", 1.5)))
                mark_abs = c0
            else:
                mark_abs = start + _timed(doc, v["words"], 1.0)
                c0 = max(shot_start, mark_abs - float(doc.get("lead", 2.2)))
                if c0 - shot_start < 1.2 or not (doc.get("pre") or doc.get("pre_exhibit")):
                    c0 = shot_start  # nothing to show before the card: the card opens the beat (no frozen previous picture)
                c1 = min(shot_end, c0 + cap)
                if shot_end - c1 < 1.0 and shot_end - c0 <= cap + 0.7:
                    c1 = shot_end
            def _still(key_beat, a, b, motion):
                if b - a < 0.05 or not key_beat:
                    return
                keys = _image_keys({"type": "reuse", "beat": key_beat, "index": doc.get("index", 0)}, beat_lookup)
                path = images[keys[0]]
                plan.shots.append(ImageShot(a, b - a, pil(path), motion, size, cfg, photo=is_archive_photo(path), seed=i * 7 + 3,
                                            depth=depth_of(path)))
                plan.shots[-1]._still_src = str(path)
            pe = doc.get("pre_exhibit")  # an archive photo as EXHIBIT before the card (instead of a repeated still)
            if c0 > shot_start and pe:
                from .devices import ExhibitShot, StillInner
                from .archive import _source
                from .config import ROOT as _ROOT
                src = np.array(_source(pe, _ROOT / ".cache" / "archive"))
                tap = None
                if pe.get("tap"):
                    tat = (_timed({"on": pe["tap_on"]}, v["words"], 2.0) + start - shot_start) if pe.get("tap_on") else 2.0
                    tap = (float(pe["tap"][0]), float(pe["tap"][1]), max(1.0, min(tat, c0 - shot_start - 0.8)))
                ex = ExhibitShot(StillInner(shot_start, c0 - shot_start, src), cfg, size, pe.get("label", "Evidence"),
                                 pe.get("tag", ""), seed=i, tap=tap)
                plan.shots.append(ex)
                for at, k_ in ex.sfx(shot_start):
                    plan.timeline.add_sfx(at, k_, seed=i)
                plan.ledger_hide.append((shot_start, c0))
            elif c0 > shot_start:
                _still(doc.get("pre"), shot_start, c0, "zoom_in")
            plan.shots.append(EvidenceShot(c0, c1 - c0, doc, cfg, size, mark_at=mark_abs - c0, seed=i))
            for at, k_ in plan.shots[-1].sfx(c0):
                plan.timeline.add_sfx(at, k_, seed=i)
            plan.ledger_hide.append((c0, c1))
            if c1 < shot_end:
                _still(doc.get("post") or doc.get("pre"), c1, shot_end, "zoom_out")
        elif vtype == "houseedge":
            from .devices import HouseEdgeShot
            he = dict(visual["houseedge"])
            for key in ("write_on", "draw_on"):
                if he.get(key):
                    tgt = "write_at" if key == "write_on" else "draw_at"
                    he[tgt] = [(_timed({"on": w}, v["words"], 1.0) + lead_in) if w else 1e9 for k, w in enumerate(he[key])]
            shot = HouseEdgeShot(shot_start, span, he, cfg, size, lead_in=0.0, seed=i)
            plan.shots.append(shot)
            for at, k_ in shot.sfx(shot_start):
                plan.timeline.add_sfx(at, k_, seed=i)
            plan.ledger_hide.append((shot_start, shot_end))
        elif vtype == "endscreen":
            from .endscreen import EndScreenShot
            es = visual["endscreen"]
            subj = None
            nx = es.get("next") or {}
            if nx.get("image_file") and beat.get("_episode_dir"):
                fp = Path(beat["_episode_dir"]) / nx["image_file"]
                if fp.exists():
                    subj = Image.open(fp).convert("RGB")
            elif nx.get("image") in images:
                subj = pil(images[nx["image"]])
            shot = EndScreenShot(shot_start, span, es, cfg, size, subject=subj, lead_in=0.0, seed=i)
            plan.shots.append(shot)
            for at, k_ in shot.sfx(shot_start):
                plan.timeline.add_sfx(at, k_, seed=i)
            plan.ledger_hide.append((shot_start, total))
            plan.timeline.align_end = True
        elif vtype == "kinetic":
            words_rel = [(w, s0, e0) for w, s0, e0 in v["words"]]
            ktext = visual.get("text") or beat["text"]
            plan.shots.append(KineticShot(shot_start, span, ktext, words_rel, cfg, size, lead_in, visual.get("bg", "paper")))
            for _w, s0, _e in words_rel[:: max(1, len(words_rel) // 4)]:
                plan.timeline.add_sfx(start + s0, "hit", seed=i)
        elif vtype == "stat":
            plan.shots.append(StatShot(shot_start, span, visual["stat"], cfg, size))
            plan.timeline.add_sfx(shot_start + min(1.4, span * 0.45), "pop", seed=i)
        elif vtype == "chart":
            shot = ChartShot(shot_start, span, visual["chart"], cfg, size)
            plan.shots.append(shot)
            for rt in shot.reveal_times():
                plan.timeline.add_sfx(shot_start + rt, "tick", seed=i)

        plan.timeline.add_voice(start, v["audio"], v["sr"])
        if beat.get("cta"):  # retro SUBSCRIBE button: pops in, gets clicked, bell rings
            c = beat["cta"] if isinstance(beat["cta"], dict) else {}
            appear = start + _timed(c, v["words"], 0.3)
            click = start + _timed({"on": c.get("click_on"), "at": c.get("click_at")}, v["words"], appear - start + 1.2) \
                if (c.get("click_on") or c.get("click_at") is not None) else appear + 1.2
            end = max(click + 1.6, start + dur + float(c.get("hold", 0.0)))
            plan.ctas.append(Cta(appear, end, click))
            plan.timeline.add_sfx(appear, "pop", seed=i + 3)
            plan.timeline.add_sfx(click, "tick", seed=i + 4)
            plan.timeline.add_sfx(click + 0.12, "ding", seed=i + 5)
        if beat.get("_music"):
            plan.timeline.music_cue(max(0.0, start - 0.4), beat["_music"])
        if beat.get("sting"):
            sat = _timed({"on": beat.get("sting_on"), "at": beat.get("sting_at", 0.0)}, v["words"], 0.0)
            plan.timeline.add_sting(start + sat, beat["sting"])
        section = beat.get("section")
        explicit = beat.get("sfx")
        if explicit:
            plan.timeline.add_sfx(max(0.0, start - (1.1 if explicit == "riser" else 0.15)), explicit, seed=i)
        elif vtype == "title":
            plan.timeline.add_sfx(max(0.0, start - 0.05), "thud", seed=i)
        elif i > 0 and section and section != last_section:
            plan.timeline.add_sfx(max(0.0, start - 0.3), "whoosh", seed=i)
        last_section = section or last_section

        if beat.get("on_screen") and vtype not in ("chart", "stat", "title"):  # those already fill the top
            appear = 0.0 if beat.get("_hook") else start + 0.25
            bub = beat.get("bubble") or {}
            bubble_top_left = bool(bub) and float(bub.get("x", 0.5)) < 0.5 and float(bub.get("y", 0.5)) < 0.4
            corner = vtype in ("image", "reuse", "photo", "clip", "archive") and size[0] > size[1] and not bubble_top_left
            plan.cards.append(Card(appear, start + dur, str(beat["on_screen"]), corner and not beat.get("_hook"),
                                   bool(beat.get("_hook"))))
            if not beat.get("_hook"):
                plan.timeline.add_sfx(appear, "pop", seed=i)
        if beat.get("counter"):
            c = beat["counter"]
            appear = start + _timed(c, v["words"], 0.5)
            plan.counters.append(Counter(appear, start + dur, float(c.get("from", 0)), float(c["to"]),
                                         float(c.get("dur", 1.2)), str(c.get("prefix", "")), str(c.get("suffix", "")),
                                         int(c.get("decimals", 0)), str(c.get("label", ""))))
            for k in range(6):
                plan.timeline.add_sfx(appear + k * float(c.get("dur", 1.2)) / 6, "tick", seed=i + k)
            plan.timeline.add_sfx(appear + float(c.get("dur", 1.2)), "cash" if c.get("sound") == "cash" else "pop", seed=i)
        for j, ins in enumerate(beat.get("inserts") or []):
            from .inserts import build_insert
            at = start + _timed(ins, v["words"], 0.3)
            end_t = min(shot_end, at + float(ins.get("dur", max(2.5, dur)))) if ins.get("dur") else shot_end
            try:
                plan.inserts.append(build_insert(ins, images, depth_of, cfg, size, at, end_t, seed=i * 11 + j))
                paperish = ins.get("kind") in ("clipping", "photo") or (ins.get("kind") is None and ins.get("file") not in images)
                plan.timeline.add_sfx(at, "paper" if paperish else "whoosh", seed=i + j)
            except Exception as exc:  # noqa: BLE001
                print(f"insert skipped on {beat['id']}: {exc}", flush=True)
        if beat.get("bubble"):
            b = beat["bubble"]
            appear = start + _timed(b, v["words"], 0.2)
            plan.bubbles.append(Bubble(appear, start + dur, str(b["text"]), float(b.get("x", 0.5)),
                                       float(b.get("y", 0.3)), str(b.get("tail", "left"))))
            plan.timeline.add_sfx(appear, "pop", seed=i + 1)

        for target in beat.get("punch") or []:
            tl = target.lower().strip("*.,!?")
            for w, s0, _e in v["words"]:
                if w.lower().strip("*.,!?\"'").startswith(tl):
                    plan.punches.append(start + s0)
                    plan.timeline.add_sfx(start + s0 - 0.02, "hit", seed=i)
                    break

        if vtype not in ("title", "kinetic"):  # those already show the words
            plan.captions.extend(group_captions(v["words"], start, max_chars, max_words, v.get("speaker", "narrator")))
        if vtype in ("title", "kinetic", "stat", "chart", "casefile", "mugshot", "roulette", "maze"):
            plan.ledger_hide.append((shot_start, shot_end))  # full-frame graphics: Larry's tab steps aside
        if beat.get("label"):
            plan.labels.append((shot_start, shot_end, str(beat["label"])))
        if beat.get("ledger_hide"):
            plan.ledger_hide.append((shot_start, shot_end))
        if beat.get("stamp"):  # a quick verdict stamp over any picture
            stp = beat["stamp"]
            sat = start + _timed(stp, v["words"], 0.3)
            plan.stamps.append((sat, shot_end, str(stp["text"])))
            plan.timeline.add_sfx(sat, "stamp", seed=i + 41)
        for row in beat.get("ledger") or []:
            ledger_rows.append({**row, "at": start + _timed(row, v["words"], 0.5)})
        for ev in beat.get("sfx_at") or []:  # extra foley synced to words (chips, roulette ball, register…)
            plan.timeline.add_sfx(start + _timed(ev, v["words"], 0.3), ev["kind"], seed=i + 17)
    for i, wt, k_ in reveal_hits:  # the number lands in silence, then the hit
        plan.timeline.add_sfx(starts[i] + wt - 0.02, k_, seed=i + 31)
    for c in plan.counters:
        plan.ledger_hide.append((c.start - 0.2, c.end + 0.2))
    for b in plan.bubbles:
        if b.x > 0.55 and b.y < 0.5:
            plan.ledger_hide.append((b.start - 0.2, b.end + 0.2))
    if ledger_rows:
        from .devices import Ledger
        plan.ledger = Ledger(ledger_rows, cfg, size, hide=plan.ledger_hide)
        for at, k_ in plan.ledger.sfx():
            plan.timeline.add_sfx(at, k_, seed=int(at * 10))
    return plan


class Overlay:
    """Cached caption / card / speech-bubble renderers for one video size."""

    def __init__(self, cfg: dict, plan: Plan):
        self.cfg, self.plan = cfg, plan
        self.W, self.H = plan.size
        self.pal = {k: hex_to_rgb(v) for k, v in cfg["style"]["palette"].items()}
        self.head = resolve_font(cfg["fonts"]["headline"])
        self.body = resolve_font(cfg["fonts"]["body"])
        self.comic = resolve_font(cfg["fonts"]["comic"])
        self.cache: dict = {}
        short = plan.kind == "short"
        self.cap_size = int(self.H * (0.05 if short else 0.052))
        self.cap_y = int(self.H * (0.78 if short else 0.86))  # Shorts: under the square picture window
        self.card_y = int(self.H * (0.035 if short else 0.06))  # Shorts: title band above the picture window

    def caption_img(self, cap: Caption, active: int) -> np.ndarray:
        key = ("c", id(cap), active)
        if key not in self.cache:
            fnt = font(self.head if self.plan.kind == "short" else self.body, self.cap_size)
            words = [w.upper() if self.plan.kind == "short" else w for w in cap.words]
            lines = wrap(" ".join(words), fnt, int(self.W * 0.86))
            other = cap.speaker != "narrator"  # character lines: gold text, white active word
            base_col = self.pal["accent"] if other else (255, 255, 255)
            act_col = (255, 255, 255) if other else self.pal["accent"]
            colors, idx = [], 0
            for line in lines:
                row = []
                for _ in line.split(" "):
                    row.append(act_col if idx == active else base_col)
                    idx += 1
                colors.append(row)
            self.cache[key] = text_block(lines, fnt, fill=(255, 255, 255), stroke_fill=self.pal["ink"],
                                         stroke=max(3, self.cap_size // 9), colors=colors)
        return self.cache[key]

    def card_img(self, card: Card) -> np.ndarray:
        """Retro price-label card: paper, ink text, thick red frame, slight tilt."""
        key = ("k", id(card))
        if key not in self.cache:
            fnt, lines = fit_font(card.text.upper(), self.head, int(self.W * (0.4 if card.corner else 0.72)),
                                   int(self.H * (0.1 if self.plan.kind == "short" else 0.18)), start=int(self.H * 0.08))
            blk = text_block(lines, fnt, fill=self.pal["ink"], pad=int(fnt.size * 0.4))
            h, w = blk.shape[:2]
            frame_w = max(6, fnt.size // 9)
            card_img = Image.new("RGBA", (w + 2 * frame_w, h + 2 * frame_w), self.pal["red"] + (255,))
            inner = Image.new("RGBA", (w, h), self.pal["paper"] + (255,))
            inner.alpha_composite(Image.fromarray(blk))
            card_img.paste(inner, (frame_w, frame_w))
            rot = card_img.rotate(-2.0, resample=Image.BICUBIC, expand=True)
            self.cache[key] = np.array(rot)
        return self.cache[key]

    def bubble_img(self, bub: Bubble) -> np.ndarray:
        """Comic speech bubble with a tail (text set by code — image models garble letters)."""
        key = ("b", id(bub))
        if key not in self.cache:
            fnt, lines = fit_font(bub.text.upper(), self.comic, int(self.W * 0.34), int(self.H * 0.22), start=int(self.H * 0.06))
            blk = text_block(lines, fnt, fill=self.pal["ink"])
            h, w = blk.shape[:2]
            pad = int(fnt.size * 0.7)
            tail = int(fnt.size * 1.4)
            W2, H2 = w + 2 * pad, h + 2 * pad + tail
            img = Image.new("RGBA", (W2, H2), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            outline = max(4, fnt.size // 10)
            body = (outline, outline, W2 - outline, H2 - tail)
            if bub.tail != "none":
                bx = W2 * (0.25 if bub.tail == "left" else 0.75)
                tip = (bx - (W2 * 0.12 if bub.tail == "left" else -W2 * 0.12), H2 - outline)
                tri = [(bx - fnt.size * 0.45, H2 - tail - outline * 2), (bx + fnt.size * 0.45, H2 - tail - outline * 2), tip]
                d.polygon(tri, fill=(255, 255, 255, 255), outline=self.pal["ink"] + (255,), width=outline)
            radius = int(min(body[2] - body[0], body[3] - body[1]) / 2.2)
            d.rounded_rectangle(body, radius=radius, fill=(255, 255, 255, 255), outline=self.pal["ink"] + (255,), width=outline)
            if bub.tail != "none":  # open the bubble where the tail joins it
                gap = fnt.size * 0.45 - outline
                d.rectangle((bx - gap, H2 - tail - outline * 1.5, bx + gap, H2 - tail + outline * 0.2), fill=(255, 255, 255, 255))
            img.alpha_composite(Image.fromarray(blk), (pad, pad))
            self.cache[key] = np.array(img)
        return self.cache[key]

    @staticmethod
    def _pop(img: np.ndarray, age: float) -> tuple[np.ndarray, float]:
        p = min(1.0, age / 0.18)
        scale = 0.7 + 0.3 * (1 - (1 - p) ** 3) + (0.04 * math.sin(p * math.pi) if p < 1 else 0)
        if abs(scale - 1) > 1e-3:
            h, w = img.shape[:2]
            img = cv2.resize(img, (max(1, int(w * scale)), max(1, int(h * scale))))
        return img, min(p * 1.5, 1.0)

    def counter_img(self, c: Counter, value: float) -> np.ndarray:
        txt = f"{c.prefix}{value:,.{c.decimals}f}{c.suffix}"
        key = ("n", id(c), txt)
        if key not in self.cache:
            short = self.plan.kind == "short"
            nf = font(self.head, int(self.H * (0.045 if short else 0.075)))
            lf = font(self.body, int(self.H * (0.018 if short else 0.026)))
            num = text_block([txt], nf, fill=self.pal["red"])
            lab = text_block([c.label.upper()], lf, fill=self.pal["ink"]) if c.label else None
            w = max(num.shape[1], lab.shape[1] if lab is not None else 0) + int(nf.size * 0.6)
            h = num.shape[0] + (lab.shape[0] if lab is not None else 0) + int(nf.size * 0.4)
            card = Image.new("RGBA", (w, h), self.pal["paper"] + (240,))
            bw = max(5, nf.size // 14)
            ImageDraw.Draw(card).rectangle((0, 0, w - 1, h - 1), outline=self.pal["red"] + (255,), width=bw)
            y = int(nf.size * 0.2)
            if lab is not None:
                card.alpha_composite(Image.fromarray(lab), ((w - lab.shape[1]) // 2, y))
                y += lab.shape[0]
            card.alpha_composite(Image.fromarray(num), ((w - num.shape[1]) // 2, y - int(nf.size * 0.08)))
            self.cache[key] = np.array(card)
        return self.cache[key]

    def cta_img(self, pressed: bool, wiggle: float) -> np.ndarray:
        key = ("cta", pressed, round(wiggle, 2))
        if key not in self.cache:
            short = self.plan.kind == "short"
            fs = int(self.H * (0.04 if short else 0.064))
            fnt = font(self.head, fs)
            label = "SUBSCRIBED" if pressed else "SUBSCRIBE"
            tw = int(fnt.getlength(label))
            bw, bh = tw + int(fs * 1.4), int(fs * 1.7)
            bell = int(bh * 1.05)
            W = bw + (bell + int(fs * 0.5) if pressed else 0) + 8
            img = Image.new("RGBA", (W, bh + 8), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            fill = (90, 90, 90, 255) if pressed else self.pal["red"] + (255,)
            d.rounded_rectangle((4, 6, bw + 4, bh + 6), radius=bh // 5, fill=(0, 0, 0, 90))  # shadow
            d.rounded_rectangle((0, 0, bw, bh), radius=bh // 5, fill=fill, outline=self.pal["ink"] + (255,), width=max(3, fs // 14))
            d.text((bw // 2, bh // 2), label, font=fnt, fill=(255, 255, 255, 255), anchor="mm")
            if pressed:  # little ringing bell, drawn by code
                b = Image.new("RGBA", (bell, bell), (0, 0, 0, 0))
                bd = ImageDraw.Draw(b)
                gold = self.pal["accent"] + (255,)
                ink = self.pal["ink"] + (255,)
                bd.pieslice((bell * 0.18, bell * 0.12, bell * 0.82, bell * 0.95), 180, 360, fill=gold, outline=ink, width=3)
                bd.rectangle((bell * 0.18, bell * 0.52, bell * 0.82, bell * 0.72), fill=gold, outline=ink, width=3)
                bd.ellipse((bell * 0.42, bell * 0.72, bell * 0.58, bell * 0.88), fill=ink)
                bd.ellipse((bell * 0.44, bell * 0.02, bell * 0.56, bell * 0.14), fill=gold, outline=ink, width=2)
                b = b.rotate(18 * wiggle, resample=Image.BICUBIC)
                img.alpha_composite(b, (bw + int(fs * 0.5), 2))
            self.cache[key] = np.array(img)
        return self.cache[key]

    def _draw_ctas(self, frame: np.ndarray, t: float) -> None:
        for c in self.plan.ctas:
            if not (c.start <= t < c.end):
                continue
            pressed = t >= c.click
            age = t - c.click
            wiggle = math.sin(age * 28) * max(0.0, 1 - age / 0.8) if pressed else 0.0
            img = self.cta_img(pressed, wiggle)
            if pressed and age < 0.12:  # press: quick squash
                img = cv2.resize(img, (img.shape[1], max(1, int(img.shape[0] * 0.9))))
            img, op = self._pop(img, t - c.start)
            op *= min(1.0, (c.end - t) / 0.25)
            if self.plan.kind == "short":
                x, y = (self.W - img.shape[1]) // 2, int(self.H * 0.56)
            else:
                x, y = int(self.W * 0.05), int(self.H * 0.66)
            blend(frame, img, x, y, opacity=op)

    def apply(self, frame: np.ndarray, t: float, cap_i: int, card_i: int, bub_i: int) -> None:
        for ins in self.plan.inserts:
            if ins.start <= t <= ins.end:
                ins.draw(frame, t)
        if self.plan.ledger is not None:
            self.plan.ledger.draw(frame, t)
        for l0, l1, txt in self.plan.labels:
            if l0 <= t < l1:
                key = ("label", txt)
                if key not in self.cache:
                    fnt = font(self.body, max(14, int(self.H * 0.026)))
                    self.cache[key] = text_block([txt.upper()], fnt, fill=self.pal["paper"], box_fill=self.pal["ink"] + (210,), pad=int(fnt.size * 0.4))
                im = self.cache[key]
                yb = self.H * (0.04 if self.H < self.W else 0.235)
                blend(frame, im, self.W - im.shape[1] - int(self.W * 0.03), int(self.H - yb - im.shape[0]) if self.H < self.W else int(self.W + self.H * 0.17 - im.shape[0] - self.H * 0.01))
        for s0, s1, txt in self.plan.stamps:
            if s0 <= t < s1:
                key = ("stamp", txt)
                if key not in self.cache:
                    from .endscreen import _stamp
                    self.cache[key] = _stamp(txt, self.cfg, int(min(self.W, self.H) * 0.62), self.pal["red"], -10, 7)
                st = self.cache[key]
                p = min(1.0, (t - s0) / 0.14)
                sc = 2.2 - 1.2 * p
                im = cv2.resize(st, (max(1, int(st.shape[1] * sc)), max(1, int(st.shape[0] * sc))))
                cy = int(self.H * (0.42 if self.H < self.W else 0.45))
                blend(frame, im, (self.W - im.shape[1]) // 2, cy - im.shape[0] // 2, opacity=min(1.0, 0.3 + p))
        if self.plan.ctas:
            self._draw_ctas(frame, t)
        for c in self.plan.counters:
            if c.start <= t < c.end:
                p = min(1.0, (t - c.start) / max(c.dur, 1e-3))
                p = 1 - (1 - p) ** 2
                img = self.counter_img(c, c.frm + (c.to - c.frm) * p)
                op = min(1.0, (t - c.start) / 0.15) * min(1.0, (c.end - t) / 0.15)
                x = self.W - img.shape[1] - int(self.W * 0.04)
                y = int(self.H * (0.25 if self.plan.kind == "short" else 0.05))
                blend(frame, img, x, y, opacity=op)
        cards = self.plan.cards
        if card_i < len(cards) and cards[card_i].start <= t < cards[card_i].end:
            card = cards[card_i]
            if card.hook:  # Shorts opener: full card from frame 0 in the title band above the picture window
                img = self.card_img(card)
                blend(frame, img, (self.W - img.shape[1]) // 2, self.card_y, opacity=min(1.0, (card.end - t) / 0.15))
            else:
                img, op = self._pop(self.card_img(card), t - card.start)
                op *= min(1.0, (card.end - t) / 0.15)
                x = int(self.W * 0.04) if card.corner else (self.W - img.shape[1]) // 2
                blend(frame, img, x, self.card_y, opacity=op)
        bubs = self.plan.bubbles
        if bub_i < len(bubs) and bubs[bub_i].start <= t < bubs[bub_i].end:
            bub = bubs[bub_i]
            img, op = self._pop(self.bubble_img(bub), t - bub.start)
            op *= min(1.0, (bub.end - t) / 0.15)
            cx, cy = bub.cur if bub.cur else (bub.x * self.W, bub.y * self.H)
            m = int(self.W * 0.03)
            x = int(min(max(cx - img.shape[1] / 2, m), self.W - img.shape[1] - m))
            y = int(min(max(cy - img.shape[0] / 2, m), self.cap_y - img.shape[0] * 0.6 - img.shape[0] / 2))
            blend(frame, img, x, y, opacity=op)
        caps = self.plan.captions
        if cap_i < len(caps) and caps[cap_i].start <= t < caps[cap_i].end:
            cap = caps[cap_i]
            active = 0
            for k, (s, _e) in enumerate(cap.word_times):
                if t >= s:
                    active = k
            img = self.caption_img(cap, active)
            blend(frame, img, (self.W - img.shape[1]) // 2, self.cap_y - img.shape[0] // 2)


def _loudnorm_filter(wav_path: Path, lufs: float) -> str:
    """Two-pass loudnorm in linear mode = one constant gain for the whole mix (single-pass loudnorm rides the
    volume up and down, which made the music swell and sink)."""
    import json as _json
    base = f"loudnorm=I={lufs}:TP=-1.0:LRA=20"
    try:
        res = subprocess.run(["ffmpeg", "-v", "info", "-nostats", "-i", str(wav_path), "-af", base + ":print_format=json",
                              "-f", "null", "-"], capture_output=True, text=True)
        txt = res.stderr
        m = _json.loads(txt[txt.rindex("{"): txt.rindex("}") + 1])
        return (f"{base}:linear=true:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
                f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}")
    except Exception:  # noqa: BLE001
        return base


def render(plan: Plan, cfg: dict, out_path: Path, wav_path: Path, log=print) -> Path:
    fps = int(cfg["video"]["fps"])
    W, H = plan.size
    A.write_wav(wav_path, plan.timeline.mix())
    lufs = cfg["audio"].get("target_lufs", -14)
    loud_af = _loudnorm_filter(wav_path, lufs)
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
        "-i", str(wav_path),
        "-map", "0:v", "-map", "1:a",
        "-c:v", "libx264", "-preset", cfg["video"].get("x264_preset", "veryfast"),
        "-crf", str(cfg["video"].get("crf", 21)), "-pix_fmt", "yuv420p",
        "-af", loud_af + ",alimiter=limit=0.78:attack=2:release=60:level=false", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-shortest", "-movflags", "+faststart", str(out_path),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    overlay = Overlay(cfg, plan)
    xfade = int(cfg["video"].get("crossfade_frames", 8)) / fps
    vig_strength = float(cfg["style"].get("vignette", 0.18))
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    rr = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) / math.sqrt(2)
    vignette = (255 * (1 - vig_strength * np.clip(rr, 0, 1) ** 2.2)).astype(np.uint16)[..., None]
    punches = sorted(plan.punches)
    punch_i = 0
    n_frames = int(np.ceil(plan.total * fps))
    shot_i = cap_i = card_i = bub_i = 0
    shots, caps, cards, bubs = plan.shots, plan.captions, plan.cards, plan.bubbles
    t0 = time.time()
    next_report = 0.1
    try:
        for f in range(n_frames):
            t = f / fps
            while shot_i < len(shots) - 1 and t >= shots[shot_i + 1].start:
                shot_i += 1
                if shot_i >= 2 and hasattr(shots[shot_i - 2], "release"):
                    shots[shot_i - 2].release()  # free pixels of shots already played
            while cap_i < len(caps) and t >= caps[cap_i].end:
                cap_i += 1
            while card_i < len(cards) and t >= cards[card_i].end:
                card_i += 1
            while bub_i < len(bubs) and t >= bubs[bub_i].end:
                bub_i += 1
            shot = shots[shot_i]
            local = t - shot.start
            frame = shot.frame(local)
            prev = shots[shot_i - 1] if shot_i > 0 else None
            # two framings of the same picture are cut, not dissolved (a dissolve looks like a doubled, torn image)
            same_pic = prev is not None and getattr(prev, "_src", (None,))[0] is not None \
                and getattr(prev, "_src", (None,))[0] is getattr(shot, "_src", (None,))[0]
            # dissolves only between two archive photos; everything else is a hard cut (no ghost images)
            both_archive = prev is not None and getattr(prev, "_archive", False) and getattr(shot, "_archive", False)
            if prev is not None and local < xfade and not same_pic and both_archive:
                a = local / xfade
                frame = cv2.addWeighted(prev.frame(t - prev.start), 1 - a, frame, a, 0)
            else:
                frame = np.ascontiguousarray(frame)
            # punch-in on emphasised words: quick 7% push, eases back over ~0.5 s
            while punch_i < len(punches) - 1 and t >= punches[punch_i + 1]:
                punch_i += 1
            if punches and 0 <= t - punches[punch_i] < 0.6:
                age = t - punches[punch_i]
                z = 1 + 0.07 * (min(1.0, age / 0.07) if age < 0.07 else max(0.0, 1 - (age - 0.07) / 0.5))
                if z > 1.001:
                    cw, ch = int(W / z), int(H / z)
                    x0, y0 = (W - cw) // 2, (H - ch) // 2
                    frame = cv2.resize(frame[y0 : y0 + ch, x0 : x0 + cw], (W, H), interpolation=cv2.INTER_LINEAR)
            if vig_strength > 0:
                frame = ((frame.astype(np.uint16) * vignette) >> 8).astype(np.uint8)
            elif not frame.flags.writeable or frame is getattr(shot, "base", None):
                frame = frame.copy()
            if bub_i < len(bubs) and bubs[bub_i].start <= t < bubs[bub_i].end:
                b = bubs[bub_i]  # the bubble rides on the picture (camera moves never slide it onto a face)
                b.cur = shot.to_screen(b.x, b.y, local) if hasattr(shot, "to_screen") and shot.start <= b.start + 0.05 else None
            overlay.apply(frame, t, cap_i, card_i, bub_i)
            proc.stdin.write(frame.tobytes())
            if f / n_frames >= next_report:
                rate = (f + 1) / max(1e-6, time.time() - t0)
                log(f"  {plan.kind}: {int(100 * f / n_frames)}%  ({rate:.0f} fps)")
                next_report += 0.1
    finally:
        proc.stdin.close()
        code = proc.wait()
    if code != 0:
        raise RuntimeError(f"ffmpeg failed with exit code {code}")
    log(f"Rendered {out_path.name}: {plan.total:.1f}s in {time.time() - t0:.0f}s")
    return out_path
