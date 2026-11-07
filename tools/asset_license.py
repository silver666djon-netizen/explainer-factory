"""docs/ASSET_LICENSES.md: one row per asset used in any video (tooling v2, item 7) and the release-blocking
asset_license check (tools/v2_qc.py).

A row's `file` is the asset's name without folder and extension (a10, ep04v2_k5_bomb, SpecialElite-Regular,
ub_night_spot, sfx:stamp ...), lower-cased when matched; `*` / `?` patterns cover a family (posters/*, hands/*). One row
covers every encode of the same asset (.png master, .jpg / .mp4 in public/). Columns:
  | file | kind | source URL | licence | date | attribution | notes |
kind: archive · ai-image · ai-video · font · music · sfx · voice · lottie · overlay · code · derived
AI rows name the model in `notes` ("model: ..."); a row that says "model: not recorded" passes the check (the row exists)
but is listed as incomplete in the QC report.

  python tools/asset_license.py check <plan.json> [kind]      rows missing for the assets of a rendered plan
  python tools/asset_license.py list                          the register as parsed
"""
from __future__ import annotations

import fnmatch
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "ASSET_LICENSES.md"
COLS = ["file", "kind", "source_url", "licence", "date", "attribution", "notes"]
HEAD = ["# Asset licences", "",
        "One row per asset used in any video (R50 / tooling v2). The release check `asset_license` (tools/v2_qc.py) blocks a "
        "release when an asset the render uses has no row here. `file` = the asset's name without folder or extension "
        "(patterns with `*` cover a family). AI-generated rows name the model in Notes.", "",
        "| file | kind | source URL | licence | date | attribution | notes |", "|---|---|---|---|---|---|---|"]
FILE_RE = re.compile(r"\.(png|jpe?g|webp|gif|mp4|webm|mov|mp3|wav|flac|ogg|m4a|ttf|otf|woff2?|lottie|json)$", re.I)


def key(name: str) -> str:
    n = str(name).replace("\\", "/")
    n = re.sub(r"^(\.\./)*(public/)?(v2/)?", "", n)
    if n.startswith(("sfx:", "music:", "voice:", "font:", "lottie:")):
        return n.lower()
    base = n.rsplit("/", 1)
    folder, leaf = (base[0] + "/", base[1]) if len(base) == 2 else ("", base[0])
    leaf = FILE_RE.sub("", leaf)
    return (folder + leaf).lower() if folder in ("posters/", "props/", "hands/", "tooling/") else leaf.lower()


def _cells(line: str) -> list[str]:
    return [c.strip().replace("\\|", "|") for c in line.strip().strip("|").split(" | ")]


def load(doc: Path = DOC) -> list[dict]:
    if not doc.exists():
        return []
    rows = []
    for line in doc.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| ") or line.startswith("| file |") or line.startswith("|---"):
            continue
        c = _cells(line)
        if len(c) < len(COLS):
            c += [""] * (len(COLS) - len(c))
        rows.append(dict(zip(COLS, c[: len(COLS)])))
    return rows


def _fmt(r: dict) -> str:
    return "| " + " | ".join(str(r.get(k, "") or "").replace("|", "\\|").replace("\n", " ") for k in COLS) + " |"


def save(rows: list[dict], doc: Path = DOC) -> None:
    text = doc.read_text(encoding="utf-8") if doc.exists() else ""
    tail = ""
    if "\n## " in text:  # sections after the table (notes) are kept
        tail = text[text.index("\n## "):]
    body = HEAD + [_fmt(r) for r in sorted(rows, key=lambda r: (r["kind"], r["file"]))]
    doc.write_text("\n".join(body) + "\n" + tail, encoding="utf-8")


def upsert(row: dict, doc: Path = DOC) -> None:
    row = {**{k: "" for k in COLS}, **row, "file": key(row["file"])}
    rows = [r for r in load(doc) if r["file"].lower() != row["file"]]
    save(rows + [row], doc)


def find(name: str, rows: list[dict]) -> dict | None:
    """The exact row, else the most specific pattern row (most literal characters) that matches."""
    k = key(name)
    best, score = None, -1
    for r in rows:
        pat = r["file"].lower()
        if pat == k:
            return r
        if any(ch in pat for ch in "*?[") and fnmatch.fnmatch(k, pat):
            s = len(re.sub(r"[*?\[\]]", "", pat))
            if s > score:
                best, score = r, s
    return best


def year_of_row(r: dict | None) -> int | None:
    m = re.search(r"\b(1[5-9]\d\d|20\d\d)\b", (r or {}).get("date", ""))
    return int(m.group(1)) if m else None


def incomplete(r: dict) -> str | None:
    if not r.get("licence") or r["licence"].lower() in ("?", "unknown", "tbd"):
        return "no licence"
    if r.get("kind", "").startswith("ai-") and ("model:" not in r.get("notes", "").lower() or "not recorded" in r.get("notes", "").lower()):
        return "AI model not recorded"
    if r.get("kind") == "archive" and not re.search(r"\d{4}", r.get("date", "")):
        return "no item date"
    return None


def used_assets(plan_kind: dict) -> list[str]:
    """Every asset one rendered plan uses: files the composition loads, fonts, music cues, SFX kinds, the voice."""
    out: set[str] = set()

    def walk(o):
        if isinstance(o, dict):
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
        elif isinstance(o, str) and FILE_RE.search(o) and not o.startswith("v2_"):
            out.add(o)

    data = plan_kind.get("data") or {}
    walk({k: v for k, v in data.items() if k not in ("fonts",)})
    for f in (data.get("fonts") or {}):
        out.add(f)
    au = plan_kind.get("audio") or {}
    for m in au.get("music") or []:
        out.add("music:" + m)
    for ev in au.get("sfx") or []:
        kind, _, arg = str(ev[2]).partition(":")
        out.add(f"music:{arg}" if kind == "stab" else f"sfx:{kind}")
    out.add("voice:" + ("ru" if any(b.get("en") for b in plan_kind.get("beats") or []) else "en"))
    if any("_ink" in s or s.get("overs") for s in data.get("shots") or []):
        out.add("hands/hand.png")  # V2.tsx draws ink, stamps and cuts with the hand images in public/hands
    return sorted(out)


def check(names: list[str], rows: list[dict] | None = None) -> tuple[list[str], list[str]]:
    """-> (missing: assets without a row, incomplete: rows that exist but lack the model / licence / date)."""
    rows = load() if rows is None else rows
    miss, inc, seen = [], [], set()
    for n in names:
        r = find(n, rows)
        if r is None:
            miss.append(n)
            continue
        why = incomplete(r)
        if why and r["file"] not in seen:
            seen.add(r["file"])
            inc.append(f"{r['file']}: {why}")
    return miss, inc


def main(a: list[str]) -> int:
    if a and a[0] == "list":
        for r in load():
            print(json.dumps(r, ensure_ascii=False))
        return 0
    if a and a[0] == "check":
        P = json.loads(Path(a[1]).read_text())
        bad = 0
        for kind in ([a[2]] if len(a) > 2 else list(P)):
            miss, inc = check(used_assets(P[kind]))
            print(f"{kind}: {len(miss)} without a row" + (": " + ", ".join(miss) if miss else "") +
                  (f"; {len(inc)} incomplete: " + "; ".join(inc) if inc else ""))
            bad |= bool(miss)
        return 1 if bad else 0
    raise SystemExit(__doc__)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
