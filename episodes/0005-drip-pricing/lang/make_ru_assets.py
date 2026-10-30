"""Russian pictures with words baked in for the Ep.4 RU review copy (code-drawn, no generations).
Re-runs the episode's own drawing code (gen_script.py makers, make_edits.py, make_l1_flip.py) with every printed English
word translated and a Cyrillic font of the same character, into lang/ru/images and lang/ru/clips (they win over the
English ones only when FACTORY_LANG=ru). Needs the storyboard cache (.cache/images/0005-drip-pricing) and the Cyrillic
fonts in assets/fonts.  python episodes/0005-drip-pricing/lang/make_ru_assets.py"""
import ast
from pathlib import Path

from PIL import ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
EP = HERE.parent
ROOT = EP.parents[1]
RU = HERE / "ru"
(RU / "images").mkdir(parents=True, exist_ok=True)
(RU / "clips").mkdir(parents=True, exist_ok=True)
F = ROOT / "assets" / "fonts"

WORDS = {
    "ADMIT ONE": "ВХОДНОЙ БИЛЕТ",
    "ROW G · SEAT 12": "РЯД 7 · МЕСТО 12",
    "No. 004": "№ 004",
    "CASE FILE": "ДЕЛО",
    "CASE FILE #004": "ДЕЛО № 004",
    "THE FEE AT THE END": "СБОР В КОНЦЕ",
    "ADD A TIP?": "ДОБАВИТЬ ЧАЕВЫЕ?",
    "CHECKOUT": "ОФОРМЛЕНИЕ",
    "TOTAL": "ИТОГО",
    "PAY": "ОПЛАТИТЬ",
    "BORDER CONTROL": "ПОГРАНИЧНЫЙ КОНТРОЛЬ",
}
CYR = {"Anton-Regular.ttf": "Oswald-Bold.ttf", "ArchivoBlack-Regular.ttf": "Montserrat-Black.ttf",
       "PermanentMarker-Regular.ttf": "ShantellSans-ExtraBold.ttf"}
missing = set()
_text = ImageDraw.ImageDraw.text


def text(self, xy, txt, *a, **kw):
    if isinstance(txt, str) and txt in WORDS:
        f = kw.get("font")
        eb = self.textbbox((0, 0), txt, font=f)
        limit = max(eb[2] - eb[0], 1) * 1.15  # the English line's width (+15 %)
        txt = WORDS[txt]
        name = Path(getattr(f, "path", "")).name
        if name in CYR:
            size = f.size
            g = ImageFont.truetype(str(F / CYR[name]), size)
            box = self.textbbox((0, 0), txt, font=g)
            while box[2] - box[0] > limit and size > 10:
                size = int(size * 0.94)
                g = ImageFont.truetype(str(F / CYR[name]), size)
                box = self.textbbox((0, 0), txt, font=g)
            kw["font"] = g
    elif isinstance(txt, str) and any(c.isalpha() and c.isascii() for c in txt) and txt not in ("$30", "L"):
        missing.add(txt)
    return _text(self, xy, txt, *a, **kw)


ImageDraw.ImageDraw.text = text

# ---- gen_script.py: only its picture makers (the module itself writes script.json)
src = (EP / "gen_script.py").read_text(encoding="utf-8")
tree = ast.parse(src)
keep = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))
        or (isinstance(n, ast.FunctionDef) and n.name in ("_fnt", "make_ticket", "make_ticket_v", "make_folders", "make_tablet", "pulled_back"))
        or (isinstance(n, ast.Assign) and n.lineno < 150)]  # the drawing constants (TK, TV, NK_*...)
g = {"__file__": str(EP / "gen_script.py"), "__name__": "gen_script_ru"}
exec(compile(ast.Module(body=keep, type_ignores=[]), str(EP / "gen_script.py"), "exec"), g)
I = RU / "images"
g["make_ticket"](I / "o1.png")
g["make_ticket_v"](I / "o1v.png")
g["pulled_back"](I / "o1.png", I / "o1w.png", g["NK_L"], g["NA_L"])
g["pulled_back"](I / "o1v.png", I / "o1vn.png", g["NK_S"], g["NA_S"])
g["make_folders"](I / "sub.png")
g["make_tablet"](RU / "next_tablet.png")


def run(script, subs, keep_out):
    s = (EP / script).read_text(encoding="utf-8")
    for a, b in subs:
        assert a in s, (script, a)
        s = s.replace(a, b)
    exec(compile(s, str(EP / script), "exec"), {"__file__": str(EP / script), "__name__": "__main__"})


# make_edits.py: l1 (ticket on the desk) and m1b (checkout page); the other pictures it writes carry no words
run("make_edits.py", [('OUT = HERE / "images"', f'OUT = __import__("pathlib").Path({str(I)!r})'),
                      ], ())
for k in ("c4", "m2", "n4", "l8"):
    (I / f"{k}.png").unlink(missing_ok=True)
# make_l1_flip.py: l2 (BORDER CONTROL back) and clips/l1.mp4 (the flip, front -> back)
run("make_l1_flip.py", [('OUT = HERE / "images"', f'OUT = __import__("pathlib").Path({str(I)!r})'),
                        ('HERE / "clips" / "l1.mp4"', f'__import__("pathlib").Path({str(RU / "clips" / "l1.mp4")!r})')], ())
(I / "z0b.png").unlink(missing_ok=True)
print("RU pictures:", sorted(p.name for p in I.iterdir()), "+ clips/l1.mp4 + next_tablet.png")
print("left in English:", sorted(missing))
