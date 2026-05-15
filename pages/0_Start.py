"""
Start page – combined Decode & Translate in one step, single output field.
"""
import concurrent.futures
import streamlit as st
from PIL import Image
import io
import fitz

from utils.auth_ui import require_login, render_sidebar
from utils.services_ui import get_decode_service, get_translate_service, get_max_line_length, get_ocr_threshold
from utils.styles import inject_styles, inject_spellcheck_off
from utils.ui import LANGUAGES, save_to_library
from domain.decoder import WordByWordDecoder
from domain.translator import Translator
# from domain.vocabulary import VocabularyManager  # MVP-01: dictionary disabled
from services.ocr_service import EasyOCRService
from services.tts_service import GTTSService
# from services.db_service import DBService  # MVP-01: only used by dictionary code

st.set_page_config(page_title="langDec – Decode Text", layout="wide")

require_login()
render_sidebar()
inject_styles()
inject_spellcheck_off()

st.title("Decode Text")

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

for key in ("input_text", "start_output", "start_decoded", "start_translated", "start_comments", "start_debug"):
    if key not in st.session_state:
        st.session_state[key] = ""
if "start_audio" not in st.session_state:
    st.session_state.start_audio = None  # bytes or None
if "start_errors" not in st.session_state:
    st.session_state.start_errors = []  # list[str]
for key in ("show_camera", "show_browse"):
    if key not in st.session_state:
        st.session_state[key] = False

_decoder = WordByWordDecoder(
    get_decode_service(),
    debug=st.session_state.get("debug_mode", False),
)
_translator = Translator(get_translate_service())
_tts = GTTSService()
ocr_line_height_threshold = get_ocr_threshold()
max_line_length = get_max_line_length()

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

# --- Auto-save decoded words (MVP-01: dictionary disabled) ---
# def _save_decoded_words(decoded: str, src_lang: str, tgt_lang: str) -> None:
#     try:
#         vocab = VocabularyManager(DBService())
#         for block in decoded.split("\n\n"):
#             lines = [l for l in block.splitlines() if l.strip()]
#             if len(lines) < 2:
#                 continue
#             src_words = lines[0].split()
#             tgt_words = lines[1].split()
#             for w_src, w_tgt in zip(src_words, tgt_words):
#                 w_src, w_tgt = w_src.strip(), w_tgt.strip()
#                 if w_src and w_tgt:
#                     vocab.add_word(st.session_state.user_id, w_src, w_tgt, src_lang, tgt_lang)
#     except Exception:
#         pass

# --- Output slots: populated live during processing or from session state on re-renders ---
# Order: Translation → Audio (its own component) → Decoding → Notes → Debug → Errors.
_translated_slot = st.empty()
_audio_slot = st.empty()
_decoded_slot = st.empty()
_notes_slot = st.empty()
_debug_slot = st.empty()
_error_slot = st.empty()


def _md_preserve_breaks(text: str) -> str:
    """Make single \\n render as a line break in st.markdown.

    Markdown collapses a single newline into a space. Two trailing spaces
    before \\n is the official hard-break syntax. \\n\\n still works as a
    paragraph break because the trailing spaces sit on an otherwise blank line.
    """
    return (text or "").replace("\n", "  \n")


def _render_audio_section(slot, audio_bytes) -> None:
    """Audio is its own UX component, rendered as soon as TTS is ready."""
    if not audio_bytes:
        return
    with slot.container():
        st.markdown("#### 🔊 Audio")
        st.audio(audio_bytes, format="audio/mp3")


def _render_decoded_section(slot, decoded: str, key: str) -> None:
    """Render the Decoding section (text only — audio is separate)."""
    if not decoded:
        return
    with slot.container():
        st.markdown("#### 🔤 Decoding (word-by-word)")
        st.text_area(
            "Decoded",
            value=decoded,
            height=200,
            key=key,
            label_visibility="collapsed",
            help="Monospace alignment — original word above, literal translation below.",
        )


def _render_debug_section(slot, debug_info: str) -> None:
    if not debug_info:
        return
    with slot.container():
        with st.expander("🔍 Debug: raw LLM payloads per chunk", expanded=False):
            st.code(debug_info, language="json")


def _render_error_section(slot, errors: list[str]) -> None:
    if not errors:
        return
    with slot.container():
        for msg in errors:
            st.error(msg)

# --- Decode & Translate & Audio logic ---
if decode_translate_clicked:
    if not input_text.strip():
        st.warning("Please enter some text first.")
    else:
        # Reset transient outputs for this click so the previous run does not leak in.
        st.session_state.start_decoded = ""
        st.session_state.start_translated = ""
        st.session_state.start_comments = ""
        st.session_state.start_debug = ""
        st.session_state.start_audio = None
        st.session_state.start_errors = []

        with st.status("Processing…", expanded=True) as _status:
            _stripped = input_text.strip()

            # Translate, Audio, and Decode all run in parallel — they no longer
            # depend on each other (the decoder no longer consumes the natural
            # translation as context).
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as _executor:
                _future_translate = _executor.submit(
                    _translator.translate, _stripped, source_language, target_language,
                )
                _future_audio = _executor.submit(
                    _tts.synthesize, _stripped, source_language,
                )
                _future_decode = _executor.submit(
                    _decoder.decode,
                    _stripped, source_language, target_language, max_line_length,
                )

                _futures = [_future_translate, _future_audio, _future_decode]
                for _future in concurrent.futures.as_completed(_futures):
                    if _future is _future_translate:
                        try:
                            _t = _future.result()
                            st.session_state.start_translated = _t
                            st.write("✅ Translation done")
                            with _translated_slot.container():
                                st.markdown("#### 🌐 Translation (natural)")
                                st.markdown(_md_preserve_breaks(_t))
                        except Exception as _e:
                            err = f"Translation failed: {type(_e).__name__}: {_e}"
                            st.write(f"❌ {err}")
                            st.session_state.start_errors.append(err)

                    elif _future is _future_audio:
                        try:
                            st.session_state.start_audio = _future.result()
                            st.write("✅ Audio ready")
                            _render_audio_section(_audio_slot, st.session_state.start_audio)
                        except Exception as _e:
                            err = f"Audio (TTS) failed: {type(_e).__name__}: {_e}"
                            st.write(f"❌ {err}")
                            st.session_state.start_errors.append(err)

                    else:  # decode
                        try:
                            _r = _future.result()
                            st.session_state.start_decoded = _r.aligned_text
                            st.session_state.start_comments = _r.comments
                            st.session_state.start_debug = _r.debug_info
                            st.write("✅ Decoding done")
                            if _r.aligned_text.strip():
                                _render_decoded_section(
                                    _decoded_slot, _r.aligned_text, key="decoded_live",
                                )
                            else:
                                err = (
                                    "Decoder produced no output. "
                                    "See Hints/Debug below for why."
                                )
                                st.write(f"⚠️ {err}")
                                st.session_state.start_errors.append(err)

                            if _r.comments:
                                with _notes_slot.container():
                                    st.markdown("#### 📝 Hints")
                                    st.info(_r.comments)
                            _render_debug_section(_debug_slot, _r.debug_info)
                        except Exception as _e:
                            err = f"Decoding failed: {type(_e).__name__}: {_e}"
                            st.write(f"❌ {err}")
                            st.session_state.start_errors.append(err)

            _status.update(label="Done!", state="complete")

        st.session_state.start_output = (
            "=== DECODING ===\n\n" + st.session_state.start_decoded
            + "\n\n=== TRANSLATION ===\n\n" + st.session_state.start_translated
            + ("\n\n=== HINTS ===\n\n" + st.session_state.start_comments
               if st.session_state.start_comments else "")
        )

        # Show errors at the bottom (above Save) so they survive into the
        # re-render path below as well.
        _render_error_section(_error_slot, st.session_state.start_errors)

# --- Populate output slots on page re-renders (NOT during the click pass,
# where the live renders inside the click block have already filled them) ---
if not decode_translate_clicked:
    if st.session_state.start_translated:
        with _translated_slot.container():
            st.markdown("#### 🌐 Translation (natural)")
            st.markdown(_md_preserve_breaks(st.session_state.start_translated))

    _render_audio_section(_audio_slot, st.session_state.start_audio)
    _render_decoded_section(
        _decoded_slot, st.session_state.start_decoded, key="decoded_state",
    )

    if st.session_state.start_comments:
        with _notes_slot.container():
            st.markdown("#### 📝 Notes")
            st.info(st.session_state.start_comments)

    _render_debug_section(_debug_slot, st.session_state.start_debug)
    _render_error_section(_error_slot, st.session_state.start_errors)

# --- Save to text library (independent of decode result: translation + audio
# alone are valid reasons to save the source text). ---
_has_anything_to_save = bool(
    st.session_state.start_decoded
    or st.session_state.start_translated
    or st.session_state.start_audio
)
if _has_anything_to_save:
    save_to_library(
        input_text.strip(),
        source_language,
        st.session_state.user_id,
        key_prefix="start_save",
        decoded_text=st.session_state.start_decoded,
        translated_text=st.session_state.start_translated,
        target_language=target_language,
        notes=st.session_state.start_comments,
        audio_bytes=st.session_state.start_audio,
    )

# --- Add word/phrase to vocabulary (MVP-01: dictionary disabled) ---
# with st.expander("Add word or phrase to vocabulary", expanded=False):
#     ...  # Re-enable in MVP-02

# --- Download ---
st.download_button(
    "Download output as .txt",
    data=st.session_state.start_output or "",
    file_name=f"langdec_{source_language}_to_{target_language}.txt",
    mime="text/plain",
    use_container_width=True,
    disabled=not bool(st.session_state.start_output),
)
