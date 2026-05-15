"""
Audio Storage Service – store and retrieve MP3 BYTEA from PostgreSQL.
"""
from __future__ import annotations

from typing import Optional
from services.db_service import DBService


class AudioStorageService:
    """Persist and retrieve TTS audio files (MP3) in PostgreSQL BYTEA."""

    def __init__(self, db: DBService):
        self._db = db

    def save(
        self,
        user_id: str,
        data: bytes,
        language: str,
        tts_service: str,
        text_id: Optional[str] = None,
    ) -> str:
        """
        Insert audio bytes into audio_files table.
        Returns the new audio file's UUID.
        """
        row = self._db.execute_returning(
            """
            INSERT INTO audio_files
                (user_id, text_id, language, tts_service, data, file_size_bytes)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING audio_file_id
            """,
            (user_id, text_id, language, tts_service, data, len(data)),
        )
        return str(row["audio_file_id"])

    def get(self, audio_id: str, user_id: str) -> Optional[bytes]:
        """
        Retrieve MP3 bytes for a given audio file, scoped to user_id.
        Returns None if not found.
        """
        row = self._db.execute_one(
            "SELECT data FROM audio_files WHERE audio_file_id = %s AND user_id = %s",
            (audio_id, user_id),
        )
        return bytes(row["data"]) if row else None

    def get_by_text_id(self, text_id: str, user_id: str) -> Optional[bytes]:
        """Retrieve the latest MP3 bytes for a given text, scoped to user_id."""
        row = self._db.execute_one(
            "SELECT data FROM audio_files WHERE text_id = %s AND user_id = %s "
            "ORDER BY created_at DESC LIMIT 1",
            (text_id, user_id),
        )
        return bytes(row["data"]) if row else None

    def list_for_user(self, user_id: str) -> list[dict]:
        """
        List all audio file metadata for a user (no binary data).
        """
        return self._db.execute(
            """
            SELECT audio_file_id, text_id, language, tts_service, file_size_bytes, created_at
            FROM audio_files
            WHERE user_id = %s
            ORDER BY created_at DESC
            """,
            (user_id,),
        )

    def delete(self, audio_id: str, user_id: str) -> None:
        """Delete an audio file (scoped to user_id)."""
        self._db.execute_write(
            "DELETE FROM audio_files WHERE audio_file_id = %s AND user_id = %s",
            (audio_id, user_id),
        )
