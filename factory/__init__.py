"""Explainer Factory: script -> images -> voice -> montage -> long video, Shorts, thumbnail."""
import os as _os
import sys as _sys
from urllib.parse import quote as _quote

# Public workflow logs: anything printed by the factory passes through this filter, which replaces the values of the
# secret environment variables (and their URL-encoded forms, e.g. a key inside an error message's URL) with ***.
_SECRET_ENV = ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "OPENROUTER_API_KEY", "GEMINI_API_KEY", "PEXELS_API_KEY",
               "PIXABAY_API_KEY", "CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_WORKERS_TOKEN",
               "BOT_GITHUB_TOKEN", "GH_TOKEN", "GITHUB_TOKEN", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN")


def _secret_values():
    vals = set()
    for k in _SECRET_ENV:
        v = (_os.environ.get(k) or "").strip()
        if len(v) >= 6 and v not in ("audit-offline",):
            vals |= {v, _quote(v, safe="")}
    return sorted(vals, key=len, reverse=True)


def redact(text: str) -> str:
    for v in _secret_values():
        text = text.replace(v, "***")
    return text


class _Redacting:
    def __init__(self, stream):
        self._s = stream

    def write(self, data):
        return self._s.write(redact(data) if isinstance(data, str) else data)

    def __getattr__(self, name):
        return getattr(self._s, name)


if not isinstance(_sys.stdout, _Redacting):
    _sys.stdout = _Redacting(_sys.stdout)
    _sys.stderr = _Redacting(_sys.stderr)
