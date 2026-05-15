"""
Build system and user prompts for the Birkenbihl plain-text decoder from a
PromptConfig.

Output format the LLM is asked to produce (no JSON, no markdown):
    <word-by-word for source line 1>
    <word-by-word for source line 2>
    ...

One plain-text line per source line, in the same order. Tokens are
whitespace-separated. Multi-word target for one source word uses "-".
Empty "[]" marks source words without a direct target equivalent.
"""
from __future__ import annotations

from prompts import PromptConfig


def build_system_prompt(config: PromptConfig) -> str:
    parts: list[str] = []

    parts.append(
        f"You are a strict word-for-word translator using the Birkenbihl decoding "
        f"method, translating from {config.source_lang_name} to {config.target_lang_name}."
    )

    if config.universal_rules:
        parts.append(config.universal_rules)

    if config.pair_rules:
        parts.append(config.pair_rules)

    if config.anti_patterns:
        formatted = "\n".join(f"- {ap}" for ap in config.anti_patterns)
        parts.append("FORBIDDEN OUTPUT PATTERNS:\n" + formatted)

    if config.examples:
        rendered = "\n\n".join(
            f"Source:        {ex.source}\nWord-by-word:  {ex.target}"
            for ex in config.examples
        )
        parts.append(
            "EXAMPLES — match this style exactly. The Source/Word-by-word labels "
            "are shown here for clarity; do NOT include them in your output.\n\n"
            + rendered
        )

    if config.disambiguation:
        formatted = "\n".join(f"- {hint}" for hint in config.disambiguation)
        parts.append("KNOWN DISAMBIGUATIONS — apply these strictly:\n" + formatted)

    parts.append(
        "OUTPUT FORMAT — return ONLY the word-by-word translation lines, one "
        "plain-text line per source line, in the same order as the input. "
        "No labels, no prose, no markdown, no JSON. Each line's whitespace-"
        "separated token count must equal the source line's word count."
    )

    return "\n\n".join(parts)


def build_user_prompt(config: PromptConfig, lines: list[str]) -> str:
    """User prompt: source lines + word counts + critical reminders near the task."""
    labeled = "\n".join(f"[L{i+1}] {line}" for i, line in enumerate(lines))
    word_counts = ", ".join(str(len(line.split())) for line in lines)

    parts: list[str] = [
        f"Decode these {len(lines)} source line(s) from "
        f"{config.source_lang_name} to {config.target_lang_name}.",
        f"SOURCE LINES (the [L1]/[L2]/… tags are line labels, NOT tokens to decode):\n{labeled}",
        f"Required token counts per line: [{word_counts}]\n"
        f"Each output line must have EXACTLY that many whitespace-separated tokens.",
    ]

    if config.critical_reminders:
        formatted = "\n".join(f"- {r}" for r in config.critical_reminders)
        parts.append("CRITICAL REMINDERS — these are the rules most often violated:\n" + formatted)

    parts.append(
        f"Return exactly {len(lines)} plain-text line(s), one per source line, "
        "in the same order. No labels, no prose, no JSON, no markdown — only "
        "the word-by-word translation lines separated by newlines."
    )
    return "\n\n".join(parts)
