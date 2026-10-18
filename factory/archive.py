"""Archive inserts (Vox-style documentary material): public-domain photos, newspaper pages, documents and
film clips, fetched once into the release "archive" (see .github/workflows/fetch.yml) and styled here.

Visual:
  {"type": "archive", "file": "lv1940_slots.jpg", "look": "print" | "clipping" | "plain",
   "crop": [x0, y0, x1, y1] (fractions of the source, optional), "page": 3 (PDF page, optional),
   "credit": "Arthur Rothstein / FSA, Library of Congress (no known restrictions)",
   "caption": "Las Vegas, 1940" (optional, printed under the photo), "motion": ..., "marks": ...}
  {"type": "clip", "file": "clip_lv_homemovie_1950s.mp4", "in": 12.0, "out": 18.0,
   "credit": "...", "newsreel": "Las Vegas, 1950s" | true}

Styled pictures are cached as PNGs and then behave like any generated frame (camera moves, marks, the
drawing hand, depth-free parallax), so nothing else in the pipeline needs to know where they came from.
"""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

from .config import ROOT
from .config import resolve_font
from .text import font

ARCHIVE_DIR = ROOT / "assets" / "archive"
LAYOUT_VERSION = 3  # bump when the styling/trim code changes, so cached frames and clips are rebuilt


def _pal(cfg):
    from .shots import hex_to_rgb
    return {k: hex_to_rgb(v) for k, v in cfg["style"]["palette"].items()}


def _source(spec: dict, cache: Path) -> Image.Image:
    path = ARCHIVE_DIR / spec["file"]
    if not path.exists():
        raise FileNotFoundError(f"archive file missing: {path} (run the Fetch archive workflow)")
    if path.suffix.lower() == ".pdf":
        page = int(spec.get("page", 1))
        out = cache / f"{path.stem}-p{page}.png"
        if not out.exists():
            subprocess.run(["pdftoppm", "-f", str(page), "-l", str(page), "-r", "170", "-png", "-singlefile",
                            str(path), str(out.with_suffix(""))], check=True)
        img = Image.open(out).convert("RGB")
    else:
        img = Image.open(path).convert("RGB")
    if spec.get("crop"):
        x0, y0, x1, y1 = spec["crop"]
        w, h = img.size
        img = img.crop((int(x0 * w), int(y0 * h), int(x1 * w), int(y1 * h)))
    return img


def _torn_mask(w: int, h: int, seed: int, rough: int) -> Image.Image:
    """Alpha mask with hand-torn newspaper edges."""
    rnd = np.random.default_rng(seed)
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)
    pts = []
    n = 40
    for i in range(n + 1):  # top
        pts.append((w * i / n, rnd.uniform(0, rough)))
    for i in range(n + 1):  # right
        pts.append((w - rnd.uniform(0, rough), h * i / n))
    for i in range(n, -1, -1):  # bottom
        pts.append((w * i / n, h - rnd.uniform(0, rough)))
    for i in range(n, -1, -1):  # left
        pts.append((rnd.uniform(0, rough), h * i / n))
    d.polygon(pts, fill=255)
    return m.filter(ImageFilter.GaussianBlur(0.8))


def clipping(img: Image.Image, cfg: dict, w: int, h: int, seed: int, caption: str | None) -> Image.Image:
    """Newspaper / document clipping: grey ink on aged paper, torn edges, slight tilt, drop shadow."""
    pal = _pal(cfg)
    rnd = np.random.default_rng(seed)
    gray = ImageOps.autocontrast(img.convert("L"), cutoff=0.5)
    gray = gray.filter(ImageFilter.UnsharpMask(radius=1.5, percent=60))
    aged = ImageOps.colorize(gray, black=(40, 36, 30), white=(241, 232, 206))
    max_w, max_h = int(w * 0.84), int(h * (0.56 if caption else 0.82))
    scale = min(max_w / aged.width, max_h / aged.height)
    aged = aged.resize((max(1, int(aged.width * scale)), max(1, int(aged.height * scale))), Image.LANCZOS)
    pad = max(8, int(min(w, h) * 0.012))
    piece = ImageOps.expand(aged, border=pad, fill=(241, 232, 206)).convert("RGBA")
    piece.putalpha(_torn_mask(piece.width, piece.height, seed, rough=pad * 1.4))
    angle = float(rnd.uniform(-2.5, 2.5))
    piece = piece.rotate(angle, resample=Image.BICUBIC, expand=True)
    canvas = Image.new("RGB", (w, h), pal["paper"])
    shadow = Image.new("RGBA", piece.size, (0, 0, 0, 0))
    shadow.paste((0, 0, 0, 80), mask=piece.split()[3])
    shadow = shadow.filter(ImageFilter.GaussianBlur(pad))
    x, y = (w - piece.width) // 2, (h - piece.height) // 2 - int(h * (0.12 if caption else 0.02))
    canvas.paste(shadow, (x + pad // 2, y + pad), shadow)
    canvas.paste(piece, (x, y), piece)
    if caption:
        _caption(canvas, caption, cfg, y + piece.height)
    return canvas


def print_photo(img: Image.Image, cfg: dict, w: int, h: int, seed: int, caption: str | None) -> Image.Image:
    from .shots import archival_print
    canvas = archival_print(img, cfg, w, h, seed, fit=0.56 if caption else 0.80, dy=-0.10 if caption else 0.0)
    if caption:
        _caption(canvas, caption, cfg, int(h * 0.64))
    return canvas


def plain(img: Image.Image, cfg: dict, w: int, h: int) -> Image.Image:
    """Full-frame archive still (for film frames and wide photos): warm duotone, no frame."""
    pal = _pal(cfg)
    gray = ImageOps.autocontrast(img.convert("L"), cutoff=1)
    tinted = ImageOps.colorize(gray, black=pal["ink"], white=tuple(min(255, c + 8) for c in pal["paper"]))
    return ImageOps.fit(tinted, (w, h), Image.LANCZOS)


def _caption(canvas: Image.Image, text: str, cfg: dict, y: int) -> None:
    pal = _pal(cfg)
    fnt = font(resolve_font(cfg["fonts"]["body"]), max(18, int(canvas.height * 0.028)))
    d = ImageDraw.Draw(canvas)
    tw = d.textlength(text, font=fnt)
    x = (canvas.width - tw) / 2
    yy = min(y + int(canvas.height * 0.012), int(canvas.height * 0.66))  # stays above the narration even at full zoom
    d.text((x, yy), text, font=fnt, fill=pal["ink"])


def ensure_archive(episode: dict, cfg: dict, cache: Path, log=print) -> dict[str, Path]:
    """Style every archive beat into a frame PNG (cached by spec), and collect credit lines."""
    cache.mkdir(parents=True, exist_ok=True)
    out: dict[str, Path] = {}
    credits: list[str] = []
    W, H = 1600, 900  # styled at working resolution; the renderer scales
    for beat in episode["beats"]:
        v = beat["visual"]
        if v["type"] != "archive":
            continue
        key = hashlib.sha1(repr({**{k: v.get(k) for k in ("file", "look", "crop", "page", "caption")}, "_layout": LAYOUT_VERSION}).encode()).hexdigest()[:10]
        dst = cache / f"archive-{beat['id']}-{key}.png"
        if not dst.exists():
            src = _source(v, cache)
            look = v.get("look", "print")
            seed = sum(map(ord, beat["id"]))
            if look == "clipping":
                img = clipping(src, cfg, W, H, seed, v.get("caption"))
            elif look == "plain":
                img = plain(src, cfg, W, H)
            else:
                img = print_photo(src, cfg, W, H, seed, v.get("caption"))
            img.save(dst)
            log(f"  archive {beat['id']}: {v['file']} ({look})")
        out[beat["id"]] = dst
        if v.get("credit") and v["credit"] not in credits:
            credits.append(v["credit"])
    for beat in episode["beats"]:
        v = beat["visual"]
        if v["type"] == "clip" and v.get("file") and v.get("credit") and v["credit"] not in credits:
            credits.append(v["credit"])
    for beat in list(episode["beats"]) + [b for sh in episode.get("shorts") or [] for b in sh["beats"]]:
        for ins in beat.get("inserts") or []:
            c = ins.get("credit")
            if not c and str(ins.get("file", "")).endswith((".jpg", ".png", ".pdf")) and not str(ins.get("file", "")).startswith("stock-"):
                c = "Library of Congress, Prints & Photographs Division (no known restrictions)"
            if c and c not in credits:
                credits.append(c)
    if credits:
        episode["sources"] = list(episode.get("sources") or []) + [f"Archive: {c}" for c in credits]
    return out


def ensure_clips(episode: dict, cache: Path, log=print) -> None:
    """Trim archive film files into per-beat clips the renderer plays (episodes/<slug>/clips/<id>.mp4 is
    still honoured for hand-made clips)."""
    cache.mkdir(parents=True, exist_ok=True)
    for beat in episode["beats"]:
        v = beat["visual"]
        if v["type"] != "clip" or not v.get("file"):
            continue
        src = ARCHIVE_DIR / v["file"]
        if not src.exists():
            raise FileNotFoundError(f"archive clip missing: {src}")
        a, b = float(v.get("in", 0)), float(v.get("out", 0) or 0)
        key = hashlib.sha1(f"{v['file']}|{a}|{b}|{LAYOUT_VERSION}".encode()).hexdigest()[:10]
        dst = cache / f"clip-{beat['id']}-{key}.mp4"
        if not dst.exists():
            cmd = ["ffmpeg", "-v", "error", "-y", "-ss", str(a), "-i", str(src)]
            if b > a:
                cmd += ["-t", str(b - a)]
            cmd += ["-an", "-vf", "scale=1280:-2,normalize=smoothing=20:strength=0.8,eq=brightness=0.04:contrast=1.08",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", str(dst)]
            subprocess.run(cmd, check=True)
            log(f"  clip {beat['id']}: {v['file']} {a:.1f}-{b:.1f}s")
        v["_clip"] = str(dst)
