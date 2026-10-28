"""Scan the narration for stutter and judder (Klot r78 G4): every distinct line of the long video and the Shorts is
synthesised exactly like the build (Kokoro, the episode's 'say' and 'pause_at'), then
  - transcribed back with faster-whisper (word timestamps): repeated words/syllables, missing or extra words;
  - checked at every join: Kokoro's own chunk joins inside a line and the silence inserted by 'pause_at'
    (level jump, click = sample step, energy right at the cut = a cut-off word or a double onset);
  - level per line (a line much louder or quieter than the rest reads as a jump at the cut).
python tools/tts_scan.py episodes/<slug> out_dir    -> out_dir/scan.md, scan.json, wav/<id>.wav"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

NUMW = {"0": "zero", "1": "one", "2": "two", "3": "three", "4": "four", "5": "five", "6": "six", "7": "seven", "8": "eight",
        "9": "nine"}


def norm(w: str) -> str:
    w = w.lower().replace("’", "'")
    w = re.sub(r"[^a-z0-9'%$£.]", "", w)
    return w.strip(".'")


def rms_db(x):
    return 20 * np.log10(np.sqrt(np.mean(x.astype(np.float64) ** 2)) + 1e-9)


def join_check(audio, sr, t, label):
    """Energy and continuity around a join at t seconds."""
    i = int(t * sr)
    w = int(0.04 * sr)
    a, b = audio[max(0, i - w):i], audio[i:i + w]
    step = float(abs(audio[min(len(audio) - 1, i)] - audio[max(0, i - 1)])) if 0 < i < len(audio) else 0.0
    ea, eb = rms_db(a) if len(a) else -120, rms_db(b) if len(b) else -120
    flags = []
    if step > 0.05:
        flags.append(f"click (sample step {step:.2f})")
    if max(ea, eb) > -32:
        flags.append(f"speech energy at the cut ({ea:.0f} / {eb:.0f} dBFS)")
    return {"t": round(t, 3), "kind": label, "before_db": round(ea, 1), "after_db": round(eb, 1), "flags": flags}


def main():
    from factory.config import load_config
    from factory.render import _with_pause
    from factory.script import load_episode
    from factory.tts import SAMPLE_RATE, _pipeline, caption_words, spoken_text
    import soundfile as sf

    ep = load_episode(sys.argv[1])
    out = Path(sys.argv[2])
    (out / "wav").mkdir(parents=True, exist_ok=True)
    cfg = load_config(ep.get("config"))
    vc = cfg["voice"]
    pipe = _pipeline(vc.get("lang_code", "a"))
    lines, seen = [], {}
    for b in ep["beats"]:
        lines.append(("long", b))
    for sh in ep.get("shorts") or []:
        for b in sh["beats"]:
            lines.append((sh["id"], b))
    from faster_whisper import WhisperModel
    asr = WhisperModel("small.en", device="cpu", compute_type="int8")
    report = []
    for where, b in lines:
        text = spoken_text(b)
        key = (text, json.dumps(b.get("pause_at"), sort_keys=True))
        if key in seen:
            seen[key]["also"].append(f"{where}:{b['id']}")
            continue
        chunks, joins, toks, off = [], [], [], 0.0
        for r in pipe(text, voice=vc.get("voice", "am_michael"), speed=float(vc.get("speed", 1.0)), split_pattern=r"\n+"):
            a = getattr(r, "audio", None)
            if a is None:
                continue
            a = (a.detach().cpu().numpy() if hasattr(a, "detach") else np.asarray(a)).astype(np.float32).reshape(-1)
            if chunks:
                joins.append(off)
            for tk in getattr(r, "tokens", None) or []:
                if getattr(tk, "start_ts", None) is not None and re.search(r"\w", tk.text or ""):
                    toks.append((tk.text, off + float(tk.start_ts), off + float(tk.end_ts)))
            chunks.append(a)
            off += len(a) / SAMPLE_RATE
        audio = np.concatenate(chunks)
        v = {"audio": audio, "sr": SAMPLE_RATE, "duration": len(audio) / SAMPLE_RATE,
             "words": caption_words(b, toks, len(audio) / SAMPLE_RATE), "speaker": "narrator"}
        checks = [join_check(audio, SAMPLE_RATE, t, "kokoro chunk join") for t in joins]
        pa = b.get("pause_at")
        if pa:
            from factory.render import word_time
            w0 = word_time(v["words"], pa["word"])
            if w0 is not None:  # where r78 cut (word start - 30 ms, no fade)
                checks.append(join_check(audio, SAMPLE_RATE, w0 - 0.03, f"r78 pause cut '{pa['word']}'"))
            v2, wt = _with_pause(v, pa["word"], float(pa.get("sec", 1.2)))
            if wt is not None:
                cut = wt - float(pa.get("sec", 1.2))
                checks.append(join_check(v2["audio"], SAMPLE_RATE, cut - 0.001, f"pause_at '{pa['word']}' (before the silence)"))
                checks.append(join_check(v2["audio"], SAMPLE_RATE, wt + 0.001, f"pause_at '{pa['word']}' (after the silence)"))
            v = v2
        audio = v["audio"]
        bid = f"{where}_{b['id']}" if where != "long" else b["id"]
        sf.write(out / "wav" / f"{bid}.wav", audio, SAMPLE_RATE)
        segs, _ = asr.transcribe(audio, language="en", word_timestamps=True, beam_size=5, condition_on_previous_text=False)
        heard = [(w.word.strip(), round(w.start, 2), round(w.end, 2)) for s in segs for w in (s.words or [])]
        hn = [norm(w) for w, _, _ in heard]
        repeats = [f"'{heard[i][0]}' x2 at {heard[i][1]:.2f}s" for i in range(1, len(hn)) if hn[i] and hn[i] == hn[i - 1]
                   and not re.match(r"^\d", hn[i])]
        expected = [norm(w) for w in text.split() if norm(w)]
        import difflib
        sm = difflib.SequenceMatcher(a=expected, b=hn, autojunk=False)
        diffs = []
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op != "equal":
                diffs.append(f"{op}: said {' '.join(expected[i1:i2]) or '-'} | heard {' '.join(hn[j1:j2]) or '-'}"
                             + (f" @ {heard[j1][1]:.2f}s" if j1 < len(heard) else ""))
        act = np.abs(audio) > 0.01
        lvl = rms_db(audio[act]) if act.any() else -120
        lead = float(np.argmax(act) / SAMPLE_RATE) if act.any() else 0
        tail = float((len(act) - np.argmax(act[::-1])) / SAMPLE_RATE) if act.any() else 0
        endcut = rms_db(audio[-int(0.03 * SAMPLE_RATE):]) > -35
        rec = {"id": bid, "where": where, "text": text, "dur": round(len(audio) / SAMPLE_RATE, 2), "chunks": len(chunks),
               "level_db": round(lvl, 1), "speech_from": round(lead, 2), "speech_to": round(tail, 2),
               "ends_in_speech": bool(endcut), "checks": checks, "repeats": repeats, "diffs": diffs,
               "heard": " ".join(w for w, _, _ in heard), "also": []}
        seen[key] = rec
        report.append(rec)
        print(f"{bid}: {len(chunks)} chunk(s), {lvl:.1f} dB, repeats {len(repeats)}, diffs {len(diffs)}", flush=True)
    med = float(np.median([r["level_db"] for r in report]))
    md = [f"# TTS scan {ep['slug']}  (median level {med:.1f} dBFS)", ""]
    for r in report:
        flags = []
        if abs(r["level_db"] - med) > 2.0:
            flags.append(f"level {r['level_db'] - med:+.1f} dB vs median")
        if r["ends_in_speech"]:
            flags.append("audio ends inside speech (cut-off)")
        for c in r["checks"]:
            for f in c["flags"]:
                flags.append(f"{c['kind']} @ {c['t']:.2f}s: {f}")
        flags += [f"repeat {x}" for x in r["repeats"]] + r["diffs"]
        r["flags"] = flags
        md.append(f"## {r['id']} ({r['dur']} s, {r['chunks']} chunk(s){', also ' + ', '.join(r['also']) if r['also'] else ''})")
        md.append(f"- text: {r['text']}")
        md.append(f"- heard: {r['heard']}")
        md += [f"- **{f}**" for f in flags] or ["- ok"]
        md.append("")
    (out / "scan.md").write_text("\n".join(md))
    (out / "scan.json").write_text(json.dumps(report, indent=1))
    print(f"{sum(1 for r in report if r['flags'])} of {len(report)} lines flagged")


if __name__ == "__main__":
    main()
