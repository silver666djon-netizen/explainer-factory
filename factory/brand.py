"""Channel brand art (logo / banner ideas): python -m factory.brand brand/logos.json [--send] [--only k1,k2]"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

from .config import ROOT, load_config
from .images import generate, provider


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--out", default=str(ROOT / "out" / "brand"))
    ap.add_argument("--send", action="store_true")
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    spec = json.loads(Path(a.spec).read_text(encoding="utf-8"))
    cfg = copy.deepcopy(load_config())
    cfg["style"]["prompt_prefix"] = ""
    cfg["style"].setdefault("variants", {})["brand"] = {"prompt_suffix": spec.get("suffix", "")}
    cfg["images"]["gemini_quality_suffix"] = spec.get("quality", "Crisp professional vector-like artwork, clean shapes.")
    cfg["images"]["aspect_ratio"] = spec.get("aspect", "1:1")
    if spec.get("size"):
        cfg["images"]["gemini_size"] = spec["size"]
    print("provider:", provider(cfg))
    only = {k for k in a.only.split(",") if k}
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    made = []
    for key, prompt in spec["items"].items():
        if only and key not in only:
            continue
        img = generate(cfg, prompt, "brand")
        p = out / f"{Path(a.spec).stem}-{key}.png"
        img.save(p)
        made.append(p)
        print("made", p.name, img.size)
    if a.send and made:
        from .notify import send_album
        send_album(made, spec.get("caption", Path(a.spec).stem))


if __name__ == "__main__":
    main()
