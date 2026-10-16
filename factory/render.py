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
from .shots import ChartShot, ImageShot, Shot, StatShot, TitleShot
from .text import blend, fit_font, font, text_block, wrap

MOTION_CYCLE = ["zoom_in", "pan_right", "zoom_out", "pan_left", "drift", "pan_up", "zoom_in", "pan_down"]


@dataclass
class Caption:
    start: float
    end: float
    words: list[str]
    word_times: list[tuple[float, float]]


@dataclass
class Card:
    start: float
    end: float
    text: str


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
    beat_starts: dict[str, float] = field(default_factory=dict)
    timeline: A.Timeline | None = None


def group_captions(words, offset: float, max_chars: int, max_words: int) -> list[Caption]:
    out: list[Caption] = []
    cur: list[tuple[str, float, float]] = []

    def flush():
        if cur:
            out.append(Caption(offset + cur[0][1], offset + cur[-1][2], [w for w, _, _ in cur],
                               [(offset + s, offset + e) for _, s, e in cur]))

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


def _image_keys(visual: dict, beat_lookup: dict[str, dict]) -> list[str]:
    if visual["type"] == "image":
        n = len(visual.get("prompts") or [visual["prompt"]])
        return [visual["_beat"] if i == 0 else f"{visual['_beat']}.{i}" for i in range(n)]
    if visual["type"] == "photo":
        return [visual["_beat"]]
    if visual["type"] == "reuse":
        src = beat_lookup[visual["beat"]]["visual"]
        if src["type"] == "photo":
            return [visual["beat"]]
        n = len(src.get("prompts") or [src["prompt"]])
        idx = int(visual.get("index", 0)) % n
        return [visual["beat"] if idx == 0 else f"{visual['beat']}.{idx}"]
    return []


def build_plan(beats, voiced, images, cfg, size, kind, beat_lookup) -> Plan:
    vcfg = cfg["video"]
    pause = float(vcfg.get("pause_after_beat", 0.18))
    max_shot = float(vcfg.get("max_shot_seconds", 3.2))
    min_shot = float(vcfg.get("min_shot_seconds", 1.4))
    lead = 0.25 if kind == "long" else 0.05
    tail = 0.8 if kind == "long" else 0.15

    t = lead
    starts, durations = [], []
    for v in voiced:
        starts.append(t)
        d = v["duration"] + pause
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

        if vtype in ("image", "reuse", "photo"):
            keys = _image_keys(visual, beat_lookup)
            marks = [dict(m, at=float(m.get("at", 0.6)) + lead_in) for m in (visual.get("marks") or [])]
            if marks:
                pieces = len(keys)  # marks need a steady picture: no extra cuts
            else:
                pieces = max(len(keys), int(np.ceil(span / max_shot)))
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
                plan.shots.append(ImageShot(shot_start + k * seg, seg, pil(path), motion, size, cfg,
                                            marks=shot_marks, photo=is_archive_photo(path), seed=i * 7 + k))
            for m in marks:
                plan.timeline.add_sfx(shot_start + m["at"], "scribble", seed=i)
        elif vtype == "title":
            plan.shots.append(TitleShot(shot_start, span, visual["text"], cfg, size))
        elif vtype == "stat":
            plan.shots.append(StatShot(shot_start, span, visual["stat"], cfg, size))
            plan.timeline.add_sfx(shot_start + min(1.4, span * 0.45), "pop", seed=i)
        elif vtype == "chart":
            shot = ChartShot(shot_start, span, visual["chart"], cfg, size)
            plan.shots.append(shot)
            for rt in shot.reveal_times():
                plan.timeline.add_sfx(shot_start + rt, "tick", seed=i)

        plan.timeline.add_voice(start, v["audio"], v["sr"])
        section = beat.get("section")
        explicit = beat.get("sfx")
        if explicit:
            plan.timeline.add_sfx(max(0.0, start - 0.15), explicit, seed=i)
        elif vtype == "title":
            plan.timeline.add_sfx(max(0.0, start - 0.05), "thud", seed=i)
        elif i > 0 and section and section != last_section:
            plan.timeline.add_sfx(max(0.0, start - 0.3), "whoosh", seed=i)
        last_section = section or last_section

        if beat.get("on_screen") and vtype not in ("chart", "stat", "title"):  # those already fill the top
            appear = start + 0.25
            plan.cards.append(Card(appear, start + dur, str(beat["on_screen"])))
            plan.timeline.add_sfx(appear, "pop", seed=i)
        if beat.get("bubble"):
            b = beat["bubble"]
            appear = start + float(b.get("at", 0.2))
            plan.bubbles.append(Bubble(appear, start + dur, str(b["text"]), float(b.get("x", 0.5)),
                                       float(b.get("y", 0.3)), str(b.get("tail", "left"))))
            plan.timeline.add_sfx(appear, "pop", seed=i + 1)

        if vtype not in ("title",):
            plan.captions.extend(group_captions(v["words"], start, max_chars, max_words))
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
            colors, idx = [], 0
            for line in lines:
                row = []
                for _ in line.split(" "):
                    row.append(self.pal["accent"] if idx == active else (255, 255, 255))
                    idx += 1
                colors.append(row)
            self.cache[key] = text_block(lines, fnt, fill=(255, 255, 255), stroke_fill=self.pal["ink"],
                                         stroke=max(3, self.cap_size // 9), colors=colors)
        return self.cache[key]

    def card_img(self, card: Card) -> np.ndarray:
        """Retro price-label card: paper, ink text, thick red frame, slight tilt."""
        key = ("k", id(card))
        if key not in self.cache:
            fnt, lines = fit_font(card.text.upper(), self.head, int(self.W * 0.72), int(self.H * 0.18), start=int(self.H * 0.08))
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

    def apply(self, frame: np.ndarray, t: float, cap_i: int, card_i: int, bub_i: int) -> None:
        cards = self.plan.cards
        if card_i < len(cards) and cards[card_i].start <= t < cards[card_i].end:
            card = cards[card_i]
            img, op = self._pop(self.card_img(card), t - card.start)
            op *= min(1.0, (card.end - t) / 0.15)
            blend(frame, img, (self.W - img.shape[1]) // 2, self.card_y, opacity=op)
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


def render(plan: Plan, cfg: dict, out_path: Path, wav_path: Path, log=print) -> Path:
    fps = int(cfg["video"]["fps"])
    W, H = plan.size
    A.write_wav(wav_path, plan.timeline.mix())
    lufs = cfg["audio"].get("target_lufs", -14)
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
        "-i", str(wav_path),
        "-map", "0:v", "-map", "1:a",
        "-c:v", "libx264", "-preset", cfg["video"].get("x264_preset", "veryfast"),
        "-crf", str(cfg["video"].get("crf", 21)), "-pix_fmt", "yuv420p",
        "-af", f"loudnorm=I={lufs}:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-shortest", "-movflags", "+faststart", str(out_path),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    overlay = Overlay(cfg, plan)
    xfade = int(cfg["video"].get("crossfade_frames", 8)) / fps
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
            while cap_i < len(caps) and t >= caps[cap_i].end:
                cap_i += 1
            while card_i < len(cards) and t >= cards[card_i].end:
                card_i += 1
            while bub_i < len(bubs) and t >= bubs[bub_i].end:
                bub_i += 1
            shot = shots[shot_i]
            local = t - shot.start
            frame = shot.frame(local)
            if shot_i > 0 and local < xfade:
                prev = shots[shot_i - 1]
                a = local / xfade
                frame = cv2.addWeighted(prev.frame(t - prev.start), 1 - a, frame, a, 0)
            else:
                frame = np.ascontiguousarray(frame)
            if not frame.flags.writeable or frame is getattr(shot, "base", None):
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
