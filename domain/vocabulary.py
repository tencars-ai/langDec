"""
VocabularyManager – CRUD for user_dictionary with deduplication and frequency tracking.

Card fields (6):
  source_word          – foreign language word/phrase
  target_word          – mother tongue: natural translation
  word_target_decoded  – mother tongue: literal/decoded translation (Birkenbihl)
  word_class           – noun, verb, adj, adv, phrase, ...
  example_sentence     – example sentence in source language
  explanation          – notes, grammar hints, context
"""
from __future__ import annotations

from typing import Optional
from services.db_service import DBService


class VocabularyManager:
    """Manages the personal dictionary for a single user."""

    def __init__(self, db: DBService):
        self._db = db

    def add_word(
        self,
        user_id: str,
        source_word: str,
        target_word: str,
        source_language: str,
        target_language: str,
        word_class: Optional[str] = None,
        word_target_decoded: Optional[str] = None,
        example_sentence: Optional[str] = None,
        explanation: Optional[str] = None,
        source_text_id: Optional[str] = None,
    ) -> None:
        """
        Insert a word pair or increment its frequency if it already exists.
        Also creates a vocab_card for the entry if one does not yet exist.
        """
        self._db.execute_write(
            """
            INSERT INTO user_dictionary
                (user_id, source_word, target_word, source_language, target_language,
                 word_class, word_target_decoded, example_sentence, explanation, source_text_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id, source_word, source_language, target_language) DO UPDATE
                SET frequency = user_dictionary.frequency + 1,
                    target_word = EXCLUDED.target_word,
                    word_class = COALESCE(EXCLUDED.word_class, user_dictionary.word_class),
                    word_target_decoded = COALESCE(EXCLUDED.word_target_decoded, user_dictionary.word_target_decoded),
                    example_sentence = COALESCE(EXCLUDED.example_sentence, user_dictionary.example_sentence),
                    explanation = COALESCE(EXCLUDED.explanation, user_dictionary.explanation)
            """,
            (
                user_id, source_word, target_word, source_language, target_language,
                word_class, word_target_decoded, example_sentence, explanation, source_text_id,
            ),
        )
        entry = self._db.execute_one(
            """
            SELECT user_dictionary_id FROM user_dictionary
            WHERE user_id = %s AND source_word = %s
              AND source_language = %s AND target_language = %s
            """,
            (user_id, source_word, source_language, target_language),
        )
        if entry:
            self._db.execute_write(
                """
                INSERT INTO vocab_cards (user_id, user_dictionary_id)
                VALUES (%s, %s)
                ON CONFLICT (user_id, user_dictionary_id) DO NOTHING
                """,
                (user_id, str(entry["user_dictionary_id"])),
            )

    def get_words(
        self,
        user_id: str,
        source_language: Optional[str] = None,
        target_language: Optional[str] = None,
        search: Optional[str] = None,
    ) -> list[dict]:
        """Return dictionary entries for a user, with optional filters."""
        conditions = ["user_id = %s"]
        params: list = [user_id]

        if source_language:
            conditions.append("source_language = %s")
            params.append(source_language)
        if target_language:
            conditions.append("target_language = %s")
            params.append(target_language)
        if search:
            conditions.append("(source_word ILIKE %s OR target_word ILIKE %s OR word_target_decoded ILIKE %s)")
            params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])

        where = " AND ".join(conditions)
        return self._db.execute(
            f"""
            SELECT user_dictionary_id, source_word, target_word, word_target_decoded,
                   source_language, target_language,
                   word_class, example_sentence, explanation, frequency, created_at
            FROM user_dictionary
            WHERE {where}
            ORDER BY frequency DESC, source_word
            """,
            tuple(params),
        )

    def get_word(self, user_id: str, word_id: str) -> Optional[dict]:
        return self._db.execute_one(
            "SELECT * FROM user_dictionary WHERE user_dictionary_id = %s AND user_id = %s",
            (word_id, user_id),
        )

    def update_word(
        self,
        user_id: str,
        word_id: str,
        target_word: Optional[str] = None,
        word_target_decoded: Optional[str] = None,
        word_class: Optional[str] = None,
        example_sentence: Optional[str] = None,
        explanation: Optional[str] = None,
    ) -> None:
        """Update editable fields of a dictionary entry."""
        self._db.execute_write(
            """
            UPDATE user_dictionary
            SET target_word         = COALESCE(%s, target_word),
                word_target_decoded = COALESCE(%s, word_target_decoded),
                word_class          = COALESCE(%s, word_class),
                example_sentence    = COALESCE(%s, example_sentence),
                explanation         = COALESCE(%s, explanation)
            WHERE user_dictionary_id = %s AND user_id = %s
            """,
            (target_word, word_target_decoded, word_class, example_sentence, explanation, word_id, user_id),
        )

    def delete_word(self, user_id: str, word_id: str) -> None:
        self._db.execute_write(
            "DELETE FROM user_dictionary WHERE user_dictionary_id = %s AND user_id = %s",
            (word_id, user_id),
        )
