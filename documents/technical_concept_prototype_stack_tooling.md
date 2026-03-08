# Technical Concept – Prototype Stack & Tooling

## 1. Goal
Define a pragmatic technology stack for the **first prototype** of the language learning software (mobile-capable web app), focusing on rapid implementation, open-source components, and future extensibility.

---

## 2. Guiding Principles
- **Quickly runnable prototype** (feature flow demonstrable)
- **Open Source** (frameworks/components, self-hosting possible in principle)
- **Clean data foundation** (Postgres as long-term persistence)
- **Architecture chosen** so that a later switch to a more "app-native" stack is possible (Variant 2)

---

## 3. Decision: Variant 1 (Initial)
### 3.1 Frontend / UI
- **Streamlit** as UI framework for the prototype
- Rationale:
  - Very fast construction of clickable interfaces in Python
  - Ideal for early validation of core features (OCR → text management → translation/decoder → audio/playlist → vocabulary)

### 3.2 Database
- **PostgreSQL** as primary database
- Rationale:
  - Stable, open source, well-suited for relational data (texts, folders, vocabulary cards, playlists, metadata)

### 3.3 Hosting (Prototype)
- **Streamlit Community Cloud** for rapid deployment of the app
- **Neon (neon.tech)** as hosted serverless Postgres instance (eu-central-1 / AWS Frankfurt)

> Note: A later switch to a self-hosted Postgres (e.g. on a VPS/managed DB) is possible.

---

## 4. AI-Assisted Development (Tooling Decision)
### 4.1 Directly in Code / IDE
- **GitHub Copilot + Copilot Chat** for:
  - Implementation of individual modules
  - Boilerplate, CRUD, tests, refactoring within project context

### 4.2 Cross-Cutting (Planning / Architecture)
- **ChatGPT** for:
  - System/module architecture and interfaces
  - Data modelling (tables/entities)
  - Specification of decoder logic (Birkenbihl)
  - Review, debugging strategies, technical decisions

---

## 5. Option for Later Expansion: Variant 2
Variant 1 is deliberately prototypical. For a "real app" with better mobile UX and long-term structure, the following is planned for later:

### 5.1 Possible Target Stack (Variant 2)
- Backend: **FastAPI (Python)**
- Database: **PostgreSQL** (unchanged)
- UI:
  - either Python-first: **Reflex**
  - or a separate web frontend (e.g. React/Next.js) and later mobile (React Native/Expo)

### 5.2 Migration Concept
- Database (Postgres) stays the same
- Business logic (decoder/translation/vocabulary trainer) encapsulated as Python modules
- Streamlit serves as the early UI layer; later the UI is swapped out, core logic reused

---

## 6. Next Steps (Concrete)
1. Define minimal data model (tables/relationships)
2. Define module interfaces:
   - Text management + folders
   - OCR import
   - Contextual translation + decoder
   - TTS + playlists/export
   - Vocabulary trainer + CSV import/export
3. Create Streamlit app skeleton (navigation + base pages)

---

## 7. Updated Decisions (Post-Original Document)

The following decisions were made after the original document was written and supersede or extend the above where applicable.

### 7.1 LLM as Primary Translation Engine
- **OpenAI (ChatGPT)** and **Anthropic (Claude)** APIs are now the **primary** translation and text-generation backend.
- Google Translate (deep-translator) and Argos Translate remain available as fallbacks.
- dict.cc is retained in code but removed from the default UI service list.
- Each user stores their own API keys (OpenAI / Anthropic), encrypted in the database.
- The `TranslationService` abstract interface is preserved — `LLMService` implements it, so the decoder and translator work without changes.

### 7.2 Rudimentary User Management (Required from Start)
- Auth via **streamlit-authenticator** (cookie-based session).
- User credentials (hashed passwords) stored in PostgreSQL.
- All data (texts, vocabulary, audio, API keys) is scoped per user.
- No OAuth or social login in prototype scope.

### 7.3 Per-User Personal Dictionary
- Every decode operation auto-saves translated word pairs to `user_dictionary`.
- Deduplication by `(user_id, word_source, lang_source, lang_target)` with frequency tracking.
- Dictionary is browsable and editable by the user.

### 7.4 LLM-Based Text / Dialogue Generation
- New page `6_Generate.py`: user prompts LLM to generate texts or dialogues in the target language.
- Difficulty and topic configurable.
- Generated texts saved directly to the text library.

### 7.5 TTS + MP3 Storage in PostgreSQL
- TTS via **gTTS** (Google Text-to-Speech), extensible via abstract `TTSService`.
- Generated MP3 audio stored as `BYTEA` in PostgreSQL (per user, per text).
- Audio playable in-browser via `st.audio`; downloadable as MP3.
- BYTEA approach chosen for prototype simplicity (browser/mobile accessible); can migrate to object storage later if needed.

### 7.6 psycopg Version Fix
- The project uses **psycopg v3** (`psycopg[binary]`) throughout.
- `dictcc_translation_service.py` used `psycopg2` — this is migrated to psycopg v3.
- `DictCcTranslationService` DB connection moved from `__post_init__` to lazy init in `translate_word()` to prevent crashes when no DB is configured.

### 7.7 Multi-Page Streamlit App
- `app.py` becomes an auth-gate entry point.
- Feature pages moved to `pages/` (Streamlit native multi-page).
- Navigation: Decoder | Texts | Dictionary | Vocab Trainer | Audio | Generate | Settings.

### 7.8 SECRET_KEY — API Key Encryption
- A `SECRET_KEY` environment variable is required at the app level.
- It is used exclusively to encrypt and decrypt the **LLM API keys** (OpenAI, Anthropic) that users store in the database.
- Encryption: **Fernet** (symmetric AES-128-CBC), implemented in `services/auth_service.py`.
- Flow:
  1. User enters their API key in Settings → `AuthService.encrypt_api_key()` encrypts it with the `SECRET_KEY`.
  2. Encrypted bytes (`BYTEA`) are stored in the `user_api_keys` table — never the plaintext key.
  3. On login, the key is decrypted and held only in `st.session_state` for the duration of the session.
- Passwords are handled separately via **bcrypt** (no key required).
- **Important:** Changing the `SECRET_KEY` after users have stored keys renders all stored keys unreadable. The key must remain stable for the lifetime of the database.
- Set via `.streamlit/secrets.toml` (local) or Streamlit Cloud secrets (deployment). This file is in `.gitignore` and must never be committed.

---

**Status:** Original stack decision (Variant 1) documented; Section 7 reflects all updates agreed as of 2026-03-07.
