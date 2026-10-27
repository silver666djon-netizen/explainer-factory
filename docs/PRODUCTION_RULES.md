# Production rules — quality without wasted runs

Every Claude session working on CoinSense follows this. Goal: Klot sees only finished, checked work;
no paid generation or Actions minute is spent twice on the same thing.

## What costs what
| action | cost | rule |
|---|---|---|
| new image (Nano Banana 2, OpenRouter) | ~$0.07 | images are cached forever; a re-render never redraws them. Redo only named frames. |
| music cue (Lyria) | ~$0.08 | the library in release `music-lib` is reused by every episode. Add cues, don't regenerate. |
| final render (1080p, 30 fps) | ~35 min of GitHub Actions | **at most one per episode**, after a clean preview. |
| preview render (540p, 15 fps) | ~5 min | for Claude's own QC; never sent to Telegram. |
| storyboard run | ~10 min + new images | manual only (no auto-run on script edits). |
| Telegram message | clutter | Klot gets: storyboard sheets once, the final video once, decisions. Nothing else. |

## Episode pipeline
1. Options → Klot's choice → script (`python -m factory check`, fix every warning that matters).
2. **Storyboard** (dispatch `storyboard.yml`, `send=yes` the first time only).
3. **Claude frame QC** on the contact sheets: hands, extra hands, text/digits/signatures in pictures,
   character consistency (Larry = `assets/characters/larry.png`), subject where the marks point.
   Batch all redos into **one** run (`redo=b13,n21,…`, `send=no`). Re-check only those frames.
4. Klot approves the storyboard.
5. **Preview render** (`render.yml`, `preview=yes`) → Claude downloads `<slug>-preview/long.mp4` and
   checks it end to end (contact sheets every 1.5 s, see checklist). Fix everything in one commit.
   Repeat preview only if something visible changed.
6. **One final render** (`preview=no`) → Telegram. Claude spot-checks the final, then reports.

## Claude's QC checklist (every preview)
- **Max still (from Ep. 3): no single illustration on screen longer than 8 s.** After 8 s cut to a new
  angle (second prompt / reuse with another framing), an archive insert or a card. Planned at the script
  stage (scene list shows each picture's seconds); the build logs `WARNING max-still` for any run > 8 s
  (`video.max_still_seconds` in channel.yaml) — a final render goes out only with zero warnings.
- Camera: no tearing on pans (parallax only on zoom/static), no double image between framings of one picture.
- Overlays: price cards never on a face (pictures → top-left), marker notes above the caption zone,
  doc cards above captions, prop notes (roulette, slots) not over numbers.
- Marks point at the real subject of the generated picture (check the frame, not the prompt).
- MARKS ARE PLACED AFTER THE STORYBOARD, NEVER BLIND: overlay the 0.1 grid on each marked frame
  (scratch tool grid.py), measure the object, then run the marks audit (marks_audit.py: long + Shorts
  window, end of the camera move) — every circle must enclose its object, nothing cut by the frame edge.
  Marks near an edge → use zoom_out/static, not zoom_in.
- Bubbles are anchored to the picture (they ride with the camera) — place them next to the face, never
  on it, and check them in the audit for both the long frame and the Shorts window.
- Every frame must read at a glance and match the line (a "low battery" is a phone with an empty
  battery, not an abstract red button). Reject abstract stand-ins in the storyboard check.
- Captions: no overlap with cards/bubbles; names spelled right.
- Sound: music mood per chapter, stings land on the right word, narration always clearly on top.
- Shorts: hook card on frame 0, hook in first line, loop back, ≤ 45 s, music matches; pictures play in
  the square window (not a macro vertical slice) — check that each one is readable on a phone.
- Thumbnail A/B/C: text readable small, circle on the subject.

## Hand-drawn beats (channel signature)
- `"draw": {"on": "<word>", "box": [x0,y0,x1,y1]}` on an image beat: the newspaper hand pencils the subject's
  outlines, then the colour hand fills it with marker strokes. Heroes, objects, details only — never scenery.
- The subject must stand on a FLAT backdrop (plain cream / one flat tone): the picture behind it is removed
  while it is drawn, and a busy background leaves a silhouette. So a draw beat gets its own prompt
  "... on a plain cream background" (one generation, ~$0.07) or reuses a flat frame (icons, mice, portraits).
  Never put "draw" on a street/room scene frame.
- 3–4 draw beats per long video, 1 per Short; red-pencil hand marks: `"hand_marks": true` on the beat.
- Archive inserts (photos, newspaper clippings, documents, film) in every episode: public domain / CC only
  (Library of Congress, Prelinger/archive.org, NARA, Wikimedia Commons), credit lines go to the description.

## Logos / banners / other brand art
Small batches (≤ 10) only after Klot picks a direction; finals are made once from the chosen draft.

## Handwriting, hands and stamps (engine rules, from Ep. 3 on)
1. Written text is revealed by a mask that follows the pen tip along the ink: nothing right of the tip exists.
   The pen takes as long as the text needs (~0.075 s per letter).
2. One line at a time: a multi-line mark is several passes; the hand leaves between them.
3. One hand on screen at a time: a second hand action waits until the first hand has left (>= 6 frames gap) —
   marks, Larry's tab, evidence-card underlines, folder-page writing, stamp hands.
4. The hand leaves only after the last letter.
5. A strike-through covers every line of the mark it cancels (one stroke per line, hand lifts between).
6. Ink colour = pen colour (graphite pencil -> black, red pencil -> red, white paint pen -> white).
7. Small stamps on paper (OPEN, SUSPECT, EXHIBIT, REAL TOTALS, …): the stamp hand (wooden handle, red rubber,
   assets/hands/hand_stamp.png) enters from above, presses (impression appears on the press frame, uneven ink),
   holds 3–4 frames, lifts, leaves; sound "kachunk" (same sample every time). Never a pen hand, never a drop-in.
8. Large stamps over the whole picture (CASE CLOSED, FAIR AND SQUARE, amounts, percentages, 1:2 REFUSED,
   PROMOTED, NOT PROVEN): drop in from above with the heavy thud.
9. Typed text (mugshot card) types letter by letter with typewriter clicks, each field when the narrator reads it.
QC: the 4 fps hand check (text ahead of pen, two hands, pen-applied stamps, marks not finishing in their shot)
must report zero before a final render.
10. No drawing hand enters a frame where a character's own hands are visible in the same area — use a push-in
    (or write on a part of the picture far from the character's hands, entering from the other side).
11. Every circle / underline / strike / cross carries a labelled "target" box and must land on it; stamps press
    with their centre inside their plate; nothing is drawn in the ledger safe zone (top-right 18 % x 22 %) while
    Larry's tab is on screen. Hero close-ups of a character (beat "hero": true) hide the tab, like newsreel,
    titles, cards and the end screen. Check: `python tools/qc/mark_audit.py episodes/<slug> <timings.json> --shorts`
    — zero exceptions before a final render.
12. Archive captions are drawn by the overlay on a solid cream plate at output resolution (never baked into the
    print). Chart bars carry their value labels. A push-in that ends on a detail returns to the full frame before
    the cut when the next shot needs context ("closeup": {..., "back": s}).
13. Subscribe bell: red with a cream outline, placed clear of the character (cta "pos").
14. Audio gate: every rendered file is metered after encoding (BS.1770, ffmpeg ebur128). True peak above
    -1.0 dBTP (`audio.true_peak_max`) fails the build. Loudness: one constant gain, calibrated so the level after
    the limiter lands on `audio.target_lufs` (-14.0). Master: 4x oversampled limiter (ceiling 0.72), 48 kHz,
    AAC 192k with an 18 kHz cutoff (the native AAC encoder overshoots up to +5 dB on the scribble/stamp top end).
    A file over the ceiling is remastered automatically (audio only, video copied) at 0.66 / 0.60 / 0.54
    before the build fails. Spot-check any file with `python tools/qc/audio_gate.py <files>`.
15. A mark is never written while its target or the mark itself is outside the frame. Written labels are kept
    inside the visible picture by the engine; a push-in that needs a mark pulls back first ("closeup":
    {"back": s, "back_marks": [...]}: written only on the full frame). The mark audit checks every frame of
    every hand action (check 4) - zero exceptions before a final render.
16. A mark is never written while a subtitle covers its target (or the mark itself): place the mark above the
    caption band or time it after the line's subtitle has cleared. Mark audit check 5 — zero exceptions before
    a final render.
17. Every animated stat lands on its final value no later than the first syllable of that number (the engine
    times the count-up from the voiced beat: stat "on" word, else the first spoken number).
18. A cream plate under a written label appears only with the pen's first stroke (write(..., plate=[sx, sy]):
    it slides in under the pen) — never a blank plate waiting on screen. Rule 16 now tests the full stroke path
    of circles / crosses / underlines and the box of labels for as long as they are on screen.
19. Klot's own subscriptions are a production resource — use them fully, before paid API generations or stock:
    - ChatGPT (GPT images): character references (Larry sheet), hero frames, backgrounds, thumbnails. Holds faces well
      (Flux 2 did not). Claude writes the prompts; Klot generates and sends the files back.
      Drop a still in as `episodes/<slug>/images/<beat id>.png` (the engine uses it instead of generating).
    - Grok Imagine: short live clips, 6–15 s (image-to-video from an approved still keeps the 1950s look; 720p).
      Good: portraits, products, objects, calm camera moves, simple gags. Poor: crowds, hands, text in motion, fast physics.
      Drop a clip in as `episodes/<slug>/clips/<beat id>.mp4` (visual type "clip"; the 8-second rule still applies).
    At the scene-list stage Claude marks which frames go to GPT and which become Grok clips, and sends the prompts
    one stage at a time.
20. No generated text inside any picture (signs, screens, plates, letters, numbers). Every word, number, price, button
    label or plate letter is code-drawn on top (marks, plates, composited props in make_edits.py) — e.g. Ep.4's laptop
    screen is generated blank and the checkout page is drawn on it; the learner car's "L" is written by our hand.
    Prompts carry no notes in brackets: production notes go in the visual's "note" field.
21. Larry's jacket belongs only to Larry. From Ep.4 on, no narrator hand (pen, marker, stamp, ledger, end-screen click)
    wears Larry's yellow check sleeve: every hand ends at a plain white cuff (assets/hands/hand_<kind>_cuff.png,
    switched on per episode with config "hands": {"sleeve": false}). Larry's tab is written by the small cuff hand
    sliding in from the right edge only as far as the card (config "ledger": {"hand": "ink_cuff", "from": "right"}).
    Ep.3 stays as released.
22. Telegram order (from Ep.4 r78 on). Every send starts with a one-line header
    "CoinSense · EP04 · r78 · FINAL CANDIDATE" — statuses PREVIEW, STILLS, FINAL CANDIDATE, APPROVED FINAL, RU REVIEW,
    SHORTS; a superseding version says so: "… · replaces r77". File names carry episode and version:
    cs_ep04_r78_long.mp4, cs_ep04_r78_s1.mp4 … s7, cs_ep04_r78_description.txt (language versions cs_ep03_r85_ru_…);
    never a bare "long.mp4" (render.yml renames the release files: python -m factory.naming rename …).
    Send only versions that passed QC and that Klot asked for — never failed or intermediate renders (render.yml sends
    nothing by default; Telegram goes out only through the Notify workflow with tag + status [+ replaces]).
    One message per version: the long video first (a 480p Telegram copy when the 1080p file is over the bot limit;
    the release link carries the full file), then the Shorts in one batch, then the description.
    After APPROVED FINAL, one last message with that header and the links.
23. Subtitle cards (burned-in karaoke and .srt, long video and Shorts; factory/captions.py). Never split a name, a
    number or a fixed phrase across cards: "J.C. Penney", "High Court", "Fair and Square", "Black Friday",
    "four eighty-nine ninety-nine", "nine hundred and eighty-five million dollars", "two fifty-nine fifty-nine",
    "zero point zero two percent", "four weeks". Number words + their unit, capitalised names, month + year,
    hyphenated adjective + noun, phrasal verbs ("wrote down") and an article with its word stay together
    automatically; an episode adds its own phrases in config "captions": {"keep": [...]}. At least two words per card
    — no lone "at." or "Name:" — except a one-word sentence that is a deliberate beat ("Twice.", "One."). A card ends at
    a sentence end; inside a sentence the split is balanced, prefers commas/colons/dashes and never ends on "the",
    "of", "can" or a subject pronoun. A long name or number may take a second line rather than split.
24. The uploaded .srt carries EVERY spoken line, including narration over chapter cards (t1–t5 "Monday, nine a.m.")
    and kinetic text (k14, e9). The burned-in subtitles may stay hidden there; the .srt may not.
25. Never place a mark on a surface a moving object covers while the mark is on screen (a lever, walking slips, a hand):
    put it where nothing in the clip moves over it, or write it only after the object has left that spot. A mark
    written ON a moving object after it has stopped (prices on the a12 slips) is marked "on_object". Mark audit check 6
    tests every mark of a live clip against the clip's moving parts over the mark's whole time on screen — frame-to-frame
    motion (optical flow after the clip's own camera track) and objects at rest (each frame against the clip's median,
    i.e. the scene without its moving parts) — not only the first frame. Ink on our own cream plate is exempt.
    Shorts: a scene whose labels are wider than the square window uses "short_fit": [x0, x1] (that width always in view,
    window pulled back, blurred background), and a reused live beat plays its clip in the Short too ("clip": true).
