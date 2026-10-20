"""Telegram notifications: python -m factory.notify <out_dir> <release_url> [--failed <run_url>]"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import requests

from .config import env

LIMIT = 49 * 1024 * 1024  # bots can upload files up to 50 MB


def _api(method: str, **kwargs):
    token, chat = env("TELEGRAM_BOT_TOKEN"), env("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print("Telegram secrets are not set — skipping notification")
        return None
    data = dict(kwargs.pop("data", {}), chat_id=chat.strip())
    try:
        resp = requests.post(f"https://api.telegram.org/bot{token.strip()}/{method}", data=data, timeout=300, **kwargs)
    except requests.RequestException as exc:  # one slow upload must not stop the rest
        print(f"::warning::Telegram {method} error: {exc}")
        return None
    if resp.status_code != 200:
        print(f"::warning::Telegram {method} failed: {resp.status_code} {resp.text[:300]}")
    return resp


def send_text(text: str) -> None:
    _api("sendMessage", data={"text": text, "disable_web_page_preview": "true"})


def send_album(paths: list[Path], caption: str = "") -> None:
    """Photos in groups of up to 10 (Telegram's album limit)."""
    for start in range(0, len(paths), 10):
        chunk = paths[start : start + 10]
        media, files = [], {}
        for i, p in enumerate(chunk):
            name = f"f{i}"
            item = {"type": "photo", "media": f"attach://{name}"}
            if i == 0 and start == 0 and caption:
                item["caption"] = caption
            media.append(item)
            files[name] = (p.name, open(p, "rb"), "image/jpeg")
        if len(chunk) == 1:
            _api("sendPhoto", data={"caption": caption if start == 0 else ""}, files={"photo": files["f0"]})
        else:
            _api("sendMediaGroup", data={"media": json.dumps(media)}, files=files)
        for f in files.values():
            f[1].close()


def send_document(path: Path, caption: str = "") -> None:
    with open(path, "rb") as fh:
        _api("sendDocument", data={"caption": caption[:1000]}, files={"document": (path.name, fh)})


def send_buttons(text: str, rows: list[list[tuple[str, str]]]) -> None:
    kb = {"inline_keyboard": [[{"text": t, "callback_data": d[:64]} for t, d in row] for row in rows]}
    _api("sendMessage", data={"text": text, "reply_markup": json.dumps(kb)})


def main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[0] == "--failed":
        send_text(f"⚠️ Explainer Factory: рендер не удался.\nЛог: {argv[1]}")
        return 0
    out_dir, release_url = Path(argv[0]), argv[1]
    meta = json.loads((out_dir / "metadata.json").read_text(encoding="utf-8"))
    minutes = meta["duration_seconds"] / 60
    lines = [
        f"✅ Готово: {meta['title']}",
        f"Длинное видео: {minutes:.1f} мин, Shorts: {len(meta['shorts'])}",
        f"Скачать всё: {release_url}",
    ]
    thumb = out_dir / "thumbnail.jpg"
    if thumb.exists():
        with open(thumb, "rb") as fh:
            _api("sendPhoto", data={"caption": "\n".join(lines)}, files={"photo": fh})
    else:
        send_text("\n".join(lines))
    for short in meta["shorts"]:
        path = out_dir / short["file"]
        if path.exists() and path.stat().st_size < LIMIT:
            with open(path, "rb") as fh:
                _api("sendVideo", data={"caption": f"Shorts: {short['title']}", "supports_streaming": "true"}, files={"video": fh})
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
