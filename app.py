"""
langDec – Entry point.
Handles authentication and defines the navigation (st.navigation).
app.py itself does not appear as a menu item.
Default page after login: Decode.
"""
import streamlit as st

st.set_page_config(page_title="langDec", layout="wide")

# -------------------------------------------------------
# Navigation definition (only shown when logged in)
# -------------------------------------------------------
PAGES = [
    st.Page("pages/0_Start.py",         title="Decode Text",   icon="🚀"),
    # st.Page("pages/1_Decode.py",        title="Decode",        icon="🔤"),
    # st.Page("pages/2_Translate.py",     title="Translate",     icon="🌐"),
    st.Page("pages/3_Texts.py",         title="Text Library",  icon="📚"),
    # st.Page("pages/4_Dictionary.py",    title="Dictionary",    icon="📖"),
    # st.Page("pages/5_Vocab_Trainer.py", title="Vocab Trainer", icon="🃏"),
    # st.Page("pages/6_Audio.py",         title="Audio",         icon="🔊"),
    # st.Page("pages/7_Generate.py",      title="Generate",      icon="✨"),
    st.Page("pages/8_Settings.py",      title="Settings",      icon="⚙️"),
    st.Page("pages/9_Help.py",          title="Help",          icon="❓"),
]


def _get_services():
    from services.db_service import DBService
    from services.auth_service import AuthService
    from services.llm_service import build_llm_service
    return DBService(), AuthService(), build_llm_service


def _load_llm_service(db, auth, build_llm_service, user_id: str) -> None:
    """Load every configured LLM provider for this user into session state.

    Populates `st.session_state.llm_services` as {service.name: service}.
    Also keeps `st.session_state.llm_service` set to the most-recently-created
    one for backward compat with code that reads the singular key.
    """
    rows = db.execute(
        "SELECT provider, api_key_encrypted FROM user_api_keys WHERE user_id = %s ORDER BY created_at DESC",
        (user_id,),
    )
    services: dict = {}
    for row in rows:
        try:
            decrypted = auth.decrypt_api_key(bytes(row["api_key_encrypted"]))
            svc = build_llm_service(row["provider"], decrypted)
            services[svc.name] = svc
        except Exception:
            continue
    st.session_state.llm_services = services
    st.session_state.llm_service = next(iter(services.values()), None)


def _init_preferences(db, user_id: str) -> None:
    """Load persisted preferences from DB, falling back to sensible defaults.

    A missing user_preferences table (e.g. migration 006 not yet applied) must
    not block login — fall back to defaults silently in that case.
    """
    from services.preferences_service import PreferencesService
    try:
        persisted = PreferencesService(db).load(user_id)
    except Exception:
        persisted = {}

    def _decode_default() -> str:
        providers = {r["provider"] for r in db.execute(
            "SELECT provider FROM user_api_keys WHERE user_id = %s", (user_id,)
        )}
        if "anthropic" in providers:
            return "Claude (Anthropic)"
        if "openai" in providers:
            return "OpenAI"
        return "Google Translate"

    st.session_state.translate_service_name = (
        persisted.get("translate_service_name") or "Google Translate"
    )
    st.session_state.decode_service_name = (
        persisted.get("decode_service_name") or _decode_default()
    )
    st.session_state.max_line_length = persisted.get("max_line_length", 65)
    st.session_state.ocr_line_height_threshold = persisted.get("ocr_line_height_threshold", 30)
    st.session_state.debug_mode = persisted.get("debug_mode", False)


def _login_page() -> None:
    """Login / register screen. Rendered with navigation hidden (see below)."""
    st.title("langDec")
    st.caption("Language learning via the Birkenbihl decoding method.")
    st.markdown("---")

    tab_login, tab_register = st.tabs(["Login", "Register"])

    with tab_login:
        with st.form("login_form"):
            login_id = st.text_input("Username or Email")
            password = st.text_input("Password", type="password")
            login_btn = st.form_submit_button("Login", type="primary", use_container_width=True)

        if login_btn:
            if not login_id.strip() or not password:
                st.error("Please enter username or email and password.")
            else:
                try:
                    db, auth, build_llm = _get_services()
                    identifier = login_id.strip()
                    user = db.execute_one(
                        "SELECT user_id, username, password_hash FROM users"
                        " WHERE username = %s OR email = %s",
                        (identifier, identifier),
                    )
                    if user and auth.verify_password(password, user["password_hash"]):
                        st.session_state.user_id = str(user["user_id"])
                        st.session_state.username = user["username"] or identifier
                        _load_llm_service(db, auth, build_llm, str(user["user_id"]))
                        _init_preferences(db, str(user["user_id"]))
                        st.rerun()
                    else:
                        st.error("Invalid username/email or password.")
                except Exception as e:
                    st.error(f"Login failed: {e}")

    with tab_register:
        with st.form("register_form"):
            new_username = st.text_input("Choose a username", key="reg_user")
            new_email = st.text_input("Email", key="reg_email")
            new_pw = st.text_input("Password", type="password", key="reg_pw")
            new_pw2 = st.text_input("Confirm password", type="password", key="reg_pw2")
            register_btn = st.form_submit_button("Register", type="primary", use_container_width=True)

        if register_btn:
            if not new_username.strip():
                st.error("Username is required.")
            elif not new_email.strip():
                st.error("Email is required.")
            elif "@" not in new_email:
                st.error("Please enter a valid email address.")
            elif len(new_pw) < 8:
                st.error("Password must be at least 8 characters.")
            elif new_pw != new_pw2:
                st.error("Passwords do not match.")
            else:
                try:
                    db, auth, build_llm = _get_services()
                    existing_user = db.execute_one(
                        "SELECT user_id FROM users WHERE username = %s", (new_username.strip(),)
                    )
                    if existing_user:
                        st.error("Username already taken.")
                    else:
                        existing_email = db.execute_one(
                            "SELECT user_id FROM users WHERE email = %s", (new_email.strip(),)
                        )
                        if existing_email:
                            st.error("An account with this email already exists.")
                        else:
                            pw_hash = auth.hash_password(new_pw)
                            user = db.execute_returning(
                                "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s) RETURNING user_id",
                                (new_username.strip(), new_email.strip(), pw_hash),
                            )
                            st.session_state.user_id = str(user["user_id"])
                            st.session_state.username = new_username.strip()
                            st.session_state.llm_service = None
                            st.session_state.llm_services = {}
                            _init_preferences(db, str(user["user_id"]))
                            st.rerun()
                except Exception as e:
                    st.error(f"Registration failed: {e}")


# -------------------------------------------------------
# Navigation: full menu once logged in, hidden while on the login screen
# -------------------------------------------------------
if "user_id" in st.session_state:
    pg = st.navigation(PAGES)
else:
    pg = st.navigation([st.Page(_login_page, title="Login")], position="hidden")
pg.run()
