"""Find what makes the narrator slow or hang: synthesise the episode's long beats IN ONE PROCESS, one after another
(exactly like the build), with a per-beat alarm, then run caption_words and build_plan on the result.
python tools/tts_probe.py episodes/<slug> [limit_seconds]"""
import signal
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class Timeout(Exception):
    pass


def _alarm(_s, _f):
    raise Timeout()


def main():
    from factory.script import load_episode
    from factory.tts import spoken_text, make_voice, caption_words, SAMPLE_RATE
    from factory.config import load_config
    ep = load_episode(sys.argv[1])
    cfg = load_config(ep.get("config"))
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 90
    V = make_voice(cfg, False, ep.get("voices"))
    signal.signal(signal.SIGALRM, _alarm)
    slow, voiced = [], []
    T0 = time.time()
    for b in ep["beats"]:
        text = spoken_text(b)
        t0 = time.time()
        signal.alarm(limit)
        try:
            audio, timings = V.synth(text, b.get("voice"))
            signal.alarm(0)
            dur = len(audio) / SAMPLE_RATE
            words = caption_words(b, timings, dur)
            voiced.append({"audio": audio, "sr": SAMPLE_RATE, "duration": dur, "words": words, "speaker": "narrator"})
            took = time.time() - t0
            line = f"{took:6.1f}s for {dur:5.1f}s audio  {b['id']}: {text[:60]}"
            if took > 20:
                slow.append(line)
        except Timeout:
            line = f"HANG >{limit}s  {b['id']}: {text}"
            slow.append(line)
            voiced.append(None)
        print(f"[{time.time() - T0:6.0f}] {line}", flush=True)
    msg = "%0A".join(slow) if slow else f"no slow beats ({time.time() - T0:.0f}s total)"
    print("::warning title=TTS synth::" + msg, flush=True)
    msg = ""
    for b in ep["beats"]:
        b["_music"] = b.get("music") or (ep.get("music") or {}).get(b.get("section") or "", (ep.get("music") or {}).get("_default", "noir"))
    if all(v is not None for v in voiced):
        import os
        os.environ.setdefault("FACTORY_SKIP_MANUAL", "placeholder")
        from factory.images import ensure_images
        from factory.archive import ensure_archive, ensure_clips
        from factory.script import image_prompts
        from factory.render import build_plan
        cache = Path(".cache/images") / ep["slug"]
        images = ensure_images(cfg, image_prompts(ep), cache, True, lambda *a: None)
        images.update(ensure_archive(ep, cfg, cache, lambda *a: None))
        ensure_clips(ep, cache, lambda *a: None)
        lookup = {b["id"]: b for b in ep["beats"]}
        signal.alarm(300)
        t0 = time.time()
        try:
            plan = build_plan(ep["beats"], voiced, images, cfg, (1920, 1080), "long", lookup)
            signal.alarm(0)
            msg += f"%0Abuild_plan OK in {time.time() - t0:.1f}s, total {plan.total:.1f}s"
            ids = [b["id"] for b in ep["beats"]]
            z1 = plan.beat_starts["z1"]
            msg += f"%0Aend screen z1..end = {plan.total - z1:.1f}s; z0..end = {plan.total - plan.beat_starts['z0']:.1f}s"
        except BaseException as exc:  # noqa: BLE001
            import traceback
            msg += f"%0Abuild_plan {'HANGS (>300s)' if isinstance(exc, Timeout) else 'FAILED'}"
            msg += "%0A" + "%0A".join(traceback.format_exc().splitlines()[-14:])
    print("::warning title=TTS probe::" + msg)


if __name__ == "__main__":
    try:
        main()
    except BaseException:  # noqa: BLE001
        import traceback
        print("::error title=TTS probe crashed::" + "%0A".join(traceback.format_exc().splitlines()[-14:]))
        raise
