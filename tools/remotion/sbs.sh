#!/usr/bin/env bash
# Side by side per pilot beat: left = the r90 render (same segments), right = the Remotion pilot.
# tools/remotion/sbs.sh <public dir> <r90 release dir> <render dir>
set -euo pipefail
PUB=$1; REL=$2; RD=$3
FONT=assets/fonts/ArchivoBlack-Regular.ttf
python3 - "$PUB" "$REL" "$RD" <<'PY'
import json, subprocess, sys
pub, rel, rd = sys.argv[1:4]
idx = json.load(open(f"{pub}/pieces.json"))
font = "assets/fonts/ArchivoBlack-Regular.ttf"
import os
for name, p in idx.items():
    if not os.path.exists(f"{rd}/{name}.mp4"):
        continue
    W, H = p["W"], p["H"]
    parts = []
    for k, (video, t0, frames, letterbox) in enumerate(p["segments"]):
        seg = json.load(open(f"{pub}/{name}.json"))["segments"][k]
        src = f"{rel}/{video}"
        out = f"{rd}/_l_{name}_{k}.mp4"
        t = t0
        vf = f"scale={W}:{H}" if not letterbox else f"scale={W}:-2,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0x1E1B18"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", src, "-frames:v", str(frames), "-an", "-vf", f"{vf},fps=30",
                        "-c:v", "libx264", "-crf", "14", "-preset", "veryfast", out], check=True)
        parts.append(out)
    lst = f"{rd}/_l_{name}.txt"
    open(lst, "w").write("".join(f"file '{p_.split('/')[-1]}'\n" for p_ in parts))
    left = f"{rd}/_l_{name}.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", left], check=True)
    fs = int(H * 0.028)
    lab = lambda txt: f"drawtext=fontfile={font}:text='{txt}':x=(w-tw)/2:y=h-{int(fs*1.8)}:fontsize={fs}:fontcolor=white:box=1:boxcolor=black@0.6:boxborderw={fs//3}"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", left, "-i", f"{rd}/{name}.mp4",
                    "-filter_complex", f"[0:v]{lab('r90  (Python engine)')}[a];[1:v]{lab('Remotion pilot')}[b];[a][b]hstack=inputs=2[v]",
                    "-map", "[v]", "-map", "1:a", "-c:v", "libx264", "-crf", "18", "-preset", "veryfast", "-c:a", "aac", "-b:a", "192k",
                    f"{rd}/cs_pilot_remotion_{name}_sbs.mp4"], check=True)
    print("sbs", name)
PY
