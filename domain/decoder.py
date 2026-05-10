# Enable modern type hints (allows referencing class names before definition)
from __future__ import annotations

import concurrent.futures
from dataclasses import dataclass
from typing import List

from services.translation_service import TranslationService


# @dataclass creates a simple data container class automatically
# frozen=True makes this class immutable (can't change values after creation)
@dataclass(frozen=True)
class DecoderResult:
    """Result from WordByWordDecoder.decode()."""
    aligned_text: str
    comments: str = ""


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
        return max(len(self.source_token or ""), len(self.target_token or ""))


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
        natural_translation: str = "",
    ) -> DecoderResult:
        """Main method to decode text word-by-word.

        Returns a DecoderResult with aligned_text and optional LLM comments.

        If natural_translation is provided and the service supports it, uses a
        two-pass approach (single LLM call for all lines).  Otherwise falls back
        to the legacy batch (one LLM call per line) or per-word path.
        """
        text = (text or "").strip()
        if not text:
            return DecoderResult(aligned_text="", comments="")

        # Two-pass: send entire text + natural translation in one LLM call
        if natural_translation and hasattr(self.translation_service, "translate_birkenbihl_full"):
            return self._decode_two_pass(text, source_lang, target_lang, max_line_length, natural_translation)

        if hasattr(self.translation_service, "translate_birkenbihl"):
            return self._decode_batch(text, source_lang, target_lang, max_line_length)
        return self._decode_per_word(text, source_lang, target_lang, max_line_length)

    _CHUNK_SIZE = 10  # lines per LLM call — balances speed vs. rate limits

    def _decode_two_pass(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        max_line_length: int,
        natural_translation: str,
    ) -> DecoderResult:
        """Two-pass: chunk text into ~10-line groups, decode each chunk in parallel."""
        raw_lines = text.split("\n")
        # Collect non-empty lines with their original index
        non_empty = [(i, line.strip()) for i, line in enumerate(raw_lines) if line.strip()]
        if not non_empty:
            return DecoderResult(aligned_text="", comments="")

        # Build chunks of consecutive lines
        chunks: list[list[tuple[int, str]]] = []
        for k in range(0, len(non_empty), self._CHUNK_SIZE):
            chunks.append(non_empty[k : k + self._CHUNK_SIZE])

        # Process chunks in parallel (max 3 concurrent to avoid rate limits)
        all_line_results: dict[int, dict] = {}
        all_comments: list[str] = []
        max_workers = min(len(chunks), 3)

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_chunk = {
                executor.submit(
                    self._decode_chunk, chunk, source_lang, target_lang, natural_translation,
                ): chunk
                for chunk in chunks
            }
            for future in concurrent.futures.as_completed(future_to_chunk):
                try:
                    result = future.result()
                    all_line_results.update(result.get("line_results", {}))
                    comments = result.get("comments", "")
                    if comments:
                        all_comments.append(comments)
                except Exception as exc:
                    chunk = future_to_chunk[future]
                    all_comments.append(f"[Chunk error: {exc}]")

        # Assemble final output preserving original line order
        decoded_lines = []
        for i, raw_line in enumerate(raw_lines):
            line = raw_line.strip()
            if not line:
                decoded_lines.append("")
                continue
            lr = all_line_results.get(i, {"words": [], "comments": ""})
            tokens = self._tokenize(line)
            translated_words = lr.get("words", [])
            pairs = [
                TokenPair(source_token=src, target_token=tgt)
                for src, tgt in zip(tokens, translated_words)
            ]
            decoded_lines.append(self._format_aligned(pairs, max_line_length=max_line_length))

        return DecoderResult(
            aligned_text="\n".join(decoded_lines),
            comments="\n\n".join(all_comments),
        )

    def _decode_chunk(
        self,
        chunk: list[tuple[int, str]],
        source_lang: str,
        target_lang: str,
        natural_translation: str,
    ) -> dict:
        """Decode a chunk of lines via translate_birkenbihl_full.

        Returns line_results keyed by the ORIGINAL line index (not chunk-local).
        """
        chunk_text = "\n".join(line for _, line in chunk)
        raw_result = self.translation_service.translate_birkenbihl_full(
            chunk_text, source_lang, target_lang, natural_translation,
        )
        # Re-key from chunk-local indices (0, 1, 2 …) to original text indices
        chunk_local = raw_result.get("line_results", {})
        remapped: dict[int, dict] = {}
        local_indices = sorted(chunk_local.keys())
        for j, orig_idx in enumerate(idx for idx, _ in chunk):
            if j < len(local_indices):
                remapped[orig_idx] = chunk_local[local_indices[j]]
        return {"line_results": remapped, "comments": raw_result.get("comments", "")}

    def _decode_batch(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        max_line_length: int,
    ) -> DecoderResult:
        """Batch path: all non-empty lines dispatched in parallel, one LLM call each."""
        raw_lines = text.split("\n")
        non_empty = [(i, line.strip()) for i, line in enumerate(raw_lines) if line.strip()]

        # Dispatch all lines concurrently (I/O-bound LLM calls → threads work well).
        line_results: dict[int, dict] = {}
        all_comments: list[str] = []

        max_workers = min(len(non_empty), 8)
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_idx = {
                executor.submit(
                    self.translation_service.translate_birkenbihl, line, source_lang, target_lang
                ): i
                for i, line in non_empty
            }
            for future in concurrent.futures.as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    line_results[idx] = future.result()
                except Exception as exc:
                    all_comments.append(f"[Line {idx + 1} error: {exc}]")
                    line_results[idx] = {"words": [], "comments": ""}

        decoded_lines = []
        for i, raw_line in enumerate(raw_lines):
            line = raw_line.strip()
            if not line:
                decoded_lines.append("")
                continue
            result = line_results[i]
            tokens = self._tokenize(line)
            translated_words = result.get("words", [])
            comments = result.get("comments", "")
            if comments:
                all_comments.append(comments)
            pairs = [
                TokenPair(source_token=src, target_token=tgt)
                for src, tgt in zip(tokens, translated_words)
            ]
            decoded_lines.append(self._format_aligned(pairs, max_line_length=max_line_length))

        return DecoderResult(
            aligned_text="\n".join(decoded_lines),
            comments="\n\n".join(all_comments),
        )

    def _decode_per_word(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        max_line_length: int,
    ) -> DecoderResult:
        """Per-word fallback path (Google/Argos services)."""
        decoded_lines = []
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                decoded_lines.append("")
                continue
            tokens = self._tokenize(line)
            pairs = self._translate_tokens(tokens, source_lang, target_lang)
            decoded_lines.append(self._format_aligned(pairs, max_line_length=max_line_length))
        return DecoderResult(aligned_text="\n".join(decoded_lines), comments="")

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
                ) or token
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
