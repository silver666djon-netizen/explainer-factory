"""Asset intake check (tooling v2, item 16): Higgsfield images and clips arrive as pull requests from claude/* branches
(the review chat never pushes to main). Before merging, every added or changed media file is checked:

  - it decodes; images: size (16:9 stills >= 1920x1080), no alpha surprise; clips: length, fps, size, audio track
  - R51: an AI clip is 3-4 s by default; > 5 s only with a reason in the shot list; its length matches the shot list's
    stated length (--expect name=seconds, or a "length_s" in the PR's shots json) within 0.1 s — no slow-motion stretch
  - asset_license (R50): the file has a row in docs/ASSET_LICENSES.md (on the PR branch) naming the model
  - size: < 95 MB per file (GitHub's limit is 100 MB)

  python tools/intake_check.py <base ref> <head ref> [--expect stem=seconds ...] [--out report.md]
Exit 1 when anything blocks the merge."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
IMG = {".png", ".jpg", ".jpeg", ".webp"}
VID = {".mp4", ".mov", ".webm", ".m4v"}


def changed(base: str, head: str) -> list[str]:
    out = subprocess.run(["git", "diff", "--name-only", "--diff-filter=AM", f"{base}...{head}"], capture_output=True, text=True, cwd=ROOT).stdout
    return [l for l in out.splitlines() if Path(l).suffix.lower() in IMG | VID]


def probe(p: Path) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height,r_frame_rate,nb_frames",
                        "-of", "json", str(p)], capture_output=True, text=True)
    return json.loads(r.stdout or "{}")


def main(a: list[str]) -> int:
    base, head = a[0], a[1]
    expect, out = {}, None
    i = 2
    while i < len(a):
        if a[i] == "--expect":
            k, v = a[i + 1].split("=")
            expect[k.lower()] = float(v)
            i += 2
        elif a[i] == "--out":
            out = a[i + 1]
            i += 2
        else:
            i += 1
    import asset_license as AL
    rows = AL.load()
    files = changed(base, head)
    rep = ["# Asset intake check", "", f"{base}...{head}: {len(files)} media files", "", "| file | what | result |", "|---|---|---|"]
    bad = 0
    for f in files:
        p = ROOT / f
        notes, block = [], []
        mb = p.stat().st_size / 1e6
        if mb > 95:
            block.append(f"{mb:.0f} MB (over the 95 MB limit)")
        suf = p.suffix.lower()
        if suf in IMG:
            try:
                from PIL import Image
                with Image.open(p) as im:
                    im.load()
                    w, h = im.size
                    notes.append(f"{w}x{h} {im.mode}")
                    if abs(w / h - 16 / 9) < 0.03 and (w < 1920 or h < 1080):
                        block.append("16:9 still under 1920x1080")
            except Exception as e:  # noqa: BLE001
                block.append(f"does not decode: {e}")
        else:
            j = probe(p)
            v = next((s for s in j.get("streams", []) if s.get("codec_type") == "video"), None)
            if not v:
                block.append("no video stream / does not decode")
            else:
                dur = float(j.get("format", {}).get("duration", 0))
                fr = v.get("r_frame_rate", "0/1").split("/")
                fps = float(fr[0]) / float(fr[1] or 1)
                aud = any(s.get("codec_type") == "audio" for s in j.get("streams", []))
                notes.append(f"{dur:.2f} s, {fps:.0f} fps, {v.get('width')}x{v.get('height')}" + (", has audio (muted in the edit unless used as SFX)" if aud else ""))
                stem = p.stem.lower()
                if stem in expect and abs(expect[stem] - dur) > 0.1:
                    block.append(f"R51: {dur:.2f} s but the shot list says {expect[stem]:.2f} s")
                if dur > 5.05 and stem not in expect:
                    block.append("R51: over 5 s and no stated length / reason in the shot list")
                elif dur > 4.05 and stem not in expect:
                    notes.append("R51: longer than the 3-4 s default — needs its stated length")
                if fps and fps < 23:
                    notes.append(f"R51: {fps:.0f} fps — looks slowed / stretched?")
        r = AL.find(f, rows)
        if r is None:
            block.append("asset_license: no row in docs/ASSET_LICENSES.md")
        elif AL.incomplete(r):
            block.append(f"asset_license: row incomplete ({AL.incomplete(r)})")
        bad += bool(block)
        rep.append(f"| {f} | {'; '.join(notes)} | {'BLOCK: ' + '; '.join(block) if block else 'OK'} |")
    rep += ["", "Merge: " + ("BLOCKED" if bad else "OK")]
    text = "\n".join(rep) + "\n"
    if out:
        Path(out).write_text(text)
    print(text)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
