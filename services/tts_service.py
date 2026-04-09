"""
TTS Service – abstract base class and gTTS implementation.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
import io


class TTSService(ABC):
    """Abstract text-to-speech service. Returns MP3 bytes."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def synthesize(self, text: str, language: str) -> bytes:
        """Convert text to MP3 bytes."""
        ...


class GTTSService(TTSService):
    """Google Text-to-Speech via gTTS."""

    # Map language codes to gTTS locale codes where they differ
    _LANG_MAP = {
        "de": "de",
        "en": "en",
        "pt": "pt",
    }

    @property
    def name(self) -> str:
        return "gTTS (Google)"

    def synthesize(self, text: str, language: str) -> bytes:
        from gtts import gTTS  # lazy import

        lang = self._LANG_MAP.get(language, language)
        tts = gTTS(text=text, lang=lang)
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        return buf.getvalue()
