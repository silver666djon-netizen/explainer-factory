"""Archive fetchers (tooling v2, item 6): Library of Congress, Smithsonian Open Access, Wikimedia Commons, Internet
Archive (Prelinger). Every downloaded file gets a sidecar <file>.license.json with the source page, the file URL, the
licence, the item's own date (and year), title, creator and the attribution text, and a row in docs/ASSET_LICENSES.md
(tools/asset_license.py). The R48 era check (tools/v2_qc.py) reads the year from that sidecar / row.

Licence gates (an item that fails its gate is never downloaded):
  loc        "Free to Use and Reuse" sets, or rights_advisory "No known restrictions on publication"
  smithsonian  CC0 only (metadata_usage.access == "CC0"); needs SI_API_KEY (free api.data.gov key; DEMO_KEY is rate-limited)
  commons    public domain / CC0 / CC BY / CC BY-SA (attribution stored); never NC, ND, fair use or "unknown"
  prelinger  collection:prelinger items whose licenseurl is a public-domain mark or CC0

  python tools/archives.py probe [out.json]                       reachability of all four APIs (+ one gated search each)
  python tools/archives.py search <source> "<query>" [n]          gated candidates (id, title, date, licence)
  python tools/archives.py fetch  <source> <id or url> <dest file> download + sidecar (+ ASSET_LICENSES row)
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

UA = {"User-Agent": "CoinSense-archive-fetch/2.0 (educational explainer videos; github.com/silver666djon-netizen/explainer-factory)"}


def _get(url: str, binary: bool = False, timeout: int = 120):
    last = None
    for a in range(4):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = r.read()
            return data if binary else json.loads(data.decode("utf-8"))
        except urllib.error.HTTPError as e:  # noqa: PERF203
            last = e
            if e.code == 429:  # loc.gov rate limit: back off for real
                time.sleep(15 * (a + 1))
                continue
            if e.code in (500, 502, 503, 504):
                time.sleep(3 + 4 * a)
                continue
            raise
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 + 2 * a)
    raise RuntimeError(f"GET {url.split('api_key=')[0]}: {last}")


def year_of(s) -> int | None:
    m = re.search(r"\b(1[5-9]\d\d|20\d\d)\b", str(s or ""))
    return int(m.group(1)) if m else None


# ---------------------------------------------------------------- Library of Congress
def _loc_record(url: str, ident: str) -> dict:
    """The item JSON; when loc.gov rate-limits the item endpoint (429, seen from GitHub Actions), the same record from
    the search endpoint (its result carries the item block: rights_advisory, date, image_url)."""
    try:
        return _get(url.split("?")[0].rstrip("/") + "/?fo=json")
    except Exception as e:  # noqa: BLE001
        if "429" not in str(e):
            raise
        num = re.sub(r"\D", "", ident.rstrip("/").rsplit("/", 1)[-1])
        j = _get("https://www.loc.gov/photos/?" + urllib.parse.urlencode({"q": num, "fo": "json", "c": 25}))
        r = next((r for r in j.get("results", []) if str(r.get("id", "")).rstrip("/").endswith(num)), None)
        if not r:
            raise
        it = dict(r.get("item") or {})
        it.setdefault("title", r.get("title"))
        it.setdefault("date", r.get("date"))
        it["image_url"] = r.get("image_url") or it.get("image_url") or []
        it["id"] = r.get("id")
        return {"item": it, "resources": r.get("resources") or [], "partof": r.get("partof")}


def loc_item(ident: str) -> dict:
    url = ident if ident.startswith("http") else f"https://www.loc.gov/item/{ident}/"
    j = _loc_record(url, ident)
    it = j.get("item", {})
    rights = _txt(it.get("rights_advisory"))
    partof = json.dumps(it.get("partof") or j.get("partof") or "").lower()
    free = "free to use and reuse" in partof or LOC_FREE.match(rights) is not None
    # the largest JPEG of the item's own files (not the related-items carousels)
    best, bw = None, -1
    for r in j.get("resources", []) or []:
        files = r.get("files") if isinstance(r.get("files"), list) else []  # the search endpoint gives a count here
        for group in files:
            for f in group if isinstance(group, list) else [group]:
                u = isinstance(f, dict) and f.get("url")
                if u and re.search(r"\.jpe?g(\?|$)", u) and int(f.get("width") or 0) > bw:
                    best, bw = u, int(f.get("width") or 0)
    if not best:
        for u in it.get("image_url") or []:
            m = re.search(r"#h=(\d+)&w=(\d+)", u)
            w = int(m.group(2)) if m else 0
            if re.search(r"\.jpe?g", u) and w > bw:
                best, bw = u.split("#")[0], w
    d = it.get("date") or it.get("created_published_date") or ""
    title = it.get("title") or ""
    creator = ", ".join(it.get("contributor_names") or it.get("creators") or []) if isinstance(it.get("contributor_names"), list) else ""
    return {"source": "Library of Congress", "id": it.get("id") or ident, "source_url": url, "file_url": best,
            "title": title, "creator": creator, "item_date": str(d), "year": year_of(d),
            "licence": ("No known restrictions on publication (LoC" + (", FSA/OWI" if "farm security" in rights.lower() else "") + ")") if free else ("NOT FREE: " + rights.strip()[:120]),
            "licence_url": "https://www.loc.gov/free-to-use/", "ok": bool(free and best),
            "attribution": f"{title} · Library of Congress" + (f", {creator}" if creator else "")}


# "No known restrictions [on publication]." — and NOT the HABS/HAER variant ("...on images made by the U.S. Government;
# images copied from other sources may be restricted"), which is checked per image, so it is refused here
# (FSA/OWI items say "No known restrictions. For information, see U.S. Farm Security Administration/...": free)
LOC_FREE = re.compile(r"\s*no known restrictions(?! on images made by the u\.s\. government)", re.I)


def _txt(v) -> str:
    return " ".join(str(x) for x in v) if isinstance(v, list) else str(v or "")


def loc_search(q: str, n: int = 10) -> list[dict]:
    j = _get("https://www.loc.gov/photos/?" + urllib.parse.urlencode({"q": q, "fo": "json", "c": max(n * 4, 25)}))
    out = []
    for r in j.get("results", []):
        it = r.get("item") if isinstance(r.get("item"), dict) else {}
        rights = _txt(it.get("rights_advisory") or r.get("rights_advisory"))
        if not LOC_FREE.match(rights) and "free to use and reuse" not in json.dumps(r.get("partof") or "").lower():
            continue
        out.append({"id": r.get("id"), "title": r.get("title"), "item_date": r.get("date"), "licence": rights.strip()[:60]})
    return out[:n]


# ---------------------------------------------------------------- Smithsonian Open Access (CC0 only)
def _si_key() -> str:
    return os.environ.get("SI_API_KEY", "").strip() or "DEMO_KEY"


def _si_row(r: dict) -> dict:
    c = r.get("content", {})
    dnr = c.get("descriptiveNonRepeating", {})
    usage = (dnr.get("metadata_usage") or {}).get("access", "")
    media = ((dnr.get("online_media") or {}).get("media") or [])
    img = next((m for m in media if m.get("type") == "Images" and (m.get("usage") or {}).get("access", usage) == "CC0"), None)
    fu = None
    if img:
        res = sorted(img.get("resources") or [], key=lambda x: -(x.get("width") or 0))
        fu = next((x.get("url") for x in res if re.search(r"(jpe?g|jpg)", x.get("label", "") + x.get("url", ""), re.I)), None) or img.get("content")
    ft = c.get("freetext", {})
    d = " ".join(x.get("content", "") for x in (ft.get("date") or []))
    title = r.get("title") or (dnr.get("title") or {}).get("content", "")
    creator = "; ".join(x.get("content", "") for x in (ft.get("name") or []))[:120]
    return {"source": "Smithsonian Open Access", "id": r.get("id"), "source_url": dnr.get("record_link") or dnr.get("guid") or "",
            "file_url": fu, "title": title, "creator": creator, "item_date": d, "year": year_of(d),
            "licence": "CC0 1.0 (Smithsonian Open Access)" if usage == "CC0" else f"NOT CC0: {usage}",
            "licence_url": "https://creativecommons.org/publicdomain/zero/1.0/", "ok": usage == "CC0" and bool(fu),
            "attribution": f"{title} · Smithsonian Institution ({dnr.get('data_source', '')})".strip()}


def si_search(q: str, n: int = 10) -> list[dict]:
    j = _get("https://api.si.edu/openaccess/api/v1.0/search?" + urllib.parse.urlencode(
        {"q": q + " AND online_media_type:Images", "rows": n * 2, "api_key": _si_key()}))
    return [x for x in (_si_row(r) for r in (j.get("response") or {}).get("rows", [])) if x["ok"]][:n]


def si_item(ident: str) -> dict:
    j = _get(f"https://api.si.edu/openaccess/api/v1.0/content/{urllib.parse.quote(ident)}?api_key={_si_key()}")
    return _si_row(j.get("response") or {})


# ---------------------------------------------------------------- Wikimedia Commons
COMMONS_OK = re.compile(r"^(public domain|pd\b|pd-|cc0|cc by(-sa)? ?\d|cc-by(-sa)?-\d)", re.I)
COMMONS_BAD = re.compile(r"\b(nc|nd)\b|non-?commercial|no ?deriv|fair use|unknown", re.I)


def _strip(h: str) -> str:
    return re.sub(r"<[^>]+>", "", h or "").strip()


def _commons_row(p: dict) -> dict:
    ii = (p.get("imageinfo") or [{}])[0]
    em = ii.get("extmetadata") or {}
    v = lambda k: _strip((em.get(k) or {}).get("value", ""))  # noqa: E731
    lic = v("LicenseShortName")
    d = v("DateTimeOriginal") or v("DateTime")
    ok = bool(COMMONS_OK.search(lic)) and not COMMONS_BAD.search(lic) and bool(ii.get("url"))
    artist = v("Artist")[:120]
    title = p.get("title", "").replace("File:", "")
    attr = f"{title} · {artist or 'unknown author'} · {lic}" + (f" ({v('LicenseUrl')})" if v("LicenseUrl") else "") + " · via Wikimedia Commons"
    return {"source": "Wikimedia Commons", "id": p.get("title"), "source_url": ii.get("descriptionurl", ""), "file_url": ii.get("url"),
            "title": title, "creator": artist, "item_date": d, "year": year_of(d), "licence": lic if ok else f"NOT OK: {lic}",
            "licence_url": v("LicenseUrl"), "ok": ok, "attribution": attr,
            "share_alike": "sa" in lic.lower()}


def commons_search(q: str, n: int = 10) -> list[dict]:
    j = _get("https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(
        {"action": "query", "format": "json", "generator": "search", "gsrnamespace": 6, "gsrsearch": f"filetype:bitmap {q}",
         "gsrlimit": n * 3, "prop": "imageinfo", "iiprop": "url|extmetadata|size", "iiextmetadatafilter":
         "LicenseShortName|LicenseUrl|Artist|DateTimeOriginal|DateTime|AttributionRequired"}))
    rows = [_commons_row(p) for p in (j.get("query") or {}).get("pages", {}).values()]
    return [r for r in rows if r["ok"]][:n]


def commons_item(title: str) -> dict:
    if title.startswith("http"):
        title = urllib.parse.unquote(title.rsplit("/", 1)[-1])
    if not title.startswith("File:"):
        title = "File:" + title
    j = _get("https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(
        {"action": "query", "format": "json", "titles": title, "prop": "imageinfo", "iiprop": "url|extmetadata|size"}))
    p = next(iter((j.get("query") or {}).get("pages", {}).values()))
    return _commons_row(p)


# ---------------------------------------------------------------- Internet Archive, Prelinger (public domain only)
def _pd(lic: str, rights: str = "") -> bool:
    """Public Domain Mark, CC0, or the old CC public-domain dedication (creativecommons.org/licenses/publicdomain/)."""
    return bool(re.search(r"publicdomain", lic or "")) or (not lic and bool(re.search(r"(?i)\bpublic domain\b", rights or "")))


def prelinger_search(q: str, n: int = 10) -> list[dict]:
    j = _get("https://archive.org/advancedsearch.php?" + urllib.parse.urlencode(
        [("q", f"collection:prelinger AND ({q})"), ("fl[]", "identifier"), ("fl[]", "title"), ("fl[]", "date"), ("fl[]", "year"),
         ("fl[]", "licenseurl"), ("fl[]", "rights"), ("rows", n * 4), ("output", "json")]))
    docs = (j.get("response") or {}).get("docs", [])
    return [{"id": d["identifier"], "title": d.get("title"), "item_date": d.get("date") or d.get("year"),
             "licence": d.get("licenseurl") or _txt(d.get("rights"))[:60]} for d in docs if _pd(d.get("licenseurl", ""), _txt(d.get("rights")))][:n]


def prelinger_item(ident: str) -> dict:
    ident = ident.rstrip("/").rsplit("/", 1)[-1] if ident.startswith("http") else ident
    j = _get(f"https://archive.org/metadata/{ident}")
    md = j.get("metadata", {})
    lic = md.get("licenseurl", "")
    cols = md.get("collection") if isinstance(md.get("collection"), list) else [md.get("collection")]
    files = j.get("files", [])
    pick = None
    for fmt in ("MPEG4", "h.264", "512Kb MPEG4", "h.264 IA"):
        pick = next((f for f in files if f.get("format") == fmt), None)
        if pick:
            break
    d = md.get("date") or md.get("year") or ""
    ok = _pd(lic, _txt(md.get("rights"))) and "prelinger" in [str(c).lower() for c in cols] and bool(pick)
    return {"source": "Internet Archive · Prelinger Archives", "id": ident, "source_url": f"https://archive.org/details/{ident}",
            "file_url": f"https://archive.org/download/{ident}/{urllib.parse.quote(pick['name'])}" if pick else None,
            "title": md.get("title", ""), "creator": md.get("creator", "") if isinstance(md.get("creator"), str) else "",
            "item_date": str(d), "year": year_of(d), "licence": ("Public Domain Mark 1.0" if "mark" in lic else "CC0 1.0" if "zero" in lic else "Public domain (CC public-domain dedication)" if lic else "Public domain (item rights statement)") if ok else f"NOT PD: {lic or 'no licence'}",
            "licence_url": lic, "ok": ok, "attribution": f"{md.get('title', '')} ({d}) · Prelinger Archives via Internet Archive"}


SOURCES = {"loc": (loc_item, loc_search), "smithsonian": (si_item, si_search), "commons": (commons_item, commons_search),
           "prelinger": (prelinger_item, prelinger_search)}


def fetch(source: str, ident: str, dest: str, register: bool = True) -> dict:
    meta = SOURCES[source][0](ident)
    if not meta.get("ok"):
        raise SystemExit(f"{source} {ident}: refused by the licence gate ({meta.get('licence')})")
    p = Path(dest)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(_get(meta["file_url"], binary=True, timeout=600))
    meta = {**meta, "file": p.name, "fetched": date.today().isoformat()}
    meta.pop("ok", None)
    Path(str(p) + ".license.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    if register:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import asset_license as AL
        AL.upsert({"file": p.name, "source_url": meta["source_url"], "licence": meta["licence"], "date": meta["item_date"] or "",
                   "attribution": meta["attribution"], "kind": "archive", "notes": f"{meta['source']}; file {meta['file_url']}"})
    return meta


def probe(out: str | None = None) -> int:
    tests = [("loc", "Library of Congress (loc.gov JSON API)", lambda: loc_search("ticket booth 1940", 3)),
             ("smithsonian", "Smithsonian Open Access (api.si.edu, key: " + ("SI_API_KEY" if os.environ.get("SI_API_KEY") else "DEMO_KEY") + ")",
              lambda: si_search("cash register", 3)),
             ("commons", "Wikimedia Commons (MediaWiki API)", lambda: commons_search("cash register 1930s", 3)),
             ("prelinger", "Internet Archive · Prelinger (advancedsearch)", lambda: prelinger_search("supermarket", 3))]
    rep = []
    for key, name, fn in tests:
        t0 = time.time()
        try:
            rows = fn()
            rep.append({"source": key, "name": name, "reachable": True, "gated_hits": len(rows), "seconds": round(time.time() - t0, 1),
                        "sample": [(r.get("id"), str(r.get("item_date"))[:20], str(r.get("licence"))[:40]) for r in rows[:2]]})
        except Exception as e:  # noqa: BLE001
            rep.append({"source": key, "name": name, "reachable": False, "error": str(e)[:200], "seconds": round(time.time() - t0, 1)})
        print(json.dumps(rep[-1], ensure_ascii=False), flush=True)
    if out:
        Path(out).write_text(json.dumps(rep, indent=1, ensure_ascii=False))
    return 0


def main(a: list[str]) -> int:
    if a[0] == "probe":
        return probe(a[1] if len(a) > 1 else None)
    if a[0] == "search":
        for r in SOURCES[a[1]][1](a[2], int(a[3]) if len(a) > 3 else 10):
            print(json.dumps(r, ensure_ascii=False))
        return 0
    if a[0] == "fetch":
        print(json.dumps(fetch(a[1], a[2], a[3]), indent=1, ensure_ascii=False))
        return 0
    raise SystemExit(__doc__)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
