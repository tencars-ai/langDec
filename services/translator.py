# This line enables better type hints in Python (allows using class names before they're defined)
from __future__ import annotations

# dataclass: A decorator that automatically generates __init__, __repr__ and other methods
from dataclasses import dataclass
# Protocol: Defines an interface (contract) that other classes should implement
# Optional: Type hint that means "this can be the specified type OR None"
from typing import Protocol, Optional

# Import the external translation library (needs to be installed via pip)
from deep_translator import GoogleTranslator


# Protocol = Interface/Contract: Any class that implements translate_word() is a valid TranslationService
class TranslationService(Protocol):
    """Abstract interface for translation providers.
    
    This defines what methods a translation service MUST have.
    Think of it as a contract: any translation service must have these methods.
    """

    def translate_word(self, word: str, source_lang: str, target_lang: str) -> str:
        # The "..." means: "this method must be implemented by concrete classes"
        ...
    
    def translate_text(self, text: str, source_lang: str, target_lang: str) -> str:
        # Method for translating complete sentences/paragraphs
        ...


# @dataclass automatically creates __init__ and other methods based on the attributes below
@dataclass
class GoogleDeepTranslatorService:
    """
    Translation service using deep_translator's GoogleTranslator.
    
    This class implements the actual translation using Google's translation API.
    Note: This is a 3rd-party service wrapper. Handle errors gracefully.
    """

    # Class attributes with default values
    # Optional[str] means: can be a string OR None
    source_default: Optional[str] = None  # Default source language, e.g. "pt" or None
    target_default: Optional[str] = None  # Default target language, e.g. "de" or None

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

        # Create a translator object from the deep_translator library
        translator = GoogleTranslator(source=source, target=target)
        
        # Call the translate method and return the result
        return translator.translate(word)
    
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

        # Create a translator object from the deep_translator library
        translator = GoogleTranslator(source=source, target=target)
        
        # Call the translate method for complete text
        return translator.translate(text)
