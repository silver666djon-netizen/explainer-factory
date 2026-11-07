"""DOM sampling for the Ep.4 v2 release checks: renders the real V2 composition (remotion mocked, tools/harness) in Chromium
at chosen times and records where the drawing hand is, where the faces of the picture are, every mark/tag box and every text
we want read (with its on-screen cap height and its contrast against what is behind it). v2_qc.py runs the checks on it.

python tools/v2_dom_qc.py <public dir: v2_<kind>.json, v2/, hands/, fonts/> <pv dir: plan.json> [esbuild binary]
-> <pv>/dom.json"""
from __future__ import annotations

import asyncio
import functools
import http.server
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
H = ROOT / "tools" / "harness"
CAP = {"Anton-Regular": 0.859, "ArchivoBlack-Regular": 0.688, "SpecialElite-Regular": 0.689, "PermanentMarker-Regular": 0.74,
       "PT-Serif-Web-Regular": 0.7}


def bundle(work: Path, esbuild: str) -> None:
    nm = ROOT / "pilot" / "remotion" / "node_modules"
    alias = [f"--alias:remotion={H / 'mock' / 'remotion.js'}", f"--alias:@remotion/layout-utils={H / 'mock' / 'layout.js'}",
             f"--alias:@remotion/noise={H / 'mock' / 'noise.js'}", f"--alias:@remotion/paths={H / 'mock' / 'paths.js'}",
             f"--alias:@remotion/rough-notation={H / 'mock' / 'rough.js'}"]
    env = dict(os.environ, NODE_PATH=f"{nm}:{os.environ.get('NODE_PATH', '')}")
    subprocess.run([esbuild, str(H / "entry.jsx"), "--bundle", f"--outfile={work / 'out.js'}", *alias, "--loader:.tsx=tsx",
                    "--jsx=automatic", "--log-level=warning", f"--resolve-extensions=.tsx,.ts,.jsx,.js"], check=True, env=env, cwd=str(H))
    shutil.copy(H / "index.html", work / "index.html")


def serve(work: Path) -> tuple[http.server.ThreadingHTTPServer, int]:
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a, **k):  # noqa: D102
            pass
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(work)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


def _rgb(s: str) -> tuple[int, int, int]:
    s = s.strip()
    if s.startswith("#"):
        return int(s[1:3], 16), int(s[3:5], 16), int(s[5:7], 16)
    v = [float(x) for x in s[s.index("(") + 1:s.index(")")].split(",")[:3]]
    return int(v[0]), int(v[1]), int(v[2])


def _lum(c) -> float:
    c = np.asarray(c, dtype=float) / 255.0
    c = np.where(c <= 0.03928, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return float(0.2126 * c[..., 0] + 0.7152 * c[..., 1] + 0.0722 * c[..., 2]) if c.ndim == 1 else 0.2126 * c[..., 0] + 0.7152 * c[..., 1] + 0.0722 * c[..., 2]


def contrast(img: np.ndarray, box, col) -> float | None:
    """WCAG contrast of the text colour against what is behind the text (the pixels in its box that are not text-coloured)."""
    h, w = img.shape[:2]
    x0, y0, x1, y1 = [int(round(v)) for v in box]
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(w, x1), min(h, y1)
    if x1 - x0 < 2 or y1 - y0 < 2:
        return None
    px = img[y0:y1, x0:x1, :3].astype(float)
    tc = np.array(col, dtype=float)
    ink = np.abs(px - tc).max(2) <= 70

    def grow(m, n):
        for _ in range(n):
            g = m.copy()
            g[1:] |= m[:-1]; g[:-1] |= m[1:]; g[:, 1:] |= m[:, :-1]; g[:, :-1] |= m[:, 1:]
            m = g
        return m
    ring = grow(ink, 6) & ~grow(ink, 3)  # what is right behind the letters (not the whole box)
    if ring.sum() < 10:
        return None
    bg = np.median(px[ring], axis=0)
    a, b = _lum(tc), _lum(bg)
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)


def times_for(data: dict) -> list[tuple[float, bool]]:
    """(t, screenshot?) — one settled frame per shot (0.3 s before its cut) and every 0.1 s while a hand is on screen."""
    out = []
    trans = data.get("transitions") or []
    # an iris that starts before the cut (it closes on the outgoing shot): that shot settles before the iris begins
    early = {x["shot"]: x["pre"] / data["fps"] for x in trans if x.get("pre") and x["type"] != "folder"}
    ids = [s["id"] for s in data["shots"]]
    for i, s in enumerate(data["shots"]):
        nxt = ids[i + 1] if i + 1 < len(ids) else None
        end = s["end"] - early.get(nxt, 0.0)
        out.append((round(max(s["start"] + 0.05, end - 0.3), 3), True))
        spans = list(s.get("_ink", []))
        for o in s.get("overs", []):  # stamp hands
            at = o.get("at_") if o.get("t") == "stamp" else o.get("stamp_") if o.get("t") == "namecard" else None
            if at is not None:
                spans.append((s["start"] + at, s["start"] + at + 0.2))
        for a, b in spans:
            t = a - 0.4
            while t <= b + 0.45:
                if s["start"] <= t < s["end"]:
                    out.append((round(t, 2), False))
                t += 0.1
    for x in trans:  # the case folder at its held moment: the act title on it is text we want read (2.8 %, contrast, 6 % margin)
        if x["type"] == "folder":
            out.append((round(x["at"] - x["pre"] / data["fps"] + x["n"] / 2 / data["fps"], 3), True))
    return sorted(set(out))


async def sample(port: int, data: dict, name: str) -> list[dict]:
    from PIL import Image
    from playwright.async_api import async_playwright
    res = []
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": data["W"], "height": data["H"]})
        errs: list[str] = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.goto(f"http://127.0.0.1:{port}/index.html")
        await pg.evaluate("(d) => { window.__data = d; }", data)
        for t, shot in times_for(data):
            await pg.evaluate("([f]) => window.renderAt(window.__data, f)", [int(round(t * data["fps"]))])
            got = await pg.evaluate("() => window.collect()")
            cur = next((s for s in data["shots"] if s["start"] <= t < s["end"]), data["shots"][-1])
            rec = {"t": t, "shot": cur["id"], "shot_t": round(t - cur["start"], 3), **got}
            if shot:
                img = np.asarray(Image.open(io.BytesIO(await pg.screenshot())).convert("RGB"))
                for r in rec["reads"]:
                    fam = r["fam"].replace('"', "").replace("'", "").split(",")[0].strip()
                    r["cap"] = r["fs"] * r["scale"] * CAP.get(fam, 0.7)
                    try:
                        r["contrast"] = contrast(img, r["box"], _rgb(r["col"]))
                    except Exception:  # noqa: BLE001
                        r["contrast"] = None
            else:
                rec.pop("reads", None)
                rec.pop("marks", None)
                rec.pop("propReads", None)
            rec["shotpic"] = shot
            res.append(rec)
        await b.close()
        if errs:
            print(f"{name}: page errors: {errs[:3]}", flush=True)
    return res


def main(pub: str, pvd: str, esbuild: str = "") -> int:
    pub_p, pv = Path(pub).resolve(), Path(pvd)
    esbuild = str(Path(esbuild).resolve()) if esbuild else str(ROOT / "pilot" / "remotion" / "node_modules" / ".bin" / "esbuild")
    plan = json.loads((pv / "plan.json").read_text())
    work = Path(tempfile.mkdtemp(prefix="v2dom"))
    bundle(work, esbuild)
    (work / "pub").symlink_to(pub_p)
    srv, port = serve(work)
    out = {}
    try:
        for kind in plan:
            data = json.loads((pub_p / f"v2_{kind}.json").read_text())
            out[kind] = {"W": data["W"], "H": data["H"], "band": data.get("band"), "samples": asyncio.run(sample(port, data, kind))}
            print(kind, len(out[kind]["samples"]), "samples", flush=True)
    finally:
        srv.shutdown()
    (pv / "dom.json").write_text(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
