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
