-- Migration 002: Add word_target_decoded and explanation to user_dictionary
-- Run against all environments (dev + prod) after 001_init / schema.sql

ALTER TABLE user_dictionary
    ADD COLUMN IF NOT EXISTS word_target_decoded VARCHAR(255),
    ADD COLUMN IF NOT EXISTS explanation TEXT;
