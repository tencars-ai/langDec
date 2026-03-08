"""
langDec – Entry point.
Handles authentication and defines the navigation (st.navigation).
app.py itself does not appear as a menu item.
Default page after login: Decode.
"""
import streamlit as st

st.set_page_config(page_title="langDec", layout="centered")

# -------------------------------------------------------
# Navigation definition (only shown when logged in)
# -------------------------------------------------------
PAGES = [
    st.Page("pages/1_Decode.py",        title="Decode",        icon="🔤"),
    st.Page("pages/2_Translate.py",     title="Translate",     icon="🌐"),
    st.Page("pages/3_Texts.py",         title="Texts",         icon="📚"),
    st.Page("pages/4_Dictionary.py",    title="Dictionary",    icon="📖"),
    st.Page("pages/5_Vocab_Trainer.py", title="Vocab Trainer", icon="🃏"),
    st.Page("pages/6_Audio.py",         title="Audio",         icon="🔊"),
    st.Page("pages/7_Generate.py",      title="Generate",      icon="✨"),
    st.Page("pages/8_Settings.py",      title="Settings",      icon="⚙️"),
    st.Page("pages/9_Help.py",          title="Help",          icon="❓"),
]


def _get_services():
    from services.db_service import DBService
    from services.auth_service import AuthService
    from services.llm_service import build_llm_service
    return DBService(), AuthService(), build_llm_service


def _load_llm_service(db, auth, build_llm_service, user_id: str) -> None:
    rows = db.execute(
        "SELECT provider, api_key_encrypted FROM user_api_keys WHERE user_id = %s ORDER BY created_at DESC",
        (user_id,),
    )
    for row in rows:
        try:
            decrypted = auth.decrypt_api_key(bytes(row["api_key_encrypted"]))
            st.session_state.llm_service = build_llm_service(row["provider"], decrypted)
            break
        except Exception:
            continue


# -------------------------------------------------------
# Logged in → run navigation
# -------------------------------------------------------
if "user_id" in st.session_state:
    pg = st.navigation(PAGES)
    pg.run()
    st.stop()

# -------------------------------------------------------
# Not logged in → show login / register
# -------------------------------------------------------
st.title("langDec")
st.caption("Language learning via the Birkenbihl decoding method.")
st.markdown("---")

tab_login, tab_register = st.tabs(["Login", "Register"])

with tab_login:
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        login_btn = st.form_submit_button("Login", type="primary", use_container_width=True)

    if login_btn:
        if not username.strip() or not password:
            st.error("Please enter username and password.")
        else:
            try:
                db, auth, build_llm = _get_services()
                user = db.execute_one(
                    "SELECT id, password_hash FROM users WHERE username = %s",
                    (username.strip(),),
                )
                if user and auth.verify_password(password, user["password_hash"]):
                    st.session_state.user_id = str(user["id"])
                    st.session_state.username = username.strip()
                    _load_llm_service(db, auth, build_llm, str(user["id"]))
                    st.rerun()
                else:
                    st.error("Invalid username or password.")
            except Exception as e:
                st.error(f"Login failed: {e}")

with tab_register:
    with st.form("register_form"):
        new_username = st.text_input("Choose a username", key="reg_user")
        new_email = st.text_input("Email (optional)", key="reg_email")
        new_pw = st.text_input("Password", type="password", key="reg_pw")
        new_pw2 = st.text_input("Confirm password", type="password", key="reg_pw2")
        register_btn = st.form_submit_button("Register", type="primary", use_container_width=True)

    if register_btn:
        if not new_username.strip():
            st.error("Username is required.")
        elif len(new_pw) < 8:
            st.error("Password must be at least 8 characters.")
        elif new_pw != new_pw2:
            st.error("Passwords do not match.")
        else:
            try:
                db, auth, build_llm = _get_services()
                existing = db.execute_one(
                    "SELECT id FROM users WHERE username = %s", (new_username.strip(),)
                )
                if existing:
                    st.error("Username already taken.")
                else:
                    pw_hash = auth.hash_password(new_pw)
                    user = db.execute_returning(
                        "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s) RETURNING id",
                        (new_username.strip(), new_email.strip() or None, pw_hash),
                    )
                    st.session_state.user_id = str(user["id"])
                    st.session_state.username = new_username.strip()
                    st.session_state.llm_service = None
                    st.rerun()
            except Exception as e:
                st.error(f"Registration failed: {e}")
