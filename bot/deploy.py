"""Deploys bot/worker.js to Cloudflare Workers and points the Telegram webhook at it.

Env: CLOUDFLARE_WORKERS_TOKEN, CLOUDFLARE_ACCOUNT_ID, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, BOT_GITHUB_TOKEN, GITHUB_REPOSITORY
"""
import json
import os
import secrets
import sys
from pathlib import Path

import requests

NAME = "coinsense-bot"


def need(name: str) -> str:
    val = (os.environ.get(name) or "").strip()
    if not val:
        sys.exit(f"Secret {name} is missing")
    return val


def main() -> int:
    cf_token, account = need("CLOUDFLARE_WORKERS_TOKEN"), need("CLOUDFLARE_ACCOUNT_ID")
    tg_token, owner = need("TELEGRAM_BOT_TOKEN"), need("TELEGRAM_CHAT_ID")
    gh_token, repo = need("BOT_GITHUB_TOKEN"), need("GITHUB_REPOSITORY")
    hook_secret = secrets.token_urlsafe(32)
    api = f"https://api.cloudflare.com/client/v4/accounts/{account}/workers"
    h = {"Authorization": f"Bearer {cf_token}"}

    metadata = {
        "main_module": "worker.js",
        "compatibility_date": "2025-01-01",
        "bindings": [
            {"type": "secret_text", "name": "TG_TOKEN", "text": tg_token},
            {"type": "plain_text", "name": "OWNER_CHAT_ID", "text": owner},
            {"type": "secret_text", "name": "GH_TOKEN", "text": gh_token},
            {"type": "plain_text", "name": "GH_REPO", "text": repo},
            {"type": "secret_text", "name": "WEBHOOK_SECRET", "text": hook_secret},
        ],
    }
    code = (Path(__file__).parent / "worker.js").read_text(encoding="utf-8")
    files = {
        "metadata": (None, json.dumps(metadata), "application/json"),
        "worker.js": ("worker.js", code, "application/javascript+module"),
    }
    r = requests.put(f"{api}/scripts/{NAME}", headers=h, files=files, timeout=60)
    if not r.ok:
        sys.exit(f"Worker upload failed ({r.status_code}): {r.text[:500]}")
    print("worker uploaded")

    sub = requests.get(f"{api}/subdomain", headers=h, timeout=30).json()
    subdomain = (sub.get("result") or {}).get("subdomain")
    if not subdomain:
        wanted = f"coinsense-{secrets.token_hex(3)}"
        r = requests.put(f"{api}/subdomain", headers=h, json={"subdomain": wanted}, timeout=30)
        if not r.ok:
            sys.exit(f"Could not create a workers.dev subdomain ({r.status_code}): {r.text[:300]}")
        subdomain = wanted
    r = requests.post(f"{api}/scripts/{NAME}/subdomain", headers=h, json={"enabled": True}, timeout=30)
    if not r.ok:
        print(f"note: enabling workers.dev route returned {r.status_code}: {r.text[:200]}")
    url = f"https://{NAME}.{subdomain}.workers.dev"
    print(f"::add-mask::{subdomain}")  # public logs: the worker address is not printed
    print("worker url: https://***.workers.dev")

    r = requests.post(f"https://api.telegram.org/bot{tg_token}/setWebhook", json={
        "url": url, "secret_token": hook_secret, "allowed_updates": ["message", "callback_query"],
        "drop_pending_updates": False}, timeout=30)
    print("webhook:", r.text[:200])
    if not r.ok or not r.json().get("ok"):
        sys.exit("Telegram refused the webhook")
    requests.post(f"https://api.telegram.org/bot{tg_token}/sendMessage", json={
        "chat_id": owner, "text": "🤖 Бот-приёмник подключён. Напиши /help, чтобы увидеть, что я умею."}, timeout=30)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
