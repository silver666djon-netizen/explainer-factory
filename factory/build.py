"""Build one episode: python -m factory build episodes/<slug> [--offline] [--out out/<slug>] [--only long|shorts]"""
from __future__ import annotations

import argparse
import os
import json
import re
import sys
import time
from pathlib import Path

import numpy as np

from .config import ROOT, load_config
from .images import ensure_images, ensure_photos, is_archive_photo
from .meta import thumbnail, write_meta
from .render import build_plan, render
from .script import ScriptError, image_prompts, load_episode, photo_sources
from .tts import SAMPLE_RATE, caption_words, make_voice, spoken_text


_T0 = __import__("time").time()


def log(msg: str) -> None:
    t = __import__("time").time() - _T0
    print(f"[{int(t // 60):02d}:{int(t % 60):02d}] {msg}", flush=True)  # elapsed time: a slow step shows in the log


def voice_beats(voice, beats: list[dict]) -> list[dict]:
    out = []
    for beat in beats:
        audio, timings = voice.synth(spoken_text(beat), beat.get("voice"))
        duration = len(audio) / SAMPLE_RATE
        out.append({"audio": audio, "sr": SAMPLE_RATE, "duration": duration,
                    "words": caption_words(beat, timings, duration), "speaker": beat.get("voice") or "narrator"})
    return out


def build(episode_path: str, out_dir: str | None, offline: bool, only: str | None, preview: bool = False,
          upto: str | None = None) -> Path:
    started = time.time()
    episode = load_episode(episode_path)
    cfg = load_config(episode.get("config"))
    if preview:  # previews may run before every hand-made frame (rule 19) has arrived: those show a marked placeholder
        import os as _os
        _os.environ.setdefault("FACTORY_SKIP_MANUAL", "placeholder")
    if preview:  # fast draft for QC: half size, 15 fps — same layout, timing and sound
        vc = cfg["video"]
        vc["fps"] = 15
        vc["long"] = {"width": vc["long"]["width"] // 2, "height": vc["long"]["height"] // 2}
        vc["short"] = {"width": vc["short"]["width"] // 2, "height": vc["short"]["height"] // 2}
        vc["x264_preset"], vc["crf"] = "ultrafast", 30
        vc["crossfade_frames"] = max(2, int(vc.get("crossfade_frames", 8)) // 2)
    slug = episode["slug"]
    out = Path(out_dir) if out_dir else ROOT / "out" / slug
    out.mkdir(parents=True, exist_ok=True)
    log(f"Episode: {episode['title']}  ({len(episode['beats'])} beats, {len(episode.get('shorts') or [])} shorts)")

    from .stock import resolve_stock, stock_offline
    if not offline:
        resolve_stock(episode, log)
    else:
        stock_offline(episode)
    prompts = image_prompts(episode)
    thumb_spec = episode.get("thumbnail") or {}
    ep_dir0 = Path(episode_path) if Path(episode_path).is_dir() else Path(episode_path).parent
    if cfg.get("make_thumbnail", True) and thumb_spec.get("prompt") and not any((ep_dir0 / f"thumbnail.{e}").exists() for e in ("png", "jpg")):
        prompts["thumbnail"] = {"prompt": thumb_spec["prompt"], "style": thumb_spec.get("style", "ad")}
    cache = ROOT / ".cache" / ("images-offline" if offline else "images") / slug
    images = ensure_images(cfg, prompts, cache, offline, log)
    from .archive import ensure_archive, ensure_clips
    images.update(ensure_archive(episode, cfg, cache, log))
    ensure_clips(episode, cache, log)
    photos = photo_sources(episode)
    if photos:
        got = ensure_photos(cfg, photos, cache, offline, log)
        images.update(got)
        credits = [f"Archive photo: {spec['credit']}" for key, spec in photos.items() if is_archive_photo(got[key])]
        episode["sources"] = list(episode.get("sources") or []) + credits

    try:  # parallax depth for frames that have none yet (e.g. hand-made ones added after the storyboard)
        from .depth import ensure_depth
        if not offline:
            ensure_depth(list(images.values()), log)
    except Exception as exc:  # noqa: BLE001
        log(f"depth skipped: {exc}")

    # music: one mood per chapter (episode "music": {section: cue}); Shorts take their own "music" or the default
    mus = episode.get("music") or {}
    default_cue = mus.get("_default", "noir")
    for beat in episode["beats"]:
        beat["_music"] = beat.get("music") or mus.get(beat.get("section") or "", default_cue)
    by_id = {b["id"]: b for b in episode["beats"]}
    for short in episode.get("shorts") or []:
        # a Short keeps one mood: the chapter most of its pictures come from (or its own "music")
        votes: dict[str, int] = {}
        for beat in short["beats"]:
            src = by_id.get((beat.get("visual") or {}).get("beat", "")) or by_id.get(beat.get("id", ""))
            if src:
                votes[src["_music"]] = votes.get(src["_music"], 0) + 1
        cue = short.get("music") or (max(votes, key=votes.get) if votes else mus.get("_shorts") or default_cue)
        for beat in short["beats"]:
            beat["_music"] = cue
        if short.get("hook") and short["beats"]:  # Shorts have no thumbnail: frame 0 must carry the hook
            short["beats"][0]["on_screen"] = short["hook"]
            short["beats"][0]["_hook"] = True

    log("Narration…")
    if episode.get("_voice"):  # language version: its own narrator (e.g. edge-tts ru-RU-DmitryNeural)
        cfg["voice"] = {**cfg["voice"], **episode["_voice"]}
    voice = make_voice(cfg, offline, episode.get("voices"))
    beat_lookup = {b["id"]: b for b in episode["beats"]}
    long_voiced = voice_beats(voice, episode["beats"])

    plan_long = build_plan(episode["beats"], long_voiced, images, cfg,
                           (cfg["video"]["long"]["width"], cfg["video"]["long"]["height"]), "long", beat_lookup)
    target = float(cfg["video"].get("long_min_seconds", 0))
    extra = 0.0
    if target and plan_long.total < target:
        # stretch breathing room between beats (max +0.45 s each) to reach the mid-roll threshold
        extra = min(0.45, (target - plan_long.total) / max(1, len(episode["beats"])) + 0.01)
        plan_long = build_plan(episode["beats"], long_voiced, images, cfg,
                               (cfg["video"]["long"]["width"], cfg["video"]["long"]["height"]), "long", beat_lookup, extra)
        log(f"Stretched pauses by +{extra:.2f}s per beat to reach {target:.0f}s")
    log(f"Long video: {plan_long.total / 60:.2f} min, {len(plan_long.shots)} shots")
    from .render import still_runs
    lim = float(cfg["video"].get("max_still_seconds", 8.0))
    warns = []
    for a, b, name in still_runs(plan_long, lim):
        warns.append({"start": a, "end": b, "picture": name})
        log(f"WARNING max-still: {name} on screen {b - a:.1f}s ({a // 60:.0f}:{a % 60:04.1f}–{b // 60:.0f}:{b % 60:04.1f}) > {lim:.0f}s — add an angle, insert or card")
    import json as _json
    ids = [b["id"] for b in episode["beats"]]
    (out / "timings.json").write_text(_json.dumps({  # real narration timings: Shorts are cut against these
        "total": plan_long.total, "max_still_warnings": warns,
        "beats": [{"id": bid, "start": plan_long.beat_starts.get(bid), "voice": round(v["duration"], 3),
                   "text": b["text"], "words": [[w, round(s0, 3), round(e0, 3)] for w, s0, e0 in v["words"]]}
                  for bid, b, v in zip(ids, episode["beats"], long_voiced)]}, indent=1))
    if upto:  # preview of one part: "cf1" = opening up to and including cf1; "z0..z5" = from z0 to z5 (end screen)
        k0, k1 = (upto.split("..", 1) if ".." in upto else (ids[0], upto))
        a, k = ids.index(k0), ids.index(k1) + 1
        sub = episode["beats"][a:k]
        plan_long = build_plan(sub, long_voiced[a:k], images, cfg,
                               (cfg["video"]["long"]["width"], cfg["video"]["long"]["height"]), "long", beat_lookup,
                               extra)
        log(f"Preview cut {k0}..{k1}: {plan_long.total:.1f}s")
        render(plan_long, cfg, out / "long.mp4", out / "long.wav", log)
        (out / "long.wav").unlink(missing_ok=True)
        return out
    if only in (None, "long"):
        render(plan_long, cfg, out / "long.mp4", out / "long.wav", log)
        (out / "long.wav").unlink(missing_ok=True)
    from . import qc as _qc
    _qc.STT_KNOWN = [(k["script"], k["heard"]) for k in episode.get("stt_known") or []]
    qc_res = {}
    qc_plans = {"long": plan_long}
    # language review copy (Klot r90 RU): the narration is not the English script and Shorts may run long
    qc_skip = ("stt_diff", "text_lint", "shorts_length") if episode.get("lang") else ()
    if only in (None, "long"):  # Klot r84 part C: release-blocking checks on the real plan (real narration)
        qc_res["long"] = _qc.run_all(plan_long, cfg, episode["beats"], qc_skip)
        log("QC long: " + ", ".join(f"{c} {'ok' if not r['fails'] else 'FAIL ' + str(len(r['fails']))}" for c, r in qc_res["long"].items()))

    short_timings = []
    shorts_info = []
    size_short = (cfg["video"]["short"]["width"], cfg["video"]["short"]["height"])
    for short in episode.get("shorts") or []:
        voiced = voice_beats(voice, short["beats"])
        plan = build_plan(short["beats"], voiced, images, cfg, size_short, "short", beat_lookup)
        short_timings += [{"id": b["id"], "start": plan.beat_starts.get(b["id"]), "voice": round(v["duration"], 3), "text": b["text"],
                           "words": [[w, round(s0, 3), round(e0, 3)] for w, s0, e0 in v["words"]]}
                          for b, v in zip(short["beats"], voiced)]
        name = f"short_{short['id']}.mp4"
        log(f"Short {short['id']}: {plan.total:.1f}s")
        for a, b, nm in still_runs(plan, lim):
            log(f"WARNING max-still: short {short['id']} {nm} on screen {b - a:.1f}s at {a:.1f}s > {lim:.0f}s")
        if plan.total > 60:
            log(f"  warning: {plan.total:.0f}s is longer than 60 s")
        if only in (None, "shorts"):
            render(plan, cfg, out / name, out / f"short_{short['id']}.wav", log)
            (out / f"short_{short['id']}.wav").unlink(missing_ok=True)
            qc_res[short["id"]] = _qc.run_all(plan, cfg, short["beats"], qc_skip)
            if len(qc_plans) < 2:
                qc_plans[short["id"]] = plan
            log(f"QC {short['id']}: " + ", ".join(f"{c} {'ok' if not r['fails'] else 'FAIL ' + str(len(r['fails']))}" for c, r in qc_res[short["id"]].items()))
        from .meta import music_credits
        cue = short["beats"][0].get("_music") if short["beats"] else None
        shorts_info.append({"id": short["id"], "title": short.get("title", ""), "file": name, "duration_seconds": round(plan.total, 1),
                            "music_credit": "\n".join(music_credits(episode, {cue} if cue else set()))})

    if short_timings and (out / "timings.json").exists():  # the Shorts' own lines too (mark audit / stt spans)
        tj = json.loads((out / "timings.json").read_text())
        tj["short_beats"] = short_timings
        (out / "timings.json").write_text(json.dumps(tj, indent=1))
    if qc_res:
        st_rows = _qc.selftest(qc_plans, cfg, {})  # R40: every check must FAIL on its planted bug
        st_ok = _qc.selftest_ok(st_rows)
        (out / "qc_checks.md").write_text("# Release checks (CI build)\n\n" + _qc.table(qc_res) + "\n\n## Check self-test (R40)\n\n"
                                         + _qc.selftest_table(st_rows) + "\n")
        (out / "qc_checks.json").write_text(json.dumps({**qc_res, "_selftest": st_rows}, indent=1))
        log("QC checks: " + ("FAIL - release blocked" if _qc.failed(qc_res) or not st_ok else "all PASS")
            + f" · self-test {'ok' if st_ok else 'BLIND CHECK'}")
    if episode.get("lang"):  # language version (review copy): no thumbnail; files carry the language code
        write_meta(out, episode, plan_long, shorts_info)
        code = episode["lang"]
        for name in ("long.mp4", "long.srt"):
            if (out / name).exists():
                (out / name).rename(out / name.replace("long.", f"long_{code}."))
        meta_p = out / "metadata.json"
        meta = json.loads(meta_p.read_text(encoding="utf-8"))
        meta["lang"] = code
        meta_p.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        log(f"Done in {(time.time() - started) / 60:.1f} min -> {out} (language version: {code})")
        return out
    thumb = episode.get("thumbnail") or {}
    ep_dir = Path(episode_path) if Path(episode_path).is_dir() else Path(episode_path).parent
    custom = next((p for p in (ep_dir / "thumbnail.png", ep_dir / "thumbnail.jpg") if p.exists()), None)
    if custom:  # hand-made cinematic thumbnail (e.g. from ChatGPT): use as is, fitted to 1280x720 JPEG
        from PIL import Image, ImageOps
        ImageOps.fit(Image.open(custom).convert("RGB"), (1280, 720), Image.LANCZOS).save(out / "thumbnail.jpg", quality=92)
        write_meta(out, episode, plan_long, shorts_info)
        log(f"Done in {(time.time() - started) / 60:.1f} min -> {out}")
        return out
    if not cfg.get("make_thumbnail", True):  # channel makes its thumbnails separately
        write_meta(out, episode, plan_long, shorts_info)
        log(f"Done in {(time.time() - started) / 60:.1f} min -> {out} (no thumbnail: made separately)")
        return out
    first_image = next((b["id"] for b in episode["beats"] if b["visual"]["type"] in ("image", "photo", "mugshot")), None)
    if "thumbnail" in images:
        thumb_img = images["thumbnail"]
    elif thumb.get("beat") or first_image:
        thumb_img = images[thumb.get("beat") or first_image]
    else:  # no pictures at all: use a frame from the video
        import subprocess
        thumb_img = out / "thumb_src.png"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(plan_long.total * 0.3), "-i", str(out / "long.mp4"),
                        "-frames:v", "1", str(thumb_img)], check=True)
    thumbnail(cfg, thumb_img, thumb.get("text") or episode["title"], out / "thumbnail.jpg", circle=thumb.get("circle", True))
    write_meta(out, episode, plan_long, shorts_info)
    log(f"Done in {(time.time() - started) / 60:.1f} min -> {out}")
    return out


def lint(ep: dict) -> list[str]:
    """Retention + correctness warnings (not errors)."""
    warns: list[str] = []
    wpm = 150 / 60
    t = 0.0
    changes_hook = 0
    for b in ep["beats"]:
        dur = max(1.0, len(b["text"].split()) / wpm)
        vt = b["visual"]["type"]
        if t < 30:
            if vt in ("image", "reuse", "photo") and not b["visual"].get("marks"):
                changes_hook += max(len(b["visual"].get("prompts") or [1]), int(np.ceil(dur / 1.8)))
            else:
                changes_hook += 1
            changes_hook += bool(b.get("on_screen")) + bool(b.get("bubble")) + len(b.get("punch") or [])
        if dur > 10:
            warns.append(f"beat {b['id']}: ~{dur:.0f}s of narration — split it (one idea per beat)")
        if re.search(r"[0-9$%£€]", b["text"]) and not b.get("say"):
            warns.append(f"beat {b['id']}: digits/symbols in text without 'say' — the narrator may misread them")
        t += dur
    if changes_hook < 14:
        warns.append(f"first 30 s: only ~{changes_hook} visual changes — aim for 15+ (cuts, labels, punch-ins, marks)")
    minutes = t / 60
    marks = sum(len(b["visual"].get("marks") or []) for b in ep["beats"])
    jokes = sum(1 for b in ep["beats"] if b.get("bubble") or b["visual"].get("ad") or b["visual"].get("style") == "comic")
    docs = sum(1 for b in ep["beats"] if b["visual"]["type"] == "doc")
    if marks < max(1, int(minutes)):
        warns.append(f"only {marks} red-marker marks for ~{minutes:.1f} min — the signature look wants ~1–3 per minute")
    if jokes < max(1, int(minutes / 1.5)):
        warns.append(f"only {jokes} humour beats (comic/bubble/ad gag) — aim for one every 1–2 minutes")
    if not ep.get("sources"):
        warns.append("no sources listed")
    elif docs == 0:
        warns.append("no 'doc' highlighter beat — show at least one study on screen")
    for sh in ep.get("shorts") or []:
        st = sum(max(1.0, len(b["text"].split()) / wpm) for b in sh["beats"])
        if st > 50:
            warns.append(f"short {sh['id']}: ~{st:.0f}s — keep Shorts under 45 s")
    return warns


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m factory")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="render an episode")
    b.add_argument("episode", help="episodes/<slug> folder or script.json")
    b.add_argument("--out")
    b.add_argument("--offline", action="store_true", help="placeholder images and voice (no APIs)")
    b.add_argument("--only", choices=["long", "shorts"])
    b.add_argument("--preview", action="store_true", help="fast half-size 15 fps draft for checking")
    b.add_argument("--upto", help="render only the beats up to and including this id (opening preview)")
    b.add_argument("--lang", help="language version from episodes/<slug>/lang/<code>.json (long + Shorts), e.g. ru")
    c = sub.add_parser("check", help="validate a script without rendering")
    c.add_argument("episode")
    args = ap.parse_args(argv)
    try:
        if args.cmd == "check":
            ep = load_episode(args.episode)
            n_img = len(image_prompts(ep))
            words = sum(len(x["text"].split()) for x in ep["beats"])
            print(json.dumps({"ok": True, "beats": len(ep["beats"]), "images": n_img,
                              "approx_minutes": round(words / 150, 1), "shorts": len(ep.get("shorts") or []),
                              "warnings": lint(ep)}, indent=2, ensure_ascii=False))
            return 0
        if getattr(args, "lang", None):
            os.environ["FACTORY_LANG"] = args.lang
        build(args.episode, args.out, args.offline, args.only, args.preview, args.upto)
        return 0
    except ScriptError as exc:
        print(f"Script error:\n{exc}", file=sys.stderr)
        return 2
