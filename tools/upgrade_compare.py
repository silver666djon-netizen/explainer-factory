"""Remotion upgrade check (tooling v2, item 1): what changed between the toolchain the Ep.4 v2 master was made with
(Remotion 4.0.290) and 4.0.541. Nothing is published to the episode's drafts and the episode is not re-rendered.

  python tools/upgrade_compare.py qc <baseline qc md> <new qc md> <out md>
      every check / self-test row whose result changed (and checks that are new)
  python tools/upgrade_compare.py stills <old dir> <new dir> <out md>
      the same V2 frames rendered by both versions: mean / max pixel difference per frame
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image


def table(md: str, header: str) -> dict[str, list[str]]:
    rows, on = {}, False
    for line in md.splitlines():
        if line.startswith(header):
            on = True
            continue
        if on:
            if line.startswith("|---"):
                continue
            if not line.startswith("|"):
                if rows:
                    break
                continue
            c = [x.strip() for x in line.strip().strip("|").split(" | ")]
            rows[c[0]] = c[1:]
    return rows


def qc(base: str, new: str, out: str) -> int:
    b, n = Path(base).read_text(), Path(new).read_text()
    lines = ["# Remotion 4.0.290 -> 4.0.541 · QC on the Ep.4 v2 master", ""]
    changed = 0
    for title, header in (("Release checks", "| check | what |"), ("Self-tests (R40)", "| check | planted bug |")):
        tb, tn = table(b, header), table(n, header)
        lines += [f"## {title}", "", "| check | before (4.0.290) | after (4.0.541) |", "|---|---|---|"]
        for k in sorted(set(tb) | set(tn), key=lambda x: (x not in tb, x)):
            vb, vn = (tb.get(k) or ["", "—"])[-1], (tn.get(k) or ["", "—"])[-1]
            if k not in tb:
                lines.append(f"| {k} | (new check) | {vn} |")
            elif vb != vn:
                changed += 1
                lines.append(f"| {k} | {vb} | **{vn}** |")
        lines += [f"| (all other rows) | unchanged | unchanged |", ""]
    lines.insert(2, f"Rows whose result changed: {changed}.")
    Path(out).write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


def stills(old: str, new: str, out: str) -> int:
    lines = ["## Same frames, both versions (V2 composition, the Ep.4 v2 plan)", "", "| frame | mean abs diff (0-255) | max | pixels > 8 |", "|---|---|---|---|"]
    worst = 0.0
    for p in sorted(Path(new).glob("*.png")):
        q = Path(old) / p.name
        if not q.exists():
            lines.append(f"| {p.stem} | old render missing | | |")
            continue
        a = np.asarray(Image.open(p).convert("RGB")).astype(np.int16)
        c = np.asarray(Image.open(q).convert("RGB")).astype(np.int16)
        if a.shape != c.shape:
            lines.append(f"| {p.stem} | size differs {a.shape} vs {c.shape} | | |")
            continue
        d = np.abs(a - c)
        worst = max(worst, float(d.mean()))
        lines.append(f"| {p.stem} | {d.mean():.3f} | {int(d.max())} | {float((d.max(axis=2) > 8).mean()) * 100:.2f} % |")
    lines += ["", f"Worst mean difference: {worst:.3f} (identical = 0; < 0.5 is invisible encoder-level noise)."]
    with open(out, "a") as fh:
        fh.write("\n" + "\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    a = sys.argv[1:]
    sys.exit(qc(a[1], a[2], a[3]) if a[0] == "qc" else stills(a[1], a[2], a[3]))
