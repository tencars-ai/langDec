# CLAUDE.md – langDec Project Notes

## Project Overview
**langDec** is a language learning prototype based on the **Birkenbihl decoding method**.
Core idea: word-for-word (decoded) translation preserving original word order + contextual translation side by side.

**Status:** Prototype (Variant 1 – Streamlit) — MVP-01 in production since 2026-05-15
**Branch strategy:** `main` = stable, auto-deployed to Streamlit Cloud. All work happens on dedicated branches.

---

## Development workflow

**Rule: never commit directly to `main`.** Every change — feature, fix, refactor, doc tweak — goes through a dedicated branch.

- Feature branches: `feature/<short-name>`
- Bug fix branches: `fix/<short-name>` (or a longer-lived batch branch like `fix/mvp-01` for a release-window bugfix series)
- Refactor branches: `refactor/<short-name>`
- DB schema changes: include a `sql/00N_*.sql` delta migration on the same branch (see `sql/README.md`)

**Per-branch checklist before merging to `main`:**
1. Local smoke test — start `streamlit run app.py`, exercise the changed flow + at least login/logout.
2. If DB schema changed: delta migration tested locally and ready to apply to prod.
3. Merge to `main` (auto-deploys to Streamlit Cloud).
4. If schema changed: run the delta migration against the prod Neon DB after the cloud build is green.

**Why this matters:** Prod holds real tester data since 2026-05-15 (Tag 0), and Streamlit Cloud auto-deploys `main`. So `main` must always be green and schema must always be migratable.

---

## Tech Stack

| Layer | Technology |
|---|---|
| UI | Streamlit (multi-page) |
| Auth | own bcrypt login/register in `app.py` + `st.navigation()` (NOT streamlit-authenticator — that dependency is unused) |
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
app.py                   # Entry point: auth gate (login/register), PAGES nav, session init
pages/
  0_Start.py             # "Decode Text" – ACTIVE, the main product surface today
  1_Decode.py            # decode-only variant – commented out of PAGES
  2_Translate.py         # translate-only variant – commented out of PAGES
  3_Texts.py             # "Text Library" – ACTIVE
  4_Dictionary.py        # Personal dictionary – commented out of PAGES
  5_Vocab_Trainer.py     # Flashcard trainer – commented out of PAGES
  6_Audio.py             # TTS playback / saved audio – commented out of PAGES
  7_Generate.py          # LLM text generation – commented out of PAGES
  8_Settings.py          # "Settings" – ACTIVE (preferences, API keys, password, delete account)
  9_Help.py              # "Help" – ACTIVE
domain/
  decoder.py             # WordByWordDecoder – core Birkenbihl decode logic, chunking, alignment
  translator.py          # Translator – contextual translation wrapper
  vocabulary.py          # VocabularyManager – dictionary CRUD + frequency
  flashcard.py           # FlashcardBox – spaced repetition logic
prompts/
  __init__.py            # load_prompt_config(src, tgt) – YAML loader, lru_cache
  _default.yaml          # universal Birkenbihl rules + anti-patterns
  pt_de.yaml             # the only language-pair file so far
services/
  translation_service.py # TranslationService (ABC), GoogleDeepTranslatorService, ArgosTranslateService
  dictcc_translation_service.py  # DictCcTranslationService – psycopg v3, lazy init, not in UI
  llm_service.py         # LLMService (ABC), OpenAIService, ClaudeService, build_llm_service
  prompt_builder.py      # build_system_prompt / build_user_prompt from a PromptConfig
  preferences_service.py # PreferencesService – user_preferences load/save
  tts_service.py         # TTSService (ABC), GTTSService
  auth_service.py        # AuthService – bcrypt hash, Fernet API key encryption
  db_service.py          # DBService – psycopg v3, fresh connection per call
  audio_storage_service.py  # AudioStorageService – MP3 BYTEA in PostgreSQL
  ocr_service.py         # OCRService (ABC), TesseractOCRService, EasyOCRService
utils/
  ui.py                  # LANGUAGES dict, save_to_library()
  styles.py              # central CSS (inject_styles and friends)
  auth_ui.py             # require_login(), render_sidebar()
  services_ui.py         # get_decode_service(), get_translate_service(), preference getters
tests/
  test_decoder_e2e.py    # standalone LLM prompt-iteration harness (pt->de reference suite)
scripts/
  convert_freedict_tei_to_tsv.py  # Convert FreeDICT TEI XML to TSV
  load_dictcc_to_db.py            # Load dict.cc data into PostgreSQL
sql/
  schema.sql             # Full DB schema (authoritative baseline)
  README.md              # delta-migration workflow; next free number is 007
dictionaries/            # Local dictionary files (gitignored)
documents/               # Project documentation (requirements, concepts, architecture)
```

**Note:** `app.py` builds navigation from a module-level `PAGES` list. Only four pages are active;
the others are written and working but commented out (MVP-01 scoping decision, see `TODO.md`).

---

## Supported Languages (Prototype)
- German (`de`) – primary native language
- English (`en`)
- Portuguese (`pt`)
- Swedish (`sv`)

Architecture is language-agnostic. Adding a language pair requires **one YAML file**
`prompts/<src>_<tgt>.yaml` plus an entry in the `LANGUAGES` dict in `utils/ui.py` — no code change.
So far only `pt_de.yaml` exists; every other pair runs on the universal rules in `_default.yaml`
alone. See `documents/decoder-prompting-rules.md` §7.

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
- `app.py` – auth gate (login/register) + `PAGES` navigation list
- `pages/0_Start.py` – main decoder UI (the active product surface)
- `domain/decoder.py` – Birkenbihl decode logic
- `prompts/_default.yaml` + `prompts/<src>_<tgt>.yaml` – the language rules (data, not code)
- `services/prompt_builder.py` – how those rules become a prompt
- `services/llm_service.py` – add/modify LLM translation backends
- `services/translation_service.py` – Google/Argos fallback backends
- `utils/services_ui.py` – service resolution (there is no `AVAILABLE_SERVICES` dict)
- `sql/schema.sql` – full DB schema (authoritative baseline)
- `requirements.txt` – Python dependencies
- `documents/decoder-prompting-rules.md` – **the authority on decode behaviour**; read before
  touching any prompt
- `documents/vokabeluniversum_overview.md` – entry point to the current concept work

## Documentation status (2026-08-08)

Several documents in `documents/` have drifted from the code and are being corrected on branch
`verbiverse-concept`. Until that lands, treat them with care:

| Document | State |
|---|---|
| `decoder-prompting-rules.md` | current, verified against code — the authority |
| `vokabeluniversum_*.md`, `target_architecture.md`, `cross_lingual_similarity_concept.md`, `coding_standards.md`, `code_review_2026-08.md` | new, 2026-08-08 |
| `software-architecture.md` | **stale**: describes a JSON decoder (`BIRKENBIHL_JSON_SCHEMA`) that no longer exists |
| `adding_translation_services.md` | **stale**: references `AVAILABLE_SERVICES` in `app.py`, which does not exist |
| `technical_implementation_plan.md`, `technical_concept_prototype_stack_tooling.md` | partly stale: page names, and an incorrect claim that auth uses streamlit-authenticator |
| `anforderungsdokument_*.md`, `technisches_konzept_*.md` (DE) | **v1 state**, superseded by their EN counterparts |

**Product name:** use **langDec** everywhere. Several older documents use other names.
