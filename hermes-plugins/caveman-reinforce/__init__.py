"""Re-inject the active caveman level into every Hermes turn.

SOUL.md and the caveman skill are read once per prompt build, so the style
drifts in long sessions. Claude Code's caveman plugin fixes that with a
per-turn UserPromptSubmit reminder; this is the Hermes equivalent.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

# Reminder texts from caveman's src/hooks/caveman-mode-tracker.js (MIT).
RULES = {
    "lite": "No filler, hedging, or pleasantries. Keep articles and full sentences OK, but stay tight.",
    "full": "Drop articles (a/an/the), filler, pleasantries, and hedging. Prefer fragments over full natural-prose sentences. No preamble or recap.",
    "ultra": "Drop articles, filler, pleasantries, hedging, and excess conjunctions. Prefer fragments over full natural-prose sentences. State each fact once. No preamble or recap.",
    "wenyan-lite": "Use wenyan-lite: semi-classical terse register. Drop filler and hedging. Keep meaning exact.",
    "wenyan-full": "Use wenyan-full: maximum classical terseness. Drop filler and hedging. Keep meaning exact.",
    "wenyan-ultra": "Use wenyan-ultra: extreme classical terseness. Drop filler and hedging. Keep meaning exact.",
}


def _normalize(mode: Any) -> str | None:
    if not isinstance(mode, str):
        return None
    mode = mode.strip().lower()
    if mode == "wenyan":
        mode = "wenyan-full"
    return mode if mode in RULES or mode == "off" else None


def resolve_mode() -> str:
    """Same order as caveman: env var, user config file, then full."""
    env_mode = _normalize(os.environ.get("CAVEMAN_DEFAULT_MODE"))
    if env_mode:
        return env_mode
    base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    try:
        data = json.loads((base / "caveman" / "config.json").read_text(encoding="utf-8"))
        return _normalize(data.get("defaultMode")) or "full"
    except (OSError, ValueError, AttributeError):
        return "full"


def reminder(mode: str) -> str | None:
    if mode not in RULES:
        return None
    return (
        f"CAVEMAN MODE ACTIVE ({mode}). Enforce this reply: {RULES[mode]}"
        " Technical terms, code, commands, paths, and errors stay exact."
    )


def _pre_llm_call(**_: Any) -> dict[str, str] | None:
    text = reminder(resolve_mode())
    return {"context": text} if text else None


def register(ctx: Any) -> None:
    ctx.register_hook("pre_llm_call", _pre_llm_call)
