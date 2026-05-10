# CLAUDE.md – langDec Project Notes

## Project Overview
**langDec** is a language learning prototype based on the **Birkenbihl decoding method**.
Core idea: word-for-word (decoded) translation preserving original word order + contextual translation side by side.

**Status:** Prototype (Variant 1 – Streamlit)
**Branch strategy:** `main` = stable, `dev2` = active development

---

## Tech Stack

| Layer | Technology |
|---|---|
| UI | Streamlit (multi-page) |
| Auth | streamlit-authenticator (login/register via PostgreSQL) |
| Language (backend) | Python |
| Database | PostgreSQL via psycopg v3 + psycopg-pool |
| LLM | OpenAI SDK + Anthropic SDK (primary translation + generation) |
| TTS | gTTS (Google Text-to-Speech) |
| OCR | EasyOCR (default), Tesseract (alternative) |
| Translation (fallback) | deep-translator (Google), Argos Translate (offline) |
| Audio storage | PostgreSQL BYTEA |
| PDF handling | PyMuPDF (fitz) |

**Run the app:**
```bash
streamlit run app.py
```

---

## Project Structure

```
app.py                   # Entry point: auth gate (login/register), session init
pages/
  1_Decoder.py           # Decoder (user-aware, auto-saves words to dictionary)
  2_Texts.py             # Text library with folders
  3_Dictionary.py        # Personal dictionary: browse, edit, delete
  4_Vocab_Trainer.py     # Flashcard trainer (spaced repetition box system)
  5_Audio.py             # TTS playback, MP3 save, saved audio list
  6_Generate.py          # LLM text/dialogue generation
  7_Settings.py          # API key management, password change
domain/
  decoder.py             # WordByWordDecoder – core Birkenbihl decode logic
  translator.py          # Translator – contextual translation wrapper
  vocabulary.py          # VocabularyManager – dictionary CRUD + frequency
  flashcard.py           # FlashcardBox – spaced repetition logic
services/
  translation_service.py # GoogleDeepTranslatorService, ArgosTranslateService (fallback)
  dictcc_translation_service.py  # DictCcTranslationService – psycopg v3, lazy init
  llm_service.py         # LLMService (ABC), OpenAIService, ClaudeService
  tts_service.py         # TTSService (ABC), GTTSService
  auth_service.py        # AuthService – bcrypt hash, Fernet API key encryption
  db_service.py          # DBService – psycopg v3 connection pool
  audio_storage_service.py  # AudioStorageService – MP3 BYTEA in PostgreSQL
  ocr_service.py         # TesseractOCRService, EasyOCRService
scripts/
  convert_freedict_tei_to_tsv.py  # Convert FreeDICT TEI XML to TSV
  load_dictcc_to_db.py            # Load dict.cc data into PostgreSQL
sql/
  schema.sql             # Full DB schema (run once against PostgreSQL/Neon)
dictionaries/            # Local dictionary files
documents/               # Project documentation (requirements, tech concept)
```

---

## Supported Languages (Prototype)
- German (`de`) – primary native language
- English (`en`)
- Portuguese (`pt`)
- Swedish (`sv`)

Architecture is language-agnostic; adding new languages requires only extending the `LANGUAGES` dict in `utils/ui.py` and ensuring translation service support.

---

## Key Architectural Decisions

- **LLM is the primary translation engine.** `LLMService` implements `TranslationService`, so `WordByWordDecoder` and `Translator` work without changes. Google/Argos remain available as fallbacks.
- **Translation services are interchangeable** via `TranslationService` base class. New services implement the interface and are added to `AVAILABLE_SERVICES` in `pages/1_Decoder.py`.
- **Decoder and Translator** in `domain/` are pure logic classes – no UI coupling.
- **Auth via login/register in `app.py`** – credentials stored in PostgreSQL with bcrypt hashes. `st.session_state.user_id` gates all pages.
- **API keys encrypted at rest** using Fernet symmetric encryption (app `SECRET_KEY` env var).
- **All user data scoped by `user_id`** – texts, dictionary, vocab cards, audio files.
- **EasyOCR is the default OCR** (works on Streamlit Cloud without extra install).
- **MP3 audio stored as BYTEA in PostgreSQL** – simple for prototype, can migrate to object storage later.
- **psycopg v3** (`psycopg[binary]` + `psycopg-pool`) used throughout. psycopg2 removed.
- **dict.cc** retained in code but not shown in Decoder UI by default (lazy DB init prevents crash).

---

## Translation Services

| Service | Type | Notes |
|---|---|---|
| `OpenAIService` | LLM (primary) | Requires OpenAI API key stored in DB |
| `ClaudeService` | LLM (primary) | Requires Anthropic API key stored in DB |
| `GoogleDeepTranslatorService` | Online (fallback) | Requires internet, uses deep-translator |
| `ArgosTranslateService` | Offline (fallback) | Requires language pack download |
| `DictCcTranslationService` | Local DB (hidden) | Lazy init; not shown in UI by default |

---

## Future Direction (Variant 2)
- Backend: **FastAPI**
- Frontend: **Reflex** (Python-first) or **React/Next.js**
- Mobile: React Native / Expo
- Database: PostgreSQL (unchanged)
- Core logic in `domain/` is designed to be reused across variants

---

## Out of Scope (Prototype)
- Gamification
- Automatic language detection
- OAuth / social login
- CSV import/export for vocabulary (planned)
- Clickable word-by-word output (planned)

## Environment Variables Required
| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `SECRET_KEY` | App-level secret for API key encryption (min 32 chars) |

Set in `.streamlit/secrets.toml` for local dev, Streamlit Cloud secrets for deployment.

---

## Key Files to Know
- `app.py` – auth gate (login/register)
- `pages/1_Decoder.py` – main decoder UI
- `domain/decoder.py` – Birkenbihl decode logic
- `services/llm_service.py` – add/modify LLM translation backends
- `services/translation_service.py` – Google/Argos fallback backends
- `sql/schema.sql` – full DB schema (run this first!)
- `requirements.txt` – Python dependencies
- `documents/technical_implementation_plan.md` – full technical plan
- `documents/technical_concept_prototype_stack_tooling.md` – stack decisions (EN)
