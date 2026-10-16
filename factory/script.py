"""Episode script format (episodes/<slug>/script.json) — loading and validation."""
from __future__ import annotations

import json
from pathlib import Path

MOTIONS = {"zoom_in", "zoom_out", "pan_left", "pan_right", "pan_up", "pan_down", "drift", "static"}
VISUAL_TYPES = {"image", "chart", "title", "reuse", "stat", "photo"}
MARK_TYPES = {"circle", "underline", "arrow", "cross", "check"}
STYLES = {"ad", "comic"}
CHART_KINDS = {"bar", "line"}
SFX = {"whoosh", "pop", "tick", "thud", "none"}


class ScriptError(ValueError):
    pass


def _check_visual(where: str, visual: dict, errors: list[str]) -> None:
    vtype = visual.get("type")
    if vtype not in VISUAL_TYPES:
        errors.append(f"{where}: visual.type must be one of {sorted(VISUAL_TYPES)}, got {vtype!r}")
        return
    motion = visual.get("motion")
    if motion is not None and motion not in MOTIONS:
        errors.append(f"{where}: motion must be one of {sorted(MOTIONS)}, got {motion!r}")
    if vtype == "image":
        prompts = visual.get("prompts") or ([visual["prompt"]] if visual.get("prompt") else [])
        if not prompts or not all(isinstance(p, str) and p.strip() for p in prompts):
            errors.append(f"{where}: image visual needs 'prompt' or non-empty 'prompts'")
    elif vtype == "chart":
        chart = visual.get("chart") or {}
        if chart.get("kind") not in CHART_KINDS:
            errors.append(f"{where}: chart.kind must be one of {sorted(CHART_KINDS)}")
        labels, values = chart.get("labels") or [], chart.get("values") or []
        if not labels or len(labels) != len(values):
            errors.append(f"{where}: chart.labels and chart.values must be non-empty and equal length")
        if not all(isinstance(v, (int, float)) for v in values):
            errors.append(f"{where}: chart.values must be numbers")
    elif vtype == "title":
        if not str(visual.get("text", "")).strip():
            errors.append(f"{where}: title visual needs 'text'")
    elif vtype == "reuse":
        if not visual.get("beat"):
            errors.append(f"{where}: reuse visual needs 'beat' (id of a long-video beat)")
    elif vtype == "stat":
        if not isinstance((visual.get("stat") or {}).get("value"), (int, float)):
            errors.append(f"{where}: stat visual needs stat.value (number)")
    elif vtype == "photo":
        if not str(visual.get("url", "")).startswith("http"):
            errors.append(f"{where}: photo visual needs 'url' (public-domain archive photo)")
        if not str(visual.get("credit", "")).strip():
            errors.append(f"{where}: photo visual needs 'credit' (source + licence)")
    if visual.get("style") is not None and visual["style"] not in STYLES:
        errors.append(f"{where}: style must be one of {sorted(STYLES)}")
    for mark in visual.get("marks") or []:
        if mark.get("type") not in MARK_TYPES:
            errors.append(f"{where}: mark type must be one of {sorted(MARK_TYPES)}")
        for key in ("x", "y", "w", "h", "from_x", "from_y", "text_x", "text_y"):
            if key in mark and not (isinstance(mark[key], (int, float)) and -0.2 <= mark[key] <= 1.2):
                errors.append(f"{where}: mark.{key} must be a number around 0..1")
    if visual.get("marks") and vtype not in ("image", "reuse", "photo"):
        errors.append(f"{where}: marks only work on image, reuse or photo visuals")


def _check_beats(prefix: str, beats: list, errors: list[str], seen: set[str]) -> None:
    if not isinstance(beats, list) or not beats:
        errors.append(f"{prefix}: 'beats' must be a non-empty list")
        return
    for i, beat in enumerate(beats):
        bid = beat.get("id") or f"{prefix}-{i + 1:02d}"
        beat["id"] = bid
        where = f"{prefix} beat {bid}"
        if bid in seen:
            errors.append(f"{where}: duplicate id")
        seen.add(bid)
        if not str(beat.get("text", "")).strip():
            errors.append(f"{where}: 'text' (narration) is empty")
        if beat.get("sfx") is not None and beat["sfx"] not in SFX:
            errors.append(f"{where}: sfx must be one of {sorted(SFX)}")
        bubble = beat.get("bubble")
        if bubble is not None and not str((bubble or {}).get("text", "")).strip():
            errors.append(f"{where}: bubble needs 'text'")
        if not isinstance(beat.get("visual"), dict):
            errors.append(f"{where}: 'visual' object is missing")
            continue
        _check_visual(where, beat["visual"], errors)


def load_episode(path: str | Path) -> dict:
    path = Path(path)
    if path.is_dir():
        path = path / "script.json"
    try:
        episode = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ScriptError(f"{path}: invalid JSON — {exc}") from exc

    errors: list[str] = []
    for key in ("slug", "title", "beats"):
        if not episode.get(key):
            errors.append(f"missing required field '{key}'")

    long_ids: set[str] = set()
    _check_beats("long", episode.get("beats") or [], errors, long_ids)

    image_beats = {
        b["id"] for b in episode.get("beats") or [] if (b.get("visual") or {}).get("type") in ("image", "photo")
    }
    all_beats = list(episode.get("beats") or [])
    for short in episode.get("shorts") or []:
        sid = short.get("id") or f"s{len(all_beats)}"
        short["id"] = sid
        _check_beats(f"short {sid}", short.get("beats") or [], errors, set(long_ids))
        all_beats.extend(short.get("beats") or [])

    for beat in all_beats:
        visual = beat.get("visual") or {}
        if visual.get("type") == "reuse" and visual.get("beat") not in image_beats:
            errors.append(f"beat {beat.get('id')}: reuse target {visual.get('beat')!r} is not an image beat")

    thumb = episode.get("thumbnail") or {}
    if thumb.get("beat") and thumb["beat"] not in image_beats:
        errors.append(f"thumbnail.beat {thumb['beat']!r} is not an image beat")

    if errors:
        raise ScriptError(f"{path}:\n  - " + "\n  - ".join(errors))
    episode["_dir"] = str(path.parent)
    return episode


def image_prompts(episode: dict) -> dict[str, dict]:
    """Unique image keys -> {prompt, style}, for long beats. Key is '<beat id>' or '<beat id>.<n>'."""
    out: dict[str, dict] = {}
    for beat in episode["beats"]:
        visual = beat["visual"]
        if visual["type"] != "image":
            continue
        prompts = visual.get("prompts") or [visual["prompt"]]
        for n, prompt in enumerate(prompts):
            out[beat["id"] if n == 0 else f"{beat['id']}.{n}"] = {"prompt": prompt, "style": visual.get("style", "ad")}
    return out


def photo_sources(episode: dict) -> dict[str, dict]:
    """Archive photos: beat id -> {url, credit, fallback_prompt}."""
    return {
        b["id"]: {"url": b["visual"]["url"], "credit": b["visual"]["credit"], "fallback_prompt": b["visual"].get("fallback_prompt")}
        for b in episode["beats"] if b["visual"]["type"] == "photo"
    }
