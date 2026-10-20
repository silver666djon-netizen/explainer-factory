"""One-off probe (Case 003 'The Fake Sale'): LOC photo searches for sale signs, bargain windows, price tags,
department-store crowds, furniture/mattress windows. Saves results + preview images (probe3-*.jpg)."""
import json, time, urllib.request
UA = {"User-Agent": "Mozilla/5.0 CoinSense-archive-probe/1.0"}


def get(url, raw=False, tries=3):
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=90) as r:
                data = r.read()
            return data if raw else json.loads(data.decode())
        except Exception:  # noqa
            if k == tries - 1:
                raise
            time.sleep(4 + 4 * k)


Q = "https://www.loc.gov/photos/?q={}&dates=1930/1965&fo=json&c=25"
searches = {
    "salesign": "sale+sign+store+window",
    "deptsale": "department+store+sale",
    "bargain": "bargain+sale",
    "pricetag": "price+tags",
    "xmascrowd": "christmas+shopping+crowd+department+store",
    "clearance": "clearance+sale",
    "furniture": "furniture+store+window",
    "counter": "department+store+counter+shoppers",
}
out = {}
for k, q in searches.items():
    res = []
    try:
        d = get(Q.format(q))
        for i, r in enumerate(d.get("results", [])[:25]):
            img = (r.get("image_url") or [None])[0]
            item = {"id": r.get("id"), "title": r.get("title"), "date": r.get("date"), "img": img,
                    "rights": r.get("rights_advisory") or r.get("rights")}
            res.append(item)
            if img and i < 14:
                try:
                    url = img if img.startswith("http") else "https:" + img
                    open(f"out/archive/probe3-{k}-{i:02d}.jpg", "wb").write(get(url, raw=True))
                except Exception as e:  # noqa
                    item["img_error"] = str(e)
                time.sleep(0.4)
    except Exception as e:
        res = {"error": str(e)}
    out[k] = res
    time.sleep(1.5)
json.dump(out, open("out/archive/loc_probe3.json", "w"), indent=1)
print("done", {k: (len(v) if isinstance(v, list) else v) for k, v in out.items()})
