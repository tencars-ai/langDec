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
    ) -> str:
        """Main method to decode text word-by-word.
        
        Args:
            text: The text to decode (can be multiple words)
            source_lang: Language code of input text (e.g., "en")
            target_lang: Language code for translation (e.g., "de")
            max_line_length: Maximum characters per line before breaking
            
        Returns:
            Formatted string with aligned translations
        """
        # Clean up the input: if text is None, use ""
        text = (text or "").strip()
        
        # Early return: if text is empty, just return empty string
        if not text:
            return ""

        # Process each line separately to preserve line breaks
        lines = text.split('\n')
        decoded_lines = []
        
        for line in lines:
            line = line.strip()
            # Skip empty lines but preserve them in output
            if not line:
                decoded_lines.append("")
                continue
                
            # Step 1: Split line into individual words
            tokens = self._tokenize(line)
            
            # Step 2: Translate each word and create TokenPair objects
            pairs = self._translate_tokens(tokens, source_lang, target_lang)
            
            # Step 3: Format the pairs into aligned two-line output with line breaks
            decoded_lines.append(self._format_aligned(pairs, max_line_length=max_line_length))
        
        return "\n".join(decoded_lines)

    # Methods starting with _ are "private" - meant for internal use only
    def _tokenize(self, text: str) -> List[str]:
        """Split text into individual words.
        
        Args:
            text: Input text to split
            
        Returns:
            List of words (tokens)
            
        Example:
            "hello world" → ["hello", "world"]
        """
        # Simple whitespace tokenization (can be improved later)
        # .split() without arguments splits on any whitespace and removes empty strings
        return text.split()

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

            # Check: would adding this word exceed our line length limit?
            if running_width + width >= max_line_length and source_line:
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
