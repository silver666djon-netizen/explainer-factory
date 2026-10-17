"""YouTube: upload, schedule, metadata, thumbnails, captions, analytics.

Secrets (GitHub): YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN.

python -m factory.youtube upload   <out_dir> <episode_dir>      # uploads long + Shorts as private, saves youtube.json
python -m factory.youtube schedule <episode_dir> [YYYY-MM-DD]  # sets publish times (long on the next slot, Shorts 2/day after)
python -m factory.youtube update   <episode_dir>               # re-applies title/description/tags/thumbnail from files
python -m factory.youtube analytics [days]                     # writes reports/analytics-<date>.json + .md, sends a summary
python -m factory.youtube whoami
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
import time
from pathlib import Path

import requests

from .config import ROOT, env, load_config

API = "https://www.googleapis.com/youtube/v3"
UPLOAD = "https://www.googleapis.com/upload/youtube/v3"
ANALYTICS = "https://youtubeanalytics.googleapis.com/v2/reports"
REPORTING = "https://youtubereporting.googleapis.com/v1"

_token: dict = {}


def token() -> str:
    if _token.get("exp", 0) > time.time() + 60:
        return _token["access"]
    cid, sec, ref = env("YT_CLIENT_ID"), env("YT_CLIENT_SECRET"), env("YT_REFRESH_TOKEN")
    if not (cid and sec and ref):
        raise SystemExit("YouTube secrets YT_CLIENT_ID / YT_CLIENT_SECRET / YT_REFRESH_TOKEN are not set")
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": cid.strip(), "client_secret": sec.strip(), "refresh_token": ref.strip(), "grant_type": "refresh_token"}, timeout=60)
    if r.status_code != 200:
        raise SystemExit(f"Google refused the refresh token ({r.status_code}): {r.text[:300]}")
    data = r.json()
    _token.update(access=data["access_token"], exp=time.time() + int(data.get("expires_in", 3600)))
    return _token["access"]


def _h(extra: dict | None = None) -> dict:
    h = {"Authorization": f"Bearer {token()}"}
    h.update(extra or {})
    return h


def _check(r: requests.Response, what: str) -> dict:
    if r.status_code >= 300:
        raise SystemExit(f"YouTube API error during {what} ({r.status_code}): {r.text[:600]}")
    return r.json() if r.text else {}


def whoami() -> dict:
    data = _check(requests.get(f"{API}/channels", headers=_h(), params={"part": "snippet,statistics", "mine": "true"}, timeout=60), "channels.list")
    items = data.get("items") or []
    if not items:
        raise SystemExit("This Google account has no YouTube channel")
    return items[0]


def upload_video(path: Path, title: str, description: str, tags: list[str], cfg: dict, publish_at: str | None = None) -> str:
    yt = cfg.get("youtube") or {}
    status = {"privacyStatus": "private", "selfDeclaredMadeForKids": False, "embeddable": True}
    if publish_at:
        status["publishAt"] = publish_at
    body = {
        "snippet": {"title": title[:100], "description": description[:4900], "tags": tags[:30],
                    "categoryId": str(yt.get("category_id", 27)),
                    "defaultLanguage": cfg.get("language", "en"), "defaultAudioLanguage": cfg.get("language", "en")},
        "status": status,
    }
    size = path.stat().st_size
    init = requests.post(f"{UPLOAD}/videos", params={"uploadType": "resumable", "part": "snippet,status"},
                         headers=_h({"Content-Type": "application/json; charset=UTF-8", "X-Upload-Content-Type": "video/mp4",
                                     "X-Upload-Content-Length": str(size)}),
                         data=json.dumps(body), timeout=60)
    _check(init, "upload init")
    url = init.headers["Location"]
    chunk = 32 * 1024 * 1024
    sent = 0
    with open(path, "rb") as fh:
        while sent < size:
            data = fh.read(chunk)
            end = sent + len(data) - 1
            for attempt in range(5):
                try:
                    r = requests.put(url, headers=_h({"Content-Length": str(len(data)), "Content-Range": f"bytes {sent}-{end}/{size}"}),
                                     data=data, timeout=600)
                    break
                except requests.RequestException:
                    time.sleep(5 * (attempt + 1))
            else:
                raise SystemExit("Upload kept failing")
            if r.status_code in (200, 201):
                return r.json()["id"]
            if r.status_code != 308:
                _check(r, "upload chunk")
            rng = r.headers.get("Range")
            sent = int(rng.split("-")[1]) + 1 if rng else sent + len(data)
            fh.seek(sent)
    raise SystemExit("Upload finished without a video id")


def set_thumbnail(video_id: str, path: Path) -> None:
    with open(path, "rb") as fh:
        r = requests.post(f"{UPLOAD}/thumbnails/set", params={"videoId": video_id},
                          headers=_h({"Content-Type": "image/jpeg"}), data=fh.read(), timeout=120)
    if r.status_code >= 300:
        print(f"Thumbnail not set ({r.status_code}): {r.text[:300]} — is the channel phone-verified (youtube.com/verify)?")


def upload_captions(video_id: str, srt: Path, lang: str = "en") -> None:
    meta = {"snippet": {"videoId": video_id, "language": lang, "name": "English", "isDraft": False}}
    boundary = "xxCAPTIONxx"
    body = (f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n{json.dumps(meta)}\r\n"
            f"--{boundary}\r\nContent-Type: application/octet-stream\r\n\r\n").encode() + srt.read_bytes() + f"\r\n--{boundary}--".encode()
    r = requests.post(f"{UPLOAD}/captions", params={"uploadType": "multipart", "part": "snippet"},
                      headers=_h({"Content-Type": f"multipart/related; boundary={boundary}"}), data=body, timeout=120)
    if r.status_code >= 300:
        print(f"Captions not uploaded ({r.status_code}): {r.text[:300]}")


def set_status(video_id: str, publish_at: str | None, privacy: str = "private") -> None:
    status = {"privacyStatus": privacy, "selfDeclaredMadeForKids": False}
    if publish_at:
        status["publishAt"] = publish_at
    _check(requests.put(f"{API}/videos", params={"part": "status"}, headers=_h({"Content-Type": "application/json"}),
                        data=json.dumps({"id": video_id, "status": status}), timeout=60), "videos.update status")


def update_snippet(video_id: str, title: str, description: str, tags: list[str], cfg: dict) -> None:
    yt = cfg.get("youtube") or {}
    body = {"id": video_id, "snippet": {"title": title[:100], "description": description[:4900], "tags": tags[:30],
                                        "categoryId": str(yt.get("category_id", 27)), "defaultLanguage": cfg.get("language", "en")}}
    _check(requests.put(f"{API}/videos", params={"part": "snippet"}, headers=_h({"Content-Type": "application/json"}),
                        data=json.dumps(body), timeout=60), "videos.update snippet")


def add_to_playlist(video_id: str, playlist_id: str) -> None:
    body = {"snippet": {"playlistId": playlist_id, "resourceId": {"kind": "youtube#video", "videoId": video_id}}}
    r = requests.post(f"{API}/playlistItems", params={"part": "snippet"}, headers=_h({"Content-Type": "application/json"}),
                      data=json.dumps(body), timeout=60)
    if r.status_code >= 300:
        print(f"Playlist add failed ({r.status_code}): {r.text[:200]}")


# ------------------------------------------------------------------ episode-level commands

def _state_path(ep_dir: Path) -> Path:
    return ep_dir / "youtube.json"


def _load_state(ep_dir: Path) -> dict:
    p = _state_path(ep_dir)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _save_state(ep_dir: Path, state: dict) -> None:
    _state_path(ep_dir).write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def _short_description(meta: dict, short: dict, long_id: str | None) -> str:
    parts = [short.get("title", "").replace("#shorts", "").strip()]
    if long_id:
        parts.append(f"Full case file: https://youtu.be/{long_id}")
    parts.append("#shorts #psychologyofmoney")
    return "\n\n".join(p for p in parts if p)


def cmd_upload(out_dir: Path, ep_dir: Path) -> dict:
    cfg = load_config()
    meta = json.loads((out_dir / "metadata.json").read_text(encoding="utf-8"))
    state = _load_state(ep_dir)
    if not state.get("long"):
        vid = upload_video(out_dir / "long.mp4", meta["title"], meta["description"], meta.get("tags", []), cfg)
        state["long"] = {"id": vid, "title": meta["title"]}
        _save_state(ep_dir, state)
        print("long uploaded", vid)
        if (out_dir / "thumbnail.jpg").exists():
            set_thumbnail(vid, out_dir / "thumbnail.jpg")
        if (out_dir / "long.srt").exists():
            upload_captions(vid, out_dir / "long.srt", cfg.get("language", "en"))
        pl = (cfg.get("youtube") or {}).get("playlist_long")
        if pl:
            add_to_playlist(vid, pl)
    long_id = state["long"]["id"]
    shorts = state.setdefault("shorts", {})
    for short in meta.get("shorts", []):
        if short["id"] in shorts:
            continue
        vid = upload_video(out_dir / short["file"], short["title"], _short_description(meta, short, long_id),
                           meta.get("tags", [])[:8] + ["shorts"], cfg)
        shorts[short["id"]] = {"id": vid, "title": short["title"]}
        _save_state(ep_dir, state)
        print("short uploaded", short["id"], vid)
    state["uploaded_at"] = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    _save_state(ep_dir, state)
    return state


WEEKDAYS = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}


def plan_schedule(cfg: dict, start: dt.date | None, n_shorts: int) -> tuple[dt.datetime, list[dt.datetime]]:
    sch = (cfg.get("youtube") or {}).get("schedule") or {}
    days = [WEEKDAYS[d] for d in sch.get("long_days", ["mon", "thu"])]
    hh, mm = [int(x) for x in sch.get("long_time_utc", "14:00").split(":")]
    shorts_times = [tuple(int(x) for x in t.split(":")) for t in sch.get("shorts_times_utc", ["12:00", "20:00"])]
    now = dt.datetime.utcnow() + dt.timedelta(hours=2)  # leave time for processing
    day = start or now.date()
    while True:
        cand = dt.datetime(day.year, day.month, day.day, hh, mm)
        if day.weekday() in days and cand > now:
            break
        day += dt.timedelta(days=1)
    long_at = cand
    shorts_at = []
    d = long_at.date()
    k = 0
    while len(shorts_at) < n_shorts:
        h, m = shorts_times[k % len(shorts_times)]
        t = dt.datetime(d.year, d.month, d.day, h, m)
        if t > long_at + dt.timedelta(hours=3):
            shorts_at.append(t)
        k += 1
        if k % len(shorts_times) == 0:
            d += dt.timedelta(days=1)
    return long_at, shorts_at


def _iso(t: dt.datetime) -> str:
    return t.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def cmd_schedule(ep_dir: Path, start: str | None) -> dict:
    cfg = load_config()
    state = _load_state(ep_dir)
    if not state.get("long"):
        raise SystemExit("Nothing uploaded yet for this episode")
    start_date = dt.date.fromisoformat(start) if start else None
    shorts = list(state.get("shorts", {}).items())
    long_at, shorts_at = plan_schedule(cfg, start_date, len(shorts))
    set_status(state["long"]["id"], _iso(long_at))
    state["long"]["publish_at"] = _iso(long_at)
    for (sid, info), t in zip(shorts, shorts_at):
        set_status(info["id"], _iso(t))
        info["publish_at"] = _iso(t)
    state["scheduled"] = True
    _save_state(ep_dir, state)
    return state


def cmd_update(ep_dir: Path, out_dir: Path | None) -> None:
    cfg = load_config()
    state = _load_state(ep_dir)
    src = out_dir or ep_dir
    meta = json.loads((src / "metadata.json").read_text(encoding="utf-8"))
    update_snippet(state["long"]["id"], meta["title"], meta["description"], meta.get("tags", []), cfg)
    if (src / "thumbnail.jpg").exists():
        set_thumbnail(state["long"]["id"], src / "thumbnail.jpg")


# ------------------------------------------------------------------ analytics

def _report(params: dict) -> dict:
    p = {"ids": "channel==MINE"}
    p.update(params)
    return _check(requests.get(ANALYTICS, headers=_h(), params=p, timeout=60), "analytics")


def _rows(rep: dict) -> list[dict]:
    cols = [c["name"] for c in rep.get("columnHeaders", [])]
    return [dict(zip(cols, r)) for r in rep.get("rows", []) or []]


def video_titles(ids: list[str]) -> dict:
    out = {}
    for i in range(0, len(ids), 50):
        data = _check(requests.get(f"{API}/videos", headers=_h(), params={"part": "snippet,contentDetails", "id": ",".join(ids[i:i + 50])}, timeout=60), "videos.list")
        for it in data.get("items", []):
            out[it["id"]] = {"title": it["snippet"]["title"], "duration": it["contentDetails"]["duration"]}
    return out


def ensure_reach_job() -> str | None:
    """Thumbnail impressions + CTR come from the Reporting API (daily bulk reports, ~2 days delay)."""
    types = _check(requests.get(f"{REPORTING}/reportTypes", headers=_h(), timeout=60), "reportTypes").get("reportTypes", [])
    reach = [t["id"] for t in types if "reach" in t["id"] and t["id"].startswith("channel_")]
    if not reach:
        return None
    rtype = sorted(reach)[0]
    jobs = _check(requests.get(f"{REPORTING}/jobs", headers=_h(), timeout=60), "jobs").get("jobs", [])
    for j in jobs:
        if j.get("reportTypeId") == rtype:
            return j["id"]
    j = _check(requests.post(f"{REPORTING}/jobs", headers=_h({"Content-Type": "application/json"}),
                             data=json.dumps({"reportTypeId": rtype, "name": "coinsense-reach"}), timeout=60), "jobs.create")
    return j.get("id")


def reach_summary(job_id: str) -> dict:
    reps = _check(requests.get(f"{REPORTING}/jobs/{job_id}/reports", headers=_h(), timeout=60), "reports").get("reports", [])
    if not reps:
        return {"note": "no reach reports yet (they appear ~2 days after the job is created)"}
    totals: dict[str, dict] = {}
    for rep in sorted(reps, key=lambda r: r["startTime"])[-28:]:
        csv = requests.get(rep["downloadUrl"], headers=_h(), timeout=120).text.splitlines()
        if not csv:
            continue
        head = csv[0].split(",")
        for line in csv[1:]:
            row = dict(zip(head, line.split(",")))
            vid = row.get("video_id")
            if not vid:
                continue
            t = totals.setdefault(vid, {"impressions": 0.0, "clicks": 0.0})
            imp = float(row.get("video_thumbnail_impressions") or 0)
            ctr = float(row.get("video_thumbnail_impressions_ctr") or 0)
            t["impressions"] += imp
            t["clicks"] += imp * ctr
    return {vid: {"impressions": int(v["impressions"]), "ctr_percent": round(100 * v["clicks"] / v["impressions"], 2) if v["impressions"] else None}
            for vid, v in totals.items()}


def cmd_analytics(days: int = 28) -> Path:
    end = dt.date.today()
    start = end - dt.timedelta(days=days)
    base = {"startDate": start.isoformat(), "endDate": end.isoformat()}
    channel = _rows(_report(dict(base, metrics="views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,subscribersGained,subscribersLost,likes,comments,shares")))
    daily = _rows(_report(dict(base, metrics="views,estimatedMinutesWatched,subscribersGained", dimensions="day", sort="day")))
    videos = _rows(_report(dict(base, metrics="views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,likes,comments,shares,subscribersGained",
                                dimensions="video", sort="-views", maxResults=50)))
    traffic = _rows(_report(dict(base, metrics="views,estimatedMinutesWatched", dimensions="insightTrafficSourceType", sort="-views")))
    geo = _rows(_report(dict(base, metrics="views,estimatedMinutesWatched", dimensions="country", sort="-views", maxResults=10)))
    titles = video_titles([v["video"] for v in videos])
    retention = {}
    for v in videos[:6]:
        try:
            retention[v["video"]] = _rows(_report(dict(base, metrics="audienceWatchRatio,relativeRetentionPerformance",
                                                      dimensions="elapsedVideoTimeRatio", filters=f"video=={v['video']}")))
        except SystemExit as exc:
            retention[v["video"]] = str(exc)
    reach = {}
    try:
        job = ensure_reach_job()
        if job:
            reach = reach_summary(job)
    except SystemExit as exc:
        reach = {"error": str(exc)}
    data = {"period": base, "channel": channel, "daily": daily, "videos": [dict(v, **titles.get(v["video"], {})) for v in videos],
            "traffic_sources": traffic, "countries": geo, "retention": retention, "reach": reach}
    out = ROOT / "reports"
    out.mkdir(exist_ok=True)
    path = out / f"analytics-{end.isoformat()}.json"
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    try:
        from .notify import send_text
        c = channel[0] if channel else {}
        lines = [f"📊 CoinSense, {days} дней: просмотры {int(c.get('views', 0))}, часы просмотра {round(c.get('estimatedMinutesWatched', 0) / 60, 1)}, "
                 f"подписчики +{int(c.get('subscribersGained', 0))}/−{int(c.get('subscribersLost', 0))}"]
        for v in data["videos"][:5]:
            lines.append(f"• {v.get('title', v['video'])[:50]} — {int(v['views'])} просм., ср. {round(v.get('averageViewPercentage', 0))}%")
        lines.append("Подробный разбор — в чате с Claude.")
        send_text("\n".join(lines))
    except Exception as exc:  # noqa: BLE001
        print("telegram summary failed:", exc)
    return path


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 1
    cmd = argv[0]
    if cmd == "whoami":
        ch = whoami()
        print(json.dumps({"id": ch["id"], "title": ch["snippet"]["title"], "stats": ch.get("statistics")}, indent=2))
    elif cmd == "upload":
        state = cmd_upload(Path(argv[1]), Path(argv[2]))
        print(json.dumps(state, indent=2))
    elif cmd == "schedule":
        state = cmd_schedule(Path(argv[1]), argv[2] if len(argv) > 2 and argv[2] else None)
        print(json.dumps(state, indent=2))
    elif cmd == "update":
        cmd_update(Path(argv[1]), Path(argv[2]) if len(argv) > 2 else None)
    elif cmd == "analytics":
        print(cmd_analytics(int(argv[1]) if len(argv) > 1 else 28))
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
