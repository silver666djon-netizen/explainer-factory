"""Episode 0003 — Same Basket, Different Price. Writes episodes/0003-same-basket/script.json"""
import json
from pathlib import Path

OUT = Path("/home/claude/explainer-factory/episodes/0003-same-basket/script.json")

B = []


def beat(id, section, text, visual, **kw):
    b = {"id": id, "section": section, "text": text, "visual": visual}
    b.update(kw)
    B.append(b)


def img(prompt=None, prompts=None, motion=None, **kw):
    v = {"type": "image"}
    if prompts:
        v["prompts"] = prompts
    else:
        v["prompt"] = prompt
    if motion:
        v["motion"] = motion
    v.update(kw)
    return v


def reuse(b, motion=None, index=0, **kw):
    v = {"type": "reuse", "beat": b, "index": index}
    if motion:
        v["motion"] = motion
    v.update(kw)
    return v


def arch(file, look="print", credit="", motion="zoom_in", **kw):
    v = {"type": "archive", "file": file, "look": look, "credit": credit, "motion": motion}
    v.update(kw)
    return v


LOC = "Library of Congress, Prints & Photographs Division (no known restrictions)"
PRELINGER = "Prelinger Archives / Internet Archive (public domain)"


def kin(bg="paper"):
    return {"type": "kinetic", "kinetic": {"bg": bg}}


def title(t):
    return {"type": "title", "text": t}


def doc(source, headline, body, highlight=None, at=1.6, seed=1):
    d = {"source": source, "headline": headline, "body": body, "seed": seed, "at": at if highlight else 999}
    if highlight:
        d["highlight"] = highlight
    return {"type": "doc", "doc": d}


# ------------------------------------------------------------------ cold open
S = "The case"
beat("c01", S, "In 2016, Uber's own head of economic research said something on a podcast that he may have come to regret.",
     img(prompts=["a 1950s radio studio microphone on a desk under a glowing red on-air lamp, warm studio light",
                  "a cream retro-styled smartphone standing upright in the centre, its screen filled by a large horizontal battery outline with only a thin red sliver of charge at the left end, nothing else in the picture, plain dark green background"], motion="zoom_in"),
     say="In twenty sixteen, Uber's own head of economic research said something on a podcast that he may have come to regret.")
beat("c02", S, "People whose phone is about to die, he said, are more likely to accept a higher surge price.",
     reuse("c01", index=1, motion="static", marks=[{"type": "circle", "x": 0.5, "y": 0.5, "w": 0.22, "h": 0.3, "text": "3%", "text_x": 0.5, "text_y": 0.66, "on": "die"}]),
     on_screen="Low battery = higher price?")
beat("c03", S, "So, before we go any further, charge your phone.",
     img("a cream retro-styled smartphone lying on a table and an oversized ordinary household two-prong wall plug, clearly bigger than the phone, being pushed against its tiny charging port — a comically wrong fit, the phone screen showing a red nearly-empty battery icon, close up", motion="zoom_in"), sfx="tick")
beat("c04", S, "*Trust* me.", kin("ink"))
beat("c05", S, "Because tonight, your phone is at three percent. You need a ride home.",
     img("{larry} standing alone, looking at the faint glow of his phone with a hopeful half-smile, mid shot, plain cream background, no scenery", motion="static",
         draw={"on": "tonight", "dur": 3.4, "box": [0.15, 0.0, 0.85, 1.0]}))
beat("c06", S, "And somewhere, an algorithm might know exactly what that's worth.",
     img("a frosted glass office door with a brass handle; behind the glass, the soft grey blurred outline of a round-headed retro robot with a small bow tie, lit from behind by warm amber light, no face visible, film-noir mood", motion="zoom_in"))
beat("c07", S, "The battery story? A rumour. What we found next isn't.",
     reuse("c05", motion="static", marks=[{"type": "cross", "x": 0.5, "y": 0.45, "w": 0.3, "h": 0.36, "on": "rumour"}]), punch=["isn't."])
beat("cf1", S, "Case file number two. Same basket, different price.", hold=1.0,
     visual={"type": "casefile", "casefile": {"mode": "open", "number": "002", "title": "Same basket",
             "inside": ["SUBJECT: Larry (fictional)", "WITNESS: Linda, his sister", "SUSPECTS: 2", "STATUS: open"]}})

# ------------------------------------------------------------------ 11:47 PM
S = "11:47 PM: 3% battery"
beat("t01", S, "Eleven forty-seven p.m.", title("11:47 PM — 3% battery"))
beat("b10", S, "Larry is back from Vegas. Broke, tired, and down to three percent.",
     img("{larry} slumped on a bus-stop bench at night holding his phone, an empty wallet on his knee", motion="zoom_in"),
     bubble={"text": "3%… and falling.", "x": 0.83, "y": 0.2, "tail": "left", "at": 1.8})
beat("b11", S, "He opens the ride app. The fare looks high. Is it the rain? The hour? Or the battery?",
     img("a retro-styled taxi ordering screen glowing on a phone, a yellow 1950s taxi cab waiting in the rain behind it", motion="zoom_in"),
     punch=["battery?"])
beat("m12", S, "Suspect number one: the battery rumour. Alias: the three-percent tax. Last seen: every group chat since 2016.",
     {"type": "mugshot", "prompt": "a single cream retro-styled smartphone standing upright, its battery icon nearly empty and glowing red, plain light grey background, studio lighting",
      "suspect": {"number": 1, "name": "The battery rumour", "alias": "The 3% tax", "last_seen": "Every group chat since 2016", "tag": "RUMOUR"}},
     say="Suspect number one: the battery rumour. Alias: the three-percent tax. Last seen: every group chat since twenty sixteen.")
beat("d13", S, "Here's what was actually said. Uber had noticed that riders with a nearly dead phone seemed more willing to accept surge pricing.",
     doc("Summary · NPR, Hidden Brain · 2016", "Uber's economist on dying phones",
         "Uber's head of economic research said riders whose phones were nearly out of battery seemed more willing to accept surge pricing. He also said Uber does not use battery level to set prices.",
         highlight="more willing to accept surge pricing", at=4.0, seed=31))
beat("d14", S, "But he also said Uber does not use your battery to set the price. And nobody has shown that it does.",
     reuse("c01", index=1, motion="zoom_out"))
beat("d14b", S, "Surge pricing itself is real, of course. When lots of people want rides and few drivers are around, the price goes up for everyone in the area. That's demand. Not your battery.",
     img("a 1950s city street at night in the rain with many people waiting at the kerb and only one yellow taxi in sight", motion="pan_left"))
beat("b15", S, "Verdict: *not* *proven.*", kin("red"), sfx="thud")
beat("b16", S, "But notice what the rumour got right. Your phone knows things about you. Where you are. What you're doing. How badly you need it.",
     img("a cream retro-styled smartphone on a table with dotted lines radiating from it to tiny icons of a map pin, a clock and a shopping basket", motion="zoom_out", hand_marks=True,
         marks=[{"type": "circle", "x": 0.31, "y": 0.22, "w": 0.1, "h": 0.2, "on": "Where"},
                {"type": "circle", "x": 0.49, "y": 0.13, "w": 0.09, "h": 0.19, "on": "doing."},
                {"type": "circle", "x": 0.67, "y": 0.23, "w": 0.1, "h": 0.2, "on": "badly"}]))
beat("b17", S, "And some apps really have changed the price because of one of those things. Exhibit A.",
     reuse("b16", motion="static", marks=[{"type": "circle", "x": 0.31, "y": 0.22, "w": 0.12, "h": 0.24, "on": "Exhibit"}]), sfx="riser")

# ------------------------------------------------------------------ 8:02 AM
S = "8:02 AM: The parking lot"
beat("t02", S, "Eight oh two a.m.", title("8:02 AM — The parking lot"))
beat("a20", S, "February 2019. A TV news team in Minneapolis, KARE 11, tried something simple with the Target app.",
     img("a 1950s television news van with a tall antenna parked outside a big modern department store on a winter morning", motion="zoom_in", newsreel="Reconstruction"),
     say="February twenty nineteen. A TV news team in Minneapolis, Kare Eleven, tried something simple with the Target app.")
beat("a21", S, "At home, a 55-inch Samsung TV showed up in the app at 499 dollars 99.",
     img("a sleek modern flat television on a stand in a cosy 1950s-style living room, a phone on the sofa", motion="zoom_in"),
     on_screen="$499.99", say="At home, a fifty-five inch Samsung TV showed up in the app at four ninety-nine ninety-nine.")
beat("a22", S, "Then the reporter drove to the store. In the parking lot, the same TV, in the same app, said 599 dollars 99.",
     img("a top-down view of a big store parking lot with painted bays, one small red car pulling into a space, flat graphic style", motion="static"),
     counter={"from": 499.99, "to": 599.99, "prefix": "$", "decimals": 2, "label": "same TV · same app", "on": "said", "dur": 1.4},
     say="Then the reporter drove to the store. In the parking lot, the same TV, in the same app, said five ninety-nine ninety-nine.")
beat("a23", S, "The app had quietly switched to the in-store price the moment the phone arrived near the store.",
     img("a cream retro-styled smartphone with a red map pin hovering above its screen, standing on a car dashboard", motion="static",
         marks=[{"type": "circle", "x": 0.47, "y": 0.2, "w": 0.15, "h": 0.3, "on": "quietly"}]))
beat("a24", S, "A hundred dollars, for driving to the store.", kin("paper"), punch=["hundred"])
beat("a25", S, "After the report, Target said changes were coming to the app. But the lesson stuck: the price on your screen can depend on where your screen is.",
     reuse("b16", motion="zoom_out", marks=[{"type": "circle", "x": 0.31, "y": 0.22, "w": 0.12, "h": 0.24, "on": "where"}]))
beat("a26", S, "Exhibit A. *Confirmed.*", kin("green"), sfx="thud")
beat("k1", S, "If you enjoy catching prices red-handed, subscribe. The Inspector has more files.",
     reuse("c05", motion="zoom_in"), cta={"on": "subscribe", "click_on": "Inspector"})

# ------------------------------------------------------------------ 10:15 AM
S = "10:15 AM: Same basket"
beat("t03", S, "Ten fifteen a.m.", title("10:15 AM — Same basket"))
beat("s30", S, "Larry orders his groceries on a delivery app. Across town, his sister Linda orders the exact same basket.",
     img(prompts=["{larry} at a small kitchen table tapping on his phone, a coffee cup beside him, mid shot",
                  "{linda} at her own kitchen table tapping on her phone, a neat shopping list beside her, mid shot"], motion="zoom_in"))
beat("s31", S, "Same store. Same items. Same minute. Then they compare receipts.",
     img("two long paper shop receipts lying side by side on a kitchen table, their totals hidden under a pencil", motion="zoom_in"),
     bubble={"text": "Why is YOURS cheaper?", "x": 0.75, "y": 0.22, "tail": "left", "at": 1.6})
beat("s32", S, "That's not a made-up scene. In 2025, Consumer Reports and the Groundwork Collaborative had hundreds of volunteers buy the same basket, at the same store, at the same time.",
     doc("Summary · Consumer Reports & Groundwork Collaborative · Dec 2025", "Same cart, different price",
         "437 volunteers shopped identical baskets through Instacart at the same stores at the same moment. About three-quarters of the products checked were offered at different prices, by up to 23% per item.",
         highlight="offered at different prices", at=6.5, seed=41),
     say="That's not a made-up scene. In twenty twenty-five, Consumer Reports and the Groundwork Collaborative had hundreds of volunteers buy the same basket, at the same store, at the same time.")
beat("s33", S, "At one Safeway in Seattle, the cheapest basket came to 114 dollars 34. The most expensive: 123 dollars 93.",
     {"type": "chart", "chart": {"kind": "bar", "title": "Same Safeway basket, Seattle", "labels": ["Cheapest", "Most expensive"],
                                 "values": [114.34, 123.93], "unit": "$", "decimals": 2, "highlight": 1}},
     say="At one Safeway in Seattle, the cheapest basket came to one hundred and fourteen dollars thirty-four. The most expensive: one hundred and twenty-three ninety-three.")
beat("s33b", S, "Nearly ten dollars of difference. On one ordinary grocery run. For nothing but luck.",
     reuse("s31", motion="zoom_in"), punch=["luck."])
beat("s34", S, "Only eight percent of shoppers got the lowest total.",
     {"type": "stat", "stat": {"value": 8, "suffix": "%", "label": "got the cheapest basket", "decimals": 0}})
beat("s35", S, "Quick game. Pause the video. Five price tags, one product. Which one is real?",
     img("five blank paper price tags with red borders hanging on strings in a row in front of a single carton of eggs on a shop shelf", motion="static"),
     sfx="pop", bubble={"text": "Pause!", "x": 0.2, "y": 0.2, "tail": "right", "at": 0.6})
beat("s36", S, "Trick question. In these tests, some items carried up to five different prices at the very same moment.",
     reuse("s35", motion="zoom_out", marks=[{"type": "underline", "x": 0.48, "y": 0.955, "w": 0.86, "text": "all of them", "text_y": 0.62, "on": "five"}]))
beat("s37", S, "Now look at these crackers. Shoppers were shown three different 'original' prices: five ninety-three, five ninety-nine, and six sixty-nine.",
     img("a box of premium saltine crackers on a cream shop shelf with a red sale ribbon across it, the box front plain and unlettered", motion="zoom_in"),
     on_screen="Was $5.93 · $5.99 · $6.69")
beat("s38", S, "And every single one of them paid the same sale price: three ninety-nine.",
     reuse("s37", motion="static", marks=[{"type": "circle", "x": 0.48, "y": 0.5, "w": 0.44, "h": 0.6, "text": "everyone: $3.99", "text_y": 0.74, "on": "same"}]))
beat("s39", S, "Same price. Different *feeling.*", kin("paper"))
beat("s39b", S, "The bigger the fake 'was', the better the deal felt. Economists call it anchoring.",
     reuse("s37", motion="static"), punch=["anchoring."])
beat("s39c", S, "That trick is older than the phone. Montana, 1887: these shoes sell for double the price. One week only.",
     arch("np_lottery_1887.jpg", look="clipping", credit="The Daily Yellowstone Journal, 15 Oct 1887 — Chronicling America, " + LOC,
          crop=[0.045, 0.818, 0.232, 0.975], caption="The Daily Yellowstone Journal, Miles City, 15 October 1887", motion="static", hand_marks=True,
          marks=[{"type": "underline", "x": 0.52, "y": 0.455, "w": 0.27, "on": "double"}]),
     say="That trick is older than the phone. Montana, eighteen eighty-seven: these shoes sell for double the price. One week only.")
beat("s3a", S, "Instacart confirmed the findings reflected its own price tests, running at ten retailers. It called the differences negligible.",
     img("a tidy corporate press statement on letterhead lying on a polished desk beside a fountain pen", motion="zoom_in",
         marks=[{"type": "underline", "x": 0.5, "y": 0.55, "w": 0.4, "text": "negligible?", "text_y": 0.7, "on": "negligible"}]))
beat("s3b", S, "Negligible, by Consumer Reports' estimate, could add up to about twelve hundred dollars a year for a family of four.",
     reuse("s30", index=1, motion="zoom_in"),
     counter={"from": 0, "to": 1200, "prefix": "$", "decimals": 0, "label": "a year · family of four (CR estimate)", "on": "twelve", "dur": 1.6})
beat("s3c", S, "Within two weeks of the report, Instacart ended the experiments. But the method is not Instacart's alone. And the tests were only the visible part.",
     {"type": "clip", "file": "clip_supermarket_1950s.mp4", "in": 96.0, "out": 112.0, "newsreel": "Supermarket film, 1960s",
      "credit": "\"The Supermarket\" (Ezra Baker Films) — " + PRELINGER})

# ------------------------------------------------------------------ 1:30 PM
S = "1:30 PM: The machine"
beat("t04", S, "One thirty p.m.", title("1:30 PM — The machine"))
beat("h40", S, "To see why this matters, rewind a hundred and fifty years. For most of history, prices were personal. You walked into a shop, and you haggled.",
     arch("general_store_1936.jpg", credit="Walker Evans / Farm Security Administration, " + LOC, caption="General store, Moundville, Alabama, 1936 — Walker Evans", motion="zoom_in"))
beat("h41a", S, "Then shops like Wanamaker's in Philadelphia championed a radical idea.",
     arch("wanamaker_phila_1896.jpg", credit="Alfred S. Campbell stereograph, 1896, " + LOC, crop=[0.06, 0.1, 0.49, 0.9], caption="Wanamaker's, Philadelphia, 1896", motion="zoom_in"))
beat("h41", S, "One price, for everyone, written on a tag.",
     img("a single old-fashioned paper price tag on a string hanging from a folded shirt in a grand 1870s department store", motion="zoom_in",
         ad={"badge": "NEW!", "badge_x": 0.82, "badge_y": 0.2, "slogan": "One price. For everyone. Imagine that.", "slogan_y": 0.86}))
beat("h42", S, "The price tag was a promise. The rich man and the poor widow paid the same.",
     reuse("h41", motion="static", marks=[{"type": "circle", "x": 0.6, "y": 0.6, "w": 0.18, "h": 0.3, "text": "one price", "text_x": 0.8, "text_y": 0.5, "on": "same"}]))
beat("h43", S, "Personalised pricing quietly brings the haggling back.", reuse("h40", motion="zoom_out"))
beat("h43b", S, "Except only *one* side knows the haggling is happening.", kin("paper"))
beat("p40", S, "So who sets these prices now? Meet the machine. We'll call him Mister Price.",
     img("{price} standing proudly, arms open in welcome with white-gloved cartoon hands, full figure, plain cream background, no scenery", motion="static",
         draw={"on": "Meet", "dur": 3.4, "box": [0.1, 0.0, 0.9, 1.0]}))
beat("p41", S, "Good afternoon! Shopping on a phone, I see. Sorting by price, low to high. Lovely.",
     img("{price} leaning over a shop counter with a big friendly grin, white-gloved cartoon hands resting on the counter, comic panel close-up", style="comic", motion="static"), voice="price")
beat("p42", S, "In January 2025, staff at the US Federal Trade Commission published early findings from a study of companies that help sellers personalise prices.",
     doc("Summary · US Federal Trade Commission · Jan 2025", "Surveillance pricing: initial findings",
         "Intermediary firms said they could use details such as location, device, browsing, mouse movements and items left in a cart to tailor prices for individual shoppers. The staff called the findings preliminary.",
         highlight="tailor prices for individual shoppers", at=6.0, seed=51),
     say="In January twenty twenty-five, staff at the US Federal Trade Commission published early findings from a study of companies that help sellers personalise prices.")
beat("p42b", S, "Here's the document itself. Page six.",
     arch("ftc_surveillance_pricing_2025.pdf", look="clipping", page=6, crop=[0.52, 0.07, 0.98, 0.31],
          credit="US Federal Trade Commission staff, Surveillance Pricing 6(b) study research summaries, Jan 2025 (US government work, public domain)",
          caption="FTC staff report, January 2025, p. 6", motion="zoom_in", hand_marks=True,
          marks=[{"type": "underline", "x": 0.39, "y": 0.245, "w": 0.26, "on": "six."}]))
beat("p43", S, "The ingredients on the table: where you are, what device you use, what you browse, even how you move your mouse, and what you leave in your cart.",
     img("{price} examining a shopper's silhouette with a big brass magnifying glass held in one white-gloved cartoon hand, small floating labels around it", motion="static"),
     on_screen="Location · Device · Cart")
beat("p44", S, "One illustration in the report: a seller spots a new parent from baby purchases and recent searches, and offers a fast-delivery baby thermometer at a premium.",
     img("a white baby thermometer in a gift box with a red price tag growing larger beside it, soft nursery colours", motion="zoom_in"),
     on_screen="FTC example")
beat("p45", S, "The FTC staff stressed it was preliminary, and that no law had been found broken. But the toolbox exists.",
     img("an open wooden toolbox on a workbench, filled with neat price tags, a magnifier and a little map pin", motion="zoom_in"))
beat("p46", S, "Nothing personal, of course. Just data.", reuse("p40", motion="zoom_in"), voice="price")

# ------------------------------------------------------------------ defence
S = "In defence of the accused"
beat("t05", S, "In defence of the accused.", title("In defence of the accused"))
beat("d50", S, "Prices change all the time, sir. That's just shopping.", reuse("p40", motion="static"), voice="price")
beat("d51", S, "To be fair, he has a point. Shops have always tested prices, and a personalised offer can also mean a discount for the careful shopper.",
     img("brass balance scales with a small red discount coupon on one pan and a price tag on the other, evenly balanced", motion="zoom_in"))
beat("d51b", S, "Airlines have charged different fares for the same seat for decades, and most of us accept it, because at least we know the game.",
     img("a 1950s airliner parked on a sunny runway with passengers climbing a boarding stair", motion="pan_right"))
beat("d52", S, "And Instacart said shoppers were put into test groups at random, by product and location. Not by who they are.",
     reuse("s3a", motion="zoom_out"))
beat("d53", S, "Alibi: partial.",
     {"type": "mugshot", "prompt": "a cream retro-styled shopping basket with a few groceries, plain light grey background, studio lighting",
      "suspect": {"number": 2, "name": "The price experiment", "alias": "A/B test", "last_seen": "Your delivery app", "tag": "ALIBI: PARTIAL"}})

# ------------------------------------------------------------------ twist
S = "The twist"
beat("t06", S, "Which brings us to the twist.", title("The twist"))
beat("w60", S, "Larry thought the machine had picked on him. That it knew about the battery, the broke weekend, the bad luck.",
     img("{larry} at his kitchen table frowning at his phone, a red marker question mark drawn on the wall behind him", motion="zoom_in"))
beat("w61", S, "It didn't need to.", kin("ink"))
beat("w61b", S, "A test doesn't need to know who you are. It just needs enough people. Group A sees one price. Group B sees another. And the machine learns which one people will put up with.",
     img("two neat queues of little white cartoon mice with shopping carts, one queue under a green sign shape and one under a red sign shape, no lettering", motion="static", hand_marks=True,
         marks=[{"type": "circle", "x": 0.27, "y": 0.7, "w": 0.4, "h": 0.5, "text": "A", "text_x": 0.27, "text_y": 0.35, "on": "Group"},
                {"type": "circle", "x": 0.74, "y": 0.7, "w": 0.4, "h": 0.5, "text": "B", "text_x": 0.74, "text_y": 0.35, "on": "B"}]))
beat("w62", S, "It tested everyone. At random. Like mice running through a supermarket.",
     img("dozens of little white cartoon mice each pushing a tiny shopping cart down a long supermarket aisle", motion="zoom_in"), sfx="whoosh",
     bubble={"text": "Is this the cheese aisle?", "x": 0.74, "y": 0.22, "tail": "left", "at": 1.6})
beat("w63", S, "Instacart's own marketing material put it plainly: shoppers are not aware that they're in an experiment.",
     doc("Instacart marketing & investor material · as reported by Consumer Reports", "“Shoppers are not aware”",
         "The company's materials describing its pricing tools said that shoppers are not aware that they're in an experiment.",
         highlight="shoppers are not aware that they're in an experiment", at=3.0, seed=61))
beat("w64", S, "You weren't *targeted.* You were *sampled.*", kin("red"), sfx="thud")

# ------------------------------------------------------------------ case closed
S = "Case closed"
beat("v70", S, "So, the verdict.",
     {"type": "casefile", "casefile": {"mode": "closed", "number": "002", "title": "Same basket", "stamp": "Case closed",
                                        "lines": ["Battery rumour: not proven", "Price tests: confirmed"], "stamp_at": 0.4}})
beat("v71", S, "And the ten-second defence.", reuse("c03", motion="zoom_in"))
beat("v72", S, "Before you pay, check the price somewhere else: another phone, logged out, or the store's own website.",
     img(prompts=["two cream retro-styled smartphones side by side on a table showing the same plain shopping screen",
                  "a laptop on a kitchen table next to a phone, both showing a plain shop page"], motion="zoom_in"))
beat("v73", S, "Switch off location for shopping apps when you don't need it.",
     reuse("a23", motion="static", marks=[{"type": "cross", "x": 0.47, "y": 0.2, "w": 0.13, "h": 0.26, "on": "off"}]))
beat("v74b", S, "None of this means every price is a trick. It means a price on a screen is no longer a fact. It's a guess. And you're allowed to check it.",
     reuse("h41", motion="zoom_out", marks=[{"type": "circle", "x": 0.6, "y": 0.6, "w": 0.18, "h": 0.3, "on": "guess."}]))
beat("v75", S, "Larry's phone is now at a hundred percent. He's still checking the price.",
     img("{larry} at home holding his fully charged phone at arm's length and squinting at it suspiciously, mid shot", motion="zoom_in"),
     bubble={"text": "Twice.", "x": 0.75, "y": 0.22, "tail": "left", "at": 2.4})
beat("v76", S, "And that 'was' price on the crackers? It deserves a case file of its own.",
     reuse("s37", motion="static", hand_marks=True, marks=[{"type": "circle", "x": 0.48, "y": 0.5, "w": 0.44, "h": 0.6, "text": "next case", "text_y": 0.74, "on": "own"}]))
beat("k2", S, "Larry's learning. You don't have to learn the hard way. Your next case is right here on screen.",
     reuse("v75", motion="static"), cta={"on": "next", "click_on": "screen"})
beat("k3", S, "Case file zero zero three.", hold=14,
     visual={"type": "casefile", "casefile": {"mode": "open", "number": "003", "title": "The fake sale",
             "inside": ["NEXT CASE: the sale that never was", "SUSPECT: the 'was' price", "STATUS: open"]}},
     cta={"at": 0.2, "click_at": 1.4, "hold": 14})

for b in B:
    b.pop("visual_override", None)

# ------------------------------------------------------------------ shorts
def r(beat_id, text, motion="zoom_in", index=0, **kw):
    v = {"type": "reuse", "beat": beat_id, "index": index, "motion": motion}
    for k in ("draw", "marks", "hand_marks"):  # visual-level keys
        if k in kw:
            v[k] = kw.pop(k)
    d = {"text": text, "visual": v}
    d.update(kw)
    return d


shorts = [
    {"id": "s1", "hook": 'Low battery = higher price?', "title": "Does your ride cost more on low battery? #shorts", "beats": [
        r("c05", "Does your ride cost more when your battery is low?", motion="static", punch=["low?"], draw={"at": 0.1, "dur": 2.8, "box": [0.15, 0.0, 0.85, 1.0]}),
        r("c01", "In 2016, Uber's own economist said riders with a dying phone were more willing to accept surge pricing.", index=1,
          say="In twenty sixteen, Uber's own economist said riders with a dying phone were more willing to accept surge pricing."),
        r("c01", "But he also said Uber doesn't use battery to set prices. Nobody has shown it does.", index=0),
        {"text": "Verdict: *not* *proven.*", "visual": kin("red"), "sfx": "thud"},
        r("b16", "But your phone still knows where you are, and some apps have changed prices because of that."),
        r("a22", "That's the real case. And it starts with one question people keep asking:", motion="static"),
    ]},
    {"id": "s2", "hook": 'Same TV. +$100.', "title": "The TV that got $100 dearer in the parking lot #shorts", "beats": [
        r("a21", "This TV cost $499.99 in the app.", say="This TV cost four ninety-nine ninety-nine in the app."),
        r("a22", "The reporter drove to the store. In the parking lot, same TV, same app: $599.99.", motion="static",
          counter={"from": 499.99, "to": 599.99, "prefix": "$", "decimals": 2, "label": "same TV · same app", "on": "same", "dur": 1.2},
          say="The reporter drove to the store. In the parking lot, same TV, same app: five ninety-nine ninety-nine."),
        r("a23", "The Target app had switched to the in-store price as the phone got close. KARE 11 found it in 2019.", motion="static", hand_marks=True,
          marks=[{"type": "circle", "x": 0.47, "y": 0.2, "w": 0.15, "h": 0.3, "on": "close"}],
          say="The Target app had switched to the in-store price as the phone got close. Kare Eleven found it in twenty nineteen."),
        {"text": "A hundred dollars, for driving closer.", "visual": kin("paper"), "punch": ["hundred"]},
        r("a20", "So before you buy, check the price somewhere else. Because this TV cost $499.99 in the app.",
          say="So before you buy, check the price somewhere else. Because this TV cost four ninety-nine ninety-nine in the app."),
    ]},
    {"id": "s3", "hook": 'Same cart. +$9.59', "title": "Same groceries. Same store. $10 more. #shorts", "beats": [
        r("s31", "Same groceries. Same store. Same minute. Different total.", motion="zoom_in"),
        {"text": "At one Seattle Safeway, the same basket cost from $114.34 to $123.93.",
         "say": "At one Seattle Safeway, the same basket cost from one fourteen thirty-four to one twenty-three ninety-three.",
         "visual": {"type": "chart", "chart": {"kind": "bar", "title": "Same Safeway basket", "labels": ["Cheapest", "Most expensive"],
                                                "values": [114.34, 123.93], "unit": "$", "decimals": 2, "highlight": 1}}},
        {"text": "Only eight percent of shoppers got the cheapest one.",
         "visual": {"type": "stat", "stat": {"value": 8, "suffix": "%", "label": "got the cheapest basket", "decimals": 0}}},
        r("s3c", "Instacart said they were price tests. It ended them in December 2025.",
          say="Instacart said they were price tests. It ended them in December twenty twenty-five."),
        r("s30", "So next time, compare. Because it can be the same groceries, same store, same minute.", index=1),
    ]},
    {"id": "s4", "hook": '5 prices. 1 product.', "title": "Five price tags. One product. #shorts", "beats": [
        r("s35", "Five price tags. One product. Which one is real?", motion="static", sfx="pop", hand_marks=True,
          marks=[{"type": "underline", "x": 0.48, "y": 0.955, "w": 0.86, "on": "real?"}]),
        r("s35", "All of them. In a 2025 test, some items had up to five prices at the same moment.",
          say="All of them. In a twenty twenty-five test, some items had up to five prices at the same moment."),
        {"text": "The gap on a single item reached 23 percent.", "say": "The gap on a single item reached twenty-three percent.",
         "visual": {"type": "stat", "stat": {"value": 23, "suffix": "%", "label": "max gap, same item", "decimals": 0}}},
        r("s31", "Shoppers weren't told. They just saw a price and paid it."),
        r("v72", "So check on another phone before you pay. Then ask again: five price tags, one product?"),
    ]},
    {"id": "s5", "hook": "The fake 'was' price", "title": "Everyone paid $3.99. Not everyone felt the same #shorts", "beats": [
        r("s37", "These crackers had three different 'was' prices."),
        r("s37", "Five ninety-three. Five ninety-nine. Six sixty-nine. Everyone paid three ninety-nine.", motion="static"),
        {"text": "Same price. Different *feeling.*", "visual": kin("paper")},
        {"text": "The bigger the fake 'was', the better the bargain feels. That's *anchoring.*", "visual": kin("ink")},
        r("s39c", "Montana, 1887. 'These shoes sell for double the price.' One week only. Same trick.", motion="static", hand_marks=True,
          marks=[{"type": "underline", "x": 0.52, "y": 0.455, "w": 0.27, "on": "double"}],
          say="Montana, eighteen eighty-seven. These shoes sell for double the price. One week only. Same trick."),
        r("s37", "So ignore the 'was'. Look again at these crackers: three different 'was' prices."),
    ]},
    {"id": "s6", "hook": 'What shops know about you', "title": "What shops may know before you pay #shorts", "beats": [
        r("p40", "Meet the machine. He'd like a word about your shopping.", motion="static", draw={"at": 0.1, "dur": 2.8, "box": [0.1, 0.0, 0.9, 1.0]}),
        r("p43", "Location. Device. Browsing. Even your mouse movements and abandoned carts.", motion="static"),
        r("p42b", "It's in the regulator's own report: where you are, who you are, what you're doing.", motion="static", hand_marks=True,
          marks=[{"type": "underline", "x": 0.39, "y": 0.245, "w": 0.26, "on": "where"}]),
        r("p44", "An FTC example: spot a new parent, offer a baby thermometer at a premium.", on_screen="FTC example"),
        r("p45", "The FTC said the findings were preliminary. But the toolbox exists."),
        {"text": "Nothing personal. Just data.", "voice": "price", "visual": {"type": "reuse", "beat": "p40", "motion": "zoom_in"}},
        r("p40", "So, before you pay, meet the machine.", motion="static"),
    ]},
    {"id": "s7", "hook": "You're the test", "title": "You weren't targeted. You were sampled. #shorts", "beats": [
        r("w60", "Think the app picked on you?"),
        r("w62", "It didn't need to. It tested everyone, at random. Like mice in a supermarket."),
        r("w61b", "Group A sees one price. Group B sees another.", motion="static", hand_marks=True,
          marks=[{"type": "circle", "x": 0.27, "y": 0.7, "w": 0.4, "h": 0.5, "text": "A", "text_x": 0.27, "text_y": 0.35, "on": "Group"},
                 {"type": "circle", "x": 0.74, "y": 0.7, "w": 0.4, "h": 0.5, "text": "B", "text_x": 0.74, "text_y": 0.35, "on": "B"}]),
        r("w62", "The company's own material said: shoppers are not aware that they're in an experiment.", motion="static"),
        {"text": "You weren't *targeted.* You were *sampled.*", "visual": kin("red"), "sfx": "thud"},
        r("v72", "Check the price on another phone. Because next time, ask yourself: think the app picked on you?"),
    ]},
]

# ------------------------------------------------------------------ documentary layer (inserts / stock)
LOC = "Library of Congress, Prints & Photographs Division (no known restrictions)"
INS = {
    # cold open
    "c01": [{"file": "lv1940_corner.jpg", "kind": "photo", "from": "left", "x": 0.2, "y": 0.42, "w": 0.3, "on": "2016", "caption": "Main street corner, Las Vegas, 1940"}],
    "c02": [{"file": "c05", "kind": "cutout", "from": "right", "x": 0.86, "y": 0.6, "w": 0.26, "on": "People"}],
    "c06": [{"file": "p40", "kind": "cutout", "from": "left", "x": 0.14, "y": 0.6, "w": 0.24, "on": "somewhere"}],
    # 11:47
    "b11": [{"stock_photo": "taxi rain night", "pick": 10435616, "kind": "photo", "from": "right", "x": 0.8, "y": 0.4, "w": 0.3, "on": "fare"}],
    "d13": [{"stock_photo": "radio microphone vintage", "pick": 2627991, "kind": "photo", "from": "right", "x": 0.82, "y": 0.5, "w": 0.28, "on": "podcast" , "at": 0.3}],
    "d14": [{"file": "c05", "kind": "cutout", "from": "right", "x": 0.86, "y": 0.62, "w": 0.26, "on": "nobody"}],
    "d14b": [{"stock_photo": "people umbrellas rain street", "pick": 3867745, "kind": "photo", "from": "left", "x": 0.2, "y": 0.4, "w": 0.3, "on": "lots"}],
    "b16": [{"stock_photo": "smartphone gps map navigation", "pick": 2198559, "kind": "photo", "from": "right", "x": 0.84, "y": 0.42, "w": 0.26, "on": "Where", "dur": 2.4}],
    # 8:02
    "a20": [{"stock_photo": "television news camera", "pick": 2808321, "kind": "photo", "from": "left", "x": 0.2, "y": 0.42, "w": 0.3, "on": "KARE"}],
    "a21": [{"stock_photo": "television electronics store", "pick": 627876, "kind": "photo", "from": "right", "x": 0.82, "y": 0.4, "w": 0.28, "on": "Samsung"}],
    "a22": [{"stock_photo": "supermarket parking lot", "pick": 4054031, "kind": "photo", "from": "bottom", "x": 0.24, "y": 0.62, "w": 0.3, "on": "parking"}],
    "a25": [{"file": "c05", "kind": "cutout", "from": "right", "x": 0.86, "y": 0.62, "w": 0.26, "on": "lesson"}],
    # 10:15
    "s30": [{"stock_photo": "online grocery shopping phone", "pick": 6974508, "kind": "photo", "from": "right", "x": 0.84, "y": 0.4, "w": 0.26, "on": "delivery"}],
    "s32": [{"file": "supermarket_1957_a.jpg", "kind": "photo", "from": "left", "x": 0.2, "y": 0.45, "w": 0.3, "on": "volunteers", "caption": "Shopping in a supermarket, 1957"}],
    "s33b": [{"file": "grocery_lincoln_1942.jpg", "kind": "photo", "from": "right", "x": 0.82, "y": 0.42, "w": 0.28, "on": "ordinary", "caption": "Grand Grocery, Lincoln, 1942"}],
    "s36": [{"file": "piggly_aisle_1918.jpg", "kind": "photo", "from": "left", "x": 0.2, "y": 0.4, "w": 0.3, "on": "tests", "caption": "Piggly Wiggly, 1918 — the first self-service store"}],
    "s3b": [{"file": "supermarket_carts_1958.jpg", "kind": "photo", "from": "left", "x": 0.2, "y": 0.42, "w": 0.3, "on": "family", "caption": "Supermarket, 1958"}],
    # 1:30
    "h41": [{"file": "wanamaker_oakhall_1865.jpg", "kind": "clipping", "from": "right", "x": 0.84, "y": 0.45, "w": 0.22, "on": "tag", "caption": "Wanamaker & Brown, Oak Hall, 1865"}],
    "p41": [{"file": "c05", "kind": "cutout", "from": "left", "x": 0.14, "y": 0.62, "w": 0.24, "on": "Shopping"}],
    "p43": [{"stock_photo": "computer mouse hand", "pick": 625152, "kind": "photo", "from": "right", "x": 0.84, "y": 0.42, "w": 0.26, "on": "mouse"}],
    "p45": [{"file": "p40", "kind": "cutout", "from": "right", "x": 0.86, "y": 0.62, "w": 0.24, "on": "toolbox"}],
    # defence / twist / close
    "d51": [{"stock_photo": "coupons", "pick": 5219531, "kind": "photo", "from": "right", "x": 0.82, "y": 0.4, "w": 0.26, "on": "discount"}],
    "d51b": [{"stock_photo": "airport departure board", "pick": 4865665, "kind": "photo", "from": "left", "x": 0.2, "y": 0.4, "w": 0.3, "on": "fares"}],
    "w60": [{"file": "s30.1", "kind": "cutout", "from": "right", "x": 0.86, "y": 0.6, "w": 0.24, "on": "knew"}],
    "w63": [{"file": "w62", "kind": "cutout", "from": "left", "x": 0.16, "y": 0.6, "w": 0.26, "on": "experiment"}],
    "v72": [{"stock_photo": "comparing prices phone store", "pick": 410324, "kind": "photo", "from": "left", "x": 0.2, "y": 0.42, "w": 0.28, "on": "website"}],
    "v74b": [{"file": "p40", "kind": "cutout", "from": "right", "x": 0.86, "y": 0.62, "w": 0.24, "on": "guess."}],
}
for b in B:
    if b["id"] in INS:
        b["inserts"] = INS[b["id"]]
# stock film where the picture is a plain illustration of a real-world scene
STOCK = {
    "d14b": {"stock": "city street night rain traffic", "pick": 290317, "in": 0, "out": 12, "newsreel": False, "fallback": "d14b"},
    "a22": {"stock": "parking lot cars aerial", "pick": 271386, "in": 0, "out": 12, "newsreel": False, "fallback": "a22"},
    "d51b": {"stock": "airplane passengers boarding", "pick": 4732, "in": 0, "out": 14, "newsreel": False, "fallback": "d51b"},
}
for b in B:
    st = STOCK.get(b["id"])
    if st and b["visual"]["type"] == "image":
        # keep the illustration prompt as the fallback picture: move it to a hidden sibling beat id
        fb = dict(b); fb["id"] = b["id"] + "_pic"
        # not inserted into timeline; the fallback is the same illustration so just keep type image when stock missing
        b["visual"] = {"type": "clip", "stock": st["stock"], "pick": st.get("pick"), "in": st["in"], "out": st["out"], "newsreel": st["newsreel"],
                       "fallback_prompt": b["visual"].get("prompt"), "credit": "Stock footage / Pixabay"}
        if b["visual"].get("newsreel") is False:
            b["visual"].pop("newsreel")


SHORT_INS = {  # (short id, beat index) -> inserts; positions inside the Shorts picture window
    ("s1", 1): [{"stock_photo": "radio microphone vintage", "pick": 2627991, "kind": "photo", "from": "right", "x": 0.72, "y": 0.42, "w": 0.46}],
    ("s1", 4): [{"stock_photo": "smartphone gps map navigation", "pick": 2198559, "kind": "photo", "from": "left", "x": 0.3, "y": 0.45, "w": 0.46}],
    ("s2", 0): [{"stock_photo": "television electronics store", "pick": 627876, "kind": "photo", "from": "right", "x": 0.7, "y": 0.5, "w": 0.46, "at": 1.0}],
    ("s2", 1): [{"stock_photo": "supermarket parking lot", "pick": 4054031, "kind": "photo", "from": "left", "x": 0.3, "y": 0.42, "w": 0.48}],
    ("s3", 0): [{"file": "supermarket_1957_a.jpg", "kind": "photo", "from": "right", "x": 0.7, "y": 0.45, "w": 0.48, "caption": "Supermarket, 1957", "at": 0.8}],
    ("s3", 4): [{"stock_photo": "online grocery shopping phone", "pick": 6974508, "kind": "photo", "from": "left", "x": 0.3, "y": 0.45, "w": 0.46}],
    ("s4", 3): [{"file": "piggly_aisle_1918.jpg", "kind": "photo", "from": "right", "x": 0.7, "y": 0.45, "w": 0.48, "caption": "Piggly Wiggly, 1918"}],
    ("s5", 0): [{"file": "grocery_lincoln_1942.jpg", "kind": "photo", "from": "left", "x": 0.3, "y": 0.42, "w": 0.48, "caption": "Grocery, 1942", "at": 1.0}],
    ("s6", 1): [{"stock_photo": "computer mouse hand", "pick": 625152, "kind": "photo", "from": "right", "x": 0.72, "y": 0.42, "w": 0.46}],
    ("s6", 4): [{"file": "c05", "kind": "cutout", "from": "left", "x": 0.24, "y": 0.6, "w": 0.4}],
    ("s7", 0): [{"file": "s30.1", "kind": "cutout", "from": "right", "x": 0.78, "y": 0.62, "w": 0.4}],
    ("s7", 5): [{"stock_photo": "comparing prices phone store", "pick": 410324, "kind": "photo", "from": "left", "x": 0.3, "y": 0.45, "w": 0.46}],
}
for sh in shorts:
    for k, b in enumerate(sh["beats"]):
        if (sh["id"], k) in SHORT_INS:
            b["inserts"] = SHORT_INS[(sh["id"], k)]

for sh in shorts:
    for k, b in enumerate(sh["beats"]):
        b.setdefault("id", f"{sh['id']}_{k}")

ep = {
    "slug": "0003-same-basket",
    "title": "Why Your Groceries Cost More Than Your Neighbour's",
    "description": "Does your ride really cost more when your battery is low? Case file #002 follows Larry (fictional) through one day: a viral battery rumour, a TV that got $100 dearer in a parking lot, and a real 2025 investigation in which hundreds of shoppers paid different prices for the same groceries at the same store, at the same moment.",
    "tags": ["personalized pricing", "surveillance pricing", "instacart prices", "uber battery", "dynamic pricing", "anchoring",
             "psychology of money", "behavioral economics", "price discrimination"],
    "characters": {
        "larry": "a cheerful middle-aged man with a round face and a thin moustache, wearing a loud yellow checked sports jacket and a red fedora",
        "linda": "a sharp, practical woman in her forties with a neat dark bob and cat-eye glasses, wearing a mint-green 1950s shirt dress",
        "price": "a friendly retro 1950s department-store robot salesman with a polished round chrome head, a smiling speaker-grille mouth, a red bow tie, a small price-tag badge on its chest, and simple hands in white four-fingered cartoon gloves like a 1950s advertising mascot",
    },
    "voices": {"price": {"lang_code": "a", "voice": "am_puck", "speed": 0.98}},
    "music": {"_default": "ub_comic_detective", "_shorts": "ub_jump_around",
              "The case": "ub_comic_detective", "11:47 PM: 3% battery": "ub_frostfall",
              "8:02 AM: The parking lot": "ub_comic_detective", "10:15 AM: Same basket": "ub_night_spot",
              "1:30 PM: The machine": "ub_ticking_tension", "In defence of the accused": "ub_mystery_theatre",
              "The twist": "ub_ticking_tension", "Case closed": "ub_jump_around"},
    "thumbnail": {"text": "Same basket. Different price.",
                  "prompt": "two identical shopping baskets of groceries side by side on the right side of the frame, one with a small red price tag and one with a larger red price tag, plain cream background"},
    "sources": [
        "Consumer Reports & Groundwork Collaborative (Dec 2025). Instacart's AI pricing experiment — same cart, different price. consumerreports.org",
        "Instacart halts AI price-testing program (Dec 22, 2025) — e.g. SiliconANGLE, Anchorage Daily News.",
        "NPR, Hidden Brain (2016): Uber's Keith Chen on low battery and surge pricing; Uber states battery level is not used in pricing.",
        "KARE 11 (Feb 2019): Target app price switch near stores (TV $499.99 → $599.99 in the parking lot).",
        "US Federal Trade Commission (Jan 17, 2025): Surveillance pricing 6(b) study — preliminary staff findings.",
        "Larry, Linda and Mister Price are fictional characters. Scenes marked 'Reconstruction' are illustrations.",
    ],
    "beats": B,
    "shorts": shorts,
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(ep, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
words = sum(len(b["text"].split()) for b in B)
print(len(B), "beats,", words, "words")
