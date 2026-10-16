"""Text rendering helpers (PIL) that produce RGBA numpy overlays."""
from __future__ import annotations

from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFont


@lru_cache(maxsize=64)
def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def wrap(text: str, fnt: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words, lines, line = text.split(), [], ""
    for word in words:
        trial = f"{line} {word}".strip()
        if fnt.getlength(trial) <= max_width or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def fit_font(text: str, path: str, max_width: int, max_height: int, start: int, min_size: int = 18):
    """Largest font size where the wrapped text fits the box."""
    size = start
    while size > min_size:
        fnt = font(path, size)
        lines = wrap(text, fnt, max_width)
        height = len(lines) * int(size * 1.12)
        if height <= max_height and all(fnt.getlength(l) <= max_width for l in lines):
            return fnt, lines
        size -= 4
    fnt = font(path, min_size)
    return fnt, wrap(text, fnt, max_width)


def text_block(
    lines: list[str],
    fnt: ImageFont.FreeTypeFont,
    fill,
    stroke_fill=None,
    stroke: int = 0,
    box_fill=None,
    pad: int = 0,
    line_gap: float = 1.12,
    align: str = "center",
    colors: list[list] | None = None,
) -> np.ndarray:
    """Render lines to an RGBA array. `colors` optionally gives a per-word fill for each line."""
    size = fnt.size
    widths = [fnt.getlength(l) for l in lines]
    w = int(max(widths) + 2 * pad + 2 * stroke + 4)
    lh = int(size * line_gap)
    h = int(lh * len(lines) + 2 * pad + 2 * stroke + size * 0.25)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    if box_fill is not None:
        draw.rounded_rectangle((0, 0, w - 1, h - 1), radius=max(6, size // 5), fill=box_fill)
    for i, line in enumerate(lines):
        y = pad + stroke + i * lh
        x0 = (w - widths[i]) / 2 if align == "center" else pad + stroke
        if colors and colors[i]:
            x = x0
            for word, color in zip(line.split(" "), colors[i]):
                draw.text((x, y), word, font=fnt, fill=color, stroke_width=stroke, stroke_fill=stroke_fill)
                x += fnt.getlength(word + " ")
        else:
            draw.text((x0, y), line, font=fnt, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)
    return np.array(img)


def blend(frame: np.ndarray, rgba: np.ndarray, x: int, y: int, opacity: float = 1.0) -> None:
    """Alpha-composite rgba onto frame (in place) with top-left at (x, y); clips at edges."""
    fh, fw = frame.shape[:2]
    h, w = rgba.shape[:2]
    x0, y0, x1, y1 = max(0, x), max(0, y), min(fw, x + w), min(fh, y + h)
    if x1 <= x0 or y1 <= y0:
        return
    sub = rgba[y0 - y : y1 - y, x0 - x : x1 - x]
    alpha = sub[..., 3:4].astype(np.float32) / 255.0 * opacity
    region = frame[y0:y1, x0:x1].astype(np.float32)
    frame[y0:y1, x0:x1] = (region * (1 - alpha) + sub[..., :3].astype(np.float32) * alpha).astype(np.uint8)
