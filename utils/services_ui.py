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


def _resolve(name: str):
    """Look up a service by display name across LLMs and fallbacks."""
    llm_services = st.session_state.get("llm_services") or {}
    if name in llm_services:
        return llm_services[name]
    # Backward-compat with old singular session key.
    llm = st.session_state.get("llm_service")
    if llm and name == llm.name:
        return llm
    return _fallback_services().get(name, GoogleDeepTranslatorService())


def get_decode_service():
    """Return the TranslationService to use for decoding."""
    return _resolve(st.session_state.get("decode_service_name", "Google Translate"))


def get_translate_service():
    """Return the TranslationService to use for translation."""
    return _resolve(st.session_state.get("translate_service_name", "Google Translate"))


def get_max_line_length() -> int:
    return st.session_state.get("max_line_length", 65)


def get_ocr_threshold() -> int:
    return st.session_state.get("ocr_line_height_threshold", 30)
