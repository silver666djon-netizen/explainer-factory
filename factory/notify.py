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
    resp = requests.post(f"https://api.telegram.org/bot{token.strip()}/{method}", data=data, timeout=120, **kwargs)
    if resp.status_code != 200:
        print(f"Telegram {method} failed: {resp.status_code} {resp.text[:300]}")
    return resp


def send_text(text: str) -> None:
    _api("sendMessage", data={"text": text, "disable_web_page_preview": "true"})


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
