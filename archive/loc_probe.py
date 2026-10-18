"""One-off: query the LOC JSON API for candidate items + newspaper pages, dump a compact list. Runs on the Actions runner."""
import json, sys, time, urllib.request, urllib.parse
UA = {"User-Agent": "Mozilla/5.0 CoinSense-archive-probe/1.0"}
def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())
out = {}
items = ["2017779953", "2017779956", "2017779911", "2017779958", "2017646581", "2004676518", "2018652675", "2018652676", "2017762325"]
for it in items:
    try:
        d = get(f"https://www.loc.gov/item/{it}/?fo=json")
        i = d["item"]
        files = [f for r in d.get("resources", []) for f in (r.get("files") or [[]])[0]]
        best = sorted([f for f in files if f.get("url", "").endswith((".jpg", ".tif"))], key=lambda f: (f.get("width") or 0))[-3:]
        out[it] = {"title": i.get("title"), "date": i.get("date"), "rights": i.get("rights_advisory") or i.get("rights"), "files": [(f.get("url"), f.get("width"), f.get("height")) for f in best]}
    except Exception as e:
        out[it] = {"error": str(e)}
    time.sleep(1)
searches = {
    "lv_1940": "https://www.loc.gov/pictures/search/?q=Las%20Vegas%20Rothstein%201940&fo=json&c=40",
    "slot_machine": "https://www.loc.gov/photos/?q=slot+machine&fo=json&c=40",
    "roulette": "https://www.loc.gov/photos/?q=roulette&fo=json&c=40",
    "wanamaker": "https://www.loc.gov/photos/?q=wanamaker+store&fo=json&c=40",
    "supermarket": "https://www.loc.gov/photos/?q=supermarket+1950&fo=json&c=40",
    "grocery_prices": "https://www.loc.gov/photos/?q=grocery+store+prices&fo=json&c=40",
    "cash_register": "https://www.loc.gov/photos/?q=cash+register+store&fo=json&c=40",
    "gambling_hall": "https://www.loc.gov/photos/?q=gambling+hall&fo=json&c=40",
    "np_wanamaker": "https://www.loc.gov/collections/chronicling-america/?q=wanamaker+one+price&dates=1876/1915&fo=json&c=20",
    "np_roulette": "https://www.loc.gov/collections/chronicling-america/?q=roulette+wheel+gambling&dates=1895/1925&fo=json&c=20",
    "np_grocery": "https://www.loc.gov/collections/chronicling-america/?q=grocery+prices+sale&dates=1915/1925&fo=json&c=20",
}
for k, u in searches.items():
    try:
        d = get(u)
        res = []
        for r in d.get("results", [])[:40]:
            res.append({"id": r.get("id"), "title": r.get("title"), "date": r.get("date"), "img": (r.get("image_url") or [None])[-1], "rights": None})
        out["search_" + k] = res
    except Exception as e:
        out["search_" + k] = {"error": str(e)}
    time.sleep(1.5)
json.dump(out, open("out/archive/loc_probe.json", "w"), indent=1)
print("done", {k: (len(v) if isinstance(v, list) else "item") for k, v in out.items()})
