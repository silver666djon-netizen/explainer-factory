"""Side-by-side comparison of image models -> Telegram + tests/imgtest/.

python -m factory.imgtest  (needs Cloudflare + Telegram secrets)
"""
from __future__ import annotations

import copy
import io
from pathlib import Path

from PIL import Image, ImageDraw

from .config import ROOT, load_config, resolve_font
from .images import _cloudflare
from .notify import _api
from .text import font

LARRY = ("a cheerful middle-aged man with a round face and a thin moustache, wearing a loud yellow checked "
         "sports jacket and a red fedora")
TESTS = [
    ("larry_win", f"{LARRY} jumping for joy beside a roulette table, arms in the air", "comic"),
    ("croupier", "a slick casino croupier with slicked-back silver hair and a thin knowing smile, white dinner jacket "
                 "and black bow tie, smiling behind a roulette table, mid shot", "ad"),
    ("chips", "five colourful casino chips stacked neatly on green felt, studio light", "ad"),
    ("larry_slots", f"{LARRY} wandering between rows of glowing slot machines", "ad"),
]
MODELS = [("A — сейчас (FLUX.1 schnell)", "@cf/black-forest-labs/flux-1-schnell"),
          ("B — новая (FLUX.2 klein 4B)", "@cf/black-forest-labs/flux-2-klein-4b")]


def main() -> int:
    out_dir = ROOT / "tests" / "imgtest"
    out_dir.mkdir(parents=True, exist_ok=True)
    cfg0 = load_config()
    lab_font = font(resolve_font(cfg0["fonts"]["headline"]), 44)
    for key, prompt, style in TESTS:
        tiles = []
        for label, model in MODELS:
            cfg = copy.deepcopy(cfg0)
            cfg["images"]["model"] = model
            img = _cloudflare(cfg, prompt, style).convert("RGB")
            img = img.resize((960, int(960 * img.height / img.width)))
            canvas = Image.new("RGB", (960, img.height + 70), (243, 233, 210))
            canvas.paste(img, (0, 70))
            ImageDraw.Draw(canvas).text((20, 12), label, font=lab_font, fill=(30, 27, 24))
            tiles.append(canvas)
            img.save(out_dir / f"{key}_{model.split('/')[-1]}.png")
        h = max(t.height for t in tiles)
        combo = Image.new("RGB", (1940, h), (30, 27, 24))
        combo.paste(tiles[0], (0, 0))
        combo.paste(tiles[1], (980, 0))
        path = out_dir / f"{key}_compare.jpg"
        combo.save(path, quality=88)
        buf = io.BytesIO()
        combo.save(buf, "JPEG", quality=85)
        _api("sendPhoto", data={"caption": f"Сравнение картинок: {key}. Слева сейчас, справа FLUX.2"},
             files={"photo": ("compare.jpg", buf.getvalue(), "image/jpeg")})
        print("sent", key)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
