"""
Translate page – natural/contextual translation only.
"""
import streamlit as st

from utils.auth_ui import render_sidebar
from domain.translator import Translator
from services.translation_service import GoogleDeepTranslatorService, ArgosTranslateService

st.set_page_config(page_title="langDec – Translate", layout="centered")

if "user_id" not in st.session_state:
    st.warning("Please log in first.")
    st.stop()

render_sidebar()

LANGUAGES = {
    "German (de)": "de",
    "English (en)": "en",
    "Portuguese (pt)": "pt",
}

AVAILABLE_SERVICES = {
    "Google Translate": GoogleDeepTranslatorService(),
    "Argos Translate": ArgosTranslateService(),
}
_llm = st.session_state.get("llm_service")
if _llm:
    AVAILABLE_SERVICES[_llm.name] = _llm

st.markdown(
    """
    <style>
      h1 { font-size: 1.8rem !important; margin-top: 0.5rem !important; margin-bottom: 0.3rem !important; }
      textarea { font-family: "Courier New", Courier, monospace !important; font-size: 14px !important; line-height: 1.35 !important; }
      button[kind="primary"] { background-color: #007bff !important; border-color: #007bff !important; }
      button[kind="primary"]:hover { background-color: #0056b3 !important; border-color: #004085 !important; }
      textarea[aria-label="Translated text (natural translation)"] { background-color: #d1ecf1 !important; color: black !important; }
      .stDownloadButton > button { background-color: white !important; border: 1px solid #cccccc !important; color: black !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

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
btn_col1, btn_col2 = st.columns(2)
with btn_col1:
    translate_clicked = st.button("Translate", type="primary", use_container_width=True)
with btn_col2:
    if st.button("← Jump to Decode", use_container_width=True):
        st.session_state.transfer_source_label = source_label
        st.session_state.transfer_target_label = target_label
        st.switch_page("pages/1_Decode.py")

# --- Configuration ---
with st.expander("Configuration", expanded=False):
    selected_service_name = st.radio("Translation Service", options=list(AVAILABLE_SERVICES.keys()), index=0, horizontal=True)
    _translation_service = AVAILABLE_SERVICES[selected_service_name]
    _translator = Translator(_translation_service)

# --- Translate logic ---
if translate_clicked:
    try:
        with st.spinner("Translating..."):
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
st.text_area("Translated text (natural translation)", value=st.session_state.translated_text, height=220, help="Select and copy (Ctrl/Cmd + C).")

# --- Download ---
st.download_button(
    "Download translation as .txt",
    data=st.session_state.translated_text or "",
    file_name=f"translated_{source_language}_to_{target_language}.txt",
    mime="text/plain",
    use_container_width=True,
    disabled=not bool(st.session_state.translated_text),
)
