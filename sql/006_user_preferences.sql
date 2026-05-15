-- Migration 006: user_preferences table
-- Persists per-user UI/service preferences that were previously only kept in
-- st.session_state (and therefore lost on logout).

BEGIN;

CREATE TABLE IF NOT EXISTS user_preferences (
    user_id UUID PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    decode_service_name VARCHAR(100),
    translate_service_name VARCHAR(100),
    max_line_length INTEGER NOT NULL DEFAULT 65,
    ocr_line_height_threshold INTEGER NOT NULL DEFAULT 30,
    debug_mode BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trg_user_preferences_updated_at
    BEFORE UPDATE ON user_preferences
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

COMMIT;
