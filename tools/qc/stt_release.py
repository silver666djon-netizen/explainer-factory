"""STT diff of a finished release (Klot r89 #7, line by line since r90): the narration of every published video is
transcribed beat by beat and diffed against the script. Two steps, so the CI job needs no picture cache:

  spans   (local, needs the image cache): python3 tools/qc/stt_release.py spans episodes/<slug> <timings.json> <out.json>
          -> every video's narration lines: [start, end, beat id, script text] from the real render plan
  check   (CI, needs faster-whisper):     python3 tools/qc/stt_release.py check episodes/<slug> <spans.json> <dir with
          cs_*_<video>.mp4> <out.md>   -> exit 1 on any difference not in the episode's stt_known

The check reads the published file's own audio (narration + music + effects), so it hears what a viewer hears."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("OPENROUTER_API_KEY", "audit-offline")


def spans(ep_dir: str, tj: str, out: str) -> int:
    import mark_audit as MA
    from factory.config import load_config
    from factory.script import load_episode
    import factory.render as R
    _bp = R.build_plan

    def big(beats, vb, images, cfg_, size, kind, lookup, *r):
        return _bp(beats, vb, images, cfg_, (1920, 1080) if kind == "long" else (1080, 1920), kind, lookup, *r)
    MA.build_plan = big
    if os.environ.get("STT_REAL_VOICE"):  # CI: lines missing from timings.json (Short-only lines) get the real voice,
        from factory.tts import make_voice  # so their spans are the rendered ones, not estimates
        MA.make_voice = lambda cfg, offline, extra=None: make_voice(cfg, False, extra)
        os.environ.setdefault("MARK_AUDIT_ALLOW_PLACEHOLDERS", "1")
    os.chdir(ROOT)
    ep = load_episode(ep_dir)
    cfg = load_config(ep.get("config"))
    for sh in ep.get("shorts") or []:  # as the build does: the hook card is the Short's first beat on screen
        if sh.get("hook"):
            sh["beats"][0]["on_screen"] = sh["hook"]
            sh["beats"][0]["_hook"] = True
    beats = {"long": ep["beats"], **{sh["id"]: sh["beats"] for sh in ep.get("shorts") or []}}
    res = {}
    for name, plan in MA.build(ep, cfg, json.load(open(tj)), True):
        texts = {str(b.get("id", "")): str(b.get("text", "")) for b in beats[name]}
        res[name] = [[round(a, 3), round(b, 3), i, texts.get(i, "")] for a, b, i in plan.timeline.voice_lines]
    Path(out).write_text(json.dumps(res, indent=1))
    print({k: len(v) for k, v in res.items()})
    return 0


def _audio(mp4: Path):
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(mp4), "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)


def check(ep_dir: str, sj: str, rel: str, out: str) -> int:
    from factory import sttdiff
    from factory.script import load_episode
    ep = load_episode(ep_dir)
    known = [(k["script"], k["heard"]) for k in ep.get("stt_known") or []]
    tc = lambda t: f"{int(t // 60)}:{t % 60:04.1f}"
    S = json.load(open(sj))
    md = [f"# STT diff (line by line, published audio) {ep['slug']}", "",
          "| video | lines | differences | result |", "|---|---|---|---|"]
    detail, bad, js = [], False, {}
    for name, lines in S.items():
        f = next(iter(sorted(Path(rel).glob(f"cs_*_{name}.mp4"))), None)
        if f is None:
            md.append(f"| {name} | - | file missing | FAIL |")
            bad = True
            continue
        a = _audio(f)
        texts = {i: t for _, _, i, t in lines}
        fails, notes = sttdiff.check_lines(a, 16000, [(x, y, i) for x, y, i, _ in lines], texts, known, tc)
        js[name] = {"fails": fails, "heard": notes}
        bad |= bool(fails)
        md.append(f"| {name} | {sum(1 for l in lines if l[3].strip())} | {len(fails)} | {'FAIL' if fails else 'PASS'} |")
        detail += [f"\n## {name}\n"] + [f"- **{x}**" for x in fails] + ["", "<details><summary>heard, line by line</summary>", ""] \
            + [f"- {n}" for n in notes] + ["", "</details>"]
    md += ["", "Waived (stt_known, each verified against the voice's phonemes):", ""] + \
          [f"- '{k['script']}' heard '{k['heard']}': {k.get('why', '')}" for k in ep.get("stt_known") or []]
    Path(out).write_text("\n".join(md + detail) + "\n")
    Path(out).with_suffix(".json").write_text(json.dumps(js, indent=1))
    print("\n".join(md))
    return 1 if bad else 0


if __name__ == "__main__":
    a = sys.argv[1:]
    sys.exit(spans(*a[1:4]) if a[0] == "spans" else check(*a[1:5]))
