"""
Decode page – word-by-word Birkenbihl decoding only.
"""
import streamlit as st
from PIL import Image
import io
import fitz

from utils.auth_ui import render_sidebar
from domain.decoder import WordByWordDecoder
from domain.vocabulary import VocabularyManager
from services.translation_service import GoogleDeepTranslatorService, ArgosTranslateService
from services.ocr_service import EasyOCRService
from services.db_service import DBService

st.set_page_config(page_title="langDec – Decode", layout="centered")

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
      button[kind="primary"] { background-color: #28a745 !important; border-color: #28a745 !important; }
      button[kind="primary"]:hover { background-color: #218838 !important; border-color: #1e7e34 !important; }
      textarea[aria-label="Decoded text (word-by-word)"] { background-color: #d4edda !important; color: black !important; }
      .stDownloadButton > button { background-color: white !important; border: 1px solid #cccccc !important; color: black !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Decode")

_ocr_service = EasyOCRService()
ocr_line_height_threshold = 30
max_line_length = 65

col_left, col_right = st.columns(2)
with col_left:
    st.markdown("**Source Language**")
    source_label = st.selectbox("Source Language", list(LANGUAGES.keys()), index=2, label_visibility="collapsed")
with col_right:
    st.markdown("**Target Language (Mother Tongue)**")
    target_label = st.selectbox("Target Language (Mother Tongue)", list(LANGUAGES.keys()), index=0, label_visibility="collapsed")

source_language = LANGUAGES[source_label]
target_language = LANGUAGES[target_label]

for key in ("input_text", "decoded_text"):
    if key not in st.session_state:
        st.session_state[key] = ""
for key in ("show_camera", "show_browse"):
    if key not in st.session_state:
        st.session_state[key] = False

st.markdown("**Input Text**")
ocr_col1, ocr_col2 = st.columns(2)
with ocr_col1:
    if st.button("📷 Take Photo (OCR)", use_container_width=True):
        st.session_state.show_camera = not st.session_state.show_camera
        st.session_state.show_browse = False
with ocr_col2:
    if st.button("📁 Browse Files (OCR)", use_container_width=True):
        st.session_state.show_browse = not st.session_state.show_browse
        st.session_state.show_camera = False

if st.session_state.show_camera:
    camera_photo = st.camera_input("Take a photo")
    if camera_photo:
        image = Image.open(camera_photo)
        st.image(image, caption="Image to process", use_container_width=True)
        if st.button("🔍 Extract Text (OCR)", type="secondary", use_container_width=True, key="ocr_camera"):
            with st.spinner("Extracting text..."):
                ocr_lang = EasyOCRService.get_language_code(source_label)
                extracted = _ocr_service.extract_text(image, lang=ocr_lang, line_height_threshold=ocr_line_height_threshold)
                st.session_state.input_text += ("\n" if st.session_state.input_text.strip() else "") + extracted
                st.session_state.show_camera = False
                st.rerun()
    st.markdown("---")

if st.session_state.show_browse:
    uploaded_file = st.file_uploader("Browse and select an image or PDF", type=["png", "jpg", "jpeg", "tiff", "bmp", "pdf"])
    if uploaded_file:
        if uploaded_file.name.lower().endswith(".pdf"):
            pdf_bytes = uploaded_file.read()
            pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            page_count = len(pdf_doc)
            pix = pdf_doc[0].get_pixmap(matrix=fitz.Matrix(2, 2))
            st.image(Image.open(io.BytesIO(pix.tobytes("png"))), caption=f"PDF Preview – Page 1 of {page_count}", use_container_width=True)
            pdf_doc.close()
            if st.button("🔍 Extract Text from PDF (OCR)", type="secondary", use_container_width=True, key="ocr_pdf"):
                pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                all_text = []
                for i in range(page_count):
                    pix = pdf_doc[i].get_pixmap(matrix=fitz.Matrix(2, 2))
                    with st.spinner(f"Page {i+1}/{page_count}..."):
                        all_text.append(_ocr_service.extract_text(Image.open(io.BytesIO(pix.tobytes("png"))), lang=EasyOCRService.get_language_code(source_label), line_height_threshold=ocr_line_height_threshold))
                pdf_doc.close()
                combined = "\n\n".join(all_text)
                st.session_state.input_text += ("\n" if st.session_state.input_text.strip() else "") + combined
                st.session_state.show_browse = False
                st.rerun()
        else:
            image = Image.open(uploaded_file)
            st.image(image, caption="Image to process", use_container_width=True)
            if st.button("🔍 Extract Text (OCR)", type="secondary", use_container_width=True, key="ocr_browse"):
                with st.spinner("Extracting text..."):
                    extracted = _ocr_service.extract_text(image, lang=EasyOCRService.get_language_code(source_label), line_height_threshold=ocr_line_height_threshold)
                    st.session_state.input_text += ("\n" if st.session_state.input_text.strip() else "") + extracted
                    st.session_state.show_browse = False
                    st.rerun()
    st.markdown("---")

input_text = st.text_area("Input Text", height=220, placeholder="Paste your text here or use OCR above…", key="input_text", label_visibility="collapsed")

if source_language == target_language:
    st.warning("Source and target language are identical.")

# --- Buttons ---
btn_col1, btn_col2 = st.columns(2)
with btn_col1:
    decode_clicked = st.button("Decode", type="primary", use_container_width=True)
with btn_col2:
    if st.button("Jump to Translate →", use_container_width=True):
        st.session_state.transfer_source_label = source_label
        st.session_state.transfer_target_label = target_label
        st.switch_page("pages/2_Translate.py")

# --- Configuration ---
with st.expander("Configuration", expanded=False):
    selected_service_name = st.radio("Translation Service", options=list(AVAILABLE_SERVICES.keys()), index=0, horizontal=True)
    _translation_service = AVAILABLE_SERVICES[selected_service_name]
    _decoder = WordByWordDecoder(_translation_service)

    st.markdown("#### OCR")
    ocr_line_height_threshold = st.number_input("Line height threshold (pixels)", min_value=10, max_value=100, value=30, step=5)
    st.markdown("#### Decoder Output")
    max_line_length = st.number_input("Line break after number of characters (0 = disabled)", min_value=0, max_value=300, value=65, step=5)

# --- Auto-save decoded words ---
def _save_decoded_words(decoded: str, src_lang: str, tgt_lang: str) -> None:
    try:
        vocab = VocabularyManager(DBService())
        for token in decoded.split():
            if "/" in token:
                parts = token.split("/", 1)
                if len(parts) == 2:
                    w_src, w_tgt = parts[0].strip(), parts[1].strip()
                    if w_src and w_tgt:
                        vocab.add_word(st.session_state.user_id, w_src, w_tgt, src_lang, tgt_lang)
    except Exception:
        pass

# --- Decode logic ---
if decode_clicked:
    try:
        with st.spinner("Decoding..."):
            st.session_state.decoded_text = _decoder.decode(
                text=input_text.strip(),
                source_lang=source_language,
                target_lang=target_language,
                max_line_length=max_line_length,
            )
        _save_decoded_words(st.session_state.decoded_text, source_language, target_language)
        st.success("Decoding completed!")
    except Exception as e:
        st.error(f"Error: {e}")
        st.session_state.decoded_text = ""

# --- Output ---
st.text_area("Decoded text (word-by-word)", value=st.session_state.decoded_text, height=220, help="Select and copy (Ctrl/Cmd + C).")

# --- Save to text library ---
if st.session_state.decoded_text:
    with st.expander("Save to text library", expanded=False):
        title = st.text_input("Title", value="Untitled text")
        if st.button("Save text", type="primary"):
            if title.strip():
                try:
                    DBService().execute_returning(
                        "INSERT INTO texts (user_id, title, content, source_language) VALUES (%s, %s, %s, %s) RETURNING id",
                        (st.session_state.user_id, title.strip(), input_text.strip(), source_language),
                    )
                    st.success(f"Saved as '{title}'.")
                except Exception as e:
                    st.error(f"Failed: {e}")

# --- Download ---
st.download_button(
    "Download decoded text as .txt",
    data=st.session_state.decoded_text or "",
    file_name=f"decoded_{source_language}_to_{target_language}.txt",
    mime="text/plain",
    use_container_width=True,
    disabled=not bool(st.session_state.decoded_text),
)
