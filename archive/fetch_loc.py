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
    acc = []; walk(j, acc)
    best = None; score = -1
    for u in acc:
        m = re.search(r"#h=(\d+)&w=(\d+)", u)
        w = int(m.group(2)) if m else (640 if u.endswith("r.jpg") else 1024 if u.endswith("v.jpg") else 0)
        if "pct:" in u:  # IIIF full-size newspaper page
            w = 4000 if "pct:100" in u else (2000 if "pct:50" in u else 1000)
        if u.endswith(".tif"): w = 0  # too big; jpg only
        if w > score: best, score = u.split("#")[0], w
    meta = j.get("item", {})
    return best, {"title": meta.get("title"), "date": meta.get("date"), "rights": meta.get("rights_advisory") or meta.get("rights")}

items = json.load(open(sys.argv[1]))
outdir = pathlib.Path("out/archive"); outdir.mkdir(parents=True, exist_ok=True)
log = {}
for it in items:
    url, meta = it["url"], {}
    try:
        if "loc.gov/item/" in url or "loc.gov/resource/" in url:
            url, meta = resolve_loc(url)
            time.sleep(1)
        data = get(url, binary=True)
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
