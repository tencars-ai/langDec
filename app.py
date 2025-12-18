
import streamlit as st

#import psycopg


# -------------------------------------------------
# 1) Page configuration
# -------------------------------------------------
st.set_page_config(page_title="langDec – Decoder", layout="centered")

LANGUAGES = {
    "German (de)": "de",
    "English (en)": "en",
    "Portuguese (pt)": "pt",
}

# Apply monospace font to all textareas
st.markdown(
    """
    <style>
      textarea {
        font-family: "Courier New", Courier, monospace !important;
        font-size: 14px !important;
        line-height: 1.35 !important;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("langDec – Word-by-Word Decoder")
st.caption("Paste text → select languages → configure → decode")

# -------------------------------------------------
# 2) Helper: line wrapping
# -------------------------------------------------
def apply_line_breaks(text: str, max_chars: int) -> str:
    """
    Inserts line breaks after max_chars characters.
    If max_chars <= 0, the text is returned unchanged.
    """
    if max_chars <= 0:
        return text

    lines = []
    current_line = ""

    for word in text.split(" "):
        if len(current_line) + len(word) + 1 <= max_chars:
            current_line += (" " if current_line else "") + word
        else:
            lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    return "\n".join(lines)

# -------------------------------------------------
# 3) Decoder hook (replace with your real decoder)
# -------------------------------------------------
def decode_text(text: str, source_lang: str, target_lang: str) -> str:
    # Placeholder – plug in your existing decoder here
    return f"[DECODED {source_lang}->{target_lang}]\n\n{text}"

# -------------------------------------------------
# 4) Configuration
# -------------------------------------------------
with st.expander("Decoder configuration", expanded=True):
    max_line_length = st.number_input(
        "Line break after number of characters (0 = disabled)",
        min_value=0,
        max_value=300,
        value=80,
        step=5,
        help="Automatically inserts line breaks to improve readability.",
    )

# -------------------------------------------------
# 5) Language selection and input
# -------------------------------------------------
col_left, col_right = st.columns(2)

with col_left:
    source_label = st.selectbox(
        "Source language",
        list(LANGUAGES.keys()),
        index=1,
    )

with col_right:
    target_label = st.selectbox(
        "Target language",
        list(LANGUAGES.keys()),
        index=0,
    )

source_language = LANGUAGES[source_label]
target_language = LANGUAGES[target_label]

input_text = st.text_area(
    "Input text",
    height=220,
    placeholder="Paste your text here…",
)

if source_language == target_language:
    st.warning("Source and target language are identical.")

decode_clicked = st.button(
    "Decode",
    type="primary",
    use_container_width=True,
)

# -------------------------------------------------
# 6) Output
# -------------------------------------------------
if "decoded_text" not in st.session_state:
    st.session_state.decoded_text = ""

if decode_clicked:
    raw_decoded = decode_text(
        input_text.strip(),
        source_language,
        target_language,
    )

    st.session_state.decoded_text = apply_line_breaks(
        raw_decoded,
        max_line_length,
    )

st.text_area(
    "Decoded text (output)",
    value=st.session_state.decoded_text,
    height=260,
    help="Select and copy the text (Ctrl/Cmd + C).",
)

st.download_button(
    "Download output as .txt",
    data=st.session_state.decoded_text or "",
    file_name=f"decoded_{source_language}_to_{target_language}.txt",
    mime="text/plain",
    use_container_width=True,
    disabled=not bool(st.session_state.decoded_text),
)

