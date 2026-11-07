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
HF_CLI = "@hyperframes/cli@0.9.19"
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
        for wait in (0, 30, 60, 90):  # loc.gov answers 429 for a while after a burst (the probe's searches)
            time.sleep(wait)
            try:
                m = A.fetch("loc", LOC_ID, str(PUB / "photo.jpg"), register=False)
                break
            except Exception as e:  # noqa: BLE001
                if "429" not in str(e) or wait == 90:
                    raise
        rep["photo"] = {"ok": True, "seconds": round(time.time() - t0, 1), "title": m["title"], "date": m["item_date"], "licence": m["licence"]}
    except Exception as e:  # noqa: BLE001
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
    (hf / "index.html").write_text(html)
    code, sec, out = sh(["npx", "-y", HF_CLI, "--version"], log=log, timeout=600)
    rep["hyperframes_cli"] = {"exit": code, "install_seconds": sec, "out": [l for l in out.strip().splitlines() if l.strip()][-8:]}
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
    for f in ("theme_noir_jazz_20s.mp3", "sfx_rubber_stamp.mp3"):
        if (A_ / f).exists():
            shutil.copy(A_ / f, PUB / f)
            if (A_ / (f + ".json")).exists():
                shutil.copy(A_ / (f + ".json"), PUB / (f + ".json"))
    rep["audio"] = {f: (PUB / f).exists() for f in ("theme_noir_jazz_20s.mp3", "sfx_rubber_stamp.mp3")}
    cfg = {"lottie": "tooling/stamp.json" if rep["lottie"]["ok"] else None, "lottieAt": 0.7, "flap": {"from": "$30", "to": "$48", "startAt": 0.6}}
    (PUB / "test.json").write_text(json.dumps(cfg))
    # 5. where the stamp lands inside the Lottie: the first frame the stamp's area reaches 90 % of its final coverage
    bundle(log)
    if rep["lottie"]["ok"]:
        fr = O / "lottie_frames"
        code, sec, out = remotion(["render", "src/index.ts", "LottieProbe", str(fr), "--sequence", "--image-format=png"], fr, log)
        cov = []
        for p in sorted(fr.glob("*.png")):
            a = np.asarray(Image.open(p).convert("RGBA"))[..., 3] > 40
            cov.append(float(a.mean()))
        if cov:
            fin = cov[-1] or max(cov)
            hit = next((i for i, c in enumerate(cov) if fin and c >= 0.9 * fin), 0)
            # the slam: the biggest single-frame jump in coverage at or before that frame
            jumps = [cov[i] - cov[i - 1] for i in range(1, hit + 1)] or [0]
            slam = int(np.argmax(jumps)) + 1 if hit else 0
            cfg["stampHit"] = round(cfg["lottieAt"] + slam / 30.0, 3)
            rep["lottie"].update({"render_seconds": sec, "hit_frame": slam, "coverage_final": round(fin, 3)})
            (PUB / "test.json").write_text(json.dumps(cfg))
    (O / "prep.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False))
    print(json.dumps(rep, indent=1, ensure_ascii=False))
    return 0


def webm_alpha(path: Path) -> dict:
    """Alpha coverage of a VP9 WebM over time (decoded with libvpx so the alpha plane is kept)."""
    tmp = Path("/tmp/hf/alpha")
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    subprocess.run(["ffmpeg", "-v", "error", "-c:v", "libvpx-vp9", "-i", str(path), "-vf", "fps=10,scale=480:-1,format=rgba", str(tmp / "%03d.png")], check=False)
    cov = [float((np.asarray(Image.open(p))[..., 3] > 128).mean()) for p in sorted(tmp.glob("*.png"))]
    if not cov:
        return {"ok": False, "why": "no frames decoded"}
    return {"ok": cov[0] < 0.02 and max(cov) > 0.97 and cov[-1] < 0.02, "first": round(cov[0], 3), "max": round(max(cov), 3),
            "last": round(cov[-1], 3), "frames": len(cov), "coverage_10fps": [round(c, 2) for c in cov]}


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
    spans = {"effects": (0, 89), "title": (0, 89), "circle": (20, 80), "overlay": (55, 130), "flap": (90, 179), "wipe": (155, 185), "lottie": (162, 239)}
    for el, (a, b) in spans.items():
        code, sec, out = remotion(["render", "src/index.ts", "ToolingTest", str(O / f"el_{el}.mp4"), f"--props={json.dumps({'only': el})}",
                                   f"--frames={a}-{b}", "--muted", "--concurrency=4"], O, log)
        err = [l for l in out.splitlines() if re.search(r"(?i)error|fail|falling back|not supported|webgpu|webgl", l)][:6]
        res[el] = {"render_ok": code == 0, "seconds": sec, "frames": b - a + 1, "log": err}
    # checks (stills)
    S = lambda n, f, p, c="ToolingTest": still(O, n, f, p, log, c)  # noqa: E731
    PHOTO, TAG, LOT = (142, 232, 998, 828), (1180, 500, 1800, 860), (1230, 250, 1790, 810)
    try:
        on, off = S("effects_on", 40, {"only": "effects"}), S("effects_off", 40, {"only": "effects", "fx": False})
        bg = (1100, 900, 1880, 1060)
        res["effects"]["check"] = {"halftone_hf_on": round(hf_energy(on, PHOTO), 2), "halftone_hf_off": round(hf_energy(off, PHOTO), 2),
                                   "paper_mad_vs_plain": round(mad(on, off, bg), 2),
                                   "speckle_dark_px": round(float((on[900:1060, 1100:1880, :3].mean(axis=2) < 90).mean()), 4) if on is not None else -1}
        c = res["effects"]["check"]
        res["effects"]["ok"] = res["effects"]["render_ok"] and c["halftone_hf_on"] > 1.5 * max(c["halftone_hf_off"], 0.5) and c["paper_mad_vs_plain"] > 2 and c["speckle_dark_px"] > 0.0005
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
        o0, o1, o2 = S("overlay_before", 55, {"only": "overlay"}), S("overlay_full", 92, {"only": "overlay"}), S("overlay_after", 130, {"only": "overlay"})
        full = (0, 0, 1920, 1080)
        res["overlay"]["check"] = {"red_before": round(red(o0, full), 3), "red_full_cover": round(red(o1, full), 3), "red_after": round(red(o2, full), 3)}
        c = res["overlay"]["check"]
        res["overlay"]["ok"] = res["overlay"]["render_ok"] and c["red_full_cover"] > 0.95 and c["red_before"] < 0.01 and c["red_after"] < 0.01
    except Exception as e:  # noqa: BLE001
        res["overlay"]["ok"], res["overlay"]["check"] = False, str(e)
    try:
        f = cfg["flap"]
        s30 = S("flap_static30", 120, {"only": "flap", "flap": {"from": f["from"], "to": f["from"], "startAt": 0}})
        s48 = S("flap_static48", 120, {"only": "flap", "flap": {"from": f["to"], "to": f["to"], "startAt": 0}})
        a0, am, a1 = S("flap_start", 95, {"only": "flap"}), S("flap_mid", 115, {"only": "flap"}), S("flap_end", 175, {"only": "flap"})
        box = (560, 300, 1360, 700)
        res["flap"]["check"] = {"start_vs_$30": round(mad(a0, s30, box), 2), "end_vs_$48": round(mad(a1, s48, box), 2),
                                "mid_vs_$30": round(mad(am, s30, box), 2), "mid_vs_$48": round(mad(am, s48, box), 2)}
        c = res["flap"]["check"]
        res["flap"]["ok"] = res["flap"]["render_ok"] and c["start_vs_$30"] < 0.5 and c["end_vs_$48"] < 0.5 and c["mid_vs_$30"] > 1 and c["mid_vs_$48"] > 1
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
        hit = int(round((A_START_C() + cfg.get("stampHit", 1.0)) * 30))
        l0, l1 = S("lottie_before", 170, {"only": "lottie"}), S("lottie_after", min(239, hit + 15), {"only": "lottie"})
        d = mad(l0, l1, LOT)
        res["lottie"]["check"] = {"box_change_mad": round(d, 2), "stamp_hit_s": round(A_START_C() + cfg.get("stampHit", 0), 2)}
        res["lottie"]["ok"] = res["lottie"]["render_ok"] and d > 3
    except Exception as e:  # noqa: BLE001
        res["lottie"]["ok"], res["lottie"]["check"] = False, str(e)
    # the @remotion/gsap port of the same HyperFrames block, against the CLI render (alpha coverage, frame by frame)
    try:
        ious = []
        for lf in (10, 20, 30, 45, 55):
            pr = still(O, f"port_{lf}", lf, {"color": "#a8231c"}, log, "ScribblePort")
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-c:v", "libvpx-vp9", "-i", str(PUB / "overlay.webm"), "-vf", f"select=eq(n\\,{lf}),format=rgba",
                            "-frames:v", "1", str(O / "stills" / f"cli_{lf}.png")], check=False)
            cl = np.asarray(Image.open(O / "stills" / f"cli_{lf}.png").convert("RGBA"))[..., 3] > 128
            pa = pr[..., 3] > 128 if pr is not None else np.zeros_like(cl)
            u = (cl | pa).sum()
            ious.append(round(float((cl & pa).sum() / u) if u else 1.0, 3))
        res["gsap_port"] = {"ok": min(ious) > 0.9, "alpha_iou_vs_cli": ious}
    except Exception as e:  # noqa: BLE001
        res["gsap_port"] = {"ok": False, "error": str(e)[:300]}
    # the full composition
    code, sec, out = remotion(["render", "src/index.ts", "ToolingTest", str(O / "tooling_silent.mp4"), "--muted", "--concurrency=4", "--crf=18"], O, log)
    res["full"] = {"render_ok": code == 0, "seconds": sec, "frames": 240}
    # the mix: the theme under the whole piece, the stamp on the Lottie's hit
    hit_s = A_START_C() + cfg.get("stampHit", 1.0)
    th, st = PUB / "theme_noir_jazz_20s.mp3", PUB / "sfx_rubber_stamp.mp3"
    if th.exists() and st.exists() and (O / "tooling_silent.mp4").exists():
        fc = (f"[1:a]atrim=0:8,asetpts=PTS-STARTPTS,afade=t=in:d=0.4,afade=t=out:st=7.1:d=0.9,volume=0.55[m];"
              f"[2:a]adelay={int(hit_s * 1000)}|{int(hit_s * 1000)},volume=1.0[s];[m][s]amix=inputs=2:normalize=0:duration=first,"
              f"loudnorm=I=-14:TP=-1.5:LRA=11[a]")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(O / "tooling_silent.mp4"), "-i", str(th), "-i", str(st), "-filter_complex", fc,
                        "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-t", "8", "-movflags", "+faststart",
                        str(O / "tooling_test.mp4")], check=True)
        res["audio"] = {"ok": True, "stamp_at_s": round(hit_s, 2), **loud(O / "tooling_test.mp4")}
    else:
        if (O / "tooling_silent.mp4").exists():
            shutil.copy(O / "tooling_silent.mp4", O / "tooling_test.mp4")
        res["audio"] = {"ok": False, "why": "theme / stamp SFX missing (ElevenLabs test)"}
    (O / "render.json").write_text(json.dumps(res, indent=1, ensure_ascii=False, default=str))
    print(json.dumps(res, indent=1, ensure_ascii=False, default=str))
    return 0


def A_START_C() -> float:
    return (90 + 90 - 18) / 30.0  # scene C starts at 5.4 s


def loud(p: Path) -> dict:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(p), "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
    i = re.findall(r"I:\s+(-?[\d.]+) LUFS", r)
    tp = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r)
    return {"lufs": float(i[-1]) if i else None, "true_peak": float(tp[-1]) if tp else None}


# ------------------------------------------------------------------ report
LABEL = {"effects": "@remotion/effects halftone + paper + speckle", "title": "Special Elite title (@remotion/google-fonts)",
         "circle": "red-ink rough-notation circle", "overlay": "HyperFrames transparent WebM overlay (hw-scribble-transition, CLI)",
         "flap": "split-flap $30 -> $48 (Remotion port)", "wipe": "clockWipe transition", "lottie": "Lottie icon (LottieFiles approved stamp)"}


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
        what = "A" if t < 3 else ("B" if t < 5.4 else ("wipe" if t < 6 else "C"))
        if 2.0 <= t <= 4.2:
            what += " + scribble overlay"
        d.text((x + 4, y + h + 3), f"{t:.2f} s · {what}", fill=(220, 210, 190), font=F)
    S.save(O / "tooling_test_sheet.png")


TEST_ASSETS = ["tooling/photo.jpg", "tooling/overlay.webm", "tooling/stamp.json", "font:special elite", "font:courier prime",
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
                   "attribution": f"{m['title']} by {m['author']} (LottieFiles)", "notes": f"file {m['url']}"})
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
    md.append(f"| theme + stamp SFX (ElevenLabs) | {yn(a.get('ok'))} | mixed after the render | stamp at {a.get('stamp_at_s')} s; master {a.get('lufs')} LUFS, TP {a.get('true_peak')} dBTP |")
    f = res.get("full", {})
    md += ["", f"Full 8 s composition (240 frames, all elements): {'OK' if f.get('render_ok') else 'FAILED'} in {f.get('seconds', '?')} s.", ""]
    g = res.get("gsap_port", {})
    md += [f"HyperFrames -> Remotion port via @remotion/gsap (the same hw-scribble-transition): {'matches' if g.get('ok') else 'DOES NOT match'} the CLI render "
           f"(alpha IoU per frame {g.get('alpha_iou_vs_cli', g.get('error'))}).", ""]
    if pr.get("archives"):
        md += ["## Archive APIs from Actions", "", "| source | reachable | gated hits | seconds | note |", "|---|---|---|---|---|"]
        for x in pr["archives"]:
            md.append(f"| {x['name']} | {yn(x.get('reachable'))} | {x.get('gated_hits', '-')} | {x.get('seconds')} | {x.get('error', '')[:120]} |")
    ph = prep_.get("photo", {})
    md += ["", f"Photo for the halftone: LoC item {LOC_ID} through tools/archives.py: {'OK' if ph.get('ok') else 'FAILED'} · {ph.get('title', '')} · "
           f"item date {ph.get('date', '?')} · {ph.get('licence', ph.get('error', ''))}"]
    lt = prep_.get("lottie", {})
    md += [f"Lottie: {LOTTIE['title']} by {LOTTIE['author']} ({LOTTIE['page']}), {LOTTIE['licence']} · {lt}"]
    md += ["", f"asset_license check on this test's assets: {'PASS' if not miss else 'FAIL: ' + ', '.join(miss)}" + (f" (incomplete: {'; '.join(inc)})" if inc else "")]
    (O / "tooling_test.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    short = ["Per element (renders without a GPU · time alone):"] + [
        f"- {LABEL[e]}: {yn(res.get(e, {}).get('ok'))} · {res.get(e, {}).get('seconds', '?')} s" for e in LABEL] + [
        f"- theme + stamp SFX: {yn(a.get('ok'))} · {a.get('lufs')} LUFS",
        f"Full 8 s render: {f.get('seconds', '?')} s. gsap port matches CLI: {yn(g.get('ok'))}."]
    if pr.get("archives"):
        short += ["Archive APIs from Actions: " + "; ".join(f"{x['source']} {'reachable' if x.get('reachable') else 'NOT reachable'}" for x in pr["archives"])]
    (O / "tooling_test_note.txt").write_text("\n".join(short) + "\n", encoding="utf-8")
    print("\n".join(md))
    return 0


if __name__ == "__main__":
    a = sys.argv[1:]
    sys.exit({"prep": lambda: prep(a[1], a[2]), "render": lambda: render(a[1]), "report": lambda: report(a[1], a[2] if len(a) > 2 else "")}[a[0]]())
