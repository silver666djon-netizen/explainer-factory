"""Overlay a labelled 0.1 grid on pictures to read mark coordinates. usage: grid.py out.jpg cols img1 img2 ..."""
import sys
from PIL import Image, ImageDraw
out, cols, paths = sys.argv[1], int(sys.argv[2]), sys.argv[3:]
tiles = []
for p in paths:
    im = Image.open(p).convert("RGB").resize((640, 360)); d = ImageDraw.Draw(im)
    for i in range(1, 10):
        x, y = 64 * i, 36 * i
        d.line((x, 0, x, 360), fill=(0, 90, 255), width=1); d.line((0, y, 640, y), fill=(0, 90, 255), width=1)
        d.text((x + 2, 2), f".{i}", fill=(0, 0, 200)); d.text((2, y + 1), f".{i}", fill=(0, 0, 200))
    d.rectangle((560, 340, 640, 360), fill="black"); d.text((564, 344), p.split("/")[-1][:12], fill="yellow")
    tiles.append(im)
rows = (len(tiles) + cols - 1) // cols
sheet = Image.new("RGB", (640 * cols, 360 * rows), "white")
for i, t in enumerate(tiles):
    sheet.paste(t, ((i % cols) * 640, (i // cols) * 360))
sheet.save(out, quality=85)
