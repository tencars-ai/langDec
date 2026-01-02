"""
Dict.cc Translation Service - Database-backed word-to-word translation.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional, List, Dict
import psycopg2
from psycopg2.extras import RealDictCursor


@dataclass
class Translation:
    """Represents a single translation result."""
    word_source: str
    word_target: str
    gender_source: Optional[str] = None
    gender_target: Optional[str] = None
    word_class: Optional[str] = None
    subject_tags: Optional[List[str]] = None
    usage_context: Optional[str] = None
    additional_info_source: Optional[str] = None
    additional_info_target: Optional[str] = None
    
    def format_target(self) -> str:
        """Format the target word with gender and additional info."""
        result = self.word_target
        if self.gender_target:
            result = f"{result} {{{self.gender_target}}}"
        if self.additional_info_target:
            result = f"{result} [{self.additional_info_target}]"
        return result
    
    def format_full(self) -> str:
        """Full formatted output with all information."""
        target = self.format_target()
        if self.word_class:
            return f"{target} ({self.word_class})"
        return target
    
    def __str__(self) -> str:
        """String representation of translation - returns only the word."""
        return self.word_target


@dataclass
class DictCcTranslationService:
    """
    Translation service using dict.cc database for word-to-word translation.
    
    This service queries the PostgreSQL database loaded with dict.cc data
    to provide accurate, dictionary-based translations.
    
    Compatible with the TranslationService interface.
    """
    
    db_connection_string: Optional[str] = None
    source_language: str = 'pt'
    target_language: str = 'de'
    
    def __post_init__(self):
        """Initialize database connection string from environment if not provided."""
        if self.db_connection_string is None:
            self.db_connection_string = os.getenv('DATABASE_URL')
            if self.db_connection_string is None:
                raise ValueError("DATABASE_URL environment variable not set")
    
    @property
    def name(self) -> str:
        """Return the display name of this service."""
        return "dict.cc Dictionary"
    
    def _get_connection(self):
        """Get a database connection."""
        return psycopg2.connect(self.db_connection_string)
    
    def translate_word(
        self, 
        word: str, 
        source_lang: str, 
        target_lang: str
    ) -> str:
        """
        Translate a single word using dict.cc database.
        Returns only the best matching translation as a string (compatible with interface).
        
        Args:
            word: The word to translate
            source_lang: Source language code (e.g., "pt")
            target_lang: Target language code (e.g., "de")
            
        Returns:
            Translated word as string, or original word if no translation found
        """
        translations = self.get_translations(word, source_lang, target_lang, limit=1)
        if translations:
            return translations[0].word_target
        return word  # Return original word if no translation found
    
    def translate_text(self, text: str, source_lang: str, target_lang: str) -> str:
        """
        Translate complete text word-by-word (not natural translation).
        This is a fallback - dict.cc is primarily for word translations.
        
        Args:
            text: The text to translate
            source_lang: Source language code
            target_lang: Target language code
            
        Returns:
            Translated text with each word translated individually
        """
        words = text.split()
        translated_words = [self.translate_word(word, source_lang, target_lang) for word in words]
        return " ".join(translated_words)
    
    def get_translations(
        self, 
        word: str, 
        source_lang: Optional[str] = None, 
        target_lang: Optional[str] = None,
        limit: int = 10
    ) -> List[Translation]:
        """
        Get multiple translations for a word (advanced usage).
        
        Args:
            word: The word to translate
            source_lang: Source language code (e.g., "pt"), uses default if None
            target_lang: Target language code (e.g., "de"), uses default if None
            limit: Maximum number of translations to return (default: 10)
            
        Returns:
            List of Translation objects
        """
        source = source_lang or self.source_language
        target = target_lang or self.target_language
        
        conn = self._get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Search for exact match first, then partial matches
            query = """
                SELECT 
                    word_source, word_target, gender_source, gender_target,
                    word_class, subject_tags, usage_context,
                    additional_info_source, additional_info_target
                FROM dict_cc_translations
                WHERE source_language = %s 
                  AND target_language = %s
                  AND (
                      LOWER(word_source) = LOWER(%s)
                      OR LOWER(word_source) LIKE LOWER(%s)
                  )
                ORDER BY 
                    CASE WHEN LOWER(word_source) = LOWER(%s) THEN 0 ELSE 1 END,
                    word_source
                LIMIT %s
            """
            
            cursor.execute(query, (source, target, word, f"{word}%", word, limit))
            rows = cursor.fetchall()
            
            return [Translation(**row) for row in rows]
        
        finally:
            conn.close()
    
    def translate_word_bidirectional(
        self, 
        word: str,
        limit: int = 10
    ) -> Dict[str, List[Translation]]:
        """
        Search for a word in both directions (source->target and target->source).
        
        Useful when you're not sure if the word is in source or target language.
        
        Args:
            word: The word to search for
            limit: Maximum number of translations per direction
            
        Returns:
            Dictionary with keys 'forward' and 'reverse', each containing a list of translations
        """
        results = {
            'forward': [],
            'reverse': []
        }
        
        conn = self._get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Forward search (source -> target)
            query_forward = """
                SELECT 
                    word_source, word_target, gender_source, gender_target,
                    word_class, subject_tags, usage_context,
                    additional_info_source, additional_info_target
                FROM dict_cc_translations
                WHERE source_language = %s 
                  AND target_language = %s
                  AND (
                      LOWER(word_source) = LOWER(%s)
                      OR LOWER(word_source) LIKE LOWER(%s)
                  )
                ORDER BY 
                    CASE WHEN LOWER(word_source) = LOWER(%s) THEN 0 ELSE 1 END,
                    word_source
                LIMIT %s
            """
            
            cursor.execute(query_forward, (
                self.source_language, self.target_language, 
                word, f"{word}%", word, limit
            ))
            results['forward'] = [Translation(**row) for row in cursor.fetchall()]
            
            # Reverse search (target -> source)
            query_reverse = """
                SELECT 
                    word_target as word_source, word_source as word_target,
                    gender_target as gender_source, gender_source as gender_target,
                    word_class, subject_tags, usage_context,
                    additional_info_target as additional_info_source,
                    additional_info_source as additional_info_target
                FROM dict_cc_translations
                WHERE source_language = %s 
                  AND target_language = %s
                  AND (
                      LOWER(word_target) = LOWER(%s)
                      OR LOWER(word_target) LIKE LOWER(%s)
                  )
                ORDER BY 
                    CASE WHEN LOWER(word_target) = LOWER(%s) THEN 0 ELSE 1 END,
                    word_target
                LIMIT %s
            """
            
            cursor.execute(query_reverse, (
                self.source_language, self.target_language,
                word, f"{word}%", word, limit
            ))
            results['reverse'] = [Translation(**row) for row in cursor.fetchall()]
            
        finally:
            conn.close()
        
        return results
    
    def search_by_word_class(
        self,
        word: str,
        word_class: str,
        source_lang: Optional[str] = None,
        target_lang: Optional[str] = None,
        limit: int = 10
    ) -> List[Translation]:
        """
        Search for translations filtered by word class (noun, verb, adj, etc.).
        
        Args:
            word: The word to translate
            word_class: Word class to filter (e.g., "noun", "verb", "adj")
            source_lang: Source language code
            target_lang: Target language code
            limit: Maximum number of results
            
        Returns:
            List of Translation objects
        """
        source = source_lang or self.source_language
        target = target_lang or self.target_language
        
        conn = self._get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            query = """
                SELECT 
                    word_source, word_target, gender_source, gender_target,
                    word_class, subject_tags, usage_context,
                    additional_info_source, additional_info_target
                FROM dict_cc_translations
                WHERE source_language = %s 
                  AND target_language = %s
                  AND word_class = %s
                  AND (
                      LOWER(word_source) = LOWER(%s)
                      OR LOWER(word_source) LIKE LOWER(%s)
                  )
                ORDER BY word_source
                LIMIT %s
            """
            
            cursor.execute(query, (source, target, word_class, word, f"{word}%", limit))
            rows = cursor.fetchall()
            
            return [Translation(**row) for row in rows]
        
        finally:
            conn.close()
    
    
    def get_word_with_best_match(
        self,
        word: str,
        source_lang: Optional[str] = None,
        target_lang: Optional[str] = None
    ) -> Optional[Translation]:
        """
        Get the single best matching translation for a word.
        Prioritizes exact matches.
        
        Args:
            word: The word to translate
            source_lang: Source language code
            target_lang: Target language code
            
        Returns:
            Single Translation object or None if no match found
        """
        results = self.get_translations(word, source_lang, target_lang, limit=1)
        return results[0] if results else None


# Example usage
if __name__ == "__main__":
    # Example: How to use the DictCcTranslationService
    service = DictCcTranslationService(source_language='pt', target_language='de')
    
    # Simple word translation (compatible with interface)
    test_word = "casa"
    translation = service.translate_word(test_word, 'pt', 'de')
    print(f"Simple translation: '{test_word}' -> '{translation}'")
    
    # Get multiple translations (advanced usage)
    translations = service.get_translations(test_word, 'pt', 'de')
    print(f"\nAll translations for '{test_word}':")
    for i, trans in enumerate(translations, 1):
        print(f"{i}. {trans} (full: {trans.format_full()})")
    
    # Bidirectional search
    print(f"\nBidirectional search for 'Haus':")
    results = service.translate_word_bidirectional("Haus")
    print(f"Forward (pt->de): {len(results['forward'])} results")
    print(f"Reverse (de->pt): {len(results['reverse'])} results")
    
    # Search by word class
    print(f"\nNouns containing 'ab':")
    nouns = service.search_by_word_class("ab", "noun", limit=5)
    for noun in nouns:
        print(f"  - {noun}")
