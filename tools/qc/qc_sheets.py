"""QC: contact sheets of a video, one frame every STEP seconds, with timestamps.
usage: python qc_sheets.py video.mp4 out_dir [step] [per_sheet]"""
import subprocess, sys, os
from PIL import Image, ImageDraw

video, out = sys.argv[1], sys.argv[2]
step = float(sys.argv[3]) if len(sys.argv) > 3 else 1.5
per = int(sys.argv[4]) if len(sys.argv) > 4 else 30
os.makedirs(out, exist_ok=True)
dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video]))
fr = os.path.join(out, "frames")
os.makedirs(fr, exist_ok=True)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-vf", f"fps=1/{step},scale=480:-2", os.path.join(fr, "%05d.jpg")], check=True)
files = sorted(os.listdir(fr))
cols = 5
for s in range(0, len(files), per):
    chunk = files[s:s + per]
    im0 = Image.open(os.path.join(fr, chunk[0]))
    w, h = im0.size
    rows = (len(chunk) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * w, rows * h), "black")
    d = ImageDraw.Draw(sheet)
    for i, f in enumerate(chunk):
        x, y = (i % cols) * w, (i // cols) * h
        sheet.paste(Image.open(os.path.join(fr, f)), (x, y))
        t = (s + i) * step
        d.rectangle((x, y, x + 70, y + 18), fill="black")
        d.text((x + 3, y + 3), f"{int(t // 60)}:{t % 60:04.1f}", fill="yellow")
    sheet.save(os.path.join(out, f"sheet_{s // per + 1:02d}.jpg"), quality=80)
print(dur, len(files))
