from __future__ import annotations

import concurrent.futures
import json
import re
from dataclasses import dataclass
from typing import List

from services.translation_service import TranslationService


@dataclass(frozen=True)
class DecoderResult:
    """Result from WordByWordDecoder.decode()."""
    aligned_text: str
    comments: str = ""
    debug_info: str = ""  # raw LLM payload(s) as formatted JSON when debug=True, else ""


@dataclass(frozen=True)
class TokenPair:
    """A source token paired with its target translation."""
    source_token: str
    target_token: str

    @property
    def column_width(self) -> int:
        return max(len(self.source_token or ""), len(self.target_token or ""))


@dataclass(frozen=True)
class PreprocessedLine:
    """One input line after list-marker stripping.

    `raw_idx` is the line's index in the original split-by-"\n" input. The
    marker — if any — is preserved here so the renderer can prepend it back
    onto the aligned output, while the decoder itself never sees it.
    """
    raw_idx: int
    leading_marker: str   # "1.", "-", or "" if no list marker
    content: str          # the line with the marker stripped, trimmed


_LIST_MARKER_PATTERNS = [
    re.compile(r"^\s*(\d+[\.\)])\s+"),       # 1.  2)  42.
    re.compile(r"^\s*([a-zA-Z][\.\)])\s+"),  # a.  B)
    re.compile(r"^\s*([\-*•·])\s+"),         # -   *   •   ·
]

# Line ends a sentence if it ends with . ! ? (allow trailing whitespace/quotes).
_SENTENCE_END_RE = re.compile(r'[.!?][\s"\')\]]*$')


class WordByWordDecoder:
    """Birkenbihl-style word-by-word decoder.

    Uses the LLM's plain-text decode output when the translation service
    provides `translate_birkenbihl_full`; otherwise falls back to per-word
    calls. Long inputs are chunked along paragraph and sentence boundaries
    and decoded in parallel.
    """

    _TARGET_LINES_PER_CHUNK = 10   # aim for this many source lines per LLM call
    _MAX_LINES_PER_CHUNK    = 15   # hard cap before forcing a split
    _MIN_LINES_PER_CHUNK    = 2    # merge trailing tail-chunks below this
    _MAX_PARALLEL_CHUNKS    = 3    # concurrent LLM calls

    def __init__(self, translation_service: TranslationService, debug: bool = False):
        self.translation_service = translation_service
        self.debug = debug

    # `natural_translation` is accepted but ignored — it's still in the signature
    # because callers may pass it; we removed it as an LLM input intentionally.
    def decode(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        max_line_length: int,
        natural_translation: str = "",
    ) -> DecoderResult:
        text = (text or "").strip()
        if not text:
            return DecoderResult(aligned_text="", comments="")

        pre = self._preprocess_lines(text)
        if hasattr(self.translation_service, "translate_birkenbihl_full"):
            return self._decode_llm(pre, source_lang, target_lang, max_line_length)
        return self._decode_per_word(pre, source_lang, target_lang, max_line_length)

    # ------------------------------------------------------------------
    # Pre-processing
    # ------------------------------------------------------------------

    def _preprocess_lines(self, text: str) -> list[PreprocessedLine]:
        result: list[PreprocessedLine] = []
        for i, raw in enumerate(text.split("\n")):
            marker, content = self._strip_list_marker(raw)
            result.append(
                PreprocessedLine(raw_idx=i, leading_marker=marker, content=content.strip())
            )
        return result

    @staticmethod
    def _strip_list_marker(raw: str) -> tuple[str, str]:
        for pattern in _LIST_MARKER_PATTERNS:
            m = pattern.match(raw)
            if m:
                return m.group(1), raw[m.end():]
        return "", raw

    # ------------------------------------------------------------------
    # LLM path (chunked + parallel)
    # ------------------------------------------------------------------

    def _decode_llm(
        self,
        pre: list[PreprocessedLine],
        source_lang: str,
        target_lang: str,
        max_line_length: int,
    ) -> DecoderResult:
        chunks = self._build_chunks(pre)
        if not chunks:
            return DecoderResult(aligned_text="", comments="")

        line_results: dict[int, dict] = {}
        comments_parts: list[str] = []
        debug_parts: list[str] = []
        max_workers = min(len(chunks), self._MAX_PARALLEL_CHUNKS)

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_chunk = {
                executor.submit(self._decode_chunk, chunk, source_lang, target_lang): (n, chunk)
                for n, chunk in enumerate(chunks, start=1)
            }
            for future in concurrent.futures.as_completed(future_to_chunk):
                n, chunk = future_to_chunk[future]
                first_idx = chunk[0].raw_idx + 1  # 1-based input line numbers
                last_idx = chunk[-1].raw_idx + 1
                chunk_label = f"chunk {n}/{len(chunks)} (lines {first_idx}-{last_idx})"
                try:
                    result = future.result()
                    line_results.update(result.get("line_results", {}))
                    c = result.get("comments", "")
                    if c:
                        comments_parts.append(c)
                    if self.debug:
                        payload = result.get("raw_payload")
                        debug_parts.append(
                            f"=== {chunk_label} ===\n"
                            + (json.dumps(payload, indent=2, ensure_ascii=False)
                               if payload is not None else "(no payload)")
                        )
                except Exception as exc:
                    err = f"[{chunk_label}: {type(exc).__name__}: {exc}]"
                    comments_parts.append(err)
                    if self.debug:
                        debug_parts.append(f"=== {chunk_label} ===\nERROR: {type(exc).__name__}: {exc}")

        return self._assemble(
            pre, line_results, max_line_length,
            comments="\n\n".join(comments_parts),
            debug_info="\n\n".join(debug_parts),
        )

    # ------------------------------------------------------------------
    # Chunking — paragraph- and sentence-aware
    # ------------------------------------------------------------------

    def _build_chunks(
        self, pre: list[PreprocessedLine],
    ) -> list[list[PreprocessedLine]]:
        """Group non-empty preprocessed lines into chunks for the LLM.

        Strategy:
          1. Split at blank lines into paragraphs (semantic groups).
          2. Paragraphs <= MAX go as one chunk.
          3. Longer paragraphs are sliced at sentence boundaries when possible,
             aiming for TARGET lines per chunk, never exceeding MAX.
          4. A trailing chunk smaller than MIN is merged into the previous one
             when that keeps it within MAX.
        """
        paragraphs = self._split_into_paragraphs(pre)

        chunks: list[list[PreprocessedLine]] = []
        for para in paragraphs:
            if len(para) <= self._MAX_LINES_PER_CHUNK:
                chunks.append(para)
            else:
                chunks.extend(self._slice_paragraph(para))

        # Merge a short tail into the previous chunk if it stays within MAX.
        if (
            len(chunks) >= 2
            and len(chunks[-1]) < self._MIN_LINES_PER_CHUNK
            and len(chunks[-1]) + len(chunks[-2]) <= self._MAX_LINES_PER_CHUNK
        ):
            chunks[-2].extend(chunks[-1])
            chunks.pop()

        return chunks

    @staticmethod
    def _split_into_paragraphs(
        pre: list[PreprocessedLine],
    ) -> list[list[PreprocessedLine]]:
        paragraphs: list[list[PreprocessedLine]] = []
        current: list[PreprocessedLine] = []
        for p in pre:
            if p.content:
                current.append(p)
            elif current:
                paragraphs.append(current)
                current = []
        if current:
            paragraphs.append(current)
        return paragraphs

    def _slice_paragraph(
        self, para: list[PreprocessedLine],
    ) -> list[list[PreprocessedLine]]:
        """Slice an oversized paragraph at sentence boundaries when possible."""
        result: list[list[PreprocessedLine]] = []
        current: list[PreprocessedLine] = []
        for p in para:
            current.append(p)
            ends_sentence = bool(_SENTENCE_END_RE.search(p.content))
            big_enough = len(current) >= self._TARGET_LINES_PER_CHUNK
            at_cap = len(current) >= self._MAX_LINES_PER_CHUNK
            if at_cap or (big_enough and ends_sentence):
                result.append(current)
                current = []
        if current:
            result.append(current)
        return result

    def _decode_chunk(
        self,
        chunk: list[PreprocessedLine],
        source_lang: str,
        target_lang: str,
    ) -> dict:
        """Send one chunk to `translate_birkenbihl_full` and remap indices.

        The LLM service returns `line_results` keyed by indices into the chunk
        text's split-by-newline lines (0…N-1). We remap those keys back to the
        chunk lines' original `raw_idx` in the user's input.
        """
        chunk_text = "\n".join(p.content for p in chunk)
        raw_result = self.translation_service.translate_birkenbihl_full(
            chunk_text, source_lang, target_lang,
        )
        chunk_local = raw_result.get("line_results", {}) or {}
        local_indices = sorted(chunk_local.keys())
        remapped: dict[int, dict] = {}
        for j, p in enumerate(chunk):
            if j < len(local_indices):
                remapped[p.raw_idx] = chunk_local[local_indices[j]]
        return {
            "line_results": remapped,
            "comments": raw_result.get("comments", ""),
            "raw_payload": raw_result.get("raw_payload"),
        }

    # ------------------------------------------------------------------
    # Per-word fallback path (Google / Argos)
    # ------------------------------------------------------------------

    def _decode_per_word(
        self,
        pre: list[PreprocessedLine],
        source_lang: str,
        target_lang: str,
        max_line_length: int,
    ) -> DecoderResult:
        line_results: dict[int, dict] = {}
        for p in pre:
            if not p.content:
                continue
            tokens = self._tokenize(p.content)
            pairs = self._translate_tokens(tokens, source_lang, target_lang)
            line_results[p.raw_idx] = {"words": [pair.target_token for pair in pairs]}
        return self._assemble(pre, line_results, max_line_length, comments="")

    # ------------------------------------------------------------------
    # Assembly & formatting
    # ------------------------------------------------------------------

    def _assemble(
        self,
        pre: list[PreprocessedLine],
        line_results: dict[int, dict],
        max_line_length: int,
        comments: str,
        debug_info: str = "",
    ) -> DecoderResult:
        """Build the aligned output preserving original line order + list markers."""
        out: list[str] = []
        for p in pre:
            if not p.content:
                out.append("")
                continue
            tokens = self._tokenize(p.content)
            translated_words = line_results.get(p.raw_idx, {}).get("words", [])
            pairs = [
                TokenPair(source_token=src, target_token=tgt)
                for src, tgt in zip(tokens, translated_words)
            ]
            aligned = self._format_aligned(pairs, max_line_length=max_line_length)
            if p.leading_marker:
                aligned = self._prepend_marker(aligned, p.leading_marker)
            out.append(aligned)
        return DecoderResult(
            aligned_text="\n".join(out),
            comments=comments,
            debug_info=debug_info,
        )

    @staticmethod
    def _prepend_marker(aligned: str, marker: str) -> str:
        """Prefix the first line with the marker; indent every following non-empty line."""
        indent = " " * (len(marker) + 1)
        lines = aligned.split("\n")
        if not lines:
            return aligned
        lines[0] = f"{marker} {lines[0]}"
        for i in range(1, len(lines)):
            if lines[i]:
                lines[i] = f"{indent}{lines[i]}"
        return "\n".join(lines)

    def _tokenize(self, text: str) -> List[str]:
        return text.split()

    def _translate_tokens(
        self, tokens: List[str], source_lang: str, target_lang: str,
    ) -> List[TokenPair]:
        pairs: List[TokenPair] = []
        for token in tokens:
            try:
                translated = self.translation_service.translate_word(
                    token, source_lang=source_lang, target_lang=target_lang,
                ) or token
            except Exception as exc:
                translated = f"[ERR:{exc}]"
            pairs.append(TokenPair(source_token=token, target_token=translated))
        return pairs

    def _format_aligned(self, pairs: List[TokenPair], max_line_length: int) -> str:
        """Two-line aligned output with optional line wrapping at max_line_length."""
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

            if running_width > 0 and running_width + width + 1 > max_line_length:
                output_lines.append(source_line.rstrip())
                output_lines.append(target_line.rstrip())
                output_lines.append("")
                source_line = ""
                target_line = ""
                running_width = 0

            source_line += source_chunk
            target_line += target_chunk
            running_width += width + 1

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
        return source_line.rstrip() + "\n" + target_line.rstrip() + "\n"
