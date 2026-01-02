# Streamlit is the web framework we use - it creates the web interface
import streamlit as st

# PostgreSQL connection (commented out for now)
#import psycopg

# Import our custom classes from other files
from domain.decoder import WordByWordDecoder
from domain.translator import Translator
from services.translation_service import (
    TranslationService,
    GoogleDeepTranslatorService,
    ArgosTranslateService,
)
from services.dictcc_translation_service import DictCcTranslationService
from services.ocr_service import TesseractOCRService, EasyOCRService

# For image processing
from PIL import Image
import io
import fitz  # PyMuPDF for PDF handling

# Dictionary of available translation services
# Makes it easy to add new services - just add them here!
AVAILABLE_SERVICES = {
    "Google Translate": GoogleDeepTranslatorService(),
    "Argos Translate": ArgosTranslateService(),
    "dict.cc Dictionary": DictCcTranslationService(),
}

# OCR Service - Use EasyOCR as default (works on Streamlit Cloud without additional installation)
_ocr_service = EasyOCRService()

# These will be initialized when user selects a service
_decoder = None
_translator = None

# -------------------------------------------------
# 1) Page configuration
# -------------------------------------------------
# Configure how the Streamlit page looks
st.set_page_config(page_title="langDec – Decoder", layout="centered")

# Dictionary to map display names to language codes
# Keys: what the user sees in the dropdown
# Values: what we send to the translation API
LANGUAGES = {
    "German (de)": "de",
    "English (en)": "en",
    "Portuguese (pt)": "pt",
}

# Apply custom CSS styling to make text areas use monospace font
# This makes the aligned output look better
# Triple quotes for multi-line string
st.markdown(
    """
    <style>
      /* Smaller title and reduced margins */
      h1 {
        font-size: 1.8rem !important;
        margin-top: 0.5rem !important;
        margin-bottom: 0.3rem !important;
      }
      
      /* Smaller section headings in expander */
      .stExpander h4 {
        font-size: 0.95rem !important;
        margin-top: 0.5rem !important;
        margin-bottom: 0.3rem !important;
      }
      
      textarea {
        font-family: "Courier New", Courier, monospace !important;
        font-size: 14px !important;
        line-height: 1.35 !important;
      }
      
      /* Green button for Decode */
      button[kind="primary"] {
        background-color: #28a745 !important;
        border-color: #28a745 !important;
      }
      button[kind="primary"]:hover {
        background-color: #218838 !important;
        border-color: #1e7e34 !important;
      }
      
      /* Blue button for Translate */
      button[kind="secondary"] {
        background-color: #007bff !important;
        border-color: #007bff !important;
        color: white !important;
      }
      button[kind="secondary"]:hover {
        background-color: #0056b3 !important;
        border-color: #004085 !important;
      }
      
      /* Light green background for decoded text area */
      textarea[aria-label="Decoded text (word-by-word)"] {
        background-color: #d4edda !important;
        color: black !important;
      }
      
      /* Light blue background for translated text area */
      textarea[aria-label="Translated text (natural translation)"] {
        background-color: #d1ecf1 !important;
        color: black !important;
      }
      
      /* White background for download button */
      .stDownloadButton > button {
        background-color: white !important;
        border: 1px solid #cccccc !important;
        color: black !important;
      }
      .stDownloadButton > button:hover {
        background-color: #f8f9fa !important;
        border-color: #999999 !important;
      }
    </style>
    """,
    unsafe_allow_html=True,  # Allow HTML/CSS in markdown
)

# Display the main title and subtitle
st.title("Language Decoder")

# -------------------------------------------------
# 2) Helper function: line wrapping
# -------------------------------------------------
def apply_line_breaks(text: str, max_chars: int) -> str:
    """
    Inserts line breaks after max_chars characters to make text fit nicely.
    
    Args:
        text: The text to wrap
        max_chars: Maximum characters per line
        
    Returns:
        Text with line breaks inserted
        
    If max_chars <= 0, the text is returned unchanged (no wrapping).
    """
    # No wrapping needed
    if max_chars <= 0:
        return text

    lines = []              # List to collect all lines
    current_line = ""       # Current line being built

    # Go through each word
    for word in text.split(" "):
        # Check if word fits on current line (+ 1 for the space)
        if len(current_line) + len(word) + 1 <= max_chars:
            # Word fits! Add it to current line
            # Add space before word, but not if line is empty
            current_line += (" " if current_line else "") + word
        else:
            # Word doesn't fit - save current line and start new one
            lines.append(current_line)
            current_line = word

    # Don't forget the last line
    if current_line:
        lines.append(current_line)

    # Join all lines with newline characters
    return "\n".join(lines)

# -------------------------------------------------
# 3) Decoder function - connects UI to our decoder
# -------------------------------------------------

def decode_text(text: str, source_lang: str, target_lang: str) -> str:
    """Wrapper function to call our decoder with the right parameters.
    
    Args:
        text: Text to decode
        source_lang: Source language code
        target_lang: Target language code
        
    Returns:
        Decoded and formatted text
    """
    # Call the decoder's decode method
    # max_line_length comes from the UI config below (defined later in the code)
    return _decoder.decode(
        text=text,
        source_lang=source_lang,
        target_lang=target_lang,
        max_line_length=max_line_length,  # This variable is defined below
    )


def translate_text(text: str, source_lang: str, target_lang: str) -> str:
    """Wrapper function to call our translator with the right parameters.
    
    Args:
        text: Text to translate
        source_lang: Source language code
        target_lang: Target language code
        
    Returns:
        Translated text
    """
    # Call the translator's translate method
    return _translator.translate(
        text=text,
        source_lang=source_lang,
        target_lang=target_lang,
    )


# -------------------------------------------------
# 4) Language selection and input
# -------------------------------------------------
# st.columns(2) creates two columns of equal width
# We can place different elements in each column
col_left, col_right = st.columns(2)

# Place source language selector in left column
with col_left:
    st.markdown("**Source Language**")
    # st.selectbox creates a dropdown menu
    source_label = st.selectbox(
        "Source Language",              # Label above dropdown
        list(LANGUAGES.keys()),         # Options to choose from
        index=2,                        # Default selection: index 2 = Portuguese
        label_visibility="collapsed",   # Hide label since we show it with markdown
    )

# Place target language selector in right column
with col_right:
    st.markdown("**Target Language (Mother Tongue)**")
    target_label = st.selectbox(
        "Target Language (Mother Tongue)",
        list(LANGUAGES.keys()),
        index=0,  # Default selection: index 0 = German
        label_visibility="collapsed",   # Hide label since we show it with markdown
    )

# Convert display labels to language codes
# Example: "German (de)" → "de"
source_language = LANGUAGES[source_label]
target_language = LANGUAGES[target_label]

# Initialize session state for input text if not exists
if "input_text" not in st.session_state:
    st.session_state.input_text = ""

# Initialize session state for OCR widgets visibility
if "show_camera" not in st.session_state:
    st.session_state.show_camera = False
if "show_browse" not in st.session_state:
    st.session_state.show_browse = False

# Initialize default values for configuration parameters
# These can be overridden by the Configuration expander below
ocr_line_height_threshold = 30  # Default value
max_line_length = 65  # Default value

# -------------------------------------------------
# Input Text Section
# -------------------------------------------------
st.markdown("**Input Text**")

# -------------------------------------------------
# OCR Section - Image Upload and Camera
# -------------------------------------------------
# Create two columns for OCR buttons
ocr_col1, ocr_col2 = st.columns(2)

with ocr_col1:
    if st.button(
        "📷 Take Photo (OCR)",
        use_container_width=True,
        help="Use your camera to capture text",
    ):
        # Toggle camera visibility
        st.session_state.show_camera = not st.session_state.show_camera
        st.session_state.show_browse = False  # Hide browse when camera is shown

with ocr_col2:
    if st.button(
        "📁 Browse Files (OCR)",
        use_container_width=True,
        help="Upload an image file",
    ):
        # Toggle browse visibility
        st.session_state.show_browse = not st.session_state.show_browse
        st.session_state.show_camera = False  # Hide camera when browse is shown

# Show camera input if enabled (appears above text area)
if st.session_state.show_camera:
    camera_photo = st.camera_input(
        "Take a photo",
        help="Capture an image with your camera",
    )
    if camera_photo:
        image = Image.open(camera_photo)
        st.image(image, caption="Image to process", use_container_width=True)
        
        if st.button("🔍 Extract Text (OCR)", type="secondary", use_container_width=True, key="ocr_camera"):
            with st.spinner('Extracting text from image...'):
                ocr_lang = EasyOCRService.get_language_code(source_label)
                extracted_text = _ocr_service.extract_text(
                    image, 
                    lang=ocr_lang, 
                    line_height_threshold=ocr_line_height_threshold
                )
                
                if st.session_state.input_text:
                    separator = "\n" if st.session_state.input_text.strip() else ""
                    st.session_state.input_text += separator + extracted_text
                else:
                    st.session_state.input_text = extracted_text
                
                st.success(f'Text extracted! ({len(extracted_text)} characters)')
                st.session_state.show_camera = False
                st.rerun()
    st.markdown("---")  # Separator line at the bottom

# Show file uploader if enabled (appears above text area)
if st.session_state.show_browse:
    uploaded_file = st.file_uploader(
        "Browse and select an image file or PDF",
        type=['png', 'jpg', 'jpeg', 'tiff', 'bmp', 'pdf'],
        help="Select an image file or PDF from your device (also supports drag & drop)",
    )
    if uploaded_file:
        # Check if it's a PDF
        if uploaded_file.name.lower().endswith('.pdf'):
            # Show PDF preview without processing
            pdf_bytes = uploaded_file.read()
            pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
            page_count = len(pdf_document)
            
            # Preview first page only
            page = pdf_document[0]
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img_data = pix.tobytes("png")
            preview_image = Image.open(io.BytesIO(img_data))
            st.image(preview_image, caption=f"PDF Preview - Page 1 of {page_count}", use_container_width=True)
            pdf_document.close()
            
            if st.button("🔍 Extract Text from PDF (OCR)", type="secondary", use_container_width=True, key="ocr_pdf"):
                # Now do the actual OCR processing
                pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
                all_extracted_text = []
                
                for page_num in range(page_count):
                    page = pdf_document[page_num]
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                    img_data = pix.tobytes("png")
                    image = Image.open(io.BytesIO(img_data))
                    
                    with st.spinner(f'Extracting text from page {page_num + 1} of {page_count}...'):
                        ocr_lang = EasyOCRService.get_language_code(source_label)
                        extracted_text = _ocr_service.extract_text(
                            image, 
                            lang=ocr_lang, 
                            line_height_threshold=ocr_line_height_threshold
                        )
                        all_extracted_text.append(extracted_text)
                
                pdf_document.close()
                combined_text = "\n\n".join(all_extracted_text)
                
                if st.session_state.input_text:
                    separator = "\n" if st.session_state.input_text.strip() else ""
                    st.session_state.input_text += separator + combined_text
                else:
                    st.session_state.input_text = combined_text
                
                st.success(f'Text extracted from {page_count} pages! ({len(combined_text)} characters)')
                st.session_state.show_browse = False
                st.rerun()
        else:
            # Regular image file
            image = Image.open(uploaded_file)
            st.image(image, caption="Image to process", use_container_width=True)
            
            if st.button("🔍 Extract Text (OCR)", type="secondary", use_container_width=True, key="ocr_browse"):
                with st.spinner('Extracting text from image...'):
                    ocr_lang = EasyOCRService.get_language_code(source_label)
                    extracted_text = _ocr_service.extract_text(
                        image, 
                        lang=ocr_lang, 
                        line_height_threshold=ocr_line_height_threshold
                    )
                    
                    if st.session_state.input_text:
                        separator = "\n" if st.session_state.input_text.strip() else ""
                        st.session_state.input_text += separator + extracted_text
                    else:
                        st.session_state.input_text = extracted_text
                    
                    st.success(f'Text extracted! ({len(extracted_text)} characters)')
                    st.session_state.show_browse = False
                    st.rerun()
    st.markdown("---")  # Separator line at the bottom

# Input text area below the OCR buttons and expandable areas
input_text = st.text_area(
    "Input Text",
    height=220,
    placeholder="Paste your text here or use OCR above…",
    key="input_text",  # This automatically syncs with st.session_state.input_text
    label_visibility="collapsed",  # Hide the label since we show it as markdown above
)

# Show warning if user selected same language for source and target
if source_language == target_language:
    st.warning("Source and target language are identical.")

# Create three buttons side by side
# st.columns creates columns for side-by-side layout
btn_col1, btn_col2, btn_col3 = st.columns(3)

# st.button creates a clickable button
# Returns True when clicked, False otherwise
with btn_col1:
    decode_clicked = st.button(
        "Decode",                          # Button text
        type="primary",                    # Makes button green/prominent
        use_container_width=True,          # Makes button full width
    )

with btn_col2:
    translate_clicked = st.button(
        "Translate",                       # Button text
        type="secondary",                  # Blue button style
        use_container_width=True,          # Makes button full width
    )

with btn_col3:
    decode_translate_clicked = st.button(
        "Decode & Translate",              # Button text
        use_container_width=True,          # Makes button full width
        help="Perform both decode and translate in one step",
    )

# -------------------------------------------------
# Configuration section (moved below buttons)
# -------------------------------------------------
# st.expander creates a collapsible section
# expanded=False means it's collapsed by default
with st.expander("Configuration", expanded=False):
    # Radio button for translation service selection
    selected_service_name = st.radio(
        "Translation Service",
        options=list(AVAILABLE_SERVICES.keys()),
        index=0,  # Default: first service (Google Translate)
        help="Choose which translation service to use for decoding and translation.",
        horizontal=True,  # Display options horizontally
    )
    
    # Get the selected service instance
    _translation_service = AVAILABLE_SERVICES[selected_service_name]
    
    # Initialize decoder and translator with selected service
    _decoder = WordByWordDecoder(_translation_service)
    _translator = Translator(_translation_service)
    
    st.markdown("#### OCR")
    # OCR line height threshold parameter
    ocr_line_height_threshold = st.number_input(
        "Line height threshold (pixels)",
        min_value=10,
        max_value=100,
        value=30,
        step=5,
        help="Vertical distance threshold to detect line breaks. Higher = fewer line breaks, lower = more line breaks.",
    )
    
    st.markdown("#### Decoder Output")
    # st.number_input creates a number input field
    # The return value is stored in max_line_length
    max_line_length = st.number_input(
        "Line break after number of characters (0 = disabled)",
        min_value=0,      # Minimum value allowed
        max_value=300,    # Maximum value allowed
        value=65,         # Default value when page loads
        step=5,           # Increment when using +/- buttons
        help="Automatically inserts line breaks to improve readability.",
    )

# -------------------------------------------------
# 6) Output section
# -------------------------------------------------
# st.session_state is like a dictionary that persists between page reruns
# It allows us to store data that survives when user interacts with the page
# Check if 'decoded_text' and 'translated_text' exist in session state, if not, create them
if "decoded_text" not in st.session_state:
    st.session_state.decoded_text = ""  # Initialize with empty string
if "translated_text" not in st.session_state:
    st.session_state.translated_text = ""  # Initialize with empty string

# Check if the Decode button was clicked
if decode_clicked:
    try:
        # Show a spinner while processing
        with st.spinner('Decoding...'):
            # Perform the decoding
            # .strip() removes leading/trailing whitespace from input
            # The decoder already handles line breaks internally
            st.session_state.decoded_text = decode_text(
                input_text.strip(),
                source_language,
                target_language,
            )
        st.success('Decoding completed!')
    except Exception as e:
        st.error(f'Error during decoding: {str(e)}')
        st.session_state.decoded_text = ""

# Check if the Translate button was clicked
if translate_clicked:
    try:
        # Show a spinner while processing
        with st.spinner('Translating...'):
            # Perform the translation
            # .strip() removes leading/trailing whitespace from input
            st.session_state.translated_text = translate_text(
                input_text.strip(),
                source_language,
                target_language,
            )
        st.success('Translation completed!')
    except Exception as e:
        st.error(f'Error during translation: {str(e)}')
        st.session_state.translated_text = ""

# Check if the Decode & Translate button was clicked
if decode_translate_clicked:
    try:
        # Show a spinner while processing
        with st.spinner('Decoding and translating...'):
            # Perform decoding first
            st.session_state.decoded_text = decode_text(
                input_text.strip(),
                source_language,
                target_language,
            )
            # Then perform translation
            st.session_state.translated_text = translate_text(
                input_text.strip(),
                source_language,
                target_language,
            )
        st.success('Decoding and translation completed!')
    except Exception as e:
        st.error(f'Error during decoding/translation: {str(e)}')
        st.session_state.decoded_text = ""
        st.session_state.translated_text = ""

# Display the decoded output in a text area
# This text area is read-only by default (user can select/copy but not edit)
st.text_area(
    "Decoded text (word-by-word)",              # Label
    value=st.session_state.decoded_text,        # Content to display
    height=220,                                 # Height in pixels
    help="Select and copy the text (Ctrl/Cmd + C).",  # Help tooltip
)

# Display the translated output in a second text area
st.text_area(
    "Translated text (natural translation)",    # Label
    value=st.session_state.translated_text,     # Content to display
    height=220,                                 # Height in pixels
    help="Select and copy the text (Ctrl/Cmd + C).",  # Help tooltip
)

# Create combined output for download
combined_output = ""
if st.session_state.decoded_text:
    combined_output += "=== DECODED (Word-by-Word) ===\n\n"
    combined_output += st.session_state.decoded_text + "\n\n"
if st.session_state.translated_text:
    combined_output += "=== TRANSLATED (Natural) ===\n\n"
    combined_output += st.session_state.translated_text + "\n"

# Download button to save both outputs as a text file
st.download_button(
    "Download output as .txt",                  # Button text
    data=combined_output or "",                 # File content with both outputs
    file_name=f"output_{source_language}_to_{target_language}.txt",  # f-string for filename
    mime="text/plain",                          # File type
    use_container_width=True,                   # Full width button
    disabled=not bool(combined_output),         # Disable if no output
)

