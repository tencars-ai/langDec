"# langDec – Language Learning Software (Prototype)

## Overview
A language learning application based on the **Birkenbihl decoding method**, enabling learners to process texts through word-by-word translation alongside traditional contextual translation. The software combines reading, listening, and active vocabulary work to facilitate effective language acquisition.

## Key Features

### 🔤 Dual Translation Modes
- **Contextual Translation**: Natural, fluent translations
- **Decoded Translation**: 1:1 word-for-word translation preserving original word order for structural transparency

### 📚 Text Management
- Copy & paste text input
- OCR support for images and PDFs
- Folder-based organization with metadata
- Local storage

### 🔊 Audio & Listening
- Text-to-Speech in original and translated languages
- Adjustable playback speed
- Playlist creation and management
- MP3 export for external players

### 📖 Vocabulary Trainer
- Flashcard-based learning system
- Multiple learning boxes (spaced repetition)
- Quick word lookup and card creation
- CSV import/export

## Supported Languages (Initial Phase)
- German (native language)
- English
- Portuguese

The architecture is **language-agnostic** and designed for easy expansion to additional languages.

## Target Audience
- Adult self-learners
- Language enthusiasts
- Users of the Birkenbihl method
- Autodidacts focused on reading & listening

## Technical Approach
- Modular architecture (translation, audio, vocabulary as separate components)
- Platform-independent design
- Focus on learning usability over perfect AI translation
- Extensible for future desktop/web/mobile implementations

## Stack Summary

| Layer | Technology |
|---|---|
| UI | Streamlit (multi-page) |
| Auth | Login/register with bcrypt-hashed passwords in PostgreSQL |
| LLM | OpenAI API + Anthropic Claude API (primary translation & generation) |
| Translation fallback | Google Translate (deep-translator), Argos Translate (offline) |
| Database | PostgreSQL on Neon (neon.tech), accessed via psycopg v3 |
| TTS | gTTS (Google Text-to-Speech), MP3 stored as BYTEA in PostgreSQL |
| OCR | EasyOCR (images + PDF via PyMuPDF) |

## Security Notes

- **Passwords** are hashed with bcrypt and never stored in plaintext.
- **LLM API keys** (OpenAI, Anthropic) entered by users are encrypted with Fernet (AES-128) before storage. The encryption key is the `SECRET_KEY` environment variable, which must never be committed to version control.
- **`.streamlit/secrets.toml`** is in `.gitignore`. It contains `DATABASE_URL` and `SECRET_KEY` and must be set up locally before running the app.

## Setup

1. Copy `.streamlit/secrets.toml.example` (or create `.streamlit/secrets.toml`) with:
   ```toml
   DATABASE_URL="postgresql://..."
   SECRET_KEY="your-secret-key-min-32-chars"
   ```
2. Run the DB schema: `psql $DATABASE_URL -f sql/schema.sql`
3. Install dependencies: `pip install -r requirements.txt`
4. Run the app: `streamlit run app.py`

## Documentation
- [Technical Implementation Plan](documents/technical_implementation_plan.md)
- [Technical Concept & Stack Decisions](documents/technical_concept_prototype_stack_tooling.md)
- [Requirements Document](documents/requirements_document_language_learning_software_prototype.md)

---

**Status:** Prototype Development 

## Erkenntnisse
- Die Rechtschreibung muss gut sein vom input text geprüft / korrigiert werden, damit die Aussprache des generierten Texts funktioniert