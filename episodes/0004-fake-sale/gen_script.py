"""Episode 0004 — Case file #003 "The Fake Sale". Writes episodes/0004-fake-sale/script.json
Run: python episodes/0004-fake-sale/gen_script.py
Marks/inserts coordinates are first guesses; they are measured on the storyboard frames before the preview."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "script.json"
LOC = "Library of Congress, Prints & Photographs Division (no known restrictions)"

B = []


def make_ticket(path):
    """Code-drawn subject for the Ep.4 teaser sketch: a 1950s concert ticket with a blank price box (no generation)."""
    from PIL import Image, ImageDraw, ImageFont
    W, H = 1376, 768
    im = Image.new("RGB", (W, H), (243, 233, 210))
    d = ImageDraw.Draw(im)
    ink, red, paper = (30, 27, 24), (210, 69, 47), (252, 247, 233)

    def fnt(name, size):
        for q in (HERE.parent.parent / "assets" / "fonts" / name, Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")):
            if q.exists():
                return ImageFont.truetype(str(q), size)
    x0, y0, x1, y1 = 250, 190, 1130, 590
    d.rounded_rectangle((x0, y0, x1, y1), radius=26, fill=paper, outline=ink, width=10)
    sx = x1 - 230  # perforated stub
    for yy in range(y0 + 24, y1 - 20, 34):
        d.ellipse((sx - 7, yy - 7, sx + 7, yy + 7), fill=(243, 233, 210), outline=ink, width=3)
    d.rectangle((x0 + 40, y0 + 40, sx - 40, y0 + 150), fill=red)
    d.text(((x0 + sx) / 2, y0 + 95), "ADMIT ONE", font=fnt("Anton-Regular.ttf", 92), fill=paper, anchor="mm")
    d.text(((x0 + sx) / 2, y0 + 215), "ROW G · SEAT 12", font=fnt("ArchivoBlack-Regular.ttf", 40), fill=ink, anchor="mm")
    d.rectangle((x0 + 160, y0 + 270, sx - 160, y1 - 40), outline=ink, width=6)  # the blank price box
    d.text((x1 - 115, (y0 + y1) / 2), "No. 004", font=fnt("ArchivoBlack-Regular.ttf", 40), fill=ink, anchor="mm")
    im.save(path)


make_ticket(HERE / "next_ticket.png")


def beat(id, section, text, visual, **kw):
    b = {"id": id, "section": section, "text": text, "visual": visual}
    b.update(kw)
    B.append(b)
    return b


def img(prompt=None, prompts=None, motion="zoom_in", **kw):
    v = {"type": "image", "motion": motion}
    if prompts:
        v["prompts"] = prompts
    else:
        v["prompt"] = prompt
    v.update(kw)
    return v


def reuse(b, motion="static", index=0, **kw):
    v = {"type": "reuse", "beat": b, "index": index, "motion": motion}
    v.update(kw)
    return v


def arch(file, caption, motion="zoom_in", **kw):
    v = {"type": "archive", "file": file, "look": "print", "credit": LOC, "motion": motion, "caption": caption}
    v.update(kw)
    return v


def kin(text=None, bg="paper"):
    v = {"type": "kinetic", "kinetic": {"bg": bg}}
    if text:
        v["text"] = text
    return v


def title(t):
    return {"type": "title", "text": t}


def doc(source, headline, body, highlight, on, mark="underline", kicker=None, seed=1, pre=None, **kw):
    d = {"source": source, "headline": headline, "body": body, "highlight": highlight, "on": on, "mark": mark, "seed": seed}
    if kicker:
        d["kicker"] = kicker
    if pre:
        d["pre"] = pre
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


def cross(x, y, w, h, on, **kw):
    return {"type": "cross", "x": x, "y": y, "w": w, "h": h, "on": on, **kw}


def closeup(on, center, zoom=2.0, marks=None, motion="zoom_in"):
    """Second framing of the same picture: push-in on a detail from the word `on`; marks in original-picture fractions."""
    return {"on": on, "center": center, "zoom": zoom, "marks": marks or [], "motion": motion}


def strike(x, y, w, on, **kw):
    """A red line struck through a written price."""
    m = {"type": "underline", "x": x, "y": y, "w": w, "h": 0.02, **kw}
    if on is not None:
        m["on"] = on
    return m


WAS_DASH = [write("WAS $—", at=0.0, x=0.50, y=0.52, w=0.16, h=0.09, color="ink"),
            strike(0.50, 0.52, 0.19, None, at=0.0, dur=0.01, hand=False)]


def chapter(id, section, spoken, card):
    return beat(id, section, spoken, title(card), pause_before=1.0, sting="ub_sting_trumpet", sting_at=-1.0)


S_OPEN, S_PEN, S_KOHL, S_BRAIN, S_DEF, S_CLOCK, S_CHECK, S_CLOSE = (
    "The case", "Monday 9:00 AM: Fair and square", "Tuesday 7:40 PM: Always on sale", "Why your brain says yes",
    "In defence of the accused", "Friday 11:58 PM: The clock that resets", "Saturday 10:00 AM: Three checks", "Case closed")

TAG_W = dict(color="ink", fnt="marker")

# ------------------------------------------------------------------ cold open (≤ 15 s to the folder)
beat("o1", S_OPEN, "A hair dryer at Boots. Was forty-nine ninety-nine.",
     img("a chrome 1950s hand-held hair dryer standing on a shop shelf beside a large blank cream paper price tag with a red border on a string, plain cream background, product shot",
         motion="static", hand_marks=True,
         marks=[write("BRITAIN · 2024", at=0.0, x=0.365, y=0.555, w=0.15, h=0.035, color="ink", fnt="body"),
                write("WAS £49.99", on="Was", x=0.365, y=0.635, w=0.20, h=0.07, **TAG_W)]),
     pause_at={"word": "forty-nine", "sec": 0.45, "hit": "stamp"})
beat("o2", S_OPEN, "Now eighteen ninety-nine.",
     reuse("o1", hand_marks=True,
           marks=[write("BRITAIN · 2024", at=0.0, x=0.365, y=0.555, w=0.15, h=0.035, color="ink", fnt="body"),
                  write("WAS £49.99", at=0.0, x=0.365, y=0.635, w=0.20, h=0.07, color="ink"),
                  cross(0.365, 0.635, 0.22, 0.08, "Now"),
                  write("NOW £18.99", on="eighteen", x=0.365, y=0.725, w=0.22, h=0.075)]),
     pause_at={"word": "eighteen", "sec": 0.45, "hit": "stamp"})
beat("o3", S_OPEN, "In the twelve months before, it had never cost forty-nine ninety-nine there. Not once.",
     doc("Which? · price check · Nov 2024", "The £49.99 that wasn't",
         "A hair dryer was £18.99 on Black Friday, marked down from £49.99. It had never been £49.99 at Boots in the preceding 12 months.",
         "never been £49.99", on="never", kicker="CONSUMER GROUP  ·  QUOTED", seed=11, lead=0.6))
beat("cf1", S_OPEN, "Case file number three. The sale that never was. Larry is made up. The forty-nine ninety-nine was too.",
     {"type": "casefile", "casefile": {"mode": "open", "number": "003", "title": "The fake sale", "typed": False, "open_stamp_on": "never",
                                        "inside": ["SUBJECT: Larry", "EXHIBIT: one hair dryer", "", "SUSPECTS: 2", "STATUS: open"],
                                        "writes": [{"line": 0, "text": "(fictional)", "on": "made"},
                                                   {"line": 2, "text": "£49.99 — also fictional", "on": "forty-nine"}]}})
beat("m1", S_OPEN, "Suspect number one. Name: the was price. Aliases: original, regular, compare at.",
     {"type": "mugshot", "prompt": "a single cream paper price tag with a thick red border hanging on a string from a small nail, a bold black line struck through its upper half, plain light grey wall, nothing else in the picture, studio lighting",
      "suspect": {"number": 1, "name": "The WAS price", "alias": "Original · Regular · Compare at", "last_seen": "Every Black Friday", "tag": "SUSPECT"},
      "photo_marks": [write("WAS", on="was", x=0.5, y=0.47, w=0.30, h=0.13, color="ink"),
                      write("$—", on="price.", x=0.5, y=0.62, w=0.24, h=0.13, color="ink"),
                      strike(0.5, 0.47, 0.34, "Aliases:"), strike(0.5, 0.62, 0.30, "Aliases:", delay=0.5)]})
beat("m1c", S_OPEN, "Last seen: every Black Friday.",
     reuse("o1", hand_marks=True, push={"center": [0.40, 0.62], "zoom": 1.6},
           marks=[write("BRITAIN · 2024", at=0.0, x=0.365, y=0.555, w=0.15, h=0.035, color="ink", fnt="body"),
                  write("WAS £49.99", at=0.0, x=0.365, y=0.635, w=0.20, h=0.07, color="ink"),
                  circle(0.365, 0.635, 0.26, 0.14, "Black")]))
beat("m1b", S_OPEN, "It never touches your money. It just tells you how much you're saving.",
     img("{larry} leaning in with a delighted smile while an oversized cream paper price tag on a string hovers by his ear as if whispering a secret, plain cream background",
         motion="static", hand_marks=True, marks=[write("YOU SAVE £31", on="saving.", x=0.28, y=0.55, w=0.19, h=0.07, angle=27)]))

# ------------------------------------------------------------------ Monday 9:00 AM — Fair and square (J.C. Penney spine, ≥ 10 pictures)
chapter("t1", S_PEN, "Monday, nine a.m.", "Monday 9:00 AM — Fair and square")
beat("p1", S_PEN, "Larry reads about a store that tried to arrest this suspect.",
     img("{larry} at a sunny breakfast table reading a folded newspaper with a coffee cup, mid shot", motion="zoom_in"))
beat("p2", S_PEN, "In 2011, J.C. Penney ran five hundred and ninety different promotions.",
     arch("sale_signs_montgomery_1939.jpg", "Sale signs, Montgomery, Alabama, 1939 · Library of Congress", motion="zoom_in", crop=[0.05, 0.0, 0.95, 1.0]),
     pause_at={"word": "five", "sec": 0.8, "hit": "stamp"}, stamp={"text": "590 promotions", "on": "promotions"},
     label="J.C. Penney · 2011")
beat("p3", S_PEN, "Only zero point two percent of its revenue came from full-price sales.",
     {"type": "stat", "stat": {"value": 0.2, "decimals": 1, "suffix": "%", "label": "of revenue at full price · J.C. Penney, 2011"}},
     pause_at={"word": "zero", "sec": 0.7, "hit": "stamp"})
beat("p3b", S_PEN, "Almost three-quarters came from things marked half off or more.",
     {"type": "stat", "stat": {"value": 73, "prefix": "≈", "suffix": "%", "label": "of revenue at 50 % off or more · LA Times, Jan 2012"}})
beat("p4", S_PEN, "So in 2012 a new boss, Ron Johnson, the man behind the Apple Store, tore it all up.",
     img("a shop wall covered from edge to edge with rows of pinned red and cream paper sale tags of different sizes, flat front view, no people, nothing in front of the wall",
         motion="static", hand_marks=True, marks=[cross(0.5, 0.5, 0.62, 0.62, "tore")]))
beat("p5", S_PEN, "No fake markdowns. No coupons. One honest price on every tag. He called it Fair and Square.",
     img("a neatly folded white shirt on a shop counter with one clean cream price tag on a string, warm light, simple composition", motion="zoom_in"),
     stamp={"text": "Fair and square", "on": "Fair"})
beat("p6", S_PEN, "\"People are disgusted,\" he said, \"with the lack of integrity on pricing.\"",
     doc("Fortune · Jan 2012", "Ron Johnson on pricing", "\"People are disgusted with the lack of integrity on pricing.\"",
         "disgusted with the lack of integrity", on="disgusted", kicker="INTERVIEW  ·  QUOTED", seed=21, lead=0.4))
beat("p7", S_PEN, "Honest prices. The customers were not ready for the experience.",
     img("an empty, spotless 1950s department store floor with tidy clothing racks and one bored shop assistant leaning on the counter, no customers", motion="zoom_out"))
beat("p8", S_PEN, "That year, sales fell by a quarter.",
     {"type": "chart", "chart": {"kind": "bar", "title": "J.C. Penney sales", "labels": ["2011", "2012"], "values": [17.26, 12.99],
                                 "unit": "$bn", "highlight": 1, "note": "−24.8 % · annual results, Feb 2013"}},
     pause_at={"word": "quarter.", "sec": 0.7, "hit": "stamp"})
beat("p9", S_PEN, "The company lost nine hundred and eighty-five million dollars.",
     img("an old brass cash register with its drawer wide open and completely empty, a single moth fluttering out, dark shop at night", motion="zoom_in"),
     pause_at={"word": "nine", "sec": 0.8, "hit": "stamp"}, stamp={"text": "−$985,000,000", "on": "dollars."})
beat("p10", S_PEN, "Even before Johnson was fired in April 2013, the old game was back.",
     arch("chain_store_window_signs_1940.jpg", "Signs on a chain store window, 1940", motion="zoom_in", crop=[0.02, 0.03, 0.96, 0.93]), label="April 2013")
beat("p11", S_PEN, "A five-dollar T-shirt got a six-dollar tag, so it could be marked down to five again.",
     img("a plain white T-shirt on a wooden hanger with a large blank cream paper price tag, plain cream background", motion="static", hand_marks=True,
         marks=[write("$5", on="five-dollar", x=0.50, y=0.45, w=0.06, h=0.07, **TAG_W),
                cross(0.50, 0.45, 0.08, 0.08, "six-dollar"),
                write("$6", on="six-dollar", x=0.50, y=0.55, w=0.06, h=0.07, **TAG_W),
                write("SALE $5", on="again.", x=0.50, y=0.65, w=0.09, h=0.06)]))
beat("p12", S_PEN, "The T-shirt did not change. The tag got promoted.",
     img("a cream paper price tag on a string wearing a tiny gold crown and a small red sash, proud, plain cream background", motion="zoom_in"),
     stamp={"text": "Promoted", "on": "promoted."})
beat("p13", S_PEN, "The store that stopped lying nearly went broke. Our suspect doesn't work alone.",
     reuse("m1", hand_marks=True, marks=WAS_DASH + [write("+ ?", on="alone.", x=0.78, y=0.45, w=0.12, h=0.12)]))

# ------------------------------------------------------------------ Tuesday 7:40 PM — Always on sale (Kohl's)
chapter("t2", S_KOHL, "Tuesday, seven-forty p.m.", "Tuesday 7:40 PM — Always on sale")
beat("k1", S_KOHL, "Larry wants a stand mixer. And it's on sale. Of course it is.",
     img("{larry} in a department store aisle gazing lovingly at a shiny cream stand mixer on a pedestal under a spotlight, a big blank red sign hanging above it",
         motion="static", hand_marks=True, marks=[write("SALE", at=0.3, x=0.495, y=0.145, w=0.15, h=0.12, color="paper", fnt="headline")]))
beat("k2", S_KOHL, "First, the evidence. Britain's Which? checked two hundred and twenty-seven Black Friday deals.",
     {"type": "stat", "stat": {"value": 227, "label": "Black Friday deals checked · Which?, Britain, 2024"}},
     pause_at={"word": "two", "sec": 0.8, "hit": "stamp"})
beat("k2b", S_KOHL, "Nine in ten were the same price, or cheaper, at other times of the year.",
     doc("Which? · Nov 2024", "Black Friday deals",
         "Of 227 Black Friday deals at eight big retailers, 92% were the same price or cheaper at other times of the year.",
         "92% were the same price or cheaper", on="Nine", kicker="CONSUMER GROUP  ·  PARAPHRASED", seed=31, lead=0.3))
beat("k3a", S_KOHL, "Now Larry's mixer. Consumer Reports priced this exact one at Kohl's:",
     doc("Consumer Reports · June 2013", "Fake sales can cost you",
         "Last year, we compared prices of more than a dozen home and kitchen products on sale at Kohl's with prices at a handful of online retailers. We easily were able to beat Kohl's deals.",
         "We easily were able to beat Kohl's deals", on="priced", kicker="CONSUMER REPORTS  ·  QUOTED", seed=35, lead=0.2),
     label="Consumer Reports · checked 2012")
beat("k3", S_KOHL, "on sale for four eighty-nine ninety-nine.",
     img("a shiny cream stand mixer on a white shop shelf with a large blank cream paper price tag hanging from it, plain background, product shot", motion="static", hand_marks=True,
         marks=[write("SALE $489.99", on="four", x=0.81, y=0.60, w=0.15, h=0.06, angle=-12)]),
     pause_at={"word": "four", "sec": 0.7, "hit": "stamp"}, label="Consumer Reports · checked 2012",
     ledger=[{"label": "MIXER", "amount": "$489.99", "on": "four"}])
beat("k4", S_KOHL, "\"Regular\" price: five forty-nine ninety-nine.",
     reuse("k3", hand_marks=True, push={"center": [0.80, 0.57], "zoom": 2.2},
           marks=[write("SALE $489.99", at=0.0, x=0.81, y=0.60, w=0.15, h=0.06, angle=-12),
                  write("REG. $549.99", on="five", x=0.80, y=0.51, w=0.15, h=0.06, angle=-12, **TAG_W)]),
     label="Consumer Reports · checked 2012", ledger=[{"label": "\"WAS\"", "amount": "$549.99", "on": "five"}])
beat("k5", S_KOHL, "On Amazon, the same mixer: three ninety-nine ninety-nine.",
     img("the same shiny cream stand mixer sitting in an open plain cardboard delivery box on a doorstep, daylight", motion="zoom_in"),
     pause_at={"word": "three", "sec": 0.7, "hit": "stamp"}, label="Consumer Reports · checked 2012",
     ledger=[{"label": "ELSEWHERE", "amount": "$399.99", "on": "three"}])
beat("k6", S_KOHL, "Larry's saving: sixty dollars. His real overpay: ninety.",
     img("{larry} proudly holding up a long shop receipt with both hands, beaming, plain cream background", motion="zoom_in"),
     pause_at={"word": "ninety.", "sec": 0.7, "hit": "stamp"},
     ledger=[{"label": "OVERPAID", "amount": "$90.00", "loss": True, "circle": True, "on": "ninety."}])
beat("k7", S_KOHL, "So how regular is regular? One consumer advocate tracked twenty Kohl's items for a hundred and three days.",
     img("a 1950s desk wall calendar with many days crossed out in red pencil, next to a notebook full of handwritten price columns and a pencil", motion="static",
         hand_marks=True, marks=[circle(0.37, 0.35, 0.38, 0.58, "tracked"), write("103 DAYS", on="hundred", x=0.73, y=0.30, w=0.20, h=0.08)]),
     label="tracked 2003")
beat("k8", S_KOHL, "They were on sale eighty-six percent of the time.",
     {"type": "stat", "stat": {"value": 86, "suffix": "%", "label": "of the time on sale · tracked 2003"}},
     pause_at={"word": "eighty-six", "sec": 0.8, "hit": "stamp"})
beat("k9", S_KOHL, "One in four never sold at its regular price at all. Regular price: the thing that happens on the other fourteen percent of days.",
     img("four identical white shirts on hangers on a rail, three wearing bright red sale tags and the fourth wearing a plain tag covered in dust and cobwebs",
         motion="static", hand_marks=True, marks=[circle(0.79, 0.58, 0.12, 0.26, "never"),
                                                 write("REG.", on="regular", x=0.79, y=0.585, w=0.05, h=0.04, color="ink")],
         closeup=closeup("Regular", [0.80, 0.55], 2.2, [circle(0.79, 0.58, 0.12, 0.26, None, at=0.0, hand=False, dur=0.01),
                                                        write("REG.", at=0.0, x=0.79, y=0.585, w=0.05, h=0.04, color="ink"),
                                                        write("14 %", on="fourteen", x=0.66, y=0.36, w=0.07, h=0.06)])),
     label="tracked 2003")
beat("k10", S_KOHL, "Years later, Checkbook magazine tracked nineteen big retailers. Most of the time, the sale price simply was the price.",
     img("a 1950s woman with a clipboard and pencil noting down prices on a department store shelf of boxed goods, mid shot", motion="static",
         hand_marks=True, closeup=closeup("Most", [0.40, 0.58], 2.0, [{"type": "underline", "x": 0.38, "y": 0.64, "w": 0.10, "h": 0.02, "on": "simply"}])),
     label="Checkbook 2018")
beat("k11", S_KOHL, "A federal appeals court summed it up in three words: price advertisements matter.",
     doc("Hinojos v. Kohl's · 9th Cir. · 2013", "Fake 'original' prices", "\"Misinformation about a product's 'normal' price is, therefore, significant to many consumers ... In sum, price advertisements matter.\"",
         "price advertisements matter", on="price", kicker="COURT OPINION  ·  QUOTED", seed=41, lead=1.2))
beat("k12", S_KOHL, "Los Angeles sued four department-store chains over fake original prices.",
     img("four department-store shopping bags standing in a row on courthouse steps like defendants, 1950s courthouse columns behind, morning light", motion="zoom_in"),
     label="LA lawsuit 2016")
beat("k13", S_KOHL, "Five years later, the city dropped its case against Kohl's and Macy's, after the judge tore into its expert witness.",
     img("an empty wooden witness stand in a wood-panelled 1950s courtroom, a crumpled paper chart lying on the floor beside it, morning light", motion="static",
         hand_marks=True, closeup=closeup("after", [0.60, 0.50], 2.0, [circle(0.62, 0.50, 0.14, 0.36, "expert")])),
     label="LA lawsuit 2016 · dropped 2021")
beat("k14", S_KOHL, "Turns out, proving a price was never real is harder than faking one.", kin())

# ------------------------------------------------------------------ Why your brain says yes (insert, ~27 s)
beat("n1", S_BRAIN, "Why does a made-up number work? Psychologists once spun a rigged wheel that stopped on ten or sixty-five, then asked people to guess a percentage.",
     img("a 1950s fairground wheel of fortune in a psychology lab, a scientist in a white coat holding a clipboard beside it", motion="static",
         hand_marks=True, marks=[write("10", on="ten", x=0.455, y=0.20, w=0.04, h=0.07, color="ink"),
                                 write("65", on="sixty-five,", x=0.375, y=0.20, w=0.04, h=0.07, color="ink")],
         closeup=closeup("then", [0.42, 0.35], 2.0, [write("10", at=0.0, x=0.455, y=0.20, w=0.04, h=0.07, color="ink"),
                                                     write("65", at=0.0, x=0.375, y=0.20, w=0.04, h=0.07, color="ink"),
                                                     circle(0.42, 0.15, 0.06, 0.10, "guess")])),
     label="Experiment · 1974")
beat("n2", S_BRAIN, "The sixty-five group guessed almost twice as high.",
     {"type": "chart", "chart": {"kind": "bar", "title": "Median guess", "labels": ["Wheel: 10", "Wheel: 65"], "values": [25, 45],
                                 "unit": "%", "highlight": 1, "note": "Tversky & Kahneman, 1974"}})
beat("n3", S_BRAIN, "At MIT, students wrote down the last digits of their social security number, then bid on a keyboard.",
     img("a 1950s university lecture room seen from the front, students with simple friendly cartoon faces writing numbers on small white cards, a cordless keyboard displayed on the lecturer's desk", motion="static",
         hand_marks=True, marks=[circle(0.50, 0.78, 0.30, 0.16, "keyboard.")]),
     label="MIT · 2003")
beat("n4", S_BRAIN, "High numbers bid fifty-six dollars. Low numbers, sixteen.",
     {"type": "chart", "chart": {"kind": "bar", "title": "Bid for the same keyboard", "labels": ["Low numbers", "High numbers"], "values": [16, 56],
                                 "unit": "$", "highlight": 1, "note": "Ariely, Loewenstein & Prelec, 2003"}},
     pause_at={"word": "fifty-six", "sec": 0.7, "hit": "stamp"})
beat("n5", S_BRAIN, "A later replication found the effect much weaker. Weaker, but not zero.",
     doc("Fudenberg, Levine & Maniadis · AEJ: Micro · 2012", "Replication 2012: effect much weaker",
         "Repeating the experiment, the authors found very weak anchoring effects on what people were willing to pay.",
         "very weak anchoring effects", on="weaker.", kicker="REPLICATION  ·  PARAPHRASED", seed=51, lead=0.4))
beat("n6", S_BRAIN, "And Harvard researchers found outlet shoppers paid about seventy-seven cents more for every extra dollar of original price.",
     img("a factory outlet store clothing rail, each garment wearing a large blank cream paper price tag with a red border, nothing written on the tags", motion="static",
         hand_marks=True, marks=[write("ORIGINAL?", on="original", x=0.5, y=0.15, w=0.16, h=0.06), circle(0.49, 0.50, 0.08, 0.17, "original")]),
     label="HBS · 2018", ledger=[{"label": "each fake $1 → +77¢ paid (HBS 2018)", "note": True, "on": "seventy-seven"}])
beat("sub", S_BRAIN, "If you like catching prices in the act, subscribe. The Inspector has more files.",
     reuse("k1", motion="zoom_in", marks=[write("SALE", at=0.0, x=0.495, y=0.145, w=0.15, h=0.12, color="paper", fnt="headline")]),
     cta={"on": "subscribe.", "click_on": "Inspector"})

# ------------------------------------------------------------------ In defence of the accused
chapter("t3", S_DEF, "In defence of the accused.", "In defence of the accused")
beat("f1", S_DEF, "One: Penney tried honesty, and shoppers walked out. They wanted the hunt.",
     {"type": "clip", "file": "clip_supermarket_1950s.mp4", "in": 256.0, "out": 266.0, "newsreel": "Supermarket film, 1960s",
      "credit": "\"The Supermarket\" (Ezra Baker Films) — Prelinger Archives / Internet Archive (public domain)"})
beat("f2", S_DEF, "Two: a sale can still be a deal. An FTC study checked twenty department-store regular prices.",
     arch("ceiling_price_tag_furniture_1942.jpg", "Price tag drawing, 1942 · Library of Congress", motion="zoom_in", crop=[0.04, 0.12, 0.96, 0.92]), label="FTC study · 1992")
beat("f3", S_DEF, "Twelve were higher than any rival charged. Yet the sale prices averaged about four percent below the competition.",
     doc("FTC Bureau of Economics · 1992", "Department store reference pricing",
         "In 12 of 20 items, the 'regular' price was above the highest competitor price. On average, sale prices were about 4% below competitor average prices.",
         "about 4% below competitor average prices", on="four", kicker="FTC STUDY  ·  PARAPHRASED", seed=61, lead=1.0, post="f2"))
beat("f4", S_DEF, "Three: nobody buys a mattress every month. Waiting for a sale is smart.",
     img("{larry} lying on his back on a showroom mattress with his eyes closed and hands folded, a tiny wall calendar propped on his chest, plain cream background", motion="zoom_in"))
beat("f5", S_DEF, "The was price may be fiction. The saving isn't always. And the accomplice nobody arrests? Our love of a bargain.",
     reuse("m1", hand_marks=True, marks=WAS_DASH + [write("FICTION", on="fiction.", x=0.5, y=0.66, w=0.13, h=0.055, color="ink")],
           closeup=closeup("accomplice", [0.5, 0.66], 1.8, WAS_DASH + [write("FICTION", at=0.0, x=0.5, y=0.66, w=0.13, h=0.055, color="ink"),
                                                             write("BARGAIN!", on="bargain.", x=0.5, y=0.77, w=0.14, h=0.055)])))

# ------------------------------------------------------------------ Friday 11:58 PM — The clock that resets (Emma)
chapter("t4", S_CLOCK, "Friday, eleven fifty-eight p.m.", "Friday 11:58 PM — The clock that resets")
beat("c1", S_CLOCK, "Larry is buying a mattress. Sale ends in two minutes.",
     img("{larry} in striped pyjamas sitting up in bed at night, his face lit by a glowing laptop showing a big mattress, wide-eyed", motion="zoom_in",
         marks=[{"type": "led", "text": "00:02:00", "label": "Sale ends in", "x": 0.22, "y": 0.25, "w": 0.27, "on": "Sale"}]))
beat("m2", S_CLOCK, "Suspect number two. Name: the countdown clock. Aliases: sale ends in two fifty-nine fifty-nine.",
     {"type": "mugshot", "prompt": "a digital countdown timer (hand-made frame: images/m2.png)",
      "suspect": {"number": 2, "name": "The countdown clock", "alias": "'Sale ends in 02:59:59' · 'Only 3 left'", "last_seen": "Checkout, 11:58 PM", "tag": "SUSPECT"}})
beat("m2b", S_CLOCK, "Only three left.",
     reuse("c1", hand_marks=True, push={"center": [0.42, 0.45], "zoom": 1.3},
           marks=[{"type": "led", "text": "00:01:58", "label": "Sale ends in", "x": 0.22, "y": 0.25, "w": 0.27, "at": 0.0, "hand": False},
                  write("ONLY 3 LEFT!", on="three", x=0.22, y=0.40, w=0.20, h=0.06)]))
beat("e1", S_CLOCK, "In Britain, the competition watchdog took mattress-maker Emma to court. The judgment has the numbers.",
     arch("furniture_windows_shenandoah_1938.jpg", "Furniture store windows at night, Pennsylvania, 1938", motion="zoom_in", crop=[0.0, 0.0, 1.0, 0.94]), label="High Court · July 2026")
beat("e2", S_CLOCK, "Ninety-eight point two percent of Emma's sales were products shown with a struck-through was price.",
     {"type": "stat", "stat": {"value": 98.2, "decimals": 1, "suffix": "%", "label": "of sales had a struck-through 'was' price · High Court, 2026"}},
     pause_before=0.8)
beat("e3", S_CLOCK, "In 2024 it sold seven discounted mattresses for every one at full price.",
     img("a tall stack of mattresses in a warehouse, seven wearing red sale tags and the single one at the top wearing a plain white tag", motion="zoom_in",
         marks=[write("7 : 1", on="seven", x=0.86, y=0.20, w=0.12, h=0.09)]))
beat("e4", S_CLOCK, "One model, in one test period, sold just zero point zero two percent at full price. At full price, this mattress is rarer than a quiet Black Friday.",
     img("a single mattress displayed inside a glass museum case with a blank brass plaque, under a spotlight in a dark gallery", motion="static",
         hand_marks=True, marks=[write("0.02 %", on="zero", x=0.5, y=0.32, w=0.16, h=0.08)],
         closeup=closeup("At", [0.505, 0.78], 2.2, [write("RARE", on="rarer", x=0.505, y=0.815, w=0.08, h=0.045, color="ink")])),
     pause_at={"word": "zero", "sec": 0.7, "hit": "stamp"})
beat("e5", S_CLOCK, "The watchdog wanted a simple rule: for every two sold on sale, one at full price.",
     img("a brass balance scale with two small mattresses on one pan and one small mattress on the other, plain cream background (edited: images/e5.png)", motion="static", hand_marks=True,
         marks=[write("1 : 2", on="rule:", x=0.14, y=0.20, w=0.12, h=0.08),
                write("2 ON SALE", on="two", x=0.30, y=0.75, w=0.17, h=0.06),
                write("1 FULL PRICE", on="full", x=0.71, y=0.62, w=0.19, h=0.06, color="ink")]))
beat("e6", S_CLOCK, "In July 2026, the High Court found Emma had broken the law in places, but refused the ratio.",
     doc("CMA v Emma · [2026] EWHC 1995 (Ch) · 30 July 2026", "No fixed ratio",
         "\"I do not consider that I should make an enforcement order that imposes a 1:2 FVR.\"",
         "I do not consider that I should make an enforcement order that imposes a 1:2 FVR", on="refused", kicker="HIGH COURT  ·  QUOTED", seed=71, lead=1.2, post="e5"),
     stamp={"text": "1:2 refused", "on": "ratio."})
beat("e7", S_CLOCK, "A fixed rule, the judge said, risked drawing the line in the wrong place.",
     reuse("e5", hand_marks=True, marks=[write("1 : 2", at=0.0, x=0.14, y=0.20, w=0.12, h=0.08),
                                         write("2 ON SALE", at=0.0, x=0.30, y=0.75, w=0.17, h=0.06),
                                         write("1 FULL PRICE", at=0.0, x=0.71, y=0.62, w=0.19, h=0.06, color="ink"),
                                         cross(0.14, 0.20, 0.15, 0.11, "wrong")]))
beat("e8", S_CLOCK, "The clock lost anyway. In May, Emma agreed its countdown timers must end when the sale really ends, and can't be reused on a similar deal within four weeks.",
     doc("CMA v Emma · consent order · 22 May 2026", "Countdown timers",
         "Countdown timers must conclude at the same time as the sales promotion they apply to, and are not used on any substantially similar promotion within 28 days.",
         "conclude at the same time as the sales promotion", on="end", kicker="COURT ORDER  ·  PARAPHRASED", seed=81, lead=1.0, pre="m2"))
beat("e9", S_CLOCK, "The clock resets. Your decision doesn't.", kin())
beat("e10", S_CLOCK, "So what makes a was price real? America's rulebook says: a price you really offered, regularly, for a reasonably substantial time.",
     doc("FTC Guides Against Deceptive Pricing · 16 CFR 233.1 · 1964", "Former price comparisons",
         "The former price must be the actual, bona fide price at which the article was offered to the public on a regular basis for a reasonably substantial period of time.",
         "offered to the public on a regular basis", on="regularly,", kicker="US RULEBOOK  ·  QUOTED", seed=91, lead=1.6, post="o1"))
beat("e11", S_CLOCK, "Its own example is a pen tagged ten dollars for a few days, just so seven-fifty can look like a bargain.",
     img("a 1950s fountain pen lying on a velvet display stand with a large blank cream paper price tag, plain background", motion="static", hand_marks=True,
         marks=[write("$10", on="ten", x=0.21, y=0.62, w=0.08, h=0.07, angle=-14, **TAG_W)],
         closeup=closeup("just", [0.26, 0.62], 2.0, [write("$10", at=0.0, x=0.21, y=0.62, w=0.08, h=0.07, angle=-14, color="ink"),
                                                     cross(0.21, 0.62, 0.09, 0.08, "seven-fifty"),
                                                     write("$7.50!", on="seven-fifty", x=0.215, y=0.72, w=0.10, h=0.07, angle=-14)])))
beat("e12", S_CLOCK, "California says: within the last three months.",
     img("a 1950s pull-down classroom wall map showing North America on the left and Europe on the right, soft colours, no labels", motion="static",
         hand_marks=True, push={"center": [0.30, 0.58], "zoom": 1.8}, marks=[write("3 MONTHS", on="three", x=0.30, y=0.56, w=0.12, h=0.05)]),
     label="California · B&P Code §17501")
beat("e12b", S_CLOCK, "And in the EU, any was price must be the lowest of the last thirty days.",
     reuse("e12", hand_marks=True, push={"center": [0.66, 0.52], "zoom": 1.8}, marks=[write("30 DAYS", on="thirty", x=0.62, y=0.40, w=0.10, h=0.05)]),
     label="EU rule · 2022")

# ------------------------------------------------------------------ Saturday 10:00 AM — Three checks
chapter("t5", S_CHECK, "Saturday, ten a.m.", "Saturday 10:00 AM — Three checks")
beat("x1", S_CHECK, "Three checks before you pay. One. Was it ever that price here? Look for a date.",
     img("{larry} bending close to a shop shelf, inspecting a price tag through a big magnifying glass, plain cream background", motion="zoom_in"),
     music="ub_secret_report",
     inserts=[{"file": "ceiling_price_tag_shirt_1942.jpg", "kind": "photo", "from": "left", "x": 0.18, "y": 0.34, "w": 0.24, "on": "date.",
               "crop": [0.04, 0.12, 0.96, 0.92], "caption": "Stamping the facts on a price tag, 1942"}])
beat("x2", S_CHECK, "If the tag can't give you one, treat the was as decoration.",
     img("a cream paper price tag hanging as an ornament on a small decorated Christmas tree, plain cream background", motion="zoom_in"), music="ub_secret_report")
beat("x3", S_CHECK, "Two. Check the price history. Free trackers show what a product really cost, week by week:",
     {"type": "chart", "chart": {"kind": "line", "title": "Price history (illustration)", "labels": ["Jan", "Mar", "May", "Jul", "Sep", "Nov"],
                                 "values": [399, 399, 405, 399, 399, 489], "unit": "$", "highlight": 5, "note": "the 'was' price never appears"}},
     music="ub_secret_report", label="Illustration")
beat("x4", S_CHECK, "Keepa or camelcamelcamel for Amazon in the US, PriceSpy or idealo in Britain and Europe.",
     img("an open 1950s wooden index-card box with four blank white cards standing up, plain cream background", motion="static",
         marks=[write("Keepa", on="Keepa", x=0.53, y=0.36, w=0.12, h=0.05, angle=-6, color="ink", fnt="typewriter"),
                write("camelcamelcamel", on="camelcamelcamel", x=0.53, y=0.44, w=0.22, h=0.05, angle=-6, color="ink", fnt="typewriter"),
                write("PriceSpy", on="PriceSpy", x=0.54, y=0.54, w=0.14, h=0.05, angle=-6, color="ink", fnt="typewriter"),
                write("idealo", on="idealo", x=0.54, y=0.62, w=0.11, h=0.05, angle=-6, color="ink", fnt="typewriter"),
                write("US · Amazon", on="Keepa", x=0.17, y=0.40, w=0.15, h=0.05, color="red", fnt="body"),
                write("UK · EU", on="PriceSpy", x=0.17, y=0.58, w=0.11, h=0.05, color="red", fnt="body")]),
     music="ub_secret_report", say="Keepa or camel camel camel for Amazon in the US, PriceSpy or idealo in Britain and Europe.")
beat("x5", S_CHECK, "A was price that never shows up on the chart is a suspect.", reuse("m1", marks=WAS_DASH), music="ub_secret_report")
beat("x6", S_CHECK, "Three. Find the floor. In the EU, the was price must be the thirty-day low. Everywhere else, search the exact model number.",
     img("the shiny cream stand mixer seen from the side, a small blank metal model plate on its base, plain background", motion="static", hand_marks=True,
         marks=[write("30-DAY LOW?", on="thirty-day", x=0.20, y=0.10, w=0.20, h=0.07)],
         closeup=closeup("Everywhere", [0.60, 0.84], 2.2, [circle(0.48, 0.89, 0.18, 0.07, "model"), write("MODEL No.", on="number.", x=0.70, y=0.80, w=0.12, h=0.045)])),
     music="ub_secret_report")
beat("x7", S_CHECK, "Larry's mixer: ninety dollars cheaper, one click away.", reuse("k5", motion="zoom_in"), music="ub_secret_report")
beat("x8", S_CHECK, "Forget the percentage. Compare the price you'd pay with the price you could pay.",
     reuse("x1", hand_marks=True, marks=[write("COULD PAY?", on="could", x=0.20, y=0.22, w=0.20, h=0.07)]), music="ub_secret_report")
beat("x9", S_CHECK, "The sentence: a date on every tag, and a second look from you.",
     reuse("x1", hand_marks=True, push={"center": [0.72, 0.60], "zoom": 1.8}, marks=[write("DATE?", on="date", x=0.76, y=0.70, w=0.08, h=0.05)]),
     music="ub_secret_report")
beat("x10", S_CHECK, "Larry closed his tab without buying the mixer. Then he checked the price again. Twice.",
     reuse("x1", push={"center": [0.50, 0.34], "zoom": 1.7}), music="ub_secret_report",
     bubble={"text": "Twice.", "x": 0.70, "y": 0.22, "tail": "left", "on": "Twice."})

# ------------------------------------------------------------------ Case closed + end screen (Ep.4 teaser: drip pricing)
ES = {"number": "003", "title": "The fake sale", "stamp": "Case closed",
      "verdict": ["Guilty: the WAS price.", "Accomplice: the clock."],
      "next": {"number": "004", "title": "Drip pricing", "tagline": "The $30 ticket that costs $48.", "image_file": "next_ticket.png",
               "copies": 1, "fees": ["$30", "+ $8 fee", "+ $6 fee", "+ $4 fee", "= $48"], "label": "Illustration"},
      "times": {"swap": 5.8, "draw": 6.4, "ddur": 3.4, "fees": 10.0, "fgap": 0.8, "fdur": 0.55, "tagline": 14.4,
                "zone": 14.7, "sketch": 15.2, "skdur": 1.0, "sub": 16.2, "click": 17.3, "push": 18.0}}
beat("z1", S_CLOSE, "Case closed. The verdict. Guilty: the was price. Accomplice: the clock.", {"type": "endscreen", "endscreen": ES},
     block_start=True, sting="ub_sting_brass", sting_at=0.1)
beat("z4", S_CLOSE, "Next case: the thirty-dollar ticket that costs forty-eight. Fee by fee.", {"type": "continue"}, block_at=6.0)
beat("z5", S_CLOSE, "Subscribe, so the next case file finds you.", {"type": "continue"}, block_at=16.0, block_end=21.0)

ep = {
    "slug": "0004-fake-sale",
    "title": "The Sale That Never Was",
    "description": "Was £49.99, now £18.99 — except it never cost £49.99. Case file #003 follows Larry (fictional) through Black Friday week: the store that stopped lying and lost $985 million, the mixer that was always on sale, the mattress-maker taken to court over its 'was' prices and countdown clocks — and three checks that catch a fake sale.",
    "tags": ["fake sales", "reference pricing", "was price", "black friday deals", "anchoring", "jcpenney", "consumer rights",
             "psychology of money", "behavioral economics"],
    "characters": {
        "larry": "a cheerful middle-aged man with a round face and a thin moustache, wearing a loud yellow checked sports jacket and a red fedora",
    },
    "music": {"_default": "ub_private_detective", "_shorts": "ub_wells_street",
              S_OPEN: "ub_private_detective", S_PEN: "ub_tunnel_vision", S_KOHL: "ub_wells_street", S_BRAIN: "ub_mechanisms_of_action",
              S_DEF: "ub_usual_suspects", S_CLOCK: "ub_clock_is_ticking", S_CHECK: "ub_secret_report", S_CLOSE: "ub_jazz_rumble"},
    "sources": [
        "Which? (26 Nov 2024). Nine in 10 Black Friday deals cheaper or same price at other times of the year (227 deals, 8 retailers; Boots hair dryer £49.99/£18.99).",
        "J.C. Penney Form 8-K, 27 Feb 2013 (fiscal 2012: net loss $985M; total sales −24.8%; comparable sales −25.2%).",
        "Fortune (25 Jan 2012): 590 promotional events in 2011; Ron Johnson: \"People are disgusted with the lack of integrity on pricing.\"",
        "Los Angeles Times via CS Monitor (26 Jan 2012): 0.2% of revenue at full price; almost 73% at 50%+ off.",
        "TIME (2013): $5 T-shirt re-tagged $6 before markdowns returned.",
        "Consumer Reports (22 Jun 2013), 'Fake sales can cost you': KitchenAid mixer check (2012); Edgar Dworsky's 2003 Kohl's tracking (20 items, 103 days, 86%).",
        "Checkbook (2018), via 6abc: 19 retailers; sale price usually the routine price.",
        "Hinojos v. Kohl's Corp., 9th Cir. (21 May 2013).",
        "City of Los Angeles complaints (8 Dec 2016); Daily Journal (8 Oct 2021): case against Kohl's and Macy's dismissed.",
        "Tversky & Kahneman (1974), Judgment under Uncertainty, Science. Ariely, Loewenstein & Prelec (2003), QJE. Fudenberg, Levine & Maniadis (2012), AEJ: Micro.",
        "Ngwe (2018), Fake Discounts Drive Real Revenues in Retail — HBS Working Knowledge summary.",
        "FTC Bureau of Economics (1992), An Analysis of Department Store Reference Pricing in Metropolitan Washington, D.C.",
        "CMA v Emma Matratzen GmbH & Ors [2026] EWHC 1995 (Ch), 30 July 2026; consent order 22 May 2026.",
        "FTC Guides Against Deceptive Pricing, 16 CFR 233.1 (1964). California Business & Professions Code §17501. EU Directive 2019/2161, Art. 6a.",
        "Larry is a fictional character. Scenes marked 'Illustration' are illustrations.",
    ],
    "beats": B,
    "shorts": [],
}
OUT.write_text(json.dumps(ep, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(len(B), "beats,", sum(len(b["text"].split()) for b in B), "words")
