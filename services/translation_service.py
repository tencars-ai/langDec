# This line enables better type hints in Python (allows using class names before they're defined)
from __future__ import annotations

# dataclass: A decorator that automatically generates __init__, __repr__ and other methods
from dataclasses import dataclass
# Protocol: Defines an interface (contract) that other classes should implement
# Optional: Type hint that means "this can be the specified type OR None"
from typing import Protocol, Optional

# Import the external translation library (needs to be installed via pip)
from deep_translator import GoogleTranslator, MyMemoryTranslator, LingueeTranslator, PonsTranslator


# Language code mapping for services that require specific locale codes
# MyMemory requires detailed locale codes like 'pt-PT' or 'pt-BR'
# Other services like Google can work with simplified codes like 'pt'
MYMEMORY_LANGUAGE_MAP = {
    'pt-BR': 'pt-BR',  # Brazilian Portuguese
    'pt-PT': 'pt-PT',  # European Portuguese
    'pt': 'pt-PT',     # Default Portuguese to European
    'en': 'en-GB',     # Default English to British
    'de': 'de-DE',     # German
    # Add more mappings as needed
}

# For services that don't differentiate regional variants
SIMPLE_LANGUAGE_MAP = {
    'pt-BR': 'pt',  # Simplify Brazilian Portuguese to pt
    'pt-PT': 'pt',  # Simplify European Portuguese to pt
    'en-GB': 'en',  # Simplify British English to en
    'en-US': 'en',  # Simplify American English to en
    'de-DE': 'de',  # Simplify German to de
    # Add more as needed
}

def _map_language_for_mymemory(lang_code: str) -> str:
    """Convert language codes to MyMemory-specific format.
    
    Args:
        lang_code: Standard language code (e.g., 'pt', 'pt-BR', 'de')
        
    Returns:
        MyMemory-compatible language code (e.g., 'pt-PT', 'pt-BR', 'de-DE')
    """
    # Return mapped code if exists, otherwise return original
    return MYMEMORY_LANGUAGE_MAP.get(lang_code, lang_code)

def _simplify_language_code(lang_code: str) -> str:
    """Simplify regional language codes to base language codes.
    
    Args:
        lang_code: Language code that may include region (e.g., 'pt-BR', 'pt-PT')
        
    Returns:
        Simplified language code (e.g., 'pt')
    """
    # Return simplified code if exists, otherwise return original
    return SIMPLE_LANGUAGE_MAP.get(lang_code, lang_code)


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
        
        # Simplify regional codes (pt-BR/pt-PT -> pt) for Google
        source = _simplify_language_code(source)
        target = _simplify_language_code(target)

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
        
        # Simplify regional codes (pt-BR/pt-PT -> pt) for Google
        source = _simplify_language_code(source)
        target = _simplify_language_code(target)

        # Create a translator object from the deep_translator library
        translator = GoogleTranslator(source=source, target=target)
        
        # Call the translate method for complete text
        return translator.translate(text)


# @dataclass automatically creates __init__ and other methods
@dataclass
class MyMemoryTranslatorService:
    """Translation service using MyMemory Translator.
    
    MyMemory is a collaborative translation memory with good quality
    and generous free tier (500 requests/day).
    """
    
    source_default: Optional[str] = None
    target_default: Optional[str] = None

    def translate_word(self, word: str, source_lang: str, target_lang: str) -> str:
        """Translates a single word using MyMemory."""
        source = self.source_default or source_lang
        target = self.target_default or target_lang
        
        # Map language codes to MyMemory-specific format
        source = _map_language_for_mymemory(source)
        target = _map_language_for_mymemory(target)
        
        translator = MyMemoryTranslator(source=source, target=target)
        return translator.translate(word)
    
    def translate_text(self, text: str, source_lang: str, target_lang: str) -> str:
        """Translates complete text using MyMemory."""
        source = self.source_default or source_lang
        target = self.target_default or target_lang
        
        # Map language codes to MyMemory-specific format
        source = _map_language_for_mymemory(source)
        target = _map_language_for_mymemory(target)
        
        translator = MyMemoryTranslator(source=source, target=target)
        return translator.translate(text)


@dataclass
class LingueeTranslatorService:
    """Translation service using Linguee.
    
    Linguee provides translations with real-world context examples,
    ideal for language learning purposes.
    """
    
    source_default: Optional[str] = None
    target_default: Optional[str] = None

    def translate_word(self, word: str, source_lang: str, target_lang: str) -> str:
        """Translates a single word using Linguee."""
        source = self.source_default or source_lang
        target = self.target_default or target_lang
        
        # Simplify regional codes (pt-BR/pt-PT -> pt) for Linguee
        source = _simplify_language_code(source)
        target = _simplify_language_code(target)
        
        translator = LingueeTranslator(source=source, target=target)
        return translator.translate(word)
    
    def translate_text(self, text: str, source_lang: str, target_lang: str) -> str:
        """Translates complete text using Linguee."""
        source = self.source_default or source_lang
        target = self.target_default or target_lang
        
        # Simplify regional codes (pt-BR/pt-PT -> pt) for Linguee
        source = _simplify_language_code(source)
        target = _simplify_language_code(target)
        
        translator = LingueeTranslator(source=source, target=target)
        return translator.translate(text)


@dataclass
class PonsTranslatorService:
    """Translation service using PONS.
    
    PONS is a dictionary with good quality translations,
    especially for European languages.
    """
    
    source_default: Optional[str] = None
    target_default: Optional[str] = None

    def translate_word(self, word: str, source_lang: str, target_lang: str) -> str:
        """Translates a single word using PONS."""
        source = self.source_default or source_lang
        target = self.target_default or target_lang
        
        # Simplify regional codes (pt-BR/pt-PT -> pt) for PONS
        source = _simplify_language_code(source)
        target = _simplify_language_code(target)
        
        translator = PonsTranslator(source=source, target=target)
        return translator.translate(word)
    
    def translate_text(self, text: str, source_lang: str, target_lang: str) -> str:
        """Translates complete text using PONS."""
        source = self.source_default or source_lang
        target = self.target_default or target_lang
        
        # Simplify regional codes (pt-BR/pt-PT -> pt) for PONS
        source = _simplify_language_code(source)
        target = _simplify_language_code(target)
        
        translator = PonsTranslator(source=source, target=target)
        return translator.translate(text)


# Factory function to create translation service instances
def get_translation_service(service_name: str) -> TranslationService:
    """Factory function to create a translation service by name.
    
    Args:
        service_name: Name of the service ("Google", "MyMemory", "Linguee", "PONS")
        
    Returns:
        An instance of the requested translation service
        
    Raises:
        ValueError: If service_name is not recognized
    """
    services = {
        "Google": GoogleDeepTranslatorService,
        "MyMemory": MyMemoryTranslatorService,
        "Linguee": LingueeTranslatorService,
        "PONS": PonsTranslatorService,
    }
    
    if service_name not in services:
        raise ValueError(f"Unknown translation service: {service_name}. Available: {list(services.keys())}")
    
    return services[service_name]()
