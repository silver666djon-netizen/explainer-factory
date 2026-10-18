"""Resolve + download archive media on the Actions runner.
List entries: {"name": "...", "url": "..."} — url may be a direct file, or a loc.gov item/resource page
(resolved through the JSON API to the largest JPEG; newspaper pages too)."""
import json, re, sys, time, pathlib, urllib.request
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) CoinSense-archive-fetch/1.0"}

def get(url, binary=False):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=300) as r:
        data = r.read()
    return data if binary else json.loads(data.decode())

def walk(o, acc):
    if isinstance(o, dict):
        for v in o.values(): walk(v, acc)
    elif isinstance(o, list):
        for v in o: walk(v, acc)
    elif isinstance(o, str) and ("tile.loc.gov" in o or "loc.gov/storage" in o) and re.search(r"\.(jpg|jpeg|tif)(#|$)", o):
        acc.append(o)

def resolve_loc(url):
    j = get(url + ("&" if "?" in url else "?") + "fo=json")
    acc = []
    # only the item's own files (never the "related items" carousels)
    for r in j.get("resources", []) or []:
        for group in r.get("files", []) or []:
            for f in group if isinstance(group, list) else [group]:
                if isinstance(f, dict) and f.get("url"):
                    acc.append((f["url"], int(f.get("width") or 0), f.get("mimetype") or ""))
        if r.get("image"):
            acc.append((r["image"], 1024, "image/jpeg"))
    for u in (j.get("item", {}).get("image_url") or []):
        m = re.search(r"#h=(\d+)&w=(\d+)", u)
        acc.append((u.split("#")[0], int(m.group(2)) if m else 0, "image/jpeg"))
    best, score = None, -1
    for u, w, mt in acc:
        if not re.search(r"\.(jpg|jpeg)(\?|$)", u) and "default.jpg" not in u:
            continue
        m = re.search(r"/full/pct:([\d.]+)/", u)
        if m:  # IIIF: ask for half size (newspaper pages ~3000 px wide, enough to crop an ad)
            u = re.sub(r"/full/pct:[\d.]+/", "/full/pct:50/", u)
            w = 5000
        elif u.endswith("_150px.jpg"):
            w = 150
        elif u.endswith("r.jpg"):
            w = max(w, 640)
        elif u.endswith("v.jpg"):
            w = max(w, 1024)
        if w > score:
            best, score = u, w
    meta = j.get("item", {})
    return best, {"title": meta.get("title"), "date": meta.get("date"), "rights": str(meta.get("rights_advisory") or meta.get("rights") or "")[:120]}


def get_retry(url, n=3):
    for k in range(n):
        try:
            return get(url, binary=True)
        except Exception as e:
            if k == n - 1:
                raise
            time.sleep(3)

items = json.load(open(sys.argv[1]))
outdir = pathlib.Path("out/archive"); outdir.mkdir(parents=True, exist_ok=True)
log = {}
for it in items:
    url, meta = it["url"], {}
    try:
        if "loc.gov/item/" in url or "loc.gov/resource/" in url:
            url, meta = resolve_loc(url)
            time.sleep(1)
        data = get_retry(url)
        dst = outdir / it["name"]
        dst.write_bytes(data)
        ok = len(data) > 2000 and not data[:15].lower().startswith(b"<!doctype")
        log[it["name"]] = {"ok": ok, "bytes": len(data), "src": url, **meta, "page": it["url"]}
        print(("OK " if ok else "ERR"), f"{len(data):>10}", it["name"], "<-", url)
        if not ok: dst.unlink()
    except Exception as e:
        log[it["name"]] = {"ok": False, "error": str(e), "page": it["url"]}
        print("ERR", it["name"], e)
json.dump(log, open(outdir / "fetch_log.json", "w"), indent=1)
