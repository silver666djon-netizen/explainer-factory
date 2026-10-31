"""Ep.4 v2 "The Seven-Minute Heist": scene list (Stage 1). One source of truth for the plan:
python episodes/0005-drip-pricing/v2/scenes.py  ->  docs/ep04v2_scenes.md
Timing is an estimate from the words (acted documentary pace 2.2 words/s) plus the designed pause after each line; the cold
open uses the measured length of the voice samples. Final timecodes come from the render's timings.json."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WPS = 2.2
MAX_SHOT = 8.0

# source labels (Klot's four) ------------------------------------------------------------------------------------
P, A, G, K = "pipeline", "archive", "GPT-still", "GROK-clip"
# the 13 "adopt now" techniques from docs/MOTION_STUDY.md
TECH = {
    "T1": "true-stroke handwriting (@remotion/paths)",
    "T2": "spring stamp + synced hit",
    "T3": "vignette breathing",
    "T4": "eased chart build",
    "T5": "kinetic title (fitText)",
    "T6": "animated route (evolvePath)",
    "T7": "parallax from one still (depth split)",
    "T8": "paper/noise wobble + ink bleed",
    "T9": "highlighter sweep",
    "T10": "word-accurate karaoke captions (every line, not repeated below)",
    "T11": "print-style ink wipe (act/scene change)",
    "T12": "camera motion blur on fast moves",
    "T13": "determinism + pacing lint (every shot ≤8 s, checked in QC)",
}
PALETTE = {
    "COLD": ("Cold open", "night blue #0E1A2B + screen glow #9FD8FF"),
    "A1": ("Act 1 · The Mark", "night blue #0E1A2B + screen glow #9FD8FF, ticking clock corner"),
    "A2": ("Act 2 · The Lab", "lab green #2F5D50 + cream #F2EAD3, blueprint paper"),
    "A3": ("Act 3 · The Gang", "warm hotel amber #C8862E + walnut #3B2416"),
    "A4": ("Act 4 · The Cops and the Escape", "red #B3262E + gold #D9A93A"),
}

# beat = (EN line, RU line, pause after s, sound, [(picture, technique, source), ...])
# a beat's shots share its time evenly; a shot never runs over 8 s.
ACTS: list[tuple[str, list]] = []

ACTS.append(("COLD", [
    ("This is the story of a robbery that took seven minutes.",
     "Это история ограбления, которое заняло семь минут.", 0.8, "low pulse bed ub_ticking_tension −20 dB, keyboard clicks",
     [("ep04v2_a1_glow: dark room, laptop glow (Grok move of the still: slow push)", "T3 vignette breathing, slow push", K)]),
    ("No masks. No getaway car. Nobody even raised their voice.",
     "Без масок. Без машины для побега. Никто даже голос не повысил.", 0.7, "bed",
     [("three quick code-drawn crossed-out icons: mask · car · megaphone, on night blue", "T2 spring stamp ×3, a soft tick on each", P)]),
    ("The victim typed in his own card number, ticked the box, and said thank you.",
     "Жертва сама ввела номер своей карты, поставила галочку и сказала «спасибо».", 1.0, "bed, three soft UI clicks",
     [("code-drawn card form on the glowing screen: digits appear as dots (no hands)", "T1 caret stroke", P),
      ("the box ticks, a 'Thank you!' button presses", "T1 tick drawn as a true stroke", P)]),
    ("His name is Larry. Larry is made up. The fees are not.",
     "Его зовут Ларри. Ларри выдуман. А сборы — нет.", 0.9, "bed; a dry stamp on 'made up'",
     [("Ep.4 o4: Larry at the kitchen table in laptop glow; name card 'LARRY' + stamp FICTIONAL", "T2 stamp", G),
      ("code-drawn fee lines slide in under the name card: SERVICE · FACILITY · PROCESSING, stamp REAL", "T9 highlighter on REAL", P)]),
    ("And before you feel sorry for him, know this... you've done it too.",
     "И прежде чем его жалеть, знайте: вы тоже так делали.", 0.6, "bed thins",
     [("slow pull back from o4 until the laptop screen fills the frame and reflects the viewer's side of the room (dark)", "T12 motion blur on the pull", G)]),
    ("You found the cheaper ticket. You picked a seat. You typed in your card.",
     "Вы нашли билет подешевле. Вы выбрали место. Вы ввели карту.", 0.4, "bed, one click per sentence",
     [("three code-drawn checkout screens flick past, each a step: price list · seat map · card form", "T12 motion blur whip between screens", P)]),
    ("Then the last screen showed a number you didn't expect... and you paid anyway.",
     "А потом последний экран показал число, которого вы не ждали… и вы всё равно заплатили.", 0.8, "bed rises, then drops out under 'paid anyway'",
     [("the last code-drawn screen: TOTAL $48 grows into frame, the Pay button lights", "T4 eased number build + T3", P)]),
    ("Why? Somebody spent years finding out exactly why. And it wasn't you.",
     "Почему? Кто-то потратил годы, чтобы выяснить, почему именно. И это были не вы.", 1.35,
     "bed fades on the hit; brass hit ub_sting_brass; ONE SECOND OF SILENCE",
     [("blueprint lines start drawing themselves over the dark screen (Act 2 teaser), cut to black on the hit", "T1 true-stroke lines, hard cut", P)]),
    ("Case file number four. The seven-minute heist.",
     "Дело номер четыре. Ограбление за семь минут.", 1.6, "case folder slide (paper whoosh), bed back for the title",
     [("Ep.4 cf1 case folder slides in, typed: CASE FILE 004 · THE SEVEN-MINUTE HEIST", "T5 kinetic title + T8 paper wobble", P)]),
]))

ACTS.append(("A1", [
    ("Tuesday. 8:12 p.m. Larry has fifty dollars, and it has to last him until Friday.",
     "Вторник. 20:12. У Ларри пятьдесят долларов, и их должно хватить до пятницы.", 0.6, "Act 1 bed ub_night_spot, clock tick",
     [("ACT 1 · THE MARK title, then ep04v2_a1_wallet: an open wallet with $50 on the table", "T11 ink wipe in, T5 title; corner clock 8:12", G),
      ("code-drawn calendar strip TUE → FRI, the $50 shrinks along it", "T4 eased bar", P)]),
    ("His favourite band plays on Saturday night, two hours away. And Larry has a plan.",
     "Его любимая группа играет в субботу вечером, в двух часах езды. И у Ларри есть план.", 0.5, "bed",
     [("code-drawn small route: Larry's flat → the city hall, '2 h' (night map)", "T6 animated route", P),
      ("Ep.4 o4 push-in on Larry: a little smile", "T7 parallax", G)]),
    ("Two websites. On the first one, a ticket costs forty dollars. Everything included.",
     "Два сайта. На первом билет стоит сорок долларов. Всё включено.", 0.3, "UI click",
     [("code-drawn browser, tab 1: $40 · ALL-IN (green tick)", "T9 highlighter on 'ALL-IN'", P)]),
    ("On the second one — same concert, same hall — thirty.",
     "На втором — тот же концерт, тот же зал — тридцать.", 0.4, "UI click",
     [("tab 2 opens beside it: $30 (fees not shown)", "T2 spring on $30", P)]),
    ("Larry closes the first tab. Ten dollars saved. Larry is a genius.",
     "Ларри закрывает первую вкладку. Десять долларов сэкономлены. Ларри — гений.", 0.8, "tab-close click; a wry little pizzicato",
     [("tab 1 closes with a small whoosh; '+$10' floats up; a hand-drawn crown over Larry (o4)", "T1 handwriting crown, ironic", P)]),
    ("Remember that number. Thirty. Hold on to it — because over the next seven minutes it's going to change, quietly, three times.",
     "Запомните это число. Тридцать. Держитесь за него — потому что за следующие семь минут оно тихо изменится трижды.", 0.6, "bed thins, clock louder",
     [("$30 big in the centre, the ink of the number slowly breathing", "T8 ink bleed + T3", P),
      ("three empty slots appear under $30: ①②③ (the coming changes)", "T2 three soft stamps", P)]),
    ("8:13. The seat map. Row G, seat 12. Larry can already hear the band.",
     "20:13. Схема зала. Ряд G, место 12. Ларри уже слышит группу.", 0.5, "faint muffled concert sound under the bed",
     [("code-drawn seat map, the camera flies to Row G seat 12, it lights", "T12 motion blur fly-in, corner clock 8:13", P),
      ("Ep.4 a10 Grok clip: the empty 1950s hall, front rows lit", "slow push", K)]),
    ("8:14. A little clock appears. \"Your ticket is held for ten minutes.\" Nobody is rushing Larry. The clock is just... there.",
     "20:14. Появляются маленькие часы. «Ваш билет забронирован на десять минут». Никто Ларри не торопит. Часы просто… есть.", 0.7, "the tick moves to the foreground",
     [("code-drawn hold timer 10:00 slides into the screen corner and starts", "T2 spring in", P),
      ("close on the timer, digits ticking 9:59 · 9:58", "T3 breathing vignette", P)]),
    ("8:16. Name. Email. Card number. Larry types the sixteen digits he knows by heart.",
     "20:16. Имя. Почта. Номер карты. Ларри вводит шестнадцать цифр, которые знает наизусть.", 0.4, "typing clicks, sixteen of them",
     [("code-drawn card form fills field by field; 16 digits as dots (no hands, no real number)", "T1 caret stroke", P)]),
    ("If you've ever bought a ticket online, you know every one of these screens. You've been on all of them.",
     "Если вы хоть раз покупали билет онлайн, вы знаете каждый из этих экранов. Вы побывали на всех.", 0.5, "bed",
     [("the four screens so far fan out like cards: tabs · seat map · timer · card form", "T12 blur on the fan", P),
      ("archive radio_city_ticket_booth_1942: people at a ticket window, every era buys this way", "slow push", A)]),
    ("8:18. Next screen. Service fee: eight dollars. Facility fee: six. Processing: four.",
     "20:18. Следующий экран. Сервисный сбор: восемь долларов. Сбор площадки: шесть. Обработка: четыре.", 0.4, "HEARTBEAT starts",
     [("code-drawn fee lines drop in one by one: SERVICE $8 · FACILITY $6 · PROCESSING $4", "T2 stamp per line on the heartbeat", P),
      ("slot ① ② ③ under $30 fill in with the three fees", "T9 highlighter", P)]),
    ("Total: forty-eight dollars.",
     "Итого: сорок восемь долларов.", 0.6, "heartbeat",
     [("TOTAL $48 builds up from $30", "T4 eased number build", P)]),
    ("Larry's ticket just grew by sixty percent between the first screen and the last.",
     "Билет Ларри только что вырос на шестьдесят процентов между первым экраном и последним.", 0.4, "heartbeat",
     [("code-drawn bar: $30 → $48, '+60%' stamp", "T4 chart + T2", P)]),
    ("It's now eight dollars more than the ticket he closed. And it leaves him two dollars until Friday.",
     "Теперь он на восемь долларов дороже билета, который он закрыл. И до пятницы у него останется два доллара.", 0.5, "heartbeat",
     [("ghost of the closed tab $40 returns next to $48: '+$8'", "T9", P),
      ("ep04v2_a1_wallet: the wallet empties to $2; calendar strip TUE → FRI", "T4", G)]),
    ("He looks at the clock. Six minutes left. He thinks about the seat he picked. The evening he has already imagined.",
     "Он смотрит на часы. Осталось шесть минут. Он думает о месте, которое выбрал. О вечере, который уже себе представил.", 0.3, "heartbeat speeds a touch",
     [("timer 6:00, close", "T3", P),
      ("Ep.4 a11 (hall, seat lit), soft dreamy glow", "T7 parallax", G)]),
    ("8:19. Larry presses Pay.",
     "20:19. Ларри нажимает «Оплатить».", 1.0, "heartbeat STOPS. Silence. One click.",
     [("the Pay button presses, screen flashes white once; corner clock 8:19", "T2 hit on the click", P)]),
    ("Seven minutes. Eighteen dollars. And here's the strange part: Larry saw the number. He chose it.",
     "Семь минут. Восемнадцать долларов. И вот что странно: Ларри видел это число. Он сам его выбрал.", 0.6, "bed back, low",
     [("the timeline 8:12 → 8:19 drawn as a line with the six steps", "T1 true stroke", P),
      ("'$18' circled by hand", "T1", P)]),
    ("So why would a man who closed a forty-dollar ticket to save ten... pay forty-eight?",
     "Так почему человек, который закрыл билет за сорок, чтобы сэкономить десять… заплатил сорок восемь?", 0.6, "bed",
     [("split screen: $40 (closed, crossed) | $48 (paid) with a big '?'", "T2 '?' stamp", P)]),
    ("To answer that, we have to go where this job was planned. And rehearsed. On millions of people.",
     "Чтобы ответить, нам придётся отправиться туда, где это дело планировали. И репетировали. На миллионах людей.", 1.2,
     "bed swells, cut on 'people' → AD BREAK",
     [("the screen dissolves into blueprint lines (pen draws a floor plan)", "T1 true stroke", P),
      ("the camera pulls out over a crowd of tiny figures (Ep.4 a5 queue), green creeps in", "T11 ink wipe to green", G)]),
]))

ACTS.append(("A2", [
    ("Every good heist starts with a blueprint. This one was drawn in 1998.",
     "Каждое хорошее ограбление начинается с чертежа. Этот нарисовали в 1998 году.", 0.5, "Act 2 bed ub_mechanisms_of_action, pen scratch",
     [("ACT 2 · THE LAB title", "T5 kinetic title + T11", P),
      ("GAP ep04v2_g01 blueprint table: blank blueprint sheet on a 1950s drafting table; the pen-line draws itself along the lines", "T1 true stroke", G)]),
    ("Three marketing researchers — Morwitz, Greenleaf and Johnson — took one price and cut it in two: a base price, and a surcharge.",
     "Три исследователя маркетинга — Морвиц, Гринлиф и Джонсон — взяли одну цену и разрезали её надвое: базовая цена и надбавка.", 0.4, "pen",
     [("typed name card 'Morwitz · Greenleaf · Johnson · 1998' + paper card 'Divide and Prosper · Journal of Marketing Research 35(4)'", "T8 paper wobble + T2", P),
      ("a code-drawn price tag cut in two by a drawn line: BASE + SURCHARGE", "T1 the cut is a true stroke", P)]),
    ("Same total. Just served in pieces.",
     "Та же сумма. Просто подана по кусочкам.", 0.4, "bed",
     [("the two halves slide apart, '=' sign stays between", "spring", P)]),
    ("And the people who saw it in pieces remembered paying less — and bought more.",
     "И те, кто видел её по кусочкам, запомнили, что заплатили меньше, — и купили больше.", 0.4, "bed",
     [("code-drawn memory bubble shows the smaller number; a basket fills", "T4", P)]),
    ("Your brain files the first number it sees. Everything after it is small print.",
     "Ваш мозг запоминает первое число, которое видит. Всё, что после, — мелкий шрифт.", 0.6, "bed",
     [("a filing drawer (Ep.4 n4) takes the first number; the rest shrinks to small print", "T8 + T9", G)]),
    ("That was the blueprint. For a rehearsal, you need a stage. And an audience. A very big one.",
     "Это был чертёж. Для репетиции нужна сцена. И публика. Очень большая.", 0.5, "bed",
     [("Ep.4 a10 Grok clip: the hall from the stage", "slow push", K),
      ("archive radio_city_crowd_1942: a huge crowd", "T12 push with blur", A)]),
    ("August 2015. StubHub, the ticket resale site — owned by eBay back then.",
     "Август 2015-го. StubHub, сайт перепродажи билетов, — тогда он принадлежал eBay.", 0.4, "bed",
     [("archive box_office_loews_capitol_1939 + typed date plate AUGUST 2015 · STUBHUB (owned by eBay)", "T5 + T8", A)]),
    ("For a couple of years, StubHub had shown every fee upfront. The price on the screen was the price you paid.",
     "Пару лет StubHub показывал все сборы сразу. Цена на экране была той, что вы платили.", 0.4, "bed",
     [("Ep.4 a4 ticket window, the price board shows one all-in price", "T1 the price written by hand", G),
      ("hand mark '= YOU PAY' under it", "T9", G)]),
    ("Then, for twelve days, it split its buyers in two. Same site. Same tickets. Two different checkouts.",
     "Потом на двенадцать дней он разделил покупателей надвое. Тот же сайт. Те же билеты. Две разные кассы.", 0.4, "bed",
     [("Ep.4 a5 queue split by a velvet rope; 'A' / 'B' written", "T1", G),
      ("code-drawn two checkouts side by side, '12 DAYS' counter ticks", "T2", P)]),
    ("Half saw the full price from the start. The other half saw the ticket alone — with the fees waiting at checkout.",
     "Половина видела полную цену с самого начала. Другая половина — только билет, а сборы ждали на кассе.", 0.4, "bed",
     [("Ep.4 a6/a7 marks: A = FULL PRICE, B = TICKET ONLY", "T1", G),
      ("Ep.4 a12 Grok clip: the three fee slips walking onto the stage, late", "slow push", K)]),
    ("Same fees. The only thing that changed was the moment you saw them.",
     "Те же сборы. Изменился только момент, когда вы их видели.", 0.5, "bed",
     [("code-drawn timeline: the same fee badge sits at START for A, at END for B", "T6 the badge travels", P)]),
    ("Here's what happened. The people who met the fees late were fourteen percent more likely to buy at all.",
     "И вот что вышло. Те, кто встречал сборы поздно, на четырнадцать процентов чаще вообще покупали.", 0.4, "bed",
     [("group B queue (a5) moves faster to the window", "T12", G),
      ("Ep.4 a9 stat 14.1% · NBER w25186", "T2 stamp + T4", P)]),
    ("They picked seats about five percent pricier — a seat looks cheaper when its fees are still offstage.",
     "Они выбирали места примерно на пять процентов дороже — место кажется дешевле, пока его сборы ещё за кулисами.", 0.4, "bed",
     [("seat map: the chosen seat jumps one row forward, '+5%'", "T12", P),
      ("fee slips waiting in the wings (a12 frame), curtain", "T7 parallax", G)]),
    ("And all together, they spent almost twenty-one percent more.",
     "А в сумме они потратили почти на двадцать один процент больше.", 1.0, "SILENCE, then a brass hit on the number",
     [("Ep.4 a8 stat ≈21% lands with the hit", "T2 spring stamp + synced hit", P)]),
    ("Twenty-one percent. For the same tickets. Because of when the number showed up.",
     "Двадцать один процент. За те же билеты. Из-за того, когда появилось число.", 0.5, "bed",
     [("Ep.4 a3 evidence card NBER w25186 · Blake, Moshary, Sweeney & Tadelis · 'Price Salience and Product Choice'", "T8 + T9 highlight '21%'", P)]),
    ("So Larry isn't foolish. Larry isn't even unusual. Larry is the average.",
     "Так что Ларри не глупый. Ларри даже не необычный. Ларри — это среднее.", 0.4, "wry pizzicato",
     [("code-drawn bell curve, a tiny Larry icon drops onto the peak", "T4 eased curve", P)]),
    ("And here's the part you might not like: you're the average too. You fall for this more often than you think.",
     "А вот что вам может не понравиться: вы тоже среднее. Вы попадаетесь на это чаще, чем думаете.", 0.7, "bed",
     [("a second icon labelled YOU drops next to Larry", "T2", P),
      ("archive concert_audience_chicago_1941: faces in a crowd", "slow push", A)]),
    ("But why does it work? Why does a man who counts every dollar let eighteen of them walk out the door?",
     "Но почему это работает? Почему человек, который считает каждый доллар, отпускает восемнадцать из них за дверь?", 0.5, "safe-room ambience",
     [("title card HOW THE LOCK WAS PICKED", "T5 kinetic title", P),
      ("ep04v2_a2_safe: the 1950s safe with four dials", "T7 parallax", G)]),
    ("Because the safe in your head has four locks. And this heist picks every one of them.",
     "Потому что у сейфа в вашей голове четыре замка. И это ограбление вскрывает каждый.", 0.5, "four soft dial ticks",
     [("code-drawn four dials over the safe, numbered 1–4", "T2 each dial springs in", P),
      ("close on dial 1, the camera settles", "T3", G)]),
    ("Lock one: the first number. Your brain grabs the first price it sees and treats it as the real one. Everything added later feels like a footnote — so you remember paying less than you did.",
     "Замок первый: первое число. Мозг хватает первую цену, которую видит, и считает её настоящей. Всё, что добавлено позже, ощущается как сноска, — поэтому вы помните, что заплатили меньше, чем на самом деле.", 0.6, "dial turns, CLICK on 'paying less'",
     [("dial 1 turns; '$30' appears big, the fees as a tiny footnote", "T9 + T8", P),
      ("Larry's memory bubble: '$30'; the receipt says $48", "T1", P),
      ("dial 1 clicks open (green)", "T2 synced click", P)]),
    ("Lock two: it's already yours. By 8:18, Larry has picked his seat. In his head, he's already sitting in it — and people hate giving up what feels like theirs.",
     "Замок второй: это уже ваше. К 20:18 Ларри выбрал место. В мыслях он уже сидит в нём, — а люди терпеть не могут отдавать то, что кажется своим.", 0.4, "dial 2 turns",
     [("dial 2 turns; seat G12 with 'LARRY' written on it", "T1", P),
      ("ep04v2_a4_seat (glimpse, dreamlike, desaturated): Larry in the seat in his head", "T7 parallax", G)]),
    ("In a famous 1990 experiment, people who had just been handed a coffee mug wanted more than twice as much to sell it as others would pay to buy it. Same mug. It was just theirs.",
     "В знаменитом эксперименте 1990 года люди, которым только что дали кофейную кружку, хотели за неё при продаже больше чем вдвое больше, чем другие готовы были заплатить. Та же кружка. Просто она была их.", 0.6, "dial 2 CLICK on 'theirs'",
     [("name card 'Kahneman, Knetsch & Thaler · 1990' + paper card 'Experimental Tests of the Endowment Effect and the Coase Theorem · J. Political Economy 98(6)'", "T8 + T2", P),
      ("ep04v2_a2_mug: one mug, two price tags", "T7 parallax", G),
      ("code-drawn tags: SELL $7.12 vs BUY $2.87 (medians)", "T4 two bars", P),
      ("Commons: the Cornell mug from Thaler's Nobel display (CC0) + licensed photos of Kahneman (CC BY-SA 2.0) and Thaler (CC BY 2.0); dial 2 opens", "T2 click", A)]),
    ("Lock three: the effort. Ten minutes of searching, a seat, sixteen digits typed in. Closing the tab now means throwing all of that away and starting again. So eighteen dollars starts to look cheaper than starting over.",
     "Замок третий: усилия. Десять минут поисков, место, шестнадцать введённых цифр. Закрыть вкладку сейчас — значит выбросить всё это и начать заново. И восемнадцать долларов начинают казаться дешевле, чем начинать сначала.", 0.6, "dial 3 turns, CLICK on 'starting over'",
     [("dial 3 turns; the four screens stack up as a pile of effort", "T12", P),
      ("a scale: '$18' vs the stack 'START OVER' — the scale tips to $18", "T4 eased tilt", P),
      ("dial 3 clicks open", "T2", P)]),
    ("Lock four: small next to big. Eighteen dollars feels small when it lands on top of a purchase you've already decided to make.",
     "Замок четвёртый: мелкое рядом с крупным. Восемнадцать долларов кажутся мелочью, когда ложатся поверх покупки, которую вы уже решили сделать.", 0.4, "dial 4 turns",
     [("dial 4 turns", "T3", P),
      ("a small '$18' block lands on a big 'DECIDED' block", "T2 spring", P)]),
    ("Psychologists showed this back in 1981: most people would drive twenty minutes to save five dollars on a fifteen-dollar calculator — but far fewer would make the same drive to save the same five dollars on a hundred-and-twenty-five-dollar one. Five dollars is five dollars. Your brain doesn't think so.",
     "Психологи показали это ещё в 1981 году: большинство людей поедут за двадцать минут, чтобы сэкономить пять долларов на калькуляторе за пятнадцать, — но куда меньше поедут так же далеко, чтобы сэкономить те же пять долларов на калькуляторе за сто двадцать пять. Пять долларов — это пять долларов. Ваш мозг так не считает.", 0.7, "dial 4 CLICK on 'doesn't think so'",
     [("name card 'Tversky & Kahneman · 1981' + paper card 'The Framing of Decisions and the Psychology of Choice · Science 211'", "T8 + T2", P),
      ("ep04v2_a2_calculators: two calculators side by side", "T7 parallax", G),
      ("code-drawn tags $15 → $10 and $125 → $120, a '20 MIN' route between", "T6 route + T9", P),
      ("bars: 68% would drive vs 29% would drive", "T4 eased chart", P),
      ("'$5 = $5' written, then dial 4 clicks open", "T1 + T2", P)]),
    ("And that little clock? It doesn't pick a lock. It's the lookout. Its only job is to make sure you don't stop and think.",
     "А те маленькие часы? Они не вскрывают замок. Они — на стрёме. Их единственная задача — чтобы вы не остановились подумать.", 0.5, "the Act 1 tick returns",
     [("ep04v2_a2_lookout: a lookout figure at a corner under a street lamp", "T7 parallax", G),
      ("the hold timer as the lookout's pocket watch", "T3", P)]),
    ("Four locks. One click. That isn't stupidity. That's how every human brain is built — and the people who design checkouts know it.",
     "Четыре замка. Один клик. Это не глупость. Так устроен каждый человеческий мозг, — и те, кто проектирует кассы, это знают.", 0.6, "the safe door swings open (low creak), bed",
     [("all four dials open, the safe door swings", "T2 + T12", G),
      ("blueprint of a checkout page with the four locks marked on it", "T1", P)]),
    ("What did StubHub do with the result? On September the first, the whole site switched. Fees at the end. For everyone.",
     "Что StubHub сделал с результатом? Первого сентября весь сайт переключили. Сборы — в конце. Для всех.", 0.4, "a big switch clunk",
     [("Ep.4 x1 toggle switch flips (Grok clip x1)", "synced clunk", K),
      ("Ep.4 d3 evidence card NBER p.27 'the switch to back-end fees'", "T8 + T9", P)]),
    ("The rehearsal was over. The show had opened.",
     "Репетиция закончилась. Спектакль начался.", 0.6, "curtain whoosh",
     [("Ep.4 a10 hall: curtain opens, the fee slips on stage (a12 last frame)", "T7 parallax", G)]),
    ("If you like catching prices in the act, subscribe. The Inspector has more files.",
     "Если вам нравится ловить цены с поличным — подпишитесь. У Инспектора ещё много дел.", 0.4, "bed",
     [("Ep.4 sub case-file stack, SUBSCRIBE written by hand", "T1", P)]),
    ("Because when a trick works this well, it never stays in one theatre.",
     "Потому что когда трюк работает так хорошо, он никогда не остаётся в одном театре.", 1.2, "bed swells, cut → AD BREAK",
     [("archive hotel_sign_cooperstown_1937: the camera swings to a hotel sign (Act 3 teaser)", "T11 ink wipe to amber", A)]),
]))

ACTS.append(("A3", [
    ("The concert is two hours away, so Larry needs a hotel. Downtown. Nowhere near a beach.",
     "Концерт в двух часах езды, так что Ларри нужен отель. В центре. Нигде рядом с пляжем.", 0.5, "Act 3 bed ub_usual_suspects, lobby ambience",
     [("ACT 3 · THE GANG title", "T5 + T11", P),
      ("Ep.4 c1 Larry in the downtown lobby, beach poster", "T7 parallax (grows about his feet)", G)]),
    ("The room says ninety-nine dollars a night. Near the end of booking, a new line appears — under a heading that sounds official: \"Taxes and Fees.\"",
     "Номер стоит девяносто девять долларов за ночь. Ближе к концу бронирования появляется новая строка — под официально звучащим заголовком: «Налоги и сборы».", 0.5, "UI click",
     [("code-drawn booking screen: ROOM $99 / NIGHT", "T2", P),
      ("a new line slides in at the bottom: TAXES AND FEES", "T9 highlighter", P)]),
    ("Inside it, next to the real taxes, sits a second member of the gang.",
     "Внутри неё, рядом с настоящими налогами, сидит второй член банды.", 0.4, "low brass",
     [("the line opens: CITY TAX · STATE TAX · RESORT FEE — the last one in shadow", "T3", P)]),
    ("Name: the resort fee. Aliases: amenity fee, destination fee.",
     "Имя: курортный сбор. Клички: сбор за удобства, сбор за местоположение.", 0.4, "camera flash, stamp",
     [("Ep.4 m2 mugshot (hotel key fob) + plate RESORT FEE, stamp SUSPECT", "T2 spring stamp + flash", G),
      ("ep04v2_a3_lineup: the lineup wall, aliases written on the height chart", "T1", G)]),
    ("Known associates: a pool Larry will never swim in, a gym he will never visit, Wi-Fi he already pays for at home, and a newspaper nobody has opened since 1998.",
     "Известные сообщники: бассейн, в котором Ларри никогда не поплавает, спортзал, куда он не зайдёт, вай-фай, за который он уже платит дома, и газета, которую никто не открывал с 1998 года.", 0.4, "four camera flashes",
     [("Ep.4 m2b paddling pool in the hotel room — associate card POOL", "T2", G),
      ("GAP ep04v2_g02 empty hotel gym — associate card GYM", "T2", G),
      ("code-drawn Wi-Fi icon over Larry's home laptop (o4) — WI-FI", "T2", P),
      ("GAP ep04v2_g03 an unopened yellowed newspaper at a hotel door — NEWSPAPER", "T2", G)]),
    ("Larry will use none of it. Larry will pay for all of it.",
     "Ларри не воспользуется ничем из этого. Ларри заплатит за всё.", 0.6, "wry beat",
     [("the four associate cards: USED 0 / PAID 4", "T4", P)]),
    ("In 2019, the Attorney General for Washington, D.C. sued Marriott. The lawsuit says at least one hundred and eighty-nine Marriott hotels charged these fees — from nine to ninety-five dollars, per room, per day.",
     "В 2019 году генеральный прокурор Вашингтона, округ Колумбия, подал в суд на Marriott. В иске говорится, что как минимум сто восемьдесят девять отелей Marriott брали эти сборы — от девяти до девяноста пяти долларов за номер в сутки.", 0.4, "bed",
     [("archive hotel_clerk_dover_1938", "slow push", A),
      ("Ep.4 c6 doc card DC AG press release July 9, 2019", "T8 + T9", P),
      ("Ep.4 c3 stat 189 hotels · ALLEGED", "T2 + T4", P),
      ("code-drawn range bar $9 —— $95 per room, per day", "T4", P)]),
    ("Resort fees aren't taxes. They just like to sit next to them.",
     "Курортные сборы — не налоги. Они просто любят сидеть рядом с ними.", 0.5, "wry pizzicato",
     [("Ep.4 c4/c5 hotel bill, the fee line nudges closer to TAX", "T1 arrow", G)]),
    ("In 2023, Marriott agreed with Texas to show the total price most prominently. Same blueprint. Different building.",
     "В 2023 году Marriott договорился с Техасом показывать полную цену на самом видном месте. Тот же чертёж. Другое здание.", 0.5, "bed",
     [("doc card Texas AG / Marriott 2023 'total price … most prominently'", "T8 + T9", P),
      ("the Act 2 blueprint laid over the hotel sign", "T11 wipe", A)]),
    ("Then there's the biggest name in tickets.",
     "А ещё есть самое громкое имя в билетах.", 0.4, "low brass",
     [("Ep.4 o1 code-drawn ticket, camera rises", "T12", P)]),
    ("In September 2025, America's Federal Trade Commission and seven states sued Live Nation and Ticketmaster.",
     "В сентябре 2025 года Федеральная торговая комиссия США и семь штатов подали в суд на Live Nation и Ticketmaster.", 0.4, "bed",
     [("archive ftc_statue_1943 + date plate SEPT 2025 · FTC + 7 STATES", "T5 + slow push", A)]),
    ("They allege the fees run from twenty-four to forty-four percent of the total price — and that fans paid over sixteen point four billion dollars in mandatory fees.",
     "Они утверждают, что сборы составляют от двадцати четырёх до сорока четырёх процентов полной цены — и что фанаты заплатили больше шестнадцати целых четырёх десятых миллиарда долларов обязательных сборов.", 0.4, "bed",
     [("Ep.4 b4 doc card FTC complaint ¶36", "T8 + T9", P),
      ("Ep.4 b5 stat $16.4bn · ALLEGED", "T2", P)]),
    ("Larry's eighteen dollars? Thirty-seven and a half percent of what he paid. Right inside that range.",
     "Восемнадцать долларов Ларри? Тридцать семь с половиной процентов от того, что он заплатил. Прямо внутри этого диапазона.", 0.5, "bed",
     [("Ep.4 b6 chart: 24% · Larry 37.5% · 44%", "T4 eased chart build", P)]),
    ("In September 2026, a judge refused to throw the case out. It goes on. Until a court decides, every word of it is an allegation.",
     "В сентябре 2026 года судья отказался закрыть дело. Оно продолжается. Пока суд не решит, каждое слово в нём — обвинение.", 0.6, "bed",
     [("Ep.4 b9 doc card Order Sept 28, 2026 · Motion to dismiss DENIED", "T2 stamp DENIED", P),
      ("plate ALLEGED stays in the corner", "T3", P)]),
    ("Now, the defence. Every accused deserves one.",
     "А теперь — защита. Она положена каждому обвиняемому.", 0.5, "GAVEL",
     [("ep04v2_a3_courtroom + title card IN DEFENCE OF THE ACCUSED", "T5 + T2 synced gavel", G)]),
    ("Here's StubHub's own story. In 2014, it says, it tried honesty. It moved to all-in prices — every fee shown upfront.",
     "Вот версия самого StubHub. В 2014 году, по его словам, он попробовал честность. Перешёл на цены «всё включено» — каждый сбор показан сразу.", 0.4, "bed",
     [("Ep.4 d2 doc card StubHub statement, White House event, March 2023", "T8 + T9", P),
      ("Ep.4 a4 ticket window, the all-in price", "slow push", G)]),
    ("And it lost customers — to rivals who kept their fees for the last screen.",
     "И потерял покупателей — конкурентам, которые оставили свои сборы на последний экран.", 0.4, "bed",
     [("Ep.4 d1 queue: line A walks across to line B", "T12", G)]),
    ("Think about that. The honest seller looked more expensive. The honest seller lost.",
     "Подумайте об этом. Честный продавец выглядел дороже. Честный продавец проиграл.", 0.6, "bed thins",
     [("two code-drawn price tags: HONEST $40 vs '$30' (+fees hidden) — the crowd goes to $30", "T4", P)]),
    ("So this isn't one villain. It's a race. And in this race, whoever tells you the truth first finishes last.",
     "Так что это не один злодей. Это гонка. И в этой гонке тот, кто первым говорит вам правду, приходит последним.", 0.5, "race tension builds",
     [("ep04v2_a3_race via Grok k2: two 1950s shop fronts; slow push-in on the empty honest shop (left) while the long queue at the right shop shuffles", "slow push; overlay writes ALL-IN on the left sign, $30 on the right sign", K),
      ("hold on the empty left doorway; code-drawn tally under each shop: LEFT 0 · RIGHT a long count", "T4 eased count", P)]),
    ("So who stops a race that nobody can afford to quit?",
     "Так кто остановит гонку, из которой никто не может себе позволить выйти?", 1.2, "a distant siren rises, cut → AD BREAK",
     [("last frame of k2 (both shop fronts, ALL-IN and $30 signs), red light sweeps across the frame (Act 4 teaser)", "T11 ink wipe to red", K)]),
]))

ACTS.append(("A4", [
    ("Funny thing is, America has caught this trick before.",
     "Забавно, что Америка уже ловила этот трюк.", 0.4, "Act 4 bed ub_clock_is_ticking, sirens in the music",
     [("ACT 4 · THE COPS AND THE ESCAPE title", "T5 + T11", P),
      ("ep04v2_a4_police: 1950s patrol car, red and gold light (Grok clip of the still)", "slow push", K)]),
    ("In 1958, a law put a sticker on the window of every new car: the price, every option, the delivery charge — and the total.",
     "В 1958 году закон наклеил стикер на окно каждой новой машины: цена, каждая опция, доставка — и итог.", 0.4, "bed",
     [("archive car_showroom_1942", "T12 push with blur", A),
      ("code-drawn window sticker fills line by line: PRICE · OPTIONS · DELIVERY · TOTAL", "T1 + T9 on TOTAL", P)]),
    ("Cars got the total sixty-seven years before concert tickets did.",
     "Машины получили итоговую цену на шестьдесят семь лет раньше, чем билеты на концерты.", 0.5, "wry beat",
     [("code-drawn timeline 1958 —— 67 YEARS —— 2025", "T6 the line draws", P)]),
    ("Because in 2025, the cops finally showed up. On both sides of the ocean.",
     "Потому что в 2025 году копы наконец появились. По обе стороны океана.", 0.4, "siren swell",
     [("night map, two flags/stamps flash: UK · USA (no real logos)", "T2", P)]),
    ("Britain first. Since April 2025, the price must include every fee you can't avoid.",
     "Сначала Британия. С апреля 2025 года в цену должны входить все сборы, которых не избежать.", 0.4, "stamp",
     [("Ep.4 l1 customs desk + the ticket travels to the UK stop on the route", "T6 animated route", G),
      ("stamp UK · ALL UNAVOIDABLE FEES · APRIL 2025", "T2", P)]),
    ("A driving-school group hid a three-pound booking fee from over eighty thousand learner drivers. It paid a four point two million pound fine. Three pounds. Very expensive pounds.",
     "Группа автошкол прятала трёхфунтовый сбор за бронирование от более чем восьмидесяти тысяч учеников. Она заплатила штраф четыре целых две десятых миллиона фунтов. Три фунта. Очень дорогие фунты.", 0.6, "wry beat on 'very expensive pounds'",
     [("Ep.4 l8 small British car with the blank L-plate area", "T7 parallax", G),
      ("code-drawn '£3' tag × 80,000 tiles", "T4", P),
      ("Ep.4 l9 stat £4.2m fine · CMA", "T2 + hit", P)]),
    ("And in June 2026, StubHub's British arm was fined too.",
     "А в июне 2026 года оштрафовали и британское подразделение StubHub.", 0.4, "stamp",
     [("route stop UK: second stamp STUBHUB UK · FINED · JUNE 2026", "T2", P)]),
    ("Then America. Since May 2025, ticket sellers and short stays — from hotels to vacation rentals — must show the total price upfront.",
     "Затем Америка. С мая 2025 года продавцы билетов и краткосрочного жилья — от отелей до съёмных квартир — должны сразу показывать полную цену.", 0.4, "stamp",
     [("the ticket flies over the ocean to the USA stop", "T6 + T12", P),
      ("Ep.4 l2/l12 stamp USA · TOTAL UPFRONT · MAY 2025", "T2", P)]),
    ("And in April 2026, StubHub agreed to pay ten million dollars back to buyers over fees it showed too late.",
     "А в апреле 2026 года StubHub согласился вернуть покупателям десять миллионов долларов за сборы, которые показывал слишком поздно.", 0.4, "hit",
     [("Ep.4 l3 stat $10m · FTC · April 2026", "T2 + T4", P),
      ("Ep.4 l3b queue push, money flowing back to line B", "T7", G)]),
    ("The same company that ran the rehearsal in 2015.",
     "Та самая компания, которая устроила репетицию в 2015-м.", 0.6, "Act 2 motif, short",
     [("flashback: Act 2 split queue (a5) in lab green, 'AUG 2015' circled", "T11 wipe + T1", G)]),
    ("Notice what the rules don't do. They ban no fee at all. Fees pay for real things — card payments, staff, the venue. The rules only want the total, upfront.",
     "Обратите внимание, чего правила не делают. Они не запрещают ни одного сбора. Сборы оплачивают реальные вещи — платежи по картам, персонал, площадку. Правила требуют только полную цену, сразу.", 0.5, "bed",
     [("fee lines return: SERVICE · FACILITY · PROCESSING, none crossed out", "T9", P),
      ("each fee gets a label: CARD PAYMENTS · STAFF · VENUE", "T1", P),
      ("all of it folds into one line: TOTAL, UPFRONT", "T2", P)]),
    ("But no law sits next to you at 8:19 p.m. So let's rewind Larry's Tuesday — and do it right.",
     "Но никакой закон не сидит рядом с вами в 20:19. Так что давайте перемотаем вторник Ларри — и сделаем всё правильно.", 0.6, "REWIND sound",
     [("o4 Larry at the laptop, corner clock 8:19", "T3", G),
      ("REWIND: the whole Act 1 runs backwards fast, clock spins to 8:12", "T12 motion blur + scan lines", P)]),
    ("8:12. Check one: look for the all-in switch. Some ticket sites can show prices with fees included. Larry turns it on — before he falls for a seat, not after.",
     "20:12. Проверка первая: ищите переключатель «всё включено». Некоторые сайты билетов умеют показывать цены сразу со сборами. Ларри включает его — до того, как влюбится в место, а не после.", 0.4, "switch clunk",
     [("CHECK 1 card", "T5", P),
      ("Ep.4 x1/x2 toggle switch flips to ALL-IN (Grok clip x1)", "synced clunk", K),
      ("code-drawn browser: a 'show prices with fees' switch turns on", "T2", P)]),
    ("Suddenly, \"thirty\" says \"forty-eight\".",
     "И вдруг «тридцать» превращается в «сорок восемь».", 0.6, "a soft hit",
     [("$30 morphs to $48 on tab 2", "T4 eased number", P)]),
    ("8:14. Check two: go to the last screen before you decide. The real price lives one click before Pay. No little clock can rush a man who already knows the total.",
     "20:14. Проверка вторая: дойдите до последнего экрана до того, как решите. Настоящая цена живёт за один клик до «Оплатить». Никакие маленькие часики не поторопят человека, который уже знает итог.", 0.4, "the tick, then it stops",
     [("CHECK 2 card", "T5", P),
      ("Ep.4 m1b laptop, LAST SCREEN written by hand", "T1", G),
      ("the hold timer appears, Larry ignores it; it fades", "T3", P)]),
    ("8:15. Check three: compare totals, not headlines. A forty-dollar ticket with no fees beats a thirty-dollar ticket with eighteen.",
     "20:15. Проверка третья: сравнивайте итоги, а не заголовки. Билет за сорок без сборов лучше билета за тридцать плюс восемнадцать.", 0.4, "bed",
     [("CHECK 3 card", "T5", P),
      ("Ep.4 x4 chart: $40 no fees vs $30 + $18 = $48", "T4 eased chart build", P)]),
    ("Larry reopens the first tab. Forty dollars. Done. Three minutes, and ten dollars still in his pocket on Friday. This time, Larry really is a genius.",
     "Ларри снова открывает первую вкладку. Сорок долларов. Готово. Три минуты — и в пятницу у него в кармане всё ещё десять долларов. На этот раз Ларри действительно гений.", 0.7, "warm major chord, the pizzicato from Act 1 returns resolved",
     [("tab 1 reopens: $40 ALL-IN, Pay pressed; corner clock 8:15", "T2", P),
      ("ep04v2_a1_wallet: $10 left, calendar TUE → FRI", "T4", G),
      ("o4 Larry, the hand-drawn crown again — now for real", "T1", G)]),
    ("Saturday night. Larry is in his seat. The band is worth every cent.",
     "Субботний вечер. Ларри на своём месте. Группа стоит каждого цента.", 0.8, "concert swell (Uppbeat, no vocals)",
     [("ep04v2_a4_seat: Larry in his seat, warm lights, smiling (Grok clip of the still)", "slow push", K),
      ("Ep.4 z0 Grok clip: Larry happy in the crowd", "T7", K)]),
    ("So — why did Larry press Pay that first Tuesday? Because the first number had already done its job. By the last screen, the fee didn't arrive at a price. It arrived at a decision that was already made.",
     "Так почему же Ларри нажал «Оплатить» в тот первый вторник? Потому что первое число уже сделало своё дело. К последнему экрану сбор пришёл не к цене. Он пришёл к решению, которое уже было принято.", 0.8, "bed low, music drops out before 'already made'",
     [("the four dials again, all open", "T2", P),
      ("$30 on the first screen, glowing", "T8", P),
      ("the fee arrives at a stamped card DECISION: MADE", "T2 stamp", P)]),
    ("Case closed.",
     "Дело закрыто.", 0.6, "stamp + brass sting",
     [("Ep.4 z1 endscreen: CASE CLOSED stamp", "T2 spring stamp + synced hit", P)]),
    ("The verdict. Guilty: the fee at the end — and its cousin, the resort fee. Accomplice: the first number on the screen.",
     "Приговор. Виновен: сбор в конце — и его кузен, курортный сбор. Соучастник: первое число на экране.", 0.6, "bed",
     [("verdict typed: GUILTY · THE FEE AT THE END", "T1 + T8", P),
      ("GUILTY · ITS COUSIN, THE RESORT FEE (m2 mugshot thumbnail)", "T2", P),
      ("ACCOMPLICE · THE FIRST NUMBER ($30 thumbnail)", "T2", P)]),
    ("Next case: the screen that asks how much you'd like to tip — before you've even had your coffee. Seventy-two percent of Americans say tipping is now expected in more places than five years ago. We'll find out who decided that.",
     "Следующее дело: экран, который спрашивает, сколько вы хотите оставить на чай, — ещё до того, как вы выпили кофе. Семьдесят два процента американцев говорят, что чаевые теперь ждут в большем числе мест, чем пять лет назад. Мы выясним, кто это решил.", 0.5, "Act 1 tick motif returns, teasing",
     [("next_tablet.png: the tip screen", "T7 parallax", P),
      ("stat 72% · Pew Research Center, Nov 2023", "T2 + T4", P),
      ("case file 005 slides in, half-open", "T8", P)]),
    ("Subscribe, so the next case file finds you.",
     "Подпишитесь, чтобы следующее дело нашло вас.", 1.5, "end sting",
     [("Ep.4 sub stack + end cards; sources plate (all 15 sources)", "T1", P)]),
]))

CLIFF = {"A1": "To answer that", "A2": "Because when a trick", "A3": "So who stops"}
STILLS = ["ep04v2_a1_wallet", "ep04v2_a1_glow", "ep04v2_a2_safe", "ep04v2_a2_mug", "ep04v2_a2_calculators",
          "ep04v2_a2_lookout", "ep04v2_a3_lineup", "ep04v2_a3_courtroom", "ep04v2_a3_race", "ep04v2_a4_police", "ep04v2_a4_seat"]


def tc(s: float) -> str:
    return f"{int(s // 60)}:{s % 60:04.1f}"


def tcs(s: float) -> str:
    return f"{int(s // 60)}:{int(round(s % 60)):02d}" if round(s % 60) < 60 else f"{int(s // 60) + 1}:00"


def main(out: str) -> int:
    vs_json = Path(__file__).with_name("voice_samples.json")
    cold_len = None
    if vs_json.exists():
        r = json.loads(vs_json.read_text())
        lens = [v["seconds"] for v in r.values() if "seconds" in v]
        cold_len = sum(lens) / len(lens) if lens else None
    t, rows, breaks, shots_n, longest, over = 0.0, [], [], 0, 0.0, False
    lines_md = []
    act_title_pad = 0.0
    for key, beats in ACTS:
        name, pal = PALETTE[key]
        raw = sum(len(en.split()) / WPS + pause for en, _, pause, _, _ in beats)
        scale = (cold_len / raw) if (key == "COLD" and cold_len) else 1.0
        lines_md.append(f"\n## {name}  ·  starts {tc(t)}\n\n**Palette:** {pal}\n")
        lines_md.append("| # | Time | Narration (EN) / Перевод (RU) | Shot · picture | Technique | Sound | Source |")
        lines_md.append("|---|---|---|---|---|---|---|")
        for bi, (en, ru, pause, sound, shots) in enumerate(beats, 1):
            d = (len(en.split()) / WPS + pause) * scale
            per = d / len(shots)
            if per > MAX_SHOT:
                print(f"OVER 8 s: {key} #{bi} {per:.1f}s x{len(shots)} {en[:40]}", file=sys.stderr)
                over = True
            longest = max(longest, per)
            for si, (pic, tech, src) in enumerate(shots):
                a = t + si * per
                shots_n += 1
                narr = f"{en}<br>*{ru}*" if si == 0 else "↳ (same line)"
                snd = sound if si == 0 else ""
                lines_md.append(f"| {key}.{bi}{chr(97 + si) if len(shots) > 1 else ''} | {tc(a)}–{tc(a + per)} ({per:.1f}s) | {narr} | {pic} | {tech} | {snd} | {src} |")
            t += d
            if key in CLIFF and en.startswith(CLIFF[key]):
                breaks.append((key, t + 0.4, en, ru))
        if key != "A4":
            t += act_title_pad
    total = t
    if over:
        return 1
    head = [
        "# Ep.4 v2 · \"The Seven-Minute Heist\" · scene list (Stage 1)",
        "",
        "Generated by `episodes/0005-drip-pricing/v2/scenes.py` — edit there, not here. r90 stays archived; nothing here touches it.",
        "",
        f"**Estimated length:** {tcs(total)} ({total:.0f} s) · **shots:** {shots_n} · **longest shot:** {longest:.1f} s (limit 8 s) · "
        f"timing = words at {WPS} w/s + designed pauses" + (f"; cold open = measured voice samples ({cold_len:.1f} s)" if cold_len else "") + ".",
        "Final timecodes come from the render's `timings.json` (the ad-break table below is re-printed from it at Stage 2).",
        "",
        "**Format (permanent from Ep.4 v2):** mechanism → why we fall for it → prosecution + defence → how not to fall for it. "
        "Everything said is shown on screen.",
        "",
        "**Source labels:** `pipeline` = code-drawn / Remotion layer · `archive` = public-domain archive photo (LoC FSA/OWI) or "
        "free-licensed Commons file · `GPT-still` = Klot's still (Ep.4 or v2) · `GROK-clip` = Grok image-to-video, 6–10 s, no text, no close-up hands.",
        "",
        "**Techniques (the 13 'adopt now' from docs/MOTION_STUDY.md):** " + " · ".join(f"{k} {v}" for k, v in TECH.items()),
        "",
        "Every line also gets T10 karaoke captions and passes the T13 pacing lint; they are not repeated in the rows.",
    ]
    tail = ["", "## Ad breaks · YouTube Studio mid-rolls", "",
            "Place each mid-roll at the timecode (YouTube Studio → Content → the video → Monetization → Ad breaks → place manually). They sit in the silence after the cliffhanger and before the act title card.",
            "", "| Break | Timecode | Cliffhanger right before it (EN / RU) |", "|---|---|---|"]
    for i, (k, at, en, ru) in enumerate(breaks, 1):
        tail.append(f"| {i} · end of {PALETTE[k][0]} | **{tcs(at)}** | {en}<br>*{ru}* |")
    tail += ["", "## The 11 GPT stills — where each one goes", "", "| Still | Used in |", "|---|---|"]
    body = "\n".join(lines_md)
    for s in STILLS:
        where = sorted({ln.split("|")[1].strip() for ln in lines_md if s in ln})
        tail.append(f"| {s} | {', '.join(where) if where else '—'} |")
        if not where:
            print("unplaced still", s, file=sys.stderr)
            return 1
    txt = "\n".join(head) + "\n" + body + "\n" + "\n".join(tail) + "\n" + (ROOT / "episodes/0005-drip-pricing/v2/scenes_tail.md").read_text()
    Path(out).write_text(txt)
    print(f"{out}: {shots_n} shots, {tcs(total)}, longest {longest:.1f}s, breaks", [tcs(b[1]) for b in breaks])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "docs" / "ep04v2_scenes.md")))
