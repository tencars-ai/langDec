"""
Shared helper – build translation service instances from session_state preferences.
"""
from __future__ import annotations
import streamlit as st
from services.translation_service import GoogleDeepTranslatorService, ArgosTranslateService

_FALLBACKS = {
    "Google Translate": None,   # instantiated lazily below
    "Argos Translate": None,
}


def _fallback_services() -> dict:
    return {
        "Google Translate": GoogleDeepTranslatorService(),
        "Argos Translate": ArgosTranslateService(),
    }


def get_decode_service():
    """Return the TranslationService to use for decoding."""
    name = st.session_state.get("decode_service_name", "Google Translate")
    llm = st.session_state.get("llm_service")
    if llm and name == llm.name:
        return llm
    return _fallback_services().get(name, GoogleDeepTranslatorService())


def get_translate_service():
    """Return the TranslationService to use for translation."""
    name = st.session_state.get("translate_service_name", "Google Translate")
    llm = st.session_state.get("llm_service")
    if llm and name == llm.name:
        return llm
    return _fallback_services().get(name, GoogleDeepTranslatorService())


def get_max_line_length() -> int:
    return st.session_state.get("max_line_length", 65)


def get_ocr_threshold() -> int:
    return st.session_state.get("ocr_line_height_threshold", 30)
