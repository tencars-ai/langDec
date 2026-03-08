"""
LLM Service – abstract base class and OpenAI / Anthropic implementations.
Implements the TranslationService interface so it works as a drop-in with the
existing WordByWordDecoder and Translator classes.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


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


def build_llm_service(provider: str, api_key: str) -> LLMService:
    """Factory: build an LLMService from provider name and decrypted API key."""
    if provider == "openai":
        return OpenAIService(api_key=api_key)
    if provider == "anthropic":
        return ClaudeService(api_key=api_key)
    raise ValueError(f"Unknown LLM provider: {provider!r}")
