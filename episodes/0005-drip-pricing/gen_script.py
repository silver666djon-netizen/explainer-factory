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


def make_ticket(path):
    """Code-drawn hero prop (no generation): the same 1950s concert ticket as the Ep.3 teaser, blank price box."""
    from PIL import Image, ImageDraw
    W, H = 1376, 768
    im = Image.new("RGB", (W, H), (243, 233, 210))
    d = ImageDraw.Draw(im)
    ink, red, paper = (30, 27, 24), (210, 69, 47), (252, 247, 233)
    x0, y0, x1, y1 = 250, 190, 1130, 590
    d.rounded_rectangle((x0, y0, x1, y1), radius=26, fill=paper, outline=ink, width=10)
    sx = x1 - 230
    for yy in range(y0 + 24, y1 - 20, 34):
        d.ellipse((sx - 7, yy - 7, sx + 7, yy + 7), fill=(243, 233, 210), outline=ink, width=3)
    d.rectangle((x0 + 40, y0 + 40, sx - 40, y0 + 150), fill=red)
    d.text(((x0 + sx) / 2, y0 + 95), "ADMIT ONE", font=_fnt("Anton-Regular.ttf", 92), fill=paper, anchor="mm")
    d.text(((x0 + sx) / 2, y0 + 215), "ROW G · SEAT 12", font=_fnt("ArchivoBlack-Regular.ttf", 40), fill=ink, anchor="mm")
    d.rectangle((x0 + 160, y0 + 270, sx - 160, y1 - 40), outline=ink, width=6)
    d.text((x1 - 115, (y0 + y1) / 2), "No. 004", font=_fnt("ArchivoBlack-Regular.ttf", 40), fill=ink, anchor="mm")
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
    d.text(((x0 + x1) / 2, y0 + 110), "ADD A TIP?", font=_fnt("ArchivoBlack-Regular.ttf", 46), fill=ink, anchor="mm")
    for k, t in enumerate(["18%", "22%", "25%"]):
        by = y0 + 190 + k * 120
        d.rounded_rectangle((x0 + 90, by, x1 - 90, by + 92), radius=18, fill=green if k else red, outline=ink, width=5)
        d.text(((x0 + x1) / 2, by + 46), t, font=_fnt("Anton-Regular.ttf", 58), fill=paper, anchor="mm")
    im.save(path)


make_ticket(HERE / "images" / "o1.png")
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
TICKET_PRICE_BOX = dict(x=0.43, y=0.62, w=0.20, h=0.10)  # the blank price box of the code-drawn ticket

# ------------------------------------------------------------------ cold open (≤ 15 s to the folder)
beat("o1", S_OPEN, "A concert ticket. Thirty dollars.",
     img("the code-drawn $30 concert ticket", note="hand-made frame: images/o1.png (code-drawn)", motion="static", hand_marks=True, marks=[write("$30", on="Thirty", **TICKET_PRICE_BOX, color="ink")]),
     pause_at={"word": "Thirty", "sec": 0.45, "hit": "stamp"}, ledger=[tab("TICKET", "$30.00", "Thirty")], label="Illustration")
beat("o2", S_OPEN, "Then the fees. Eight. Six. Four.",
     reuse("o1", hand_marks=True, marks=[write("$30", at=0.0, **TICKET_PRICE_BOX, color="ink"),
                                         write("+ $8 fee", on="Eight.", x=0.86, y=0.30, w=0.16, h=0.07),
                                         write("+ $6 fee", on="Six.", x=0.86, y=0.42, w=0.16, h=0.07),
                                         write("+ $4 fee", on="Four.", x=0.86, y=0.54, w=0.16, h=0.07)]),
     ledger=[tab("SERVICE FEE", "+$8.00", "Eight."), tab("FACILITY FEE", "+$6.00", "Six."), tab("PROCESSING FEE", "+$4.00", "Four.")],
     label="Illustration")
beat("o3", S_OPEN, "Total: forty-eight.",
     reuse("o1", push={"center": [0.62, 0.48], "zoom": 1.25}, hand_marks=True,
           marks=[write("$30", at=0.0, **TICKET_PRICE_BOX, color="ink"),
                  write("+ $8 fee", at=0.0, x=0.86, y=0.30, w=0.16, h=0.07), write("+ $6 fee", at=0.0, x=0.86, y=0.42, w=0.16, h=0.07),
                  write("+ $4 fee", at=0.0, x=0.86, y=0.54, w=0.16, h=0.07), write("= $48", on="forty-eight.", x=0.86, y=0.68, w=0.16, h=0.09)]),
     pause_at={"word": "forty-eight.", "sec": 0.45, "hit": "stamp"}, ledger=[tab("PAID", "$48.00", "forty-eight.")], label="Illustration")
beat("o4", S_OPEN, "Larry is made up. The fees are not.",
     manual(img(f"{LARRY} sitting at a kitchen table at night, lit by the glow of a cream retro laptop, a paper concert ticket propped against a coffee cup, plain cream background",
         motion="static", hand_marks=True, marks=[write("FICTIONAL", on="made", x=0.22, y=0.18, w=0.18, h=0.06),
                                                  write("REAL", on="fees", x=0.80, y=0.30, w=0.10, h=0.06)])))

# ------------------------------------------------------------------ the case + suspect no. 1
beat("cf1", S_OPEN, "Case file number four. The fee at the end.",
     {"type": "casefile", "casefile": {"mode": "open", "number": "004", "title": "The fee at the end", "typed": False, "open_stamp_on": "end.",
                                        "inside": ["SUBJECT: Larry (fictional)", "EXHIBIT: one $30 ticket", "", "SUSPECTS: 2", "STATUS: open"],
                                        "writes": [{"line": 2, "text": "paid: $48", "on": "end."}]}})
beat("m1", S_OPEN, "Suspect number one. Name: the checkout fee. Aliases: service fee, processing fee, convenience fee.",
     {"type": "mugshot", "prompt": "a long curling blank paper till receipt hanging from a small nail on a plain light grey wall, nothing else in the picture, studio lighting",
      "suspect": {"number": 1, "name": "The checkout fee", "alias": "Service · Processing · Convenience", "tag": "SUSPECT", "stamp_pos": [0.70, 0.12],
                  "type_on": ["Name:", "Aliases:"]}})
beat("m1b", S_OPEN, "Last seen: one click before Pay. It never touches the price you see. It waits for the price you pay.",
     img("a cream 1950s-styled retro laptop seen from the front, its screen completely blank and softly lit, plain cream background",
         note="after the storyboard: code-drawn checkout page (red PAY button, empty total box) composited on the screen (images/m1b.png)",
         motion="static", hand_marks=True, marks=[circle(0.55, 0.4635, 0.14, 0.085, "Pay.", target=[0.50, 0.44, 0.60, 0.487])],
         closeup=closeup("waits", [0.50, 0.40], 1.8, [write("$48", on="pay.", x=0.535, y=0.40, w=0.09, h=0.04)])))

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
         closeup=closeup("price", [0.50, 0.30], 1.8, [write("TOTAL $48", at=0.0, x=0.50, y=0.22, w=0.26, h=0.09, color="ink"),
                                                       circle(0.50, 0.22, 0.30, 0.13, "paid.", target=[0.37, 0.17, 0.63, 0.27])])),
     label="Illustration")
beat("a5", S_EXP, "Then, for twelve days in August 2015, it split its buyers in two.",
     img("a 1950s theatre lobby with a velvet rope splitting a queue of cheerful cartoon ticket buyers into two lines in front of two identical ticket windows, front view",
         motion="static", hand_marks=True, marks=[write("A", on="split", x=0.30, y=0.20, w=0.05, h=0.08), write("B", on="two.", x=0.70, y=0.20, w=0.05, h=0.08)]),
     label="Aug 19–31, 2015")
beat("a6", S_EXP, "Half kept the full price on screen. The other half saw the ticket alone, with the fees waiting at checkout.",
     reuse("a5", hand_marks=True, marks=[write("A", at=0.0, x=0.30, y=0.20, w=0.05, h=0.08), write("B", at=0.0, x=0.70, y=0.20, w=0.05, h=0.08),
                                         write("$48", on="full", x=0.30, y=0.30, w=0.09, h=0.07), write("$30…", on="alone,", x=0.70, y=0.30, w=0.10, h=0.07)],
           closeup=closeup("fees", [0.70, 0.40], 1.8, [write("B", at=0.0, x=0.70, y=0.20, w=0.05, h=0.08), write("$30…", at=0.0, x=0.70, y=0.30, w=0.10, h=0.07),
                                                       write("+ fees at checkout", on="checkout.", x=0.70, y=0.40, w=0.20, h=0.05)])),
     label="Aug 19–31, 2015")
beat("a7", S_EXP, "Same tickets. Same fees. The only thing that changed was the moment you saw them.", kin())
beat("a8", S_EXP, "The ones who met the fees late spent almost twenty-one percent more.",
     stat(21, "more spent when fees came at checkout · NBER w25186 · 2015 test", prefix="≈", suffix="%"),
     pause_at={"word": "twenty-one", "sec": 0.6, "hit": "stamp"})
beat("a9", S_EXP, "They were fourteen point one percent more likely to buy at all.",
     stat(14.1, "more likely to buy · NBER w25186 · 2015 test", decimals=1, suffix="%"),
     pause_at={"word": "fourteen", "sec": 0.6, "hit": "stamp"})
beat("a10", S_EXP, "And the buyers among them picked seats about five percent pricier.",
     manual(img("a 1950s concert hall seen from the stage, rows of red velvet seats, the front rows lit by a warm spotlight, empty hall",
         motion="static", hand_marks=True, marks=[write("+5 %", on="five", x=0.50, y=0.30, w=0.12, h=0.08)]), clip=True),
     pause_at={"word": "five", "sec": 0.5, "hit": "stamp"})
beat("a11", S_EXP, "A seat looks cheaper when its fees are still offstage, so you pick a better one.",
     reuse("a10", push={"center": [0.50, 0.55], "zoom": 1.6}),
     label="Seat choice = at least 28 % of the revenue gap · NBER w25186")
beat("a12", S_EXP, "Then the fees walk on.",
     manual(img("three small paper price slips with tiny cartoon legs walking onto a 1950s theatre stage in a spotlight, red curtain, playful print-ad style",
         motion="static"), clip=True))
beat("a13", S_EXP, "Twelve days of science. Then the science went live.", kin())
beat("a14", S_EXP, "On September the first, the whole site switched. Fees at the end, for everyone.",
     arch("radio_city_crowd_1942.jpg", "Crowd waiting to buy tickets, Radio City Music Hall, New York, 1942 · Library of Congress", motion="zoom_in"),
     stamp={"text": "Sept 1, 2015", "on": "first,"}, label="NBER w25186")

# ------------------------------------------------------------------ Wednesday 10:00 AM — $16.4 billion (Ticketmaster, ALLEGED)
chapter("t2", S_TM, "Wednesday, ten a.m.", "Wednesday 10:00 AM — $16.4 billion")
beat("b1", S_TM, "Larry reads his receipt. Eighteen dollars of fees on a forty-eight-dollar ticket.",
     manual(img(f"{LARRY} at a breakfast table frowning at a long paper receipt that unrolls across the table, coffee cup, plain cream background",
         motion="static", hand_marks=True, marks=[write("$18 FEES", on="Eighteen", x=0.78, y=0.22, w=0.18, h=0.07)]), clip=True),
     ledger=[tab("HIDDEN", "$18.00", "Eighteen", loss=True, circle=True)])
beat("b2", S_TM, "That's thirty-seven and a half percent of what he paid.",
     stat(37.5, "of Larry's total was fees · Illustration", decimals=1, suffix="%"),
     pause_at={"word": "thirty-seven", "sec": 0.6, "hit": "stamp"})
beat("b3", S_TM, "Is that unusual? In September 2025, America's Federal Trade Commission and seven states sued Live Nation and Ticketmaster.",
     arch("ftc_statue_1943.jpg", "Statue in front of the Federal Trade Commission building, Washington, D.C., 1943 · Library of Congress", motion="zoom_in"),
     label="FTC v. Live Nation/Ticketmaster · filed Sept 2025 · case pending", alleged=True)
beat("b4", S_TM, "They allege the fees run from twenty-four to forty-four percent of the total price.",
     doc("FTC complaint · C.D. Cal. · Sept 2025 · ¶36", "Ticketmaster fees",
         "The average percentage of fees charged on tickets ranges from 24% to 44% of the total price.",
         "24% to 44% of the total price", on="twenty-four", kicker="COMPLAINT  ·  ALLEGED  ·  QUOTED", seed=72, lead=0.6),
     pause_at={"word": "twenty-four", "sec": 0.4, "hit": None})
beat("b5", S_TM, "And that fans paid over sixteen point four billion dollars in mandatory fees.",
     stat(16.4, "in mandatory fees · FTC complaint, Sept 2025 · ALLEGED", decimals=1, prefix="$", suffix="bn"),
     pause_at={"word": "sixteen", "sec": 0.6, "hit": "stamp"})
beat("b6", S_TM, "Larry's thirty-seven and a half percent sits right inside that range.",
     {"type": "chart", "chart": {"kind": "bar", "title": "Fees as a share of the total", "labels": ["Low (alleged)", "Larry", "High (alleged)"],
                                 "values": [24, 37.5, 44], "unit": "%", "highlight": 1, "value_labels": True,
                                 "note": "FTC complaint ¶36 (alleged) · Larry: illustration"}})
beat("b7", S_TM, "His thirty-dollar ticket grew by sixty percent between the first screen and the last.",
     reuse("o1", hand_marks=True, marks=[write("$30", at=0.0, **TICKET_PRICE_BOX, color="ink"), write("+60 %", on="sixty", x=0.86, y=0.40, w=0.16, h=0.10)]),
     pause_at={"word": "sixty", "sec": 0.5, "hit": "stamp"}, label="Illustration",
     ledger=[tab("= 37.5 % of the total · +60 % on the $30 shown", "", "sixty", note=True)])
beat("b8", S_TM, "Larry, it turns out, is perfectly average.", reuse("b1", push={"center": [0.40, 0.35], "zoom": 1.7}), hero=True)
beat("b9", S_TM, "In September 2026, a judge refused to throw the case out. It goes on.",
     doc("U.S. District Court, C.D. Cal. · Order · Sept 28, 2026", "Motion to dismiss",
         "For the reasons stated herein, Defendant's Motion is DENIED as to each claim.",
         "DENIED as to each claim", on="refused", kicker="COURT ORDER  ·  QUOTED", seed=73, lead=0.6), alleged=True)
beat("b9b", S_TM, "Until a court decides, every word of it is an allegation.",
     reuse("b3", motion="zoom_out"), label="FTC v. Live Nation/Ticketmaster · case pending", alleged=True)

# ------------------------------------------------------------------ Thursday 11:40 PM — The resort fee (Marriott, ALLEGED)
chapter("t3", S_HOTEL, "Thursday, eleven-forty p.m.", "Thursday 11:40 PM — The resort fee")
beat("c1", S_HOTEL, "Larry needs a hotel for the concert. Downtown. Nowhere near a beach.",
     manual(img(f"{LARRY} standing with a small suitcase in a plain downtown hotel lobby at night, a framed poster of a sunny beach on the wall behind him, plain cream background",
         motion="static", hand_marks=True, marks=[write("DOWNTOWN", on="Downtown.", x=0.20, y=0.15, w=0.20, h=0.06)])))
beat("m2", S_HOTEL, "Suspect number two. Name: the resort fee. Aliases: amenity fee, destination fee.",
     {"type": "mugshot", "prompt": "an old hotel room key on a smooth oval brass key fob with a polished, completely plain surface, hanging from a small nail on a plain light grey wall, nothing else in the picture, studio lighting",
      "suspect": {"number": 2, "name": "The resort fee", "alias": "Amenity fee · Destination fee", "tag": "SUSPECT", "stamp_pos": [0.70, 0.12],
                  "type_on": ["Name:", "Aliases:"]}})
beat("m2b", S_HOTEL, "Known associates: a pool you will never swim in.",
     manual(img("a small inflatable paddling pool standing on the carpet of a plain 1950s city hotel room, a radiator and a window with city lights behind, playful print-ad style",
         motion="static"), clip=True))
beat("c2", S_HOTEL, "In 2019, the Attorney General for Washington, D.C., sued Marriott.",
     arch("hotel_clerk_dover_1938.jpg", "Hotel clerk at desk, Dover, Delaware, 1938 · Library of Congress", motion="zoom_in"),
     label="DC Attorney General v. Marriott · July 2019", alleged=True)
beat("c3", S_HOTEL, "The lawsuit says at least one hundred and eighty-nine Marriott hotels charged these fees:",
     stat(189, "Marriott hotels with resort fees · DC complaint, 2019 · ALLEGED"),
     pause_at={"word": "one", "sec": 0.5, "hit": "stamp"})
beat("c4", S_HOTEL, "from nine to ninety-five dollars, per room, per day.",
     img("a 1950s hotel bill on a desk: a cream sheet with a plain green header band, plain ruled lines and empty columns, a fountain pen beside it, plain cream background",
         motion="static", hand_marks=True, marks=[write("$9 – $95 / night", on="nine", x=0.50, y=0.40, w=0.30, h=0.07)]),
     alleged=True)
beat("c5", S_HOTEL, "Near the end of booking, the fee sat under a heading that sounded official: Taxes and Fees.",
     reuse("c4", hand_marks=True, marks=[write("$9 – $95 / night", at=0.0, x=0.50, y=0.40, w=0.30, h=0.07)],
           closeup=closeup("booking,", [0.50, 0.62], 1.8, [write("TAXES AND FEES", on="Taxes", x=0.42, y=0.62, w=0.26, h=0.06, color="ink"),
                                                            circle(0.42, 0.62, 0.30, 0.10, "Fees.", target=[0.29, 0.59, 0.55, 0.65])])))
beat("c6", S_HOTEL, "From customers in D.C. alone, the Attorney General says, that came to millions of dollars.",
     doc("DC Attorney General · press release · July 9, 2019", "Marriott resort fees",
         "Marriott has charged resort fees to tens of thousands of District consumers over the years, totaling millions of dollars.",
         "totaling millions of dollars", on="millions", kicker="PRESS RELEASE  ·  ALLEGED  ·  QUOTED", seed=74, lead=0.6))
beat("c7", S_HOTEL, "Resort fees aren't taxes. They just like to sit next to them.", kin())
beat("c8", S_HOTEL, "In 2023, Marriott agreed with Texas to show the total price most prominently.",
     arch("hotel_sign_cooperstown_1937.jpg", "Hotel sign, Cooperstown, New York, 1937 · Library of Congress", motion="zoom_in"),
     label="Texas Attorney General · May 2023")

# ------------------------------------------------------------------ Why a split price feels cheaper (insert, ~25 s)
beat("n1", S_BRAIN, "Why does it work? In 1998, three marketing researchers split prices into a base and a surcharge.",
     img("a cream paper price tag being cut into two pieces by a pair of red-handled scissors, plain cream background, 1950s print-ad style",
         motion="static", hand_marks=True, marks=[write("BASE", on="base", x=0.35, y=0.70, w=0.12, h=0.06), write("+ SURCHARGE", on="surcharge.", x=0.68, y=0.70, w=0.22, h=0.06)]),
     label="Morwitz, Greenleaf & Johnson · J. Marketing Research · 1998")
beat("n2", S_BRAIN, "The total price was the same. It was just served in pieces.",
     reuse("n1", closeup=closeup("served", [0.50, 0.50], 1.6, [write("SAME TOTAL", on="same.", x=0.50, y=0.22, w=0.24, h=0.07)])),
     label="Morwitz, Greenleaf & Johnson · J. Marketing Research · 1998")
beat("n3", S_BRAIN, "People remembered paying less in total. And they bought more.", kin())
beat("n4", S_BRAIN, "Your brain files the first number. Everything after it is small print.",
     img("an open 1950s office filing drawer with one large blank index card standing at the front and a few tiny crumpled paper slips at the very back, plain cream background",
         motion="static", hand_marks=True, marks=[write("$30", on="first", x=0.50, y=0.40, w=0.12, h=0.09, color="ink"),
                                                  write("+ fees", on="small", x=0.72, y=0.30, w=0.06, h=0.025, color="ink")]))
beat("sub", S_BRAIN, "If you like catching prices in the act, subscribe. The Inspector has more files.",
     reuse("o4", motion="zoom_in"), cta={"on": "subscribe.", "click_on": "Inspector", "pos": [0.64, 0.62]})

# ------------------------------------------------------------------ In defence of the accused
chapter("t4", S_DEF, "In defence of the accused.", "In defence of the accused")
beat("d1", S_DEF, "One: StubHub says it tried honesty.", reuse("a2", motion="zoom_out"))
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
beat("d4", S_DEF, "In plain English, hidden fees didn't just win buyers from rivals. They made people spend more.", kin())
beat("d5", S_DEF, "Three: fees pay for real things. Card payments, staff, the venue.",
     arch("giant_food_cashier_1942.jpg", "Cashier checking out a customer, Giant Food, Washington, D.C., 1942 · Library of Congress", motion="zoom_in"))
beat("d6", S_DEF, "America's new rule bans no fee at all. It only wants the total, upfront.",
     arch("briggs_stadium_tickets_1942.jpg", "Buying tickets for the ball game, Briggs Stadium, Detroit, 1942 · Library of Congress", motion="static"),
     label="FTC rule · in force May 2025")
beat("d7", S_DEF, "The fee may be fair. Hiding it isn't.", kin())

# ------------------------------------------------------------------ Friday 9:00 AM — One fee, three laws (one ticket, three stamps)
chapter("t5", S_LAW, "Friday, nine a.m.", "Friday 9:00 AM — One fee, three laws")
DESK = "a 1950s customs desk seen from above with a wooden rubber-stamp rack and an ink pad near the top edge, a wide stretch of empty plain wood in the middle, warm light"
beat("l1", S_LAW, "Larry's ticket goes on a trip. Three borders. Three stamps.",
     img(DESK, note="after the storyboard: the code-drawn $30 ticket is composited in the middle (images/l1.png)", motion="static",
         closeup=closeup("borders.", [0.50, 0.50], 1.4, motion="zoom_out")))
beat("l2", S_LAW, "Border one: America. Since May 2025, ticket sellers and short stays, from hotels to holiday rentals, must show the total price upfront.",
     reuse("l1", hand_marks=True,
           closeup=closeup("short", [0.47, 0.43], 1.45, [stamp('USA · TOTAL UPFRONT · MAY 2025', 0.35, 0.445, on='total', angle=-8, w=0.18)])),
     pause_at={"word": "May", "sec": 0.4, "hit": None})
beat("l3", S_LAW, "In April 2026, StubHub agreed to pay ten million dollars back to buyers,",
     stat(10, "StubHub settlement · FTC · April 2026", prefix="$", suffix="m"),
     pause_at={"word": "ten", "sec": 0.6, "hit": "stamp"})
beat("l3b", S_LAW, "over fees it showed too late.",
     reuse("a5", hand_marks=True, push={"center": [0.70, 0.40], "zoom": 1.8},
           marks=[write("B", at=0.0, x=0.70, y=0.20, w=0.05, h=0.08), write("$30…", at=0.0, x=0.70, y=0.30, w=0.10, h=0.07),
                  write("+ fees at checkout", at=0.0, x=0.70, y=0.40, w=0.20, h=0.05)]), label="FTC · April 2026 · settlement")
beat("l4", S_LAW, "America has done this before. In 1958, a law put a sticker on the window of every new car:",
     arch("car_showroom_1942.jpg", "Car showroom, Pierson Motor Company, Lititz, Pennsylvania, 1942 · Library of Congress", motion="zoom_in"),
     label="Automobile Information Disclosure Act · 1958")
beat("l5", S_LAW, "the price, every option, the delivery charge, and the total.",
     img("the side window of a 1950s two-tone sedan in a showroom with a large blank paper sticker taped inside the glass, close view",
         motion="static", hand_marks=True,
         marks=[write("PRICE", on="price,", x=0.50, y=0.30, w=0.16, h=0.05, color="ink"), write("OPTIONS", on="option,", x=0.50, y=0.40, w=0.18, h=0.05, color="ink"),
                write("DELIVERY", on="delivery", x=0.50, y=0.50, w=0.18, h=0.05, color="ink"), write("TOTAL", on="total.", x=0.50, y=0.62, w=0.16, h=0.06)]),
     label="15 U.S.C. 1232 · 1958")
beat("l6", S_LAW, "Cars got the total sixty-seven years before concert tickets did.",
     reuse("l5", hand_marks=True, marks=[write("TOTAL", at=0.0, x=0.50, y=0.62, w=0.16, h=0.06),
                                         circle(0.50, 0.62, 0.22, 0.10, "total", target=[0.42, 0.59, 0.58, 0.65]),
                                         write("67 YEARS", on="sixty-seven", x=0.80, y=0.62, w=0.16, h=0.06)]),
     pause_at={"word": "sixty-seven", "sec": 0.4, "hit": None})
beat("l7", S_LAW, "Border two: Britain. Since April 2025, the price must include every fee you can't avoid.",
     reuse("l1", hand_marks=True, marks=[stamp('USA · TOTAL UPFRONT · MAY 2025', 0.35, 0.445, at=0.0, angle=-8, w=0.18), stamp('UK · ALL FEES IN · APRIL 2025', 0.585, 0.58, on='include', angle=6, w=0.18)]))
beat("l8", S_LAW, "A driving-school group hid a three-pound booking fee charged to over eighty thousand learner drivers.",
     img("a small 1950s family car with a blank white square plate on the front bumper, parked on a quiet British street, cheerful print-ad style",
         motion="static", hand_marks=True, marks=[write("L", at=0.0, x=0.40, y=0.70, w=0.03, h=0.05),
                                                  write("£3 FEE", on="three-pound", x=0.78, y=0.22, w=0.14, h=0.07)]),
     label="CMA · April 2026")
beat("l9", S_LAW, "It paid a four point two million pound fine,",
     stat(4.2, "fine · CMA, April 2026", decimals=1, prefix="£", suffix="m"),
     pause_at={"word": "four", "sec": 0.6, "hit": "stamp"})
beat("l9b", S_LAW, "and over seven hundred and sixty thousand pounds in refunds.",
     stat(760, "refunded to learners · CMA, April 2026", prefix="over £", suffix="k"))
beat("l10", S_LAW, "In June, StubHub's British arm was fined too.",
     reuse("o1", hand_marks=True, marks=[write("$30", at=0.0, **TICKET_PRICE_BOX, color="ink"), stamp('UK · FINED · JUNE 2026', 0.615, 0.70, on='fined', angle=-12, w=0.20)]),
     label="CMA · June 2026")
beat("l11", S_LAW, "Three pounds. Very expensive pounds.",
     reuse("l8", push={"center": [0.60, 0.40], "zoom": 1.6}, hand_marks=True, marks=[write("£3 FEE", at=0.0, x=0.78, y=0.22, w=0.14, h=0.07),
                                                                                    circle(0.78, 0.22, 0.18, 0.11, "Very", target=[0.71, 0.185, 0.85, 0.255])]))
beat("l12", S_LAW, "Border three: the European Union. The total price, taxes included, before you pay.",
     reuse("l1", hand_marks=True, marks=[stamp('USA · TOTAL UPFRONT · MAY 2025', 0.35, 0.445, at=0.0, angle=-8, w=0.18), stamp('UK · ALL FEES IN · APRIL 2025', 0.585, 0.58, at=0.0, angle=6, w=0.18), stamp('EU · TOTAL BEFORE YOU PAY', 0.655, 0.44, on='total', angle=-4, w=0.16)]))
beat("l13", S_LAW, "And any extra charge needs your clear yes. A pre-ticked box is not a yes.",
     img("a 1950s paper order form on a desk with three plain empty lines, each line ending in a small square checkbox, the last checkbox already ticked in black ink, plain cream background",
         motion="static", hand_marks=True, marks=[circle(0.30, 0.66, 0.08, 0.10, "pre-ticked", target=[0.27, 0.62, 0.33, 0.70]),
                                                  write("NOT A YES", on="not", x=0.55, y=0.66, w=0.22, h=0.07)]))
beat("l14", S_LAW, "One ticket. Three stamps. One message: show the total.",
     reuse("l1", motion="zoom_out", marks=[stamp('USA · TOTAL UPFRONT · MAY 2025', 0.35, 0.445, at=0.0, angle=-8, w=0.18), stamp('UK · ALL FEES IN · APRIL 2025', 0.585, 0.58, at=0.0, angle=6, w=0.18), stamp('EU · TOTAL BEFORE YOU PAY', 0.655, 0.44, at=0.0, angle=-4, w=0.16)]))

# ------------------------------------------------------------------ Saturday 10:00 AM — Three checks
chapter("t6", S_CHECK, "Saturday, ten a.m.", "Saturday 10:00 AM — Three checks")
beat("x1", S_CHECK, "Three checks before you pay. One. Look for the all-in switch.",
     manual(img("a big chrome 1950s toggle switch on a cream enamel panel, switched to the left, studio lighting, plain background",
         motion="static", hand_marks=True, marks=[write("ALL-IN PRICES", on="all-in", x=0.50, y=0.18, w=0.30, h=0.07, color="ink")]), clip=True))
beat("x2", S_CHECK, "Some ticket sites can show prices with fees included. Turn it on before you browse, not after you've fallen for a seat.",
     reuse("x1", hand_marks=True, marks=[write("ALL-IN PRICES", at=0.0, x=0.50, y=0.18, w=0.30, h=0.07, color="ink"), write("ON", on="on", x=0.72, y=0.50, w=0.08, h=0.08)],
           closeup=closeup("before", [0.50, 0.50], 1.6)))
beat("x3", S_CHECK, "Two. Go to the last screen before you decide. The real price lives one click before Pay.",
     reuse("m1b", hand_marks=True, marks=[write("LAST SCREEN", on="last", x=0.17, y=0.30, w=0.22, h=0.06)],
           closeup=closeup("real", [0.50, 0.40], 1.6, [write("$48", on="price", x=0.535, y=0.40, w=0.09, h=0.04)])))
beat("x4", S_CHECK, "Three. Compare totals, not headlines. A forty-dollar ticket with no fees beats a thirty-dollar ticket with eighteen.",
     {"type": "chart", "chart": {"kind": "bar", "title": "What you actually pay", "labels": ["$40 · no fees", "$30 + $18 fees"], "values": [40, 48],
                                 "unit": "$", "highlight": 0, "value_labels": True, "note": "Illustration"}})
beat("x5", S_CHECK, "The cheapest ticket is the one with the smallest last number.", kin())

# ------------------------------------------------------------------ Case closed + end screen (Ep.5 teaser: tip screens)
beat("z0", S_CLOSE, "Case closed. Larry paid forty-eight dollars for a thirty-dollar ticket.",
     manual(img(f"{LARRY} happy in the crowd at a 1950s concert hall, stage lights in the distance, holding his paper ticket stub, warm light",
         motion="zoom_in"), clip=True), stamp={"text": "Case closed", "on": "Case", "big": True},
     ledger=[tab("PAID", "$48.00 for a $30 ticket", "forty-eight", note=True)])
beat("z0b", S_CLOSE, "He went to the concert anyway. The band was worth thirty. The checkout was worth nothing. Now he knows where the eighteen went.",
     reuse("z0", push={"center": [0.45, 0.40], "zoom": 1.6}, closeup=closeup("checkout", [0.58, 0.62], 2.0)), hero=True)
ES = {"number": "004", "title": "The fee at the end", "stamp": "Case closed",
      "verdict": ["Guilty: the checkout fee and its cousin, the resort fee.", "Accomplice: the first number on the screen."],
      "next": {"number": "005", "title": "Tip screens", "tagline": "18 % · 22 % · 25 % · No tip?", "image_file": "next_tablet.png",
               "copies": 1, "writes": [{"text": "No tip", "x": 0.5, "y": 0.86, "h": 0.035}],
               "label": ["72 % say tipping is expected in more places", "Pew Research Center · Nov 2023"], "label_under": True},
      "times": {"swap": 5.8, "draw": 6.4, "ddur": 3.0, "writes": 9.6, "tagline": 10.4, "zone": 11.0, "sketch": 11.4,
                "skdur": 1.0, "label": 12.6, "sub": 13.2, "click": 14.3, "push": 15.0}}
beat("z1", S_CLOSE, "The verdict. Guilty: the checkout fee and its cousin, the resort fee. Accomplice: the first number on the screen.",
     {"type": "endscreen", "endscreen": ES}, block_start=True, sting="ub_sting_brass", sting_at=0.1)
beat("z4", S_CLOSE, "Next case: the screen that asks how much you'd like to tip, before you've had your coffee.",
     {"type": "continue"}, block_at=7.0)  # the Pew figure is on screen only (plate under the tablet sketch)
beat("z5", S_CLOSE, "Subscribe, so the next case file finds you.", {"type": "continue"}, block_at=12.8, block_end=18.5)

# ------------------------------------------------------------------ 7 Shorts (frame 0 = hook text over the Short's strongest picture)
LONG = {b["id"]: b for b in B}


def L(bid, text=None, keep=("punch", "pause_at", "sfx_at", "sfx", "say", "stamp", "label", "ledger", "alleged"), **kw):
    src = LONG[bid]
    v = src["visual"]
    if v["type"] in ("image", "archive", "clip"):
        vis = {"type": "reuse", "beat": bid, "motion": v.get("motion", "zoom_in")}
        for k in ("marks", "hand_marks", "closeup", "push", "stamps"):
            if v.get(k) is not None:
                vis[k] = copy.deepcopy(v[k])
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
               L("a6"), L("a8"), L("a9"), L("a10"), L("a12"), L("a14")]},
    {"id": "s3", "title": "$16.4 billion in fees (alleged) #shorts", "hook": "$16.4 BILLION", "hook_on": "b5",
     "beats": [L("b1"), L("b2"), L("b3"), L("b4"), L("b5"), L("b9"), L("b6")]},
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
