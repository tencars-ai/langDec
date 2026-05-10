"""
Personal dictionary – browse, search, edit and delete entries.
6 fields per card: word_source, word_target, word_target_decoded,
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

words = vocab.get_words(user_id, lang_source=lang_src, lang_target=lang_tgt, search=search or None)

if not words:
    st.info("No entries yet. Decode a text or add words manually on the Start page.")
else:
    st.markdown(f"**{len(words)} entries**")
    for word in words:
        decoded_preview = f"  |  decoded: {word['word_target_decoded']}" if word.get("word_target_decoded") else ""
        label = f"{word['word_source']}  →  {word['word_target']}{decoded_preview}  ({word['lang_source']} → {word['lang_target']})"
        with st.expander(label, expanded=False):
            # Row 1: source translations
            col_a, col_b = st.columns(2)
            with col_a:
                new_target = st.text_input(
                    "Natural translation",
                    value=word["word_target"],
                    key=f"tgt_{word['id']}",
                    help="Contextual/natural translation",
                )
            with col_b:
                new_decoded = st.text_input(
                    "Decoded translation",
                    value=word.get("word_target_decoded") or "",
                    key=f"dec_{word['id']}",
                    help="Literal/Birkenbihl translation",
                )

            # Row 2: class + example
            col_c, col_d = st.columns(2)
            with col_c:
                new_class = st.text_input(
                    "Word class",
                    value=word["word_class"] or "",
                    key=f"cls_{word['id']}",
                )
            with col_d:
                new_example = st.text_input(
                    "Example sentence",
                    value=word["example_sentence"] or "",
                    key=f"ex_{word['id']}",
                )

            # Row 3: explanation
            new_explanation = st.text_area(
                "Explanation / notes",
                value=word.get("explanation") or "",
                height=60,
                key=f"exp_{word['id']}",
            )

            st.caption(f"Frequency: {word['frequency']}  |  First seen: {str(word['first_seen'])[:10]}")

            col_save, col_del = st.columns(2)
            with col_save:
                if st.button("Save", key=f"save_{word['id']}", type="primary"):
                    vocab.update_word(
                        user_id,
                        str(word["id"]),
                        word_target=new_target or None,
                        word_target_decoded=new_decoded or None,
                        word_class=new_class or None,
                        example_sentence=new_example or None,
                        explanation=new_explanation or None,
                    )
                    st.success("Saved.")
                    st.rerun()
            with col_del:
                if st.session_state.get(f"confirm_del_word_{word['id']}"):
                    st.warning("Are you sure?")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("Yes, delete", key=f"del_confirm_{word['id']}", type="primary"):
                            vocab.delete_word(user_id, str(word["id"]))
                            st.session_state.pop(f"confirm_del_word_{word['id']}", None)
                            st.rerun()
                    with c2:
                        if st.button("Cancel", key=f"del_cancel_{word['id']}"):
                            st.session_state.pop(f"confirm_del_word_{word['id']}", None)
                            st.rerun()
                else:
                    if st.button("Delete", key=f"del_{word['id']}"):
                        st.session_state[f"confirm_del_word_{word['id']}"] = True
                        st.rerun()
