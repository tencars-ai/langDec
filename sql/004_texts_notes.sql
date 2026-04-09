-- Migration: ensure notes column exists on texts (no-op if already present)
ALTER TABLE texts ADD COLUMN IF NOT EXISTS notes TEXT;
