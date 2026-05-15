"""
Personal dictionary – browse, search, edit and delete entries.
6 fields per card: source_word, target_word, word_target_decoded,
                   word_class, example_sentence, explanation.
"""
import streamlit as st
from utils.auth_ui import require_login, render_sidebar
from utils.styles import inject_styles
from domain.vocabulary import VocabularyManager
from services.db_service import DBService

st.set_page_config(page_title="langDec – Dictionary", layout="wide")

require_login()
render_sidebar()
inject_styles()

user_id = st.session_state.user_id
db = DBService()
vocab = VocabularyManager(db)

st.title("Personal Dictionary")

LANGUAGES = {"All": None, "German (de)": "de", "English (en)": "en", "Portuguese (pt)": "pt", "Swedish (sv)": "sv"}

col1, col2, col3 = st.columns(3)
with col1:
    src_label = st.selectbox("Source language", list(LANGUAGES.keys()), key="dict_src")
with col2:
    tgt_label = st.selectbox("Target language", list(LANGUAGES.keys()), key="dict_tgt")
with col3:
    search = st.text_input("Search word", placeholder="e.g. casa")

lang_src = LANGUAGES[src_label]
lang_tgt = LANGUAGES[tgt_label]

words = vocab.get_words(user_id, source_language=lang_src, target_language=lang_tgt, search=search or None)

if not words:
    st.info("No entries yet. Decode a text or add words manually on the Start page.")
else:
    st.markdown(f"**{len(words)} entries**")
    for word in words:
        wid = str(word["user_dictionary_id"])
        decoded_preview = f"  |  decoded: {word['word_target_decoded']}" if word.get("word_target_decoded") else ""
        label = f"{word['source_word']}  →  {word['target_word']}{decoded_preview}  ({word['source_language']} → {word['target_language']})"
        with st.expander(label, expanded=False):
            # Row 1: source translations
            col_a, col_b = st.columns(2)
            with col_a:
                new_target = st.text_input(
                    "Natural translation",
                    value=word["target_word"],
                    key=f"tgt_{wid}",
                    help="Contextual/natural translation",
                )
            with col_b:
                new_decoded = st.text_input(
                    "Decoded translation",
                    value=word.get("word_target_decoded") or "",
                    key=f"dec_{wid}",
                    help="Literal/Birkenbihl translation",
                )

            # Row 2: class + example
            col_c, col_d = st.columns(2)
            with col_c:
                new_class = st.text_input(
                    "Word class",
                    value=word["word_class"] or "",
                    key=f"cls_{wid}",
                )
            with col_d:
                new_example = st.text_input(
                    "Example sentence",
                    value=word["example_sentence"] or "",
                    key=f"ex_{wid}",
                )

            # Row 3: explanation
            new_explanation = st.text_area(
                "Explanation / notes",
                value=word.get("explanation") or "",
                height=60,
                key=f"exp_{wid}",
            )

            st.caption(f"Frequency: {word['frequency']}  |  Created: {str(word['created_at'])[:10]}")

            col_save, col_del = st.columns(2)
            with col_save:
                if st.button("Save", key=f"save_{wid}", type="primary"):
                    vocab.update_word(
                        user_id,
                        wid,
                        target_word=new_target or None,
                        word_target_decoded=new_decoded or None,
                        word_class=new_class or None,
                        example_sentence=new_example or None,
                        explanation=new_explanation or None,
                    )
                    st.success("Saved.")
                    st.rerun()
            with col_del:
                if st.session_state.get(f"confirm_del_word_{wid}"):
                    st.warning("Are you sure?")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("Yes, delete", key=f"del_confirm_{wid}", type="primary"):
                            vocab.delete_word(user_id, wid)
                            st.session_state.pop(f"confirm_del_word_{wid}", None)
                            st.rerun()
                    with c2:
                        if st.button("Cancel", key=f"del_cancel_{wid}"):
                            st.session_state.pop(f"confirm_del_word_{wid}", None)
                            st.rerun()
                else:
                    if st.button("Delete", key=f"del_{wid}"):
                        st.session_state[f"confirm_del_word_{wid}"] = True
                        st.rerun()
