"""Centralized CSS injection for langDec pages."""
import streamlit as st

_BASE_CSS = """
<style>
  h1 { font-size: 1.8rem !important; margin-top: 0.5rem !important; margin-bottom: 0.3rem !important; }
  textarea { font-family: "Consolas", "Courier New", monospace !important; font-size: 14px !important; line-height: 1.5 !important; }
  .stDownloadButton > button { background-color: white !important; border: 1px solid #DADCE0 !important; color: black !important; }
</style>
"""

_DECODED_CSS = """
<style>
  textarea[aria-label="Decoded text (word-by-word)"] { background-color: #F0F7F0 !important; color: black !important; }
</style>
"""

_TRANSLATED_CSS = """
<style>
  textarea[aria-label="Translated text (natural translation)"] { background-color: #EEF4FB !important; color: black !important; }
</style>
"""


def inject_styles() -> None:
    """Inject base styles. Call once at the top of every page."""
    st.markdown(_BASE_CSS, unsafe_allow_html=True)


def inject_decoded_style() -> None:
    """Tint the decoded output textarea. Call on pages that show decoded text."""
    st.markdown(_DECODED_CSS, unsafe_allow_html=True)


def inject_translated_style() -> None:
    """Tint the translated output textarea. Call on pages that show translated text."""
    st.markdown(_TRANSLATED_CSS, unsafe_allow_html=True)


def inject_spellcheck_off() -> None:
    """Disable browser spellcheck on all textarea elements."""
    st.markdown(
        """<script>
        const _scObs = new MutationObserver(() => {
            document.querySelectorAll('textarea').forEach(el => el.spellcheck = false);
        });
        _scObs.observe(document.body, {childList: true, subtree: true});
        document.querySelectorAll('textarea').forEach(el => el.spellcheck = false);
        </script>""",
        unsafe_allow_html=True,
    )
