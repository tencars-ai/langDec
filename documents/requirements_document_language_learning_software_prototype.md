# Requirements Document – Language Learning Software (Prototype)

**Document Status:** Updated – v2 (revised vision, LLM integration, user management)

---

## 1. Project Goal

The goal is to develop a software prototype for effective foreign language learning based on the **decoding principle (inspired by the Birkenbihl method)**. The software should enable learners to translate texts both **contextually** and **1:1 word-by-word (decoded)** and process them both auditorily and visually.

**Core vision:** Each user builds their own personal vocabulary over time – not from static textbooks or pre-built dictionaries, but from the texts that personally interest them. LLMs (initially ChatGPT and Claude) are used to generate high-quality word-by-word translations, which are then saved as the user's personal dictionary. This dictionary grows with every text the user processes.

The prototype starts with the languages **German (native language)**, **English**, and **Portuguese**, but should be designed to be **language-agnostic** so that additional languages can be easily added later.

---

## 2. Target Audience

- Adult self-learners
- Language enthusiasts
- Users of the Birkenbihl method or similar decoding approaches
- Autodidacts with a focus on reading & listening

---

## 3. Supported Languages (Initial Phase)

- German (source/native language)
- English
- Portuguese

> Architecture must be designed so that any language can be both **source** and **target language**.

---

## 4. User Management

A rudimentary user management is required from the start, since all data (texts, vocabulary, audio) is personal and must be stored per user.

### 4.1 User Accounts

- Simple registration and login (username + password)
- No social login or OAuth required in the prototype
- Each user has their own isolated data space:
  - Texts and folders
  - Personal dictionary
  - Vocabulary trainer state
  - Saved audio / MP3 files

### 4.2 Session Management

- Users stay logged in within a session
- No complex role management in the prototype (all users have equal access to their own data)

---

## 5. Core Functions

### 5.1 Text Management

- Texts can be:
  - inserted via **copy & paste**
  - read from images/PDFs via **OCR scanner**
  - **generated via LLM** (see Section 6)
- Texts are:
  - organized in **folders** per user
  - stored persistently in the database (structure: user → folders → texts)
  - provided with metadata (language, title, date, notes)

---

### 5.2 Translation Modules

#### 5.2.1 Contextual Translation

- Classic, natural translation
- Sentence-by-sentence or paragraph-by-paragraph display
- Provided by: Google Translate, Argos Translate (offline), or LLM

#### 5.2.2 Decoded Translation (Birkenbihl Principle)

- **1:1 word-for-word translation**
- Preservation of original word order
- Goal: Transparency of foreign language structure
- Provided by: **LLM (primary)**, Google Translate (fallback)

**Display Options:**

- Original text
- Decoded translation directly below or inline
- Optional highlighting of individual words

#### 5.2.3 Translation Services (Priority Order)

| Service | Type | Use Case |
|---|---|---|
| LLM (ChatGPT / Claude) | Online API | Primary – decoded + contextual translation |
| Google Translate | Online API | Fallback for contextual translation |
| Argos Translate | Offline | Fallback when no internet available |
| dict.cc | Local DB | **Deprioritized** – not needed given LLM approach |

> **Note on dict.cc:** Static dictionaries like dict.cc are not aligned with the personal vocabulary vision. They may be kept as a last-resort fallback but should not be a primary feature.

---

### 5.3 Personal Dictionary (User Vocabulary)

This is the central data asset of each user. It is built automatically as the user processes texts.

- Every word-by-word translation performed via LLM is stored in the user's personal dictionary
- Dictionary entries contain:
  - Source word (foreign language)
  - Translation (native language)
  - Language pair (e.g., pt → de)
  - Source text reference (which text the word appeared in)
  - Date first seen
  - Optional: LLM-provided context / example sentence
- The dictionary grows over time and reflects **the vocabulary the user personally encountered**
- Duplicate entries are handled gracefully (update frequency/date, don't duplicate)

---

### 5.4 Individual Word Lookup

- Words can be highlighted/clicked in the displayed text
- Lookup via LLM (returns: translation, word class, optional example sentence)
- Result can be directly saved to the user's personal dictionary
- Already-known words (in user's dictionary) can be visually marked in the text

---

### 5.5 Audio & Listening Functions (Text-to-Speech)

- Texts can be read aloud:
  - Original language
  - Optionally also translation
- Controls:
  - Playback speed
  - Repetition of individual sections

#### Playlists

- Texts can be compiled into **listening playlists** per user
- Playlists can be played within the app

#### MP3 Storage

- Users can save MP3 audio files of texts they want to listen to repeatedly
- MP3s are stored **per user** in the database / file storage
- MP3s can be downloaded for use in external players

---

### 5.6 Vocabulary Trainer (Flashcard Principle)

- Integrated vocabulary trainer based on the **flashcard box principle**
- Works directly with the user's **personal dictionary** (Section 5.3) – no separate import needed
- Each vocabulary card contains:
  - Word (foreign language)
  - Translation (native language)
  - Optional example sentence (from LLM or from source text)

#### Learning Logic

- Multiple learning boxes (e.g., new → practiced → learned)
- Repetition logic (spaced repetition, manual or semi-automated)

#### Export

- **CSV export** of the user's personal vocabulary collection
- CSV import as optional convenience feature (e.g., to seed initial vocabulary)

---

## 6. LLM Integration

### 6.1 Translation via LLM

- LLM APIs used: **OpenAI (ChatGPT)** and **Anthropic (Claude)**
- API key management per user (user provides their own key, stored encrypted) or centrally configured
- LLM is called for:
  - Word-by-word (decoded) translation
  - Contextual translation
  - Individual word lookup with context

### 6.2 Text & Dialogue Generation

- Users can request LLM to generate learning texts or dialogues:
  - Topic selectable (e.g., "Dialogue at a café in Portuguese")
  - Difficulty level selectable
  - Language pair selectable
- Generated texts are saved directly to the user's text library (with metadata)
- Generated texts can immediately be processed with the decoder

---

## 7. Data Organization

All data is stored **per user** in a PostgreSQL database.

| Data Type | Storage |
|---|---|
| User accounts | DB: `users` table |
| Folders | DB: `folders` table (FK: user) |
| Texts | DB: `texts` table (FK: folder/user) |
| Personal dictionary | DB: `user_dictionary` table (FK: user) |
| Vocabulary trainer state | DB: `vocab_cards` table (FK: user) |
| Playlists | DB: `playlists` table (FK: user) |
| Audio / MP3 files | File storage (or DB blob), referenced per user |

---

## 8. Non-Functional Requirements

- Modular structure (translation, audio, vocabulary, LLM separated as services)
- Extensibility to additional languages and LLM providers
- Platform-independent design (for future desktop/web/mobile implementations)
- API keys for LLMs must be stored securely (not in plain text)
- Focus on **learning usability**, not on perfect AI translation

---

## 9. Out of Scope (Prototype Phase)

- Gamification (points, badges, leaderboards)
- Automatic language detection
- Social features (sharing vocabulary with other users)
- Complex role-based access control
- Mobile-native app (web-responsive is sufficient)

---

## 10. Vision (Long-term)

- Each user owns a growing, **personal vocabulary** built from texts they personally care about
- LLM as the primary intelligence layer – for translation, lookup, and content generation
- Combination of reading, listening, and active vocabulary work in one tool
- Fully language-agnostic learning system
- Extended analysis of grammatical structures via LLM
