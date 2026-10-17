"""Three thumbnail variants for YouTube 'Test & compare': python -m factory.thumbs episodes/<slug> [--send]"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import ROOT, load_config
from .images import _cache_name, _manual_image
from .meta import thumbnail
from .script import image_prompts, load_episode


def frame_path(cfg, episode, key: str) -> Path | None:
    prompts = image_prompts(episode)
    th = episode.get("thumbnail") or {}
    if key == "thumbnail" and th.get("prompt"):
        prompts["thumbnail"] = {"prompt": th["prompt"], "style": th.get("style", "ad")}
    if key not in prompts:
        return None
    v = prompts[key]
    manual = _manual_image(episode.get("_dir"), key)
    if manual:
        return manual
    variants = {}
    fj = ROOT / "episodes" / episode["slug"] / "frames.json"
    if fj.exists():
        variants = json.loads(fj.read_text()).get("variants", {})
    p = ROOT / ".cache" / "images" / episode["slug"] / _cache_name(cfg, key, v["prompt"], v.get("style", "ad"), int(variants.get(key, 0)))
    return p if p.exists() else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("episode")
    ap.add_argument("--out", default=None)
    ap.add_argument("--send", action="store_true")
    a = ap.parse_args()
    episode = load_episode(a.episode)
    cfg = load_config(episode.get("config"))
    th = episode.get("thumbnail") or {}
    text = th.get("text") or episode["title"]
    keys = th.get("variants") or ["thumbnail", th.get("beat") or "b17", "n21"]
    out = Path(a.out or ROOT / "out" / episode["slug"])
    out.mkdir(parents=True, exist_ok=True)
    made = []
    for letter, key in zip("ABC", keys):
        src = frame_path(cfg, episode, key)
        if not src:
            print(f"no frame for {key}")
            continue
        made.append(thumbnail(cfg, src, text, out / f"thumbnail_{letter}.jpg"))
        print(f"thumbnail_{letter}: {key}")
    if a.send and made:
        from .notify import send_album
        send_album(made, f"Обложки для «{episode['title']}» — A / B / C (YouTube сам сравнит их на зрителях)")


if __name__ == "__main__":
    main()
