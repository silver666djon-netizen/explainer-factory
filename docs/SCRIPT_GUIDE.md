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

## Retention rules (non-negotiable)

- **First 30 s = three 10-second beats:** (1) prove the title with one concrete example,
  (2) why it matters to *this* viewer, (3) a one-line roadmap / open loop ("by the end you'll see…").
  No greetings, no channel intro. First payoff before 0:30. The renderer cuts faster here (≤1.8 s shots).
- **Something changes every 1–3 s; a surprise every 20–30 s** (stat, chart, doc, comic, gag, kinetic).
  Never two minutes of the same visual type.
- **Open loop every 2–3 minutes** ("but the strangest result came from a clothing catalog…").
- **Best moment at about two-thirds** of the runtime.
- **Humour:** dry British wit + one gag every 1–2 minutes — comic reaction panels with bubbles,
  the fake 1950s ad (`ad` badge/slogan), understatement ("Retailers noticed. Retailers always notice.").
- **Punch-ins** (`punch`: words) on 1–3 key words per minute; **kinetic** beats for the 2–4 lines
  the viewer should remember; **doc** highlighter for every cited study.
- End with a payoff of the cold open and a tease of the next episode (end-screen space).
- Every episode, topic, angle, heroes, scenes and Shorts are **agreed with Klot first** (options →
  his choice → script). Don't render an episode he hasn't approved.

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
- `doc` — Vox-style paper clipping with a yellow highlighter sweep:
  `{ "source", "headline", "body" (your paraphrase, label it "Summary ·"), "highlight" (exact part of body), "at" }`.
- `kinetic` — the narration's words slam in as they are spoken: `{ "bg": "paper|ink|red|green" }`;
  mark accent words in `text` with `*stars*`. Keep it to 2–6 words.
- `ad` (on image beats) — the fake 1950s ad gag: `{ "badge", "badge_x", "badge_y", "slogan", "slogan_y" }`.
- `punch` (on any beat) — list of words that get a quick zoom punch + hit sound.

### Channel props (code-drawn, identical every episode)

- `casefile` — `{ "mode": "open", "number": "002", "title": "The casino", "inside": [lines] }` at the start;
  `{ "mode": "closed", ..., "stamp": "Case closed", "lines": ["Guilty: your brain", "Accomplice: plastic"], "stamp_at": 0.5 }` at the end.
- `mugshot` — a "suspect" (object or idea): `{ "prompt": "<picture of the suspect>", "suspect": { "number", "name", "alias", "last_seen", "notes", "tag" } }`.
- `roulette` — American wheel spins, stops, marker circles 0 and 00: `{ "roulette": { "spin", "mark_at", "note" } }`.
- `maze` — blueprint casino floor, marker traces YOU → EXIT under a magnifier: `{ "maze": { "title", "note", "seed" } }`.
- `newsreel: true` (or a label string) on image/reuse/photo — 1950s film look with a "Reconstruction" label.
  Never present a generated image as a real historical photo.
- `counter` (on any beat) — damage counter card: `{ "from", "to", "prefix": "-$", "decimals", "label", "at", "dur" }`.
  Only real arithmetic or clearly stated example assumptions.

### Characters and voices

- `characters`: `{ "larry": "a cheerful middle-aged man in a loud yellow checked jacket and a red fedora" }` —
  write `{larry}` in prompts; the description is pasted in so he is recognisable by his clothes.
- `voices`: `{ "house": { "lang_code": "a", "voice": "am_onyx", "speed": 0.92 } }`; a beat with
  `"voice": "house"` is spoken by that voice and its captions are gold. The narrator (the Inspector) is never on screen.

### Scene rules — what AI pictures do well (rule D)

- **Good:** single objects and products, interiors, one character in a mid shot, stylised scenes,
  calm moments. **Weak:** hands in close-up, crowds, two or more interacting people, text/numbers,
  exact counts of small objects, fast action. Write scenes around the strengths.
- Hands: show them only at mid distance or holding one simple object; never as the subject.
- Numbers, prices, labels → `on_screen`, `stat`, `chart`, `counter`, marker notes (code-drawn, always correct).
- History → real public-domain archive `photo` where possible, `newsreel` reconstruction otherwise.
- Every long episode: 8–15 `"hero": true` image beats (cold open, chapter openers, thumbnail subject).
  These go into the prompt pack for Google Flow / Grok; hand-made files replace the automatic frame.
- 3–5 `clip` beats per episode for the most important moments (Grok Imagine 6–10 s), each with
  `"grok": {"action", "camera", "secondary", "sound", "seconds"}` — one subject, one action, one camera move,
  affirmative wording, material/texture words. Until the clip file arrives, the still frame is used.

### Workflow per episode

1. Script approved → commit `script.json` → **Storyboard** workflow: all frames + depth maps, contact sheets
   and prompt pack in Telegram (release `frames-<slug>`).
2. Claude reviews every frame; Klot reviews the sheets. Bad frames: `/redo b17 c03` in the bot
   (or Storyboard workflow with `redo`). Hand-made frames/clips: send to the bot as a FILE captioned `b17`.
3. "✅ Раскадровка ок" button (or `/approve`) → **Render episode** → video + Shorts in Telegram.

### Image prompt rules

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
