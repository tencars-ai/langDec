"""
Prompt configuration loader for the Birkenbihl decoder.

Each language pair has its own YAML file with rules, examples, and disambiguation
hints. The loader merges a pair-specific YAML with `_default.yaml` (universal rules)
and returns a `PromptConfig` dataclass that `prompt_builder.py` consumes.

Adding a new language pair: drop `<src>_<tgt>.yaml` into this directory.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


_PROMPTS_DIR = Path(__file__).parent


@dataclass(frozen=True)
class LineExample:
    """One reference translation: source line + plain-text word-by-word target."""
    source: str
    target: str


@dataclass(frozen=True)
class PromptConfig:
    """Resolved configuration for one source→target language pair."""
    source_lang: str
    target_lang: str
    source_lang_name: str
    target_lang_name: str
    universal_rules: str
    pair_rules: str
    examples: tuple[LineExample, ...]
    disambiguation: tuple[str, ...]
    anti_patterns: tuple[str, ...]
    critical_reminders: tuple[str, ...]


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _parse_examples(raw: list[dict[str, Any]] | None) -> tuple[LineExample, ...]:
    if not raw:
        return ()
    return tuple(
        LineExample(source=entry["source"], target=entry["target"])
        for entry in raw
    )


@lru_cache(maxsize=32)
def load_prompt_config(source_lang: str, target_lang: str) -> PromptConfig:
    """Load and merge prompt config for a language pair. Cached per pair."""
    default = _load_yaml(_PROMPTS_DIR / "_default.yaml")
    pair_path = _PROMPTS_DIR / f"{source_lang}_{target_lang}.yaml"
    pair = _load_yaml(pair_path)

    return PromptConfig(
        source_lang=source_lang,
        target_lang=target_lang,
        source_lang_name=pair.get("source_lang_name") or default.get("source_lang_name", source_lang),
        target_lang_name=pair.get("target_lang_name") or default.get("target_lang_name", target_lang),
        universal_rules=default.get("universal_rules", "").strip(),
        pair_rules=(pair.get("rules") or "").strip(),
        examples=_parse_examples(pair.get("examples")),
        disambiguation=tuple(pair.get("disambiguation") or ()),
        anti_patterns=tuple(default.get("anti_patterns") or ()),
        critical_reminders=tuple(pair.get("critical_reminders") or ()),
    )
