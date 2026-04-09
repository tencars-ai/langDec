-- Migration: add decoded_text, translated_text, target_language to texts table
ALTER TABLE texts ADD COLUMN IF NOT EXISTS target_language VARCHAR(10);
ALTER TABLE texts ADD COLUMN IF NOT EXISTS decoded_text TEXT;
ALTER TABLE texts ADD COLUMN IF NOT EXISTS translated_text TEXT;
