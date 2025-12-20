# Enable modern type hints (allows referencing class names before definition)
from __future__ import annotations

# dataclass: Automatically generates __init__, __repr__, etc. based on class attributes
from dataclasses import dataclass
# List: Type hint for lists, e.g., List[str] means "a list of strings"
from typing import List

# Import from services → translation_service module
# TranslationService is the interface (Protocol) for translation providers
from services.translation_service import TranslationService


# @dataclass creates a simple data container class automatically
# frozen=True makes this class immutable (can't change values after creation)
@dataclass(frozen=True)
class TokenPair:
    """Represents a pair of tokens: source word and its translation.
    
    Example: TokenPair(source_token="hello", target_token="hallo")
    """
    source_token: str  # The original word (e.g., "hello")
    target_token: str  # The translated word (e.g., "hallo")

    # @property makes this method accessible like an attribute: pair.column_width instead of pair.column_width()
    @property
    def column_width(self) -> int:
        """Calculate the column width needed to display both words aligned.
        
        Returns the length of the longer word so both can fit in the same column.
        Example: "hello" (5) and "hallo" (5) → returns 5
                 "hi" (2) and "hallo" (5) → returns 5
        """
        return max(len(self.source_token), len(self.target_token))


class WordByWordDecoder:
    """
    Word-by-word decoder (Birkenbihl-style alignment).
    
    This is the core class that handles the decoding process.

    Responsibilities:
      - Tokenize input text into words (simple split by spaces)
      - Translate each word individually via a TranslationService
      - Align output in two lines (source above target)
      - Insert line breaks based on configured max line length

    """

    # __init__ is the constructor - called when creating a new instance
    # self refers to the instance being created
    def __init__(self, translation_service: TranslationService):
        """Initialize the decoder with a translation service.
        
        Args:
            translation_service: Any object that implements the translate_word method
        """
        # Store the translation service as an instance variable (attribute)
        # self.xyz means "this variable belongs to this specific instance"
        self.translation_service = translation_service

    def decode(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        max_line_length: int,
    ) -> tuple:
        """Main method to decode text with sentence-based translation and word alignment.
        
        New approach:
        1. Translate entire text for maximum context
        2. Split both source and translated text into sentences
        3. Align words within each sentence pair
        
        Args:
            text: The text to decode (can be multiple sentences)
            source_lang: Language code of input text (e.g., "en")
            target_lang: Language code for translation (e.g., "de")
            max_line_length: Maximum characters per line before breaking
            
        Returns:
            Tuple of (formatted_string, debug_translations_list)
        """
        # Clean up the input: if text is None, use ""
        text = (text or "").strip()
        
        # Early return: if text is empty, just return empty string and empty debug list
        if not text:
            return "", []

        # Debug collection for individual translations
        debug_translations = []

        # Step 1: Translate the ENTIRE text at once for maximum context
        translated_text = self.translation_service.translate_text(
            text, source_lang=source_lang, target_lang=target_lang
        )
        
        # Step 2: Split both texts into sentences (at . or newlines)
        source_sentences = self._split_into_sentences(text)
        target_sentences = self._split_into_sentences(translated_text)
        
        # Step 3: Process each sentence pair
        decoded_lines = []
        for source_sent, target_sent in zip(source_sentences, target_sentences):
            # Tokenize both sentences
            source_tokens = self._tokenize(source_sent)
            target_tokens = self._tokenize(target_sent)
            
            # Align words and create TokenPairs (also collects debug info)
            pairs, sentence_debug = self._align_sentence_words(
                source_tokens, target_tokens, source_lang, target_lang
            )
            
            # Collect debug info
            debug_translations.extend(sentence_debug)
            
            # Format the aligned pairs
            decoded_lines.append(self._format_aligned(pairs, max_line_length=max_line_length))
        
        return "\n".join(decoded_lines), debug_translations

    # Methods starting with _ are "private" - meant for internal use only
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences at periods or newlines.
        
        Args:
            text: Input text to split
            
        Returns:
            List of sentences
            
        Example:
            "Hello world. How are you?" → ["Hello world", "How are you"]
            "Line 1\nLine 2" → ["Line 1", "Line 2"]
        """
        import re
        # Split on period (followed by space or end) or newline
        sentences = re.split(r'[.\n]+', text)
        # Remove empty strings and strip whitespace
        return [s.strip() for s in sentences if s.strip()]
    
    def _tokenize(self, text: str) -> List[str]:
        """Split text into individual words.
        
        Args:
            text: Input text to split
            
        Returns:
            List of words (tokens)
            
        Example:
            "hello world" → ["hello", "world"]
        """
        # Simple whitespace tokenization
        # .split() without arguments splits on any whitespace and removes empty strings
        return text.split()

    def _align_sentence_words(
        self,
        source_tokens: List[str],
        target_tokens: List[str],
        source_lang: str,
        target_lang: str,
    ) -> tuple:
        """Align words from source and target sentences using improved hybrid approach.
        
        Strategy (4-pass approach):
        1. Translate ALL source words individually
        2. Search each individual translation in ENTIRE target sentence
        3. Mark found words as "matched" (source → target mapping)
        4. Fill remaining gaps with positional alignment
        
        This handles different word order and sentence structures much better.
        
        Args:
            source_tokens: Words from source sentence
            target_tokens: Words from translated target sentence
            source_lang: Source language code
            target_lang: Target language code
            
        Returns:
            Tuple of (List of TokenPair objects, debug_info list)
        """
        # Debug info collection
        debug_info = []
        
        # Pass 1: Translate all source words individually
        individual_translations = []
        for token in source_tokens:
            try:
                translated = self.translation_service.translate_word(
                    token, source_lang=source_lang, target_lang=target_lang
                )
                individual_translations.append(translated)
                # Add to debug
                debug_info.append({
                    "source": token,
                    "translation": translated,
                    "used": "pending"
                })
            except Exception:
                individual_translations.append(None)
        
        # Track which target words have been matched
        target_matched = [False] * len(target_tokens)
        # Track which source words have been matched
        source_matches = [None] * len(source_tokens)  # None or target_index
        
        # Pass 2: Search for exact matches in target sentence
        for i, (source_token, individual_trans) in enumerate(zip(source_tokens, individual_translations)):
            if individual_trans is None:
                continue
                
            # Search for this translation in ALL target tokens
            for j, target_token in enumerate(target_tokens):
                if target_matched[j]:
                    continue  # Already matched
                    
                # Case-insensitive comparison
                if target_token.lower() == individual_trans.lower():
                    # Found a match!
                    source_matches[i] = j
                    target_matched[j] = True
                    # Update debug info
                    debug_info[i]["used"] = "✓ Found in context"
                    break
            
            # If no match found, mark as not used
            if source_matches[i] is None and individual_trans is not None:
                debug_info[i]["used"] = "✗ Not in context"
        
        # Pass 3: Create TokenPairs from confirmed matches
        pairs: List[TokenPair] = []
        
        for i, source_token in enumerate(source_tokens):
            if source_matches[i] is not None:
                # We have a confirmed match
                target_token = target_tokens[source_matches[i]]
            else:
                # No match found - use positional alignment if possible
                if i < len(target_tokens) and not target_matched[i]:
                    target_token = target_tokens[i]
                    target_matched[i] = True
                else:
                    # Find first unmatched target word
                    target_token = None
                    for j, matched in enumerate(target_matched):
                        if not matched:
                            target_token = target_tokens[j]
                            target_matched[j] = True
                            break
                    
                    if target_token is None:
                        target_token = "---"
            
            pairs.append(TokenPair(source_token=source_token, target_token=target_token))
        
        # Pass 4: Add remaining unmatched target words
        for j, (target_token, matched) in enumerate(zip(target_tokens, target_matched)):
            if not matched:
                # This target word wasn't aligned to any source word
                pairs.append(TokenPair(source_token="---", target_token=target_token))
        
        return pairs, debug_info

    def _translate_tokens(
        self,
        tokens: List[str],  # List of words to translate
        source_lang: str,   # Source language code
        target_lang: str,   # Target language code
    ) -> List[TokenPair]:
        """Translate each token and create TokenPair objects.
        
        Args:
            tokens: List of words to translate
            source_lang: Source language code (e.g., "en")
            target_lang: Target language code (e.g., "de")
            
        Returns:
            List of TokenPair objects (original word + translation)
        """
        # Create an empty list to store the pairs
        pairs: List[TokenPair] = []
        
        # Loop through each word
        for token in tokens:
            # try-except block handles errors gracefully
            try:
                # Call the translation service to translate this word
                translated = self.translation_service.translate_word(
                    token, source_lang=source_lang, target_lang=target_lang
                )
            except Exception as exc:
                # If translation fails, use an error message instead
                # f"..." is an f-string: formats the exception into the string
                translated = f"[ERR:{exc}]"
            
            # Create a TokenPair and add it to our list
            pairs.append(TokenPair(source_token=token, target_token=translated))
        
        return pairs

    def _format_aligned(self, pairs: List[TokenPair], max_line_length: int) -> str:
        """
        Creates aligned two-line output with optional line breaks.
        
        Example output:
            hello  world  how
            hallo  Welt   wie
            
            are   you
            bist  du

        Line breaking rule:
          - We keep a running sum of widths; when it reaches/exceeds max_line_length,
            we flush the current two lines.
          - If max_line_length <= 0: never force line breaks (single block).
        """
        # Special case: no line breaks wanted
        if max_line_length <= 0:
            return self._format_single_block(pairs)

        # List to collect all output lines
        output_lines: List[str] = []
        
        # Variables to build current line pair
        source_line = ""     # Current source language line being built
        target_line = ""     # Current target language line being built
        running_width = 0    # Track how many characters we've used so far

        # Process each word pair
        for pair in pairs:
            # Get the width needed for this column (length of longer word)
            width = pair.column_width
            
            # .ljust(width) pads the string with spaces to reach 'width' characters
            # Example: "hi".ljust(5) → "hi   "
            source_chunk = pair.source_token.ljust(width) + " "
            target_chunk = pair.target_token.ljust(width) + " "

            # Check: would adding this word (with space) exceed our line length limit?
            # We check if adding width+1 (word + space) would exceed the limit
            if running_width > 0 and running_width + width + 1 > max_line_length:
                # Yes! Save current lines and start new ones
                # .rstrip() removes trailing spaces
                output_lines.append(source_line.rstrip())
                output_lines.append(target_line.rstrip())
                output_lines.append("")  # Add blank line between blocks
                
                # Reset for next line
                source_line = ""
                target_line = ""
                running_width = 0

            # Add the word chunks to current lines
            source_line += source_chunk
            target_line += target_chunk
            running_width += width + 1  # +1 for the space after each word

        # Don't forget the last line if there's anything left
        if source_line or target_line:
            output_lines.append(source_line.rstrip())
            output_lines.append(target_line.rstrip())
            output_lines.append("")  # Blank line at end

        # Join all lines with newline characters
        # .rstrip() removes trailing newlines, then we add one back
        return "\n".join(output_lines).rstrip() + "\n"

    def _format_single_block(self, pairs: List[TokenPair]) -> str:
        """Format all pairs into a single two-line block (no line breaks).
        
        Used when max_line_length is 0 or negative.
        
        Returns:
            Two lines: source words on top, translations below, aligned by column
        """
        source_line = ""  # Build the top line (original language)
        target_line = ""  # Build the bottom line (translation)
        
        # Process all pairs at once (no line breaking)
        for pair in pairs:
            # Get column width for alignment
            width = pair.column_width
            
            # Add word padded to column width + extra space
            source_line += pair.source_token.ljust(width) + " "
            target_line += pair.target_token.ljust(width) + " "
        
        # Return both lines with trailing spaces removed
        # \n is newline character
        return (source_line.rstrip() + "\n" + target_line.rstrip() + "\n")
