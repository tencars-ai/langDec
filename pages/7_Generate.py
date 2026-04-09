"""
Generate page – LLM text/dialogue generation, save to text library.
"""
import streamlit as st
from utils.auth_ui import render_sidebar
from utils.styles import inject_styles
from utils.ui import LANGUAGES, save_to_library

st.set_page_config(page_title="langDec – Generate", layout="wide")

if "user_id" not in st.session_state:
    st.warning("Please log in first.")
    st.stop()

render_sidebar()
inject_styles()

user_id = st.session_state.user_id
llm = st.session_state.get("llm_service")

st.title("Generate Texts")

if llm is None:
    st.warning("No LLM API key configured. Go to Settings to add your OpenAI or Anthropic key.")
    st.stop()
DIFFICULTIES = ["beginner", "intermediate", "advanced"]
FORMATS = ["short text", "dialogue", "story", "news article", "poem"]

col1, col2, col3 = st.columns(3)
with col1:
    lang_label = st.selectbox("Language", list(LANGUAGES.keys()))
with col2:
    difficulty = st.selectbox("Difficulty", DIFFICULTIES, index=1)
with col3:
    fmt = st.selectbox("Format", FORMATS)

if "gen_topic" not in st.session_state:
    st.session_state.gen_topic = ""
if "generated_text" not in st.session_state:
    st.session_state.generated_text = ""

topic = st.text_input("Topic / prompt", placeholder="e.g. 'ordering food at a restaurant'", key="gen_topic")

if generate_btn:
    if not topic.strip():
        st.warning("Please enter a topic.")
    else:
        language = LANGUAGES[lang_label]
        prompt = f"Write a {fmt} about: {topic}"
        with st.spinner("Generating…"):
            try:
                result = llm.generate_text(prompt=prompt, language=language, difficulty=difficulty)
                st.session_state.generated_text = result
            except Exception as e:
                st.error(f"Generation failed: {e}")

if st.session_state.generated_text:
    st.markdown("---")
    col_title, col_toggle = st.columns([2, 1])
    with col_title:
        st.subheader("Generated text")
    with col_toggle:
        view_mode = st.radio(
            "View",
            ["Edit Text", "Read Markdown"],
            horizontal=True,
            label_visibility="collapsed",
        )

    if view_mode == "Read Markdown":
        st.markdown(st.session_state.generated_text)
    else:
        st.text_area("Result", value=st.session_state.generated_text, height=300, label_visibility="collapsed")

    save_to_library(
        st.session_state.generated_text,
        LANGUAGES[lang_label],
        user_id,
        default_title=f"Generated: {topic[:40]}",
        key_prefix="gen_save",
    )
