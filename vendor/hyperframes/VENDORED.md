# HyperFrames (vendored subset)

Source: https://github.com/heygen-com/hyperframes, commit `6161ae740a34b341aba98f2fcd4583f79a4f1332` (2026-11-07),
licensed under the Apache License 2.0 (`LICENSE` in this folder, unchanged). Upstream credits: `UPSTREAM_CREDITS.md`.
Copyright HeyGen and the HyperFrames contributors.

Vendored for CoinSense tooling v2 (Klot, Nov 7). Only the items below, each as upstream ships it (`<name>.html`,
`registry-item.json`, README and bundled assets). Not vendored: the `demo*` host pages and their demo pictures.
Nothing here is modified; our changes live in our own code (see "Ports").

Blocks (`registry/blocks/`): split-flap-board, news-ticker, us-map-flow, world-map, data-chart, flowchart,
freeze-frame-dressing, editorial-flash-overlay, hw-write-title, hw-scribble-transition.

Components (`registry/components/`): number-wheel, slot-machine-roll, count-up, strikethrough-replace,
marker-highlight, vox-annotate, whiteboard-ink, torn-paper-rip, paper-collage-reveal, ink-bleed-reveal,
halftone-dissolve, grain-overlay, before-after-wipe.

Third-party pieces these files load at run time (from the jsDelivr / Google Fonts CDNs, not vendored):
- GSAP 3.14.2 (GSAP Standard "no charge" licence, https://gsap.com/standard-license; commercial use allowed) — most items.
- d3 7, topojson-client 3.1.0 (ISC), us-atlas 3 / world-atlas 2 (ISC; Natural Earth / US Census data, public domain) — us-map-flow, world-map.
- Google Fonts (OFL) — data-chart, flowchart, the maps. hw-write-title bundles Caveat 700 (OFL 1.1) in `assets/fonts`.
Brand check: no third-party brand, logo or trademark in any vendored item (the only outside names are the CDNs above).

## Ports (our code, Remotion)
- split-flap-board -> `pilot/remotion/src/tooling/SplitFlap.tsx` (pure function of time; same drum walk and flap law).
- hw-scribble-transition -> `pilot/remotion/src/tooling/ScribbleWipe.tsx` (its GSAP timeline written out per frame: same tweens, eases, staggers; a first version through @remotion/gsap stayed on one pose in renders on the Actions runner).
The rest: port on first use (R50: its own test render passes QC first). Fallback for any item: the hyperframes CLI
(`npx hyperframes@0.9.19 render <dir> --format webm`, transparent) composited as an `<OffthreadVideo transparent>`.
Telemetry is always off: `HYPERFRAMES_NO_TELEMETRY=1` + `DO_NOT_TRACK=1` + `hyperframes telemetry disable`; never run
`hyperframes events` or `feedback` (the skills mention them).
