"""ElevenLabs Sound Effects + Music (tooling v2, item 5). The key comes from ELEVENLABS_API_KEY and is never printed.

  python tools/el_audio.py sfx   <out.mp3> "<prompt>" [seconds]     one sound effect  (POST /v1/sound-generation)
  python tools/el_audio.py music <out.mp3> "<prompt>" <seconds>     one instrumental  (POST /v1/music, force_instrumental)
  python tools/el_audio.py test  <out dir>                           the tooling-v2 test: 20 s channel theme + 4 SFX
  python tools/el_audio.py kit   <out dir> [stems]                   the channel sound kit (R52): sting, outro, 4 loop beds

Every file gets a sidecar <file>.json: model, prompt, length, date, plan, credits used (subscription counter before/after)
-> the row for docs/ASSET_LICENSES.md. A missing API permission is reported by name (what to tick on the key), never
retried. Each call is made once (no retries on a 200), so the credits spent are exactly what the test reports."""
from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import voice_d as VD  # noqa: E402

SFX_MODEL = "eleven_text_to_sound_v2"
MUSIC_MODEL = "music_v1"
# the permission names the API reports -> what to enable on the key (ElevenLabs > Developers > API keys > edit)
PERMS = {"sound_generation": "Sound Effects: Access", "music_generation": "Music: Access",
         "text_to_sound_effects": "Sound Effects: Access", "music": "Music: Access", "user_read": "User: Read"}

THEME = ("1950s cool jazz, noir detective, brushed drums, upright bass, muted trumpet, no vocals. Medium-slow swing, "
         "smoky late-night office, a short memorable trumpet motif stated twice, ends on a resolved chord.")
SFX = [  # (file stem, prompt, seconds)
    ("sfx_rubber_stamp", "Close-up foley: a wooden office rubber stamp slammed hard onto a paper document on a wooden desk, a sharp loud thud with a short paper slap, single impact, dry studio", 1.0),
    ("sfx_safe_dial", "Close-up of an old steel safe combination dial turning: a run of crisp small mechanical clicks, then one heavier click, dry", 2.0),
    ("sfx_typewriter_burst", "A quick burst of typing on a 1950s manual typewriter, about eight fast keystrokes, close microphone, dry office", 1.5),
    ("sfx_case_folder_slap", "A thick cardboard case-file folder with papers inside slapped down flat onto a wooden desk, one hit, dry", 1.0),
]


# The channel sound kit (Klot, Nov 7: R52). Same instruments and motif as the approved 20 s theme. The beds are made a few
# seconds longer than the loop, then folded into a seamless loop (the tail crossfaded into the head, see loop()).
KIT_STYLE = ("1950s cool jazz, noir detective, upright bass, brushed drums, muted trumpet, no vocals, no singing, no voices. "
             "The CoinSense theme: a short memorable three-note muted-trumpet motif, smoky late-night detective office.")
LOOP_S, LOOP_HEAD, LOOP_XF = 60.0, 4.0, 3.0  # loop length; skipped intro; tail->head crossfade
KIT = [  # (stem, prompt, asked seconds, kind of piece)
    ("cs_sting", KIT_STYLE + " A 4-second opening sting for a case-file title card: a sharp upright-bass pluck and a brushed "
     "cymbal swell, the muted trumpet states the three-note motif once, ends on a held minor chord. Short, punchy.", 4.0, "sting"),
    ("cs_outro", KIT_STYLE + " An 8-second closing outro for 'case closed' and the end screen: the trumpet plays the motif once "
     "more, slower, walking bass resolves, brushed drums stop, ends on a warm resolved final chord that rings out.", 8.0, "outro"),
    ("cs_bed_tension", KIT_STYLE + " Underscore bed under narration, tension: a steady pulsing upright-bass ostinato like a "
     "ticking clock, soft brushed hi-hat ticks, sparse low muted-trumpet hints of the motif, suspense, quiet and even, no "
     "build-up, no ending, no intro, loopable.", LOOP_S + LOOP_HEAD + LOOP_XF + 1, "bed"),
    ("cs_bed_investigation", KIT_STYLE + " Underscore bed under narration, investigation: medium-slow walking upright bass, "
     "brushed snare, curious muted-trumpet phrases built on the motif, thoughtful, steady, quiet and even, no build-up, no "
     "ending, no intro, loopable.", LOOP_S + LOOP_HEAD + LOOP_XF + 1, "bed"),
    ("cs_bed_irony", KIT_STYLE + " Underscore bed under narration, light irony: a sly playful swing, plucky upright bass, light "
     "brushed drums with a wink, the muted trumpet plays the motif with a cheeky bend, light and wry, quiet and even, no "
     "build-up, no ending, no intro, loopable.", LOOP_S + LOOP_HEAD + LOOP_XF + 1, "bed"),
    ("cs_bed_resolution", KIT_STYLE + " Underscore bed under narration, resolution: warm relaxed swing, the upright bass walks "
     "in a major key, soft brushed drums, the muted trumpet plays the motif calm and hopeful, relief, everything set right, "
     "quiet and even, no build-up, no ending, no intro, loopable.", LOOP_S + LOOP_HEAD + LOOP_XF + 1, "bed"),
]


class PermissionMissing(RuntimeError):
    pass


def used() -> tuple[int, dict]:
    a = VD.account()
    return a["characters_used"], a


def _fail(what: str, r) -> None:
    try:
        d = r.json().get("detail", r.json())
    except Exception:  # noqa: BLE001
        d = r.text[:300]
    msg = d.get("message", "") if isinstance(d, dict) else str(d)
    status = d.get("status", "") if isinstance(d, dict) else ""
    if r.status_code in (401, 403) and ("permission" in msg.lower() or "permission" in status):
        perm = next((p for p in PERMS if p in msg), None)
        raise PermissionMissing(f"{what}: the key lacks a permission -> enable '{PERMS.get(perm, perm or '?')}' "
                                f"(API says: {msg[:200]})")
    raise RuntimeError(f"{what}: HTTP {r.status_code} {status} {msg[:300]}")


def _post_audio(path: str, body: dict, what: str) -> tuple[bytes, dict]:
    import requests
    for a in range(4):
        r = requests.post(VD.API + path, headers={**VD.H(), "Content-Type": "application/json"},
                          params={"output_format": "mp3_44100_192"}, json=body, timeout=600)
        if r.status_code == 200 and len(r.content) > 1000:
            hdr = {k: v for k, v in r.headers.items() if any(x in k.lower() for x in ("cost", "character", "credit"))}
            return r.content, hdr
        if r.status_code in (429, 500, 502, 503):  # not billed
            time.sleep(8 + 8 * a)
            continue
        _fail(what, r)
    raise RuntimeError(f"{what}: gave up after retries")


def probe(path: Path) -> dict:
    o = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True).stdout.strip()
    vol = subprocess.run(["ffmpeg", "-v", "info", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    mx = next((float(l.split(":")[1].split()[0]) for l in vol.splitlines() if "max_volume" in l), None)
    mean = next((float(l.split(":")[1].split()[0]) for l in vol.splitlines() if "mean_volume" in l), None)
    return {"seconds": round(float(o or 0), 2), "peak_db": mx, "mean_db": mean}


def make(kind: str, out: Path, prompt: str, seconds: float, plan: str = "") -> dict:
    out.parent.mkdir(parents=True, exist_ok=True)
    before, acc = used()
    if kind == "sfx":
        body = {"text": prompt, "duration_seconds": seconds, "prompt_influence": 0.6, "model_id": SFX_MODEL}
        data, hdr = _post_audio("/v1/sound-generation", body, f"Sound Effects ({out.name})")
        model = SFX_MODEL
    else:
        body = {"prompt": prompt, "music_length_ms": int(seconds * 1000), "model_id": MUSIC_MODEL, "force_instrumental": True}
        data, hdr = _post_audio("/v1/music", body, f"Music ({out.name})")
        model = MUSIC_MODEL
    out.write_bytes(data)
    time.sleep(2)
    after, _ = used()
    meta = {"file": out.name, "kind": kind, "provider": "ElevenLabs", "model": model, "prompt": prompt, "asked_seconds": seconds,
            **probe(out), "generated": date.today().isoformat(), "plan": acc["plan"], "commercial_use": acc["commercial_use"],
            "credits_used": max(0, after - before), "cost_headers": hdr,
            "licence": "ElevenLabs output, paid plan: commercial use allowed (ElevenLabs Terms / Eleven Music terms)"
            if acc["commercial_use"] else "ElevenLabs free plan: NON-commercial, attribution required — not usable in a video"}
    if kind == "music":
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
            from factory.music import vocals_in
            meta["vocals_heard"] = vocals_in(out)
        except Exception as e:  # noqa: BLE001
            meta["vocals_heard"] = f"(check not run: {e})"
    Path(str(out) + ".json").write_text(json.dumps(meta, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return meta


MIN_PEAK_DB = -20.0  # a sound effect that peaks lower than this came back (nearly) silent: made again once


def make_checked(kind: str, out: Path, prompt: str, seconds: float) -> dict:
    m = make(kind, out, prompt, seconds)
    if kind == "sfx" and (m.get("peak_db") is None or m["peak_db"] < MIN_PEAK_DB):
        first = m
        m = make(kind, out, prompt + ", loud and clear, close microphone", seconds)
        m["retake_of"] = {"peak_db": first.get("peak_db"), "credits_used": first.get("credits_used")}
        Path(str(out) + ".json").write_text(json.dumps(m, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return m


def test(outdir: str, only: str = "") -> int:
    O = Path(outdir)
    O.mkdir(parents=True, exist_ok=True)
    start, acc = used()
    lines = [f"ElevenLabs plan: {acc['plan']} · commercial use: {'yes' if acc['commercial_use'] else 'NO'} · "
             f"{acc['characters_left']} credits left before the test"]
    rows, missing = [], []
    jobs = [("music", "theme_noir_jazz_20s", THEME, 20.0)] + [("sfx", s, p, d) for s, p, d in SFX]
    if only:
        jobs = [j for j in jobs if j[1] in only.split(",")]
    for kind, stem, prompt, sec in jobs:
        try:
            m = make_checked(kind, O / f"{stem}.mp3", prompt, sec)
            rows.append(m)
            v = f" · vocals heard: {m['vocals_heard'] or 'none'}" if kind == "music" else ""
            lines.append(f"{stem}: {m['seconds']} s (asked {sec}), peak {m['peak_db']} dB, {m['credits_used']} credits{v}")
        except PermissionMissing as e:
            missing.append(str(e))
            lines.append(f"{stem}: NOT MADE — {e}")
        except Exception as e:  # noqa: BLE001
            lines.append(f"{stem}: FAILED — {e}")
    end, acc2 = used()
    lines.append(f"Credits used by the whole test: {max(0, end - start)} ({acc2['characters_left']} left)")
    (O / "audio_test.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (O / "audio_test.json").write_text(json.dumps({"rows": rows, "missing_permissions": missing}, indent=1, ensure_ascii=False))
    print("\n".join(lines), flush=True)
    return 0 if rows else 1


def _pcm(path: Path, sr: int = 44100):
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "2", "-ar", str(sr), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).copy()


def _write(path: Path, x, sr: int = 44100) -> None:
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ac", "2", "-ar", str(sr), "-i", "-", "-c:a", "libmp3lame",
                    "-b:a", "192k", str(path)], input=x.astype("float32").tobytes(), check=True)


def loop(raw: Path, out: Path, sr: int = 44100) -> dict:
    """Fold a generated bed into a seamless LOOP_S loop: skip the first LOOP_HEAD s (the model's intro), keep LOOP_S s, and
    crossfade (equal power) the LOOP_XF s that follow the loop into its first LOOP_XF s — so the loop's last sample runs
    straight on into its first. Returns the seam check: the level jump across the seam vs the bed's own frame-to-frame jumps."""
    import numpy as np
    x = _pcm(raw, sr)
    a, n, xf = int(LOOP_HEAD * sr), int(LOOP_S * sr), int(LOOP_XF * sr)
    if len(x) < a + n + xf:  # shorter than asked: keep what there is, no intro skip
        a = max(0, len(x) - n - xf)
        n = min(n, len(x) - a - xf)
    y = x[a:a + n].copy()
    t = np.linspace(0, np.pi / 2, xf)[:, None]
    y[:xf] = x[a:a + xf] * np.sin(t) + x[a + n:a + n + xf] * np.cos(t)
    _write(out, y, sr)
    # seam check on 50 ms RMS frames: the jump from the last frame to the first, against the bed's typical jump
    f = int(0.05 * sr)
    z = _pcm(out, sr).mean(1)
    rms = np.sqrt(np.convolve(z ** 2, np.ones(f) / f, "valid")[::f] + 1e-12)
    db = 20 * np.log10(rms)
    jumps = np.abs(np.diff(db))
    seam = float(abs(db[0] - db[-1]))
    return {"loop_seconds": round(len(z) / sr, 2), "seam_jump_db": round(seam, 2), "typical_jump_db": round(float(np.percentile(jumps, 95)), 2),
            "seam_ok": seam <= max(3.0, float(np.percentile(jumps, 95))), "level_spread_db": round(float(np.percentile(db, 95) - np.percentile(db, 10)), 1)}


def kit(outdir: str, only: str = "") -> int:
    O = Path(outdir)
    O.mkdir(parents=True, exist_ok=True)
    start, acc = used()
    lines = [f"ElevenLabs plan: {acc['plan']} · commercial use: {'yes' if acc['commercial_use'] else 'NO'} · "
             f"{acc['characters_left']} credits left before the kit"]
    rows = []
    jobs = [j for j in KIT if not only or j[0] in only.split(",")]
    for stem, prompt, sec, what in jobs:
        try:
            out = O / f"{stem}.mp3"
            src = O / f"{stem}_raw.mp3" if what == "bed" else out
            m = make("music", src, prompt, sec)
            if what == "bed":
                m.update(loop(src, out), file=out.name, raw_file=src.name, loop_from_s=LOOP_HEAD, loop_crossfade_s=LOOP_XF)
                m.update({k: v for k, v in probe(out).items()})
                Path(str(out) + ".json").write_text(json.dumps(m, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
            rows.append(m)
            extra = f", loop {m['loop_seconds']} s, seam jump {m['seam_jump_db']} dB (typical {m['typical_jump_db']}) {'OK' if m['seam_ok'] else 'CHECK'}" if what == "bed" else ""
            lines.append(f"{stem}: {m['seconds']} s (asked {sec:g}), peak {m['peak_db']} dB, {m['credits_used']} credits{extra}"
                         f" · vocals heard: {m.get('vocals_heard') or 'none'}")
        except PermissionMissing as e:
            lines.append(f"{stem}: NOT MADE — {e}")
        except Exception as e:  # noqa: BLE001
            lines.append(f"{stem}: FAILED — {e}")
    end, acc2 = used()
    lines.append(f"Credits used by the kit: {max(0, end - start)} ({acc2['characters_left']} left)")
    (O / "kit.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (O / "kit.json").write_text(json.dumps({"rows": rows, "credits_used": max(0, end - start), "credits_left": acc2["characters_left"]}, indent=1, ensure_ascii=False))
    print("\n".join(lines), flush=True)
    return 0 if len(rows) == len(jobs) else 1


def main(argv: list[str]) -> int:
    if argv[0] == "kit":
        return kit(argv[1], argv[2] if len(argv) > 2 else "")
    if argv[0] == "test":
        return test(argv[1], argv[2] if len(argv) > 2 else "")
    kind, out, prompt = argv[0], Path(argv[1]), argv[2]
    sec = float(argv[3]) if len(argv) > 3 else (2.0 if kind == "sfx" else 30.0)
    print(json.dumps(make(kind, out, prompt, sec), indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
