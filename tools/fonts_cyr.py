"""Cyrillic fonts for language versions: takes the OFL originals of release "fonts-cyr" (downloaded to a folder) and
writes the static weights the engine uses into assets/fonts (instances of the variable fonts are made here, at build
time, and never redistributed).   python tools/fonts_cyr.py <download dir>"""
import shutil
import sys
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

src = Path(sys.argv[1])
dst = Path(__file__).resolve().parents[1] / "assets" / "fonts"
dst.mkdir(parents=True, exist_ok=True)
for var, out, axes in (("Oswaldwght.ttf", "Oswald-Bold.ttf", {"wght": 700}),
                       ("Montserratwght.ttf", "Montserrat-Black.ttf", {"wght": 900}),
                       ("ShantellSansBNCE-INFM-SPAC-wght.ttf", "ShantellSans-ExtraBold.ttf",
                        {"wght": 800, "BNCE": 0, "INFM": 100, "SPAC": 0})):
    if (src / var).exists():
        instancer.instantiateVariableFont(TTFont(src / var), axes).save(dst / out)
        print("made", out)
for f in ("PTM55FT.ttf", "RussoOne-Regular.ttf", "Pangolin-Regular.ttf"):
    if (src / f).exists():
        shutil.copy(src / f, dst / f)
        print("copied", f)
