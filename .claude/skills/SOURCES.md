# Agent skills in this repo

Added for tooling v2 (Klot, Nov 7). Used by Claude Code sessions working in this repo.

| skill | source | version | licence |
|---|---|---|---|
| remotion-best-practices, remotion-captions, remotion-markup, remotion-render | https://github.com/remotion-dev/skills (`npx skills add remotion-dev/skills`) | commit a2824c67f8b4585c294a8101db9f9f0ad3c643f8 (2026-11-05), for Remotion 4.0.541 | no licence file upstream; Remotion's own published agent skills, copied unchanged |
| hyperframes, hyperframes-cli, hyperframes-registry, media-use (the HyperFrames core set, `npx hyperframes skills update`) | https://github.com/heygen-com/hyperframes `skills/` | commit 6161ae740a34b341aba98f2fcd4583f79a4f1332 (2026-11-07) | Apache-2.0 (vendor/hyperframes/LICENSE) |

Changed here (Apache-2.0 §4b notice): in the four HyperFrames SKILL.md files the "Usage beacon" line (which tells an
agent to send telemetry) is replaced by "telemetry is off", and the post-render `feedback --rating` step is removed.
Everything else is as upstream. To refresh: copy the folders again from the sources above and re-apply these two edits.

Not copied: media-use's bundled sound effects (`audio/assets/sfx/*.mp3`, Pixabay). No sound enters a video without its own row in
docs/ASSET_LICENSES.md (R50); if one of them is wanted, add it with its Pixabay page and licence first.
