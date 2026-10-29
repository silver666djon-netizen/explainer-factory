# Regression checks: every bug ever found, and what catches it now

Before every release run the WHOLE list, not only the checks for the current fixes:

    tools/qc/run_regression.sh episodes/<slug> <release dir with timings.json + the rendered files>

It runs: mark audit (long + Shorts), handcheck (long + Shorts), release checks (plate_fit, crop_fit, jitter_check,
mark_in_frame, mark_on_object, hand_over_ink, shorts_picture_size, shorts_length, count_up, sfx_sync, text_stability;
voice_cut_check comes from the CI build's qc_checks.md) and the check self-test (R40: every check must FAIL on its
planted bug), the max-still warnings and
the static-frame scan, the true-peak / loudness gate and a full decode of every file. Any failure blocks the release.

Checks (RC:mark_in_frame = R32 for picture-attached marks): **MA-n** = tools/qc/mark_audit.py check n · **HC** = tools/qc/handcheck.py · **RC:name** = factory/qc.py
check (release_checks.py / CI qc_checks.md) · **STILL** = build max-still warnings (render.still_runs) ·
**AG** = tools/qc/audio_gate.py (+ the build's own gate) · **STATIC** = tools/qc/static_scan.py · **DEC** = ffmpeg full decode · **TTS** = tools/tts_scan.py
(tts-scan.yml) · **CAP** = captions engine rules (factory/captions.py, unit-checked by the build) ·
**EYE** = no automatic check possible (picture content): Claude's frame review + Klot.

| ep | bug | caught by |
|---|---|---|
| Ep.3 | a single illustration held > 8 s | STILL |
| Ep.3 | circle missing its object / drawn around empty paper | MA-1 |
| Ep.3 | stamp pressed beside its plate / photo | MA-2 |
| Ep.3 | mark or stamp drawn under Larry's tab (top-right safe zone) | MA-3 |
| Ep.3 | mark written while its target is outside the frame (push-in) | MA-4 |
| Ep.3 | mark written under a subtitle | MA-5 |
| Ep.3 | text appearing ahead of the pen tip / with no pen on it | HC (a) |
| Ep.3 | two hands on screen at once | HC (b) |
| Ep.3 | small stamp applied by a pen hand / dropped in | HC (c) |
| Ep.3 | hand leaving before the last letter; mark unfinished at the cut | HC (a) + MA-4 |
| Ep.3 | loudness off target, true peak over -1 dBTP after AAC | AG |
| Ep.3 | blank cream plate waiting on screen before the pen | MA-5 (label box) + HC |
| Ep.3 | name / number split across subtitle cards ("J.C. / Penney") | CAP |
| Ep.3 | .srt missing narration under chapter cards / kinetic text | CAP |
| Ep.3 | count-up landing after its number is said | EYE (engine times it from the voiced word, rule 17) |
| Ep.4 r60s | mark placed on a surface a moving object covers (lever, walking slips) | MA-6 |
| Ep.4 r60s | generated text inside a picture | EYE (rule 20: prompts carry no text) |
| Ep.4 r60s | narrator hand wearing Larry's sleeve | EYE (config hands.sleeve = false) |
| Ep.4 r78 G1 | fully static frames (no camera move) | STATIC |
| Ep.4 r78 G2 | red ink on dark / busy art | EYE (rule 27) |
| Ep.4 r78 G3 | marks not level with their card / tag | RC:mark_on_object (marks with "obj") |
| Ep.4 r78 G4 | reveal pause cutting inside a word (stutter) | RC:voice_cut_check + TTS |
| Ep.4 r78 G5 | count-up landing after the reveal pause | EYE (rule 30) |
| Ep.4 r78 G6 | Larry's tab covering the subject | MA-3 |
| Ep.4 r78 | doc card frozen up to 3.7 s | STATIC |
| Ep.4 r78 | end-screen push cropping the card | RC:plate_fit (card box) + EYE |
| Ep.4 r82 | handcheck run against the wrong episode (default Ep.3) | run_regression.sh always sets EP |
| Ep.4 r84 #1 | Shorts: source plate cropped by the square window; dark plate drawn over the cream caption | RC:plate_fit |
| Ep.4 r84 #2 | Shorts: crop window jumping between shots of one beat (fees leaving the ticket) | RC:crop_fit |
| Ep.4 r84 #3 | Shorts: "£3 FEE" tucked under the big plate | RC:plate_fit (plates) + RC:crop_fit + EYE |
| Ep.4 r84 #4 | plates / marks shaking during push-ins (tracked clips) | RC:jitter_check |
| Ep.4 r84 #5 | voice stutter on number lines (14.1 %) from splicing | RC:voice_cut_check + TTS |
| Ep.4 r84 #6 | marker scratch with no ink being laid | RC:sfx_sync |
| Ep.4 r84 #7 | switch OFF/ON too small, ALL-IN PRICES high on its plate | EYE (sizes in gen_script X1_*) |
| Ep.4 r84 #8 | DOWNTOWN off-centre on the counter panel | EYE |
| Ep.4 r84 #9 | mugshot SUSPECT stamp on the photo's top corner | EYE (props.Mugshot default centre, -10 deg, 70 %) |
| Ep.4 r84 #10 | typed index-card text over the red margin line | EYE (props.Mugshot text_dx, rule R30) |
| Ep.4 r84 #11 | ticket fees written beside / on the edge of the ticket | RC:mark_on_object (STUB_OBJ) |
| Ep.4 r84 #12 | "$18 FEES" crooked, floating on the wall | RC:mark_on_object + EYE (note plate) |
| Ep.4 r84 #13 | A / B letters white instead of the highlight amber | EYE |
| Ep.4 r84 #14 | SEPT 1, 2015 stamp off the photo centre | MA-2 |
| Ep.4 r84 #15 | evidence cards cropped by the push-in | RC:plate_fit (card) + evidence._camera fit |
| Ep.4 r84 #16 | FTC plate cut at the right edge | RC:plate_fit |
| Ep.4 r84 #17 | REMEMBERED: LESS started off-frame | MA-4 |
| Ep.4 r84 #18 | recap ticket price box blank for 6 s | EYE |
| Ep.4 r84 #19 | split ticket: perforation fragments on the cut, instant un-split | EYE |
| Ep.4 r84 #20 | kinetic cards re-centring with every new word | RC:text_stability |
| Ep.4 r84 #21 | 37.5 % twice in a row | EYE (script review) |
| Ep.4 r84 #22 | chart bar taller during the build, then shrinking; "37.50%" | EYE (shots.ChartShot: one common ease) |
| Ep.4 r84 #23 | USA stamp landing 9 s after "Border one: America" | EYE |
| Ep.4 r84 #24 | CASE CLOSED unreadable on the stage lights; PAID $48 tiny | EYE |
| Ep.4 r84 #25 | empty rectangle on the case folder | EYE |
| Ep.4 r84 #26 | "STOLEN BUYERS" wording | EYE (script review) |
| Ep.4 r84 #27 | UK FINED stamp beside the ticket | RC:mark_on_object |
| Ep.4 r84 | the same ticket at another position in the next beat | RC:crop_fit + EYE |
| Ep.4 r85 QC | b1 "$18 FEES" note carried off the right edge by the clip's own push-in | RC:mark_in_frame |
| Ep.4 r85 QC | Shorts: DOWNTOWN carried out of the square window at the end of c1 | RC:mark_in_frame |
| Ep.4 r85 QC | Shorts: archive caption / source plate drawn over Larry's tab; hook card touching the tab | RC:plate_fit (tab box) |
| Ep.4 r85 QC | Shorts: band plates running into the picture window (3-line plates) | RC:plate_fit (band) |
| Ep.4 r85 QC | Shorts: hook card reaching down over the picture window | RC:plate_fit (band, hook/card) |
| Ep.4 r85 QC | Shorts: pen hand entering across Larry's face (b1 note) | EYE (mark "hand_side") |
| Ep.4 r85 QC | QC false FAILs: checks read the shot state the render left (clip track on its last frame, split-moved marks) | qc._set_clip / qc._mx (checks reset it) |
| Ep.4 r86 #1 | writing hand mirrored to the left of the pen, covering the letters it had just written (15 places) | RC:hand_over_ink |
| Ep.4 r86 #2 | Shorts: picture band 270-700 px of 1920 (ticket, switch, laptop, ledger, bank windows) | RC:shorts_picture_size |
| Ep.4 r86 #3 | false PASS: plate_fit / text_stability blind to their bug | RC:check_selftest (R40) |
| Ep.4 r86 #3 | kinetic card reading as left-aligned, then re-centred (centred lines revealed word by word) | RC:text_stability + flush-left layout |
| Ep.4 r86 #4 | Shorts over 45 s (s3 47.9 s, s4 46.8 s) | RC:shorts_length |
| Ep.4 r86 #5 | count-ups showing readable wrong values (≈14 % on the 21 % card, $3.0bn, 37.3 %…) | RC:count_up |
| Ep.4 r86 #6 | sign plate blank ~3 s before TOTAL $48 | EYE (mark timing) |
| Ep.4 r86 #7 | ledger shot static 9 s, fountain-pen prop cut by the frame | STATIC + EYE |
| Ep.4 r86 #8 | grocery checkout photo under "the venue" | EYE (script review) |
| Ep.4 r86 #9 | long master at -1.0 dBTP, Telegram copy -0.7 (AAC re-encode) | AG (long -1.5) |
| Ep.4 r87 QC | false FAIL: hand_over_ink read split-moved marks + render caches after release() (n1 "+ $18") | qc.hand_over_ink uses the marks as written |
| Ep.4 r85 QC | ALL-IN PRICES ink drawn over the lever as it flips past the plate | MA-6 (unless "behind_moving") |

Add a line here for every new bug, in the round it is found, with the check that now catches it (write the check if
there is none and the bug is measurable).
