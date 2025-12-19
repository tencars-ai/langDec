from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Optional

from deep_translator import GoogleTranslator


class TranslationService(Protocol):
    """Abstract interface for translation providers."""

    def translate_word(self, word: str, source_lang: str, target_lang: str) -> str:
        ...


@dataclass
class GoogleDeepTranslatorService:
    """
    Translation service using deep_translator's GoogleTranslator.

    Note: This is a 3rd-party service wrapper. Handle errors gracefully.
    """

    source_default: Optional[str] = None  # e.g. "pt" or None
    target_default: Optional[str] = None  # e.g. "de" or None

    def translate_word(self, word: str, source_lang: str, target_lang: str) -> str:
        source = self.source_default or source_lang
        target = self.target_default or target_lang

        translator = GoogleTranslator(source=source, target=target)
        return translator.translate(word)
