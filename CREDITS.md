# Credits

Third-party code, models and assets used by CoinSense. Per-asset licences for everything that appears in a video are in
[docs/ASSET_LICENSES.md](docs/ASSET_LICENSES.md).

## Code
- **HyperFrames** by HeyGen — Apache License 2.0. A subset of its registry is vendored in `vendor/hyperframes/`
  (licence, upstream credits and the list in `vendor/hyperframes/VENDORED.md`); `SplitFlap.tsx` and `ScribbleWipe.tsx`
  in `pilot/remotion/src/tooling/` are ports of its split-flap-board and hw-scribble-transition blocks.
- **Remotion** 4.0.541 and its packages — Remotion License (free for individuals and companies of up to 3 people;
  a company licence is needed above that), some packages MIT (see each package). `@remotion/sfx` is not used.
- **GSAP** 3.14.2 — GSAP Standard "no charge" licence (commercial use allowed).
- **lottie-web** 5.12.2 — MIT. **three** 0.170.0 — MIT. **@react-three/fiber** 8.17.10 — MIT.
- Agent skills in `.claude/skills/`: Remotion skills (remotion-dev/skills) and HyperFrames skills (heygen-com/hyperframes,
  Apache-2.0), see `.claude/skills/SOURCES.md`.

## Services (generated assets; the model is named per asset in docs/ASSET_LICENSES.md)
ElevenLabs (voice, Sound Effects, Music), OpenAI gpt-audio via OpenRouter (EN narration), xAI Grok Imagine (clips by Klot),
Google Nano Banana 2 via OpenRouter (Ep.4 v1 pictures), Lyria via OpenRouter (music library).

## Archives
Library of Congress (Free to Use and Reuse / no known restrictions), Smithsonian Open Access (CC0), Wikimedia Commons
(public domain / CC with attribution), Internet Archive — Prelinger Archives (public domain). Fetchers: `tools/archives.py`.
