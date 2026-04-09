"""
LLM Service – abstract base class and OpenAI / Anthropic implementations.
Implements the TranslationService interface so it works as a drop-in with the
existing WordByWordDecoder and Translator classes.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

# Maps ISO codes to full language names used in LLM prompts.
# Full names produce more reliable results than bare codes like "de" or "pt".
_LANG_NAMES: dict[str, str] = {
    "de": "German",
    "en": "English",
    "pt": "Portuguese",
}


class LLMService(ABC):
    """
    Abstract base for LLM-backed translation and text generation.
    Implements the TranslationService interface (translate_word, translate_text).
    """

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
    ) -> str:
        """Translate a single word (word-by-word, literal)."""
        ...

    @abstractmethod
    def translate_text(self, text: str, source_lang: str, target_lang: str) -> str:
        """Contextual/natural translation of a full text."""
        ...

    @abstractmethod
    def generate_text(self, prompt: str, language: str, difficulty: str) -> str:
        """Generate a text or dialogue in the target language."""
        ...

    @abstractmethod
    def word_lookup(
        self, word: str, source_lang: str, target_lang: str
    ) -> dict:
        """
        Detailed lookup for a single word.
        Returns dict with keys: translation, word_class, example_sentence.
        """
        ...

    def translate_birkenbihl(
        self, text: str, source_lang: str, target_lang: str
    ) -> dict:
        """
        Batch Birkenbihl translation: send the full text in one LLM call.
        Returns dict with keys:
          - "words": list of translated tokens (1:1 with source tokens)
          - "comments": any notes/explanations from the LLM (may be empty string)
        Falls back to per-word translate_word() on parse errors.
        """
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Shared helpers for batch Birkenbihl translation
# ---------------------------------------------------------------------------

def _birkenbihl_system_prompt(source_lang: str, target_lang: str) -> str:
    src = _LANG_NAMES.get(source_lang, source_lang)
    tgt = _LANG_NAMES.get(target_lang, target_lang)
    return (
        f"You are a strict word-for-word translator using the Birkenbihl decoding method.\n\n"
        f"TASK: Translate each word of the given {src} text into {tgt}, one word at a time, "
        f"preserving the EXACT original word order.\n\n"
        "CRITICAL RULES:\n"
        "1. Output EXACTLY ONE translation per source word — never merge two words, never split one word into two\n"
        "2. Translate each word IN ISOLATION — do NOT rearrange words to match "
        f"{tgt} grammar\n"
        f"3. The result WILL sound grammatically broken in {tgt} — this is CORRECT and INTENDED\n"
        "4. Use [ ] only for grammatical particles that have no direct equivalent\n"
        "5. Do NOT use | inside any translation entry\n"
        "6. Do NOT produce a natural translation — if the output sounds fluent, it is WRONG\n"
        "7. Numbers written as digits (e.g. 1, 42, 1., 3.5) must be copied UNCHANGED — do not translate or spell them out\n\n"
        "CORRECT example (Portuguese → German):\n"
        "Source:  Eu  tenho  saudade  de    você\n"
        "Output:  Ich|habe  |Sehnsucht|von  |dir\n\n"
        "INCORRECT (this is a natural translation — do NOT do this):\n"
        "Source:  Eu  tenho  saudade  de  você\n"
        "Output:  Ich vermisse dich\n\n"
        "Response format:\n"
        "Line 1: pipe-separated literal translations, one entry per source word, in source order\n"
        "Optional: one line starting with NOTES: for idioms or remarks\n"
        "Output ONLY line 1 (and optional NOTES). Nothing else."
    )


def _birkenbihl_user_prompt(text: str, source_lang: str, target_lang: str, token_count: int) -> str:
    src = _LANG_NAMES.get(source_lang, source_lang)
    tgt = _LANG_NAMES.get(target_lang, target_lang)
    return (
        f"Translate word-for-word from {src} to {tgt}.\n"
        f"Source text: {text}\n"
        f"Source word count: {token_count}\n"
        f"Required output entries: {token_count} (one per source word, pipe-separated)"
    )


def _parse_birkenbihl_response(
    raw: str,
    expected_count: int,
    tokens: list,
    source_lang: str,
    target_lang: str,
    fallback_service,
) -> dict:
    """Parse the LLM batch response. Falls back to per-word on mismatch."""
    lines = raw.strip().splitlines()
    word_line = ""
    notes_lines = []
    in_notes = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.upper().startswith("NOTES:"):
            in_notes = True
            rest = stripped[6:].strip()
            if rest:
                notes_lines.append(rest)
        elif in_notes:
            notes_lines.append(stripped)
        elif not word_line:
            word_line = stripped

    words = [w.strip() for w in word_line.split("|")] if word_line else []

    if len(words) != expected_count:
        mismatch_note = (
            f"[Batch mismatch: expected {expected_count} words, got {len(words)} — fell back to per-word translation]"
        )
        fallback_words = []
        for token in tokens:
            try:
                fallback_words.append(
                    fallback_service.translate_word(token, source_lang=source_lang, target_lang=target_lang)
                )
            except Exception as exc:
                fallback_words.append(f"[ERR:{exc}]")
        comments = mismatch_note
        if notes_lines:
            comments += "\n" + "\n".join(notes_lines)
        return {"words": fallback_words, "comments": comments}

    return {"words": words, "comments": "\n".join(notes_lines).strip()}


# ---------------------------------------------------------------------------
# OpenAI implementation
# ---------------------------------------------------------------------------

class OpenAIService(LLMService):
    """Translation and generation via OpenAI API."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        from openai import OpenAI  # lazy import
        self._client = OpenAI(api_key=api_key)
        self._model = model

    @property
    def name(self) -> str:
        return "OpenAI"

    def _chat(self, system: str, user: str) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content.strip()

    def translate_word(
        self,
        word: str,
        source_lang: str,
        target_lang: str,
        context: Optional[str] = None,
    ) -> str:
        system = (
            f"You are a word-for-word translator following the Birkenbihl method. "
            f"Translate the given {source_lang} word into {target_lang}.\n\n"
            "Rules:\n"
            "- Translate the word literally — preserve meaning, not naturalness\n"
            "- No natural-sounding output — grammar may sound broken\n"
            "- Use square brackets [ ] for grammatical helper words with no direct equivalent\n"
            "- Use (note: ...) for idioms that make no literal sense\n"
            "- Every source word must appear in the target — omit nothing\n"
            "- Return ONLY the translated word or short phrase — no explanation, no punctuation"
        )
        user = f"Word: {word}"
        if context:
            user += f"\nContext: {context}"
        return self._chat(system, user)

    def translate_text(self, text: str, source_lang: str, target_lang: str) -> str:
        system = (
            f"You are a professional translator. Translate the following text from {source_lang} to {target_lang}. "
            "Provide a natural, fluent translation. Return ONLY the translation."
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
        system = (
            f"You are a bilingual dictionary. For the given {source_lang} word, provide:\n"
            "1. Best translation to " + target_lang + "\n"
            "2. Word class (noun/verb/adjective/adverb/other)\n"
            "3. One short example sentence in " + source_lang + "\n"
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

    def translate_birkenbihl(self, text: str, source_lang: str, target_lang: str) -> dict:
        tokens = text.split()
        if not tokens:
            return {"words": [], "comments": ""}
        system = _birkenbihl_system_prompt(source_lang, target_lang)
        user = _birkenbihl_user_prompt(text, source_lang, target_lang, len(tokens))
        raw = self._chat(system, user)
        return _parse_birkenbihl_response(raw, len(tokens), tokens, source_lang, target_lang, self)


# ---------------------------------------------------------------------------
# Anthropic (Claude) implementation
# ---------------------------------------------------------------------------

class ClaudeService(LLMService):
    """Translation and generation via Anthropic Claude API."""

    def __init__(self, api_key: str, model: str = "claude-haiku-4-5-20251001"):
        import anthropic  # lazy import
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    @property
    def name(self) -> str:
        return "Claude (Anthropic)"

    def _message(self, system: str, user: str) -> str:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return response.content[0].text.strip()

    def translate_word(
        self,
        word: str,
        source_lang: str,
        target_lang: str,
        context: Optional[str] = None,
    ) -> str:
        system = (
            f"You are a word-for-word translator following the Birkenbihl method. "
            f"Translate the given {source_lang} word into {target_lang}.\n\n"
            "Rules:\n"
            "- Translate the word literally — preserve meaning, not naturalness\n"
            "- No natural-sounding output — grammar may sound broken\n"
            "- Use square brackets [ ] for grammatical helper words with no direct equivalent\n"
            "- Use (note: ...) for idioms that make no literal sense\n"
            "- Every source word must appear in the target — omit nothing\n"
            "- Return ONLY the translated word or short phrase — no explanation, no punctuation"
        )
        user = f"Word: {word}"
        if context:
            user += f"\nContext: {context}"
        return self._message(system, user)

    def translate_text(self, text: str, source_lang: str, target_lang: str) -> str:
        system = (
            f"You are a professional translator. Translate the following text from {source_lang} to {target_lang}. "
            "Provide a natural, fluent translation. Return ONLY the translation."
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
        system = (
            f"You are a bilingual dictionary. For the given {source_lang} word, provide:\n"
            "1. Best translation to " + target_lang + "\n"
            "2. Word class (noun/verb/adjective/adverb/other)\n"
            "3. One short example sentence in " + source_lang + "\n"
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

    def translate_birkenbihl(self, text: str, source_lang: str, target_lang: str) -> dict:
        tokens = text.split()
        if not tokens:
            return {"words": [], "comments": ""}
        system = _birkenbihl_system_prompt(source_lang, target_lang)
        user = _birkenbihl_user_prompt(text, source_lang, target_lang, len(tokens))
        raw = self._message(system, user)
        return _parse_birkenbihl_response(raw, len(tokens), tokens, source_lang, target_lang, self)


def build_llm_service(provider: str, api_key: str) -> LLMService:
    """Factory: build an LLMService from provider name and decrypted API key."""
    if provider == "openai":
        return OpenAIService(api_key=api_key)
    if provider == "anthropic":
        return ClaudeService(api_key=api_key)
    raise ValueError(f"Unknown LLM provider: {provider!r}")
