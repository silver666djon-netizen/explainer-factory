"""Stock footage and photos for documentary inserts — Pixabay (Content Licence: free for commercial video,
no attribution required), with Pexels as a second source if a key is ever available.

Script usage:
  {"type": "clip", "stock": "supermarket shopping cart", "in": 0, "out": 6, "newsreel": "Stock footage" | false}
  {"type": "archive", "stock_photo": "cash register vintage", "look": "print" | "plain", ...}
  insert: {"stock_photo": "...", "kind": "photo" | "cutout", ...}
The first good result is downloaded once into assets/archive/stock-<hash>.(mp4|jpg); the workflow uploads
those to the 'archive' release so re-renders never call the API again.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import requests

from .archive import ARCHIVE_DIR


def _name(kind: str, query: str, ext: str) -> str:
    return f"stock-{kind}-{hashlib.sha1(query.lower().encode()).hexdigest()[:10]}{ext}"


def _download(url: str, dst: Path) -> None:
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=300) as d:
        d.raise_for_status()
        with open(dst, "wb") as fh:
            for chunk in d.iter_content(1 << 16):
                fh.write(chunk)


def stock_video(query: str, orientation: str = "landscape", min_dur: float = 4.0, log=print, pick=None) -> Path | None:
    dst = ARCHIVE_DIR / _name("v", f"{query}#{pick}" if pick else query, ".mp4")
    if dst.exists():
        return dst
    key = os.environ.get("PIXABAY_API_KEY")
    if key:
        params = {"key": key, "id": pick} if pick else {"key": key, "q": query, "per_page": 20, "safesearch": "true"}
        r = requests.get("https://pixabay.com/api/videos/", params=params, timeout=60)
        r.raise_for_status()
        hits = [h for h in r.json().get("hits", []) if pick or h.get("duration", 0) >= min_dur]
        if orientation == "landscape" and not pick:
            hits = [h for h in hits if h["videos"]["medium"]["width"] >= h["videos"]["medium"]["height"]] or hits
        if hits:
            h = sorted(hits, key=lambda x: -x.get("views", 0))[0]
            v = h["videos"].get("medium") or h["videos"]["small"]
            _download(v["url"], dst)
            dst.with_suffix(".json").write_text(json.dumps({"query": query, "source": "pixabay", "id": h["id"], "user": h.get("user"),
                                                            "url": h.get("pageURL"), "credit": f"Stock footage: {h.get('user')} / Pixabay"}, indent=1))
            log(f"  stock video '{query}': pixabay #{h['id']} by {h.get('user')} ({h.get('duration')}s)")
            return dst
        log(f"  stock video '{query}': nothing on pixabay")
    pk = os.environ.get("PEXELS_API_KEY")
    if pk:
        r = requests.get("https://api.pexels.com/videos/search", headers={"Authorization": pk},
                         params={"query": query, "orientation": orientation, "per_page": 15}, timeout=60)
        r.raise_for_status()
        vids = [v for v in r.json().get("videos", []) if v.get("duration", 0) >= min_dur]
        if vids:
            v = vids[0]
            files = sorted((f for f in v["video_files"] if f.get("width")), key=lambda f: abs((f.get("width") or 0) - 1280))
            _download(files[0]["link"], dst)
            dst.with_suffix(".json").write_text(json.dumps({"query": query, "source": "pexels", "id": v["id"],
                                                            "credit": f"Video by {v.get('user', {}).get('name')} on Pexels"}, indent=1))
            return dst
    if not key and not pk:
        log(f"  stock video '{query}': no stock API key, skipped")
    return None


def stock_photo(query: str, orientation: str = "landscape", log=print, pick=None) -> Path | None:
    dst = ARCHIVE_DIR / _name("p", f"{query}#{pick}" if pick else query, ".jpg")
    if dst.exists():
        return dst
    key = os.environ.get("PIXABAY_API_KEY")
    if key:
        params = {"key": key, "id": pick} if pick else {"key": key, "q": query, "per_page": 20, "image_type": "photo",
                                                        "orientation": "horizontal" if orientation == "landscape" else "vertical",
                                                        "safesearch": "true"}
        r = requests.get("https://pixabay.com/api/", params=params, timeout=60)
        r.raise_for_status()
        hits = r.json().get("hits", [])
        if hits:
            h = sorted(hits, key=lambda x: -x.get("views", 0))[0]
            _download(h.get("largeImageURL") or h["webformatURL"], dst)
            dst.with_suffix(".json").write_text(json.dumps({"query": query, "source": "pixabay", "id": h["id"], "user": h.get("user"),
                                                            "url": h.get("pageURL"), "credit": f"Stock photo: {h.get('user')} / Pixabay"}, indent=1))
            log(f"  stock photo '{query}': pixabay #{h['id']} by {h.get('user')}")
            return dst
        log(f"  stock photo '{query}': nothing on pixabay")
    pk = os.environ.get("PEXELS_API_KEY")
    if pk:
        r = requests.get("https://api.pexels.com/v1/search", headers={"Authorization": pk},
                         params={"query": query, "orientation": orientation, "per_page": 10}, timeout=60)
        r.raise_for_status()
        photos = r.json().get("photos", [])
        if photos:
            p = photos[0]
            _download(p["src"].get("large2x") or p["src"]["large"], dst)
            dst.with_suffix(".json").write_text(json.dumps({"query": query, "source": "pexels", "id": p["id"],
                                                            "credit": f"Photo by {p.get('photographer')} on Pexels"}, indent=1))
            return dst
    if not key and not pk:
        log(f"  stock photo '{query}': no stock API key, skipped")
    return None


def credit_for(path: Path) -> str | None:
    meta = path.with_suffix(".json")
    if meta.exists():
        return json.loads(meta.read_text()).get("credit")
    return None


def resolve_stock(episode: dict, log=print) -> None:
    """Turn 'stock' / 'stock_photo' queries into archive 'file' names (downloading once). Missing stock
    falls back to the beat named in 'fallback' (a reuse) so the render never breaks."""
    for beat in episode["beats"]:
        v = beat["visual"]
        for ins in list(beat.get("inserts") or []):
            if ins.get("stock_photo") and not ins.get("file"):
                p = stock_photo(ins["stock_photo"], ins.get("orientation", "landscape"), log, ins.get("pick"))
                if p:
                    ins["file"] = p.name
                    ins.setdefault("credit", credit_for(p))
                else:
                    beat["inserts"].remove(ins)
        if v["type"] == "clip" and v.get("stock") and not v.get("file"):
            p = stock_video(v["stock"], v.get("orientation", "landscape"), float(v.get("out", 0) or 4), log, v.get("pick"))
            if p:
                v["file"] = p.name
                v.setdefault("credit", credit_for(p))
            elif v.get("fallback_prompt"):
                v.update({"type": "image", "prompt": v["fallback_prompt"]})
                v.pop("newsreel", None)
            elif v.get("fallback"):
                v["type"], v["beat"] = "reuse", v["fallback"]
        if v["type"] == "archive" and v.get("stock_photo") and not v.get("file"):
            p = stock_photo(v["stock_photo"], v.get("orientation", "landscape"), log, v.get("pick"))
            if p:
                v["file"] = p.name
                v.setdefault("credit", credit_for(p))
                v.setdefault("look", "plain")
            elif v.get("fallback"):
                v["type"], v["beat"] = "reuse", v["fallback"]
