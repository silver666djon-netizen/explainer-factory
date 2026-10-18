"""Draw every marked/bubbled picture beat as it will look (long 16:9 and Shorts window) for a visual check.
usage: python marks_audit.py <episode dir> <frames dir> <out.jpg> [beat ids...]"""
import sys, glob, os, json
sys.path.insert(0, "/home/claude/explainer-factory")
import numpy as np
from PIL import Image, ImageDraw
from factory.config import load_config
from factory.script import load_episode
from factory.render import _image_keys
from factory.shots import ImageShot

ep_dir, fr_dir, out = sys.argv[1], sys.argv[2], sys.argv[3]
only = set(sys.argv[4:])
ep = load_episode(ep_dir); cfg = load_config(ep.get("config"))
lookup = {b["id"]: b for b in ep["beats"]}
files = {os.path.basename(f).rsplit("-", 1)[0]: f for f in glob.glob(f"{fr_dir}/*.png") if "depth" not in f}
items = []
pool = [x for sh in ep.get("shorts") or [] for x in sh["beats"]] if "shorts" in only else ep["beats"] + [x for sh in ep.get("shorts") or [] for x in sh["beats"]]
if "shorts" in only:
    only = set()
for b in pool:
    b.setdefault("id", "short")
    v = b["visual"]
    if v["type"] not in ("image", "reuse") or not (v.get("marks") or b.get("bubble")):
        continue
    if only and b["id"] not in only:
        continue
    v.setdefault("_beat", b["id"])
    key = _image_keys(v, lookup)[0]
    if key not in files:
        continue
    items.append((b["id"], key, v.get("motion", "static"), v.get("marks") or [], b.get("bubble")))
tiles = []
for bid, key, motion, marks, bub in items:
    img = Image.open(files[key]).convert("RGB")
    row = []
    for size in ((960, 540), (540, 960)):
        mk = [dict(m, at=0.0, dur=0.01) for m in marks]
        sh = ImageShot(0, 4.0, img, motion, size, cfg, marks=mk)
        fr = sh.frame(3.9)
        im = Image.fromarray(fr)
        d = ImageDraw.Draw(im)
        if bub:
            x, y = sh.to_screen(float(bub.get("x", 0.5)), float(bub.get("y", 0.3)), 3.9)
            d.ellipse((x - 40, y - 25, x + 40, y + 25), outline=(0, 120, 255), width=4)
            d.text((x - 30, y - 6), str(bub["text"])[:12], fill=(0, 0, 255))
        d.rectangle((0, 0, 140, 22), fill="black"); d.text((4, 4), f"{bid} [{key}]", fill="yellow")
        row.append(im.resize((size[0] // 2, size[1] // 2)))
    tiles.append(row)
W = 480 + 270
sheet = Image.new("RGB", (W * 3, 480 * ((len(tiles) + 2) // 3)), "white")
for i, (a, b) in enumerate(tiles):
    x, y = (i % 3) * W, (i // 3) * 480
    sheet.paste(a, (x, y)); sheet.paste(b, (x + 480, y))
sheet.save(out, quality=82)
print(len(tiles), [t[0] for t in items])
