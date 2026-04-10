"""
Text library – browse folders, save and load texts.
"""
import streamlit as st
from utils.auth_ui import require_login, render_sidebar
from utils.styles import inject_styles, inject_spellcheck_off
from utils.ui import LANGUAGES, save_to_library
from services.db_service import DBService
from services.audio_storage_service import AudioStorageService

st.set_page_config(page_title="langDec – Text Library", layout="wide")

require_login()
render_sidebar()
inject_styles()
inject_spellcheck_off()

user_id = st.session_state.user_id
db = DBService()
audio_svc = AudioStorageService(db)

st.title("Text Library")

# --- Flash messages ---
if "_folder_flash" in st.session_state:
    st.success(st.session_state.pop("_folder_flash"))

# --- Toolbar: New folder + Add text ---
col_a, col_b = st.columns(2)
with col_a:
    with st.expander("➕ New folder", expanded=False):
        folder_name = st.text_input("Folder name", key="new_folder_name")
        if st.button("Create folder", type="primary", key="create_folder_btn"):
            if folder_name.strip():
                db.execute_write(
                    "INSERT INTO folders (user_id, name) VALUES (%s, %s)",
                    (user_id, folder_name.strip()),
                )
                st.session_state["_folder_flash"] = f"Folder '{folder_name}' created."
                st.rerun()

with col_b:
    with st.expander("➕ Add text manually", expanded=False):
        folders_for_add = db.execute(
            "SELECT id, name FROM folders WHERE user_id = %s ORDER BY name", (user_id,)
        )
        folder_options_add = {"(No folder)": None, **{f["name"]: str(f["id"]) for f in folders_for_add}}
        title_add = st.text_input("Title", key="add_text_title")
        content_add = st.text_area("Content", height=120, key="add_text_content")
        lang_label_add = st.selectbox("Language", list(LANGUAGES.keys()), key="add_text_lang")
        folder_label_add = st.selectbox("Folder", list(folder_options_add.keys()), key="add_text_folder")
        if st.button("Save text", type="primary", key="add_text_btn"):
            if title_add.strip() and content_add.strip():
                db.execute_write(
                    "INSERT INTO texts (user_id, folder_id, title, content, source_language)"
                    " VALUES (%s, %s, %s, %s, %s)",
                    (user_id, folder_options_add[folder_label_add], title_add.strip(),
                     content_add.strip(), LANGUAGES[lang_label_add]),
                )
                st.success(f"Text '{title_add}' saved.")
                st.rerun()

st.markdown("---")

# --- Load all texts with folder info ---
texts = db.execute(
    """
    SELECT t.id, t.title, t.source_language, t.created_at, t.folder_id,
           f.name AS folder_name
    FROM texts t
    LEFT JOIN folders f ON f.id = t.folder_id
    WHERE t.user_id = %s
    ORDER BY COALESCE(f.name, '') ASC, t.created_at DESC
    """,
    (user_id,),
)

if not texts:
    st.info("No texts yet. Decode a text or add one manually above.")
else:
    search = st.text_input("🔍 Search", placeholder="Filter by title…", key="texts_search")

    # Group texts by folder
    from collections import defaultdict
    folders_data: dict[str | None, list] = defaultdict(list)
    for text in texts:
        if search and search.lower() not in text["title"].lower():
            continue
        key = text["folder_name"]  # None → no folder
        folders_data[key].append(text)

    if not any(folders_data.values()):
        st.info("No texts match your search.")
    else:
        # Show "(No folder)" group first if it has entries
        ordered_keys = sorted(
            folders_data.keys(),
            key=lambda k: ("" if k is None else k),
        )

        for folder_name_key in ordered_keys:
            group = folders_data[folder_name_key]
            if not group:
                continue

            label = folder_name_key if folder_name_key else "📄 (No folder)"
            icon = "📁 " if folder_name_key else ""
            count = len(group)

            with st.expander(f"{icon}{label}  —  {count} text{'s' if count != 1 else ''}", expanded=False):
                for text in group:
                    with st.expander(
                        f"{text['title']}  ·  {text['source_language'].upper()}  ·  {str(text['created_at'])[:10]}",
                        expanded=False,
                    ):
                        full = db.execute_one(
                            "SELECT content, decoded_text, translated_text, notes FROM texts WHERE id = %s",
                            (str(text["id"]),),
                        )
                        content_val = (full["content"] or "") if full else ""
                        decoded_val = (full["decoded_text"] or "") if full else ""
                        translated_val = (full["translated_text"] or "") if full else ""
                        notes_val = (full["notes"] or "") if full else ""

                        tab_labels = ["Original"]
                        if decoded_val:
                            tab_labels.append("Decoded")
                        if translated_val:
                            tab_labels.append("Translation")
                        if notes_val:
                            tab_labels.append("Notes")

                        tabs = st.tabs(tab_labels)
                        idx = 0
                        with tabs[idx]:
                            st.text_area("Content", value=content_val, height=150,
                                         key=f"content_{text['id']}", disabled=True)
                        if decoded_val:
                            idx += 1
                            with tabs[idx]:
                                st.text_area("Decoded", value=decoded_val, height=150,
                                             key=f"decoded_{text['id']}", disabled=True)
                        if translated_val:
                            idx += 1
                            with tabs[idx]:
                                st.text_area("Translation", value=translated_val, height=150,
                                             key=f"translated_{text['id']}", disabled=True)
                        if notes_val:
                            idx += 1
                            with tabs[idx]:
                                st.info(notes_val)

                        # Audio playback
                        audio_data = audio_svc.get_by_text_id(str(text["id"]), user_id)
                        if audio_data:
                            st.audio(audio_data, format="audio/mp3")

                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("Load into Decode Text", key=f"load_{text['id']}", type="primary"):
                                st.session_state.input_text = content_val
                                st.switch_page("pages/0_Start.py")
                        with col2:
                            if st.session_state.get(f"confirm_del_text_{text['id']}"):
                                st.warning("Are you sure?")
                                c1, c2 = st.columns(2)
                                with c1:
                                    if st.button("Yes, delete", key=f"del_confirm_{text['id']}", type="primary"):
                                        db.execute_write(
                                            "DELETE FROM texts WHERE id = %s AND user_id = %s",
                                            (str(text["id"]), user_id),
                                        )
                                        st.session_state.pop(f"confirm_del_text_{text['id']}", None)
                                        st.rerun()
                                with c2:
                                    if st.button("Cancel", key=f"del_cancel_{text['id']}"):
                                        st.session_state.pop(f"confirm_del_text_{text['id']}", None)
                                        st.rerun()
                            else:
                                if st.button("Delete", key=f"del_{text['id']}"):
                                    st.session_state[f"confirm_del_text_{text['id']}"] = True
                                    st.rerun()
