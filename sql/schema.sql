-- langDec Database Schema
-- PostgreSQL (psycopg v3)
-- Run this once against your Supabase / PostgreSQL instance.

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- -------------------------------------------------------
-- Users
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- -------------------------------------------------------
-- LLM API Keys (encrypted per user)
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL,        -- 'openai' | 'anthropic'
    api_key_encrypted BYTEA NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, provider)
);

-- -------------------------------------------------------
-- Text library: folders
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS folders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    parent_folder_id UUID REFERENCES folders(id) ON DELETE SET NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- -------------------------------------------------------
-- Text library: texts
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS texts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    folder_id UUID REFERENCES folders(id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    source_language VARCHAR(10) NOT NULL,   -- 'pt', 'en', 'de'
    target_language VARCHAR(10),            -- 'pt', 'en', 'de'
    decoded_text TEXT,
    translated_text TEXT,
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_texts_user_id ON texts(user_id);
CREATE INDEX IF NOT EXISTS idx_texts_folder_id ON texts(folder_id);

-- -------------------------------------------------------
-- Personal dictionary
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_dictionary (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    word_source VARCHAR(255) NOT NULL,
    word_target VARCHAR(255) NOT NULL,
    lang_source VARCHAR(10) NOT NULL,
    lang_target VARCHAR(10) NOT NULL,
    word_class VARCHAR(50),                 -- noun, verb, adj, adv, ...
    word_target_decoded VARCHAR(255),       -- literal/decoded translation (Birkenbihl)
    explanation TEXT,                       -- notes, grammar hints, context
    example_sentence TEXT,
    source_text_id UUID REFERENCES texts(id) ON DELETE SET NULL,
    first_seen TIMESTAMP NOT NULL DEFAULT NOW(),
    frequency INTEGER NOT NULL DEFAULT 1,
    UNIQUE (user_id, word_source, lang_source, lang_target)
);

CREATE INDEX IF NOT EXISTS idx_dict_user_id ON user_dictionary(user_id);
CREATE INDEX IF NOT EXISTS idx_dict_lang ON user_dictionary(user_id, lang_source, lang_target);

-- -------------------------------------------------------
-- Vocabulary trainer (spaced repetition box system)
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS vocab_cards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    dictionary_entry_id UUID NOT NULL REFERENCES user_dictionary(id) ON DELETE CASCADE,
    box_number INTEGER NOT NULL DEFAULT 1,   -- 1=new, 2=practiced, 3=learned
    last_reviewed TIMESTAMP,
    next_review TIMESTAMP NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, dictionary_entry_id)
);

CREATE INDEX IF NOT EXISTS idx_vocab_cards_due ON vocab_cards(user_id, next_review);

-- -------------------------------------------------------
-- Playlists
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS playlists (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS playlist_texts (
    playlist_id UUID NOT NULL REFERENCES playlists(id) ON DELETE CASCADE,
    text_id UUID NOT NULL REFERENCES texts(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    PRIMARY KEY (playlist_id, text_id)
);

-- -------------------------------------------------------
-- Audio files (MP3 as BYTEA)
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS audio_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    text_id UUID REFERENCES texts(id) ON DELETE SET NULL,
    language VARCHAR(10) NOT NULL,
    tts_service VARCHAR(50) NOT NULL,       -- 'gtts', 'openai_tts', ...
    data BYTEA NOT NULL,
    file_size_bytes INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audio_user_id ON audio_files(user_id);
