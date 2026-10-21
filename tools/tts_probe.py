"""Find a beat that makes the narrator voice slow or hang: synthesise every long beat of an episode one by one,
each in a child process with a time limit, and print the seconds per beat.
python tools/tts_probe.py episodes/<slug> [limit_seconds]"""
import json
import multiprocessing as mp
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


V = None  # loaded once in the parent; forked children inherit it


def _one(text, q):
    t0 = time.time()
    audio, _ = V.synth(text, None)
    q.put((time.time() - t0, len(audio) / 24000))


def main():
    global V
    from factory.script import load_episode
    from factory.tts import spoken_text, make_voice
    from factory.config import load_config
    ep = load_episode(sys.argv[1])
    V = make_voice(load_config(ep.get("config")), False, ep.get("voices"))
    V.synth("Warm up.", None)
    mp.set_start_method("fork")
    limit = float(sys.argv[2]) if len(sys.argv) > 2 else 90
    rows = []
    for b in ep["beats"]:
        text = spoken_text(b)
        q = mp.Queue()
        p = mp.Process(target=_one, args=(text, q))
        t0 = time.time()
        p.start()
        p.join(limit)
        if p.is_alive():
            p.terminate()
            rows.append(f"HANG >{limit:.0f}s  {b['id']}: {text}")
        else:
            took, dur = q.get() if not q.empty() else (time.time() - t0, 0)
            rows.append(f"{took:6.1f}s for {dur:5.1f}s audio  {b['id']}: {text[:70]}")
        print(rows[-1], flush=True)
    slow = [r for r in rows if r.startswith("HANG") or float(r.split("s for")[0]) > 20]
    print("::warning title=TTS probe::" + ("%0A".join(slow) if slow else "no slow beats"))


if __name__ == "__main__":
    main()
