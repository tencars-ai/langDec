# langDec — Software Architecture

Stand: nach JSON-Decoder-Refactor (Phasen 1–5).

This document describes the overall architecture of the langDec prototype:
system context, container/module structure, cross-cutting concerns, data flows,
and the trade-offs taken for the MVP.

---

## 1. System Context

What the system touches from the outside.

```
                          ┌─────────────────────────┐
                          │       END USER          │
                          │     (Browser-Tab)       │
                          └────────────┬────────────┘
                                       │ HTTPS
                                       ▼
                          ┌─────────────────────────┐
                          │   langDec  Streamlit    │
                          │   (Hosted: Streamlit    │
                          │    Cloud — planned)     │
                          └────┬──────┬──────┬──────┘
                               │      │      │
              ┌────────────────┘      │      └─────────────────┐
              │                       │                        │
              ▼                       ▼                        ▼
   ┌─────────────────┐   ┌───────────────────────┐   ┌──────────────────┐
   │  PostgreSQL     │   │  LLM Providers        │   │  Translation /   │
   │  (Neon,         │   │  • OpenAI API         │   │   TTS / OCR      │
   │   eu-central-1) │   │  • Anthropic API      │   │  • Google deep-  │
   │                 │   │   (Tool-Use / JSON    │   │    translator    │
   │  User-Auth      │   │    Schema enforced)   │   │  • gTTS          │
   │  User-Texts     │   │                       │   │  • EasyOCR       │
   │  Vocab/Cards    │   └───────────────────────┘   │    (local model) │
   │  Audio (BYTEA)  │                               │  • Argos (local) │
   │  Enc. API-Keys  │                               └──────────────────┘
   └─────────────────┘
```

### Key Characteristics

- **Single Tenant per Browser Session** — Streamlit isolates session state per
  browser tab; no shared in-memory user state.
- **Multi-Tenant in the database** — every table carries a `user_id` column;
  strict per-user isolation at the persistence layer.
- **BYO-Key model** — users provide their own LLM API keys. Stored encrypted
  at rest (Fernet) and decrypted into memory per session only.
- **Two server-side secrets** — `DATABASE_URL` and `SECRET_KEY` (Fernet master
  key). Everything else is per-user.

---

## 2. Container / Module View

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           langDec  (Python 3.12)                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────────┐                                                   │
│  │  app.py          │  ◄── Entry point. Auth gate + st.navigation().    │
│  │  (Auth Gate)     │      Routes to Pages if user_id in session,       │
│  └────────┬─────────┘      otherwise shows Login/Register form.         │
│           │                                                             │
│           │ st.session_state.user_id / .username / .llm_services        │
│           │                                                             │
│  ┌────────▼─────────┐  ┌──────────────────┐  ┌────────────────┐         │
│  │ pages/0_Start.py │  │ pages/3_Texts.py │  │ pages/         │         │
│  │ (Decode/TTS/     │  │ (Library)        │  │ 8_Settings,    │ ...     │
│  │  Translate UI)   │  │                  │  │ 9_Help         │         │
│  └────────┬─────────┘  └──────────────────┘  └────────────────┘         │
│           │                                                             │
│  ┌────────▼──────────────────────────────────────────────────────────┐  │
│  │  utils/   (UI helpers, no domain code)                            │  │
│  │  auth_ui.py · services_ui.py · ui.py · styles.py                  │  │
│  └────────┬──────────────────────────────────────────────────────────┘  │
│           │                                                             │
│  ┌────────▼──────────────────────────────────────────────────────────┐  │
│  │  domain/   (Pure logic, UI-free, portable)                        │  │
│  │  decoder.py  · translator.py  · vocabulary.py  · flashcard.py     │  │
│  └────────┬──────────────────────────────────────────────────────────┘  │
│           │                                                             │
│  ┌────────▼──────────────────────────────────────────────────────────┐  │
│  │  prompts/   (Config-as-data, since refactor phase 1)              │  │
│  │  _default.yaml · pt_de.yaml · …  +  __init__.py (loader, LRU)     │  │
│  └────────┬──────────────────────────────────────────────────────────┘  │
│           │                                                             │
│  ┌────────▼──────────────────────────────────────────────────────────┐  │
│  │  services/   (Adapters to externals + cross-cutting)              │  │
│  │  llm_service · translation_service · tts · ocr · auth · db ·      │  │
│  │  audio_storage · prompt_builder · dictcc                          │  │
│  └────────┬──────────────────────────────────────────────────────────┘  │
│           │                                                             │
└───────────┼─────────────────────────────────────────────────────────────┘
            │
   ┌────────▼───────────────────────────────────────┐
   │  External I/O                                  │
   │  Postgres · OpenAI/Anthropic · gTTS · Google · │
   │  EasyOCR (local model file)                    │
   └────────────────────────────────────────────────┘
```

---

## 3. Architectural Patterns in Use

| Pattern | Where used | Why |
|---|---|---|
| **Layered Architecture** | UI / Domain / Service / Persistence | Clear separation of concerns; the domain layer is portable to other UI stacks (FastAPI/Reflex). |
| **Adapter / Port** | `TranslationService` (ABC) — implemented by Google, Argos, **and** the LLM services | Backends are drop-in interchangeable without the decoder/translator caring. |
| **Strategy** | `_decode_llm` vs. `_decode_per_word` inside `WordByWordDecoder` | Same use case, different algorithm depending on whether the service supports JSON Birkenbihl output. |
| **Factory** | `build_llm_service(provider, api_key)` | Creates provider-specific service instances from a string identifier. |
| **Config-as-Data** | `prompts/*.yaml` + `PromptConfig` | New language pairs and disambiguation rules are added via YAML files — no Python edits. |
| **Schema-First Output** | `BIRKENBIHL_JSON_SCHEMA` with OpenAI `response_format=json_schema strict` and Anthropic `tool_use input_schema` | Structurally eliminates format errors in LLM responses. Only semantic per-line mismatches remain. |
| **Producer/Consumer + ThreadPool** | UI hot-path (3 tasks parallel) + decoder chunking (up to 3 LLM calls parallel) | Handles I/O-bound work without async complexity. |
| **Lazy Initialization** | DictCcService DB connect, EasyOCR model load, LLM-service reload on Settings page | App boots even when optional backends are unavailable. |
| **Graceful Degradation** | Per-line mismatch → per-word fallback; LLM call failure → whole result falls back to per-word; decrypt failure → warning, not crash | The app always returns *something*. |

---

## 4. Cross-Cutting Concerns

### 4.1 Authentication & Session Lifecycle

```
Login (app.py):
  1. Verify username/email + password (bcrypt).
  2. _load_llm_service: decrypt all DB-stored API keys (Fernet),
     build LLM services into st.session_state.llm_services.
  3. _init_preferences: choose a default decode/translate service
     based on which provider keys are present.
  4. st.rerun() → st.navigation() now routes to pages.

Logout (sidebar):
  1. st.session_state.clear()
  2. st.rerun() → app.py runs again, user_id is gone, login form shown.
```

### 4.2 Secrets Management

```
SECRET_KEY  (server secret, ≥32 chars, in .streamlit/secrets.toml)
    └─ Fernet → encrypts/decrypts user API keys at rest
                in user_api_keys.api_key_encrypted (BYTEA)

DATABASE_URL  (Postgres connection string, secrets.toml)
    └─ psycopg ConnectionPool (singleton in services/db_service.py)

User API keys  (BYO, in user_api_keys, BYTEA Fernet-encrypted)
    └─ decrypted into memory at login; cleared on logout via
       st.session_state.clear().
```

### 4.3 Multi-Tenant Isolation

- Every user-owned table includes `user_id`.
- Every page-level query filters with `WHERE user_id = %s`.
- Cross-user data leakage is structurally impossible because Streamlit
  isolates `st.session_state` per browser session.

### 4.4 Error Handling Strategy

| Layer | Strategy |
|---|---|
| Service calls (LLM, DB, gTTS, OCR) | try/except → structured fallback, never raise up to UI |
| Decoder | Per-line mismatch → per-word fallback with annotation in comments |
| UI | `st.error()` / `st.warning()` for human-readable feedback; flow does not abort |
| Auth | Decrypt failure surfaced as warning on Settings page, not as crash |

### 4.5 Caching

- `functools.lru_cache(maxsize=32)` on `load_prompt_config()` — one cache slot
  per language pair.
- `st.session_state.llm_services` as a runtime cache of decrypted LLM-service
  instances (per session).
- psycopg `ConnectionPool` as a DB connection cache (module-level singleton).

### 4.6 Concurrency Model

Single-process, **threading** (no asyncio):

```
Streamlit Worker Thread (per browser session)
    │
    ├─ ThreadPoolExecutor in UI hot-path  (max_workers=3)
    │       ├─ Translate-Future
    │       ├─ Audio-Future
    │       └─ Decode-Future
    │              │
    │              └─ ThreadPoolExecutor in decoder  (max_workers=3)
    │                      ├─ Chunk-1 LLM call
    │                      ├─ Chunk-2 LLM call
    │                      └─ Chunk-3 LLM call
    │
    └─ st.* updates always on the main thread (Streamlit requirement)
```

LLM calls are **I/O-bound**, so threading is sufficient — no asyncio needed.

---

## 5. Component-Level Data Flows

| User action | What happens |
|---|---|
| **Login** | Browser → app.py → bcrypt verify → DB read → Fernet decrypt API keys → LLM services into session → rerun |
| **Decode** | UI → 3 parallel futures (Translate, Audio, Decode) → JSON-schema-enforced LLM call → parser → aligned output back → render in `_decoded_slot` |
| **Add vocab** | UI → `VocabularyManager.upsert()` → DB INSERT/UPDATE (frequency increment) → flashcard row created for SRS |
| **Save audio** | gTTS bytes → `AudioStorageService.save()` → BYTEA in `audio_files` table |
| **Save settings** | UI → DB UPSERT API-key (Fernet-encrypted) → session-state refresh → rerun |

### 5.1 Decode Hot-Path (detailed)

```
User clicks "Decode" in pages/0_Start.py
       │
       ▼
ThreadPoolExecutor (max_workers=3)  ───┬─► Translator.translate()
                                       │       └─► Google.translate_text()
                                       │
                                       ├─► GTTSService.synthesize()
                                       │       └─► gTTS API → MP3 bytes
                                       │
                                       └─► WordByWordDecoder.decode(debug=…)
                                               │
                                               ▼
                                       _preprocess_lines()    ← strip "1.", "-", …
                                               │
                                               ▼
                                       Chunk into groups of 10 lines
                                               │
                                       ┌───────┴───────┐
                                       ▼               ▼
                              _decode_chunk()    _decode_chunk()  (parallel)
                                       │
                                       ▼
                              ClaudeService.translate_birkenbihl_full()
                                       │
                                       ├─► load_prompt_config("pt","de")    [cached]
                                       │       └─► merge _default.yaml + pt_de.yaml
                                       ├─► build_system_prompt(cfg)
                                       ├─► build_user_prompt(cfg, lines)
                                       └─► Anthropic API
                                              tools=[{input_schema=BIRKENBIHL_JSON_SCHEMA}]
                                              tool_choice="emit_birkenbihl_decoding"
                                               │
                                               ▼
                                       Structured JSON  (schema-enforced)
                                               │
                                               ▼
                              _parse_birkenbihl_json_response()
                                               │
                                       ┌───────┴───────┐
                                       ▼               ▼
                                 perfect case    mismatch → _per_word_fallback
                                               │
                                               ▼
                              {line_results, comments, raw_payload}
                                               │
                                               ▼
                                       _assemble() in decoder
                                               │
                                               ├─► TokenPair(src, tgt)
                                               ├─► _format_aligned()    (columns)
                                               ├─► _prepend_marker()    (list markers)
                                               └─► DecoderResult(
                                                       aligned_text,
                                                       comments,
                                                       debug_info,
                                                   )
                                               │
                                               ▼
                              UI renders into _decoded_slot,
                              debug block when debug_mode is on
```

---

## 6. Deployment & Runtime Model

### Current (Variant 1, MVP)

- Local: `streamlit run app.py`
- Planned hosting: Streamlit Cloud (Free Tier)
- Database: Neon (Postgres-as-a-Service, Frankfurt)
- LLM/TTS: external, per request
- OCR: EasyOCR runs locally (model file shipped with the app)

### Planned (Variant 2)

- Backend: FastAPI (REST/gRPC)
- Frontend: Reflex or React/Next.js
- Mobile: React Native / Expo
- Database: unchanged (Postgres)
- `domain/` and `prompts/` are reused 1:1 — this is the actual payoff of the
  layered architecture.

---

## 7. Intentional Trade-offs (MVP context)

| Decision | Gain | Cost |
|---|---|---|
| Streamlit instead of FastAPI+frontend | Very fast iteration, all-Python stack | Single-server, no caching layer, no WebSockets |
| Audio as BYTEA in Postgres | No second storage system to manage | Database grows; will need migration to object storage later |
| LLM keys per user (BYO) | No centralized API cost | User setup friction |
| Threading instead of asyncio | Easier to reason about and debug | Streamlit-specific; rewrite needed for the FastAPI variant |
| YAML prompts instead of DB-stored prompts | Versioned in git, easy to read | No per-user overrides (yet) |
| Pipe → JSON refactor (recent) | Structural format errors impossible | Schema must be maintained when providers update |

---

## 8. Extension Points

| If you want to… | …touch this |
|---|---|
| Add a new language (e.g. Italian) | `utils/ui.py` (LANGUAGES) + `prompts/it_de.yaml` (and reverse direction) |
| Add a new LLM provider (e.g. Gemini) | `services/llm_service.py` — new subclass + factory entry |
| Add a new TTS provider | `services/tts_service.py` — new `TTSService` subclass |
| Per-user prompt overrides | Extend `prompts/__init__.py` with a DB layer + new column in `user_*` tables |
| Add a new UI page | `pages/X_Name.py` + entry in `PAGES` in `app.py` |
| Schema change | New file `sql/00X_*.sql` (incremental migration) |

---

## 9. Known Open Issues / Roadmap

- **Prompt fidelity on Claude Haiku** — the smaller model does not reliably
  follow all rules even with explicit anti-pattern examples. Options:
  upgrade to Sonnet, or further prompt restructuring.
- **11 remaining language-pair YAMLs** are still empty (only `pt_de` is fully
  authored).
- **CSV import/export for vocabulary** — planned, not yet implemented.
- **Language-aware tokenization** (e.g. clitic splitting) — deliberately
  out of scope; may be revisited if hyphen-in-target representation proves
  insufficient.

---

## 10. Key Files to Know

| File | Purpose |
|---|---|
| `app.py` | Auth gate + page navigation |
| `pages/0_Start.py` | Combined Decode + Translate + Audio UI |
| `pages/8_Settings.py` | API-key management, service preferences, debug toggle |
| `domain/decoder.py` | Birkenbihl decoding logic (preprocessing, chunking, alignment) |
| `services/llm_service.py` | LLM adapters (OpenAI, Claude) + JSON parser + schema |
| `services/prompt_builder.py` | Builds system + user prompts from a PromptConfig |
| `prompts/__init__.py` | YAML loader + PromptConfig dataclass + LRU cache |
| `prompts/_default.yaml` | Universal Birkenbihl rules + anti-patterns |
| `prompts/pt_de.yaml` | Portuguese → German rules, examples, disambiguation |
| `sql/schema.sql` + `sql/005_*.sql` | Database schema + migrations |
| `utils/services_ui.py` | Resolves the currently selected service per session state |
| `utils/auth_ui.py` | Login guard + sidebar with logout |

---

*Last updated: after Phase 5 of the JSON-decoder refactor (debug mode + pt_de
disambiguation expansion).*
