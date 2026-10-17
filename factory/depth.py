"""Depth maps for the 2.5D parallax effect (Depth Anything V2 Small, Apache-2.0, runs on CPU).

A depth map is stored next to each frame as '<frame>.depth.png' (white = near, black = far).
If the model can't be loaded, everything still works — shots simply have no parallax.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

MODEL = "depth-anything/Depth-Anything-V2-Small-hf"
_pipe = None


def depth_path(image_path: Path) -> Path:
    return image_path.with_name(image_path.stem + ".depth.png")


def _load():
    global _pipe
    if _pipe is None:
        from transformers import pipeline  # heavy import, only when needed

        _pipe = pipeline("depth-estimation", model=MODEL, device=-1)
    return _pipe


def ensure_depth(paths: list[Path], log=print) -> int:
    todo = [p for p in paths if not depth_path(p).exists() and not p.name.endswith(".depth.png")]
    if not todo:
        return 0
    try:
        pipe = _load()
    except Exception as exc:  # noqa: BLE001
        log(f"Depth model unavailable ({exc}); parallax disabled")
        return 0
    made = 0
    for p in todo:
        try:
            img = Image.open(p).convert("RGB")
            res = pipe(img)
            d = np.asarray(res["depth"], dtype=np.float32)
            d = (d - d.min()) / max(1e-6, d.max() - d.min())
            Image.fromarray((d * 255).astype(np.uint8)).resize(img.size, Image.BILINEAR).save(depth_path(p))
            made += 1
        except Exception as exc:  # noqa: BLE001
            log(f"  depth failed for {p.name}: {exc}")
    log(f"Depth maps: {made} new")
    return made


def load_depth(image_path: Path | None) -> np.ndarray | None:
    if image_path is None:
        return None
    dp = depth_path(Path(image_path))
    if not dp.exists():
        return None
    return np.asarray(Image.open(dp).convert("L"), dtype=np.float32) / 255.0
