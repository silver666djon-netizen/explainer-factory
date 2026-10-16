"""YouTube-ready extras: description with chapters, subtitles (SRT), thumbnail."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from .config import hex_to_rgb, resolve_font
from .shots import cover
from .text import fit_font, text_block, blend


def _ts(sec: float) -> str:
    sec = int(sec)
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def chapters(episode: dict, beat_starts: dict[str, float], total: float) -> list[tuple[float, str]]:
    out: list[tuple[float, str]] = []
    last = None
    for beat in episode["beats"]:
        sec = beat.get("section")
        if sec and sec != last:
            out.append((0.0 if not out else beat_starts[beat["id"]], sec))
            last = sec
    # YouTube rules: starts at 0:00, at least 3 chapters, each at least 10 s long
    ends = [c[0] for c in out[1:]] + [total]
    if len(out) < 3 or any(e - s < 10 for (s, _), e in zip(out, ends)):
        return []
    return out


def description(episode: dict, chaps: list[tuple[float, str]]) -> str:
    parts = [episode.get("description", "").strip()]
    if chaps:
        parts.append("Chapters:\n" + "\n".join(f"{_ts(t)} {name}" for t, name in chaps))
    if episode.get("sources"):
        parts.append("Sources:\n" + "\n".join(f"- {s}" for s in episode["sources"]))
    if episode.get("tags"):
        parts.append(" ".join("#" + t.replace(" ", "") for t in episode["tags"][:3]))
    return "\n\n".join(p for p in parts if p)


def srt(captions) -> str:
    def stamp(x: float) -> str:
        ms = int(round(x * 1000))
        h, ms = divmod(ms, 3_600_000)
        m, ms = divmod(ms, 60_000)
        s, ms = divmod(ms, 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    rows = []
    for i, cap in enumerate(captions, 1):
        rows.append(f"{i}\n{stamp(cap.start)} --> {stamp(cap.end)}\n{' '.join(cap.words)}\n")
    return "\n".join(rows)


def thumbnail(cfg: dict, image_path: Path, text: str, out: Path, circle: bool = True) -> Path:
    W, H = 1280, 720
    pal = {k: hex_to_rgb(v) for k, v in cfg["style"]["palette"].items()}
    base = cover(Image.open(image_path).convert("RGB"), W, H).astype(np.float32)
    # darken the left side so the headline pops
    grad = np.linspace(0.35, 1.0, W)[None, :, None]
    base = (base * grad).clip(0, 255).astype(np.uint8)
    head = resolve_font(cfg["fonts"]["headline"])
    fnt, lines = fit_font(text.upper(), head, int(W * 0.55), int(H * 0.7), start=150, min_size=60)
    colors = [[pal["accent"] if j == 0 and i == 0 else (255, 255, 255) for j, _ in enumerate(l.split(" "))] for i, l in enumerate(lines)]
    blk = text_block(lines, fnt, fill=(255, 255, 255), stroke_fill=pal["ink"], stroke=8, align="left", colors=colors)
    if circle:  # the channel's red investigator marker around the subject
        import cv2
        from .shots import mark_strokes
        red = tuple(int(c) for c in pal["red"])
        for stroke in mark_strokes({"type": "circle", "x": 0.72, "y": 0.5, "w": 0.36, "h": 0.62}, W, H, seed=5):
            cv2.polylines(base, [stroke.astype(np.int32).reshape(-1, 1, 2)], False, red, 12, cv2.LINE_AA)
    blend(base, blk, 50, (H - blk.shape[0]) // 2)
    img = Image.fromarray(base)
    ImageDraw.Draw(img).rectangle((0, H - 18, W, H), fill=pal["red"])
    img.save(out, quality=92)
    return out


def write_meta(out_dir: Path, episode: dict, plan_long, shorts_info: list[dict]) -> dict:
    chaps = chapters(episode, plan_long.beat_starts, plan_long.total)
    meta = {
        "title": episode["title"],
        "description": description(episode, chaps),
        "tags": episode.get("tags", []),
        "duration_seconds": round(plan_long.total, 1),
        "chapters": [{"time": _ts(t), "title": n} for t, n in chaps],
        "shorts": shorts_info,
    }
    (out_dir / "metadata.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / "description.txt").write_text(meta["description"], encoding="utf-8")
    (out_dir / "long.srt").write_text(srt(plan_long.captions), encoding="utf-8")
    return meta
