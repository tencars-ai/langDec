# Requirements Document – Language Learning Software (Prototype)

## 1. Project Goal
The goal is to develop a software prototype for effective foreign language learning based on the **decoding principle (inspired by the Birkenbihl method)**. The software should enable learners to translate texts both **contextually** and **1:1 word-by-word (decoded)** and process them both auditorily and visually.

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

## 4. Core Functions

### 4.1 Text Management
- Texts can be:
  - inserted via **copy & paste**
  - read from images/PDFs via **OCR scanner**
- Texts are:
  - organized in **folders**
  - stored locally (structure: folders → texts)
  - provided with metadata (language, title, date, notes)

---

### 4.2 Translation Modules

#### 4.2.1 Contextual Translation
- Classic, natural translation
- Sentence-by-sentence or paragraph-by-paragraph display

#### 4.2.2 Decoded Translation (Birkenbihl Principle)
- **1:1 word-for-word translation**
- Preservation of original word order
- Goal: Transparency of foreign language structure

**Display Options:**
- Original text
- Decoded translation directly below or inline
- Optional highlighting of individual words

---

### 4.3 Individual Word Lookup
- Words can be:
  - highlighted in the text
  - looked up individually
- Display of:
  - Basic meaning
  - optionally part of speech
- Words can be directly:
  - saved as a **vocabulary card**

---

### 4.4 Audio & Listening Functions (Text-to-Speech)
- Texts can be read aloud:
  - Original language
  - optionally also translation
- Controls:
  - Playback speed
  - Repetition of individual sections

#### Playlists
- Texts can be compiled into **listening playlists**
- Playlists can be:
  - played within the app
  - **exported as MP3 files** (e.g., for external players)

---

### 4.5 Vocabulary Trainer (Flashcard Principle)
- Integrated vocabulary trainer based on the **flashcard box principle**
- Each vocabulary card contains:
  - Word (foreign language)
  - Translation (native language)
  - optional example sentence

#### Learning Logic
- Multiple learning boxes (e.g., new → learned)
- Repetition logic (manual or automated later)

#### Import / Export
- **CSV import** of vocabulary
- **CSV export** of personal vocabulary collection

---

## 5. Data Organization
- Folder structure for texts
- Separate storage of:
  - Texts
  - Audio files
  - Vocabulary
  - Playlists

---

## 6. Non-Functional Requirements
- Modular structure (translation, audio, vocabulary separated)
- Extensibility to additional languages
- Platform-independent design (for future desktop/web/mobile implementations)
- Focus on **learning usability**, not on perfect AI translation

---

## 7. Out of Scope (Prototype Phase)
Not part of the first prototype:
- User accounts / cloud sync
- Gamification (points, badges, etc.)
- Automatic language detection

---

## 8. Vision (Long-term)
- Fully language-agnostic learning system
- Extended analysis of grammatical structures
- Combination of reading, listening, and active vocabulary work

---

**Document Status:** Prototype requirements definition
