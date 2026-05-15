"""
Vocabulary Trainer – flashcard box system with spaced repetition.
"""
import streamlit as st
from utils.auth_ui import require_login, render_sidebar
from utils.styles import inject_styles
from domain.flashcard import FlashcardBox
from services.db_service import DBService

st.set_page_config(page_title="langDec – Vocab Trainer", layout="wide")

require_login()
render_sidebar()
inject_styles()

user_id = st.session_state.user_id
db = DBService()
flashcard = FlashcardBox(db)

st.title("Vocabulary Trainer")

# --- Progress ---
progress = flashcard.get_progress(user_id)
total = sum(progress.values())
col1, col2, col3 = st.columns(3)
col1.metric("Box 1 (New)", progress[1])
col2.metric("Box 2 (Practiced)", progress[2])
col3.metric("Box 3 (Learned)", progress[3])
st.caption(f"Total cards: {total}")
st.markdown("---")

# --- Session state for current card ---
if "trainer_cards" not in st.session_state:
    st.session_state.trainer_cards = []
if "trainer_index" not in st.session_state:
    st.session_state.trainer_index = 0
if "trainer_revealed" not in st.session_state:
    st.session_state.trainer_revealed = False

if st.button("Load due cards", type="primary"):
    st.session_state.trainer_cards = flashcard.get_due_cards(user_id, limit=20)
    st.session_state.trainer_index = 0
    st.session_state.trainer_revealed = False

cards = st.session_state.trainer_cards
idx = st.session_state.trainer_index

if not cards:
    st.info("No cards due for review. Keep decoding to build your dictionary!")
elif idx >= len(cards):
    st.success(f"Session complete! Reviewed {len(cards)} cards.")
    if st.button("Start again"):
        st.session_state.trainer_cards = []
        st.session_state.trainer_index = 0
        st.session_state.trainer_revealed = False
        st.rerun()
else:
    card = cards[idx]
    st.markdown(f"**Card {idx + 1} / {len(cards)}**  —  Box {card['box_number']}")
    st.markdown("---")

    st.markdown(f"### {card['source_word']}")
    st.caption(f"{card['source_language']} → {card['target_language']}")

    if not st.session_state.trainer_revealed:
        if st.button("Reveal answer", type="primary", use_container_width=True):
            st.session_state.trainer_revealed = True
            st.rerun()
    else:
        st.markdown(f"**Natural:** {card['target_word']}")
        if card.get("word_target_decoded"):
            st.markdown(f"**Decoded:** {card['word_target_decoded']}")
        if card.get("word_class"):
            st.caption(f"Word class: {card['word_class']}")
        if card.get("example_sentence"):
            st.caption(f"Example: {card['example_sentence']}")
        if card.get("explanation"):
            st.caption(f"Note: {card['explanation']}")

        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Correct", type="primary", use_container_width=True):
                flashcard.mark_correct(user_id, str(card["vocab_card_id"]))
                st.session_state.trainer_index += 1
                st.session_state.trainer_revealed = False
                st.rerun()
        with c2:
            if st.button("Incorrect", use_container_width=True):
                flashcard.mark_incorrect(user_id, str(card["vocab_card_id"]))
                st.session_state.trainer_index += 1
                st.session_state.trainer_revealed = False
                st.rerun()
