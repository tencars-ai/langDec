"""
PreferencesService – load/save per-user UI and service preferences.

Backed by the `user_preferences` table (migration 006). One row per user;
defaults are filled in by the table when no row exists yet.
"""
from __future__ import annotations

from typing import Any, Optional

from services.db_service import DBService


DEFAULTS: dict[str, Any] = {
    "decode_service_name": None,
    "translate_service_name": "Google Translate",
    "max_line_length": 65,
    "ocr_line_height_threshold": 30,
    "debug_mode": False,
}


class PreferencesService:
    def __init__(self, db: Optional[DBService] = None) -> None:
        self.db = db or DBService()

    def load(self, user_id: str) -> dict[str, Any]:
        """Return persisted preferences for a user, or {} if none saved yet."""
        row = self.db.execute_one(
            """
            SELECT decode_service_name, translate_service_name,
                   max_line_length, ocr_line_height_threshold, debug_mode
            FROM user_preferences
            WHERE user_id = %s
            """,
            (user_id,),
        )
        return dict(row) if row else {}

    def save(
        self,
        user_id: str,
        *,
        decode_service_name: Optional[str],
        translate_service_name: Optional[str],
        max_line_length: int,
        ocr_line_height_threshold: int,
        debug_mode: bool,
    ) -> None:
        self.db.execute_write(
            """
            INSERT INTO user_preferences (
                user_id, decode_service_name, translate_service_name,
                max_line_length, ocr_line_height_threshold, debug_mode
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
                decode_service_name        = EXCLUDED.decode_service_name,
                translate_service_name     = EXCLUDED.translate_service_name,
                max_line_length            = EXCLUDED.max_line_length,
                ocr_line_height_threshold  = EXCLUDED.ocr_line_height_threshold,
                debug_mode                 = EXCLUDED.debug_mode
            """,
            (
                user_id,
                decode_service_name,
                translate_service_name,
                int(max_line_length),
                int(ocr_line_height_threshold),
                bool(debug_mode),
            ),
        )
