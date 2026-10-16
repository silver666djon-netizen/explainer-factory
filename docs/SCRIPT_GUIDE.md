# CoinSense — script authoring guide

This is the contract for every `episodes/<NNNN-slug>/script.json`. Whoever writes an episode
(Claude in a scheduled session, or a human) follows it. Validate before committing:

```bash
python -m factory check episodes/<NNNN-slug>
```

## Channel

- **CoinSense** — the psychology of money: why our brains misjudge prices, deals, risk and value.
- English, documentary British narrator (Kokoro `bm_george`), calm, curious, slightly wry.
- Look: 1950s print advertising illustrations + flat infographics + a red "investigator marker"
  that circles and annotates the trick + 1950s comic panels + real archive photos.
- Rhythm: something changes on screen every 1–3 s (the renderer splits long beats automatically,
  but write short beats anyway).

## Episode shape (long video, 8–12 min ≈ 1,250–1,850 spoken words)

1. **Cold open (0:00–0:30)** — a concrete, surprising everyday moment + the question. No "welcome to".
2. **Chapter title cards** (`"type": "title"`) between 4–6 sections. Each section gets a
   `"section"` name; these become YouTube chapters automatically.
3. **Evidence** — at least two real, named studies or documented cases per episode, listed in
   `"sources"` (author, year, title, venue). Never invent numbers, quotes or studies. If unsure,
   leave it out. Paraphrase findings; round only when the source does.
4. **Mechanism** — explain *why* the brain does it, in plain words, with one everyday analogy.
5. **Defence** — a practical rule the viewer can use today.
6. **Closing line** that pays off the cold open.

Two long episodes per week, each with **6 Shorts** (~2 Shorts per day).

## Beats

Each beat = 1–3 sentences of narration, ~4–9 seconds. Fields:

| field | meaning |
|---|---|
| `id` | unique, e.g. `b07`, `t02`, `c01` |
| `section` | chapter name (copy it onto every beat of that chapter) |
| `text` | narration as shown in captions |
| `say` | optional: how the narrator should pronounce it (write numbers and prices in words: "nine ninety-nine") — use whenever `text` contains digits, `$`, `%`, abbreviations |
| `on_screen` | optional short label card (≤ 5 words), e.g. `"$39 beat $34"` |
| `bubble` | optional comic speech bubble `{ "text", "x", "y", "tail": "left|right|none", "at" }` — x/y are 0..1 of the frame; keep it in empty space |
| `sfx` | optional `whoosh`, `pop`, `tick`, `thud`, `none` |
| `visual` | see below |

### Visual types

- `image` — generated illustration. `prompt` or `prompts` (2–3 prompts = several pictures in one beat).
  Optional `style`: `ad` (default, 1950s print ad) or `comic` (1950s comic panel).
  Optional `motion`: `zoom_in`, `zoom_out`, `pan_left`, `pan_right`, `pan_up`, `pan_down`, `drift`, `static`.
  Optional `marks` (red marker, see below).
- `reuse` — `{ "beat": "<image or photo beat id>", "index": 0, "motion": ... }` — reuses a picture (saves the image budget; Shorts should mostly reuse).
- `photo` — real archive photo: `{ "url", "credit", "fallback_prompt" }`. **Only public-domain or
  CC0 sources** (Library of Congress FSA/OWI, NARA, Wikimedia Commons PD files). `credit` is
  printed in the description. `fallback_prompt` is used (as an illustration, never styled as a photo)
  if the download fails. Never present an AI image as a historical photo.
- `chart` — `{ "kind": "bar|line", "title", "labels", "values", "unit", "highlight", "decimals" }`.
  Real data only, from the cited sources, or plain arithmetic (like $2.00 / $2.99 / $3.00).
- `stat` — big number that counts up: `{ "value", "prefix", "suffix", "label", "decimals" }`.
- `title` — chapter card `{ "text" }`.

### Image prompt rules (Flux schnell)

- One clear subject, **centered in the frame**, simple background. Say "centered".
- Describe material and texture ("brass cash register", "paper price tag with a red border").
- Affirmative phrasing only (negatives are ignored).
- **No text, numbers, logos or prices inside images** — image models garble letters. Put numbers in
  `on_screen`, `stat`, `chart` or marker notes instead.
- Hands and crowds render poorly: prefer objects, single people, mid shots.
- The channel style suffix is appended automatically — don't repeat it.
- Budget: ≤ 150 new images per episode (free tier ≈ 170/day). Aim for 60–100 per long video.

### Red marker (`marks`)

Drawn by code over the picture (moves with the camera). Coordinates are 0..1 of the picture;
the camera shows roughly the central 80%, so keep marks within 0.15–0.85.

```json
"marks": [
  { "type": "circle", "x": 0.5, "y": 0.5, "w": 0.4, "h": 0.4, "at": 0.6, "text": "the trick", "text_y": 0.75 },
  { "type": "arrow", "x": 0.5, "y": 0.45, "from_x": 0.2, "from_y": 0.2, "at": 1.2 },
  { "type": "underline", "x": 0.5, "y": 0.7, "w": 0.35 },
  { "type": "cross" }, { "type": "check" }
]
```

`at` = seconds after the narration of the beat starts. Since generated subjects are centered,
circle/arrow the center. Use marks 1–3 times per minute — it is the channel's signature.

## Shorts (6 per long episode)

- 25–45 seconds, 5–8 beats, hook in the first line (a question or a shocking fact).
- **Loop**: the last line must flow back into the first ("…and that's exactly why every price ends in" → "Why does every price end in ninety-nine?").
- Mostly `reuse` visuals from the long episode; captions are big and centered automatically.
- `title` ≤ 60 characters + `#shorts`.

## Metadata

`title` (≤ 70 chars, curiosity + clarity), `description` (2–3 sentences), `tags` (5–10),
`sources` (required), `thumbnail: { "beat", "text" }` (≤ 4 words, punchy).
