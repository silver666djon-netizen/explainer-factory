# CoinSense motion study: Remotion + HyperFrames (Oct 2026)

**Goal:** take the overlay / motion layer toward premium streaming-documentary quality.

**Sources:**
- Remotion docs (remotion.dev/docs, API overview) and its LICENSE.md.
- HyperFrames docs (hyperframes.heygen.com: HTML schema, lint rules, catalog contributing guide), README, published skills and agent guides.
- The npm registry, checked from CI by `motion-study.yml`; its output is `packages.md` in the `study-motion` release.

**Demo reel:** `cs_study_reel_long.mp4` (16:9) and `cs_study_reel_short.mp4` (9:16), 62 s each. It shows the top 10 "adopt now" items on Ep.4 assets, with r90 narration and music and no new generations.

## 1. What the two tools are

### Remotion 4 (React; pinned 4.0.290, latest 4.0.539, 5.0 not out yet)

- **How it works:** a video is a React component. `useCurrentFrame()` drives everything, and the renderer seeks frame by frame in headless Chrome, so every frame is deterministic.
- **Core:**
  - `interpolate` with `Easing`: mapping time to values with easing curves.
  - `spring`: physical easing with damping and stiffness, plus `overshootClamping` / `durationInFrames`.
  - `Sequence` / `Series` / `TransitionSeries`: putting parts on a timeline.
  - `OffthreadVideo`: frame-exact video.
  - `Audio`: volume curves.
  - `Img`, `staticFile`, `delayRender`.
  - `calculateMetadata`: duration taken from the data.

**Official packages**, checked on npm from CI at 4.0.290 and latest:

| package | at 4.0.290 | latest 4.0.539 | what it is |
|---|---|---|---|
| @remotion/transitions | ✓ | ✓ | `TransitionSeries` + presentations (fade, slide, wipe, flip, clockWipe, iris, none) + custom presentations |
| @remotion/paths | ✓ | ✓ | `evolvePath`, `getLength`, `getPointAtLength`, `getTangentAtLength`, `interpolatePath` (morph), `reversePath`, `warpPath`, `getBoundingBox` |
| @remotion/shapes | ✓ | ✓ | `makeRect` / `Circle` / `Star` / `Pie` / `Triangle` / `Polygon` as SVG paths (stamps, badges, pies) |
| @remotion/noise | ✓ | ✓ | `noise2D/3D/4D` (simplex), seeded and deterministic: organic wobble |
| @remotion/motion-blur | ✓ | ✓ | `CameraMotionBlur` (shutter angle, samples) and `Trail` |
| @remotion/layout-utils | ✓ | ✓ | `measureText`, `fitText`, `fillTextBox`: text never overflows |
| @remotion/captions | ✓ | ✓ | `Caption` type, `createTikTokStyleCaptions`, `parseSrt` / `serializeSrt` |
| @remotion/install-whisper-cpp, @remotion/openai-whisper | ✓ | ✓ | word-level timestamps from whisper.cpp / the OpenAI API, converted to `Caption[]` |
| @remotion/whisper-web | — | ✓ | whisper in the browser (newer than the pin) |
| @remotion/google-fonts, @remotion/fonts | ✓ | ✓ | font loading that the render waits for |
| @remotion/lottie | ✓ | ✓ | Lottie JSON animations, frame-synced |
| @remotion/three | ✓ | ✓ | `ThreeCanvas` (react-three-fiber) |
| @remotion/skia | ✓ | ✓ | Skia (shaders, blur) |
| @remotion/gif, @remotion/rive, @remotion/animated-emoji | ✓ | ✓ | GIF / Rive / emoji |
| @remotion/media-utils | ✓ | ✓ | `getAudioData`, `visualizeAudio`, `getWaveformPortion` (sound-synced hits, waveforms) |
| @remotion/media-parser, @remotion/webcodecs | ✓ | ✓ | reading and converting media in JS |
| @remotion/media | — | ✓ | new video and audio tags (newer than the pin) |
| @remotion/animation-utils | ✓ | ✓ | `makeTransform`, `interpolateStyles` |
| @remotion/player | ✓ | ✓ | the same composition playing in a browser page: a review player with scrubbing |
| @remotion/studio, cli, renderer, bundler, lambda, cloudrun | ✓ | ✓ | editor, CLI, Node render API, cloud rendering |
| @remotion/tailwind(-v4), zod-types, preload, licensing | ✓ | ✓ | styling, typed props for the Studio, preloading, license telemetry |
| @remotion/light-leaks | — | ✓ | ready-made light-leak overlays (newer than the pin) |
| @remotion/sfx | — | ✓ | sound-effect helpers (newer than the pin) |
| @remotion/rounded-text-box | — | ✓ | text plates with rounded, line-hugging corners (newer than the pin) |
| @remotion/web-renderer | — | ✓ | rendering in the browser (newer than the pin) |

**Templates and showcase used as references:** hello-world, TikTok captions (`createTikTokStyleCaptions`), audiogram (waveform), text-on-video overlay, three.js, Skia, stills, and the motion-blur and noise docs examples.

### HyperFrames (HeyGen, Apache-2.0, npm `hyperframes` 0.8.222)

- **Composition model:** a composition is one HTML file. The root carries `data-composition-id`, `data-width/height` and `data-duration` (seconds). Clips are timed with `data-start` / `data-duration` (relative starts like `intro + 1.5` are allowed), media offsets with `data-media-start`, and nested compositions with `data-composition-src`.
- **Animation:** GSAP is the main engine: one paused timeline per composition, registered in `window.__timelines[id]`. Adapters cover CSS, Lottie, Three.js, Anime.js and WAAPI.
- **Rendering:** headless Chrome seeks every frame and FFmpeg encodes. Output is deterministic on Linux; embedded video is converted to frames first.
- **Lint:** about 120 rules in roughly 15 groups, such as structure, determinism (`Math.random`, `Date.now`, requestAnimationFrame, CSS transitions, infinite repeats), seek-safe GSAP patterns, media, captions (`caption_text_overflow_risk`, hard-kill exits), fonts (`font_family_without_font_face`) and textures.
- **More CLI checks:** `validate` audits text contrast over time; `inspect` finds overflow, off-frame and occluded text.
- **Catalog:** about 450 blocks and components, installed with `npx hyperframes add <name>`.
  - Blocks = full scenes, such as transitions (`cinematic-zoom`, `chromatic-radial-split`, `beat-freeze-cut`), lower thirds (`lt-clean-bar`), titles (`canopy-part-title`), data (`data-chart`, `bar-chart-race`) and backgrounds.
  - Components = snippets: motion primitives (`blur-in`, `bottom-up-letters`), caption styles (`caption-clip-wipe`, `caption-editorial-emphasis`), camera moves (`camera-shake`, `camera-scan-gate`), textures (`grain-overlay`, `ascii-render-pass`) and props (`before-after-wipe`).
  - Shader transitions: `flash-through-white`, `liquid-wipe`, `cross-warp-morph`, `chromatic-split`.
- **Templates:** blank, warm-grain, kinetic-type, product-promo, swiss-grid.
- **Agent skills (7):** `/hyperframes`, `/hyperframes-cli`, `/hyperframes-registry`, `/media-use`, `/figma`, `/slideshow`, `/remotion-to-hyperframes`.
- **Other CLI commands:** `transcribe` (word-level transcript for captions) and `tts`.

**What HyperFrames does better:**
- Plain HTML + GSAP, so agents write it fluently.
- A large ready catalog of motion recipes.
- A very complete lint: determinism, seek-safety, overflow, contrast and occlusion over time.
- Apache-2.0 with no team-size threshold.
- `inspect` / `validate` check the rendered layout across time, which is close to our own QC idea.

**What Remotion does better for us:**
- A mature ecosystem with official, typed packages (paths, motion blur, captions, layout-utils, transitions).
- React state for our data-driven plans.
- Faster rendering (the reviews quote local HyperFrames at about 3 min for 30 s of 1080p).
- `@remotion/player` for in-browser review.
- The pilot already exists.

**What we borrow from HyperFrames even when rendering in Remotion:**
- **Determinism rules as a lint** on our TSX: no `Math.random` / `Date.now` / `requestAnimationFrame` / CSS transitions; only seeded noise.
- **Its `inspect` idea:** off-frame, overflow and occlusion sampled over time, folded into our plate_fit / text checks.
- **Recipes to re-implement in our print style:** `grain-overlay`, `camera-shake` (in our number-card hit), `caption-editorial-emphasis` (karaoke box), `blur-in` / `bottom-up-letters` (kinetic titles), `before-after-wipe`.
- **Its pacing check:** flag motions under 0.2 s or over 2 s, and dead zones over 1 s. That matches our max-still rule.

## 2. Catalogue

Gain and effort are rated 1–5 (5 = most). Every item keeps rules R1–R40. Beat type = where it applies in CoinSense.

| # | feature | library | what it does in CoinSense (beat type) | gain | effort | risk | verdict |
|---|---|---|---|---|---|---|---|
| 1 | True-stroke handwriting: glyph outline revealed along centre-line strokes, pen tip on the stroke | @remotion/paths + our skeleton export | every handwritten mark, the Tab amounts (handwriting, ledger) | 5 | 2 (done in the pilot) | stroke order on rare glyphs | **adopt now** (reel 01) |
| 2 | Spring stamp: number lands at 155 % and springs to 100 %, press ghost | `spring()` | number cards (R39 kept: whole number from the first frame) | 4 | 1 | overshoot must stay ≤ 1 frame below 100 % | **adopt now** (reel 02) |
| 3 | Sound-synced hit: frame jolt + stamp on the brass stab, from the plan's stab time | spring + plan timing (media-utils for audio peaks) | number cards, stamps, CASE CLOSED | 4 | 1 | none | **adopt now** (reel 02) |
| 4 | Vignette breathing (±5 % over 3 s) | CSS / interpolate | number cards, end screen | 2 | 1 | can read as flicker if faster | **adopt now** (reel 02) |
| 5 | Eased chart build: bars staggered left to right, no overshoot (rule 35), drawn gridlines, value pop on landing | spring (`damping: 200`) + evolvePath | charts | 4 | 1 | none | **adopt now** (reel 03) |
| 6 | Kinetic chapter title: fitText (never overflows), word springs, tracking-in kicker, hand-drawn red rule | @remotion/layout-utils + spring + paths | chapter cards, kinetic cards | 4 | 2 | the Cyrillic font must be loaded before measuring | **adopt now** (reel 04) |
| 7 | Animated route on a print map: dashed route drawn, ticket rides the tangent, stamps land at each border | @remotion/paths (`evolvePath`, `getPointAtLength`, `getTangentAtLength`) | "three borders" (l1–l14), any journey | 5 | 3 | map art must stay generic (no real map data) | **adopt now** (reel 05) |
| 8 | Parallax from one still: depth split into foreground + inpainted background, grown about the subject's feet | our depth model + Remotion layers | character stills (c1, b1, z0), archive photos with a clear subject | 4 | 3 | halos and inpaint smears when moved too far: keep ≤ 5 % | **adopt now** (reel 06) |
| 9 | Paper card with noise wobble (±0.45°, ±3 px), paper fibre, ink bleed (SVG turbulence) | @remotion/noise + SVG filters | evidence cards, case file, index cards | 4 | 2 | the wobble must stay slow (≤ 0.3 Hz) or text shimmers | **adopt now** (reel 07) |
| 10 | Highlighter sweep that wraps across lines (box-decoration-break) | CSS + interpolate | evidence cards (quotes) | 4 | 1 | none | **adopt now** (reel 07) |
| 11 | Word-accurate karaoke with a gliding word box | @remotion/captions (`createTikTokStyleCaptions`) + measureText + spring | Shorts subtitles; long-video subtitles in the house style | 5 | 2 | our word timings already exist (timings.json) | **adopt now** (reel 08) |
| 12 | Print-style ink wipe: torn-paper edge, ink + red rule along the edge | @remotion/transitions custom presentation + noise | chapter breaks, kinetic → archive | 4 | 2 | use only at chapter breaks (rule: cuts inside a section) | **adopt now** (reel 09) |
| 13 | Camera motion blur on fast push-ins (shutter 200°, 10 samples) | @remotion/motion-blur `CameraMotionBlur` | archive photo push-ins, whip zooms | 4 | 1 | 10× render cost on that shot only | **adopt now** (reel 10) |
| 14 | Paper grain overlay that moves (seeded noise, 8-frame cycle) | @remotion/noise / SVG feTurbulence | every frame (subtle 2–3 %) | 3 | 1 | banding at low CRF if too strong | adopt with Ep.5 |
| 15 | Light leaks between chapters | @remotion/light-leaks (needs 4.0.539) or a CSS gradient | chapter cards, end screen | 2 | 1 | can look like a cheap wedding video, so keep it rare | Ep.6+ (taste test first) |
| 16 | Path morph: a stamp outline morphing into a seal, a price tag into a ticket | @remotion/paths `interpolatePath` | stamps, end screen | 3 | 3 | paths need equal structure | Ep.6+ |
| 17 | Shapes for badges and stamps (star, pie, polygon) as SVG paths | @remotion/shapes | stamps, "ALLEGED" seals, pies for shares | 3 | 1 | none | adopt with Ep.5 |
| 18 | Rounded line-hugging caption plates | @remotion/rounded-text-box (needs 4.0.539) | archive captions, source plates | 3 | 1 | upgrade the pin first | adopt with Ep.5 (after the pin bump) |
| 19 | fillTextBox for plates (multi-line fit, rule 26) | @remotion/layout-utils | every plate, Shorts band | 4 | 2 | metrics must match our PIL layout until the plan moves | adopt with Ep.5 |
| 20 | Frame-exact Grok clips with marks riding on them | `OffthreadVideo` + our tracked matrices | clip beats with marks (m2b, x1, l1 flip) | 4 | 3 | colour shift if codecs differ | adopt with Ep.5 |
| 21 | Audio-driven hits: brass stabs / stamp thuds placed on audio peaks | @remotion/media-utils (`getAudioData`) | stamps, CASE CLOSED, cards | 3 | 2 | none | adopt with Ep.5 |
| 22 | Ducking curves drawn in the composition (volume per frame) | `Audio` `volume={(f) => ...}` | music under narration | 2 | 2 | duplicates our Python mastering | skip (mastering stays in Python) |
| 23 | Browser review player: Klot scrubs a beat in a link before the render | @remotion/player | review of every beat | 4 | 3 | needs hosting (an Artifact page or GitHub Pages) | Ep.6+ |
| 24 | Lottie micro-animations (ink splats, bells) | @remotion/lottie | end screen bell, stamp splats | 2 | 2 | third-party art and licences | skip (keep code-drawn) |
| 25 | 3D: a real paper card turning over (two faces, light) | @remotion/three | ticket flip (l1), case-file open | 4 | 4 | render time, look drift from print style | Ep.6+ |
| 26 | Skia shaders: halftone / print-dot render of a photo, ink spread | @remotion/skia | archive photos ("print" look), wipes | 4 | 4 | heavy dependency | Ep.6+ |
| 27 | Typed props with Studio controls (zod) for each beat | @remotion/zod-types | tuning marks and plates without code | 3 | 2 | none | Ep.6+ |
| 28 | Whisper word timing inside Remotion | @remotion/install-whisper-cpp | captions | 2 | 2 | we already have word timing from the TTS and the STT diff | skip (Python owns timing) |
| 29 | Google Fonts loader | @remotion/google-fonts | fonts | 2 | 1 | we ship our own TTFs (Cyrillic) | skip (keep local TTF + FontFace) |
| 30 | Cloud rendering | @remotion/lambda / cloudrun | the whole render | 3 | 3 | cost; Lambda is paid AWS | skip for now (GitHub runners are enough) |
| 31 | HyperFrames determinism lint, as our own TSX lint | idea from HyperFrames | all Remotion code | 4 | 1 | none | **adopt with Ep.5** |
| 32 | HyperFrames `inspect`-style check: overflow, off-frame, occlusion over time | idea from HyperFrames | plates, captions, cards | 4 | 2 | none | adopt with Ep.5 (into plate_fit) |
| 33 | HyperFrames pacing check (motion < 0.2 s or > 2 s, dead zones > 1 s) | idea from HyperFrames | every beat | 3 | 1 | none | adopt with Ep.5 (next to max-still) |
| 34 | HyperFrames catalog recipes rebuilt in our style: `camera-shake`, `blur-in`, `bottom-up-letters`, `caption-editorial-emphasis`, `before-after-wipe` | HyperFrames (Apache-2.0) | hits, titles, Shorts captions, "before / after the switch" | 3 | 2 | none (re-implemented, not copied) | adopt as needed |
| 35 | HyperFrames shader transitions (`flash-through-white`, `liquid-wipe`, `chromatic-split`) | @hyperframes/shader-transitions | transitions | 1 | 3 | modern look, off-style for 1950s print | skip |
| 36 | Rendering whole episodes in HyperFrames | HyperFrames | everything | 2 | 5 | slower, Linux-only determinism, a second migration | skip |
| 37 | One easing vocabulary: 4 named curves (stamp spring, settle spring, ease-in-out sine for camera, out-cubic for text) used everywhere | Remotion `Easing` / `spring` | every motion | 4 | 1 | none | **adopt with Ep.5** |
| 38 | Match cut on shape: ticket → stamp slip → bill (same rectangle carried across the cut) | Sequence + shared layout | ticket beats, chapter ends | 4 | 3 | needs planning in the script | Ep.6+ |

## 3. Demo reel: the top 10, applied to Ep.4

| # | tag on screen | Ep.4 beat | what to look at |
|---|---|---|---|
| 01 | TRUE-STROKE HANDWRITING · @remotion/paths | cold open o1–o3 | pen draws each letter; red pen = red ink |
| 02 | SPRING STAMP + SYNCED HIT · spring() | b2 37.5 % | stamp-in on the brass stab, press ghost, breathing vignette |
| 03 | EASED CHART BUILD · spring() + @remotion/paths | b6 chart | bars left to right, drawn grid, values pop on landing |
| 04 | KINETIC TITLE · @remotion/layout-utils fitText | t5 chapter | fitted title, word springs, red rule drawn |
| 05 | ANIMATED ROUTE · @remotion/paths evolvePath | l1 "three borders" | route draws, ticket rides it, three stamps |
| 06 | PARALLAX FROM ONE STILL · depth split | c1 Larry in the lobby | Larry moves against the room |
| 07 | PAPER, INK + NOISE WOBBLE · @remotion/noise | d3 evidence card | card breathes, ink texture, highlighter wraps lines |
| 08 | WORD-ACCURATE KARAOKE · @remotion/captions | b1 receipt | word box glides with the voice |
| 09 | PRINT-STYLE INK WIPE · @remotion/transitions | x5 → l4 | torn-paper edge into the archive photo |
| 10 | CAMERA MOTION BLUR · @remotion/motion-blur | l4 Pierson Motor Co. | whip push-in with real motion blur, plates steady |

## 4. Ep.5 plan

### Which engine renders what

- **Python stays the planner:**
  - script, TTS and timings, mark placement, the layout rules R1–R40;
  - pictures and Grok clips, depth maps and splits;
  - audio mix and mastering (loudness / true-peak gate), STT diff;
  - the release checks, which read the plan.
- **Remotion (pinned 4.x, below 5.0) is the renderer of every frame:** pictures and clips with the camera, all overlays (marks, Tab, plates, captions, cards, charts, kinetic, stamps, evidence, case file, mugshots, end screen) and the transitions.
- **The plan reaches Remotion as data**, the way the pilot exports it. Python then muxes the mastered audio onto the Remotion video.
- **HyperFrames:** not a renderer for us. We use its lint and inspect ideas and its recipes.

### Order of work (sessions)

1. **Pin bump** to 4.0.539, which adds light-leaks, rounded-text-box and sfx. Re-render the 3 pilot beats and diff against the current pilot (same frames expected), then lock `package-lock.json`.
2. **Port the missing beat kinds:** stamps with the stamp hand, evidence / doc cards with the house highlighter (rows 9–10), case file, mugshot index cards, the split ticket, `OffthreadVideo` clips with marks, end screen + subscribe button, LED panel.
3. **House motion vocabulary:** the 4 named easing curves (row 37), plus the adopt-now techniques as reusable components: number-card stamp, chart build, kinetic title, route map, parallax still, ink wipe, karaoke captions, motion-blurred push. Python script keys choose them per beat.
4. **QC on the new renders** (below), then a full Ep.5 preview in both engines, side by side.
5. **Ep.5 final** in Remotion; the Python renderer stays available as a fallback for one more episode.

### What our QC must read from the new renders

- **From the plan / exported data (no change):** plate_fit, crop_fit, mark_in_frame, mark_on_object, shorts_picture_size, shorts_length, count_up, card_not_empty, text_lint, text_stability (from kinetic word boxes), sfx_sync (ink windows), voice_cut_check, stt_diff (audio).
- **From the pixels (render passes, as in the pilot):**
  - hand_over_ink: normal vs no-hand vs ink-only;
  - jitter_check: ink centroid of finished marks;
  - mark_in_frame at the window edge;
  - text_stability: text-only pass.
- **New:**
  - `motion_lint`: HyperFrames-style determinism lint on the TSX (no `Math.random`, `Date.now`, requestAnimationFrame or CSS transitions; noise only with a fixed seed);
  - `inspect`: overflow / off-frame / occlusion of every text element sampled every 0.25 s, from the DOM boxes of a debug render;
  - `pacing`: no motion shorter than 0.2 s except stamps and cuts, no dead zone over the max-still rule;
  - `parallax_halo`: inpainted-area visibility below 1 % of the frame.

### Version pins and licences

- **Remotion:** every `@remotion/*` package at one exact version (now 4.0.290; next 4.0.539), never `^`, and never 5.x without re-reading its new license text.
  - The current license gives a Free License to "an individual" and "a for-profit organization with up to 3 employees", so a sole proprietor with at most 3 people is free, commercial videos included.
- **HyperFrames:** Apache-2.0 (npm `hyperframes` 0.8.222). It is used only for ideas and re-implemented recipes, so there is no dependency.
- **Node 22 for CI. Chrome:** the headless shell that Remotion downloads, pinned by the Remotion version.
