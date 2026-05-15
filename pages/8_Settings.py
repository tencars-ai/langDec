"""
Settings page – API key management, password change, account deletion.
"""
import streamlit as st
from utils.auth_ui import require_login, render_sidebar
from utils.styles import inject_styles
from services.db_service import DBService
from services.auth_service import AuthService
from services.llm_service import build_llm_service
from services.preferences_service import PreferencesService

st.set_page_config(page_title="langDec – Settings", layout="wide")

require_login()
render_sidebar()
inject_styles()

user_id = st.session_state.user_id
db = DBService()
auth = AuthService()

st.title("Settings")

# -------------------------------------------------------
# Service Configuration
# -------------------------------------------------------
from services.translation_service import GoogleDeepTranslatorService, ArgosTranslateService

FALLBACK_SERVICES = {
    "Google Translate": GoogleDeepTranslatorService(),
    "Argos Translate": ArgosTranslateService(),
}
llm_services = st.session_state.get("llm_services") or {}

# Lazy-load LLM services from DB if not yet in session (e.g. after hot-reload without re-login,
# or sessions started before llm_services was introduced).
_db_keys = db.execute(
    "SELECT provider, api_key_encrypted FROM user_api_keys WHERE user_id = %s", (user_id,)
)
_db_providers = {r["provider"] for r in _db_keys}
_loaded_providers = {getattr(s, "provider", None) for s in llm_services.values()}
_missing = _db_providers - {p for p in _loaded_providers if p}
_decrypt_failed: set[str] = set()
if _missing:
    for row in _db_keys:
        if row["provider"] not in _missing:
            continue
        try:
            decrypted = auth.decrypt_api_key(bytes(row["api_key_encrypted"]))
            svc = build_llm_service(row["provider"], decrypted)
            llm_services[svc.name] = svc
        except Exception:
            _decrypt_failed.add(row["provider"])
    st.session_state.llm_services = llm_services

ALL_SERVICES = {**FALLBACK_SERVICES, **llm_services}

if _decrypt_failed:
    st.warning(
        f"API keys for {', '.join(sorted(_decrypt_failed))} are stored but could not be decrypted "
        "(SECRET_KEY may have changed). Re-save the key below to fix."
    )

header_col, save_col = st.columns([4, 1])
with header_col:
    st.subheader("Preferences")
with save_col:
    save_clicked = st.button(
        "Save preferences",
        type="primary",
        use_container_width=True,
        key="save_preferences_btn",
    )

st.markdown("**Decoding Service**")
st.caption("Used for word-by-word decoding (Birkenbihl method). LLM gives best quality.")

decode_options = list(ALL_SERVICES.keys())
decode_default = st.session_state.get("decode_service_name", decode_options[0])
decode_index = decode_options.index(decode_default) if decode_default in decode_options else 0
selected_decode = st.radio("Decoding service", decode_options, index=decode_index, horizontal=True, key="decode_service_radio")

st.markdown("**Decoder Output**")
max_line_length = st.number_input(
    "Line break after number of characters (0 = disabled)",
    min_value=0, max_value=300,
    value=st.session_state.get("max_line_length", 65),
    step=5,
    key="max_line_length_input",
)

st.markdown("**OCR**")
ocr_threshold = st.number_input(
    "Line height threshold (pixels)",
    min_value=10, max_value=100,
    value=st.session_state.get("ocr_line_height_threshold", 30),
    step=5,
    key="ocr_threshold_input",
)

st.markdown("**Translation Service**")
st.caption("Used for natural/contextual translation.")

translate_options = list(ALL_SERVICES.keys())
translate_default = st.session_state.get("translate_service_name", "Google Translate")
translate_index = translate_options.index(translate_default) if translate_default in translate_options else 0
selected_translate = st.radio("Translation service", translate_options, index=translate_index, horizontal=True, key="translate_service_radio")

st.markdown("**Debug**")
debug_mode = st.checkbox(
    "Show raw LLM response in Decode page",
    value=st.session_state.get("debug_mode", False),
    key="debug_mode_input",
    help="When enabled, the Decode page shows the raw JSON payload returned by the LLM. Useful for prompt tuning.",
)

if save_clicked:
    try:
        PreferencesService(db).save(
            user_id,
            decode_service_name=selected_decode,
            translate_service_name=selected_translate,
            max_line_length=max_line_length,
            ocr_line_height_threshold=ocr_threshold,
            debug_mode=debug_mode,
        )
        st.session_state.decode_service_name = selected_decode
        st.session_state.translate_service_name = selected_translate
        st.session_state.max_line_length = max_line_length
        st.session_state.ocr_line_height_threshold = ocr_threshold
        st.session_state.debug_mode = debug_mode
        st.success("Preferences saved.")
    except Exception as e:
        st.error(f"Could not save preferences: {e}")

st.markdown("---")

# -------------------------------------------------------
# API Key Management
# -------------------------------------------------------
st.subheader("LLM API Keys")
st.caption("API keys are encrypted before storage. They are only decrypted in your session.")

for provider, label in [("openai", "OpenAI"), ("anthropic", "Anthropic (Claude)")]:
    existing = db.execute_one(
        "SELECT api_key_id FROM user_api_keys WHERE user_id = %s AND provider = %s",
        (user_id, provider),
    )
    status = "Configured" if existing else "Not set"
    with st.expander(f"{label} API Key  —  {status}", expanded=not existing):
        new_key = st.text_input(f"{label} API Key", type="password", key=f"key_{provider}", placeholder="sk-…")
        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"Save {label} key", key=f"save_{provider}"):
                if new_key.strip():
                    encrypted = auth.encrypt_api_key(new_key.strip())
                    db.execute_write(
                        """
                        INSERT INTO user_api_keys (user_id, provider, api_key_encrypted)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (user_id, provider) DO UPDATE
                            SET api_key_encrypted = EXCLUDED.api_key_encrypted,
                                created_at = NOW()
                        """,
                        (user_id, provider, encrypted),
                    )
                    # Reload LLM service into session
                    try:
                        svc = build_llm_service(provider, new_key.strip())
                        st.session_state.llm_service = svc
                        services = st.session_state.get("llm_services") or {}
                        services[svc.name] = svc
                        st.session_state.llm_services = services
                    except Exception:
                        pass
                    st.success(f"{label} key saved.")
                    st.rerun()
        with col2:
            if existing and st.button(f"Test {label} key", key=f"test_{provider}"):
                row = db.execute_one(
                    "SELECT api_key_encrypted FROM user_api_keys WHERE user_id = %s AND provider = %s",
                    (user_id, provider),
                )
                if row:
                    try:
                        decrypted = auth.decrypt_api_key(bytes(row["api_key_encrypted"]))
                        svc = build_llm_service(provider, decrypted)
                        result = svc.translate_word("hello", "en", "de")
                        st.success(f"Connection OK. Test translation: hello → {result}")
                    except Exception as e:
                        st.error(f"Connection failed: {e}")

# -------------------------------------------------------
# Change password
# -------------------------------------------------------
st.markdown("---")
st.subheader("Change Password")

with st.form("change_password"):
    current_pw = st.text_input("Current password", type="password")
    new_pw = st.text_input("New password", type="password")
    new_pw2 = st.text_input("Confirm new password", type="password")
    submitted = st.form_submit_button("Update password")

if submitted:
    if new_pw != new_pw2:
        st.error("New passwords do not match.")
    elif len(new_pw) < 8:
        st.error("New password must be at least 8 characters.")
    else:
        user = db.execute_one(
            "SELECT password_hash FROM users WHERE user_id = %s",
            (user_id,),
        )
        if user and auth.verify_password(current_pw, user["password_hash"]):
            new_hash = auth.hash_password(new_pw)
            db.execute_write(
                "UPDATE users SET password_hash = %s WHERE user_id = %s",
                (new_hash, user_id),
            )
            st.success("Password updated.")
        else:
            st.error("Current password is incorrect.")

# -------------------------------------------------------
# Delete account
# -------------------------------------------------------
st.markdown("---")
st.subheader("Delete Account")
st.warning("This permanently deletes your account, all texts, dictionary entries and audio files.")

with st.form("delete_account"):
    confirm_pw = st.text_input("Enter your password to confirm", type="password")
    confirm_check = st.checkbox("I understand this cannot be undone.")
    delete_submitted = st.form_submit_button("Delete my account")

if delete_submitted:
    if not confirm_check:
        st.error("Please check the confirmation box.")
    else:
        user = db.execute_one("SELECT password_hash FROM users WHERE user_id = %s", (user_id,))
        if user and auth.verify_password(confirm_pw, user["password_hash"]):
            db.execute_write("DELETE FROM users WHERE user_id = %s", (user_id,))
            st.session_state.clear()
            st.success("Account deleted.")
            st.rerun()
        else:
            st.error("Password incorrect.")
