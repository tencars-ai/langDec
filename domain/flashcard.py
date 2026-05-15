"""
FlashcardBox – spaced repetition logic for the vocabulary trainer.

Box system:
  1 = new       → review after 1 day
  2 = practiced → review after 3 days
  3 = learned   → review after 7 days
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional
from services.db_service import DBService


_REVIEW_INTERVALS = {1: 1, 2: 3, 3: 7}
_MAX_BOX = 3


def _next_review(box_number: int) -> datetime:
    days = _REVIEW_INTERVALS.get(box_number, 1)
    return datetime.now(tz=timezone.utc) + timedelta(days=days)


class FlashcardBox:
    """Manages spaced-repetition review state for vocab cards."""

    def __init__(self, db: DBService):
        self._db = db

    def get_due_cards(self, user_id: str, limit: int = 20) -> list[dict]:
        """Return cards due for review (next_review <= NOW()), with word data."""
        return self._db.execute(
            """
            SELECT vc.vocab_card_id, vc.box_number, vc.last_reviewed, vc.next_review,
                   ud.source_word, ud.target_word, ud.source_language, ud.target_language,
                   ud.word_class, ud.word_target_decoded, ud.example_sentence, ud.explanation
            FROM vocab_cards vc
            JOIN user_dictionary ud
                 ON ud.user_dictionary_id = vc.user_dictionary_id
            WHERE vc.user_id = %s
              AND vc.next_review <= NOW()
            ORDER BY vc.next_review ASC
            LIMIT %s
            """,
            (user_id, limit),
        )

    def get_progress(self, user_id: str) -> dict:
        """Return count of cards in each box."""
        rows = self._db.execute(
            """
            SELECT box_number, COUNT(*) AS count
            FROM vocab_cards
            WHERE user_id = %s
            GROUP BY box_number
            ORDER BY box_number
            """,
            (user_id,),
        )
        progress = {1: 0, 2: 0, 3: 0}
        for row in rows:
            progress[row["box_number"]] = row["count"]
        return progress

    def mark_correct(self, user_id: str, card_id: str) -> None:
        """
        Advance card to the next box and set next_review.
        Cards already in box 3 stay in box 3.
        """
        card = self._db.execute_one(
            "SELECT box_number FROM vocab_cards WHERE vocab_card_id = %s AND user_id = %s",
            (card_id, user_id),
        )
        if not card:
            return
        new_box = min(card["box_number"] + 1, _MAX_BOX)
        self._db.execute_write(
            """
            UPDATE vocab_cards
            SET box_number = %s,
                last_reviewed = NOW(),
                next_review = %s
            WHERE vocab_card_id = %s AND user_id = %s
            """,
            (new_box, _next_review(new_box), card_id, user_id),
        )

    def mark_incorrect(self, user_id: str, card_id: str) -> None:
        """Reset card to box 1 and set next_review to tomorrow."""
        self._db.execute_write(
            """
            UPDATE vocab_cards
            SET box_number = 1,
                last_reviewed = NOW(),
                next_review = %s
            WHERE vocab_card_id = %s AND user_id = %s
            """,
            (_next_review(1), card_id, user_id),
        )
