"""
Settings page – API key management, password change, account deletion.
"""
import streamlit as st
from utils.auth_ui import render_sidebar
from services.db_service import DBService
from services.auth_service import AuthService
from services.llm_service import build_llm_service

st.set_page_config(page_title="langDec – Settings", layout="centered")

if "user_id" not in st.session_state:
    st.warning("Please log in first.")
    st.stop()

render_sidebar()

user_id = st.session_state.user_id
db = DBService()
auth = AuthService()

st.title("Settings")

# -------------------------------------------------------
# API Key Management
# -------------------------------------------------------
st.subheader("LLM API Keys")
st.caption("API keys are encrypted before storage. They are only decrypted in your session.")

for provider, label in [("openai", "OpenAI"), ("anthropic", "Anthropic (Claude)")]:
    existing = db.execute_one(
        "SELECT id FROM user_api_keys WHERE user_id = %s AND provider = %s",
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
            "SELECT password_hash FROM users WHERE id = %s",
            (user_id,),
        )
        if user and auth.verify_password(current_pw, user["password_hash"]):
            new_hash = auth.hash_password(new_pw)
            db.execute_write(
                "UPDATE users SET password_hash = %s WHERE id = %s",
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
    delete_submitted = st.form_submit_button("Delete my account", type="primary")

if delete_submitted:
    if not confirm_check:
        st.error("Please check the confirmation box.")
    else:
        user = db.execute_one("SELECT password_hash FROM users WHERE id = %s", (user_id,))
        if user and auth.verify_password(confirm_pw, user["password_hash"]):
            db.execute_write("DELETE FROM users WHERE id = %s", (user_id,))
            st.session_state.clear()
            st.success("Account deleted.")
            st.rerun()
        else:
            st.error("Password incorrect.")
