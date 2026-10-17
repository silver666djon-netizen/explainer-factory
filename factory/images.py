"""Image generation: Cloudflare Workers AI (Flux) with an on-disk cache, plus offline placeholders."""
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


def _cache_name(cfg: dict, key: str, prompt: str, style_name: str = "ad") -> str:
    digest = hashlib.sha1(f"{cfg['images']['model']}|{full_prompt(cfg, prompt, style_name)}".encode()).hexdigest()[:10]
    safe_key = "".join(c if c.isalnum() or c in "-_." else "_" for c in key)
    return f"{safe_key}-{digest}.png"


SAFE_PREFIXES = ["", "Wholesome family-friendly vintage illustration, fully clothed characters, ",
                 "Simple wholesome children's-book style picture, "]


def _cloudflare(cfg: dict, prompt: str, style_name: str = "ad") -> Image.Image:
    """Tries the prompt; if the provider's safety filter misfires, retries with softer wording."""
    last: Exception | None = None
    for prefix in SAFE_PREFIXES:
        try:
            return _cloudflare_once(cfg, prefix + prompt, style_name)
        except _SafetyFilter as exc:
            last = exc
            print(f"  safety filter misfire, retrying with softer wording: {prompt[:60]}")
    raise RuntimeError(f"Image prompt keeps tripping the safety filter, please reword it: {prompt!r} ({last})")


class _SafetyFilter(RuntimeError):
    pass


def _cloudflare_once(cfg: dict, prompt: str, style_name: str = "ad") -> Image.Image:
    account = env("CLOUDFLARE_ACCOUNT_ID")
    token = env("CLOUDFLARE_API_TOKEN")
    if not account or not token:
        raise RuntimeError("CLOUDFLARE_ACCOUNT_ID / CLOUDFLARE_API_TOKEN are not set")
    url = f"https://api.cloudflare.com/client/v4/accounts/{account.strip()}/ai/run/{cfg['images']['model']}"
    body = {"prompt": full_prompt(cfg, prompt, style_name), "steps": int(cfg["images"].get("steps", 4))}
    delay = 4.0
    last_error = ""
    for _attempt in range(6):
        try:
            resp = requests.post(url, headers={"Authorization": f"Bearer {token.strip()}"}, json=body, timeout=120)
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
        if resp.status_code == 400 and ("nsfw" in lowered or "8007" in lowered):
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
    for key, spec in prompts.items():
        prompt, style_name = spec["prompt"], spec.get("style", "ad")
        path = cache_dir / _cache_name(cfg, key, prompt, style_name)
        if not path.exists():
            img = placeholder(cfg, key, prompt) if offline else _cloudflare(cfg, prompt, style_name)
            img.save(path)
            made += 1
            log(f"  image {key}: generated ({made})")
        out[key] = path
    log(f"Images ready: {len(out)} total, {made} new")
    return out


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
                    _cloudflare(cfg, spec["fallback_prompt"]).save(fallback)
                    out[key] = fallback
                    continue
        out[key] = path
    return out
