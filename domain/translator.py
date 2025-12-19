# Enable modern type hints (allows referencing class names before definition)
from __future__ import annotations

# Import from services → translation_service module
# TranslationService is the interface (Protocol) for translation providers
from services.translation_service import TranslationService


class Translator:
    """
    Standard text translator for complete sentence/paragraph translation.
    
    Unlike the WordByWordDecoder which translates word-by-word for learning,
    this translator provides natural, fluent translations of entire texts.
    
    Responsibilities:
      - Translate complete texts while preserving line breaks
      - Maintain natural sentence structure and grammar
      - Handle multi-paragraph texts
    """

    def __init__(self, translation_service: TranslationService):
        """Initialize the translator with a translation service.
        
        Args:
            translation_service: Any object that implements the translate_word method
        """
        self.translation_service = translation_service

    def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
    ) -> str:
        """Translate complete text naturally.
        
        Args:
            text: The text to translate (can be multiple sentences/paragraphs)
            source_lang: Language code of input text (e.g., "en")
            target_lang: Language code for translation (e.g., "de")
            
        Returns:
            Naturally translated text with preserved line breaks
        """
        # Clean up the input: if text is None, use ""
        text = (text or "").strip()
        
        # Early return: if text is empty, just return empty string
        if not text:
            return ""

        # Process each line separately to preserve line breaks
        lines = text.split('\n')
        translated_lines = []
        
        for line in lines:
            line = line.strip()
            # Skip empty lines but preserve them in output
            if not line:
                translated_lines.append("")
                continue
            
            # Translate the entire line (not word-by-word)
            try:
                translated = self.translation_service.translate_text(
                    line, source_lang=source_lang, target_lang=target_lang
                )
                translated_lines.append(translated)
            except Exception as exc:
                # If translation fails, use an error message
                translated_lines.append(f"[Translation Error: {exc}]")
        
        return "\n".join(translated_lines)
