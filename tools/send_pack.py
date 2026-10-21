"""Send a folder of reference files to Telegram as documents (originals, no compression).
python tools/send_pack.py <folder> "<intro text>"  — run by .github/workflows/send-pack.yml (secrets live there)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from factory.notify import send_document, send_text  # noqa: E402

folder = Path(sys.argv[1])
intro = sys.argv[2] if len(sys.argv) > 2 else ""
captions = {}
cap_file = folder / "captions.txt"
if cap_file.exists():
    for line in cap_file.read_text(encoding="utf-8").splitlines():
        if "|" in line:
            k, v = line.split("|", 1)
            captions[k.strip()] = v.strip()
if intro:
    send_text(intro)
for f in sorted(folder.iterdir()):
    if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".mp4"):
        send_document(f, captions.get(f.name, f.name))
        print("sent", f.name)
