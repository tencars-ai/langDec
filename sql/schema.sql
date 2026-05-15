-- langDec Database Schema
-- PostgreSQL (psycopg v3)
-- Run this once against your Neon (neon.tech) / PostgreSQL instance.

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- -------------------------------------------------------
-- updated_at trigger function (shared)
-- -------------------------------------------------------
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- -------------------------------------------------------
-- Users
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- -------------------------------------------------------
-- LLM API Keys (encrypted per user)
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_api_keys (
    api_key_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL,        -- 'openai' | 'anthropic'
    api_key_encrypted BYTEA NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, provider)
);

-- -------------------------------------------------------
-- Text library: folders
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS folders (
    folder_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    parent_folder_id UUID REFERENCES folders(folder_id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_folders_user_id ON folders(user_id);

-- -------------------------------------------------------
-- Text library: texts
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS texts (
    text_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    folder_id UUID REFERENCES folders(folder_id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    source_language VARCHAR(10) NOT NULL,   -- 'pt', 'en', 'de', 'sv'
    target_language VARCHAR(10),            -- 'pt', 'en', 'de', 'sv'
    decoded_text TEXT,
    translated_text TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_texts_user_id ON texts(user_id);
CREATE INDEX IF NOT EXISTS idx_texts_folder_id ON texts(folder_id);

CREATE TRIGGER trg_texts_updated_at
    BEFORE UPDATE ON texts
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- -------------------------------------------------------
-- Personal dictionary
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_dictionary (
    user_dictionary_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    source_word VARCHAR(255) NOT NULL,
    target_word VARCHAR(255) NOT NULL,
    source_language VARCHAR(10) NOT NULL,
    target_language VARCHAR(10) NOT NULL,
    word_class VARCHAR(50),                 -- noun, verb, adj, adv, ...
    word_target_decoded VARCHAR(255),       -- literal/decoded translation (Birkenbihl)
    explanation TEXT,                       -- notes, grammar hints, context
    example_sentence TEXT,
    source_text_id UUID REFERENCES texts(text_id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    frequency INTEGER NOT NULL DEFAULT 1,
    UNIQUE (user_id, source_word, source_language, target_language)
);

CREATE INDEX IF NOT EXISTS idx_dict_user_id ON user_dictionary(user_id);
CREATE INDEX IF NOT EXISTS idx_dict_lang ON user_dictionary(user_id, source_language, target_language);

CREATE TRIGGER trg_user_dictionary_updated_at
    BEFORE UPDATE ON user_dictionary
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- -------------------------------------------------------
-- Vocabulary trainer (spaced repetition box system)
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS vocab_cards (
    vocab_card_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    user_dictionary_id UUID NOT NULL REFERENCES user_dictionary(user_dictionary_id) ON DELETE CASCADE,
    box_number INTEGER NOT NULL DEFAULT 1,   -- 1=new, 2=practiced, 3=learned
    last_reviewed TIMESTAMPTZ,
    next_review TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, user_dictionary_id)
);

CREATE INDEX IF NOT EXISTS idx_vocab_cards_due ON vocab_cards(user_id, next_review);

CREATE TRIGGER trg_vocab_cards_updated_at
    BEFORE UPDATE ON vocab_cards
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- -------------------------------------------------------
-- Playlists
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS playlists (
    playlist_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_playlists_user_id ON playlists(user_id);

CREATE TRIGGER trg_playlists_updated_at
    BEFORE UPDATE ON playlists
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE IF NOT EXISTS playlist_texts (
    playlist_id UUID NOT NULL REFERENCES playlists(playlist_id) ON DELETE CASCADE,
    text_id UUID NOT NULL REFERENCES texts(text_id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    PRIMARY KEY (playlist_id, text_id)
);

-- -------------------------------------------------------
-- Audio files (MP3 as BYTEA)
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS audio_files (
    audio_file_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    text_id UUID REFERENCES texts(text_id) ON DELETE SET NULL,
    language VARCHAR(10) NOT NULL,
    tts_service VARCHAR(50) NOT NULL CHECK (tts_service IN ('gtts', 'openai_tts')),
    data BYTEA NOT NULL,
    file_size_bytes INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audio_user_id ON audio_files(user_id);

-- -------------------------------------------------------
-- User preferences (UI/service settings persisted across sessions)
-- -------------------------------------------------------
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
