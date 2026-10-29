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


def _tg_copy(src: Path, dst: Path, limit: int = LIMIT) -> Path:
    """The long video as a Telegram copy under the bot limit (480p, bitrate from the duration); the release keeps 1080p."""
    import subprocess
    if src.stat().st_size < limit:
        if src != dst:
            import shutil
            shutil.copy(src, dst)
        return dst
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(src)],
                               capture_output=True, text=True).stdout.strip() or 600)
    vbr = max(250, int((limit * 0.92 * 8 / dur) / 1000) - 192)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-vf", "scale=-2:480", "-c:v", "libx264", "-preset", "veryfast",
                    "-b:v", f"{vbr}k", "-maxrate", f"{int(vbr * 1.1)}k", "-bufsize", f"{vbr * 2}k", "-c:a", "copy",  # Klot r86: the mastered audio as is (a re-encode overshot to -0.7 dBTP)
                    "-movflags", "+faststart", str(dst)], check=True)
    return dst


def main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[0] == "--failed":
        send_text(f"⚠️ Explainer Factory: рендер не удался.\nЛог: {argv[1]}")
        return 0
    from . import naming

    def opt(name, default=None):
        return argv[argv.index(name) + 1] if name in argv else default
    out_dir, release_url = Path(argv[0]), argv[1]
    tag = opt("--tag", "")
    meta = json.loads((out_dir / "metadata.json").read_text(encoding="utf-8")) if (out_dir / "metadata.json").exists() else {}
    slug, lang, run = naming.parse_tag(tag) if tag else (meta.get("slug", ""), meta.get("lang"), 0)
    epno = naming.episode_number(Path("episodes") / slug)
    status = (opt("--status") or ("RU REVIEW" if lang else "FINAL CANDIDATE")).upper()
    head = naming.header(epno, run, status, opt("--replaces"))
    pre = naming.prefix(epno, run, lang)
    files = {naming.kind_of(f.name): f for f in sorted(out_dir.iterdir()) if naming.kind_of(f.name)}
    title = meta.get("title", slug)
    if status == "APPROVED FINAL":  # one last message: header, upload title, the 1080p link; then .srt + description
        names = "\n".join(f"• {f.name}" for f in sorted(out_dir.iterdir()) if f.suffix in (".mp4", ".txt", ".srt", ".jpg"))
        long_name = files["long"].name if "long" in files else f"{pre}_long.mp4"
        send_text(f"{head}\nНазвание для загрузки: {title}\n1080p ({long_name}): {release_url}\nФайлы релиза:\n{names}")
        _send_texts(files, pre, head)
        return 0
    minutes = float(meta.get("duration_seconds", 0)) / 60
    link = opt("--link") or ""
    if link and "long" in files:  # the direct 1080p download (a draft release: opens while logged in to GitHub)
        mb = files["long"].stat().st_size / 1e6
        cap = (f"{head}\n{title}\nДлинное видео: {minutes:.1f} мин\n1080p, {files['long'].name} ({mb:.0f} МБ), прямая ссылка:\n{link}"
               f"\n(черновой релиз: открывается, когда вы вошли в GitHub)")
    else:
        cap = f"{head}\n{title}\nДлинное видео: {minutes:.1f} мин · полное 1080p: {release_url}"
    if lang:
        cap += "\nТолько для проверки, не загружать."
    tmp = out_dir / "_tg"
    tmp.mkdir(exist_ok=True)
    if "long" in files:  # 1) the long video first
        tg = _tg_copy(files["long"], tmp / f"{pre}_long.mp4")
        if files["long"].stat().st_size >= LIMIT:
            cap += "\n(в Telegram — копия 480p)"
        with open(tg, "rb") as fh:
            r = _api("sendVideo", data={"caption": cap[:1000], "supports_streaming": "true"}, files={"video": (tg.name, fh)})
        if r is None or r.status_code != 200:
            send_text(cap)
    else:
        send_text(cap)
    if opt("--only") == "long":  # the long video as its own message, nothing else
        return 0
    shorts = sorted((k, f) for k, f in files.items() if k and k[0] == "s" and k[1:].isdigit())
    shorts = [(k, f) for k, f in sorted(shorts, key=lambda x: int(x[0][1:])) if f.stat().st_size < LIMIT]
    if shorts:  # 2) the Shorts in one batch (an album; split only where one request would exceed the upload limit)
        groups, cur, size = [], [], 0
        for k, f in shorts:
            if cur and (len(cur) == 10 or size + f.stat().st_size > LIMIT * 0.9):
                groups.append(cur)
                cur, size = [], 0
            cur.append((k, f))
            size += f.stat().st_size
        groups.append(cur)
        for g_i, grp in enumerate(groups):
            media, up = [], {}
            for n, (k, f) in enumerate(grp):
                item = {"type": "video", "media": f"attach://v{n}", "supports_streaming": True}
                if n == 0 and g_i == 0:
                    item["caption"] = f"{head} · Shorts ({len(shorts)})"
                media.append(item)
                up[f"v{n}"] = (f"{pre}_{k}.mp4", open(f, "rb"), "video/mp4")
            r = _api("sendMediaGroup", data={"media": json.dumps(media)}, files=up) if len(grp) > 1 else None
            for v in up.values():
                v[1].close()
            if r is None or r.status_code != 200:  # one Short, or the album failed: one by one
                for k, f in grp:
                    with open(f, "rb") as fh:
                        _api("sendVideo", data={"caption": f"{head} · {k}", "supports_streaming": "true"},
                             files={"video": (f"{pre}_{k}.mp4", fh)})
    _send_texts(files, pre, head)  # 3) the texts
    return 0


def _send_texts(files: dict, pre: str, head: str) -> None:
    for k in ("srt", "description"):
        if k in files:
            name = f"{pre}_description.txt" if k == "description" else f"{pre}_long.srt"
            with open(files[k], "rb") as fh:
                _api("sendDocument", data={"caption": head}, files={"document": (name, fh)})


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
