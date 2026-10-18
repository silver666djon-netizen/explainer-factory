"""Stock scouting: for every stock query in an episode, fetch 8 Pixabay candidates and draw one contact
sheet per kind (photos / videos) with numbered thumbnails, so a human (or Claude) can pick by eye.
Picks go back into the script as "pick": <pixabay id>.  python -m factory.stock_scout episodes/<slug>"""
from __future__ import annotations

import io
import json
import os
import sys
from pathlib import Path

import requests
from PIL import Image, ImageDraw

from .script import load_episode


def queries(ep: dict):
    for b in ep["beats"]:
        v = b["visual"]
        if v.get("type") == "clip" and v.get("stock") and not v.get("pick"):
            yield "video", v["stock"], b["id"]
        if v.get("type") == "archive" and v.get("stock_photo") and not v.get("pick"):
            yield "photo", v["stock_photo"], b["id"]
        for ins in b.get("inserts") or []:
            if ins.get("stock_photo") and not ins.get("pick"):
                yield "photo", ins["stock_photo"], b["id"]
    for sh in ep.get("shorts") or []:
        for b in sh["beats"]:
            for ins in b.get("inserts") or []:
                if ins.get("stock_photo") and not ins.get("pick"):
                    yield "photo", ins["stock_photo"], sh["id"]


def main() -> int:
    ep = load_episode(sys.argv[1])
    key = os.environ["PIXABAY_API_KEY"]
    out = Path("out/stock_scout"); out.mkdir(parents=True, exist_ok=True)
    sheets: dict[str, list] = {"photo": [], "video": []}
    data = {}
    seen = set()
    for kind, q, bid in queries(ep):
        if (kind, q) in seen:
            continue
        seen.add((kind, q))
        url = "https://pixabay.com/api/videos/" if kind == "video" else "https://pixabay.com/api/"
        params = {"key": key, "q": q, "per_page": 8, "safesearch": "true"}
        if kind == "photo":
            params.update({"image_type": "photo", "orientation": "horizontal"})
        hits = requests.get(url, params=params, timeout=60).json().get("hits", [])
        row = []
        for h in hits[:8]:
            if kind == "video":
                th = (h["videos"].get("tiny") or {}).get("thumbnail") or f"https://i.vimeocdn.com/video/{h.get('picture_id')}_295x166.jpg"
            else:
                th = h.get("webformatURL") or h.get("previewURL")
            try:
                im = Image.open(io.BytesIO(requests.get(th, timeout=30).content)).convert("RGB")
            except Exception:  # noqa: BLE001
                im = Image.new("RGB", (320, 180), "gray")
            row.append((h["id"], im, h.get("tags", ""), h.get("duration")))
        data[f"{kind}:{q}"] = [{"id": i, "tags": t, "duration": d} for i, _, t, d in row]
        sheets[kind].append((q, bid, row))
    for kind, rows in sheets.items():
        if not rows:
            continue
        W, H = 260, 160
        sheet = Image.new("RGB", (W * 8 + 260, (H + 18) * len(rows)), "black")
        d = ImageDraw.Draw(sheet)
        for r, (q, bid, row) in enumerate(rows):
            y = r * (H + 18)
            d.text((4, y + 4), f"{bid}", fill="yellow")
            d.text((4, y + 22), q[:38], fill="white")
            for c, (i, im, tags, dur) in enumerate(row):
                im.thumbnail((W - 4, H - 4))
                x = 260 + c * W
                sheet.paste(im, (x, y))
                d.rectangle((x, y + H - 2, x + W - 4, y + H + 16), fill="black")
                d.text((x + 2, y + H), f"{c+1}: #{i}" + (f" {dur}s" if dur else ""), fill="yellow")
        sheet.save(out / f"scout_{kind}.jpg", quality=80)
    (out / "scout.json").write_text(json.dumps(data, indent=1))
    print({k: len(v) for k, v in sheets.items()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
