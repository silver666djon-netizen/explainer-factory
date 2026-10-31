"""Ep.4 v2 voice sample D: ElevenLabs v3 (eleven_v3) with sparse audio tags, two British male narrator voices (D1, D2).
Same lines, same designed pauses, same bed, brass hit + one real second of silence as samples A/B/C (tools/voice_samples.py).
Also: the account report (plan, characters left, commercial use, characters per episode) and the pronunciation dictionary
("Live Nation" read "lyve"), used in every ElevenLabs render. The key comes from ELEVENLABS_API_KEY and is never printed.
python tools/voice_d.py <out dir>"""
from __future__ import annotations

import json
import math
import os
import re
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import voice_samples as vs  # noqa: E402

API = "https://api.elevenlabs.io"
MODEL = "eleven_v3"
DICT_NAME = "coinsense-names"
RULES = [{"type": "alias", "string_to_replace": "Live Nation", "alias": "Lyve Nation"}]
PROBE = "In September 2025, the FTC sued Live Nation and Ticketmaster. Live Nation denies it."
# the cold open with sparse tags: acting, not effects (index-aligned with vs.LINES)
TAGGED = [
    "[low] This is the story of a robbery that took seven minutes.",
    "No masks. No getaway car. Nobody even raised their voice.",
    "The victim typed in his own card number, ticked the box... [dry] and said thank you.",
    "His name is Larry. [smiling] Larry is made up. [serious] The fees are not.",
    "And before you feel sorry for him, know this... you've done it too.",
    "You found the cheaper ticket. You picked a seat. You typed in your card.",
    "Then the last screen showed a number you didn't expect... [slow] and you paid anyway.",
    "Why? Somebody spent years finding out exactly why. [whispers] And it wasn't you.",
    "Case file number four. The seven-minute heist.",
]
KEYWORDS = {"documentary": 4, "narrat": 3, "deep": 2, "low": 2, "calm": 1, "warm": 1, "authorit": 1, "storytell": 2,
            "mature": 1, "rich": 1, "gravel": 1, "measured": 1}


def H() -> dict:
    k = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not k:
        raise SystemExit("ELEVENLABS_API_KEY is empty in this run")
    return {"xi-api-key": k}


def get(path: str, **params):
    import requests
    for a in range(4):
        r = requests.get(API + path, headers=H(), params=params, timeout=60)
        if r.status_code == 200:
            return r.json()
        if r.status_code in (429, 500, 502, 503):
            time.sleep(4 + 4 * a)
            continue
        raise RuntimeError(f"GET {path}: {r.status_code} {r.text[:300]}")
    raise RuntimeError(f"GET {path}: gave up")


def post(path: str, body: dict, **params):
    import requests
    return requests.post(API + path, headers={**H(), "Content-Type": "application/json"}, params=params, json=body, timeout=240)


def account() -> dict:
    s = get("/v1/user/subscription")
    tier = s.get("tier", "?")
    used, limit = s.get("character_count", 0), s.get("character_limit", 0)
    reset = s.get("next_character_count_reset_unix")
    return {"plan": tier, "status": s.get("status"), "characters_used": used, "character_limit": limit,
            "characters_left": max(0, limit - used),
            "resets": time.strftime("%Y-%m-%d", time.gmtime(reset)) if reset else None,
            # ElevenLabs: the free plan is non-commercial (attribution required); every paid plan includes a commercial licence
            "commercial_use": tier not in ("free", "?"),
            "can_extend_character_limit": s.get("can_extend_character_limit"),
            "voice_slots_used": s.get("voice_slots_used"), "voice_limit": s.get("voice_limit")}


def dictionary() -> dict:
    """Reuse the dictionary if it exists (same rules), else create it. Returns the locator."""
    have = get("/v1/pronunciation-dictionaries", page_size=100).get("pronunciation_dictionaries", [])
    for d in have:
        if d.get("name") == DICT_NAME:
            return {"pronunciation_dictionary_id": d["id"], "version_id": d.get("latest_version_id")}
    r = post("/v1/pronunciation-dictionaries/add-from-rules", {"name": DICT_NAME, "rules": RULES,
                                                                "description": "CoinSense: names the voice must say our way"})
    if r.status_code != 200:
        raise RuntimeError(f"dictionary: {r.status_code} {r.text[:300]}")
    j = r.json()
    return {"pronunciation_dictionary_id": j["id"], "version_id": j["version_id"]}


def score(text: str) -> int:
    t = text.lower()
    return sum(w for k, w in KEYWORDS.items() if k in t)


def pick_voices() -> list[dict]:
    """D1: the best documentary/narration British male voice in the voice library (added to the account);
    D2: the best British male voice already in the account (premade = it can't be withdrawn by an owner)."""
    mine = get("/v2/voices", page_size=100).get("voices", [])
    acc = []
    for v in mine:
        lab = {k: str(x).lower() for k, x in (v.get("labels") or {}).items()}
        if "british" in lab.get("accent", "") and lab.get("gender") == "male":
            txt = " ".join([v.get("name", ""), v.get("description") or "", *lab.values()])
            acc.append({"voice_id": v["voice_id"], "name": v["name"], "source": f"your account ({v.get('category')})",
                        "about": (v.get("description") or ", ".join(f"{k}: {x}" for k, x in lab.items()))[:200],
                        "score": score(txt) + (2 if v.get("category") == "premade" else 0)})
    acc.sort(key=lambda x: -x["score"])
    lib = []
    for uc in ("narrative_story", "informative_educational"):
        try:
            got = get("/v1/shared-voices", page_size=50, gender="male", accent="british", language="en", use_cases=uc,
                      sort="trending").get("voices", [])
        except RuntimeError as e:
            print("library search:", e, flush=True)
            got = []
        for v in got:
            txt = " ".join(str(v.get(k) or "") for k in ("name", "description", "descriptive", "use_case", "age"))
            lib.append({"voice_id": v["voice_id"], "owner": v.get("public_owner_id"), "name": v.get("name"),
                        "source": "voice library", "about": (v.get("description") or "")[:200],
                        "notice_days": v.get("notice_period"), "uses": v.get("cloned_by_count") or 0,
                        "score": score(txt) + math.log10(1 + (v.get("cloned_by_count") or 0))})
    seen, libu = set(), []
    for v in sorted(lib, key=lambda x: -x["score"]):
        if v["voice_id"] not in seen:
            seen.add(v["voice_id"])
            libu.append(v)
    print("account British male voices:", [(v["name"], round(v["score"], 1)) for v in acc[:6]], flush=True)
    print("library candidates:", [(v["name"], round(v["score"], 1)) for v in libu[:8]], flush=True)
    picks = []
    if libu:
        v = libu[0]
        if v["voice_id"] not in {m["voice_id"] for m in mine}:
            r = post(f"/v1/voices/add/{v['owner']}/{v['voice_id']}", {"new_name": f"CS {v['name']}"[:40]})
            if r.status_code == 200:
                v["voice_id"] = r.json().get("voice_id", v["voice_id"])
            else:
                print("could not add library voice:", r.status_code, r.text[:200], flush=True)
                v = None
        if v:
            picks.append(v)
    for v in acc:
        if len(picks) == 2:
            break
        if v["voice_id"] not in {p["voice_id"] for p in picks}:
            picks.append(v)
    for v in libu[1:]:
        if len(picks) == 2:
            break
        picks.append(v)
    return picks[:2]


def tts(text: str, voice_id: str, loc: dict | None) -> tuple[np.ndarray, bool]:
    body = {"text": text, "model_id": MODEL, "voice_settings": {"stability": 0.5}}
    if loc:
        body["pronunciation_dictionary_locators"] = [loc]
    for a in range(5):
        r = post(f"/v1/text-to-speech/{voice_id}", body, output_format="pcm_24000")
        if r.status_code == 200:
            return np.frombuffer(r.content, np.int16).astype(np.float32) / 32768.0, bool(loc)
        if r.status_code == 400 and loc and "pronunciation" in r.text.lower():
            # the model refuses dictionaries: apply the same alias rules to the text instead
            print("dictionary refused by", MODEL, "-> alias applied in the text:", r.text[:160], flush=True)
            return tts(apply_alias(text), voice_id, None)[0], False
        if r.status_code in (429, 500, 502, 503):
            time.sleep(5 + 5 * a)
            continue
        raise RuntimeError(f"TTS {r.status_code} {r.text[:300]}")
    raise RuntimeError("TTS: gave up")


def apply_alias(text: str) -> str:
    for r in RULES:
        text = text.replace(r["string_to_replace"], r["alias"])
    return text


def untag(t: str) -> str:
    return re.sub(r"\[[^\]]*\]\s*", "", t)


def voice_lines(voice_id: str, loc: dict | None, log: dict) -> list[np.ndarray]:
    clips = []
    for tagged, (plain, *_rest) in zip(TAGGED, vs.LINES):
        assert vs._words(untag(tagged)) == vs._words(plain), tagged
        best = None
        for take in range(4):
            x, used = tts(tagged, voice_id, loc)
            log["dictionary_used"] = log.get("dictionary_used", True) and used
            heard = vs.hear(x)
            ratio = vs._match(plain, heard)
            log["takes"] = log.get("takes", 0) + 1
            if best is None or ratio > best[0]:
                best = (ratio, x)
            if ratio >= 0.97:
                break
            print(f"  retake: heard {heard[:100]!r} ({ratio:.0%})", flush=True)
        clips.append(vs.trim(best[1]))
    return clips


def episode_chars() -> dict:
    sys.path.insert(0, str(vs.ROOT / "episodes" / "0005-drip-pricing" / "v2"))
    import scenes
    en = sum(len(b[0]) for _, bs in scenes.ACTS for b in bs)
    ru = sum(len(b[1]) for _, bs in scenes.ACTS for b in bs)
    tags = sum(len(t) - len(untag(t)) for t in TAGGED) / sum(len(t) for t in TAGGED)
    return {"en_script": en, "ru_script": ru, "tag_share": round(tags, 3),
            # tags + about 25% retakes (this run's own retake rate is reported next to it)
            "en_per_episode": round(en * (1 + tags) * 1.25, -2), "ru_per_episode": round(ru * (1 + tags) * 1.25, -2)}


def main(out_dir: str) -> int:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rep = {"account_before": account()}
    print("account:", {k: v for k, v in rep["account_before"].items()}, flush=True)
    rep["episode_characters"] = episode_chars()
    loc = None
    try:
        loc = dictionary()
        rep["dictionary"] = {"name": DICT_NAME, "rules": RULES, "id": loc["pronunciation_dictionary_id"]}
    except Exception as e:  # noqa: BLE001
        rep["dictionary"] = {"error": str(e)[:300]}
    picks = pick_voices()
    rep["voices"] = picks
    old = out / "voice_samples.json"
    report = json.loads(old.read_text()) if old.exists() else {}
    ok = len(picks) == 2
    for i, v in enumerate(picks, 1):
        name = f"D{i}_eleven_{re.sub(r'[^a-z0-9]+', '', v['name'].lower())[:16]}"
        log = {}
        try:
            clips = voice_lines(v["voice_id"], loc, log)
            report[name] = {**vs.assemble(clips, out, name), "engine": f"ElevenLabs {MODEL}", "voice": v["name"],
                            "voice_source": v["source"], "takes": log.get("takes"), "lines": len(vs.LINES),
                            "dictionary": "on" if log.get("dictionary_used") else "alias in text",
                            "characters": sum(len(t) for t in TAGGED)}
            if i == 1:
                x, used = tts(PROBE, v["voice_id"], loc)
                vs.write_wav(out / "_probe.wav", x)
                import subprocess
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(out / "_probe.wav"), "-ar", "48000", "-c:a", "libmp3lame",
                                "-b:a", "192k", str(out / "cs_ep04v2_probe_live_nation_D1.mp3")], check=True)
                (out / "_probe.wav").unlink()
                rep["probe"] = {"file": "cs_ep04v2_probe_live_nation_D1.mp3", "text": PROBE, "heard": vs.hear(x),
                                "dictionary": "on" if used else "alias in text"}
        except Exception as e:  # noqa: BLE001
            report[name] = {"error": str(e)[:400]}
            ok = False
        print(name, report[name], flush=True)
    rep["account_after"] = account()
    rep["characters_this_run"] = rep["account_after"]["characters_used"] - rep["account_before"]["characters_used"]
    old.write_text(json.dumps(report, indent=1))
    (out / "voice_d_report.json").write_text(json.dumps(rep, indent=1))
    (out / "voice_d_report.md").write_text(md(rep, report))
    return 0 if ok else 1


def md(rep: dict, samples: dict) -> str:
    a, e = rep["account_after"], rep["episode_characters"]
    L = ["Voice D · ElevenLabs v3 (eleven_v3), cold open, same pauses / bed / hit / silence as A-B-C", "",
         f"Plan: {a['plan']} ({a.get('status')}) · characters left this month: {a['characters_left']:,} of {a['character_limit']:,}"
         + (f" (resets {a['resets']})" if a.get("resets") else ""),
         f"Commercial use: {'yes (paid plan)' if a['commercial_use'] else 'NO: the free plan is non-commercial'}",
         f"This run used {rep['characters_this_run']:,} characters (2 voices, retakes and the Live Nation probe included).",
         f"Per full episode (with tags + ~25% retakes): EN ≈ {e['en_per_episode']:,.0f} · RU review copy ≈ {e['ru_per_episode']:,.0f}"
         f" (script: EN {e['en_script']:,} / RU {e['ru_script']:,} characters)", ""]
    d = rep.get("dictionary", {})
    L.append(f"Pronunciation dictionary '{DICT_NAME}': Live Nation -> 'Lyve Nation' (alias)" if "id" in d else
             f"Pronunciation dictionary: FAILED {d.get('error')}")
    if rep.get("probe"):
        L.append(f"Probe (listen): {rep['probe']['file']} · dictionary {rep['probe']['dictionary']}")
    L.append("")
    for i, v in enumerate(rep["voices"], 1):
        s = next((x for k, x in samples.items() if k.startswith(f"D{i}_")), {})
        L.append(f"D{i}: {v['name']} ({v['source']}) · {s.get('seconds', '?')} s · {s.get('takes', '?')} takes for {s.get('lines', '?')} lines")
        L.append(f"    {v.get('about', '')}")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
