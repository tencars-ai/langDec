from __future__ import annotations

from dataclasses import dataclass
from typing import List

from ..services.translator import TranslationService


@dataclass(frozen=True)
class TokenPair:
    source_token: str
    target_token: str

    @property
    def column_width(self) -> int:
        return max(len(self.source_token), len(self.target_token))


class WordByWordDecoder:
    """
    Word-by-word decoder (Birkenbiel-style alignment).

    Responsibilities:
      - Tokenize input text into words (simple split)
      - Translate each word via a TranslationService
      - Align output in two lines (source above target)
      - Insert line breaks based on configured max line length
    """

    def __init__(self, translation_service: TranslationService):
        self.translation_service = translation_service

    def decode(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        max_line_length: int = 50,
    ) -> str:
        text = (text or "").strip()
        if not text:
            return ""

        tokens = self._tokenize(text)
        pairs = self._translate_tokens(tokens, source_lang, target_lang)
        return self._format_aligned(pairs, max_line_length=max_line_length)

    def _tokenize(self, text: str) -> List[str]:
        # Simple whitespace tokenization (can be improved later)
        return text.split()

    def _translate_tokens(
        self,
        tokens: List[str],
        source_lang: str,
        target_lang: str,
    ) -> List[TokenPair]:
        pairs: List[TokenPair] = []
        for token in tokens:
            try:
                translated = self.translation_service.translate_word(
                    token, source_lang=source_lang, target_lang=target_lang
                )
            except Exception as exc:
                translated = f"[ERR:{exc}]"
            pairs.append(TokenPair(source_token=token, target_token=translated))
        return pairs

    def _format_aligned(self, pairs: List[TokenPair], max_line_length: int) -> str:
        """
        Creates aligned two-line output with optional line breaks.

        Line breaking rule:
          - We keep a running sum of widths; when it reaches/exceeds max_line_length,
            we flush the current two lines.
          - If max_line_length <= 0: never force line breaks (single block).
        """
        if max_line_length <= 0:
            return self._format_single_block(pairs)

        output_lines: List[str] = []
        source_line = ""
        target_line = ""
        running_width = 0

        for pair in pairs:
            width = pair.column_width
            source_chunk = pair.source_token.ljust(width) + " "
            target_chunk = pair.target_token.ljust(width) + " "

            # Would adding this exceed max_line_length?
            if running_width + width >= max_line_length and source_line:
                output_lines.append(source_line.rstrip())
                output_lines.append(target_line.rstrip())
                output_lines.append("")  # blank line
                source_line = ""
                target_line = ""
                running_width = 0

            source_line += source_chunk
            target_line += target_chunk
            running_width += width

        if source_line or target_line:
            output_lines.append(source_line.rstrip())
            output_lines.append(target_line.rstrip())
            output_lines.append("")

        return "\n".join(output_lines).rstrip() + "\n"

    def _format_single_block(self, pairs: List[TokenPair]) -> str:
        source_line = ""
        target_line = ""
        for pair in pairs:
            width = pair.column_width
            source_line += pair.source_token.ljust(width) + " "
            target_line += pair.target_token.ljust(width) + " "
        return (source_line.rstrip() + "\n" + target_line.rstrip() + "\n")
