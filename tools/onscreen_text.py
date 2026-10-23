"""Every on-screen text string of an episode's long video, with its timecode (for proofreading and translation).

python tools/onscreen_text.py episodes/<slug> path/to/timings.json [--md out.md] [--json out.json]

Walks the script beat by beat: plates, stamps, handwritten and typed marks, evidence cards (tag, kicker, headline,
body, highlight), chart and stat labels, typed case-file and mugshot fields, Larry's tab rows, chapter cards, archive
captions, newsreel labels, speech bubbles, subscribe buttons and the end screen, plus the engine's own fixed words
(LARRY'S TAB, EVIDENCE, CASE FILE #, SUSPECT No., NAME, ALIAS, CONFIDENTIAL, NEXT CASE, SUBSCRIBE, ALLEGED ...).
Timecode = beat start (real narration timings) + the word a string is anchored to ("on") or its "at" offset."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from factory.script import load_episode  # noqa: E402

# keys whose string value is shown on screen (per context); lists whose items are shown
TEXT_KEYS = {"text", "label", "caption", "title", "headline", "body", "highlight", "kicker", "source", "name", "alias",
             "tag", "stamp", "tagline", "newsreel", "prefix", "suffix", "quote"}
LIST_KEYS = {"inside", "verdict", "labels", "fees", "value_labels", "lines"}
ANCHOR_KEYS = ("on", "label_on", "open_stamp_on", "click_on")


def _norm(w: str) -> str:
    return "".join(c for c in w.lower() if c.isalnum())


def word_at(words, phrase):
    target = [_norm(x) for x in str(phrase).split() if _norm(x)]
    toks = [_norm(w[0]) for w in words]
    for i in range(len(toks) - len(target) + 1):
        if target and toks[i:i + len(target)] == target:
            return float(words[i][1])
    return None


def tc(t: float) -> str:
    return f"{int(t // 60)}:{t % 60:05.2f}"


def collect(ep: dict, timings: dict, ui=lambda s: s) -> list[dict]:
    T = {b["id"]: b for b in timings["beats"]}
    out = []

    def add(bid, t, kind, s, where):
        s = str(s).strip()
        if s:
            out.append({"t": t, "beat": bid, "kind": kind, "text": s, "where": where})

    for beat in ep["beats"]:
        bid = beat["id"]
        tb = T.get(bid) or {}
        t0 = float(tb.get("start") or 0.0)
        words = [tuple(w) for w in tb.get("words") or []]

        def at_of(d, default=0.0):
            for k in ANCHOR_KEYS:
                if isinstance(d, dict) and d.get(k):
                    wt = word_at(words, d[k])
                    if wt is not None:
                        return t0 + wt
            if isinstance(d, dict) and isinstance(d.get("at"), (int, float)):
                return t0 + float(d["at"])
            return t0 + default

        v = beat["visual"]
        vt = v.get("type")

        CONTAINERS = ("chart", "stat", "doc", "suspect", "casefile", "endscreen", "next")

        def walk(o, path, t_parent, ctx):
            if isinstance(o, dict):
                anchored = any(k in o for k in ANCHOR_KEYS + ("at",)) and path.split(".")[-1] not in CONTAINERS
                t_here = at_of(o, t_parent - t0) if anchored else t_parent
                mt = o.get("type") if isinstance(o.get("type"), str) else None
                if mt in ("write", "stamp", "led", "circle", "underline", "strike", "cross", "check", "arrow"):
                    ctx = {"write": "typed mark" if o.get("font") == "typewriter" else "handwritten mark", "stamp": "stamp mark",
                           "led": "LED panel"}.get(mt, f"{mt} mark")
                for k, x in o.items():
                    if k in ("prompt", "note", "credit", "file", "image_file", "pre", "post", "font", "color", "role", "align",
                             "look", "motion", "mode", "type", "kind", "unit", "mark", "bg", "beat", "say") + ANCHOR_KEYS:
                        if k == "note" and ctx == "chart":
                            add(bid, t_here, "chart note", x, path + ".note")
                        continue
                    if k == "type_on":
                        continue
                    if isinstance(x, str) and k in TEXT_KEYS:
                        if path == "visual" and k == "text" and vt not in ("title",):
                            continue  # kinetic/image "text" never set in practice; titles are chapter cards
                        if ctx == "stat" and k in ("prefix", "suffix"):
                            continue  # shown with the number
                        t_k = at_of(o) if (ctx == "doc" and k == "highlight") else t_here
                        kind = "chapter card" if (vt == "title" and path == "visual") else (ctx if ctx.endswith(("mark", "panel")) else f"{ctx} {k}")
                        add(bid, t_k, kind.strip(), x, f"{path}.{k}")
                    elif isinstance(x, list) and k in LIST_KEYS:
                        for i, it in enumerate(x):
                            if isinstance(it, str):
                                add(bid, t_here, f"{ctx} {k}[{i}]".strip(), it, f"{path}.{k}[{i}]")
                    elif isinstance(x, (dict, list)):
                        walk(x, f"{path}.{k}", t_here, k if k in ("chart", "stat", "doc", "suspect", "casefile", "endscreen", "next",
                                                                  "closeup", "bubble", "stamp") else ctx)
            elif isinstance(o, list):
                for i, it in enumerate(o):
                    walk(it, f"{path}[{i}]", t_parent, ctx)

        walk(v, "visual", t0, vt)
        if vt == "title":
            pass
        if vt == "kinetic":
            add(bid, t0, "kinetic (narration words typed on screen)", v.get("text") or beat["text"], "visual.kinetic")
        if vt == "stat":
            st = v["stat"]
            val = f"{st.get('prefix', '')}{st.get('value')}{st.get('suffix', '')}"
            add(bid, t0, "stat number", val, "visual.stat.value")
        if vt == "chart":
            ch = v["chart"]
            if not isinstance(ch.get("value_labels"), list):
                for lab, val in zip(ch.get("labels", []), ch.get("values", [])):
                    add(bid, t0, "chart value", f"{val} {ch.get('unit', '')} ({lab})", "visual.chart.values")
        if vt == "doc":
            add(bid, t0, "engine", ui("EVIDENCE"), "evidence tag word")
        if vt == "mugshot":
            sp = v.get("suspect") or {}
            add(bid, t0, "engine", ui("SUSPECT No.") + f" {sp.get('number', 1)}", "mugshot plate")
            for lab in ("NAME", "ALIAS"):
                add(bid, t0, "engine", ui(lab), "mugshot card field label")
        if vt == "casefile":
            cf = v["casefile"]
            add(bid, t0, "engine", ui("CASE FILE #") + str(cf.get("number", "")), "case file label")
            add(bid, t0, "engine", ui("CONFIDENTIAL"), "case file cover")
            if cf.get("open_stamp_on"):
                add(bid, at_of({"on": cf["open_stamp_on"]}), "engine stamp", ui("OPEN"), "case file stamp")
        if vt == "endscreen":
            es = v["endscreen"]
            nx = es.get("next") or {}
            add(bid, t0, "engine", ui("CASE FILE #") + str(es.get("number", "")), "end screen folder label")
            add(bid, t0, "engine", ui("CONFIDENTIAL"), "end screen folder")
            add(bid, t0, "engine", ui("NEXT: CASE FILE #") + str(nx.get("number", "")), "next-case sheet header")
            add(bid, t0, "engine", ui("NEXT CASE  >"), "end screen zone label")
            add(bid, t0, "engine", ui("SUBSCRIBE") + " / " + ui("SUBSCRIBED"), "subscribe button")
        if vt == "clip" and v.get("newsreel") is True:
            add(bid, t0, "engine", ui("Archive film"), "newsreel label")
        # beat-level overlays
        if beat.get("label"):
            t_l = at_of({"on": beat.get("label_on")}) if beat.get("label_on") else t0
            add(bid, t_l, "plate", beat["label"], "beat.label")
        if beat.get("alleged"):
            add(bid, t0, "engine plate", ui("ALLEGED"), "beat.alleged")
        if isinstance(beat.get("stamp"), dict):
            add(bid, at_of(beat["stamp"], 0.3), "stamp", beat["stamp"].get("text", ""), "beat.stamp")
        if isinstance(beat.get("bubble"), dict):
            add(bid, at_of(beat["bubble"]), "speech bubble", beat["bubble"].get("text", ""), "beat.bubble")
        for i, ins in enumerate(beat.get("inserts") or []):
            if ins.get("caption"):
                add(bid, at_of(ins), "insert caption", ins["caption"], f"beat.inserts[{i}]")
        if beat.get("cta"):
            add(bid, at_of(beat["cta"]), "engine button", ui("SUBSCRIBE") + " / " + ui("SUBSCRIBED"), "beat.cta")
        for i, row in enumerate(beat.get("ledger") or []):
            add(bid, at_of(row, 0.5), "Larry's tab row", f"{row.get('label', '')}  {row.get('amount', '')}".strip(), f"beat.ledger[{i}]")
    for b in ep["beats"]:
        nx = ((b.get("visual") or {}).get("endscreen") or {}).get("next") or {}
        if nx.get("image_file"):
            t0 = float((T.get(b["id"]) or {}).get("start") or 0.0)
            out.append({"t": t0, "beat": b["id"], "kind": "picture (code-drawn)", "where": nx["image_file"],
                        "text": f"words drawn inside {nx['image_file']} (next-case sketch)"})
    first_tab = min((r["t"] for r in out if r["kind"] == "Larry's tab row"), default=None)
    if first_tab is not None:
        out.append({"t": first_tab, "beat": "-", "kind": "engine", "text": ui("LARRY'S TAB"), "where": "Larry's tab title"})
    out.sort(key=lambda r: (r["t"], r["beat"]))
    return out


def main(argv):
    ep_dir, tj = argv[0], argv[1]
    ep = load_episode(ep_dir)
    timings = json.load(open(tj))
    from factory.i18n import ui
    rows = collect(ep, timings, ui)
    md = ["| time | beat | what | on-screen text |", "|---|---|---|---|"]
    for r in rows:
        md.append(f"| {tc(r['t'])} | {r['beat']} | {r['kind']} | {r['text'].replace('|', '/')} |")
    if "--md" in argv:
        Path(argv[argv.index("--md") + 1]).write_text("\n".join(md) + "\n", encoding="utf-8")
    if "--json" in argv:
        Path(argv[argv.index("--json") + 1]).write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    if "--md" not in argv and "--json" not in argv:
        print("\n".join(md))
    print(f"{len(rows)} strings", file=sys.stderr)


if __name__ == "__main__":
    os.environ.setdefault("OPENROUTER_API_KEY", "audit-offline")
    main(sys.argv[1:])
