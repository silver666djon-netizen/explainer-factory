# Approved blocks, effects and asset sources (R50)

A block, effect or asset source enters an episode only after its own test render passes QC. One row each: what it is,
the test that proved it (workflow run + draft release), the date, and any limits found. Until a row says APPROVED, the
item may be used in tests only.

| item | kind | status | proved by | date | notes / limits |
|---|---|---|---|---|---|
| Remotion 4.0.541 (all @remotion/* on the same version) | toolchain | pending | remotion-upgrade-check.yml (QC + self-tests vs 4.0.290) | | stay on 4.0.x, never 5.0 |
| @remotion/effects halftone, paper, speckle | effect | pending | tooling-v2.yml test render | | software GL on Actions: `--gl=swangle --preferred-effect-backend=webgl2` |
| @remotion/rough-notation Circle (red ink) | effect | pending | tooling-v2.yml test render | | |
| @remotion/transitions clockWipe | transition | pending | tooling-v2.yml test render | | |
| SplitFlap.tsx (port of HyperFrames split-flap-board) | block | pending | tooling-v2.yml test render | | |
| HyperFrames hw-scribble-transition via the CLI (transparent WebM) | block | pending | tooling-v2.yml test render | | |
| ScribbleWipe.tsx (the same block through @remotion/gsap) | block | pending | tooling-v2.yml test render (alpha IoU vs the CLI render) | | |
| @remotion/lottie + LottieFiles "Approved Stamp" (Anu Menon) | asset source | pending | tooling-v2.yml test render | | Lottie Simple License |
| @remotion/google-fonts Special Elite, Courier Prime | font | pending | tooling-v2.yml test render | | Latin only: no Cyrillic (RU copies keep their Cyrillic fallbacks) |
| @remotion/google-fonts Playfair Display | font | pending | — | | covers Cyrillic |
| @remotion/google-fonts Abril Fatface | font | pending | — | | Latin only |
| ElevenLabs Sound Effects (eleven_text_to_sound_v2) | asset source | pending | tooling-v2.yml probe (audio test) | | |
| ElevenLabs Music (music_v1, instrumental) | asset source | pending | tooling-v2.yml probe (audio test) | | |
| Library of Congress fetcher (tools/archives.py loc) | asset source | pending | tooling-v2.yml probe + the test's photo | | Free to Use and Reuse / no known restrictions only |
| Smithsonian Open Access fetcher (CC0 only) | asset source | pending | tooling-v2.yml probe | | needs SI_API_KEY (api.data.gov) for real use |
| Wikimedia Commons fetcher | asset source | pending | tooling-v2.yml probe | | PD / CC0 / CC BY / CC BY-SA; attribution stored |
| Internet Archive Prelinger fetcher (public domain only) | asset source | pending | tooling-v2.yml probe | | |
| the other 21 vendored HyperFrames items | block | not tested | — | | port or CLI-render on first use, each with its own test |
