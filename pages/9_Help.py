"""
Help page – overview of the app and the Birkenbihl method.
"""
import streamlit as st
from utils.auth_ui import require_login, render_sidebar
from utils.styles import inject_styles

st.set_page_config(page_title="langDec – Help", layout="wide")

require_login()
render_sidebar()
inject_styles()

st.title("Help")

st.markdown("""
## What is the Birkenbihl Method?

The Birkenbihl decoding method is a language learning approach developed by Vera F. Birkenbihl.
The core idea: read a foreign text **word-for-word** in your native language, preserving the original word order —
even if the result sounds grammatically broken. This forces your brain to absorb the foreign sentence structure naturally, without memorization.

**Step 1 – Decode:** Translate each word literally, keeping the original order.
> *"I go tomorrow to the store"* (from German: *Ich gehe morgen zum Laden*)

**Step 2 – Listen & Read:** Read the decoded text while listening to the original language.

**Step 3 – Vocabulary:** Words you encounter repeatedly end up in your personal dictionary automatically.

---

## Pages

| Page | What it does |
|---|---|
| **Decode** | Word-for-word literal translation (Birkenbihl method) |
| **Translate** | Natural, contextual translation of the full text |
| **Texts** | Save and organize texts in folders |
| **Dictionary** | Your personal vocabulary built from decoded texts |
| **Vocab Trainer** | Flashcard system with spaced repetition (3 boxes) |
| **Audio** | Text-to-Speech: play or save MP3 |
| **Generate** | Let the LLM write texts or dialogues for you to practice |
| **Settings** | Add your OpenAI / Anthropic API key, change password |

---

## Vocab Trainer – Box System

| Box | Status | Next review |
|---|---|---|
| 1 | New | After 1 day |
| 2 | Practiced | After 3 days |
| 3 | Learned | After 7 days |

Answer correctly → card moves to the next box.
Answer incorrectly → card goes back to box 1.

---

## Translation Services

| Service | When to use |
|---|---|
| **OpenAI / Claude** | Best quality, requires API key (set in Settings) |
| **Google Translate** | Good fallback, requires internet |
| **Argos Translate** | Offline fallback, lower quality |

---

## Tips

- **Decode first, then Translate** — use the "Jump to Translate" button to carry the text over.
- **Save texts** from the Decode page to your library for later use.
- **API keys** are encrypted in the database — they are safe to store.
- The app uses **Neon (PostgreSQL)** as the database — all your data is persistent across sessions.

---

## Feedback & Issues

Report issues at the project repository or contact the developer directly.
""")
