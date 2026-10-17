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


@dataclass
class Bubble:
    start: float
    end: float
    text: str
    x: float
    y: float
    tail: str


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
    punches: list[float] = field(default_factory=list)
    beat_starts: dict[str, float] = field(default_factory=dict)
    timeline: A.Timeline | None = None


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
    if visual["type"] in ("photo", "mugshot"):
        return [visual["_beat"]]
    if visual["type"] == "reuse":
        src = beat_lookup[visual["beat"]]["visual"]
        if src["type"] in ("photo", "mugshot"):
            return [visual["beat"]]
        n = len(src.get("prompts") or [src["prompt"]])
        idx = int(visual.get("index", 0)) % n
        return [visual["beat"] if idx == 0 else f"{visual['beat']}.{idx}"]
    return []


def build_plan(beats, voiced, images, cfg, size, kind, beat_lookup, extra_pause: float = 0.0) -> Plan:
    vcfg = cfg["video"]
    pause = float(vcfg.get("pause_after_beat", 0.18)) + extra_pause
    max_shot = float(vcfg.get("max_shot_seconds", 3.2))
    min_shot = float(vcfg.get("min_shot_seconds", 1.4))
    lead = 0.25 if kind == "long" else 0.05
    tail = 0.8 if kind == "long" else 0.15

    t = lead
    starts, durations = [], []
    for v, b in zip(voiced, beats):
        starts.append(t)
        d = v["duration"] + pause + float(b.get("hold", 0))
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
    for i, (beat, v, start, dur) in enumerate(zip(beats, voiced, starts, durations)):
        plan.beat_starts[beat["id"]] = start
        shot_start = 0.0 if i == 0 else start
        shot_end = total if i == len(beats) - 1 else start + dur
        span = shot_end - shot_start
        visual = dict(beat["visual"])
        visual["_beat"] = beat["id"]
        vtype = visual["type"]
        lead_in = start - shot_start  # marks are timed from the narration start

        clip_file = None
        if vtype == "clip" or visual.get("clip"):
            clip_file = _clip_path(beat, visual, beat_lookup)
        if clip_file is not None:
            plan.shots.append(ClipShot(shot_start, span, clip_file, size, cfg, float(visual.get("clip_speed", 1.0))))
        elif vtype in ("image", "reuse", "photo", "clip"):
            keys = _image_keys(visual, beat_lookup)
            marks = [dict(m, at=float(m.get("at", 0.6)) + lead_in) for m in (visual.get("marks") or [])]
            beat_max_shot = hook_max_shot if (start < hook_seconds or kind == "short") else max_shot
            if marks:
                pieces = len(keys)  # marks need a steady picture: no extra cuts
            else:
                pieces = max(len(keys), int(np.ceil(span / beat_max_shot)))
                while pieces > len(keys) and span / pieces < min_shot:
                    pieces -= 1
            seg = span / pieces
            for k in range(pieces):
                key = keys[k % len(keys)]
                path = images[key]
                if k == 0 and visual.get("motion"):
                    motion = visual["motion"]
                elif marks:
                    motion = "static"
                else:
                    motion = MOTION_CYCLE[cycle_i % len(MOTION_CYCLE)]
                    cycle_i += 1
                shot_marks = [dict(m, at=m["at"] - k * seg) for m in marks] if k == 0 else []
                shot = ImageShot(shot_start + k * seg, seg, pil(path), motion, size, cfg,
                                 marks=shot_marks, photo=is_archive_photo(path), seed=i * 7 + k,
                                 ad=visual.get("ad") if k == 0 else None, depth=depth_of(path))
                if visual.get("newsreel"):
                    label = visual.get("newsreel") if isinstance(visual.get("newsreel"), str) else "Reconstruction"
                    shot = NewsreelShot(shot, cfg, label, seed=i * 7 + k)
                plan.shots.append(shot)
            if visual.get("newsreel"):
                for at in projector_sfx_times(shot_start, span):
                    plan.timeline.add_sfx(at, "projector", seed=i)
            for m in marks:
                plan.timeline.add_sfx(shot_start + m["at"], "scribble", seed=i)
        elif vtype == "title":
            plan.shots.append(TitleShot(shot_start, span, visual["text"], cfg, size))
        elif vtype in ("mugshot", "roulette", "maze", "casefile", "slot"):
            if vtype == "mugshot":
                prop = MugshotShot(shot_start, span, pil(images[beat["id"]]), visual["suspect"], cfg, size, lead_in, seed=i)
            elif vtype == "roulette":
                prop = RouletteShot(shot_start, span, visual.get("roulette") or {}, cfg, size, lead_in)
            elif vtype == "maze":
                prop = MazeShot(shot_start, span, visual.get("maze") or {}, cfg, size, lead_in)
            elif vtype == "slot":
                prop = SlotShot(shot_start, span, visual.get("slot") or {}, cfg, size, lead_in)
            else:
                prop = CaseFileShot(shot_start, span, visual["casefile"], cfg, size, lead_in)
            plan.shots.append(prop)
            for at, kind_sfx in prop.sfx(shot_start):
                plan.timeline.add_sfx(at, kind_sfx, seed=i)
        elif vtype == "doc":
            doc = visual["doc"]
            plan.shots.append(DocShot(shot_start, span, doc, cfg, size, lead_in=lead_in, seed=i))
            plan.timeline.add_sfx(start + float(doc.get("at", 1.0)), "scribble", seed=i)
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
        if beat.get("_music"):
            plan.timeline.music_cue(max(0.0, start - 0.4), beat["_music"])
        if beat.get("sting"):
            plan.timeline.add_sting(start + float(beat.get("sting_at", 0.0)), beat["sting"])
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
            appear = start + 0.25
            bub = beat.get("bubble") or {}
            bubble_top_left = bool(bub) and float(bub.get("x", 0.5)) < 0.5 and float(bub.get("y", 0.5)) < 0.4
            corner = vtype in ("image", "reuse", "photo", "clip") and size[0] > size[1] and not bubble_top_left
            plan.cards.append(Card(appear, start + dur, str(beat["on_screen"]), corner))
            plan.timeline.add_sfx(appear, "pop", seed=i)
        if beat.get("counter"):
            c = beat["counter"]
            appear = start + float(c.get("at", 0.5))
            plan.counters.append(Counter(appear, start + dur, float(c.get("from", 0)), float(c["to"]),
                                         float(c.get("dur", 1.2)), str(c.get("prefix", "")), str(c.get("suffix", "")),
                                         int(c.get("decimals", 0)), str(c.get("label", ""))))
            for k in range(6):
                plan.timeline.add_sfx(appear + k * float(c.get("dur", 1.2)) / 6, "tick", seed=i + k)
            plan.timeline.add_sfx(appear + float(c.get("dur", 1.2)), "cash" if c.get("sound") == "cash" else "pop", seed=i)
        if beat.get("bubble"):
            b = beat["bubble"]
            appear = start + float(b.get("at", 0.2))
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
        self.cap_y = int(self.H * (0.68 if short else 0.86))
        self.card_y = int(self.H * (0.11 if short else 0.06))

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
            fnt, lines = fit_font(card.text.upper(), self.head, int(self.W * (0.4 if card.corner else 0.72)), int(self.H * 0.18), start=int(self.H * 0.08))
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

    def apply(self, frame: np.ndarray, t: float, cap_i: int, card_i: int, bub_i: int) -> None:
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
            img, op = self._pop(self.card_img(card), t - card.start)
            op *= min(1.0, (card.end - t) / 0.15)
            x = int(self.W * 0.04) if card.corner else (self.W - img.shape[1]) // 2
            blend(frame, img, x, self.card_y, opacity=op)
        bubs = self.plan.bubbles
        if bub_i < len(bubs) and bubs[bub_i].start <= t < bubs[bub_i].end:
            bub = bubs[bub_i]
            img, op = self._pop(self.bubble_img(bub), t - bub.start)
            op *= min(1.0, (bub.end - t) / 0.15)
            x = int(bub.x * self.W - img.shape[1] / 2)
            y = int(bub.y * self.H - img.shape[0] / 2)
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
    base = f"loudnorm=I={lufs}:TP=-1.5:LRA=20"
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
        "-af", loud_af, "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
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
            if prev is not None and local < xfade and not same_pic:
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
