# Approved blocks, effects and asset sources (R50)

A block, effect or asset source enters an episode only after its own test render passes QC. One row each: what it is,
the test that proved it (workflow run + draft release), the date, and any limits found. Until a row says APPROVED, the
item may be used in tests only.

| item | kind | status | proved by | date | notes / limits |
|---|---|---|---|---|---|
| Remotion 4.0.541 (all @remotion/* on the same version) | toolchain | APPROVED | remotion-upgrade-check runs 42358268908 + stills-only: 0 QC rows changed; 12 frames differ only in text anti-aliasing (mean ≤ 0.14/255) | 2026-11-07 | stay on 4.0.x, never 5.0 |
| @remotion/effects halftone, paper, speckle | effect | APPROVED | tooling-v2 run 42364382643 | 2026-11-07 | software GL on Actions: `--gl=swangle --preferred-effect-backend=webgl2` |
| @remotion/rough-notation Circle (red ink) | effect | APPROVED | tooling-v2 run 42364382643 | 2026-11-07 | |
| @remotion/transitions clockWipe | transition | APPROVED | tooling-v2 run 42364382643 | 2026-11-07 | |
| SplitFlap.tsx (port of HyperFrames split-flap-board) | block | APPROVED | tooling-v2 run 42364382643 (start = static $30, end = static $48, pixel-exact) | 2026-11-07 | |
| HyperFrames hw-scribble-transition via the CLI (transparent WebM) | block | APPROVED | tooling-v2 run 42364382643 (alpha 0 → 1 → 0; full cover 0.85–1.35 s) | 2026-11-07 | |
| ScribbleWipe.tsx (Remotion port of the same block, GSAP timeline written out) | block | not yet | tooling-v2 run 42364382643: same coverage curve within ~2 frames, mean alpha IoU 0.74 (< 0.9) | 2026-11-07 | |
| @remotion/lottie + LottieFiles "Approved Stamp" (Anu Menon) | asset source | APPROVED (tests) | tooling-v2 run 42364382643 | 2026-11-07 | Lottie Simple License; its pastel purple pad is off our palette — fine for tests, pick our own for episodes |
| @remotion/google-fonts Special Elite, Courier Prime | font | APPROVED | tooling-v2 run 42364382643 | 2026-11-07 | Latin only: no Cyrillic (RU copies keep their Cyrillic fallbacks) |
| @remotion/google-fonts Playfair Display | font | pending | — | | covers Cyrillic |
| @remotion/google-fonts Abril Fatface | font | pending | — | | Latin only |
| ElevenLabs Sound Effects (eleven_text_to_sound_v2) | asset source | pending | tooling-v2.yml probe (audio test) | | |
| ElevenLabs Music (music_v1, instrumental) | asset source | pending | tooling-v2.yml probe (audio test) | | |
| Library of Congress fetcher (tools/archives.py loc) | asset source | APPROVED (outside Actions) | the test's photo; from Actions loc.gov answers 429 to item requests | 2026-11-07 | Free to Use and Reuse / no known restrictions only |
| Smithsonian Open Access fetcher (CC0 only) | asset source | pending | tooling-v2.yml probe | | needs SI_API_KEY (api.data.gov) for real use |
| Wikimedia Commons fetcher | asset source | pending | tooling-v2.yml probe | | PD / CC0 / CC BY / CC BY-SA; attribution stored |
| Internet Archive Prelinger fetcher (public domain only) | asset source | pending | tooling-v2.yml probe | | |
| the other 21 vendored HyperFrames items | block | not tested | — | | port or CLI-render on first use, each with its own test |
