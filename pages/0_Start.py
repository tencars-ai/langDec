"""
Start page – combined Decode & Translate in one step, single output field.
"""
import streamlit as st
from PIL import Image
import io
import fitz

from utils.auth_ui import render_sidebar
from utils.services_ui import get_decode_service, get_translate_service, get_max_line_length, get_ocr_threshold
from domain.decoder import WordByWordDecoder
from domain.translator import Translator
from domain.vocabulary import VocabularyManager
from services.ocr_service import EasyOCRService
from services.db_service import DBService

st.set_page_config(page_title="langDec – Start", layout="centered")

if "user_id" not in st.session_state:
    st.warning("Please log in first.")
    st.stop()

render_sidebar()

LANGUAGES = {
    "German (de)": "de",
    "English (en)": "en",
    "Portuguese (pt)": "pt",
}

st.markdown(
    """
    <style>
      h1 { font-size: 1.8rem !important; margin-top: 0.5rem !important; margin-bottom: 0.3rem !important; }
      textarea { font-family: "Courier New", Courier, monospace !important; font-size: 14px !important; line-height: 1.35 !important; }
      button[kind="primary"] { background-color: #007bff !important; border-color: #007bff !important; color: white !important; }
      button[kind="primary"]:hover { background-color: #0056b3 !important; border-color: #004085 !important; }
      .stDownloadButton > button { background-color: white !important; border: 1px solid #cccccc !important; color: black !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Start")

_ocr_service = EasyOCRService()

col_left, col_right = st.columns(2)
with col_left:
    st.markdown("**Source Language**")
    source_label = st.selectbox("Source Language", list(LANGUAGES.keys()), index=2, label_visibility="collapsed")
with col_right:
    st.markdown("**Target Language (Mother Tongue)**")
    target_label = st.selectbox("Target Language (Mother Tongue)", list(LANGUAGES.keys()), index=0, label_visibility="collapsed")

source_language = LANGUAGES[source_label]
target_language = LANGUAGES[target_label]

for key in ("input_text", "start_output"):
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
                extracted = _ocr_service.extract_text(image, lang=EasyOCRService.get_language_code(source_label), line_height_threshold=ocr_line_height_threshold)
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

decode_translate_clicked = st.button("Decode & Translate", type="primary", use_container_width=True)

_decoder = WordByWordDecoder(get_decode_service())
_translator = Translator(get_translate_service())
ocr_line_height_threshold = get_ocr_threshold()
max_line_length = get_max_line_length()

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

# --- Decode & Translate logic ---
if decode_translate_clicked:
    if not input_text.strip():
        st.warning("Please enter some text first.")
    else:
        try:
            decoded_text = ""
            translated_text = ""
            with st.spinner("Decoding..."):
                decoded_text = _decoder.decode(
                    text=input_text.strip(),
                    source_lang=source_language,
                    target_lang=target_language,
                    max_line_length=max_line_length,
                )
            _save_decoded_words(decoded_text, source_language, target_language)
            with st.spinner("Translating..."):
                translated_text = _translator.translate(
                    text=input_text.strip(),
                    source_lang=source_language,
                    target_lang=target_language,
                )
            st.session_state.start_output = (
                "=== DECODING ===\n\n"
                + decoded_text
                + "\n\n=== TRANSLATION ===\n\n"
                + translated_text
            )
            st.success("Done!")
        except Exception as e:
            st.error(f"Error: {e}")
            st.session_state.start_output = ""

# --- Combined output ---
st.text_area(
    "Output",
    value=st.session_state.start_output,
    height=400,
    label_visibility="collapsed",
    help="Decoded text followed by natural translation.",
)

# --- Save to text library ---
if st.session_state.start_output:
    with st.expander("Save to text library", expanded=False):
        db = DBService()
        title = st.text_input("Title", value="Untitled text", key="save_title")

        folders = db.execute(
            "SELECT id, name FROM folders WHERE user_id = %s ORDER BY name",
            (st.session_state.user_id,),
        )
        folder_options = {"(No folder)": None, **{f["name"]: str(f["id"]) for f in folders}}
        folder_label = st.selectbox("Folder", list(folder_options.keys()), key="save_folder")

        if st.button("Save text", type="primary", key="save_text_btn"):
            if title.strip():
                try:
                    db.execute_returning(
                        "INSERT INTO texts (user_id, folder_id, title, content, source_language) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                        (st.session_state.user_id, folder_options[folder_label], title.strip(), input_text.strip(), source_language),
                    )
                    st.success(f"Saved as '{title}'.")
                except Exception as e:
                    st.error(f"Failed: {e}")

# --- Add word/phrase to vocabulary ---
with st.expander("Add word or phrase to vocabulary", expanded=False):
    st.caption("Copy a word or phrase from the output above and paste it here.")

    vocab_word = st.text_input("Word / phrase (source language)", key="vocab_word_input")

    col_t1, col_t2 = st.columns(2)
    with col_t1:
        vocab_translation = st.text_input("Natural translation", key="vocab_trans_input",
                                          help="Contextual/natural translation in your mother tongue")
    with col_t2:
        vocab_decoded = st.text_input("Decoded translation", key="vocab_decoded_input",
                                      help="Literal word-for-word translation (Birkenbihl)")

    if st.button("Auto-translate both", key="vocab_autotrans_btn"):
        if vocab_word.strip():
            try:
                natural = get_translate_service().translate_word(vocab_word.strip(), source_language, target_language)
                decoded = get_decode_service().translate_word(vocab_word.strip(), source_language, target_language)
                st.session_state.vocab_trans_input = natural
                st.session_state.vocab_decoded_input = decoded
                st.rerun()
            except Exception as e:
                st.error(f"Auto-translate failed: {e}")

    col_w1, col_w2 = st.columns(2)
    with col_w1:
        word_class_options = ["", "noun", "verb", "adjective", "adverb", "phrase", "other"]
        word_class = st.selectbox("Word class", word_class_options, key="vocab_class_input")
    with col_w2:
        example = st.text_input("Example sentence", key="vocab_example_input")

    explanation = st.text_area("Explanation / notes", height=60, key="vocab_explanation_input")

    if st.button("Save to dictionary", type="primary", key="vocab_save_btn"):
        if vocab_word.strip() and vocab_translation.strip():
            try:
                from domain.vocabulary import VocabularyManager
                VocabularyManager(DBService()).add_word(
                    user_id=st.session_state.user_id,
                    word_source=vocab_word.strip(),
                    word_target=vocab_translation.strip(),
                    word_target_decoded=vocab_decoded.strip() or None,
                    lang_source=source_language,
                    lang_target=target_language,
                    word_class=word_class or None,
                    example_sentence=example.strip() or None,
                    explanation=explanation.strip() or None,
                )
                st.success(f"'{vocab_word}' saved to dictionary.")
            except Exception as e:
                st.error(f"Failed: {e}")
        else:
            st.warning("Please enter at least the word and natural translation.")

# --- Download ---
st.download_button(
    "Download output as .txt",
    data=st.session_state.start_output or "",
    file_name=f"langdec_{source_language}_to_{target_language}.txt",
    mime="text/plain",
    use_container_width=True,
    disabled=not bool(st.session_state.start_output),
)
