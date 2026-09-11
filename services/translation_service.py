# This line enables better type hints in Python (allows using class names before they're defined)
from __future__ import annotations

# ABC: Abstract Base Class for defining interfaces
from abc import ABC, abstractmethod
# dataclass: A decorator that automatically generates __init__, __repr__ and other methods
from dataclasses import dataclass
# Optional: Type hint that means "this can be the specified type OR None"
from typing import Optional

# Import the external translation libraries (need to be installed via pip)
import requests
from bs4 import BeautifulSoup

# Google now serves a fake "Error 500" block page instead of a translation
# when a request's User-Agent looks like a script (e.g. the default
# "python-requests/x.y" the deep-translator library used to send
# unconditionally, with no way to override it). A browser User-Agent avoids
# that block, so we talk to the same public endpoint deep-translator used
# directly instead of going through it.
_GOOGLE_TRANSLATE_URL = "https://translate.google.com/m"
_BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


_MAX_CHARS = 5000


def _google_translate(text: str, source: str, target: str) -> str:
    """Translate `text` via Google Translate's public /m (mobile) endpoint."""
    if not text or source == target:
        return text
    if len(text) >= _MAX_CHARS:
        raise ValueError(f"Google Translate: text too long ({len(text)} chars, limit {_MAX_CHARS})")
    response = requests.get(
        _GOOGLE_TRANSLATE_URL,
        params={"sl": source, "tl": target, "q": text},
        headers={"User-Agent": _BROWSER_USER_AGENT},
        timeout=15,
    )
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    element = soup.find("div", {"class": "result-container"})
    if element is None:
        raise RuntimeError("Google Translate: no translation found in the response")
    return element.get_text(strip=True)


# ABC = Abstract Base Class: Defines an interface that subclasses must implement
class TranslationService(ABC):
    """Abstract interface for translation providers.
    
    This defines what methods a translation service MUST have.
    Think of it as a contract: any translation service must have these methods.
    """

    @abstractmethod
    def translate_word(self, word: str, source_lang: str, target_lang: str) -> str:
        """Translate a single word."""
        pass
    
    @abstractmethod
    def translate_text(self, text: str, source_lang: str, target_lang: str) -> str:
        """Translate complete text (sentences/paragraphs)."""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the display name of this translation service."""
        pass


# @dataclass automatically creates __init__ and other methods based on the attributes below
@dataclass
class GoogleDeepTranslatorService(TranslationService):
    """
    Translation service using Google Translate's public web endpoint.

    This class implements the actual translation using Google's translation API.
    Note: This is a 3rd-party service wrapper. Handle errors gracefully.
    """

    # Class attributes with default values
    # Optional[str] means: can be a string OR None
    source_default: Optional[str] = None  # Default source language, e.g. "pt" or None
    target_default: Optional[str] = None  # Default target language, e.g. "de" or None
    
    @property
    def name(self) -> str:
        """Return the display name of this service."""
        return "Google Translate"

    def translate_word(self, word: str, source_lang: str, target_lang: str) -> str:
        """Translates a single word from source language to target language.
        
        Args:
            word: The word to translate
            source_lang: Source language code (e.g., "pt" for Portuguese)
            target_lang: Target language code (e.g., "de" for German)
            
        Returns:
            The translated word as a string
        """
        # Use default language if set, otherwise use the provided parameter
        # "x or y" means: if x is truthy (not None, not empty), use x, else use y
        source = self.source_default or source_lang
        target = self.target_default or target_lang

        # Google can return an empty result for numbers/punctuation — fall back to original word
        return _google_translate(word, source, target) or word
    
    def translate_text(self, text: str, source_lang: str, target_lang: str) -> str:
        """Translates complete text (sentences/paragraphs) naturally.
        
        Args:
            text: The text to translate (can be multiple sentences)
            source_lang: Source language code (e.g., "pt" for Portuguese)
            target_lang: Target language code (e.g., "de" for German)
            
        Returns:
            The translated text as a string
        """
        # Use default language if set, otherwise use the provided parameter
        source = self.source_default or source_lang
        target = self.target_default or target_lang

        return _google_translate(text, source, target) or text


@dataclass
class ArgosTranslateService(TranslationService):
    """Translation service using ArgosTranslate (offline translation).
    
    ArgosTranslate provides offline translation capabilities using
    pre-downloaded language models. This can be useful when:
    - Internet connection is limited
    - Privacy is a concern
    - Need faster translation without API calls
    
    Note: Requires argostranslate package and language models to be installed.
    """
    
    source_default: Optional[str] = None
    target_default: Optional[str] = None
    
    @property
    def name(self) -> str:
        """Return the display name of this service."""
        return "Argos Translate"
    
    def translate_word(self, word: str, source_lang: str, target_lang: str) -> str:
        """Translates a single word using Argos Translate.
        
        Args:
            word: The word to translate
            source_lang: Source language code (e.g., "en")
            target_lang: Target language code (e.g., "de")
            
        Returns:
            The translated word as a string
        """
        try:
            import argostranslate.package
            import argostranslate.translate
            
            source = self.source_default or source_lang
            target = self.target_default or target_lang
            
            # Translate using Argos
            translated = argostranslate.translate.translate(word, source, target)
            return translated
        except ImportError:
            # Fallback if argostranslate is not installed
            return f"[ArgosTranslate not installed: {word}]"
        except Exception as e:
            # Handle any translation errors
            return f"[Error: {word}]"
    
    def translate_text(self, text: str, source_lang: str, target_lang: str) -> str:
        """Translates complete text using Argos Translate.
        
        Args:
            text: The text to translate (can be multiple sentences)
            source_lang: Source language code (e.g., "en")
            target_lang: Target language code (e.g., "de")
            
        Returns:
            The translated text as a string
        """
        try:
            import argostranslate.package
            import argostranslate.translate
            
            source = self.source_default or source_lang
            target = self.target_default or target_lang
            
            # Translate using Argos
            translated = argostranslate.translate.translate(text, source, target)
            return translated
        except ImportError:
            # Fallback if argostranslate is not installed
            return f"[ArgosTranslate not installed]"
        except Exception as e:
            # Handle any translation errors
            return f"[Translation Error: {e}]"
