"""True-peak / loudness gate for rendered files (same check the build runs after every render).

python tools/qc/audio_gate.py file.mp4 [...]   -> prints LUFS and dBTP per file, exit 1 if any true peak > -1.0 dBTP"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from factory.render import measure_audio  # noqa: E402

CEIL = -1.0
bad = 0
for f in sys.argv[1:]:
    i, tp = measure_audio(Path(f))
    ok = tp <= CEIL
    bad += not ok
    print(f"{'PASS' if ok else 'FAIL'}  {Path(f).name:16s} {i:6.1f} LUFS  {tp:5.1f} dBTP")
sys.exit(1 if bad else 0)
