"""
Personal dictionary – browse, search, edit and delete entries.
"""
import streamlit as st
from utils.auth_ui import render_sidebar
from domain.vocabulary import VocabularyManager
from services.db_service import DBService

st.set_page_config(page_title="langDec – Dictionary", layout="centered")

if "user_id" not in st.session_state:
    st.warning("Please log in first.")
    st.stop()

render_sidebar()

user_id = st.session_state.user_id
db = DBService()
vocab = VocabularyManager(db)

st.title("Personal Dictionary")

LANGUAGES = {"All": None, "German (de)": "de", "English (en)": "en", "Portuguese (pt)": "pt"}

col1, col2, col3 = st.columns(3)
with col1:
    src_label = st.selectbox("Source language", list(LANGUAGES.keys()), key="dict_src")
with col2:
    tgt_label = st.selectbox("Target language", list(LANGUAGES.keys()), key="dict_tgt")
with col3:
    search = st.text_input("Search word", placeholder="e.g. casa")

lang_src = LANGUAGES[src_label]
lang_tgt = LANGUAGES[tgt_label]

words = vocab.get_words(user_id, lang_source=lang_src, lang_target=lang_tgt, search=search or None)

if not words:
    st.info("No entries yet. Decode a text to auto-populate your dictionary.")
else:
    st.markdown(f"**{len(words)} entries**")
    for word in words:
        with st.expander(f"{word['word_source']}  →  {word['word_target']}  ({word['lang_source']} → {word['lang_target']})", expanded=False):
            col_a, col_b = st.columns(2)
            with col_a:
                new_target = st.text_input("Translation", value=word["word_target"], key=f"tgt_{word['id']}")
                new_class = st.text_input("Word class", value=word["word_class"] or "", key=f"cls_{word['id']}")
            with col_b:
                new_example = st.text_area("Example sentence", value=word["example_sentence"] or "", height=80, key=f"ex_{word['id']}")
                st.caption(f"Frequency: {word['frequency']}  |  First seen: {str(word['first_seen'])[:10]}")

            col_save, col_del = st.columns(2)
            with col_save:
                if st.button("Save", key=f"save_{word['id']}"):
                    vocab.update_word(
                        user_id,
                        str(word["id"]),
                        word_target=new_target or None,
                        word_class=new_class or None,
                        example_sentence=new_example or None,
                    )
                    st.success("Saved.")
                    st.rerun()
            with col_del:
                if st.button("Delete", key=f"del_{word['id']}"):
                    vocab.delete_word(user_id, str(word["id"]))
                    st.rerun()
