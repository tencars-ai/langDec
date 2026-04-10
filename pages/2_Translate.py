"""
Translate page – natural/contextual translation only.
"""
import streamlit as st

from utils.auth_ui import require_login, render_sidebar
from utils.services_ui import get_translate_service
from utils.styles import inject_styles, inject_translated_style
from utils.ui import LANGUAGES
from domain.translator import Translator

st.set_page_config(page_title="langDec – Translate", layout="wide")

require_login()
render_sidebar()
inject_styles()
inject_translated_style()

st.title("Translate")

# --- Pick up text transferred from Decode page ---
if "transfer_source_label" in st.session_state:
    _transfer_src = st.session_state.pop("transfer_source_label")
    _transfer_tgt = st.session_state.pop("transfer_target_label", None)
else:
    _transfer_src = None
    _transfer_tgt = None

col_left, col_right = st.columns(2)
with col_left:
    st.markdown("**Source Language**")
    src_index = list(LANGUAGES.keys()).index(_transfer_src) if _transfer_src in LANGUAGES else 2
    source_label = st.selectbox("Source Language", list(LANGUAGES.keys()), index=src_index, label_visibility="collapsed")
with col_right:
    st.markdown("**Target Language (Mother Tongue)**")
    tgt_index = list(LANGUAGES.keys()).index(_transfer_tgt) if _transfer_tgt in LANGUAGES else 0
    target_label = st.selectbox("Target Language (Mother Tongue)", list(LANGUAGES.keys()), index=tgt_index, label_visibility="collapsed")

source_language = LANGUAGES[source_label]
target_language = LANGUAGES[target_label]

if "input_text" not in st.session_state:
    st.session_state.input_text = ""
if "translated_text" not in st.session_state:
    st.session_state.translated_text = ""

st.markdown("**Input Text**")
input_text = st.text_area(
    "Input Text",
    height=220,
    placeholder="Paste your text here…",
    key="input_text",
    label_visibility="collapsed",
)

if source_language == target_language:
    st.warning("Source and target language are identical.")

# --- Buttons ---
btn_col1, btn_col2 = st.columns([3, 1])
with btn_col1:
    translate_clicked = st.button("Translate", type="primary", use_container_width=True)
with btn_col2:
    if st.button("← Decode"):
        st.session_state.transfer_source_label = source_label
        st.session_state.transfer_target_label = target_label
        st.switch_page("pages/1_Decode.py")

_translator = Translator(get_translate_service())

# --- Translate logic ---
if translate_clicked:
    try:
        with st.spinner("Translating…"):
            st.session_state.translated_text = _translator.translate(
                text=input_text.strip(),
                source_lang=source_language,
                target_lang=target_language,
            )
        st.success("Translation completed!")
    except Exception as e:
        st.error(f"Error: {e}")
        st.session_state.translated_text = ""

# --- Output ---
if st.session_state.translated_text:
    col_title, col_toggle = st.columns([2, 1])
    with col_title:
        st.markdown("#### 🌐 Translation (natural)")
    with col_toggle:
        trans_view = st.radio(
            "View",
            ["Edit Text", "Read Markdown"],
            horizontal=True,
            label_visibility="collapsed",
        )
    if trans_view == "Read Markdown":
        st.markdown(st.session_state.translated_text)
    else:
        st.text_area(
            "Translated text (natural translation)",
            value=st.session_state.translated_text,
            height=220,
            label_visibility="collapsed",
            help="Select and copy (Ctrl/Cmd + C).",
        )

# --- Download ---
st.download_button(
    "Download translation as .txt",
    data=st.session_state.translated_text or "",
    file_name=f"translated_{source_language}_to_{target_language}.txt",
    mime="text/plain",
    use_container_width=True,
    disabled=not bool(st.session_state.translated_text),
)
