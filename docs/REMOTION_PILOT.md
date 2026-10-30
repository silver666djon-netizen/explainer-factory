# Remotion pilot: the overlay layer of Ep.4 r90 (CoinSense · PILOT · Remotion)

**3 beats, long (1920x1080) + Shorts (1080x1920), 30 fps; same timing, pictures and audio as r90.**

## What was built

The Python engine stays the planner and Remotion draws everything that sits on top of the pictures.

- **`tools/remotion/export_pilot.py`** rebuilds the r90 plan and exports it as data, not pixels.
  - **Text:** every plate, caption, card, label and kinetic word, with its lines, TTF font, size, colours, plate fill, padding, stroke and baselines.
  - **Layout:** each text element's place per frame comes from the same layout code the r90 render used (R26/R27 band rules, caption grouping).
  - **Handwriting:** each mark is the marker font's glyph outline plus centre-line strokes. The strokes are the ink's skeleton turned into a graph, with spurs pruned; strokes run straight through junctions, glyphs go left to right and each glyph starts top-first.
  - **Camera:** every picture's camera move is exported as parameters.
  - **Cards and the Tab:** number card, bar chart and kinetic card specs; Larry's Tab rows and its state machine.
  - **Files:** pictures, Shorts backdrops, card paper and the r90 audio.
- **`pilot/remotion`** (Remotion 4.0.290 + React) renders it.
  - Text is vector SVG in the same fonts.
  - Handwriting is a true stroke reveal: a `stroke-dashoffset` mask along the centre lines over the glyph. The pen tip is the point of the stroke being laid, with lifted travel between strokes.
  - Camera, pops, the Tab's grow and shrink, and push-ins are computed per frame in floating point.
- **Workflow `remotion-pilot.yml`** runs headless on GitHub Actions: export → `npm install` → timed renders → pixel QC → side-by-side files → draft release `pilot-remotion`.

## Results

| piece | video | Remotion render | s per min of video |
|---|---|---|---|
| beat 1 long (cold open ticket) | 9.7 s | 34 s | 209 |
| beat 2 long (37.5 % + bar chart) | 10.2 s | 24 s | 140 |
| beat 3 long (kinetic + Pierson photo) | 13.7 s | 43 s | 187 |
| beat 1 Short | 9.5 s | 22 s | 139 |
| beat 2 Short | 10.2 s | 23 s | 137 |
| beat 3 Short | 13.9 s | 37 s | 161 |

- **Render speed:** about 140–210 s per minute of video on a standard 4-core GitHub runner, concurrency 4, lossless PNG frames.
- **Fixed costs:** the export takes 46 s for all six pieces. The QC passes (no-hand / ink-only / text-only) cost about three more renders.
- **Full-episode estimate:** about 25 min for the long video and about 10 min for 7 Shorts.
- **r90 comparison:** the r90 Python render step was 46 min for 12.5 min of video, but that included TTS, depth maps, QC and STT. Speed is roughly a draw; it is not a reason to switch.

### Pixel QC on the Remotion output

| check | b1 long | b2 long | b3 long | b1 Short | b2 Short | b3 Short |
|---|---|---|---|---|---|---|
| plate_fit | PASS | PASS | PASS | PASS | PASS | PASS |
| mark_in_frame | PASS | PASS | PASS | PASS | PASS | PASS |
| jitter_check | PASS (0.000 px) | PASS | PASS | PASS (0.000 px) | PASS | PASS |
| hand_over_ink | PASS (2.8 %) | PASS | PASS | **FAIL (15 %)** | PASS | PASS |
| text_stability | PASS | PASS | PASS | PASS | PASS | PASS |

- **The one fail** is the Short's red ring around "= $48", at 35 % of the ring. The hand sits where it sits in r90 (same strokes, same R37 hand).
- **The measure is stricter than r90's check.** It counts every pixel the hand changes, including its soft edge and shadow; r90's check counts the sprite's alpha above 128. The fix for Ep.5 is the ring's own start point or turn in the Shorts layout.
- **Noticed on the way, in r90 itself:** a chain of marks keeps the first mark's pen. In the cold open the red ring is drawn with the graphite pencil, which breaks "red pen = red ink". The pilot uses each mark's own pen.

## What is better in Remotion

1. **Handwriting.** The pen draws each letter along its strokes, with the tip on the line; r90 wipes the text left to right with the pen at the column centre. This is the most visible difference: loops, crossings and the "$" bar are drawn the way a hand draws them.
2. **Vector text and smooth motion.** Text edges are crisp at any scale. Pops, the Tab's grow and the camera run in floating point, so a finished mark never moved backwards by even 0.001 px.
3. **Animation code.** It is declarative (React and CSS), so a new overlay kind is short to write.

## What is the same or worse

- **Speed:** no gain.
- **Tooling:** a second stack (Node, Chrome headless, React) next to Python. The pinned Remotion 4.x and Chrome must stay in step.
- **QC:** our QC reads Python plans. On Remotion output it has to become pixel checks (this pilot) or check the exported data, and the pixel passes cost extra renders.
- **Fonts:** browser text metrics differ slightly from FreeType. The layout stays in Python (PIL metrics), so offsets are below 1 px; this has to be watched with Cyrillic fonts.

## Moving the whole overlay layer for Ep.5: effort and risks

**Already ported** (it renders the 3 beats): image shots with camera, write / circle / underline marks with the hand, Larry's Tab, captions with karaoke, all plates and labels (long and Shorts band), hook card, number card, bar chart, kinetic card, vignette, punch-ins.

**Still to port:**
- rubber stamps with the stamp hand and slips;
- evidence / doc cards with the highlighter sweep and pre-exhibit;
- case file and mugshot props;
- the split ticket;
- marks on Grok clips (`OffthreadVideo` + matte);
- inserts, end screen + subscribe button, LED panel, line charts.

**Estimate:** about 3–4 working sessions to port the rest, 1 session to move the pixel QC into the release gates, then Ep.5 rendered by both engines once before switching.

**Pipeline change:** Python plans and masters the audio. Remotion draws the frames. Python re-muxes, applies the loudness / true-peak gate and runs the release checks. Those checks stay on the plan where they can (R26–R36 geometry is inherited, because Remotion reads the plan's layout); pixel checks cover hand, jitter, ink and text.

**What breaks:**
- `render.yml` turns into two stages.
- The Python checks that render frames (hand_over_ink, sfx_sync timing of ink) must read the exported data instead.
- Language versions need the Cyrillic fonts in `public/fonts`.
- Preview renders get slower to start (bundling takes about 10 s).

**Risks:** Chrome / Remotion version drift (pin versions), Remotion 5.0 license text (re-read before upgrading), and Node + Chrome CI time.

## License (checked against the current text)

The Remotion `LICENSE.md` (main branch, © 2026 Remotion) gives a Free License to:
- "an individual";
- "a for-profit organization with up to 3 employees";
- "a non-profit or not-for-profit organization";
- anyone evaluating it who is not yet using it commercially.

Everyone else needs a Company License. Its summary says "Individuals and small companies are allowed to use Remotion to create videos for free (even commercial)".

A sole proprietor with at most 3 people qualifies. The file also says "In Remotion 5.0, the license will slightly change": the pilot pins 4.0.290, and the 5.0 text must be checked before any upgrade.
