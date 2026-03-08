"""
Generate page – LLM text/dialogue generation, save to text library.
"""
import streamlit as st
from utils.auth_ui import render_sidebar
from services.db_service import DBService

st.set_page_config(page_title="langDec – Generate", layout="centered")

if "user_id" not in st.session_state:
    st.warning("Please log in first.")
    st.stop()

render_sidebar()

user_id = st.session_state.user_id
llm = st.session_state.get("llm_service")

st.title("Generate Texts")

if llm is None:
    st.warning("No LLM API key configured. Go to Settings to add your OpenAI or Anthropic key.")
    st.stop()

LANGUAGES = {"German (de)": "de", "English (en)": "en", "Portuguese (pt)": "pt"}
DIFFICULTIES = ["beginner", "intermediate", "advanced"]
FORMATS = ["short text", "dialogue", "story", "news article", "poem"]

col1, col2, col3 = st.columns(3)
with col1:
    lang_label = st.selectbox("Language", list(LANGUAGES.keys()))
with col2:
    difficulty = st.selectbox("Difficulty", DIFFICULTIES, index=1)
with col3:
    fmt = st.selectbox("Format", FORMATS)

topic = st.text_input("Topic / prompt", placeholder="e.g. 'ordering food at a restaurant'")

generate_btn = st.button("Generate", type="primary", use_container_width=True)

if "generated_text" not in st.session_state:
    st.session_state.generated_text = ""

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
    st.subheader("Generated text")
    st.text_area("Result", value=st.session_state.generated_text, height=300, label_visibility="collapsed")

    with st.expander("Save to text library", expanded=False):
        db = DBService()
        title = st.text_input("Title", value=f"Generated: {topic[:40]}", key="gen_save_title")
        lang_save = LANGUAGES[lang_label]
        if st.button("Save", type="primary"):
            if title.strip():
                db.execute_write(
                    "INSERT INTO texts (user_id, title, content, source_language) VALUES (%s, %s, %s, %s)",
                    (user_id, title.strip(), st.session_state.generated_text, lang_save),
                )
                st.success(f"Saved as '{title}'.")
