"""Episode 0005 — Case file #004 "The fee at the end" (drip pricing). Writes episodes/0005-drip-pricing/script.json
Run: python episodes/0005-drip-pricing/gen_script.py
Scene-list stage: pictures, inserts, plates, stamps and Tab rows are placed; mark coordinates are first guesses and are
measured on the storyboard frames before the preview (rules 11, 15, 16)."""
import copy
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "script.json"
LOC = "Library of Congress, Prints & Photographs Division (no known restrictions)"
LOC_FSA = "Library of Congress, FSA/OWI Collection (no known restrictions)"
LOC_USN = "Library of Congress, U.S. News & World Report Collection (no known restrictions on publication)"
(HERE / "images").mkdir(exist_ok=True)

B = []


def _fnt(name, size):
    from PIL import ImageFont
    for q in (HERE.parent.parent / "assets" / "fonts" / name, Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")):
        if q.exists():
            return ImageFont.truetype(str(q), size)


TICKET_DX = -167  # px in the 1376-wide picture (make_edits.py uses the same offset for the l1 desk composite)


def make_ticket(path, stub_number=True):
    """Code-drawn hero prop (no generation): the same 1950s concert ticket as the Ep.3 teaser, blank price box.
    stub_number=False: the stub is left blank (n1/n2: the fees are written on it before it is cut off)."""
    from PIL import Image, ImageDraw
    W, H = 1376, 768
    im = Image.new("RGB", (W, H), (243, 233, 210))
    d = ImageDraw.Draw(im)
    ink, red, paper = (30, 27, 24), (210, 69, 47), (252, 247, 233)
    x0, y0, x1, y1 = 250 + TICKET_DX, 190, 1130 + TICKET_DX, 590  # centre at 38 % of the frame: the fee column fits on the right
    d.rounded_rectangle((x0, y0, x1, y1), radius=26, fill=paper, outline=ink, width=10)
    sx = x1 - 230
    for yy in range(y0 + 24, y1 - 20, 34):
        d.ellipse((sx - 7, yy - 7, sx + 7, yy + 7), fill=(243, 233, 210), outline=ink, width=3)
    d.rectangle((x0 + 40, y0 + 40, sx - 40, y0 + 150), fill=red)
    d.text(((x0 + sx) / 2, y0 + 95), "ADMIT ONE", font=_fnt("Anton-Regular.ttf", 92), fill=paper, anchor="mm")
    d.text(((x0 + sx) / 2, y0 + 215), "ROW G · SEAT 12", font=_fnt("ArchivoBlack-Regular.ttf", 40), fill=ink, anchor="mm")
    d.rectangle((x0 + 160, y0 + 270, sx - 160, y1 - 40), outline=ink, width=6)
    if stub_number:
        d.text((x1 - 115, (y0 + y1) / 2), "No. 004", font=_fnt("ArchivoBlack-Regular.ttf", 40), fill=ink, anchor="mm")
    im.save(path)


def make_folders(path):
    """Code-drawn case-file stack for the subscribe beat (no generation): four manila folders, staggered tabs
    CASE FILE #001-#004, level, on the left half of a plain cream page; the right half stays clear for the button."""
    from PIL import Image, ImageDraw, ImageFilter
    W, H = 1376, 768
    im = Image.new("RGB", (W, H), (243, 233, 210))
    ink, manila, paper = (30, 27, 24), (222, 186, 120), (252, 247, 233)
    fx, fw, fh, top = 90, 640, 470, 205
    tab_w, tab_h = 148, 64
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rectangle((fx + 14, top + 22, fx + fw + 14, top + 3 * 16 + fh + 22), fill=(0, 0, 0, 90))
    im.paste(sh.filter(ImageFilter.GaussianBlur(14)), (0, 0), sh.filter(ImageFilter.GaussianBlur(14)))
    d = ImageDraw.Draw(im)
    f_small, f_num = _fnt("ArchivoBlack-Regular.ttf", 19), _fnt("ArchivoBlack-Regular.ttf", 30)
    for k in range(4):  # #001 at the back (highest), #004 in front
        y = top + k * 16
        shade = tuple(int(c * (0.86 + 0.045 * k)) for c in manila)
        tx = fx + 18 + k * (tab_w + 6)
        d.rounded_rectangle((tx, y - tab_h, tx + tab_w, y + 12), radius=12, fill=shade, outline=ink, width=4)
        d.rectangle((fx, y, fx + fw, y + fh), fill=shade, outline=ink, width=5)
        d.rectangle((tx + 4, y - 3, tx + tab_w - 4, y + 8), fill=shade)  # the tab joins the folder
        d.text((tx + tab_w / 2, y - tab_h + 20), "CASE FILE", font=f_small, fill=ink, anchor="mm")
        d.text((tx + tab_w / 2, y - tab_h + 46), f"#00{k + 1}", font=f_num, fill=ink, anchor="mm")
    y = top + 3 * 16  # the front folder's label
    lx0, ly0, lx1, ly1 = fx + 90, y + 90, fx + fw - 90, y + 230
    d.rectangle((lx0, ly0, lx1, ly1), fill=paper, outline=ink, width=4)
    d.text(((lx0 + lx1) / 2, ly0 + 42), "CASE FILE #004", font=_fnt("ArchivoBlack-Regular.ttf", 34), fill=ink, anchor="mm")
    d.text(((lx0 + lx1) / 2, ly0 + 98), "THE FEE AT THE END", font=_fnt("Anton-Regular.ttf", 46), fill=ink, anchor="mm")
    im.save(path)


def make_tablet(path):
    """Code-drawn Ep.5 teaser sketch (no generation): a payment tablet with three tip buttons, blank bottom line."""
    from PIL import Image, ImageDraw
    W, H = 1376, 768
    im = Image.new("RGB", (W, H), (243, 233, 210))
    d = ImageDraw.Draw(im)
    ink, red, paper, green = (30, 27, 24), (210, 69, 47), (252, 247, 233), (96, 140, 96)
    x0, y0, x1, y1 = 418, 70, 958, 700
    d.rounded_rectangle((x0, y0, x1, y1), radius=40, fill=(60, 56, 52), outline=ink, width=8)
    d.rounded_rectangle((x0 + 34, y0 + 34, x1 - 34, y1 - 34), radius=18, fill=paper)
    d.text(((x0 + x1) / 2, y0 + 100), "ADD A TIP?", font=_fnt("ArchivoBlack-Regular.ttf", 46), fill=ink, anchor="mm")
    for k, t in enumerate(["18%", "22%", "25%"]):
        by = y0 + 165 + k * 112  # leaves room under the 25 % button for the handwritten "No tip"
        d.rounded_rectangle((x0 + 90, by, x1 - 90, by + 92), radius=18, fill=green if k else red, outline=ink, width=5)
        d.text(((x0 + x1) / 2, by + 46), t, font=_fnt("Anton-Regular.ttf", 58), fill=paper, anchor="mm")
    im.save(path)


make_ticket(HERE / "images" / "o1.png")
make_ticket(HERE / "images" / "n1.png", stub_number=False)
make_folders(HERE / "images" / "sub.png")
make_tablet(HERE / "next_tablet.png")


def beat(id, section, text, visual, **kw):
    b = {"id": id, "section": section, "text": text, "visual": visual}
    b.update(kw)
    B.append(b)
    return b


def img(prompt=None, motion="zoom_in", **kw):
    v = {"type": "image", "motion": motion, "prompt": prompt}
    v.update(kw)
    return v


def manual(v, clip=False):
    """Klot makes this still in ChatGPT (episodes/0005-drip-pricing/images/<beat>.png); clip=True: a Grok clip from that
    still may arrive as clips/<beat>.mp4 (muted, trimmed to the beat, our overlays on top; the still is the fallback)."""
    v["manual"] = True
    if clip:
        v["clip"] = True
    return v


def reuse(b, motion="static", index=0, **kw):
    v = {"type": "reuse", "beat": b, "index": index, "motion": motion}
    v.update(kw)
    return v


def arch(file, caption, credit=LOC_FSA, motion="zoom_in", **kw):
    v = {"type": "archive", "file": file, "look": "print", "credit": credit, "motion": motion, "caption": caption}
    v.update(kw)
    return v


def kin(text=None, bg="paper"):
    v = {"type": "kinetic", "kinetic": {"bg": bg}}
    if text:
        v["text"] = text
    return v


def title(t):
    return {"type": "title", "text": t}


def stat(value, label, **kw):
    return {"type": "stat", "stat": {"value": value, "label": label, **kw}}


def doc(source, headline, body, highlight, on, mark="underline", kicker=None, seed=1, **kw):
    d = {"source": source, "headline": headline, "body": body, "highlight": highlight, "on": on, "mark": mark, "seed": seed}
    if kicker:
        d["kicker"] = kicker
    d.update(kw)
    return {"type": "doc", "doc": d}


def write(text, x, y, w, h, on=None, angle=0, color="red", fnt="marker", **kw):
    m = {"type": "write", "text": text, "x": x, "y": y, "w": w, "h": h, "angle": angle, "color": color, "font": fnt, "dur": 0.7}
    if on is not None:
        m["on"] = on
    m.update(kw)
    if m.get("at") == 0.0 and "on" not in m:
        m.update({"hand": False, "dur": 0.01})
    return m


def circle(x, y, w, h, on, **kw):
    return {"type": "circle", "x": x, "y": y, "w": w, "h": h, "on": on, **kw}


def closeup(on, center, zoom=2.0, marks=None, motion="zoom_in"):
    return {"on": on, "center": center, "zoom": zoom, "marks": marks or [], "motion": motion}


def stamp(text, x, y, on=None, angle=-6, w=0.30, **kw):
    """A small rubber stamp pressed onto the picture by the stamp hand (rule 7); at=0.0 = already there."""
    m = {"type": "stamp", "text": text, "x": x, "y": y, "w": w, "angle": angle, "dur": 0.45, **kw}
    if on is not None:
        m["on"] = on
        m["hand"] = True
    if m.get("at") == 0.0:
        m["hand"] = False
    return m


def chapter(id, section, spoken, card):
    return beat(id, section, spoken, title(card), pause_before=1.0, sting="ub_sting_trumpet", sting_at=-1.0)


def tab(label, amount, on, **kw):
    return {"label": label, "amount": amount, "on": on, **kw}


ALLEGED = "ALLEGED"  # red plate next to the date/source plate while a case is undecided (engine: label "alleged": True)

S_OPEN, S_EXP, S_TM, S_HOTEL, S_BRAIN, S_DEF, S_LAW, S_CHECK, S_CLOSE = (
    "The case", "Tuesday 8:12 PM: The experiment", "Wednesday 10:00 AM: $16.4 billion", "Thursday 11:40 PM: The resort fee",
    "Why a split price feels cheaper", "In defence of the accused", "Friday 9:00 AM: One fee, three laws",
    "Saturday 10:00 AM: Three checks", "Case closed")
LARRY = "{larry}"
# x1/x2 switch (Klot, 2026-10-27): a NEW still (only the top plate, empty cream panel left and right of the lever) and a
# new Grok clip are coming. The clip's first frame (lever on OFF) holds through x1 and x2 with one slow even push; the
# flip plays from "Turn" and the click lands on "on" (clip_sync: the clip's movement is found in the clip itself and
# sped up to fit). ALL-IN PRICES on the top plate; OFF / ON hand-written (marker) on the cream panel left and right of
# the lever's travel, one size, clear of the lever in every frame (rule 25, mark audit check 6).
# Klot's new still + Grok clip (2026-10-28, camera locked): lever on OFF until 3.3 s, flip 3.3-4.0 s, ON after.
# Measured on the clip: top plate x .33-.65, y .155-.27; at the top of the flip (3.5-3.7 s) the knob reaches y .245
# over x .40-.48, so ALL-IN PRICES sits in the upper band of the plate (letters .17-.22). Pivot x .465, y .47; the lever's
# travel spans x .26-.64. OFF / ON mirrored about the pivot on the empty cream at mid-height.
LBL = dict(angle=1.0, color="ink", font="headline", fs=0.058)  # one plate lettering, size and angle for all three
X1_TOP = dict(x=0.49, y=0.19, w=0.26, h=0.06, **LBL, short={"fs": 0.070})  # Shorts: larger (Klot r78), still clear of the knob
X1_OFF = dict(x=0.17, y=0.46, w=0.09, h=0.08, **LBL, short={"fs": 0.11})
X1_ON = dict(x=0.76, y=0.46, w=0.09, h=0.08, **LBL, short={"fs": 0.11})
X_FIT = [0.04, 0.96]  # Shorts: the whole panel width stays in the window (pull back, blurred background)
X_PUSH = 0.006  # zoom per second: ~1.00 -> 1.09 over x1 + x2, one continuous push across the cut
TICKET_PRICE_BOX = dict(x=0.2965, y=0.660, w=0.20, h=0.10)  # centred in the price box (.177-.416 x .599-.716), ~60 % of its height
# the fee column on the clear paper right of the ticket (border at .70): left-aligned from .745, even 11 % line pitch
# (Klot r78 G3: centred on the empty paper between the ticket's edge .70 and the frame margin, inside the push)
FEE = lambda y, **kw: dict(x=0.835, y=y, w=0.19, h=0.068, fs=0.062, align="left", **kw)
FEE_Y = (0.37, 0.48, 0.59)
SUM_RULE = dict(type="underline", x=0.818, y=0.637, w=0.15, h=0.01, color="ink", target=[0.743, 0.555, 0.893, 0.625])
SUM = dict(x=0.835, y=0.71, w=0.19, h=0.068, fs=0.062, align="left")
SUM_RING = dict(type="circle", x=0.815, y=0.712, w=0.18, h=0.105, target=[0.748, 0.676, 0.888, 0.748])

# a5 queue (Klot r78 G2): A / B sit on the green arch -> white paint-pen; the prices sit in the window glass and the
# arch frame -> red marker on a cream plate. ARCH_PEN: one letter size for the line on the arch (a7).
AB_A = dict(x=0.30, y=0.20, w=0.05, h=0.08, color="#FFFFFF")
AB_B = dict(x=0.70, y=0.20, w=0.05, h=0.08, color="#FFFFFF")
GLASS_A = dict(x=0.405, y=0.300, w=0.070, h=0.058, plate=[1.25, 1.30])
GLASS_B = dict(x=0.605, y=0.292, w=0.066, h=0.054, plate=[1.25, 1.30])
GLASS_B2 = dict(x=0.605, y=0.345, w=0.076, h=0.042, plate=[1.20, 1.30])
ARCH_PEN = dict(color="#FFFFFF", align="left", fs=0.040)
WOOD_PEN = dict(color="#FFFFFF", align="left")  # on the l1 desk wood: white paint-pen (G2)

# ------------------------------------------------------------------ cold open (≤ 15 s to the folder)
beat("o1", S_OPEN, "A concert ticket. Thirty dollars.",
     img("the code-drawn $30 concert ticket", note="hand-made frame: images/o1.png (code-drawn)", motion="static", hand_marks=True, marks=[write("$30", on="Thirty", **TICKET_PRICE_BOX, color="ink")]),
     pause_at={"word": "Thirty", "sec": 0.45, "hit": "stamp"}, ledger=[tab("TICKET", "$30.00", "Thirty")], label="Illustration")
beat("o2", S_OPEN, "Then the fees. Eight. Six. Four.",
     reuse("o1", hand_marks=True, marks=[write("$30", at=0.0, **TICKET_PRICE_BOX, color="ink"),
                                         write("+ $8 fee", on="Eight.", dur=0.45, **FEE(FEE_Y[0])),
                                         write("+ $6 fee", on="Six.", chain=True, dur=0.45, **FEE(FEE_Y[1])),
                                         write("+ $4 fee", on="Four.", chain=True, dur=0.45, **FEE(FEE_Y[2]))]),
     # (Klot, option 2: the fee rows and PAID go on Larry's tab in one pass at b1, "Eighteen dollars of fees")
     label="Illustration", hold=0.35)  # the third fee finishes before the cut
beat("o3", S_OPEN, "Total: forty-eight.",
     reuse("o1", hand_marks=True,  # no push: the fee column stays clear of Larry's tab and of the ILLUSTRATION plate
           marks=[write("$30", at=0.0, **TICKET_PRICE_BOX, color="ink"),
                  write("+ $8 fee", at=0.0, **FEE(FEE_Y[0])), write("+ $6 fee", at=0.0, **FEE(FEE_Y[1])),
                  write("+ $4 fee", at=0.0, **FEE(FEE_Y[2])),
                  dict(SUM_RULE, on="Total:", dur=0.3, hand=True), write("= $48", on="forty-eight.", dur=0.5, chain=True, **SUM),
                  dict(SUM_RING, on="forty-eight.", delay=0.6, dur=0.45, chain=True, hand=True)]),  # ruled, written, then ringed in red
     pause_at={"word": "forty-eight.", "sec": 0.45, "hit": "stamp"}, label="Illustration")
beat("o4", S_OPEN, "Larry is made up. The fees are not.",
     manual(img(f"{LARRY} sitting at a kitchen table at night, lit by the glow of a cream retro laptop, a paper concert ticket propped against a coffee cup, plain cream background",
         motion="static",
         hand_marks=True, marks=[write("FICTIONAL", on="made", x=0.655, y=0.275, w=0.118, h=0.047, color="#FFFFFF", align="left", hand_scale=0.6),
                                 write("REAL", on="fees", x=0.655, y=0.335, w=0.118, h=0.047, color="#FFFFFF", align="left", hand_scale=0.6, dur=0.45)],
         clip_until=3.0), clip=True),  # Grok clip (Klot): only 0-3 s, the push-in later takes the ticket out of frame; dark cabinets: white pen
     caption_x=0.64)  # the ticket sits low-left: this beat's subtitles move right, clear of it

# ------------------------------------------------------------------ the case + suspect no. 1
beat("cf1", S_OPEN, "Case file number four. The fee at the end.",
     {"type": "casefile", "casefile": {"mode": "open", "number": "004", "title": "The fee at the end", "typed": False, "open_stamp_on": "end.",
                                        "inside": ["SUBJECT: Larry (fictional)", "EXHIBIT: one $30 ticket", "", "SUSPECTS: 2", "STATUS: open"]}})
# (the handwritten "paid: $48" note was dropped: it could only start ~0.3 s before the cut, Klot 22 Oct)
beat("m1", S_OPEN, "Suspect number one. Name: the checkout fee. Aliases: service fee, processing fee, convenience fee.",
     {"type": "mugshot", "prompt": "a long curling blank paper till receipt hanging from a small nail on a plain light grey wall, nothing else in the picture, studio lighting",
      "suspect": {"number": 1, "name": "The checkout fee", "alias": "Service · Processing · Convenience", "tag": "SUSPECT", "stamp_pos": [0.70, 0.12],
                  "type_on": ["Name:", "Aliases:"]}})
beat("m1b", S_OPEN, "Last seen: one click before Pay. It never touches the price you see. It waits for the price you pay.",
     img("a cream 1950s-styled retro laptop seen from the front, its screen completely blank and softly lit, plain cream background",
         note="after the storyboard: code-drawn checkout page (red PAY button, empty total box) composited on the screen (images/m1b.png)",
         motion="static", hand_marks=True, marks=[circle(0.55, 0.4635, 0.14, 0.085, "Pay.", target=[0.50, 0.44, 0.60, 0.487])],
         closeup=closeup("waits", [0.50, 0.40], 1.8, [write("$48", on="pay.", x=0.535, y=0.40, w=0.09, h=0.04)])), ledger_hide=True)

# ------------------------------------------------------------------ Tuesday 8:12 PM — The experiment (StubHub, spine)
chapter("t1", S_EXP, "Tuesday, eight-twelve p.m.", "Tuesday 8:12 PM — The experiment")
beat("a1", S_EXP, "Larry has a ticket in his basket.",
     reuse("o4", push={"center": [0.62, 0.45], "zoom": 1.5}), hero=True)
beat("a2", S_EXP, "To see how the fees got there, we go back to 2015,",
     arch("box_office_loews_capitol_1939.jpg", "Ticket line, Loew's Capitol, Washington, D.C., 1939 · Library of Congress", motion="zoom_in"),
     label="StubHub · 2015")
beat("a2b", S_EXP, "and a company that tested them on its own customers.",
     arch("radio_city_ticket_booth_1942.jpg", "Waiting to buy tickets, Radio City Music Hall, New York, 1942 · Library of Congress", motion="zoom_in"),
     label="StubHub · 2015")
beat("a3", S_EXP, "StubHub, the ticket resale site, was owned by eBay back then.",
     doc("NBER Working Paper 25186 · Blake, Moshary, Sweeney & Tadelis", "Price Salience and Product Choice",
         "Between August 19 and August 31 of 2015, the firm ran an experiment where treated consumers were initially shown ticket prices without fees.",
         "shown ticket prices without fees", on="StubHub,", kicker="WORKING PAPER  ·  QUOTED", seed=71, lead=0.4))
beat("a4", S_EXP, "For a couple of years before that summer, it showed every fee upfront. The price on the screen was the price you paid.",
     img("a 1950s theatre ticket window with a large blank cream price board above the glass, warm light, nobody inside, plain cream wall",
         motion="static", hand_marks=True, marks=[write("TOTAL $48", on="every", x=0.50, y=0.22, w=0.26, h=0.09, color="ink")],
         closeup=closeup("price", [0.50, 0.28], 1.5, [write("TOTAL $48", at=0.0, x=0.50, y=0.22, w=0.26, h=0.09, color="ink"),
                                                       circle(0.50, 0.22, 0.30, 0.13, "paid.", target=[0.37, 0.17, 0.63, 0.27])])),
     label="Illustration", ledger_hide=True)
beat("a5", S_EXP, "Then, for twelve days in August 2015, it split its buyers in two.",
     img("a 1950s theatre lobby with a velvet rope splitting a queue of cheerful cartoon ticket buyers into two lines in front of two identical ticket windows, front view",
         motion="static", hand_marks=True, marks=[write("A", on="split", **AB_A), write("B", on="buyers", chain=True, **AB_B)]),
     label="Aug 19–31, 2015", ledger_hide=True)
beat("a6", S_EXP, "Half kept the full price on screen. The other half saw the ticket alone, with the fees waiting at checkout.",
     reuse("a5", hand_marks=True, marks=[write("A", at=0.0, **AB_A), write("B", at=0.0, **AB_B),
                                         write("$48", on="full", **GLASS_A), write("$30", on="alone,", **GLASS_B)],
           closeup=closeup("fees", [0.62, 0.36], 1.7, [write("B", at=0.0, **AB_B), write("$30", at=0.0, **GLASS_B),
                                                       write("+ fees", on="waiting", **GLASS_B2)])),  # in window B's glass, cream plates
     label="Aug 19–31, 2015", ledger_hide=True)
# a7 (was a kinetic card, Klot r78 item 1): the hand writes the line in white paint-pen on the green arch above the windows
beat("a7", S_EXP, "Same tickets. Same fees. The only thing that changed was the moment you saw them.",
     reuse("a5", hand_marks=True, cam_rate=0.008,
           marks=[write("A", at=0.0, **AB_A), write("B", at=0.0, **AB_B), write("$48", at=0.0, **GLASS_A), write("$30", at=0.0, **GLASS_B),
                  write("+ fees", at=0.0, **GLASS_B2),
                  write("SAME FEES.", on="fees.", x=0.412, y=0.168, w=0.135, h=0.052, **ARCH_PEN),
                  write("NEW MOMENT.", on="moment", x=0.577, y=0.168, w=0.172, h=0.052, **ARCH_PEN)]),
     label="Aug 19–31, 2015", ledger_hide=True)
beat("a8", S_EXP, "The ones who met the fees late spent almost twenty-one percent more.",
     stat(21, "more spent when fees came at checkout · NBER w25186 · 2015 test", prefix="≈", suffix="%"),
     pause_at={"word": "twenty-one", "sec": 0.6, "hit": "stamp"})
beat("a9", S_EXP, "They were fourteen point one percent more likely to buy at all.",
     stat(14.1, "more likely to buy · NBER w25186 · 2015 test", decimals=1, suffix="%"),
     pause_at={"word": "fourteen", "sec": 0.6, "hit": "stamp"})
beat("a10", S_EXP, "And the buyers among them picked seats about five percent pricier.",
     manual(img("a 1950s concert hall seen from the stage, rows of red velvet seats, the front rows lit by a warm spotlight, empty hall",
         motion="static", hand_marks=True, marks=[write("+5 %", on="five", x=0.70, y=0.40, w=0.10, h=0.07, plate=[1.35, 1.45])]), clip=True),  # cream plate on the seats: the clip's push-in takes the floor away
     pause_at={"word": "five", "sec": 0.5, "hit": "stamp"})
beat("a11", S_EXP, "A seat looks cheaper when its fees are still offstage, so you pick a better one.",
     manual(img("last frame of the a10 clip", note="images/a11.png = last frame of clips/a10.mp4", motion="static",
                push={"center": [0.50, 0.60], "zoom": 1.15})),
     label="Seat choice = at least 28 % of the revenue gap · NBER w25186")
beat("a12", S_EXP, "Then the fees walk on.",
     manual(img("three small paper price slips with tiny cartoon legs walking onto a 1950s theatre stage in a spotlight, red curtain, playful print-ad style",
         motion="static", hand_marks=True, clip_until=4.0, short_still=True,  # Grok clip: the slips walk to centre stage and stop (frozen at 4.0 s); the Short keeps the still
         marks=[write("$8", at=4.05, on_object=True, dur=0.3, x=0.3732, y=0.5499, w=0.065, h=0.09, angle=5.3, color="ink", short={"x": 0.184, "y": 0.544, "angle": -6, "w": 0.06, "h": 0.075, "at": 0.45}),
                write("$6", at=4.47, on_object=True, dur=0.3, chain=True, x=0.4933, y=0.5499, w=0.065, h=0.09, angle=-1.8, color="ink", short={"x": 0.3, "y": 0.547, "angle": -6, "w": 0.06, "h": 0.075, "at": 0.87}),
                write("$4", at=4.89, on_object=True, dur=0.3, chain=True, x=0.6193, y=0.5548, w=0.065, h=0.09, angle=6.1, color="ink", short={"x": 0.424, "y": 0.543, "angle": 11, "w": 0.06, "h": 0.075, "at": 1.29})]), clip=True),
     hold=3.6)  # the line, then the three prices go on the stopped slips
beat("a13", S_EXP, "Twelve days of science. Then the science went live.", kin())
beat("a14", S_EXP, "On September the first, the whole site switched. Fees at the end, for everyone.",
     arch("radio_city_crowd_1942.jpg", "Crowd waiting to buy tickets, Radio City Music Hall, New York, 1942 · Library of Congress", motion="zoom_in"),
     stamp={"text": "Sept 1, 2015", "on": "first,"}, label="NBER w25186")

# ------------------------------------------------------------------ Wednesday 10:00 AM — $16.4 billion (Ticketmaster, ALLEGED)
chapter("t2", S_TM, "Wednesday, ten a.m.", "Wednesday 10:00 AM — $16.4 billion")
beat("b1", S_TM, "Larry reads his receipt. Eighteen dollars of fees on a forty-eight-dollar ticket.",
     manual(img(f"{LARRY} at a breakfast table frowning at a long paper receipt that unrolls across the table, coffee cup, plain cream background",
         motion="static", hand_marks=True, marks=[write("$18 FEES", on="Larry", fade_after=0.75, short={"fade_after": None}, x=0.84, y=0.56, w=0.16, h=0.07)]), clip=True),
     ledger=[tab("SERVICE FEE", "+$8.00", "Eighteen", dur=0.42), tab("FACILITY FEE", "+$6.00", "Eighteen", dur=0.42, chain=True),
             tab("PROCESSING FEE", "+$4.00", "Eighteen", dur=0.42, chain=True), tab("PAID", "$48.00", "Eighteen", dur=0.42, chain=True),
             tab("HIDDEN", "$18.00", "Eighteen", dur=0.5, chain=True, loss=True, circle=True)])  # one pass of the tab hand
beat("b2", S_TM, "That's thirty-seven and a half percent of what he paid.",
     stat(37.5, "of Larry's total was fees · Illustration", decimals=1, suffix="%"),
     pause_at={"word": "thirty-seven", "sec": 0.6, "hit": "stamp"})
beat("b3a", S_TM, "Is that unusual?",  # Klot r78 item 7: the statue appears once; this line is on Larry's ticket + the 37.5 % note
     reuse("o1", hand_marks=True, push={"center": [0.56, 0.50], "zoom": 1.15}, cam_rate=0.012,
           marks=[write("$30", at=0.0, **TICKET_PRICE_BOX, color="ink"), write("= 37.5 %", at=0.0, **FEE(0.44)), write("IN FEES", at=0.0, **FEE(0.55))]),
     label="Illustration")
beat("b3", S_TM, "In September 2025, America's Federal Trade Commission and seven states sued Live Nation and Ticketmaster.",
     arch("ftc_statue_1943.jpg", "Statue in front of the Federal Trade Commission building, Washington, D.C., 1943 · Library of Congress", motion="zoom_in",
          one_shot=True),
     label="FTC v. Live Nation/Ticketmaster · filed Sept 2025 · case pending", alleged=True)
B4_DOC = ("FTC complaint · C.D. Cal. · Sept 2025 · ¶36", "Ticketmaster fees",
          "The average percentage of fees charged on tickets ranges from 24% to 44% of the total price.", "24% to 44% of the total price")
beat("b4", S_TM, "They allege the fees run from twenty-four to forty-four percent of the total price.",
     doc(*B4_DOC, on="twenty-four", kicker="COMPLAINT  ·  ALLEGED  ·  QUOTED", seed=72, lead=0.6),
     pause_at={"word": "twenty-four", "sec": 0.4, "hit": None})
beat("b5", S_TM, "And that fans paid over sixteen point four billion dollars in mandatory fees.",
     stat(16.4, "in mandatory fees · FTC complaint, Sept 2025 · ALLEGED", decimals=1, prefix="$", suffix="bn"),
     pause_at={"word": "sixteen", "sec": 0.6, "hit": "stamp"})
beat("b6", S_TM, "Larry's thirty-seven and a half percent sits right inside that range.",
     {"type": "chart", "chart": {"kind": "bar", "title": "Fees as a share of the total", "labels": ["Low (alleged)", "Larry", "High (alleged)"],
                                 "values": [24, 37.5, 44], "unit": "%", "highlight": 1, "value_labels": True,
                                 "note": "FTC complaint ¶36 (alleged) · Larry: illustration"}})
beat("b7", S_TM, "His thirty-dollar ticket grew by sixty percent between the first screen and the last.",
     reuse("o1", hand_marks=True, marks=[write("$30", at=0.0, **TICKET_PRICE_BOX, color="ink"), write("+60 %", on="sixty", x=0.85, y=0.45, w=0.18, h=0.10)]),
     pause_at={"word": "sixty", "sec": 0.5, "hit": "stamp"}, label="Illustration",
     ledger=[tab("= 37.5 % of the total · +60 % on the $30 shown", "", "sixty", note=True)])
beat("b8", S_TM, "Larry, it turns out, is perfectly average.", reuse("b1", push={"center": [0.40, 0.35], "zoom": 1.7}), hero=True)
beat("b9", S_TM, "In September 2026, a judge refused to throw the case out. It goes on.",
     doc("U.S. District Court, C.D. Cal. · Order · Sept 28, 2026", "Motion to dismiss",
         "For the reasons stated herein, Defendant's Motion is DENIED as to each claim.",
         "DENIED as to each claim", on="refused", kicker="COURT ORDER  ·  QUOTED", seed=73, lead=0.6), alleged=True)
beat("b9b", S_TM, "Until a court decides, every word of it is an allegation.",  # item 7: push-in on the b4 complaint card
     doc(*B4_DOC, on="Until", kicker="COMPLAINT  ·  ALLEGED  ·  QUOTED", seed=72, lead=0.0, push_on="Until", push_ease=1.2),
     label="FTC v. Live Nation/Ticketmaster · case pending", alleged=True)

# ------------------------------------------------------------------ Thursday 11:40 PM — The resort fee (Marriott, ALLEGED)
chapter("t3", S_HOTEL, "Thursday, eleven-forty p.m.", "Thursday 11:40 PM — The resort fee")
beat("c1", S_HOTEL, "Larry needs a hotel for the concert. Downtown. Nowhere near a beach.",
     manual(img(f"{LARRY} standing with a small suitcase in a plain downtown hotel lobby at night, a framed poster of a sunny beach on the wall behind him, plain cream background",
         motion="static", hand_marks=True, marks=[write("DOWNTOWN", on="concert.", x=0.660, y=0.575, w=0.150, h=0.085, color="#FFFFFF")]), clip=True))
# c1 Grok clip (Klot): by ~3 s the push-in swaps the dark right wall for the window, so DOWNTOWN is written by 2.5 s (on
# "concert."); the clip plays to its end (he glances at the beach poster)
beat("m2", S_HOTEL, "Suspect number two. Name: the resort fee. Aliases: amenity fee, destination fee.",
     {"type": "mugshot", "prompt": "an old hotel room key on a smooth oval brass key fob with a polished, completely plain surface, hanging from a small nail on a plain light grey wall, nothing else in the picture, studio lighting",
      "suspect": {"number": 2, "name": "The resort fee", "alias": "Amenity fee · Destination fee", "tag": "SUSPECT", "stamp_pos": [0.70, 0.12],
                  "type_on": ["Name:", "Aliases:"]}})
beat("m2b", S_HOTEL, "Known associates: a pool you will never swim in.",
     manual(img("a small inflatable paddling pool standing on the carpet of a plain 1950s city hotel room, a radiator and a window with city lights behind, playful print-ad style",
         motion="static", cam_rate=0.010, clip_until=4.6,  # Klot r78 item 2: one shot, the clip ends on the fully inflated
         clip_sync={"from": "Known", "to": "swim", "to_delay": 0.0, "start": 0.0, "end": 4.6}), clip=True),  # pool and holds it
     ledger_hide=True)  # Larry's tab steps aside: lamp and bed sit top right
beat("c2", S_HOTEL, "In 2019, the Attorney General for Washington, D.C., sued Marriott.",
     arch("hotel_clerk_dover_1938.jpg", "Hotel clerk at desk, Dover, Delaware, 1938 · Library of Congress", motion="zoom_in"),
     label="DC Attorney General v. Marriott · July 2019", alleged=True)
beat("c3", S_HOTEL, "The lawsuit says at least one hundred and eighty-nine Marriott hotels charged these fees:",
     stat(189, "Marriott hotels with resort fees · DC complaint, 2019 · ALLEGED"),
     pause_at={"word": "one", "sec": 0.5, "hit": "stamp"})
# c4/c5/c7 hotel bill (Klot r78 item 3): no blank form on screen - the camera starts on the first table line and the hand
# writes RESORT FEE ... $9-$95 as the shot starts; then TAXES AND FEES as a level heading in the header row, then the ring.
# Measured on images/c4.png: header row y .315-.415 (description box x .33-.517), first line y .425-.47 (description
# x .376-.581, amount x .581-.654). Red on the cream paper only (G2).
BILL_PUSH = {"center": [0.47, 0.40], "zoom": 1.75}
BILL_FEE = dict(x=0.437, y=0.449, w=0.110, h=0.040, fs=0.034, align="left")   # both inside the description column,
BILL_AMT = dict(x=0.540, y=0.449, w=0.070, h=0.040, fs=0.034, align="left")   # clear of the amount column's rule
BILL_HEAD = dict(x=0.432, y=0.368, w=0.175, h=0.046, fs=0.040, color="ink", align="left")
BILL_RING = dict(type="circle", x=0.432, y=0.368, w=0.205, h=0.085, target=[0.340, 0.340, 0.522, 0.396])
beat("c4", S_HOTEL, "from nine to ninety-five dollars, per room, per day.",
     img("a 1950s hotel bill on a desk: a cream sheet with a plain green header band, plain ruled lines and empty columns, a fountain pen beside it, plain cream background",
         motion="static", hand_marks=True, push=BILL_PUSH, cam_rate=0.008,
         marks=[write("RESORT FEE", at=0.05, dur=0.5, **BILL_FEE), write("$9–$95", on="ninety-five", chain=True, dur=0.45, **BILL_AMT)]),
     alleged=True, ledger_hide=True)  # the pen reaches into the tab's corner (G6)
beat("c5", S_HOTEL, "Near the end of booking, the fee sat under a heading that sounded official: Taxes and Fees.",
     reuse("c4", hand_marks=True, push=BILL_PUSH, cam_rate=0.008, cam_continue=True,
           marks=[write("RESORT FEE", at=0.0, **BILL_FEE), write("$9–$95", at=0.0, **BILL_AMT),
                  write("TAXES AND FEES", on="official:", delay=0.25, dur=0.6, **BILL_HEAD), dict(BILL_RING, on="Fees.", dur=0.45, hand=True, chain=True)]),
     hold=0.5, ledger_hide=True)
beat("c6", S_HOTEL, "From customers in D.C. alone, the Attorney General says, that came to millions of dollars.",
     doc("DC Attorney General · press release · July 9, 2019", "Marriott resort fees",
         "Marriott has charged resort fees to tens of thousands of District consumers over the years, totaling millions of dollars.",
         "totaling millions of dollars", on="millions", kicker="PRESS RELEASE  ·  ALLEGED  ·  QUOTED", seed=74, lead=0.6))
beat("c7", S_HOTEL, "Resort fees aren't taxes. They just like to sit next to them.",  # (was a kinetic card, Klot r78 item 1)
     reuse("c4", hand_marks=True, push=BILL_PUSH, cam_rate=0.008,
           marks=[write("RESORT FEE", at=0.0, **BILL_FEE), write("$9–$95", at=0.0, **BILL_AMT), write("TAXES AND FEES", at=0.0, **BILL_HEAD),
                  dict(BILL_RING, at=0.0, dur=0.01, hand=False), write("NOT A TAX", on="aren't", dur=0.55, x=0.437, y=0.494, w=0.110, h=0.040, fs=0.034, align="left")]),
     alleged=True, ledger_hide=True)
beat("c8", S_HOTEL, "In 2023, Marriott agreed with Texas to show the total price most prominently.",
     arch("hotel_sign_cooperstown_1937.jpg", "Hotel sign, Cooperstown, New York, 1937 · Library of Congress", motion="zoom_in"),
     label="Texas Attorney General · May 2023")

# ------------------------------------------------------------------ Why a split price feels cheaper (insert, ~25 s)
# n1/n2 (Klot r78 item 4, replaces the scissors): the code-drawn o1 ticket with a blank stub (images/n1.png). On "split
# prices" $30 goes in the price box and "+ $18 / FEES" on the stub; on "base and a surcharge" the hand draws a dashed cut
# line down the perforation, then the ticket separates cleanly along it: the stub slides 8 % right, eased (visual
# "split": the right piece of the picture moves, marks with "follow" ride on it). One slow push across n1 and n2.
# Ticket (1376 x 768): x .060-.700, y .247-.768; perforation x .5327; stub x .533-.70.
N_CUT = 0.5327
N_FEE1 = dict(x=0.616, y=0.452, w=0.120, h=0.085, color="ink", follow=True)
N_FEE2 = dict(x=0.616, y=0.572, w=0.110, h=0.080, color="ink", follow=True)
N_DASH = dict(type="dash", x=N_CUT - 0.008, y=0.508, w=0.01, h=0.480)
N_SAME = dict(x=0.573, y=0.160, w=0.260, h=0.075)
N_FIT = [0.04, 0.82]  # Shorts: the whole ticket and the slid stub stay in the window
N_PUSH = 0.006
beat("n1", S_BRAIN, "Why does it work? In 1998, three marketing researchers split prices into a base and a surcharge.",
     img("the code-drawn $30 concert ticket, blank stub", note="code-drawn: images/n1.png (gen_script make_ticket)", motion="static",
         hand_marks=True, short_fit=N_FIT, cam_rate=N_PUSH,
         split={"x": N_CUT, "dx": 0.08, "on": "surcharge.", "delay": 0.35, "dur": 0.75},
         marks=[write("$30", on="split", dur=0.5, **TICKET_PRICE_BOX, color="ink"),
                write("+ $18", on="prices", chain=True, dur=0.45, **N_FEE1), write("FEES", on="prices", delay=0.5, chain=True, dur=0.4, **N_FEE2),
                dict(N_DASH, on="base", chain=True, dur=0.5, hand=True)]),
     label="Morwitz, Greenleaf & Johnson · J. Marketing Research · 1998",
     sfx_at=[{"on": "surcharge.", "delay": 0.35, "kind": "paper"}])
beat("n2", S_BRAIN, "The total price was the same. It was just served in pieces.",
     reuse("n1", hand_marks=True, short_fit=N_FIT, cam_rate=N_PUSH, cam_continue=True, split={"x": N_CUT, "dx": 0.08, "done": True},
           marks=[write("$30", at=0.0, **TICKET_PRICE_BOX, color="ink"), write("+ $18", at=0.0, **N_FEE1), write("FEES", at=0.0, **N_FEE2),
                  dict(N_DASH, at=0.0, dur=0.01, hand=False), write("SAME TOTAL", on="same.", **N_SAME)]),
     label="Morwitz, Greenleaf & Johnson · J. Marketing Research · 1998")
# n3 (was a kinetic card, Klot r78 item 1): the cold-open ticket with its fee column and total; the hand writes the
# finding above the ticket, on the clear cream (clear of Larry's tab, top right)
N3_A = dict(x=0.380, y=0.105, w=0.40, h=0.068, align="left", fs=0.064)
N3_B = dict(x=0.380, y=0.190, w=0.40, h=0.068, align="left", fs=0.064)
beat("n3", S_BRAIN, "People remembered paying less in total. And they bought more.",
     reuse("o1", hand_marks=True, cam_rate=0.008, short_fit=[0.04, 0.96],
           marks=[write("$30", at=0.0, **TICKET_PRICE_BOX, color="ink"),
                  write("+ $8 fee", at=0.0, **FEE(FEE_Y[0])), write("+ $6 fee", at=0.0, **FEE(FEE_Y[1])), write("+ $4 fee", at=0.0, **FEE(FEE_Y[2])),
                  dict(SUM_RULE, at=0.0, dur=0.01, hand=False), write("= $48", at=0.0, **SUM), dict(SUM_RING, at=0.0, dur=0.01, hand=False),
                  write("REMEMBERED: LESS", on="remembered", dur=0.75, **N3_A), write("BOUGHT: MORE", on="bought", dur=0.6, **N3_B)]),
     label="Morwitz, Greenleaf & Johnson · J. Marketing Research · 1998")
beat("n4", S_BRAIN, "Your brain files the first number. Everything after it is small print.",
     img("an open 1950s office filing drawer with one large blank index card standing at the front and a few tiny crumpled paper slips at the very back, plain cream background",
         motion="static", hand_marks=True, marks=[write("$30", on="first", x=0.442, y=0.412, w=0.120, h=0.090, angle=-12, color="ink"),
                                                  write("+ fees", on="small", x=0.432, y=0.503, w=0.110, h=0.052, angle=-12, color="ink")]),
     ledger_hide=True)  # the drawer reaches into the tab's corner (G6)
beat("sub", S_BRAIN, "If you like catching prices in the act, subscribe. The Inspector has more files.",  # Klot r78 item 6
     img("code-drawn case-file stack", note="code-drawn: images/sub.png (gen_script make_folders)", motion="static", cam_rate=0.008, one_shot=True),
     cta={"on": "subscribe.", "click_on": "Inspector", "pos": [0.60, 0.44]}, ledger_hide=True)

# ------------------------------------------------------------------ In defence of the accused
chapter("t4", S_DEF, "In defence of the accused.", "In defence of the accused")
beat("d1", S_DEF, "One: StubHub says it tried honesty.",  # Klot r78 item 8: the a5 queue, not the Loew's archive again
     reuse("a5", hand_marks=True, cam_rate=0.010, marks=[write("A", at=0.0, **AB_A), write("$48", at=0.0, **GLASS_A)]), ledger_hide=True)
beat("d2", S_DEF, "In 2014, it says, it moved to all-in prices, and lost customers to rivals who kept their fees.",
     doc("StubHub statement · White House event · March 2023", "Why StubHub went back",
         "In 2014, the company voluntarily moved to all-in pricing ... The result was a significant shift in market share away from StubHub to our competitors.",
         "significant shift in market share", on="lost", kicker="COMPANY STATEMENT  ·  QUOTED", seed=75, lead=0.6),
     label="StubHub statement · White House event · March 2023")
beat("d2b", S_DEF, "It went back in the fall of 2015.",
     reuse("a2b", motion="zoom_out"), stamp={"text": "Fees back · fall 2015", "on": "back"},
     label="StubHub statement · White House event · March 2023")
beat("d3", S_DEF, "Two: its own economists saw it differently. Their finding on the switch to late fees: market-expanding, rather than pure business-stealing.",
     doc("NBER Working Paper 25186 · p. 27", "What the switch did",
         "These findings suggest that the switch to BF at StubHub was market-expanding, rather than pure business-stealing.",
         "market-expanding, rather than pure business-stealing", on="market-expanding,", kicker="WORKING PAPER  ·  QUOTED", seed=76, lead=0.6,
         push_on="market-expanding,"),
     label="NBER w25186")
beat("d4", S_DEF, "In plain English, hidden fees didn't just win buyers from rivals. They made people spend more.",  # (was a card)
     reuse("l1", hand_marks=True, cam_rate=0.006,
           marks=[write("NOT JUST STOLEN BUYERS", on="win", dur=0.8, x=0.50, y=0.700, w=0.46, h=0.052, fs=0.046, **WOOD_PEN),
                  write("PEOPLE SPENT MORE", on="They", dur=0.65, x=0.50, y=0.752, w=0.46, h=0.052, fs=0.046, **WOOD_PEN)]))
beat("d5", S_DEF, "Three: fees pay for real things. Card payments, staff, the venue.",
     arch("giant_food_cashier_1942.jpg", "Cashier checking out a customer, Giant Food, Washington, D.C., 1942 · Library of Congress", motion="zoom_in"))
beat("d6", S_DEF, "America's new rule bans no fee at all. It only wants the total, upfront.",
     arch("briggs_stadium_tickets_1942.jpg", "Buying tickets for the ball game, Briggs Stadium, Detroit, 1942 · Library of Congress", motion="static"),
     label="FTC rule · in force May 2025")
beat("d7", S_DEF, "The fee may be fair. Hiding it isn't.", kin())

# ------------------------------------------------------------------ Friday 9:00 AM — One fee, three laws (one ticket, three stamps)
chapter("t5", S_LAW, "Friday, nine a.m.", "Friday 9:00 AM — One fee, three laws")
DESK = "a 1950s customs desk seen from above with a wooden rubber-stamp rack and an ink pad near the top edge, a wide stretch of empty plain wood in the middle, warm light"
# Klot r78 item 9: on "Three borders" the hand flips the ticket (code-made clip, make_l1_flip.py -> clips/l1.mp4); its
# back (images/l2.png) is plain cream with a faint BORDER CONTROL header, the stub now on the left. The three stamps land
# on clear space on the back, each at its own slight angle, never on each other or on any text.
STAMP_USA = dict(text='USA · TOTAL UPFRONT · MAY 2025', x=0.468, y=0.392, angle=-8, w=0.15)
STAMP_UK = dict(text='UK · ALL FEES IN · APRIL 2025', x=0.607, y=0.478, angle=4, w=0.15)
STAMP_EU = dict(text='EU · TOTAL BEFORE YOU PAY', x=0.478, y=0.568, angle=-2, w=0.14)
ST = lambda d, **kw: stamp(d["text"], d["x"], d["y"], angle=d["angle"], w=d["w"], **kw)
beat("l1", S_LAW, "Larry's ticket goes on a trip. Three borders. Three stamps.",
     manual(img(DESK, note="images/l1.png: the code-drawn $30 ticket on the desk; clips/l1.mp4: the hand flips it (make_l1_flip.py)",
                motion="static", cam_rate=0.006, clip_sync={"from": "borders.", "from_delay": -0.55, "start": 0.0, "end": 1.4}), clip=True),
     sfx_at=[{"on": "borders.", "delay": -0.2, "kind": "paper"}])
beat("l2", S_LAW, "Border one: America. Since May 2025, ticket sellers and short stays, from hotels to holiday rentals, must show the total price upfront.",
     img("the back of the code-drawn ticket on the customs desk", note="code-drawn: images/l2.png (make_l1_flip.py)", motion="static",
         hand_marks=True, closeup=closeup("short", [0.47, 0.43], 1.35, [ST(STAMP_USA, on='total')])),
     pause_at={"word": "May", "sec": 0.4, "hit": None})
beat("l3", S_LAW, "In April 2026, StubHub agreed to pay ten million dollars back to buyers,",
     stat(10, "StubHub settlement · FTC · April 2026", prefix="$", suffix="m"),
     pause_at={"word": "ten", "sec": 0.6, "hit": "stamp"})
beat("l3b", S_LAW, "over fees it showed too late.",
     reuse("a5", hand_marks=True, push={"center": [0.62, 0.36], "zoom": 1.7},
           marks=[write("B", at=0.0, **AB_B), write("$30", at=0.0, **GLASS_B), write("+ fees", at=0.0, **GLASS_B2)]),
     label="FTC · April 2026 · settlement", ledger_hide=True)
beat("l4", S_LAW, "America has done this before. In 1958, a law put a sticker on the window of every new car:",
     arch("car_showroom_1942.jpg", "Car showroom, Pierson Motor Company, Lititz, Pennsylvania, 1942 · Library of Congress", motion="zoom_in"),
     label="Automobile Information Disclosure Act · 1958")
STK_Y = (0.375, 0.455, 0.535, 0.615)
STK = lambda k: dict(x=0.443 - 0.03 * (STK_Y[k] - 0.30) + 0.13, y=STK_Y[k], w=0.26, h=0.056, fs=0.05, angle=-2.0, align="left", color="ink")
beat("l5", S_LAW, "the price, every option, the delivery charge, and the total.",
     img("the side window of a 1950s two-tone sedan in a showroom with a large blank paper sticker taped inside the glass, close view",
         motion="static", hand_marks=True,
         marks=[write("PRICE", on="price,", **STK(0)), write("OPTIONS", on="option,", chain=True, **STK(1)),
                write("DELIVERY", on="delivery", chain=True, **STK(2)),
                write("TOTAL", on="total.", chain=True, **STK(3))]),  # one hand writes the list, level and left-aligned
     label="15 U.S.C. 1232 · 1958", ledger_hide=True)
beat("l6", S_LAW, "Cars got the total sixty-seven years before concert tickets did.",
     reuse("l5", hand_marks=True, marks=[write("PRICE", at=0.0, **STK(0)), write("OPTIONS", at=0.0, **STK(1)), write("DELIVERY", at=0.0, **STK(2)),
                                         write("TOTAL", at=0.0, **STK(3)),
                                         circle(0.481, STK_Y[3], 0.140, 0.088, "total", target=[0.440, 0.590, 0.522, 0.640]),
                                         write("67 YEARS", on="sixty-seven", x=0.565, y=0.105, w=0.18, h=0.055, angle=-0.6)]),
     ledger_hide=True)  # (no reveal pause: the cut before "sixty-seven" left a fragment - TTS scan, Klot r78 G4)
beat("l7", S_LAW, "Border two: Britain. Since April 2025, the price must include every fee you can't avoid.",
     reuse("l2", hand_marks=True, cam_rate=0.006, marks=[ST(STAMP_USA, at=0.0), ST(STAMP_UK, on='include')]))
L8_FEE = dict(x=0.36, y=0.085, w=0.15, h=0.07, plate=[1.25, 1.30])
beat("l8", S_LAW, "A driving-school group hid a three-pound booking fee charged to over eighty thousand learner drivers.",
     img("a small 1950s family car with a blank white square plate on the front bumper, parked on a quiet British street, cheerful print-ad style",
         motion="static", hand_marks=True, marks=[write("£3 FEE", on="three-pound", **L8_FEE)]),  # cream plate: it sits on the trees (G2)
     label="CMA · April 2026")
beat("l9", S_LAW, "It paid a four point two million pound fine,",
     stat(4.2, "fine · CMA, April 2026", decimals=1, prefix="£", suffix="m"),
     pause_at={"word": "four", "sec": 0.6, "hit": "stamp"})
beat("l9b", S_LAW, "and over seven hundred and sixty thousand pounds in refunds.",
     stat(760, "refunded to learners · CMA, April 2026", prefix="over £", suffix="k"))
beat("l10", S_LAW, "In June, StubHub's British arm was fined too.",
     reuse("o1", hand_marks=True, marks=[write("$30", at=0.0, **TICKET_PRICE_BOX, color="ink"), stamp('UK · FINED · JUNE 2026', 0.850, 0.520, on='fined', angle=-7, w=0.20)]),
     label="CMA · June 2026")
beat("l11", S_LAW, "Three pounds. Very expensive pounds.",
     reuse("l8", push={"center": [0.45, 0.30], "zoom": 1.35}, hand_marks=True, marks=[write("£3 FEE", at=0.0, **L8_FEE),
                                                                                    circle(0.36, 0.085, 0.20, 0.115, "Very", target=[0.285, 0.05, 0.435, 0.12])]))
beat("l12", S_LAW, "Border three: the European Union. The total price, taxes included, before you pay.",
     reuse("l2", hand_marks=True, cam_rate=0.006, marks=[ST(STAMP_USA, at=0.0), ST(STAMP_UK, at=0.0), ST(STAMP_EU, on='total')]))
beat("l13", S_LAW, "And any extra charge needs your clear yes. A pre-ticked box is not a yes.",
     img("a 1950s paper order form on a desk with three plain empty lines, each line ending in a small square checkbox, the last checkbox already ticked in black ink, plain cream background",
         motion="static", hand_marks=True, marks=[circle(0.60, 0.455, 0.055, 0.085, "pre-ticked", target=[0.586, 0.43, 0.615, 0.479]),
                                                  write("NOT A YES", on="not", x=0.47, y=0.445, w=0.17, h=0.055)]), ledger_hide=True)  # on the ticked line, clean paper
beat("l14", S_LAW, "One ticket. Three stamps. One message: show the total.",
     reuse("l2", motion="zoom_out", marks=[ST(STAMP_USA, at=0.0), ST(STAMP_UK, at=0.0), ST(STAMP_EU, at=0.0)]))

# ------------------------------------------------------------------ Saturday 10:00 AM — Three checks
chapter("t6", S_CHECK, "Saturday, ten a.m.", "Saturday 10:00 AM — Three checks")
beat("x1", S_CHECK, "Three checks before you pay. One. Look for the all-in switch.",
     manual(img("a big chrome 1950s toggle switch on a cream enamel panel, only one blank plate above it, switched to the left, studio lighting, plain background",
         motion="static", hand_marks=True, short_fit=X_FIT, clip_hold=True, cam_rate=X_PUSH,  # first frame: lever on OFF
         marks=[write("OFF", on="One.", **X1_OFF),
                write("ALL-IN PRICES", on="all-in", **X1_TOP)]), clip=True), ledger_hide=True)
beat("x2", S_CHECK, "Some ticket sites can show prices with fees included. Turn it on before you browse, not after you've fallen for a seat.",
     reuse("x1", clip=True, hand_marks=True, short_fit=X_FIT, cam_rate=X_PUSH, cam_continue=True,
           clip_sync={"from": "Turn", "to": "on", "to_delay": 0.22, "start": 3.3, "end": 4.0},  # flip on "Turn it on", click on "on" (1.25x)
           marks=[write("ALL-IN PRICES", at=0.0, **X1_TOP), write("OFF", at=0.0, **X1_OFF),
                  write("ON", on="included.", **X1_ON)]), ledger_hide=True)  # ON goes on before the lever moves there
beat("x3", S_CHECK, "Two. Go to the last screen before you decide. The real price lives one click before Pay.",
     reuse("m1b", hand_marks=True, marks=[write("LAST SCREEN", on="last", x=0.17, y=0.30, w=0.22, h=0.06)],
           closeup=closeup("real", [0.50, 0.40], 1.6, [write("$48", on="price", x=0.535, y=0.40, w=0.09, h=0.04)])), ledger_hide=True)
beat("x4", S_CHECK, "Three. Compare totals, not headlines. A forty-dollar ticket with no fees beats a thirty-dollar ticket with eighteen.",
     {"type": "chart", "chart": {"kind": "bar", "title": "What you actually pay", "labels": ["$40 · no fees", "$30 + $18 fees"], "values": [40, 48],
                                 "unit": "$", "highlight": 0, "value_labels": True, "note": "Illustration"}})
beat("x5", S_CHECK, "The cheapest ticket is the one with the smallest last number.", kin(), hold=1.0)  # item 1: no cut-off at the end

# ------------------------------------------------------------------ Case closed + end screen (Ep.5 teaser: tip screens)
# z0 (Klot r78 item 12): the clip plays to 1.9 s and holds there with a slow push; the stamp hand presses PAID $48 on
# the blank stub between the perforations, clear of his thumb (measured on the 1.9 s frame, mapped to the still)
Z0_PAID = dict(text="PAID $48", x=0.578, y=0.386, angle=19, w=0.068)
beat("z0", S_CLOSE, "Case closed. Larry paid forty-eight dollars for a thirty-dollar ticket.",
     manual(img(f"{LARRY} happy in the crowd at a 1950s concert hall, stage lights in the distance, holding his paper ticket stub, warm light",
         motion="static", cam_rate=0.008, clip_until=1.9, hand_marks=True, marks=[ST(Z0_PAID, on="paid", on_object=True)]), clip=True),
     stamp={"text": "Case closed", "on": "Case", "big": True, "x": 0.735, "y": 0.150, "w": 0.40},  # twice the r78 size, dark upper right
     hero=True)  # Larry's hand and ticket fill the frame: the tab steps aside (no hand near his hands)
beat("z0b", S_CLOSE, "He went to the concert anyway. The band was worth thirty. The checkout was worth nothing. Now he knows where the eighteen went.",
     manual(img("the z0 clip at 1.9 s", note="images/z0b.png = clips/z0.mp4 at 1.9 s (make_l1_flip.py), where z0 holds", motion="static",
                push={"center": [0.45, 0.40], "zoom": 1.1}, hand_marks=True,
                marks=[ST(dict(Z0_PAID, x=0.598, y=0.381, w=0.075), at=0.0)],
                closeup=closeup("checkout", [0.61, 0.40], 1.3, [ST(dict(Z0_PAID, x=0.598, y=0.381, w=0.075), at=0.0)]))), hero=True)  # on the ticket
ES = {"number": "004", "title": "The fee at the end", "stamp": "Case closed",
      # four lines at the Ep.3 letter size, each written from its first spoken word (real-voice word times)
      "verdict": ["Guilty: the checkout fee", "and its cousin, the resort fee.", "Accomplice:", "the first number on the screen."],
      "verdict_at": [1.4, 3.17, 5.36, 6.25], "verdict_dur": [1.55, 1.9, 0.72, 1.55],
      "next": {"number": "005", "title": "Tip screens", "tagline": "18 % · 22 % · 25 % · No tip?", "image_file": "next_tablet.png",
               "copies": 1, "writes": [{"text": "No tip", "x": 0.5, "y": 0.880, "h": 0.085}],
               "label": ["72 % say tipping is expected in more places", "Pew Research Center · Nov 2023"], "label_under": True,
               "subject_scale": 1.5, "subject_top": 0.285, "label_gap": 0.03, "tagline_y": 0.214, "tagline_h": 0.075},  # tablet 1.5x for phones, Pew plate under it
      # timed on the real voice (CI timings 2026-10-21): verdict lines written as spoken, swap after "screen.",
      # sketch with "Next case", "No tip" on "tip", Pew plate after "coffee", click on "Subscribe"
      "times": {"v1": 1.4, "v2": 5.36, "vdur": 2.2, "swap": 8.4, "draw": 8.9, "ddur": 3.0, "writes": 11.9, "tagline": 12.5,
                "zone": 13.0, "sketch": 13.2, "skdur": 1.0, "label": 13.6, "sub": 14.5, "click": 15.2, "push": 15.9}}
beat("z1", S_CLOSE, "The verdict. Guilty: the checkout fee and its cousin, the resort fee. Accomplice: the first number on the screen.",
     {"type": "endscreen", "endscreen": ES}, block_start=True, sting="ub_sting_brass", sting_at=0.1)
beat("z4", S_CLOSE, "Next case: the screen that asks how much you'd like to tip, before you've had your coffee.",
     {"type": "continue"}, block_at=7.0)  # the Pew figure is on screen only (plate under the tablet sketch)
beat("z5", S_CLOSE, "Subscribe, so the next case file finds you.", {"type": "continue"}, block_at=12.8, block_end=18.5)

# ------------------------------------------------------------------ 7 Shorts (frame 0 = hook text over the Short's strongest picture)
LONG = {b["id"]: b for b in B}


def L(bid, text=None, keep=("punch", "pause_at", "sfx_at", "sfx", "say", "stamp", "label", "ledger", "alleged", "hold", "ledger_hide", "hero"), **kw):
    src = LONG[bid]
    v = src["visual"]
    if v["type"] in ("image", "archive", "clip"):
        vis = {"type": "reuse", "beat": bid, "motion": v.get("motion", "zoom_in")}
        for k in ("marks", "hand_marks", "closeup", "push", "stamps"):
            if v.get(k) is not None:
                vis[k] = copy.deepcopy(v[k])
        for k in ("clip_hold", "clip_sync", "clip_at", "clip_until", "cam_rate", "cam_continue", "split", "one_shot"):
            if v.get(k) is not None:  # held clip frame, synced flip, even push, the n1 split
                vis[k] = copy.deepcopy(v[k])
        if v.get("clip") and not v.get("short_still"):
            vis["clip"] = True  # the Short plays the same live clip as the long video
        if v.get("short_fit"):  # the whole subject stays in the Short's window for the whole beat: no push-in
            vis["short_fit"] = list(v["short_fit"])
            vis.pop("closeup", None)
    else:
        vis = copy.deepcopy(v)
        if v["type"] == "mugshot":
            vis["from_beat"] = bid
    b = {"text": text or src["text"], "visual": vis}
    if text is None:
        for k in keep:
            if k in src:
                b[k] = copy.deepcopy(src[k])
    b.update(kw)
    return b


SHORTS = [
    {"id": "s1", "title": "The $30 ticket that costs $48 #shorts", "hook": "$30 → $48", "hook_on": "o3",
     "beats": [L("o1"), L("o2"), L("o3"), L("m1"), L("b6"), L("o1", text="So before you pay thirty, ask what it costs.", keep=())]},
    {"id": "s2", "title": "StubHub tested hidden fees on its own buyers #shorts", "hook": "THEY TESTED IT ON YOU", "hook_on": "a5",
     "beats": [L("a5", text="StubHub showed every fee upfront. Then, for twelve days in August 2015, it split its buyers in two."),
               L("a6"), L("a8"), L("a9"), L("a10"), L("a12", hold=0.6), L("a14")]},
    {"id": "s3", "title": "$16.4 billion in fees (alleged) #shorts", "hook": "$16.4 BILLION", "hook_on": "b5",
     "beats": [L("b1"), L("b2"), L("b3a"), L("b3"), L("b4"), L("b5"), L("b9"), L("b6")]},
    {"id": "s4", "title": "A resort fee at a city hotel #shorts", "hook": "RESORT FEE?", "hook_on": "c1",
     "beats": [L("c1"), L("m2"), L("m2b"), L("c2"), L("c3"), L("c4"), L("c5"), L("c7")]},
    {"id": "s5", "title": "Why a split price feels cheaper #shorts", "hook": "YOUR BRAIN FILES THE FIRST NUMBER", "hook_on": "n4",
     "beats": [L("o1", text="Thirty dollars. Then the fees.", keep=()), L("n1"), L("n2"), L("n3"), L("n4")]},
    {"id": "s6", "title": "The £3 fee that cost £4.2 million #shorts", "hook": "£3 → £4,200,000", "hook_on": "l8",
     "beats": [L("l8"), L("l9"), L("l4"), L("l5"), L("l6")]},
    {"id": "s7", "title": "3 checks before you pay #shorts", "hook": "3 CHECKS", "hook_on": "x1",
     "beats": [L("x1"), L("x2"), L("x3"), L("x4"), L("x5")]},
]
for sh in SHORTS:
    for k, b in enumerate(sh["beats"]):
        b["id"] = f"{sh['id']}_{k}"

ep = {
    "config": {"ledger": {"hand": "ink_cuff", "hand_scale": 0.43, "from": "right"},  # plain cuff hand, from the right edge
               "hands": {"sleeve": False}},  # rule 21: Larry's jacket belongs only to Larry
    "slug": "0005-drip-pricing",
    "title": "The $30 Ticket That Costs $48",
    "description": "Case file #004: the fee at the end. Larry (fictional) buys a $30 concert ticket and pays $48. StubHub's own 2015 experiment, the FTC's case against Ticketmaster (alleged), Marriott's city-hotel resort fees (alleged), why a split price feels cheaper, one ticket stamped by three laws — and three checks before you pay.",
    "tags": ["drip pricing", "junk fees", "hidden fees", "ticket fees", "resort fees", "stubhub", "ticketmaster", "consumer rights",
             "psychology of money", "behavioral economics"],
    "characters": {
        "larry": "a cheerful middle-aged man with a round face and a thin moustache, wearing a loud yellow checked sports jacket and a red fedora",
    },
    "music": {"_default": "ub_private_detective", "_shorts": "ub_wells_street",
              S_OPEN: "ub_private_detective", S_EXP: "ub_mechanisms_of_action", S_TM: "ub_tunnel_vision", S_HOTEL: "ub_night_spot",
              S_BRAIN: "ub_mechanisms_of_action", S_DEF: "ub_usual_suspects", S_LAW: "ub_secret_report", S_CHECK: "ub_wells_street",
              S_CLOSE: "ub_jazz_rumble"},
    "sources": [
        "Blake, Moshary, Sweeney & Tadelis, Price Salience and Product Choice, NBER Working Paper 25186 (pp. 8, 14, 16, 22, 27).",
        "StubHub remarks, White House convening on junk fees, 21 March 2023.",
        "FTC v. Live Nation Entertainment, Inc., No. 2:25-cv-08884 (C.D. Cal.), complaint ¶36 (filed 18 Sept 2025) — allegations; order denying motion to dismiss, 28 Sept 2026.",
        "FTC (9 April 2026): StubHub to pay $10 million to settle charges under the FTC Act and the Rule on Unfair or Deceptive Fees.",
        "FTC Rule on Unfair or Deceptive Fees, 16 CFR Part 464 (90 FR 2066), effective 12 May 2025.",
        "District of Columbia v. Marriott International (complaint and press release, 9 July 2019) — allegations. Texas Attorney General agreement with Marriott, 16 May 2023.",
        "Morwitz, Greenleaf & Johnson (1998), Divide and Prosper, Journal of Marketing Research 35(4), 453–463.",
        "Automobile Information Disclosure Act of 1958, 15 U.S.C. 1232.",
        "Digital Markets, Competition and Consumers Act 2024, s.230; CMA: The AA and BSM (15 April 2026); StubHub UK (23 June 2026).",
        "EU: Consumer Rights Directive 2011/83/EU Arts. 6(1)(e), 22; Unfair Commercial Practices Directive 2005/29/EC Art. 7(4)(c); Regulation 1008/2008 Art. 23.",
        "Pew Research Center (9 Nov 2023), Tipping Culture in America.",
        "Larry is a fictional character. Scenes marked 'Illustration' are illustrations.",
    ],
    "beats": B,
    "shorts": SHORTS,
}
OUT.write_text(json.dumps(ep, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(len(B), "beats,", sum(len(b["text"].split()) for b in B), "words")
