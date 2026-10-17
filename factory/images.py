"""Image generation: Gemini (Nano Banana) or Cloudflare Workers AI (Flux), on-disk cache, hand-made overrides,
offline placeholders."""
from __future__ import annotations

import base64
import hashlib
import io
import random
import time
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

from .config import env, hex_to_rgb, resolve_font


class ImageQuotaError(RuntimeError):
    pass


def full_prompt(cfg: dict, prompt: str, style_name: str = "ad") -> str:
    style = cfg["style"]
    variant = (style.get("variants") or {}).get(style_name) or {}
    suffix = variant.get("prompt_suffix", style.get("prompt_suffix", ""))
    text = f"{style.get('prompt_prefix', '')}{prompt.strip().rstrip('.')}. {suffix}".strip()
    return text[:2000]


def provider(cfg: dict) -> str:
    """'gemini' when a Gemini key is available (and allowed), otherwise 'cloudflare'."""
    want = (cfg["images"].get("provider") or "auto").lower()
    if want == "cloudflare":
        return "cloudflare"
    if want in ("gemini", "auto") and env("GEMINI_API_KEY"):
        return "gemini"
    return "cloudflare"


def model_id(cfg: dict) -> str:
    return cfg["images"].get("gemini_model", "gemini-nano-banana-2.1") if provider(cfg) == "gemini" else cfg["images"]["model"]


def _cache_name(cfg: dict, key: str, prompt: str, style_name: str = "ad", variant: int = 0) -> str:
    salt = f"|v{variant}" if variant else ""
    digest = hashlib.sha1(f"{model_id(cfg)}|{full_prompt(cfg, prompt, style_name)}{salt}".encode()).hexdigest()[:10]
    safe_key = "".join(c if c.isalnum() or c in "-_." else "_" for c in key)
    return f"{safe_key}-{digest}.png"


def _find_image_b64(obj):
    """Walks any JSON response and returns the first base64 image payload."""
    if isinstance(obj, dict):
        mime = str(obj.get("mime_type") or obj.get("mimeType") or "")
        data = obj.get("data")
        if isinstance(data, str) and len(data) > 1000 and (mime.startswith("image/") or obj.get("type") in ("image", "output_image")):
            return data
        for k in ("inlineData", "inline_data", "output_image", "image"):
            if isinstance(obj.get(k), dict):
                got = _find_image_b64(obj[k])
                if got:
                    return got
        for v in obj.values():
            got = _find_image_b64(v)
            if got:
                return got
    elif isinstance(obj, list):
        for v in obj:
            got = _find_image_b64(v)
            if got:
                return got
    return None


def _gemini(cfg: dict, prompt: str, style_name: str = "ad", refs: list[Path] | None = None, variant: int = 0) -> Image.Image:
    key = env("GEMINI_API_KEY").strip()
    icfg = cfg["images"]
    model = icfg.get("gemini_model", "gemini-nano-banana-2.1")
    text = full_prompt(cfg, prompt, style_name)
    extra = (icfg.get("gemini_quality_suffix") or "").strip()
    if extra:
        text = f"{text.rstrip('. ')}. {extra}"
    if refs:
        text += " Keep the character's face, outfit and colours exactly as in the reference portrait."
    if variant:
        text += f" (alternative take {variant})"
    parts = [{"type": "text", "text": text}]
    legacy_parts = [{"text": text}]
    for ref in (refs or [])[:4]:
        im = Image.open(ref).convert("RGB")
        im.thumbnail((1024, 1024))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=90)
        b64 = base64.b64encode(buf.getvalue()).decode()
        parts.append({"type": "image", "mime_type": "image/jpeg", "data": b64})
        legacy_parts.append({"inline_data": {"mime_type": "image/jpeg", "data": b64}})
    aspect = icfg.get("aspect_ratio", "16:9")
    size = icfg.get("gemini_size", "1K")
    headers = {"x-goog-api-key": key, "Content-Type": "application/json"}
    attempts = [
        ("https://generativelanguage.googleapis.com/v1beta/interactions",
         {"model": model, "input": parts,
          "response_format": {"type": "image", "mime_type": "image/png", "aspect_ratio": aspect, "image_size": size}}),
        (f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
         {"contents": [{"parts": legacy_parts}],
          "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": aspect, "imageSize": size}}}),
    ]
    last = ""
    for url, body in attempts:
        delay = 5.0
        for _try in range(4):
            try:
                r = requests.post(url, headers=headers, json=body, timeout=180)
            except requests.RequestException as exc:
                last = str(exc)
                time.sleep(delay)
                delay *= 2
                continue
            if r.status_code == 200:
                b64 = _find_image_b64(r.json())
                if b64:
                    return Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")
                last = f"no image in response: {r.text[:300]}"
                if "safety" in r.text.lower() or "blocked" in r.text.lower():
                    raise _SafetyFilter(last)
                break
            last = f"HTTP {r.status_code}: {r.text[:400]}"
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(delay)
                delay *= 2
                continue
            if r.status_code in (400, 404) and url.endswith("/interactions"):
                break  # try the classic endpoint
            if r.status_code in (401, 403):
                raise RuntimeError(f"Gemini rejected the key or region/billing ({last})")
            break
    raise RuntimeError(f"Gemini image generation failed: {last}")


def generate(cfg: dict, prompt: str, style_name: str = "ad", refs: list[Path] | None = None, variant: int = 0) -> Image.Image:
    if provider(cfg) == "gemini":
        last: Exception | None = None
        for prefix in SAFE_PREFIXES:
            try:
                return _gemini(cfg, prefix + prompt, style_name, refs, variant)
            except _SafetyFilter as exc:
                last = exc
        raise RuntimeError(f"Image prompt keeps getting blocked, please reword it: {prompt!r} ({last})")
    return _cloudflare(cfg, prompt if not variant else f"{prompt}, alternative composition {variant}", style_name, refs)


SAFE_PREFIXES = ["", "Wholesome family-friendly vintage illustration, fully clothed characters, ",
                 "Simple wholesome children's-book style picture, "]


def _cloudflare(cfg: dict, prompt: str, style_name: str = "ad", refs: list[Path] | None = None) -> Image.Image:
    """Tries the prompt; if the provider's safety filter misfires, retries with softer wording."""
    last: Exception | None = None
    for prefix in SAFE_PREFIXES:
        try:
            return _cloudflare_once(cfg, prefix + prompt, style_name, refs)
        except _SafetyFilter as exc:
            last = exc
            print(f"  safety filter misfire, retrying with softer wording: {prompt[:60]}")
    raise RuntimeError(f"Image prompt keeps tripping the safety filter, please reword it: {prompt!r} ({last})")


class _SafetyFilter(RuntimeError):
    pass


def _cloudflare_once(cfg: dict, prompt: str, style_name: str = "ad", refs: list[Path] | None = None) -> Image.Image:
    account = env("CLOUDFLARE_ACCOUNT_ID")
    token = env("CLOUDFLARE_API_TOKEN")
    if not account or not token:
        raise RuntimeError("CLOUDFLARE_ACCOUNT_ID / CLOUDFLARE_API_TOKEN are not set")
    model = cfg["images"]["model"]
    url = f"https://api.cloudflare.com/client/v4/accounts/{account.strip()}/ai/run/{model}"
    text_prompt = full_prompt(cfg, prompt, style_name)
    multipart = "flux-2" in model  # FLUX.2 models take multipart form data (and optional reference images)
    delay = 4.0
    last_error = ""
    for _attempt in range(6):
        try:
            headers = {"Authorization": f"Bearer {token.strip()}"}
            if multipart:
                fields = {
                    "prompt": (None, text_prompt),
                    "width": (None, str(int(cfg["images"].get("width", 1280)))),
                    "height": (None, str(int(cfg["images"].get("height", 720)))),
                    "seed": (None, str(int(hashlib.sha1(text_prompt.encode()).hexdigest()[:6], 16))),
                }
                for n, ref in enumerate((refs or [])[:4]):
                    buf = io.BytesIO()
                    im = Image.open(ref).convert("RGB")
                    im.thumbnail((500, 500))
                    im.save(buf, "PNG")
                    fields[f"input_image_{n}"] = (f"ref{n}.png", buf.getvalue(), "image/png")
                resp = requests.post(url, headers=headers, files=fields, timeout=180)
            else:
                body = {"prompt": text_prompt, "steps": int(cfg["images"].get("steps", 4))}
                resp = requests.post(url, headers=headers, json=body, timeout=120)
        except requests.RequestException as exc:
            last_error = str(exc)
            time.sleep(delay)
            delay *= 2
            continue
        text = resp.text[:500]
        if resp.status_code == 200:
            data = resp.json()
            image_b64 = (data.get("result") or {}).get("image")
            if not image_b64:
                raise RuntimeError(f"Cloudflare returned no image: {text}")
            return Image.open(io.BytesIO(base64.b64decode(image_b64))).convert("RGB")
        lowered = text.lower()
        if "allocation" in lowered or "quota" in lowered or "neurons" in lowered:
            raise ImageQuotaError(f"Cloudflare free daily limit reached: {text}")
        if resp.status_code in (401, 403):
            raise RuntimeError(f"Cloudflare rejected the token/account (HTTP {resp.status_code}): {text}")
        if resp.status_code == 400 and ("nsfw" in lowered or "8007" in lowered or "flagged" in lowered or "3030" in lowered):
            raise _SafetyFilter(text)
        if resp.status_code == 400:
            raise RuntimeError(f"Cloudflare rejected the prompt (HTTP 400): {text}")
        last_error = f"HTTP {resp.status_code}: {text}"
        time.sleep(delay)
        delay *= 2
    raise RuntimeError(f"Cloudflare image generation failed after retries: {last_error}")


def placeholder(cfg: dict, key: str, prompt: str, size: int = 1024) -> Image.Image:
    """Deterministic stand-in image so the whole montage can be tested without any API."""
    pal = [hex_to_rgb(v) for v in cfg["style"]["palette"].values()]
    rnd = random.Random(key)
    bg, fg = rnd.sample(pal, 2)
    img = Image.new("RGB", (size, size), bg)
    draw = ImageDraw.Draw(img)
    for _ in range(14):
        color = rnd.choice(pal)
        x, y, r = rnd.randint(0, size), rnd.randint(0, size), rnd.randint(40, 260)
        draw.ellipse((x - r, y - r, x + r, y + r), fill=color)
    for gx in range(0, size, 128):  # grid makes camera motion visible
        draw.line((gx, 0, gx, size), fill=fg, width=3)
        draw.line((0, gx, size, gx), fill=fg, width=3)
    font = ImageFont.truetype(resolve_font(cfg["fonts"]["headline"]), 72)
    small = ImageFont.truetype(resolve_font(cfg["fonts"]["body"]), 30)
    draw.rectangle((60, 380, size - 60, 650), fill=pal[0])
    draw.text((size // 2, 470), key.upper(), font=font, fill=pal[1], anchor="mm")
    words, line, lines = prompt.split(), "", []
    for word in words:
        if len(line) + len(word) > 48:
            lines.append(line)
            line = ""
        line += word + " "
    lines.append(line)
    for i, ln in enumerate(lines[:2]):
        draw.text((size // 2, 555 + i * 38), ln.strip(), font=small, fill=pal[1], anchor="mm")
    return img


def ensure_images(cfg: dict, prompts: dict[str, dict], cache_dir: Path, offline: bool, log=print) -> dict[str, Path]:
    """Generate (or reuse from cache) every image. Returns key -> file path."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    limit = int(cfg["images"].get("max_per_episode", 150))
    if len(prompts) > limit:
        raise RuntimeError(f"Episode needs {len(prompts)} images, limit is {limit}. Reuse images or raise the limit.")
    out: dict[str, Path] = {}
    made = 0
    variants = _variants(prompts)
    for key, spec in prompts.items():
        prompt, style_name = spec["prompt"], spec.get("style", "ad")
        manual = _manual_image(spec.get("episode_dir"), key)
        if manual is not None:  # hand-made frame (Google Flow, Grok…) dropped into episodes/<slug>/images/
            out[key] = manual
            log(f"  image {key}: hand-made file {manual.name}")
            continue
        variant = int(variants.get(key, 0))
        path = cache_dir / _cache_name(cfg, key, prompt, style_name, variant)
        if not path.exists():
            refs = [Path(p) for p in spec.get("refs") or [] if Path(p).exists()]
            img = placeholder(cfg, key, prompt) if offline else generate(cfg, prompt, style_name, refs, variant)
            img.save(path)
            made += 1
            log(f"  image {key}: generated ({made})")
        out[key] = path
    log(f"Images ready: {len(out)} total, {made} new")
    return out


def _variants(prompts: dict[str, dict]) -> dict[str, int]:
    """episodes/<slug>/frames.json -> {"variants": {"b17": 2}}: a 'redo' bumps the number."""
    import json
    dirs = {spec.get("episode_dir") for spec in prompts.values() if spec.get("episode_dir")}
    for d in dirs:
        f = Path(d) / "frames.json"
        if f.exists():
            return json.loads(f.read_text(encoding="utf-8")).get("variants", {})
    return {}


def _manual_image(episode_dir: str | None, key: str) -> Path | None:
    if not episode_dir:
        return None
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        cand = Path(episode_dir) / "images" / f"{key}{ext}"
        if cand.exists():
            return cand
    return None


def is_archive_photo(path: Path) -> bool:
    return Path(path).name.startswith("photo-")


def ensure_photos(cfg: dict, photos: dict[str, dict], cache_dir: Path, offline: bool, log=print) -> dict[str, Path]:
    """Download archive photos (public domain). If a download fails, fall back to an illustration."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    out: dict[str, Path] = {}
    for key, spec in photos.items():
        digest = hashlib.sha1(spec["url"].encode()).hexdigest()[:10]
        path = cache_dir / f"photo-{key}-{digest}.png"
        fallback = cache_dir / f"illus-{key}-{digest}.png"
        if fallback.exists() and not path.exists():
            out[key] = fallback
            continue
        if not path.exists():
            if offline:
                placeholder(cfg, key, "ARCHIVE PHOTO " + spec["credit"]).convert("L").convert("RGB").save(path)
            else:
                try:
                    resp = requests.get(spec["url"], timeout=60, headers={
                        "User-Agent": "ExplainerFactory/1.0 (YouTube education channel; contact via GitHub)"})
                    resp.raise_for_status()
                    Image.open(io.BytesIO(resp.content)).convert("RGB").save(path)
                    log(f"  photo {key}: downloaded")
                except Exception as exc:  # noqa: BLE001
                    if not spec.get("fallback_prompt"):
                        raise RuntimeError(f"Photo {key} could not be downloaded ({exc}) and has no fallback_prompt") from exc
                    log(f"  photo {key}: download failed ({exc}); using illustration instead")
                    generate(cfg, spec["fallback_prompt"]).save(fallback)
                    out[key] = fallback
                    continue
        out[key] = path
    return out
