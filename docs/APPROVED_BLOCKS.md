# Approved blocks, effects and asset sources (R50)

A block, effect or asset source enters an episode only after its own test render passes QC. One row each: what it is,
the test that proved it (workflow run + draft release), the date, and any limits found. Until a row says APPROVED, the
item may be used in tests only.

| item | kind | status | proved by | date | notes / limits |
|---|---|---|---|---|---|
| Remotion 4.0.541 (all @remotion/* on the same version) | toolchain | APPROVED | remotion-upgrade-check runs 42358268908 + stills-only: 0 QC rows changed; 12 frames differ only in text anti-aliasing (mean ≤ 0.14/255) | 2026-11-07 | stay on 4.0.x, never 5.0 |
| @remotion/effects halftone, paper, speckle | effect | APPROVED | tooling-v2 run 42377153886 (after Klot's frame review) | 2026-11-07 | software GL on Actions: `--gl=swangle --preferred-effect-backend=webgl2` |
| @remotion/rough-notation Circle (red ink) | effect | APPROVED | tooling-v2 run 42364382643 | 2026-11-07 | |
| @remotion/transitions clockWipe | transition | APPROVED | tooling-v2 run 42364382643 | 2026-11-07 | |
| SplitFlap.tsx (port of HyperFrames split-flap-board) | block | APPROVED | tooling-v2 run 42377153886: straight flip, every frame checked: rests only on $30 and $48 | 2026-11-07 | |
| @remotion/lottie (support) | toolchain | APPROVED | tooling-v2 run 42377153886 (LottieProbe renders without a GPU) | 2026-11-07 | for other icons; each Lottie file still needs its own row and test |
| RubberStamp.tsx (flat 1950s rubber stamp + PAID imprint) | block | APPROVED | tooling-v2 run 42377153886: rubber on the paper on the frame the imprint appears (R49); SFX impact on that frame | 2026-11-07 | |
| @remotion/google-fonts Special Elite, Courier Prime | font | APPROVED | tooling-v2 run 42364382643 | 2026-11-07 | Latin only: no Cyrillic (RU copies keep their Cyrillic fallbacks) |
| House transition 8 · case folder (drawn in code, Transitions.tsx) | transition | APPROVED — **act changes only** | transition-reel run 42385540357 + Klot's pick | 2026-11-07 | the folder carries the act title; its label text ≥ 2.8 % of frame height and the tab inside the 6 % edge margin |
| House transition 2 · torn paper (HyperFrames torn-paper-rip, port) | transition | APPROVED — **default scene change inside an act** | transition-reel run 42385540357 + Klot's pick | 2026-11-07 | |
| House transition 1 · halftone dissolve (HyperFrames halftone-dissolve, port) | transition | APPROVED — **default scene change inside an act** | transition-reel run 42385540357 + Klot's pick | 2026-11-07 | |
| House transition 6 · iris (old cinema) | transition | APPROVED — **time jumps (the rewind) and the final "Case closed"** | transition-reel run 42385540357 + Klot's pick | 2026-11-07 | |
| House transition 7 · film burn (@remotion/transitions filmBurn) | transition | APPROVED — **optional, archive / past-date moments only** | transition-reel run 42385540357 + Klot's pick | 2026-11-07 | HTML-in-canvas: works in the bundled Chromium |
| @remotion/google-fonts Playfair Display | font | pending | — | | covers Cyrillic |
| @remotion/google-fonts Abril Fatface | font | pending | — | | Latin only |
| ElevenLabs Sound Effects (eleven_text_to_sound_v2) | asset source | APPROVED | tooling-v2 run 42377153886 + the audio test | 2026-11-07 | the first stamp came back near-silent (-41 dB peak): el_audio now remakes any SFX under -20 dB once |
| ElevenLabs Music (music_v1, instrumental) | asset source | APPROVED | tooling-v2 run 42377153886 + the audio test (no vocals heard) | 2026-11-07 | |
| Library of Congress fetcher (tools/archives.py loc) | asset source | APPROVED (outside Actions) | the test's photo; from Actions loc.gov answers 429 to item requests | 2026-11-07 | Free to Use and Reuse / no known restrictions only |
| Smithsonian Open Access fetcher (CC0 only) | asset source | pending | tooling-v2.yml probe | | needs SI_API_KEY (api.data.gov) for real use |
| Wikimedia Commons fetcher | asset source | pending | tooling-v2.yml probe | | PD / CC0 / CC BY / CC BY-SA; attribution stored |
| Internet Archive Prelinger fetcher (public domain only) | asset source | pending | tooling-v2.yml probe | | |
| the other 21 vendored HyperFrames items | block | not tested | — | | port or CLI-render on first use, each with its own test |

## Rejected — never in episodes

| item | kind | rejected by | date | why |
|---|---|---|---|---|
| HyperFrames hw-scribble-transition (red scribble wipe; CLI render and the ScribbleWipe.tsx port) | transition | Klot, tooling test 2 review | 2026-11-07 | off-style for CoinSense |
| LottieFiles "Approved Stamp" (Anu Menon) | asset | Klot, tooling test 1 review | 2026-11-07 | modern isometric, lavender paper: off-style for 1950s print |
| Transition 3 · page turn (@remotion/transitions bookFlip) | transition | Klot, transition reel review | 2026-11-07 | reads as a box flip, dark gaps, the board split in half |
| Transition 4 · paper collage (HyperFrames paper-collage-reveal, port) | transition | Klot, transition reel review | 2026-11-07 | black holes; a stray red circle pops up at 7.6 s |
| Transition 5 · ink bleed (HyperFrames ink-bleed-reveal, port) | transition | Klot, transition reel review | 2026-11-07 | a flat red full-screen cover — the same problem as the rejected scribble |

