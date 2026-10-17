"""Channel music library via Lyria (OpenRouter): python -m factory.music [--only noir,fanfare] [--send]

Beds (instrumental backgrounds per mood) and stings (short hits) are made once and stored in the
GitHub release 'music-lib'; the renderer downloads them into assets/music/."""
from __future__ import annotations

import argparse
import base64
import json
import subprocess
import time
from pathlib import Path

import requests

from .config import ROOT, env

SPEC = ROOT / "channel" / "music.json"
URL = "https://openrouter.ai/api/v1/chat/completions"


def _headers() -> dict:
    return {"Authorization": f"Bearer {env('OPENROUTER_API_KEY').strip()}", "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/silver666djon-netizen/explainer-factory", "X-Title": "CoinSense"}


def _collect(obj, out: list) -> None:
    """Finds base64 audio anywhere in a (streamed or plain) response chunk."""
    if isinstance(obj, dict):
        a = obj.get("audio")
        if isinstance(a, dict) and isinstance(a.get("data"), str):
            out.append(a["data"])
        for k in ("input_audio", "output_audio"):
            if isinstance(obj.get(k), dict) and isinstance(obj[k].get("data"), str):
                out.append(obj[k]["data"])
        url = (obj.get("audio_url") or {}).get("url") if isinstance(obj.get("audio_url"), dict) else None
        if isinstance(url, str) and "base64," in url:
            out.append(url.split("base64,", 1)[1])
        for k, v in obj.items():
            if k not in ("audio", "audio_url"):
                _collect(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _collect(v, out)


def generate(model: str, prompt: str) -> bytes:
    attempts = [
        {"model": model, "messages": [{"role": "user", "content": prompt}], "modalities": ["audio"],
         "audio": {"format": "wav"}, "stream": True},
        {"model": model, "messages": [{"role": "user", "content": prompt}], "modalities": ["text", "audio"],
         "audio": {"format": "wav"}, "stream": True},
        {"model": model, "messages": [{"role": "user", "content": prompt}], "modalities": ["audio"]},
    ]
    last = ""
    for body in attempts:
        for _try in range(3):
            try:
                r = requests.post(URL, headers=_headers(), json=body, timeout=600, stream=bool(body.get("stream")))
            except requests.RequestException as exc:
                last = str(exc)
                time.sleep(10)
                continue
            if r.status_code != 200:
                last = f"HTTP {r.status_code}: {r.text[:500]}"
                if r.status_code in (429, 500, 502, 503, 504):
                    time.sleep(15)
                    continue
                break
            parts: list[str] = []
            if body.get("stream"):
                for line in r.iter_lines():
                    if not line:
                        continue
                    s = line.decode("utf-8", "ignore")
                    if not s.startswith("data: "):
                        continue
                    data = s[6:]
                    if data.strip() == "[DONE]":
                        break
                    try:
                        _collect(json.loads(data), parts)
                    except json.JSONDecodeError:
                        pass
            else:
                _collect(r.json(), parts)
            if parts:
                return base64.b64decode("".join(parts))
            last = f"no audio in response ({body.get('modalities')}, stream={body.get('stream')})"
            break
    raise RuntimeError(f"Music generation failed for {model}: {last}")


def _sniff_ext(data: bytes) -> str:
    if data[:4] == b"RIFF":
        return "wav"
    if data[:3] == b"ID3" or data[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
        return "mp3"
    if data[:4] == b"fLaC":
        return "flac"
    if data[:4] == b"OggS":
        return "ogg"
    return "bin"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--out", default=str(ROOT / "out" / "music"))
    ap.add_argument("--send", action="store_true")
    a = ap.parse_args()
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    only = {k for k in a.only.split(",") if k}
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    jobs = [(k, "bed", p) for k, p in spec["beds"].items()] + [(k, "sting", p) for k, p in spec["stings"].items()]
    made, errors = [], []
    for key, kind, prompt in jobs:
        if only and key not in only:
            continue
        model = spec["model"] if kind == "bed" else spec.get("clip_model", spec["model"])
        text = f"{prompt}. {spec['common']}" if kind == "bed" else f"{prompt}. Instrumental only, no vocals."
        try:
            data = generate(model, text)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{key}: {exc}")
            print("ERROR", key, exc, flush=True)
            continue
        raw = out / f"{key}.{_sniff_ext(data)}"
        raw.write_bytes(data)
        mp3 = out / f"{key}.mp3"
        if raw.suffix != ".mp3":
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-b:a", "192k", str(mp3)], check=True)
            raw.unlink()
        dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(mp3)],
                             capture_output=True, text=True).stdout.strip()
        print(f"made {mp3.name} ({dur}s, {kind})", flush=True)
        made.append(mp3)
    if a.send and made:
        from .notify import send_document
        for p in made:
            send_document(p, f"🎵 {p.stem}")
    if errors:
        (out / "errors.txt").write_text("\n".join(errors))
        if not made:
            raise SystemExit("\n".join(errors))


if __name__ == "__main__":
    main()
