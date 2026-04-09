# Technical Implementation Plan – langDec Prototype

**Date:** 2026-03-07
**Branch:** dev2
**Status:** Planning complete — implementation in progress

---

## 1. Overview

langDec is a language learning prototype based on the Birkenbihl decoding method. This document describes the full technical plan for evolving the existing single-page Streamlit prototype into a multi-page app with user management, LLM-based translation, personal dictionary, vocabulary trainer, TTS/audio, and text generation.

---

## 2. Confirmed Stack

| Layer | Technology |
|---|---|
| UI | Streamlit (multi-page) |
| Auth | streamlit-authenticator |
| Backend logic | Python services + domain modules |
| Database | PostgreSQL via psycopg v3 |
| LLM | OpenAI SDK + Anthropic SDK |
| TTS | gTTS (extensible abstract service) |
| OCR | EasyOCR (existing) |
| Audio storage | PostgreSQL BYTEA |

---

## 3. Database Schema

```sql
-- Users
users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  username VARCHAR UNIQUE NOT NULL,
  email VARCHAR UNIQUE,
  password_hash VARCHAR NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
)

-- LLM API Keys (encrypted per user)
user_api_keys (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  provider VARCHAR NOT NULL,        -- 'openai' | 'anthropic'
  api_key_encrypted BYTEA NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE (user_id, provider)
)

-- Text library: folders
folders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name VARCHAR NOT NULL,
  parent_folder_id UUID REFERENCES folders(id) ON DELETE SET NULL,
  created_at TIMESTAMP DEFAULT NOW()
)

-- Text library: texts
texts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  folder_id UUID REFERENCES folders(id) ON DELETE SET NULL,
  title VARCHAR NOT NULL,
  content TEXT NOT NULL,
  source_language VARCHAR NOT NULL,   -- 'pt', 'en', 'de'
  notes TEXT,
  created_at TIMESTAMP DEFAULT NOW()
)

-- Personal dictionary
user_dictionary (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  word_source VARCHAR NOT NULL,
  word_target VARCHAR NOT NULL,
  lang_source VARCHAR NOT NULL,
  lang_target VARCHAR NOT NULL,
  word_class VARCHAR,                 -- noun, verb, adj, ...
  example_sentence TEXT,
  source_text_id UUID REFERENCES texts(id) ON DELETE SET NULL,
  first_seen TIMESTAMP DEFAULT NOW(),
  frequency INTEGER NOT NULL DEFAULT 1,
  UNIQUE (user_id, word_source, lang_source, lang_target)
)

-- Vocabulary trainer (spaced repetition box system)
vocab_cards (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  dictionary_entry_id UUID NOT NULL REFERENCES user_dictionary(id) ON DELETE CASCADE,
  box_number INTEGER NOT NULL DEFAULT 1,   -- 1=new, 2=practiced, 3=learned
  last_reviewed TIMESTAMP,
  next_review TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW()
)

-- Playlists
playlists (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name VARCHAR NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
)

playlist_texts (
  playlist_id UUID NOT NULL REFERENCES playlists(id) ON DELETE CASCADE,
  text_id UUID NOT NULL REFERENCES texts(id) ON DELETE CASCADE,
  position INTEGER NOT NULL,
  PRIMARY KEY (playlist_id, text_id)
)

-- Audio files (MP3 as BYTEA)
audio_files (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  text_id UUID REFERENCES texts(id) ON DELETE SET NULL,
  language VARCHAR NOT NULL,
  tts_service VARCHAR NOT NULL,       -- 'gtts', 'openai_tts', ...
  data BYTEA NOT NULL,
  file_size_bytes INTEGER,
  created_at TIMESTAMP DEFAULT NOW()
)
```

---

## 4. Service Layer

### 4.1 New Services

| File | Class | Purpose |
|---|---|---|
| `services/llm_service.py` | `LLMService` (ABC), `OpenAIService`, `ClaudeService` | LLM translation + text generation |
| `services/tts_service.py` | `TTSService` (ABC), `GTTSService` | Text-to-Speech |
| `services/auth_service.py` | `AuthService` | Password hashing, API key encryption/decryption |
| `services/db_service.py` | `DBService` | PostgreSQL connection pool, query helpers |
| `services/audio_storage_service.py` | `AudioStorageService` | Store/retrieve MP3 BYTEA from DB |

### 4.2 LLM Service Design

Abstract base class `LLMService` with methods:
- `translate_word(word, source_lang, target_lang, context=None) -> str`
- `translate_text(text, source_lang, target_lang) -> str`
- `generate_text(prompt, language, difficulty) -> str`
- `word_lookup(word, source_lang, target_lang) -> dict` → translation, word_class, example

Implementations: `OpenAIService`, `ClaudeService`

Each user's LLM is resolved from their stored API keys at session start. `LLMService` implements `TranslationService` interface — decoder and translator work without changes.

### 4.3 TTS Service Design

Abstract base class `TTSService`:
- `synthesize(text, language) -> bytes` → MP3 bytes
- `name -> str`

Implementation: `GTTSService`

Returned bytes are played in-browser (`st.audio`) or saved to PostgreSQL via `AudioStorageService`.

### 4.4 Auth Service Design

`AuthService` responsibilities:
- `hash_password(password) -> str` — bcrypt
- `verify_password(password, hash) -> bool`
- `encrypt_api_key(api_key, secret) -> bytes` — Fernet symmetric encryption
- `decrypt_api_key(encrypted, secret) -> str`

Encryption secret derived from app-level `SECRET_KEY` environment variable.

### 4.5 DB Service Design

`DBService` wraps psycopg v3:
- Connection pool (min/max configurable via env)
- `execute(sql, params) -> list[dict]` helper
- `execute_one(sql, params) -> dict | None`
- `execute_write(sql, params) -> None`
- Context-manager support

### 4.6 Existing Services (Changes)

| Service | Change |
|---|---|
| `dictcc_translation_service.py` | `psycopg2` → `psycopg` v3; DB connection moved to lazy init in `translate_word()` |
| `translation_service.py` | No changes |
| `ocr_service.py` | No changes |

---

## 5. Domain Layer

### 5.1 New Domain Modules

| File | Class | Purpose |
|---|---|---|
| `domain/vocabulary.py` | `VocabularyManager` | Dictionary CRUD, deduplication, frequency tracking |
| `domain/flashcard.py` | `FlashcardBox` | Spaced repetition logic (box system) |

### 5.2 VocabularyManager

Methods:
- `add_word(user_id, word_source, word_target, lang_source, lang_target, word_class=None, example=None, source_text_id=None)` — upserts, increments frequency
- `get_words(user_id, lang_source=None, lang_target=None) -> list[dict]`
- `delete_word(user_id, word_id)`
- `get_word(user_id, word_id) -> dict`

### 5.3 FlashcardBox

Box system (1=new, 2=practiced, 3=learned):
- `get_due_cards(user_id, limit=20) -> list[dict]`
- `mark_correct(user_id, card_id)` — advance box, set next_review
- `mark_incorrect(user_id, card_id)` — reset to box 1
- Review intervals: box 1 = 1 day, box 2 = 3 days, box 3 = 7 days

---

## 6. App Structure (Multi-Page Streamlit)

```
app.py                      ← Entry point: auth gate, session init
pages/
  1_Decoder.py              ← Decoder (refactored from app.py, user-aware)
  2_Texts.py                ← Text library: folders, save/load texts
  3_Dictionary.py           ← Personal dictionary: browse, edit entries
  4_Vocab_Trainer.py        ← Flashcard trainer
  5_Audio.py                ← TTS playback, MP3 save, playlists
  6_Generate.py             ← LLM text/dialogue generation
  7_Settings.py             ← API key management, user preferences
```

### 6.1 Auth Flow

1. `app.py` loads user credentials from PostgreSQL on startup
2. Login/register form shown to unauthenticated users via `streamlit-authenticator`
3. On successful login: `st.session_state.user_id` set, all DB queries scoped to this user
4. API keys loaded (decrypted) into session at login
5. All pages check `st.session_state.get("user_id")` and redirect to login if not set

---

## 7. Page Specifications

### 7.1 `pages/1_Decoder.py`
- Refactored from current `app.py` decoder logic
- Adds: "Save text to library" button → writes to `texts` table
- Adds: Auto-save decoded word pairs to `user_dictionary` after decode
- LLM service selected from session (user's configured API key)

### 7.2 `pages/2_Texts.py`
- List all texts (grouped by folder)
- Create/rename/delete folders
- Open text → loads into decoder or shows read view
- Save new text manually with title + folder assignment

### 7.3 `pages/3_Dictionary.py`
- Table view of `user_dictionary` for current user
- Filter by source/target language
- Search by word
- Edit translation, word_class, example
- Delete entry

### 7.4 `pages/4_Vocab_Trainer.py`
- Flashcard UI: show source word, user guesses/reveals target
- Mark correct/incorrect → updates box and next_review
- Progress display: cards per box
- Only shows cards due today (`next_review <= NOW()`)

### 7.5 `pages/5_Audio.py`
- Select text from library or paste text directly
- Choose language + TTS service
- Generate audio → `st.audio` playback
- Save MP3 to DB per user
- List saved audio files, play or download

### 7.6 `pages/6_Generate.py`
- LLM prompt builder: topic, language, difficulty, format (dialogue/text/story)
- Generate → display result
- Save generated text to text library with one click

### 7.7 `pages/7_Settings.py`
- Enter/update OpenAI API key → encrypted, stored in `user_api_keys`
- Enter/update Anthropic API key → same
- Test API key connection
- Change password
- Delete account (with confirmation)

---

## 8. Dependencies (requirements.txt)

### Additions
```
streamlit-authenticator
openai
anthropic
gtts
bcrypt
cryptography
```

### Removals
- `psycopg2` / `psycopg2-binary` (not currently in requirements.txt but in dictcc service — fixed in code)

`psycopg[binary]` is already in requirements.txt and covers all DB access.

---

## 9. Implementation Phases

### Phase 1 – Foundation
1. `sql/schema.sql` — full DB schema
2. `services/db_service.py` — connection pool, base queries
3. `services/auth_service.py` — password hash, API key encryption
4. Auth gate in `app.py` via streamlit-authenticator
5. Refactoring: psycopg fix in dictcc service, lazy init, remove dict.cc from AVAILABLE_SERVICES default

### Phase 2 – LLM Integration
6. `services/llm_service.py` — OpenAI + Claude implementations
7. `pages/7_Settings.py` — API key management UI
8. Wire LLM service into decoder/translator (drop-in via TranslationService interface)

### Phase 3 – Persistence
9. `pages/2_Texts.py` — text library with folders
10. Auto-save decoded words to `user_dictionary`
11. `domain/vocabulary.py` — deduplication + frequency

### Phase 4 – Dictionary & Vocab Trainer
12. `pages/3_Dictionary.py` — browse/search personal dictionary
13. `domain/flashcard.py` — flashcard box logic
14. `pages/4_Vocab_Trainer.py` — trainer UI

### Phase 5 – Audio
15. `services/tts_service.py` — gTTS implementation
16. `services/audio_storage_service.py` — BYTEA store/retrieve
17. `pages/5_Audio.py` — playback + MP3 save per user

### Phase 6 – LLM Generation
18. `pages/6_Generate.py` — dialogue/text generation UI
19. Save generated texts to text library

---

## 10. Verification Checklist

- [ ] `streamlit run app.py` → login screen appears
- [ ] Register new user → stored in DB with hashed password
- [ ] Enter LLM API key in Settings → encrypted, retrievable
- [ ] Paste text in Decoder, click Decode → LLM called, result shown
- [ ] Words auto-saved to personal dictionary after decode
- [ ] Dictionary page → saved words visible
- [ ] Vocab Trainer → flashcards from personal dictionary
- [ ] Mark card correct/incorrect → box updated, next_review set
- [ ] TTS → audio plays in browser, MP3 saveable to DB
- [ ] Generate → LLM creates text, saved to text library
- [ ] Logout → session cleared, login required again

---

## 11. Environment Variables Required

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `SECRET_KEY` | App-level secret for API key encryption |

Both set in `.streamlit/secrets.toml` for local dev and in Streamlit Cloud secrets for deployment.
