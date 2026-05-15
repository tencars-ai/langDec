"""
LLM Service — abstract base class and OpenAI / Anthropic implementations.
Implements the TranslationService interface so it works as a drop-in with the
existing WordByWordDecoder and Translator classes.

Birkenbihl decoding uses a plain-text output format (no JSON, no tool-use).
The LLM is asked to return one whitespace-tokenized line per source line.
Hyphens mark multi-word targets for a single source word ("werden-wir");
empty "[]" marks source words with no direct target equivalent.

The per-line token count is verified by the parser; mismatched lines fall
back to per-word translation.
"""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Optional

from prompts import load_prompt_config
from services.prompt_builder import build_system_prompt, build_user_prompt


# Maps ISO codes to full language names for translate_word / translate_text.
# Birkenbihl decoding uses prompts/<src>_<tgt>.yaml for richer naming.
_LANG_NAMES: dict[str, str] = {
    "de": "German",
    "en": "English",
    "pt": "Portuguese",
    "sv": "Swedish",
}


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class LLMService(ABC):
    """Abstract base for LLM-backed translation and generation."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def translate_word(
        self,
        word: str,
        source_lang: str,
        target_lang: str,
        context: Optional[str] = None,
    ) -> str: ...

    @abstractmethod
    def translate_text(self, text: str, source_lang: str, target_lang: str) -> str: ...

    @abstractmethod
    def generate_text(self, prompt: str, language: str, difficulty: str) -> str: ...

    @abstractmethod
    def word_lookup(self, word: str, source_lang: str, target_lang: str) -> dict: ...

    def translate_birkenbihl_full(
        self, text: str, source_lang: str, target_lang: str,
    ) -> dict:
        """Full-text Birkenbihl decoding in one plain-text LLM call.

        Returns: {"line_results": {orig_idx: {"words": [...], "comments": ""}},
                  "comments": "<aggregated notes/errors>",
                  "raw_payload": {"raw_text": "...", "parsed_lines": [...]}}
        """
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Shared parser + fallback
# ---------------------------------------------------------------------------

# Lines starting with these prefixes are labels emitted by the LLM despite
# being told not to — we strip them defensively.
_LABEL_PREFIXES = (
    "word-by-word:",
    "word-for-word:",
    "translation:",
    "target:",
    "output:",
)
_SOURCE_PREFIXES = ("source:", "source ")

# Pattern for stripping parenthetical asides like "Italo (proper name)".
_PAREN_RE = re.compile(r"\s*\([^)]*\)\s*")


def _clean_word_translation(raw: str, fallback: str = "") -> str:
    """Clean a single-word LLM translation.

    Used by translate_word and the per-word fallback. Defensively strips
    parenthetical asides ("Italo (proper name)" → "Italo"), takes only the
    first non-empty line, and collapses any remaining whitespace inside the
    result to a hyphen so it stays a single token.
    """
    if not raw:
        return fallback
    line = ""
    for candidate in raw.splitlines():
        candidate = candidate.strip()
        if candidate:
            line = candidate
            break
    if not line:
        return fallback
    line = _PAREN_RE.sub(" ", line).strip()
    # Strip surrounding quotes the LLM sometimes adds.
    line = line.strip("\"'")
    if " " in line:
        line = "-".join(line.split())
    return line or fallback


def _per_word_fallback(
    tokens: list[str], source_lang: str, target_lang: str, fallback_service,
) -> list[str]:
    """Last-resort: translate each token individually via the service."""
    result: list[str] = []
    for token in tokens:
        try:
            result.append(
                fallback_service.translate_word(
                    token, source_lang=source_lang, target_lang=target_lang,
                )
            )
        except Exception as exc:
            result.append(f"[ERR:{exc}]")
    return result


def _extract_word_by_word_lines(raw: str) -> list[str]:
    """Extract the word-by-word translation lines from the raw LLM output.

    Defensively skips Source: echo lines, strips Word-by-word: prefixes,
    ignores empty lines / markdown fences, and drops lines that are pure
    parenthetical commentary (e.g. "(This is a proper name…)").
    """
    result: list[str] = []
    for raw_line in raw.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("```") or line.startswith("---"):
            continue
        # Drop lines that are entirely a parenthetical aside.
        if line.startswith("(") and line.endswith(")"):
            continue
        lower = line.lower()
        if any(lower.startswith(p) for p in _SOURCE_PREFIXES):
            continue
        for prefix in _LABEL_PREFIXES:
            if lower.startswith(prefix):
                line = line[len(prefix):].strip()
                break
        # Strip a leading "[L<n>]" label if the LLM echoed it back.
        line = re.sub(r"^\[L\d+\]\s*", "", line)
        # Strip inline parenthetical asides anywhere in the line.
        line = _PAREN_RE.sub(" ", line).strip()
        if line:
            result.append(line)
    return result


def _parse_birkenbihl_text_response(
    raw: str,
    source_lines: list[tuple[int, str]],
    source_lang: str,
    target_lang: str,
    fallback_service,
) -> dict:
    """Parse the plain-text Birkenbihl response and produce decoder output."""
    parsed_lines = _extract_word_by_word_lines(raw)

    line_results: dict[int, dict] = {}
    comments: list[str] = []

    for j, (idx, src_line) in enumerate(source_lines):
        src_tokens = src_line.split()
        expected = len(src_tokens)

        if j >= len(parsed_lines):
            comments.append(
                f"[Line {idx + 1}: LLM omitted this line — per-word fallback]"
            )
            line_results[idx] = {
                "words": _per_word_fallback(src_tokens, source_lang, target_lang, fallback_service),
                "comments": "",
            }
            continue

        target_tokens = parsed_lines[j].split()

        if len(target_tokens) != expected:
            comments.append(
                f"[Line {idx + 1}: expected {expected} tokens, got {len(target_tokens)} — per-word fallback]"
            )
            target_tokens = _per_word_fallback(
                src_tokens, source_lang, target_lang, fallback_service,
            )

        line_results[idx] = {"words": target_tokens, "comments": ""}

    return {
        "line_results": line_results,
        "comments": "\n".join(comments).strip(),
        "raw_payload": {"raw_text": raw, "parsed_lines": parsed_lines},
    }


def _fallback_all_lines(
    source_lines: list[tuple[int, str]],
    source_lang: str,
    target_lang: str,
    fallback_service,
    reason: str,
) -> dict:
    """Catastrophic-failure path: per-word translate every line."""
    line_results: dict[int, dict] = {}
    for idx, src_line in source_lines:
        tokens = src_line.split()
        line_results[idx] = {
            "words": _per_word_fallback(tokens, source_lang, target_lang, fallback_service),
            "comments": "",
        }
    return {
        "line_results": line_results,
        "comments": f"[Decoder fallback: {reason}]",
        "raw_payload": {"_error": reason},
    }


def _prepare_decode_call(text: str, source_lang: str, target_lang: str):
    """Split into non-empty source lines + build prompts from config."""
    raw_lines = text.split("\n")
    source_lines = [(i, line.strip()) for i, line in enumerate(raw_lines) if line.strip()]
    if not source_lines:
        return None
    cfg = load_prompt_config(source_lang, target_lang)
    non_empty = [line for _, line in source_lines]
    system = build_system_prompt(cfg)
    user = build_user_prompt(cfg, non_empty)
    return source_lines, system, user


# ---------------------------------------------------------------------------
# OpenAI implementation
# ---------------------------------------------------------------------------

class OpenAIService(LLMService):
    """Translation and generation via OpenAI API."""

    provider = "openai"

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        from openai import OpenAI  # lazy import
        self._client = OpenAI(api_key=api_key)
        self._model = model

    @property
    def name(self) -> str:
        return "OpenAI"

    _REQUEST_TIMEOUT = 60.0

    def _chat(self, system: str, user: str, max_tokens: int = 2048) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
            max_tokens=max_tokens,
            timeout=self._REQUEST_TIMEOUT,
        )
        return response.choices[0].message.content.strip()

    def translate_word(
        self,
        word: str,
        source_lang: str,
        target_lang: str,
        context: Optional[str] = None,
    ) -> str:
        src = _LANG_NAMES.get(source_lang, source_lang)
        tgt = _LANG_NAMES.get(target_lang, target_lang)
        system = (
            f"You are a strict word-for-word translator. Translate the given "
            f"{src} word into {tgt}.\n\n"
            "RULES (each mandatory):\n"
            "- Return EXACTLY ONE token: a single word, or multiple words joined with '-'.\n"
            "- If the word is a proper name (person, place, brand), return it UNCHANGED.\n"
            "- If there is no direct equivalent, return '[]'.\n"
            "- NO parentheses, NO explanations, NO 'or X' alternatives, NO commentary, NO quotes.\n"
            "- NO spaces inside the output."
        )
        user = f"Word: {word}"
        if context:
            user += f"\nContext: {context}"
        raw = self._chat(system, user, max_tokens=64)
        return _clean_word_translation(raw, fallback=word)

    def translate_text(self, text: str, source_lang: str, target_lang: str) -> str:
        src = _LANG_NAMES.get(source_lang, source_lang)
        tgt = _LANG_NAMES.get(target_lang, target_lang)
        system = (
            f"You are a professional translator. Translate the following text from {src} to {tgt}. "
            "Provide a natural, fluent translation. "
            "Preserve the original line break and paragraph structure exactly — "
            "do not merge separate lines, do not split single lines. "
            "Return ONLY the translation."
        )
        return self._chat(system, text)

    def generate_text(self, prompt: str, language: str, difficulty: str) -> str:
        system = (
            f"You are a language learning assistant. Generate a {difficulty}-level text in {language} "
            "suitable for language learners. Use vocabulary appropriate for the difficulty level. "
            "Return ONLY the generated text."
        )
        return self._chat(system, prompt)

    def word_lookup(self, word: str, source_lang: str, target_lang: str) -> dict:
        src = _LANG_NAMES.get(source_lang, source_lang)
        tgt = _LANG_NAMES.get(target_lang, target_lang)
        system = (
            f"You are a bilingual dictionary. For the given {src} word, provide:\n"
            f"1. Best translation to {tgt}\n"
            "2. Word class (noun/verb/adjective/adverb/other)\n"
            f"3. One short example sentence in {src}\n"
            "Respond in this exact format:\n"
            "translation: <word>\nword_class: <class>\nexample: <sentence>"
        )
        raw = self._chat(system, word)
        result = {"translation": word, "word_class": "", "example_sentence": ""}
        for line in raw.splitlines():
            if line.startswith("translation:"):
                result["translation"] = line.split(":", 1)[1].strip()
            elif line.startswith("word_class:"):
                result["word_class"] = line.split(":", 1)[1].strip()
            elif line.startswith("example:"):
                result["example_sentence"] = line.split(":", 1)[1].strip()
        return result

    def translate_birkenbihl_full(
        self, text: str, source_lang: str, target_lang: str,
    ) -> dict:
        prep = _prepare_decode_call(text, source_lang, target_lang)
        if prep is None:
            return {"line_results": {}, "comments": "", "raw_payload": None}
        source_lines, system, user = prep

        try:
            raw = self._chat(system, user, max_tokens=4096)
        except Exception as exc:
            return _fallback_all_lines(
                source_lines, source_lang, target_lang, self,
                reason=f"OpenAI call failed: {exc}",
            )

        return _parse_birkenbihl_text_response(
            raw, source_lines, source_lang, target_lang, self,
        )


# ---------------------------------------------------------------------------
# Anthropic (Claude) implementation
# ---------------------------------------------------------------------------

class ClaudeService(LLMService):
    """Translation and generation via Anthropic Claude API."""

    provider = "anthropic"

    def __init__(self, api_key: str, model: str = "claude-haiku-4-5-20251001"):
        import anthropic  # lazy import
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    @property
    def name(self) -> str:
        return "Claude (Anthropic)"

    _REQUEST_TIMEOUT = 60.0

    def _message(self, system: str, user: str, max_tokens: int = 1024) -> str:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
            timeout=self._REQUEST_TIMEOUT,
        )
        return response.content[0].text.strip()

    def translate_word(
        self,
        word: str,
        source_lang: str,
        target_lang: str,
        context: Optional[str] = None,
    ) -> str:
        src = _LANG_NAMES.get(source_lang, source_lang)
        tgt = _LANG_NAMES.get(target_lang, target_lang)
        system = (
            f"You are a strict word-for-word translator. Translate the given "
            f"{src} word into {tgt}.\n\n"
            "RULES (each mandatory):\n"
            "- Return EXACTLY ONE token: a single word, or multiple words joined with '-'.\n"
            "- If the word is a proper name (person, place, brand), return it UNCHANGED.\n"
            "- If there is no direct equivalent, return '[]'.\n"
            "- NO parentheses, NO explanations, NO 'or X' alternatives, NO commentary, NO quotes.\n"
            "- NO spaces inside the output."
        )
        user = f"Word: {word}"
        if context:
            user += f"\nContext: {context}"
        raw = self._message(system, user, max_tokens=64)
        return _clean_word_translation(raw, fallback=word)

    def translate_text(self, text: str, source_lang: str, target_lang: str) -> str:
        src = _LANG_NAMES.get(source_lang, source_lang)
        tgt = _LANG_NAMES.get(target_lang, target_lang)
        system = (
            f"You are a professional translator. Translate the following text from {src} to {tgt}. "
            "Provide a natural, fluent translation. "
            "Preserve the original line break and paragraph structure exactly — "
            "do not merge separate lines, do not split single lines. "
            "Return ONLY the translation."
        )
        return self._message(system, text)

    def generate_text(self, prompt: str, language: str, difficulty: str) -> str:
        system = (
            f"You are a language learning assistant. Generate a {difficulty}-level text in {language} "
            "suitable for language learners. Use vocabulary appropriate for the difficulty level. "
            "Return ONLY the generated text."
        )
        return self._message(system, prompt)

    def word_lookup(self, word: str, source_lang: str, target_lang: str) -> dict:
        src = _LANG_NAMES.get(source_lang, source_lang)
        tgt = _LANG_NAMES.get(target_lang, target_lang)
        system = (
            f"You are a bilingual dictionary. For the given {src} word, provide:\n"
            f"1. Best translation to {tgt}\n"
            "2. Word class (noun/verb/adjective/adverb/other)\n"
            f"3. One short example sentence in {src}\n"
            "Respond in this exact format:\n"
            "translation: <word>\nword_class: <class>\nexample: <sentence>"
        )
        raw = self._message(system, word)
        result = {"translation": word, "word_class": "", "example_sentence": ""}
        for line in raw.splitlines():
            if line.startswith("translation:"):
                result["translation"] = line.split(":", 1)[1].strip()
            elif line.startswith("word_class:"):
                result["word_class"] = line.split(":", 1)[1].strip()
            elif line.startswith("example:"):
                result["example_sentence"] = line.split(":", 1)[1].strip()
        return result

    def translate_birkenbihl_full(
        self, text: str, source_lang: str, target_lang: str,
    ) -> dict:
        prep = _prepare_decode_call(text, source_lang, target_lang)
        if prep is None:
            return {"line_results": {}, "comments": "", "raw_payload": None}
        source_lines, system, user = prep

        try:
            raw = self._message(system, user, max_tokens=4096)
        except Exception as exc:
            return _fallback_all_lines(
                source_lines, source_lang, target_lang, self,
                reason=f"Claude call failed: {exc}",
            )

        return _parse_birkenbihl_text_response(
            raw, source_lines, source_lang, target_lang, self,
        )


def build_llm_service(provider: str, api_key: str) -> LLMService:
    """Factory: build an LLMService from provider name and decrypted API key."""
    if provider == "openai":
        return OpenAIService(api_key=api_key)
    if provider == "anthropic":
        return ClaudeService(api_key=api_key)
    raise ValueError(f"Unknown LLM provider: {provider!r}")
