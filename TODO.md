# TODO – langDec

## Refactoring (completed 2026-03-07)

- [x] **psycopg version conflict fixed**
  - `dictcc_translation_service.py` migrated from `psycopg2` to `psycopg` v3
  - `psycopg-pool` added to requirements.txt

- [x] **`DictCcTranslationService` – lazy DB init**
  - `__post_init__` no longer raises on missing `DATABASE_URL`
  - Connection opened lazily in `_get_connection()` with graceful fallback in `translate_word()`

- [x] **`argostranslate` added to `requirements.txt`**

- [x] **dict.cc removed from default AVAILABLE_SERVICES in Decoder page**
  - Code retained, not surfaced in UI by default

---

## Implementation Phases

### Phase 1 – Foundation
- [x] `sql/schema.sql` — full DB schema
- [x] `services/db_service.py` — connection pool, base queries
- [x] `services/auth_service.py` — password hash, API key encryption
- [x] Auth gate in `app.py` (login + register)
- [ ] Run `sql/schema.sql` against Neon (neon.tech) / local PostgreSQL instance
- [ ] Set `DATABASE_URL` and `SECRET_KEY` in `.streamlit/secrets.toml`

### Phase 2 – LLM Integration
- [x] `services/llm_service.py` — OpenAI + Claude implementations
- [x] `pages/7_Settings.py` — API key management UI
- [x] LLM service wired into Decoder via `TranslationService` interface

### Phase 3 – Persistence
- [x] `pages/2_Texts.py` — text library with folders
- [x] Auto-save decoded words to `user_dictionary` (in `pages/1_Decoder.py`)
- [x] `domain/vocabulary.py` — deduplication + frequency

### Phase 4 – Dictionary & Vocab Trainer
- [x] `pages/3_Dictionary.py` — browse/search personal dictionary
- [x] `domain/flashcard.py` — flashcard box logic
- [x] `pages/4_Vocab_Trainer.py` — trainer UI

### Phase 5 – Audio
- [x] `services/tts_service.py` — gTTS implementation
- [x] `services/audio_storage_service.py` — BYTEA store/retrieve
- [x] `pages/5_Audio.py` — playback + MP3 save per user

### Phase 6 – LLM Generation
- [x] `pages/6_Generate.py` — dialogue/text generation UI

---

### To-be-checked later
-[ ] Datenmodell gg. anpassen. Pro Trabelle sprechende ID. email als unique identifier und mandatory.
-[ ] Spellcorrection ausschalen oder entsprechen der sprache durchfüreh (rote kringellinien)
-[ ] translator und decoder in 2 verschiedene menüpunkte unterteilen
-[ ] wenn ich ausgeloggt bin bleibt die aktuelle seite ohne login button
-[ ] keine Rückmeldung wenn Folder angelegt wurde, und sieht man irgendwo die folder?
-[ ] decoder algorithmus ggf. anpassen, dass der ganze text und nicht einzelne wörter vergleichen werden.
-[ ] abfangen wenn der Text leer ist, nicht sagen es sei komplett
-[ ] text und md files erlauben
-[ ] beim speichern solle man auch den Folder wählen können
-[ ] erklärungen, naming, vision, help editieren und birkenbihl nicht zu prominent platzieren. all in one, from zero to hero, build your own Wortschatz.

## Remaining / Future

### Near-term
- [ ] CSV import/export for vocabulary
- [ ] Clickable word-by-word output (single-word lookup)
- [ ] Playlist management UI (tables in DB are ready)
- [ ] Streamlit Cloud deployment with Neon (neon.tech) secrets configured

### Vocabulary card extensions (planned)
- [ ] Link similar words (similar meaning, similar sounding)
- [ ] Link antonyms and synonyms
- [ ] Verb conjugation tables: store and practice tenses per verb card
- [ ] DB: `vocab_relations` table (word_id, related_word_id, relation_type)
- [ ] DB: `verb_conjugations` table (dictionary_entry_id, tense, person, form)
- [ ] UI: conjugation view in Dictionary and Vocab Trainer

### Long-term
- [ ] Variant 2: FastAPI + Reflex/React
