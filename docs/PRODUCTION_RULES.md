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
26. No frame is ever fully static (Klot r78 G1). Every still runs a slow, continuous camera move for its whole time on
    screen (static = 1.02 -> 1.08 push; "cam_rate" + "cam_continue" = one even push across beats on the same picture,
    no zoom jump at the cut). Cards get the same: stat, chart, kinetic, evidence and the end screen run a slow push
    (render.CARD_PUSH). A live clip held on a frame ("clip_until", "clip_at") keeps "cam_rate". A clip beat is one shot
    (never cut back to its still mid-line); an archive shown once is "one_shot" (one continuous move, not re-cut).
27. Ink colour by background (G2): red marker only on light paper or cream. On green, dark or busy art: the white
    paint-pen (color "#FFFFFF") or our cream plate ("plate": [sx, sy]) under the red. Checked per mark.
28. Marks sit level on the surface they are written on (G3): measure the card, tag, sticker or form line on the still,
    give the mark that angle, keep it inside the surface's margins and centred on its empty area; a list is left-aligned
    on one margin ("align": "left", one "fs" for all lines); labels written in a column are centred on the clear paper
    between the subject and the frame margin, inside the push.
29. Reveal pauses never cut a word (G4) - superseded by R33 below: "pause_at" no longer splices; it cut in the quietest 10 ms before the word (hiss of s / f / th
    counts as sound), soft 25 ms fade-out, 6 ms fade-in. tools/tts_scan.py (tts-scan.yml) synthesises every line like
    the build, transcribes it back (faster-whisper) and checks every join; run it on any new narration.
30. A count-up lands on its value before the number is said (G5): with a reveal pause before the number, it lands as
    the silence starts; otherwise at the number's first syllable.
31. Larry's tab never covers the subject (G6): a beat whose subject reaches into the tab's corner (top-right 18 % x
    22 %) gets "ledger_hide" (the tab steps aside); Shorts inherit it.

## R-rules (Klot r84, from Ep.4 r85 on; long video AND Shorts, every episode)

Numbered R26-R36 as Klot gave them (separate from rules 26-31 above). Every rule has an automatic check in
factory/qc.py (run by the CI build -> qc_checks.md next to the videos, and locally by tools/qc/release_checks.py);
any FAIL blocks the release. Bugs they came from: docs/REGRESSION_CHECKS.md.

- **R26 Plate fit:** every plate/caption fully inside the frame with >= 24 px margin, never overlapping another plate,
  text never overflowing its plate. (Overlay._fit_plate shrinks, then wraps to two lines.) Check: plate_fit.
- **R27 Shorts layout:** Shorts have their own layout pass - plates in the top band above the picture, stacked and
  centred (cream archive caption, then the dark source/date plate with ALLEGED as its prefix; <= 88 % width, >= 40 px
  side margins, cap height 36 -> min 30 px, then two lines; a caption or label too long for two lines gets a Shorts
  version: visual "caption_short", beat "label_short"; Larry's tab steps aside while a band plate or a top card is up); one fixed crop window per beat containing the subject and
  all its marks with >= 6 % margin (render.short_windows; push-ins zoom inside it). Checks: plate_fit, crop_fit.
- **R28 No jitter:** camera moves are sub-pixel (float affine, never integer crops); picture-attached overlays are
  composited onto the picture before the move; tracked clips are smoothed (shots._smooth_tracks). Screen-fixed
  plates never move. Check: jitter_check (no reversal > 0.25 px).
- **R29 Marks sit on their object:** handwriting and stamps land on blank paper of the object they belong to, inside it
  with >= 6 % margin, level with the object (+-2 deg), never over printed text, never floating on a busy illustration
  (use a cream note: mark "note": true). Ink on a surface a clip's moving part passes in front of (the switch lever)
  gets "behind_moving": the engine hides the ink wherever the frame differs from the clip's still scene. Mugshot stamps centred, about -10 deg, ~70 % of the photo width. Give such
  marks "obj": [x0, y0, x1, y1, angle] and "printed": [[x0, y0, x1, y1], ...] (picture fractions). Check: mark_on_object.
- **R30 Typed card text starts right of the red margin line** (>= 16 px; props.Mugshot text_dx).
- **R31 Kinetic text is laid out in its final position before the reveal;** nothing moves when a word appears (only the
  background pushes). Check: text_stability.
- **R32 Push-ins never crop the object they are about** (evidence card incl. its tag with >= 4 % margin, ticket, plate;
  evidence._camera fits the zoom); a mark on the picture never leaves the frame while it is on screen - a clip's own
  push-in included (fade it out first: "fade_after"). Checks: plate_fit, crop_fit, mark_in_frame.
- **R33 Narration cuts/pauses only at word boundaries with silence on both sides;** otherwise regenerate with a break.
  "pause_at" makes the voice itself pause (a "..." break in the text sent to the TTS) - no splicing unless
  "splice": true and the scan shows >= 40 ms of silence on both sides. Check: voice_cut_check (RMS < -45 dBFS in the
  30 ms before and after every edit point, every point listed) + tools/tts_scan.py.
- **R34 Marker scratch SFX only while ink is being laid:** the sound is driven by the handwriting engine (one scratch
  per stroke, from the first stroke to pen lift; a mark already there makes no sound). Check: sfx_sync (no scratch
  outside an ink span, none > 80 ms after pen lift).
- **R35 Chart bars grow monotonically from zero,** all together; labels without trailing zeros (37.5 %). Check: handcheck.
- **R36 The same object keeps its position across consecutive beats** (no ticket jump between shots: one picture,
  "cam_continue", one Shorts window per run of beats on the same picture). Checks: crop_fit, handcheck.

## R-rules (Klot r86, from Ep.4 r87 on)

- **R37 Writing hand:** always a right hand, to the right of and below the pen tip, never mirrored; the frame may crop
  the hand, never the mark. (draw._hand: never mirrored, turned 18 deg clockwise about the tip; rings 32 deg and drawn
  clockwise from just left of the bottom.) Check: hand_over_ink (<= 5 % of the ink already laid under the hand; the
  letter under the nib, 2.5 % of the frame around the tip, is not counted).
- **R38 Shorts picture band >= 50 % of the frame height** (960 of 1920 px; shots.SHORT_MIN_BAND); code-drawn objects use
  vertical-native layouts in Shorts: visual "short_image" (e.g. the portrait ticket images/o1v.png, stub under a
  horizontal perforation), mark "short" overrides, "short_split" ("axis": "y"), "short_subject_x"; wide props move their
  marks in (switch OFF/ON) instead of shrinking the band. Check: shorts_picture_size.
- **R39 (replaced, Klot r89) No count-ups; numbers appear whole.** The number card - final value and its subline -
  arrives with a short stamp (110 % -> 100 % over 0.2 s, brass stab) on the first word of the sentence that carries
  the number (the shot before it holds until then). A wrong number on screen is a factual error. Checks: count_up
  (every frame of a number card shows the final value), card_not_empty.
- **R40 Every automatic check must FAIL on its planted-bug test frame before a release can pass** (qc.selftest: one
  planted bug per check - plate off the edge, a mark out of the window, shaking mark, mark off its object, mirrored hand
  over its ink, 30 % picture band, 50 s Short, 1.4 s count-up, scratch without ink, edit point inside a word, kinetic
  words re-centring). The self-test table sits under the checks table in qc_checks.md; a check that PASSES its planted
  bug is blind and blocks the release.
- Shorts length: <= 45.0 s (check: shorts_length). Kinetic cards: lines flush left in a centred block (a line revealed
  word by word never looks like it re-centres). The long master's true peak <= -1.5 dBTP (channel.yaml
  true_peak_max_long); the Telegram 480p copy keeps the mastered audio stream (no re-encode).

## Text and voice (Klot r89)

- No unexplained abbreviation inside a quote: expand it in square brackets ("the switch to [back-end fees] at StubHub").
- No space before % ("+5%", "28%"); number cards are all caps ("OVER £760K"); no double spaces (the "  ·  " kicker
  separators excepted); one kind of quotes per episode. Check: text_lint (every on-screen string of every beat).
- Index cards say ALIASES when more than one alias is listed (props.Mugshot).
- Every render's narration (the voice track) is transcribed (faster-whisper medium.en) and diffed against the script
  after normalising numbers / money / years to words; any difference blocks the release (check: stt_diff). A
  transcription slip may only be waived in the episode's "stt_known" with its reason, after the voice's own phonemes
  (tools/tts_scan.py: per-word G2P) confirm the word is spoken right. Transcription is line by line (each beat's own
  voice span), never one pass over the whole track (whisper carries words across lines). The published files are
  checked the same way on their final audio before FINAL: tools/qc/stt_release.py (stt-release.yml) -> stt_diff.md.
