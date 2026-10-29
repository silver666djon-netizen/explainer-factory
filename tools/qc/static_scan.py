"""Static-frame scan (rule 26 / Klot r78 G1): runs of >= 0.6 s where the picture (outside the caption band and the tab)
does not move. python tools/qc/static_scan.py <video.mp4> <timings.json>  -> exit 1 if any run."""
import sys, json, subprocess, numpy as np
vid, tj = sys.argv[1], sys.argv[2]
W, H, FPS = 192, 108, 12
vert = 'short' in vid or '_s' in vid.split('/')[-1]
if vert: W, H = 108, 192
p = subprocess.run(["ffmpeg","-v","error","-i",vid,"-vf",f"fps={FPS},scale={W}:{H}","-f","rawvideo","-pix_fmt","gray","-"],capture_output=True).stdout
f = np.frombuffer(p, np.uint8).reshape(-1, H, W).astype(np.float32)
m = np.ones((H, W), bool)
if not vert:
    m[int(H*0.74):] = False; m[:int(H*0.25), int(W*0.80):] = False
else:
    m[int(H*0.62):] = False
d = np.array([np.abs(f[i]-f[i-1])[m].mean() for i in range(1, len(f))])
st = d < 0.08
T = json.load(open(tj))
beats = T['beats'] if not vert else None
runs, i = [], 0
while i < len(st):
    if st[i]:
        j = i
        while j < len(st) and st[j]: j += 1
        if (j - i) / FPS >= 0.6: runs.append((i / FPS, j / FPS))
        i = j
    else: i += 1
def beat_at(t):
    if not beats: return ''
    b = [x for x in beats if x['start'] <= t + 0.3]
    return b[-1]['id'] if b else ''
for a, b in runs:
    print(f"{int(a//60)}:{a%60:05.2f}-{int(b//60)}:{b%60:05.2f} ({b-a:.1f}s) {beat_at(a)}")
print(len(runs), 'static runs')
sys.exit(1 if runs else 0)
