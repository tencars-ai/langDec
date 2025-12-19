# Streamlit is the web framework we use - it creates the web interface
import streamlit as st

# PostgreSQL connection (commented out for now)
#import psycopg

# Import our custom classes from other files
from domain.decoder import WordByWordDecoder
from domain.translator import Translator
from services.translation_service import GoogleDeepTranslatorService

# Create instances that will be used throughout the app
# _ prefix indicates these are module-level "private" variables
_translation_service = GoogleDeepTranslatorService()  # Creates the translation service
_decoder = WordByWordDecoder(_translation_service)    # Creates the decoder with the service
_translator = Translator(_translation_service)        # Creates the translator with the service

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
st.caption("Paste text → select languages → configure → decode")

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
# 4) Configuration section
# -------------------------------------------------
# st.expander creates a collapsible section
# expanded=True means it's open by default
with st.expander("Decoder configuration", expanded=True):
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
# 5) Language selection and input
# -------------------------------------------------
# st.columns(2) creates two columns of equal width
# We can place different elements in each column
col_left, col_right = st.columns(2)

# Place source language selector in left column
with col_left:
    # st.selectbox creates a dropdown menu
    source_label = st.selectbox(
        "Source Language",              # Label above dropdown
        list(LANGUAGES.keys()),         # Options to choose from
        index=2,                        # Default selection: index 2 = Portuguese
    )

# Place target language selector in right column
with col_right:
    target_label = st.selectbox(
        "Target Language (Mother Tongue)",
        list(LANGUAGES.keys()),
        index=0,  # Default selection: index 0 = German
    )

# Convert display labels to language codes
# Example: "German (de)" → "de"
source_language = LANGUAGES[source_label]
target_language = LANGUAGES[target_label]

# st.text_area creates a multi-line text input field
input_text = st.text_area(
    "Input text",                      # Label
    height=220,                        # Height in pixels
    placeholder="Paste your text here…",  # Hint text when empty
)

# Show warning if user selected same language for source and target
if source_language == target_language:
    st.warning("Source and target language are identical.")

# Create two buttons side by side
# st.columns creates columns for side-by-side layout
btn_col1, btn_col2 = st.columns(2)

# st.button creates a clickable button
# Returns True when clicked, False otherwise
with btn_col1:
    decode_clicked = st.button(
        "Decode",                          # Button text
        type="primary",                    # Makes button blue/prominent
        use_container_width=True,          # Makes button full width
    )

with btn_col2:
    translate_clicked = st.button(
        "Translate",                       # Button text
        type="secondary",                  # Secondary button style
        use_container_width=True,          # Makes button full width
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
            raw_decoded = decode_text(
                input_text.strip(),
                source_language,
                target_language,
            )
            
            # Debug: Show what we got
            st.write(f"DEBUG - Raw decoded length: {len(raw_decoded)}")
            st.write(f"DEBUG - Raw decoded preview: {raw_decoded[:100] if raw_decoded else 'EMPTY'}")

            # Apply additional line wrapping to the output
            # Store result in session state so it persists
            st.session_state.decoded_text = apply_line_breaks(
                raw_decoded,
                max_line_length,
            )
            
            # Debug: Show what's in session state
            st.write(f"DEBUG - Session state length: {len(st.session_state.decoded_text)}")
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

# Display the decoded output in a text area
# This text area is read-only by default (user can select/copy but not edit)
st.text_area(
    "Decoded text (word-by-word)",              # Label
    value=st.session_state.decoded_text,        # Content to display
    height=220,                                 # Height in pixels
    help="Select and copy the text (Ctrl/Cmd + C).",  # Help tooltip
    key="decoded_output",                       # Unique key for styling
)

# Display the translated output in a second text area
st.text_area(
    "Translated text (natural translation)",    # Label
    value=st.session_state.translated_text,     # Content to display
    height=220,                                 # Height in pixels
    help="Select and copy the text (Ctrl/Cmd + C).",  # Help tooltip
    key="translated_output",                    # Unique key for styling
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

