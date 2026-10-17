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
- Captions: no overlap with cards/bubbles; names spelled right.
- Sound: music mood per chapter, stings land on the right word, narration always clearly on top.
- Shorts: hook in first line, loop back, ≤ 45 s, music matches.
- Thumbnail A/B/C: text readable small, circle on the subject.

## Logos / banners / other brand art
Small batches (≤ 10) only after Klot picks a direction; finals are made once from the chosen draft.
