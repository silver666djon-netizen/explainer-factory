"""Storyboard stage: generate every frame BEFORE the montage, so bad frames can be fixed first.

python -m factory.storyboard episodes/<slug> [--redo b17,c03] [--offline]

- character reference portraits (assets/characters/<name>.png) are made once and reused;
- all frames + depth maps are written to out/frames/<slug>/ (the workflow publishes them as release 'frames-<slug>');
- numbered contact sheets go to out/storyboard/<slug>/ and to Telegram;
- the Flow/Grok prompt pack for hero frames and clips is written to episodes/<slug>/prompt_pack.md.
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw

from .config import ROOT, load_config, resolve_font
from .depth import depth_path, ensure_depth
from .images import ensure_images, ensure_photos, generate
from .prompts import write_pack
from .script import image_prompts, load_episode, photo_sources
from .text import font


def log(msg: str) -> None:
    print(msg, flush=True)


def ensure_characters(episode: dict, cfg: dict, offline: bool) -> list[Path]:
    made = []
    folder = ROOT / "assets" / "characters"
    folder.mkdir(parents=True, exist_ok=True)
    for name, desc in (episode.get("characters") or {}).items():
        path = folder / f"{name}.png"
        if path.exists() or offline:
            continue
        log(f"Character reference portrait: {name}")
        img = generate(cfg, f"character reference portrait of {desc}, three-quarter view, waist up, neutral friendly "
                            f"expression, plain cream background, even studio light", "ad")
        img.save(path)
        made.append(path)
    return made


def bump_variants(ep_dir: Path, keys: list[str], cache_dir: Path) -> None:
    f = ep_dir / "frames.json"
    data = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    var = data.setdefault("variants", {})
    for k in keys:
        var[k] = int(var.get(k, 0)) + 1
        for old in cache_dir.glob(f"{k}-*.png"):
            old.unlink()
    f.write_text(json.dumps(data, indent=2), encoding="utf-8")
    log(f"Redo: {', '.join(keys)}")


def contact_sheets(episode: dict, images: dict[str, Path], out_dir: Path, cfg: dict) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("sheet_*.jpg"):
        old.unlink()
    texts = {b["id"]: b["text"] for b in episode["beats"]}
    keys = list(images)
    tw, th, cols, rows = 480, 270, 3, 4
    lab_h = 58
    head = font(resolve_font(cfg["fonts"]["headline"]), 30)
    small = font("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf" if Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf").exists()
                 else resolve_font(cfg["fonts"]["body"]), 15)
    sheets = []
    per = cols * rows
    for s in range(0, len(keys), per):
        chunk = keys[s : s + per]
        sheet = Image.new("RGB", (cols * tw + (cols + 1) * 8, rows * (th + lab_h) + (rows + 1) * 8), (30, 27, 24))
        d = ImageDraw.Draw(sheet)
        for i, key in enumerate(chunk):
            x = 8 + (i % cols) * (tw + 8)
            y = 8 + (i // cols) * (th + lab_h + 8)
            im = Image.open(images[key]).convert("RGB")
            im.thumbnail((tw, th))
            sheet.paste(im, (x + (tw - im.width) // 2, y))
            hand = "images" in str(images[key].parent.name)
            d.rectangle((x, y + th, x + tw, y + th + lab_h), fill=(243, 233, 210))
            d.text((x + 8, y + th + 4), (("✋ " if hand else "") + key).upper(), font=head, fill=(210, 69, 47))
            base = key.split(".")[0]
            d.text((x + 8, y + th + 38), (texts.get(base, "")[:62]), font=small, fill=(30, 27, 24))
        path = out_dir / f"sheet_{s // per + 1:02d}.jpg"
        sheet.save(path, quality=86)
        sheets.append(path)
    return sheets


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("episode")
    ap.add_argument("--redo", default="")
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--no-telegram", action="store_true")
    args = ap.parse_args(argv)

    episode = load_episode(args.episode)
    cfg = load_config(episode.get("config"))
    slug = episode["slug"]
    ep_dir = Path(episode["_dir"])
    cache = ROOT / ".cache" / ("images-offline" if args.offline else "images") / slug
    cache.mkdir(parents=True, exist_ok=True)

    chars = ensure_characters(episode, cfg, args.offline)
    if chars:
        episode = load_episode(args.episode)  # refs now exist
    redo = [k.strip() for k in args.redo.replace(" ", ",").split(",") if k.strip()]
    if redo:
        bump_variants(ep_dir, redo, cache)

    prompts = image_prompts(episode)
    thumb = episode.get("thumbnail") or {}
    if thumb.get("prompt"):
        prompts["thumbnail"] = {"prompt": thumb["prompt"], "style": thumb.get("style", "ad"), "episode_dir": str(ep_dir)}
    images = ensure_images(cfg, prompts, cache, args.offline, log)
    photos = photo_sources(episode)
    if photos:
        images.update(ensure_photos(cfg, photos, cache, args.offline, log))
    ensure_depth([p for p in images.values()], log)

    frames_out = ROOT / "out" / "frames" / slug
    if frames_out.exists():
        shutil.rmtree(frames_out)
    frames_out.mkdir(parents=True)
    for p in cache.glob("*.png"):
        shutil.copy2(p, frames_out / p.name)
    sheets = contact_sheets(episode, images, ROOT / "out" / "storyboard" / slug, cfg)
    pack = write_pack(episode, cfg)
    log(f"Storyboard: {len(images)} frames, {len(sheets)} sheets, prompt pack: {pack}")

    if not args.no_telegram:
        from .notify import send_album, send_document, send_buttons
        send_album(sheets, f"🎬 Раскадровка {slug}: {len(images)} кадров. Проверь — номер кадра подписан на каждом.")
        if pack and pack.exists():
            send_document(pack, "Промпты для ключевых кадров (Flow) и живых вставок (Grok). Готовый файл присылай боту КАК ФАЙЛ с подписью-номером кадра.")
        send_buttons(f"Раскадровка {slug} готова. Монтируем?",
                     [[("✅ Раскадровка ок — монтаж", f"approve|{slug}")], [("🔁 Переделать кадры", f"redo|{slug}")]])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
