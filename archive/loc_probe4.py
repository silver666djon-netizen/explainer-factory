"""One-off probe (Ep.4 r86 item 8): LOC photos of a venue - theatre / concert-hall interior or audience, 1930-1965.
Saves results + preview images (probe4-*.jpg)."""
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
    "theatreaud": "theater+audience",
    "concert": "concert+audience",
    "auditorium": "auditorium+interior",
    "symphony": "symphony+orchestra+concert",
    "theatreint": "theatre+interior",
    "stage": "stage+theater+seats",
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
                    open(f"out/archive/probe4-{k}-{i:02d}.jpg", "wb").write(get(url, raw=True))
                except Exception as e:  # noqa
                    item["img_error"] = str(e)
                time.sleep(0.4)
    except Exception as e:
        res = {"error": str(e)}
    out[k] = res
    time.sleep(1.5)
json.dump(out, open("out/archive/loc_probe4.json", "w"), indent=1)
print("done", {k: (len(v) if isinstance(v, list) else v) for k, v in out.items()})
