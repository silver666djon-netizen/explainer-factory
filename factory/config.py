from __future__ import annotations

import copy
import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def _merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


def load_config(episode_overrides: dict | None = None) -> dict:
    with open(ROOT / "channel" / "channel.yaml", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    return _merge(cfg, episode_overrides or {})


def resolve_font(candidates: list[str]) -> str:
    for cand in candidates:
        path = Path(cand)
        if not path.is_absolute():
            path = ROOT / path
        if path.exists():
            return str(path)
    raise FileNotFoundError(f"None of the fonts exist: {candidates}")


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def env(name: str, default: str | None = None) -> str | None:
    val = os.environ.get(name)
    return val if val else default
