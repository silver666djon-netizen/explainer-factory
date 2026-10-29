"""Release-blocking checks (Klot r84 part C) on the long video and every Short, built from the episode + real timings.
Exit 1 when any check fails. The CI build runs the same checks on the real plans (with the real narration) and
publishes qc_checks.md / qc_checks.json next to the videos.
OPENROUTER_API_KEY=audit-offline python3 tools/qc/release_checks.py episodes/<slug> <timings.json> [--out report.md]
  [--skip voice_cut_check,...]"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("OPENROUTER_API_KEY", "audit-offline")


def main() -> int:
    a = sys.argv[1:]
    ep_dir, tj = a[0], a[1]
    out = a[a.index("--out") + 1] if "--out" in a else None
    skip = tuple(a[a.index("--skip") + 1].split(",")) if "--skip" in a else ()
    os.chdir(ROOT)
    import mark_audit as MA
    from factory import qc
    from factory.config import load_config
    from factory.script import load_episode
    ep = load_episode(ep_dir)
    cfg = load_config(ep.get("config"))
    for sh in ep.get("shorts") or []:
        if sh.get("hook"):
            sh["beats"][0]["on_screen"] = sh["hook"]
            sh["beats"][0]["_hook"] = True
    T = json.load(open(tj))
    beats = {"long": ep["beats"], **{sh["id"]: sh["beats"] for sh in ep.get("shorts") or []}}
    res = {}
    for name, plan in MA.build(ep, cfg, T, True):
        res[name] = qc.run_all(plan, cfg, beats[name], skip)
        print(f"{name}: " + ", ".join(f"{c} {'ok' if not r['fails'] else len(r['fails'])}" for c, r in res[name].items()), flush=True)
    md = "# Release checks " + ep["slug"] + "\n\n" + qc.table(res) + "\n"
    print(md)
    if out:
        Path(out).write_text(md)
        Path(out).with_suffix(".json").write_text(json.dumps(res, indent=1))
    return 1 if qc.failed(res) else 0


if __name__ == "__main__":
    sys.exit(main())
