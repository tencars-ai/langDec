"""
VocabularyManager – CRUD for user_dictionary with deduplication and frequency tracking.

Card fields (6):
  word_source          – foreign language word/phrase
  word_target          – mother tongue: natural translation
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
        word_source: str,
        word_target: str,
        lang_source: str,
        lang_target: str,
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
                (user_id, word_source, word_target, lang_source, lang_target,
                 word_class, word_target_decoded, example_sentence, explanation, source_text_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id, word_source, lang_source, lang_target) DO UPDATE
                SET frequency = user_dictionary.frequency + 1,
                    word_target = EXCLUDED.word_target,
                    word_class = COALESCE(EXCLUDED.word_class, user_dictionary.word_class),
                    word_target_decoded = COALESCE(EXCLUDED.word_target_decoded, user_dictionary.word_target_decoded),
                    example_sentence = COALESCE(EXCLUDED.example_sentence, user_dictionary.example_sentence),
                    explanation = COALESCE(EXCLUDED.explanation, user_dictionary.explanation)
            """,
            (
                user_id, word_source, word_target, lang_source, lang_target,
                word_class, word_target_decoded, example_sentence, explanation, source_text_id,
            ),
        )
        entry = self._db.execute_one(
            """
            SELECT id FROM user_dictionary
            WHERE user_id = %s AND word_source = %s
              AND lang_source = %s AND lang_target = %s
            """,
            (user_id, word_source, lang_source, lang_target),
        )
        if entry:
            self._db.execute_write(
                """
                INSERT INTO vocab_cards (user_id, dictionary_entry_id)
                VALUES (%s, %s)
                ON CONFLICT (user_id, dictionary_entry_id) DO NOTHING
                """,
                (user_id, str(entry["id"])),
            )

    def get_words(
        self,
        user_id: str,
        lang_source: Optional[str] = None,
        lang_target: Optional[str] = None,
        search: Optional[str] = None,
    ) -> list[dict]:
        """Return dictionary entries for a user, with optional filters."""
        conditions = ["user_id = %s"]
        params: list = [user_id]

        if lang_source:
            conditions.append("lang_source = %s")
            params.append(lang_source)
        if lang_target:
            conditions.append("lang_target = %s")
            params.append(lang_target)
        if search:
            conditions.append("(word_source ILIKE %s OR word_target ILIKE %s OR word_target_decoded ILIKE %s)")
            params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])

        where = " AND ".join(conditions)
        return self._db.execute(
            f"""
            SELECT id, word_source, word_target, word_target_decoded, lang_source, lang_target,
                   word_class, example_sentence, explanation, frequency, first_seen
            FROM user_dictionary
            WHERE {where}
            ORDER BY frequency DESC, word_source
            """,
            tuple(params),
        )

    def get_word(self, user_id: str, word_id: str) -> Optional[dict]:
        return self._db.execute_one(
            "SELECT * FROM user_dictionary WHERE id = %s AND user_id = %s",
            (word_id, user_id),
        )

    def update_word(
        self,
        user_id: str,
        word_id: str,
        word_target: Optional[str] = None,
        word_target_decoded: Optional[str] = None,
        word_class: Optional[str] = None,
        example_sentence: Optional[str] = None,
        explanation: Optional[str] = None,
    ) -> None:
        """Update editable fields of a dictionary entry."""
        self._db.execute_write(
            """
            UPDATE user_dictionary
            SET word_target         = COALESCE(%s, word_target),
                word_target_decoded = COALESCE(%s, word_target_decoded),
                word_class          = COALESCE(%s, word_class),
                example_sentence    = COALESCE(%s, example_sentence),
                explanation         = COALESCE(%s, explanation)
            WHERE id = %s AND user_id = %s
            """,
            (word_target, word_target_decoded, word_class, example_sentence, explanation, word_id, user_id),
        )

    def delete_word(self, user_id: str, word_id: str) -> None:
        self._db.execute_write(
            "DELETE FROM user_dictionary WHERE id = %s AND user_id = %s",
            (word_id, user_id),
        )
