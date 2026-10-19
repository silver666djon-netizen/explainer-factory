"""One-off probe (Case 002): LOC searches for a cash register, a grocery price board and a mail-order catalogue page.
Saves results + small preview images (probe2-*.jpg) so Claude can pick. Runs on the Actions runner."""
import json, time, urllib.request, urllib.parse
UA = {"User-Agent": "Mozilla/5.0 CoinSense-archive-probe/1.0"}


def get(url, raw=False):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    return data if raw else json.loads(data.decode())


searches = {
    "register": "https://www.loc.gov/photos/?q=cash+register&dates=1935/1960&fo=json&c=30",
    "pricesign": "https://www.loc.gov/photos/?q=grocery+store+window+prices&dates=1935/1960&fo=json&c=30",
    "catalog": "https://www.loc.gov/search/?q=sears+roebuck+catalogue&fo=json&c=30",
    "catalog2": "https://www.loc.gov/search/?q=montgomery+ward+catalogue&fo=json&c=30",
}
out = {}
for k, u in searches.items():
    res = []
    try:
        d = get(u)
        for i, r in enumerate(d.get("results", [])[:30]):
            img = (r.get("image_url") or [None])[0]
            item = {"id": r.get("id"), "title": r.get("title"), "date": r.get("date"), "img": img,
                    "rights": r.get("rights_advisory") or r.get("rights"), "original_format": r.get("original_format")}
            res.append(item)
            if img and i < 24:
                try:
                    url = img if img.startswith("http") else "https:" + img
                    open(f"out/archive/probe2-{k}-{i:02d}.jpg", "wb").write(get(url, raw=True))
                except Exception as e:  # noqa
                    item["img_error"] = str(e)
                time.sleep(0.5)
    except Exception as e:
        res = {"error": str(e)}
    out[k] = res
    time.sleep(1.5)
json.dump(out, open("out/archive/loc_probe2.json", "w"), indent=1)
print("done", {k: (len(v) if isinstance(v, list) else v) for k, v in out.items()})
