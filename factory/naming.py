"""Release file names and Telegram headers (production rule 22).

Files: cs_ep04_r78_long.mp4, cs_ep04_r78_s1.mp4 … s7, cs_ep04_r78_description.txt (language versions:
cs_ep03_r85_ru_long.mp4). Header: "CoinSense · EP04 · r78 · FINAL CANDIDATE · replaces r77".

python -m factory.naming rename <out_dir> <episode dir> <run number> [lang]   -> renames the build output in place"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

STATUSES = ("PREVIEW", "STILLS", "FINAL CANDIDATE", "APPROVED FINAL", "RU REVIEW", "SHORTS")
CHANNEL = "CoinSense"


def episode_number(ep_dir: str | Path) -> int:
    """The case-file number on the end screen (Ep.3 = case file 003); fallback: the folder number minus one."""
    ep_dir = Path(ep_dir)
    try:
        s = json.loads((ep_dir / "script.json").read_text(encoding="utf-8"))
        for b in s.get("beats") or []:
            es = (b.get("visual") or {}).get("endscreen")
            if es and str(es.get("number", "")).strip().isdigit():
                return int(es["number"])
    except (OSError, ValueError):
        pass
    m = re.match(r"(\d+)", ep_dir.name)
    return max(1, int(m.group(1)) - 1) if m else 0


def parse_tag(tag: str) -> tuple[str, str | None, int]:
    """'0005-drip-pricing-r78' -> ('0005-drip-pricing', None, 78); '0004-fake-sale-ru-r85' -> (…, 'ru', 85)."""
    m = re.match(r"^(.*?)(?:-([a-z]{2}))?-r(\d+)$", tag)
    if not m:
        raise ValueError(f"not a release tag: {tag}")
    return m.group(1), m.group(2), int(m.group(3))


def prefix(epno: int, run: int, lang: str | None = None) -> str:
    return f"cs_ep{epno:02d}_r{run}" + (f"_{lang}" if lang else "")


def header(epno: int, run: int, status: str, replaces: str | None = None) -> str:
    h = f"{CHANNEL} · EP{epno:02d} · r{run} · {status.upper()}"
    if replaces:
        h += f" · replaces {replaces if str(replaces).startswith('r') else 'r' + str(replaces)}"
    return h


def kind_of(name: str) -> str | None:
    """'long' / 's3' / 'description' / 'srt' / 'thumbnail' for any old or new file name."""
    n = name.lower()
    if n.endswith(".srt"):
        return "srt"
    if n.endswith("description.txt"):
        return "description"
    if n.endswith((".jpg", ".png")) and "thumb" in n:
        return "thumbnail"
    m = re.search(r"(?:^|_)(?:short_)?(s\d+)\.mp4$", n)
    if m:
        return m.group(1)
    if n.endswith(".mp4") and "long" in n:
        return "long"
    return None


def rename(out_dir: str | Path, ep_dir: str | Path, run: int, lang: str | None = None) -> list[str]:
    out_dir = Path(out_dir)
    pre = prefix(episode_number(ep_dir), run, lang)
    done = []
    for f in sorted(out_dir.iterdir()):
        k = kind_of(f.name)
        if k is None:
            continue
        ext = {"srt": ".srt", "description": ".txt", "thumbnail": f.suffix}.get(k, ".mp4")
        new = out_dir / (f"{pre}_long{ext}" if k == "srt" else f"{pre}_{k}{ext}")
        if new != f:
            f.rename(new)
            done.append(f"{f.name} -> {new.name}")
    return done


if __name__ == "__main__":
    if len(sys.argv) >= 5 and sys.argv[1] == "rename":
        for line in rename(sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5] if len(sys.argv) > 5 and sys.argv[5] else None):
            print(line)
