"""Build one episode: python -m factory build episodes/<slug> [--offline] [--out out/<slug>] [--only long|shorts]"""
from __future__ import annotations

import argparse
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


def log(msg: str) -> None:
    print(msg, flush=True)


def voice_beats(voice, beats: list[dict]) -> list[dict]:
    out = []
    for beat in beats:
        audio, timings = voice.synth(spoken_text(beat), beat.get("voice"))
        duration = len(audio) / SAMPLE_RATE
        out.append({"audio": audio, "sr": SAMPLE_RATE, "duration": duration,
                    "words": caption_words(beat, timings, duration), "speaker": beat.get("voice") or "narrator"})
    return out


def build(episode_path: str, out_dir: str | None, offline: bool, only: str | None, preview: bool = False) -> Path:
    started = time.time()
    episode = load_episode(episode_path)
    cfg = load_config(episode.get("config"))
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
    if thumb_spec.get("prompt") and not any((ep_dir0 / f"thumbnail.{e}").exists() for e in ("png", "jpg")):
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
    voice = make_voice(cfg, offline, episode.get("voices"))
    beat_lookup = {b["id"]: b for b in episode["beats"]}
    long_voiced = voice_beats(voice, episode["beats"])

    plan_long = build_plan(episode["beats"], long_voiced, images, cfg,
                           (cfg["video"]["long"]["width"], cfg["video"]["long"]["height"]), "long", beat_lookup)
    target = float(cfg["video"].get("long_min_seconds", 0))
    if target and plan_long.total < target:
        # stretch breathing room between beats (max +0.45 s each) to reach the mid-roll threshold
        extra = min(0.45, (target - plan_long.total) / max(1, len(episode["beats"])) + 0.01)
        plan_long = build_plan(episode["beats"], long_voiced, images, cfg,
                               (cfg["video"]["long"]["width"], cfg["video"]["long"]["height"]), "long", beat_lookup, extra)
        log(f"Stretched pauses by +{extra:.2f}s per beat to reach {target:.0f}s")
    log(f"Long video: {plan_long.total / 60:.2f} min, {len(plan_long.shots)} shots")
    if only in (None, "long"):
        render(plan_long, cfg, out / "long.mp4", out / "long.wav", log)
        (out / "long.wav").unlink(missing_ok=True)

    shorts_info = []
    size_short = (cfg["video"]["short"]["width"], cfg["video"]["short"]["height"])
    for short in episode.get("shorts") or []:
        voiced = voice_beats(voice, short["beats"])
        plan = build_plan(short["beats"], voiced, images, cfg, size_short, "short", beat_lookup)
        name = f"short_{short['id']}.mp4"
        log(f"Short {short['id']}: {plan.total:.1f}s")
        if plan.total > 60:
            log(f"  warning: {plan.total:.0f}s is longer than 60 s")
        if only in (None, "shorts"):
            render(plan, cfg, out / name, out / f"short_{short['id']}.wav", log)
            (out / f"short_{short['id']}.wav").unlink(missing_ok=True)
        from .meta import music_credits
        cue = short["beats"][0].get("_music") if short["beats"] else None
        shorts_info.append({"id": short["id"], "title": short.get("title", ""), "file": name, "duration_seconds": round(plan.total, 1),
                            "music_credit": "\n".join(music_credits(episode, {cue} if cue else set()))})

    thumb = episode.get("thumbnail") or {}
    ep_dir = Path(episode_path) if Path(episode_path).is_dir() else Path(episode_path).parent
    custom = next((p for p in (ep_dir / "thumbnail.png", ep_dir / "thumbnail.jpg") if p.exists()), None)
    if custom:  # hand-made cinematic thumbnail (e.g. from ChatGPT): use as is, fitted to 1280x720 JPEG
        from PIL import Image, ImageOps
        ImageOps.fit(Image.open(custom).convert("RGB"), (1280, 720), Image.LANCZOS).save(out / "thumbnail.jpg", quality=92)
        write_meta(out, episode, plan_long, shorts_info)
        log(f"Done in {(time.time() - started) / 60:.1f} min -> {out}")
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
        build(args.episode, args.out, args.offline, args.only, args.preview)
        return 0
    except ScriptError as exc:
        print(f"Script error:\n{exc}", file=sys.stderr)
        return 2
