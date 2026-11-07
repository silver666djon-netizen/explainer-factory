"""Tooling v2 test render (Klot, item 14), run on GitHub Actions (ubuntu, no GPU):

  python tools/tooling_test.py prep   <audio dir> <out dir>   assets: LoC photo (archive fetcher), LottieFiles stamp,
                                                              HyperFrames CLI overlay (transparent WebM), the Lottie hit
  python tools/tooling_test.py render <out dir>               per-element renders + checks, the full 8 s render, the mix
  python tools/tooling_test.py report <out dir> <probe json>  tooling_test.md, the contact sheet, the asset rows

Every Remotion call uses --gl=swangle --preferred-effect-backend=webgl2 (software GL: the runner has no GPU).
Each element is rendered alone (ToolingTest only=<element>) and timed, then checked against its own absence
(fx off / fallback font / the static end state), so "renders correctly without a GPU" is measured, not assumed."""
from __future__ import annotations

import io
import json
import os
import re
import shutil
import subprocess
import sys
import time
import zipfile
from datetime import date
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
RM = ROOT / "pilot" / "remotion"
PUB = RM / "public" / "tooling"
sys.path.insert(0, str(ROOT / "tools"))
GL = ["--gl=swangle", "--preferred-effect-backend=webgl2"]
LOC_ID = "2017745251"  # Box office, Loew's Capitol, Washington, D.C., 1939 (LoC, no known restrictions)
LOTTIE = {"url": "https://assets-v2.lottiefiles.com/a/35c0e3d5-a81c-4361-961b-d5ef7a71429e/A4svAPaEV9.lottie",
          "page": "https://lottiefiles.com/free-animation/approved-stamp-A4svAPaEV9", "title": "Approved Stamp", "author": "Anu Menon",
          "licence": "Lottie Simple License (free for commercial use; attribution not required)",
          "licence_url": "https://lottiefiles.com/page/license"}
HF_CLI = "hyperframes@0.9.19"  # the npm name of the CLI (@hyperframes/cli is the monorepo package name, not published)
INK = (168, 35, 28)
ENV = dict(os.environ, HYPERFRAMES_NO_TELEMETRY="1", DO_NOT_TRACK="1", REMOTION_DISABLE_TELEMETRY="1")


def sh(cmd: list[str], cwd: Path | None = None, log: Path | None = None, timeout: int = 1800) -> tuple[int, float, str]:
    t0 = time.time()
    r = subprocess.run(cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True, env=ENV, timeout=timeout)
    out = (r.stdout or "") + (r.stderr or "")
    if log:
        with open(log, "a", encoding="utf-8") as fh:
            fh.write(f"\n$ {' '.join(cmd)}\n{out[-20000:]}\n")
    return r.returncode, round(time.time() - t0, 1), out


ENTRY = "src/index.ts"


def bundle(log: Path) -> None:
    """Bundle once (every still/render then reuses it instead of re-bundling)."""
    global ENTRY
    code, sec, out = sh(["npx", "remotion", "bundle", "src/index.ts", "--out-dir", "/tmp/rbundle"], cwd=RM, log=log)
    if code == 0 and Path("/tmp/rbundle/index.html").exists():
        ENTRY = "/tmp/rbundle"
    print(f"bundle: {'ok' if ENTRY != 'src/index.ts' else 'failed, using src/index.ts'} ({sec} s)", flush=True)


def remotion(args: list[str], out: Path, log: Path) -> tuple[int, float, str]:
    args = [ENTRY if a == "src/index.ts" else a for a in args]
    return sh(["npx", "remotion", *args, *GL, "--log=error"], cwd=RM, log=log)


# ------------------------------------------------------------------ prep
def prep(audio_dir: str, outdir: str) -> int:
    O = Path(outdir).resolve()
    O.mkdir(parents=True, exist_ok=True)
    PUB.mkdir(parents=True, exist_ok=True)
    log = O / "prep.log"
    rep: dict = {}
    import archives as A
    # 1. the photo, through the new LoC fetcher (licence gate + sidecar with the item date)
    t0 = time.time()
    try:
        m = None
        A.MAX_429 = 0  # loc.gov keeps answering 429 to GitHub's runners: one try, then the session-fetched copy
        for wait in (0,):
            time.sleep(wait)
            try:
                m = A.fetch("loc", LOC_ID, str(PUB / "photo.jpg"), register=False)
                break
            except Exception as e:  # noqa: BLE001
                if "429" not in str(e) or wait == 0:
                    raise
        rep["photo"] = {"ok": True, "seconds": round(time.time() - t0, 1), "title": m["title"], "date": m["item_date"], "licence": m["licence"]}
    except Exception as e:  # noqa: BLE001
        # loc.gov rate-limits GitHub's runners (429): use the same item fetched by the same tool from the review session
        keep = ROOT / "assets/tooling/loc_2017745251_loews_1939.jpg"
        if keep.exists():
            shutil.copy(keep, PUB / "photo.jpg")
            shutil.copy(str(keep) + ".license.json", PUB / "photo.jpg.license.json")
            m = json.loads((PUB / "photo.jpg.license.json").read_text())
            rep["photo"] = {"ok": True, "via": "tools/archives.py run outside Actions (loc.gov answered 429 here)", "actions_error": str(e)[:160],
                            "title": m["title"], "date": m["item_date"], "licence": m["licence"]}
        else:
            rep["photo"] = {"ok": False, "error": str(e)[:300]}
            Image.new("RGB", (1200, 840), (120, 110, 100)).save(PUB / "photo.jpg")
    # 2. the Lottie stamp (.lottie = zip with animations/*.json)
    try:
        data = A._get(LOTTIE["url"], binary=True)
        z = zipfile.ZipFile(io.BytesIO(data))
        name = next(n for n in z.namelist() if n.startswith("animations/") and n.endswith(".json"))
        anim = json.loads(z.read(name))
        (PUB / "stamp.json").write_text(json.dumps(anim))
        meta = {**LOTTIE, "file": "stamp.json", "fetched": date.today().isoformat(), "frames": anim.get("op", 0) - anim.get("ip", 0),
                "fps": anim.get("fr"), "w": anim.get("w"), "h": anim.get("h"), "has_text_layers": any(l.get("ty") == 5 for l in anim.get("layers", []))}
        (PUB / "stamp.json.license.json").write_text(json.dumps(meta, indent=1))
        rep["lottie"] = {"ok": True, **{k: meta[k] for k in ("frames", "fps", "w", "h", "has_text_layers")}}
    except Exception as e:  # noqa: BLE001
        rep["lottie"] = {"ok": False, "error": str(e)[:300]}
    # 3. the HyperFrames overlay: hw-scribble-transition in our red, rendered by the CLI as a transparent WebM
    hf = Path("/tmp/hf/scribble")
    shutil.rmtree(hf, ignore_errors=True)
    hf.mkdir(parents=True)
    html = (ROOT / "vendor/hyperframes/registry/blocks/hw-scribble-transition/hw-scribble-transition.html").read_text()
    html = html.replace("color: null, // css color", "color: \"#a8231c\", // css color (CoinSense red ink)")
    # Klot (frame review): full red cover <= 0.25 s. Upstream clears from 1.42 s (cover ~0.55 s); ours from 1.00 s (1.10 s measured 0.33 s)
    for a, b in (("}, 1.42);", "}, 1.00);"), ("1.42 + 0.035 * i", "1.00 + 0.035 * i"), ("}, 2.17);", "}, 1.75);")):
        assert html.count(a) == 1, a
        html = html.replace(a, b)
    (hf / "index.html").write_text(html)
    global HF_CLI
    code, sec, out = sh(["npx", "-y", HF_CLI, "--version"], log=log, timeout=600)
    if code:  # that exact version not published: take the latest and say so
        HF_CLI = "hyperframes@latest"
        code, sec, out = sh(["npx", "-y", HF_CLI, "--version"], log=log, timeout=600)
    rep["hyperframes_cli"] = {"package": HF_CLI, "exit": code, "install_seconds": sec, "out": [l for l in out.strip().splitlines() if l.strip()][-8:]}
    if code:  # print the reason (npm / engine / CLI) into the job log
        print("hyperframes CLI --version failed:\n" + out[-3000:], flush=True)
    sh(["npx", "-y", HF_CLI, "telemetry", "disable"], log=log, timeout=120)
    code, sec, out = sh(["npx", "-y", HF_CLI, "render", str(hf), "--format", "webm", "--fps", "30", "-o", str(PUB / "overlay.webm")], log=log, timeout=1200)
    rep["overlay"] = {"ok": code == 0 and (PUB / "overlay.webm").exists(), "seconds": sec, "exit": code,
                      "summary": " | ".join(l.strip() for l in out.splitlines() if re.search(r"capture|gpu|Render|encode|✗|Fix:|rror", l))[-900:]}
    if not rep["overlay"]["ok"]:
        print("hyperframes render failed:\n" + out[-4000:], flush=True)
    if rep["overlay"]["ok"]:
        rep["overlay"]["alpha"] = webm_alpha(PUB / "overlay.webm")
    # 4. audio from the ElevenLabs test (draft tooling-v2)
    A_ = Path(audio_dir)
    for f in sorted(A_.glob("*.mp3")):
        shutil.copy(f, PUB / f.name)
        if Path(str(f) + ".json").exists():
            shutil.copy(str(f) + ".json", PUB / (f.name + ".json"))
    rep["audio"] = {f: (PUB / f).exists() for f in ("theme_noir_jazz_20s.mp3", "sfx_rubber_stamp.mp3")}
    cfg = {"lottie": "tooling/stamp.json" if rep["lottie"]["ok"] else None, "flap": {"from": "$30", "to": "$48", "startAt": 1.3}}  # flips at 4.3 s, after the scribble has cleared
    (PUB / "test.json").write_text(json.dumps(cfg))
    # 5. Lottie support (LottieProbe composition; the Lottie stamp itself was refused for episodes: off-style)
    bundle(log)
    if rep["lottie"]["ok"]:
        fr = O / "lottie_frames"
        code, sec, out = remotion(["render", "src/index.ts", "LottieProbe", str(fr), "--sequence", "--image-format=png"], fr, log)
        cov = []
        for p in sorted(fr.glob("*.png")):
            a = np.asarray(Image.open(p).convert("RGBA"))[..., 3] > 40
            cov.append(float(a.mean()))
        if cov:
            fin = cov[-1]
            # the stamp has landed at the first frame after which its coverage stays within 3 % of the frame of the final
            # coverage (a stamp scales / drops in, then sits still): that frame is the impact, where the SFX goes
            slam = next((i for i in range(len(cov)) if all(abs(c - fin) <= 0.03 for c in cov[i:])), 0)
            rep["lottie"].update({"render_seconds": sec, "hit_frame": slam, "coverage_final": round(fin, 3),
                                  "coverage": [round(c, 3) for c in cov]})
            strip = [Image.open(p).convert("RGBA").resize((120, 120)) for p in sorted(fr.glob("*.png"))[::3]]
            S = Image.new("RGBA", (120 * len(strip), 120), (239, 228, 203, 255))
            for k, im in enumerate(strip):
                S.alpha_composite(im, (120 * k, 0))
            S.convert("RGB").save(O / "lottie_strip.png")
            (PUB / "test.json").write_text(json.dumps(cfg))
    (O / "prep.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False))
    print(json.dumps(rep, indent=1, ensure_ascii=False))
    return 0


def webm_alpha(path: Path) -> dict:
    """Alpha coverage of a VP9 WebM over time (decoded with libvpx so the alpha plane is kept)."""
    tmp = Path("/tmp/hf/alpha")
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    subprocess.run(["ffmpeg", "-v", "error", "-c:v", "libvpx-vp9", "-i", str(path), "-vf", "scale=480:-1,format=rgba", str(tmp / "%03d.png")], check=False)
    cov = [float((np.asarray(Image.open(p))[..., 3] > 128).mean()) for p in sorted(tmp.glob("*.png"))]
    if not cov:
        return {"ok": False, "why": "no frames decoded"}
    full = [i for i, c in enumerate(cov) if c >= 0.995]  # frames (30 fps) where the red covers the whole frame
    full_s = round(len(full) / 30.0, 3)
    return {"ok": cov[0] < 0.02 and max(cov) > 0.97 and cov[-1] < 0.02 and 0 < full_s <= 0.25, "first": round(cov[0], 3), "max": round(max(cov), 3),
            "last": round(cov[-1], 3), "frames": len(cov), "full_cover_frames": [full[0], full[-1]] if full else None, "full_cover_s": full_s,
            "coverage_every3": [round(c, 2) for c in cov[::3]]}


# ------------------------------------------------------------------ render + checks
def still(O: Path, name: str, frame: int, props: dict, log: Path, comp: str = "ToolingTest") -> np.ndarray | None:
    p = O / "stills" / f"{name}.png"
    p.parent.mkdir(exist_ok=True)
    code, sec, out = remotion(["still", "src/index.ts", comp, str(p), f"--frame={frame}", f"--props={json.dumps(props)}", "--image-format=png"], p, log)
    if code or not p.exists():
        return None
    return np.asarray(Image.open(p).convert("RGBA")).astype(np.float32)


def mad(a, b, box=None) -> float:
    if a is None or b is None:
        return -1.0
    if box:
        x0, y0, x1, y1 = box
        a, b = a[y0:y1, x0:x1], b[y0:y1, x0:x1]
    return float(np.abs(a[..., :3] - b[..., :3]).mean())


def red(a, box) -> float:
    x0, y0, x1, y1 = box
    r = a[y0:y1, x0:x1]
    return float(((r[..., 0] > 120) & (r[..., 0] > r[..., 1] + 60) & (r[..., 0] > r[..., 2] + 60)).mean())


def hf_energy(a, box) -> float:
    """High-frequency energy (halftone dots) in a box: mean |laplacian| of the luminance."""
    x0, y0, x1, y1 = box
    g = a[y0:y1, x0:x1, :3].mean(axis=2)
    lap = np.abs(4 * g[1:-1, 1:-1] - g[:-2, 1:-1] - g[2:, 1:-1] - g[1:-1, :-2] - g[1:-1, 2:])
    return float(lap.mean())


def render(outdir: str) -> int:
    O = Path(outdir).resolve()
    O.mkdir(parents=True, exist_ok=True)
    log = O / "render.log"
    cfg = json.loads((PUB / "test.json").read_text())
    res: dict = {}
    bundle(log)
    dri = Path("/dev/dri").exists()
    vga = subprocess.run("lspci 2>/dev/null | grep -iE 'vga|3d|display' || true", shell=True, capture_output=True, text=True).stdout.strip()
    nv = shutil.which("nvidia-smi") is not None
    res["gpu"] = f"/dev/dri: {'present' if dri else 'absent'}; nvidia-smi: {'present' if nv else 'absent'}; display adapters: {vga or 'none'}"
    # per element: render it alone over its active frames, time it, check it
    spans = {"effects": (0, 89), "title": (0, 89), "circle": (20, 80), "overlay": (55, 130), "flap": (90, 179), "wipe": (155, 185), "stamp": (162, 239)}
    for el, (a, b) in spans.items():
        code, sec, out = remotion(["render", "src/index.ts", "ToolingTest", str(O / f"el_{el}.mp4"), f"--props={json.dumps({'only': el})}",
                                   f"--frames={a}-{b}", "--muted", "--concurrency=4"], O, log)
        err = [l for l in out.splitlines() if re.search(r"(?i)error|fail|falling back|not supported|webgpu|webgl", l)][:6]
        res[el] = {"render_ok": code == 0, "seconds": sec, "frames": b - a + 1, "log": err}
    # checks (stills)
    S = lambda n, f, p, c="ToolingTest": still(O, n, f, p, log, c)  # noqa: E731
    PHOTO, TAG = (150, 240, 990, 820), (1180, 500, 1800, 860)
    try:
        on, off = S("effects_on", 40, {"only": "effects"}), S("effects_off", 40, {"only": "effects", "fx": False})
        bg = (1100, 900, 1880, 1060)
        res["effects"]["check"] = {"halftone_hf_on": round(hf_energy(on, PHOTO), 2), "halftone_hf_off": round(hf_energy(off, PHOTO), 2),
                                   "paper_mad_vs_plain": round(mad(on, off, bg), 2),
                                   "speckle_dark_px": round(float((on[900:1060, 1100:1880, :3].mean(axis=2) < 90).mean()), 4) if on is not None else -1}
        c = res["effects"]["check"]
        # Klot (frame review): the photo must stay readable. The halftone print against the plain photo, 8x smaller (what the
        # eye reads as the picture): structure (correlation), contrast (std ratio) and brightness (mean shift)
        def small(a):
            x0, y0, x1, y1 = PHOTO
            g = a[y0:y1, x0:x1, :3].mean(axis=2)
            h, w = g.shape[0] // 8, g.shape[1] // 8
            return g[: h * 8, : w * 8].reshape(h, 8, w, 8).mean(axis=(1, 3))
        a_, b_ = small(on), small(off)
        c.update({"readable_corr": round(float(np.corrcoef(a_.ravel(), b_.ravel())[0, 1]), 3), "contrast_ratio": round(float(a_.std() / max(b_.std(), 1e-6)), 3),
                  "mean_shift": round(float(a_.mean() - b_.mean()), 1)})
        res["effects"]["ok"] = (res["effects"]["render_ok"] and c["halftone_hf_on"] > 1.2 * max(c["halftone_hf_off"], 0.5) and c["paper_mad_vs_plain"] > 2
                                and c["speckle_dark_px"] > 0.0005 and c["readable_corr"] >= 0.95 and c["contrast_ratio"] >= 0.85 and abs(c["mean_shift"]) <= 25)
    except Exception as e:  # noqa: BLE001
        res["effects"]["ok"], res["effects"]["check"] = False, str(e)
    try:
        w, fb = S("title_web", 40, {"only": "title"}), S("title_fallback", 40, {"only": "title", "font": "fallback"})
        d = mad(w, fb, (100, 50, 1100, 190))
        res["title"]["check"] = {"special_elite_vs_monospace_mad": round(d, 2)}
        res["title"]["ok"] = res["title"]["render_ok"] and d > 3
    except Exception as e:  # noqa: BLE001
        res["title"]["ok"], res["title"]["check"] = False, str(e)
    try:
        b0, b1 = S("circle_before", 25, {"only": "circle"}), S("circle_after", 70, {"only": "circle"})
        res["circle"]["check"] = {"red_before": round(red(b0, TAG), 4), "red_after": round(red(b1, TAG), 4)}
        res["circle"]["ok"] = res["circle"]["render_ok"] and red(b1, TAG) > 0.01 and red(b0, TAG) < 0.002
    except Exception as e:  # noqa: BLE001
        res["circle"]["ok"], res["circle"]["check"] = False, str(e)
    try:
        full = (0, 0, 1920, 1080)
        o0, o2 = S("overlay_before", 55, {"only": "overlay"}), S("overlay_after", 130, {"only": "overlay"})
        cut = [S(f"overlay_cut_{f}", f, {"only": "overlay"}) for f in (89, 90)]  # the A -> B hard cut is at frame 90
        al = json.loads((O / "prep.json").read_text()).get("overlay", {}).get("alpha", {}) if (O / "prep.json").exists() else {}
        res["overlay"]["check"] = {"red_before": round(red(o0, full), 3), "red_at_cut": [round(red(x, full), 3) for x in cut], "red_after": round(red(o2, full), 3),
                                   "full_cover_s": al.get("full_cover_s"), "full_cover_frames_local": al.get("full_cover_frames")}
        c = res["overlay"]["check"]
        res["overlay"]["ok"] = (res["overlay"]["render_ok"] and min(c["red_at_cut"]) > 0.98 and c["red_before"] < 0.01 and c["red_after"] < 0.01
                                and c["full_cover_s"] is not None and 0 < c["full_cover_s"] <= 0.25)
    except Exception as e:  # noqa: BLE001
        res["overlay"]["ok"], res["overlay"]["check"] = False, str(e)
    try:
        f = cfg["flap"]
        s30 = S("flap_static30", 120, {"only": "flap", "flap": {"from": f["from"], "to": f["from"], "startAt": 0}})
        s48 = S("flap_static48", 120, {"only": "flap", "flap": {"from": f["to"], "to": f["to"], "startAt": 0}})
        # Klot (frame review): the board never rests on a number that is not $30 or $48 (no intermediate value held > 2 frames).
        # Every frame of B (90-161), against the two static boards: a run of >= 3 identical frames must be $30 or $48.
        fd = O / "flap_frames"
        shutil.rmtree(fd, ignore_errors=True)
        fd.mkdir()
        remotion(["render", "src/index.ts", "ToolingTest", str(fd), "--sequence", "--image-format=png", "--frames=90-161", f"--props={json.dumps({'only': 'flap'})}"], fd, log)
        box = (560, 300, 1360, 700)
        F_ = [np.asarray(Image.open(p).convert("RGBA")).astype(np.float32) for p in sorted(fd.glob("*.png"))]
        same = [mad(F_[i], F_[i - 1], box) < 0.3 for i in range(1, len(F_))]
        runs, k = [], 0
        while k < len(F_):
            j = k
            while j + 1 < len(F_) and same[j]:
                j += 1
            runs.append((k, j))
            k = j + 1
        bad = []
        for a, b in runs:
            if b - a + 1 >= 3:
                d30, d48 = mad(F_[a], s30, box), mad(F_[a], s48, box)
                if d30 >= 0.5 and d48 >= 0.5:
                    bad.append(f"frames {90 + a}-{90 + b} hold a value that is neither $30 nor $48")
        moving = [f"{90 + a}-{90 + b}" for a, b in runs if b - a + 1 < 3]
        res["flap"]["check"] = {"frames": len(F_), "start_vs_$30": round(mad(F_[0], s30, box), 2), "end_vs_$48": round(mad(F_[-1], s48, box), 2),
                                "rests": [f"{90 + a}-{90 + b}" for a, b in runs if b - a + 1 >= 3], "in_motion": moving, "intermediate_rests": bad}
        c = res["flap"]["check"]
        res["flap"]["ok"] = res["flap"]["render_ok"] and len(F_) == 72 and c["start_vs_$30"] < 0.5 and c["end_vs_$48"] < 0.5 and not bad
    except Exception as e:  # noqa: BLE001
        res["flap"]["ok"], res["flap"]["check"] = False, str(e)
    try:
        w0, wm, w1 = S("wipe_before", 160, {"only": "wipe"}), S("wipe_mid", 171, {"only": "wipe"}), S("wipe_after", 182, {"only": "wipe"})
        lum = lambda a: a[..., :3].mean(axis=2)  # noqa: E731
        dark_b, dark_m, dark_a = (float((lum(x) < 80).mean()) for x in (w0, wm, w1))
        res["wipe"]["check"] = {"dark_share_before": round(dark_b, 3), "dark_share_mid": round(dark_m, 3), "dark_share_after": round(dark_a, 3)}
        res["wipe"]["ok"] = res["wipe"]["render_ok"] and dark_b > 0.9 and 0.15 < dark_m < 0.85 and dark_a < 0.05
    except Exception as e:  # noqa: BLE001
        res["wipe"]["ok"], res["wipe"]["check"] = False, str(e)
    try:
        # R49: the rubber face reaches the paper on the very frame the imprint appears, and the imprint stays
        CF = contact_frame()
        sb, s1, sc, sa = (S(f"stamp_{n}", f, {"only": "stamp"}) for n, f in (("before", CF - 6), ("pre", CF - 1), ("contact", CF), ("after", CF + 30)))
        BOX = (1144, 624, 1616, 806)  # the imprint (440 x 150 at 1160, 640) with room for the document's -2.5 deg tilt
        STRIP = (1170, 768, 1590, 798)  # where the rubber face sits when it presses (the imprint's bottom edge)
        UPPER = (1170, 700, 1590, 755)  # the imprint's lettering band: not inked before contact
        res["stamp"]["check"] = {"contact_frame": CF, "contact_s": round(CF / 30, 3), "imprint_before": round(red(sb, BOX), 4),
                                 "ink_band_1_frame_before": round(red(s1, UPPER), 4), "rubber_on_paper_at_contact": round(red(sc, STRIP), 3),
                                 "rubber_on_paper_1_frame_before": round(red(s1, STRIP), 3), "imprint_after": round(red(sa, BOX), 4)}
        c = res["stamp"]["check"]
        res["stamp"]["ok"] = (res["stamp"]["render_ok"] and c["imprint_before"] < 0.003 and c["ink_band_1_frame_before"] < 0.003
                              and c["rubber_on_paper_at_contact"] > 0.5 and c["rubber_on_paper_1_frame_before"] < 0.2 and c["imprint_after"] > 0.03)
    except Exception as e:  # noqa: BLE001
        res["stamp"]["ok"], res["stamp"]["check"] = False, str(e)
    # the Remotion port of the same HyperFrames block, against the CLI render: alpha masks frame by frame (all 66),
    # IoU at the best time shift (a constant offset between the two clocks is reported, not hidden)
    try:
        pd, cd = O / "port_frames", O / "cli_frames"
        for d in (pd, cd):
            shutil.rmtree(d, ignore_errors=True)
            d.mkdir()
        remotion(["render", "src/index.ts", "ScribblePort", str(pd), "--sequence", "--image-format=png", "--scale=0.25"], pd, log)
        subprocess.run(["ffmpeg", "-v", "error", "-c:v", "libvpx-vp9", "-i", str(PUB / "overlay.webm"), "-vf", "scale=480:270,format=rgba",
                        str(cd / "%03d.png")], check=False)
        P_ = [np.asarray(Image.open(p).convert("RGBA").resize((480, 270)))[..., 3] > 128 for p in sorted(pd.glob("*.png"))]
        C_ = [np.asarray(Image.open(p).convert("RGBA"))[..., 3] > 128 for p in sorted(cd.glob("*.png"))]

        def iou(a, b):
            u = (a | b).sum()
            return float((a & b).sum() / u) if u else 1.0
        best = None
        for sh_ in range(-3, 4):
            pairs = [(P_[i], C_[i + sh_]) for i in range(len(P_)) if 0 <= i + sh_ < len(C_)]
            # frames where either side has ink: the mean IoU over them
            vals = [iou(x, y) for x, y in pairs if x.any() or y.any()]
            m = float(np.mean(vals)) if vals else 0.0
            if best is None or m > best[1]:
                best = (sh_, m, vals)
        cov_p = [round(float(x.mean()), 2) for x in P_][::3]
        cov_c = [round(float(x.mean()), 2) for x in C_][::3]
        res["gsap_port"] = {"ok": best[1] > 0.9, "frames": [len(P_), len(C_)], "best_shift_frames": best[0], "mean_alpha_iou": round(best[1], 3),
                            "min_alpha_iou": round(min(best[2]), 3) if best[2] else None, "coverage_port_every3": cov_p, "coverage_cli_every3": cov_c}
    except Exception as e:  # noqa: BLE001
        res["gsap_port"] = {"ok": False, "error": str(e)[:300]}
    # the full composition
    code, sec, out = remotion(["render", "src/index.ts", "ToolingTest", str(O / "tooling_silent.mp4"), "--muted", "--concurrency=4", "--crf=18"], O, log)
    res["full"] = {"render_ok": code == 0, "seconds": sec, "frames": 240}
    # the mix: the theme under the whole piece, the stamp SFX's own onset on the contact frame
    hit_s = contact_frame() / 30.0 - onset(PUB / "sfx_rubber_stamp.mp3")
    th, st = PUB / "theme_noir_jazz_20s.mp3", PUB / "sfx_rubber_stamp.mp3"
    if th.exists() and st.exists() and (O / "tooling_silent.mp4").exists():
        fc = (f"[1:a]atrim=0:8,asetpts=PTS-STARTPTS,afade=t=in:d=0.4,afade=t=out:st=7.1:d=0.9,volume=0.55[m];"
              f"[2:a]adelay={int(hit_s * 1000)}|{int(hit_s * 1000)},volume=1.0[s];[m][s]amix=inputs=2:normalize=0:duration=first,"
              f"loudnorm=I=-14:TP=-2.0:LRA=11[a]")  # -2.0 so the AAC file stays under the channel's -1.5 dBTP
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(O / "tooling_silent.mp4"), "-i", str(th), "-i", str(st), "-filter_complex", fc,
                        "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-t", "8", "-movflags", "+faststart",
                        str(O / "tooling_test.mp4")], check=True)
        L = loud(O / "tooling_test.mp4")
        res["audio"] = {"ok": L["lufs"] is not None and abs(L["lufs"] + 14) <= 1.0 and L["true_peak"] <= -1.5, "stamp_onset_at_s": round(contact_frame() / 30.0, 3), **L}
    else:
        if (O / "tooling_silent.mp4").exists():
            shutil.copy(O / "tooling_silent.mp4", O / "tooling_test.mp4")
        res["audio"] = {"ok": False, "why": "theme / stamp SFX missing (ElevenLabs test)"}
    (O / "render.json").write_text(json.dumps(res, indent=1, ensure_ascii=False, default=str))
    print(json.dumps(res, indent=1, ensure_ascii=False, default=str))
    return 0


def A_START_C() -> float:
    return (90 + 90 - 18) / 30.0  # scene C starts at 5.4 s


STAMP_HIT = 0.95  # = ToolingTest.tsx STAMP_HIT (s into C)


def contact_frame() -> int:
    """The first frame on which the rubber face touches the paper (RubberStamp.tsx: t >= hitAt)."""
    import math
    return 162 + math.ceil(STAMP_HIT * 30 - 1e-9)


def onset(p: Path) -> float:
    """Seconds from the start of an SFX file to its attack (first 5 ms window within 20 dB of the peak)."""
    if not p.exists():
        return 0.0
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(p), "-ac", "1", "-ar", "48000", "-f", "s16le", "-"], capture_output=True).stdout
    x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0
    if not len(x):
        return 0.0
    w = 240
    e = np.sqrt(np.convolve(x * x, np.ones(w) / w, mode="valid"))
    k = int(np.argmax(e > e.max() * 0.1))
    return k / 48000.0


def loud(p: Path) -> dict:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(p), "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
    i = re.findall(r"I:\s+(-?[\d.]+) LUFS", r)
    tp = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r)
    return {"lufs": float(i[-1]) if i else None, "true_peak": float(tp[-1]) if tp else None}


# ------------------------------------------------------------------ report
LABEL = {"effects": "@remotion/effects halftone + paper + speckle", "title": "Special Elite title (@remotion/google-fonts)",
         "circle": "red-ink rough-notation circle", "overlay": "HyperFrames transparent WebM overlay (hw-scribble-transition, CLI)",
         "flap": "split-flap $30 -> $48 (Remotion port, straight flip)", "wipe": "clockWipe transition",
         "stamp": "flat 1950s rubber stamp hits the statement, leaves its imprint (R49)"}


def sheet(O: Path) -> None:
    v = O / "tooling_test.mp4"
    tiles = []
    for k in range(16):
        t = 0.25 + k * 0.5
        p = O / "stills" / f"sheet_{k:02d}.png"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(v), "-frames:v", "1", "-vf", "scale=480:-1", str(p)], check=False)
        if p.exists():
            tiles.append((t, Image.open(p).convert("RGB")))
    if not tiles:
        return
    w, h = tiles[0][1].size
    S = Image.new("RGB", (4 * w + 50, 4 * (h + 30) + 70), (24, 22, 20))
    d = ImageDraw.Draw(S)
    try:
        F = ImageFont.truetype(str(ROOT / "assets/fonts/SpecialElite-Regular.ttf"), 22)
        F2 = ImageFont.truetype(str(ROOT / "assets/fonts/SpecialElite-Regular.ttf"), 30)
    except Exception:  # noqa: BLE001
        F = F2 = ImageFont.load_default()
    d.text((12, 14), "CoinSense · tooling v2 test · 8 s · 1080p · contact sheet (every 0.5 s)", fill=(240, 228, 200), font=F2)
    for i, (t, im) in enumerate(tiles):
        x, y = 10 + (i % 4) * (w + 10), 60 + (i // 4) * (h + 30)
        S.paste(im, (x, y))
        what = "A" if t < 3 else ("B" if t < 5.4 else ("wipe" if t < 6 else "C + stamp"))
        if 2.0 <= t <= 4.2:
            what += " + scribble overlay"
        d.text((x + 4, y + h + 3), f"{t:.2f} s · {what}", fill=(220, 210, 190), font=F)
    S.save(O / "tooling_test_sheet.png")


TEST_ASSETS = ["tooling/photo.jpg", "tooling/overlay.webm", "font:special elite", "font:courier prime",
               "theme_noir_jazz_20s.mp3", "sfx_rubber_stamp.mp3"]


def ingest_test_assets() -> tuple[list[str], list[str]]:
    """Rows for the test's own assets (from their sidecars) into docs/ASSET_LICENSES.md, then the asset_license check."""
    import asset_license as AL
    side = PUB / "photo.jpg.license.json"
    if side.exists():
        m = json.loads(side.read_text())
        AL.upsert({"file": "tooling/photo", "kind": "archive", "source_url": m["source_url"], "licence": m["licence"], "date": m["item_date"],
                   "attribution": m["attribution"], "notes": f"tools/archives.py (LoC); file {m.get('file_url', '')}"})
    side = PUB / "stamp.json.license.json"
    if side.exists():
        m = json.loads(side.read_text())
        AL.upsert({"file": "tooling/stamp", "kind": "lottie", "source_url": m["page"], "licence": m["licence"], "date": m["fetched"],
                   "attribution": f"{m['title']} by {m['author']} (LottieFiles)", "notes": f"file {m['url']}; Lottie probe only — refused for episodes (off-style, Klot)"})
    AL.upsert({"file": "tooling/overlay", "kind": "overlay", "source_url": "vendor/hyperframes/registry/blocks/hw-scribble-transition",
               "licence": "rendered from Apache-2.0 code (HyperFrames, HeyGen); output is ours", "date": date.today().isoformat(),
               "attribution": "HyperFrames hw-scribble-transition (Apache-2.0) · CREDITS", "notes": f"{HF_CLI} render --format webm; colour #a8231c"})
    for j in sorted(PUB.glob("*.mp3.json")):
        m = json.loads(j.read_text())
        AL.upsert({"file": m["file"], "kind": "music" if m["kind"] == "music" else "sfx", "source_url": "ElevenLabs API",
                   "licence": m["licence"], "date": m["generated"], "attribution": "—",
                   "notes": f"model: ElevenLabs {m['model']}; prompt: {m['prompt'][:160]}; {m['credits_used']} credits"})
    return AL.check(TEST_ASSETS)


def report(outdir: str, probe: str) -> int:
    O = Path(outdir).resolve()
    miss, inc = ingest_test_assets()
    prep_ = json.loads((O / "prep.json").read_text()) if (O / "prep.json").exists() else {}
    res = json.loads((O / "render.json").read_text()) if (O / "render.json").exists() else {}
    pr = json.loads(Path(probe).read_text()) if probe and Path(probe).exists() else {}
    if (O / "tooling_test.mp4").exists():
        sheet(O)
    yn = lambda b: "yes" if b else "NO"  # noqa: E731
    md = ["# Tooling v2 · test render", "", f"GitHub Actions ubuntu runner, no GPU: Chrome with `--gl=swangle` (SwiftShader on ANGLE), "
          f"effects on `--preferred-effect-backend=webgl2`. Remotion {pr.get('remotion_version', '4.0.541')}.", "",
          f"GPU report (`npx remotion gpu`): {res.get('gpu') or 'n/a'}", "",
          "| element | renders correctly without a GPU | render time (alone) | how it was checked |", "|---|---|---|---|"]
    for el, lab in LABEL.items():
        r = res.get(el, {})
        extra = ""
        if el == "overlay":
            extra = f"; CLI render {prep_.get('overlay', {}).get('seconds', '?')} s, alpha {prep_.get('overlay', {}).get('alpha', {})}"
            extra = extra[:400]
        md.append(f"| {lab} | {yn(r.get('ok'))} | {r.get('seconds', '?')} s for {r.get('frames', '?')} frames | {json.dumps(r.get('check'), ensure_ascii=False)}{extra} |")
    a = res.get("audio", {})
    md.append(f"| theme + stamp SFX (ElevenLabs) | {yn(a.get('ok'))} | mixed after the render | stamp SFX onset on the contact frame ({a.get('stamp_onset_at_s')} s); master {a.get('lufs')} LUFS integrated, true peak {a.get('true_peak')} dBTP |")
    f = res.get("full", {})
    md += ["", f"Full 8 s composition (240 frames, all elements): {'OK' if f.get('render_ok') else 'FAILED'} in {f.get('seconds', '?')} s.", ""]
    g = res.get("gsap_port", {})
    md += [f"HyperFrames -> Remotion port (ScribbleWipe.tsx, the same hw-scribble-transition, its GSAP timeline written out per frame): {'matches' if g.get('ok') else 'DOES NOT match'} the CLI render "
           f"(mean alpha IoU {g.get('mean_alpha_iou')} over the inked frames, min {g.get('min_alpha_iou')}, clock offset {g.get('best_shift_frames')} frames; "
           f"coverage every 3rd frame, port {g.get('coverage_port_every3')} vs CLI {g.get('coverage_cli_every3')}){' · ' + g['error'] if g.get('error') else ''}.", ""]
    if pr.get("archives"):
        md += ["## Archive APIs from Actions", "", "| source | reachable | gated hits | seconds | note |", "|---|---|---|---|---|"]
        for x in pr["archives"]:
            md.append(f"| {x['name']} | {yn(x.get('reachable'))} | {x.get('gated_hits', '-')} | {x.get('seconds')} | {x.get('error', '')[:120]} |")
    ph = prep_.get("photo", {})
    md += ["", f"Photo for the halftone: LoC item {LOC_ID} through tools/archives.py: {'OK' if ph.get('ok') else 'FAILED'} · {ph.get('title', '')} · "
           f"item date {ph.get('date', '?')} · {ph.get('licence', ph.get('error', ''))}"]
    lt = prep_.get("lottie", {})
    md += [f"Lottie support (LottieProbe composition, not in the film): {'renders' if lt.get('coverage_final') else 'FAILED'} in {lt.get('render_seconds', '?')} s. "
           f"The LottieFiles Approved Stamp itself is refused for episodes (modern isometric, off-style)."]
    md += ["", f"asset_license check on this test's assets: {'PASS' if not miss else 'FAIL: ' + ', '.join(miss)}" + (f" (incomplete: {'; '.join(inc)})" if inc else "")]
    (O / "tooling_test.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    ov = (prep_.get("overlay") or {}).get("alpha") or {}
    fc = res.get("flap", {}).get("check") or {}
    ef = res.get("effects", {}).get("check") or {}
    st = res.get("stamp", {}).get("check") or {}
    short = [f"Loudness: {a.get('lufs')} LUFS integrated, true peak {a.get('true_peak')} dBTP (channel standard: -14 LUFS, true peak <= -1.5 dBTP).",
             "Frame-review fixes:",
             f"a. halftone: 3 px screen over the plain photo; readable (structure {ef.get('readable_corr')}, contrast {ef.get('contrast_ratio')}x, brightness {ef.get('mean_shift')})",
             f"b. split-flap: straight $30 -> $48; rests only on {fc.get('rests')}; intermediate rests: {len(fc.get('intermediate_rests') or [])}",
             f"c. scribble: full red cover {ov.get('full_cover_s')} s (cap 0.25 s), the cut inside it",
             f"d. stamp: flat 1950s rubber stamp, touches the paper on frame {st.get('contact_frame')} ({st.get('contact_s')} s) where the PAID imprint appears; stamp SFX on that frame",
             "Per element (renders without a GPU · time rendered alone):"] + [
        f"- {LABEL[e]}: {yn(res.get(e, {}).get('ok'))} · {res.get(e, {}).get('seconds', '?')} s" for e in LABEL] + [
        f"- theme + stamp SFX (ElevenLabs): {yn(a.get('ok'))}",
        f"Full 8 s render: {f.get('seconds', '?')} s."]
    if pr.get("archives"):
        short += ["Archive APIs from Actions: " + "; ".join(f"{x['source']} {'reachable' if x.get('reachable') else 'NOT reachable'}" for x in pr["archives"])]
    (O / "tooling_test_note.txt").write_text("\n".join(short) + "\n", encoding="utf-8")
    print("\n".join(md))
    return 0


if __name__ == "__main__":
    a = sys.argv[1:]
    sys.exit({"prep": lambda: prep(a[1], a[2]), "render": lambda: render(a[1]), "report": lambda: report(a[1], a[2] if len(a) > 2 else "")}[a[0]]())
