-- Migration 005: PK renames + naming consistency + schema-quality improvements
-- Run as a single transaction. Safe to re-run only if rolled back; column renames are not idempotent.
--
-- Summary:
--   1) Rename PKs from `id` to `<table_singular>_id`
--   2) user_dictionary column renames (consistency with `texts` table)
--   3) vocab_cards FK rename (FK convention)
--   4) TIMESTAMP -> TIMESTAMPTZ on all timestamp columns (assumes existing values are UTC)
--   5) Add updated_at + BEFORE UPDATE trigger on mutable tables
--   6) CHECK constraint on audio_files.tts_service
--   7) Missing indexes on folders(user_id) and playlists(user_id)

BEGIN;

-- 1) PK renames -------------------------------------------------------
ALTER TABLE users           RENAME COLUMN id TO user_id;
ALTER TABLE user_api_keys   RENAME COLUMN id TO api_key_id;
ALTER TABLE folders         RENAME COLUMN id TO folder_id;
ALTER TABLE texts           RENAME COLUMN id TO text_id;
ALTER TABLE user_dictionary RENAME COLUMN id TO user_dictionary_id;
ALTER TABLE vocab_cards     RENAME COLUMN id TO vocab_card_id;
ALTER TABLE playlists       RENAME COLUMN id TO playlist_id;
ALTER TABLE audio_files     RENAME COLUMN id TO audio_file_id;

-- 2) user_dictionary column renames -----------------------------------
ALTER TABLE user_dictionary RENAME COLUMN word_source TO source_word;
ALTER TABLE user_dictionary RENAME COLUMN word_target TO target_word;
ALTER TABLE user_dictionary RENAME COLUMN lang_source TO source_language;
ALTER TABLE user_dictionary RENAME COLUMN lang_target TO target_language;
ALTER TABLE user_dictionary RENAME COLUMN first_seen  TO created_at;

-- 3) vocab_cards FK rename --------------------------------------------
ALTER TABLE vocab_cards RENAME COLUMN dictionary_entry_id TO user_dictionary_id;

-- 4) TIMESTAMP -> TIMESTAMPTZ -----------------------------------------
ALTER TABLE users           ALTER COLUMN created_at    TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC';
ALTER TABLE user_api_keys   ALTER COLUMN created_at    TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC';
ALTER TABLE folders         ALTER COLUMN created_at    TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC';
ALTER TABLE texts           ALTER COLUMN created_at    TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC';
ALTER TABLE user_dictionary ALTER COLUMN created_at    TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC';
ALTER TABLE vocab_cards     ALTER COLUMN last_reviewed TYPE TIMESTAMPTZ USING last_reviewed AT TIME ZONE 'UTC';
ALTER TABLE vocab_cards     ALTER COLUMN next_review   TYPE TIMESTAMPTZ USING next_review AT TIME ZONE 'UTC';
ALTER TABLE vocab_cards     ALTER COLUMN created_at    TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC';
ALTER TABLE playlists       ALTER COLUMN created_at    TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC';
ALTER TABLE audio_files     ALTER COLUMN created_at    TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC';

-- 5) updated_at + trigger ---------------------------------------------
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

ALTER TABLE texts           ADD COLUMN updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE user_dictionary ADD COLUMN updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE vocab_cards     ADD COLUMN updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE playlists       ADD COLUMN updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

CREATE TRIGGER trg_texts_updated_at
    BEFORE UPDATE ON texts
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_user_dictionary_updated_at
    BEFORE UPDATE ON user_dictionary
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_vocab_cards_updated_at
    BEFORE UPDATE ON vocab_cards
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_playlists_updated_at
    BEFORE UPDATE ON playlists
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- 6) CHECK constraint on audio_files.tts_service ----------------------
ALTER TABLE audio_files
    ADD CONSTRAINT chk_audio_tts_service
    CHECK (tts_service IN ('gtts', 'openai_tts'));

-- 7) Missing indexes --------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_folders_user_id   ON folders(user_id);
CREATE INDEX IF NOT EXISTS idx_playlists_user_id ON playlists(user_id);

COMMIT;
