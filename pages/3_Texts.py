"""
Text library – browse folders, save and load texts.
"""
import streamlit as st
from utils.auth_ui import render_sidebar
from services.db_service import DBService

st.set_page_config(page_title="langDec – Texts", layout="centered")

if "user_id" not in st.session_state:
    st.warning("Please log in first.")
    st.stop()

render_sidebar()

user_id = st.session_state.user_id
db = DBService()

st.title("Text Library")

# --- Create folder ---
with st.expander("New folder", expanded=False):
    folder_name = st.text_input("Folder name", key="new_folder_name")
    if st.button("Create folder"):
        if folder_name.strip():
            db.execute_write(
                "INSERT INTO folders (user_id, name) VALUES (%s, %s)",
                (user_id, folder_name.strip()),
            )
            st.success(f"Folder '{folder_name}' created.")
            st.rerun()

# --- Load folders ---
folders = db.execute(
    "SELECT id, name FROM folders WHERE user_id = %s ORDER BY name",
    (user_id,),
)
folder_map = {str(f["id"]): f["name"] for f in folders}
folder_options = {"(No folder)": None, **{f["name"]: str(f["id"]) for f in folders}}

# --- Add text manually ---
with st.expander("Add text manually", expanded=False):
    title = st.text_input("Title", key="add_text_title")
    content = st.text_area("Content", height=150, key="add_text_content")
    lang_options = {"German (de)": "de", "English (en)": "en", "Portuguese (pt)": "pt"}
    lang_label = st.selectbox("Source language", list(lang_options.keys()), key="add_text_lang")
    folder_label = st.selectbox("Folder", list(folder_options.keys()), key="add_text_folder")
    if st.button("Save text", type="primary"):
        if title.strip() and content.strip():
            folder_id = folder_options[folder_label]
            db.execute_write(
                "INSERT INTO texts (user_id, folder_id, title, content, source_language) VALUES (%s, %s, %s, %s, %s)",
                (user_id, folder_id, title.strip(), content.strip(), lang_options[lang_label]),
            )
            st.success(f"Text '{title}' saved.")
            st.rerun()

# --- List texts ---
st.markdown("---")

texts = db.execute(
    """
    SELECT t.id, t.title, t.source_language, t.created_at, t.folder_id,
           f.name AS folder_name
    FROM texts t
    LEFT JOIN folders f ON f.id = t.folder_id
    WHERE t.user_id = %s
    ORDER BY t.created_at DESC
    """,
    (user_id,),
)

if not texts:
    st.info("No texts yet. Use the Decoder or add one manually above.")
else:
    search = st.text_input("Search texts", placeholder="Filter by title…")
    for text in texts:
        if search and search.lower() not in text["title"].lower():
            continue
        folder_label_display = text["folder_name"] or "(No folder)"
        with st.expander(f"{text['title']}  —  {text['source_language'].upper()}  |  {folder_label_display}", expanded=False):
            full = db.execute_one("SELECT content, notes FROM texts WHERE id = %s", (str(text["id"]),))
            st.text_area("Content", value=full["content"] if full else "", height=150, key=f"content_{text['id']}", disabled=True)

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Load into Decoder", key=f"load_{text['id']}"):
                    st.session_state.input_text = full["content"] if full else ""
                    st.switch_page("pages/1_Decode.py")
            with col2:
                if st.button("Delete", key=f"del_{text['id']}"):
                    db.execute_write(
                        "DELETE FROM texts WHERE id = %s AND user_id = %s",
                        (str(text["id"]), user_id),
                    )
                    st.rerun()
