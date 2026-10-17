"""Prompt pack for hand-made frames (Google Flow / Grok image) and live clips (Grok Imagine).

Beats marked "hero": true get a Flow image prompt; beats of type "clip" (or with "grok": {...}) get a
Grok Imagine motion prompt that follows the channel's rules:
  preservation block -> one action -> one camera move -> one secondary movement -> AUDIO block,
  affirmative phrasing only, material/texture words, 6–10 s, one subject.
"""
from __future__ import annotations

from pathlib import Path

from .images import full_prompt

DEFAULT_SOUND = "AUDIO: no music. No voice. Quiet room tone only (the narration and sound effects are added later)."


def _image_prompt(cfg: dict, visual: dict, prompt: str) -> str:
    text = full_prompt(cfg, prompt, visual.get("style", "ad"))
    extra = (cfg["images"].get("gemini_quality_suffix") or "").strip()
    return f"{text.rstrip('. ')}. {extra} Aspect ratio 16:9.".strip()


def _grok_prompt(episode: dict, visual: dict) -> str:
    g = visual.get("grok") or {}
    chars = episode.get("characters") or {}
    keep = []
    for name in visual.get("_chars") or []:
        if name in chars:
            keep.append(f"{name.capitalize()} stays exactly as in the image: {chars[name]}")
    preserve = ("PRESERVE: the frame stays exactly as the uploaded image — same composition, same colours "
                "(cream, money green, tomato red, ink black), same 1950s print-advertisement style with halftone dots "
                "and warm paper grain. " + " ".join(keep)).strip()
    action = "ACTION: " + g.get("action", "one small natural movement of the main subject")
    camera = "CAMERA: " + g.get("camera", "slow steady push-in")
    secondary = "SECONDARY: " + g.get("secondary", "soft dust motes drifting in the light")
    sound = g.get("sound", DEFAULT_SOUND)
    if not sound.upper().startswith("AUDIO"):
        sound = "AUDIO: " + sound
    length = g.get("seconds", 8)
    return f"{preserve}\n{action}\n{camera}\n{secondary}\n{sound}\nLength: {length} seconds."


def write_pack(episode: dict, cfg: dict) -> Path | None:
    lines = [f"# Prompt pack — {episode['slug']}", "",
             "Готовые кадры присылай боту **как файл** с подписью = номер кадра (например `b17`).",
             "Картинки для Flow — формат 16:9. Видео из Grok — 6–10 секунд.", ""]
    n_img = n_clip = 0
    for b in episode["beats"]:
        v = b["visual"]
        if v.get("hero") and v.get("type") in ("image", "clip"):
            prompts = v.get("prompts") or [v.get("prompt")]
            for i, p in enumerate(prompts):
                key = b["id"] if i == 0 else f"{b['id']}.{i}"
                lines += [f"## 🖼 {key} — картинка (Flow / Grok)", f"_Текст в ролике: {b['text'][:110]}_", "```", _image_prompt(cfg, v, p), "```", ""]
                n_img += 1
        if v.get("type") == "clip" or v.get("grok"):
            lines += [f"## 🎞 {b['id']} — живая вставка (Grok Imagine: сначала картинка {b['id']}, потом этот промпт)",
                      f"_Текст в ролике: {b['text'][:110]}_", "```", _grok_prompt(episode, v), "```", ""]
            n_clip += 1
    if not n_img and not n_clip:
        return None
    path = Path(episode["_dir"]) / "prompt_pack.md"
    lines.insert(2, f"Ключевых кадров: {n_img}, живых вставок: {n_clip}.")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
