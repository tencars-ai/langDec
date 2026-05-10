"""Shared UI constants and components for langDec pages."""
import streamlit as st

LANGUAGES = {
    "German (de)": "de",
    "English (en)": "en",
    "Portuguese (pt)": "pt",
    "Swedish (sv)": "sv",
}

LANGUAGES_WITH_ALL = {
    "All": None,
    **LANGUAGES,
}


def save_to_library(
    content: str,
    source_language: str,
    user_id: str,
    default_title: str = "Untitled text",
    key_prefix: str = "save",
    decoded_text: str = "",
    translated_text: str = "",
    target_language: str = "",
    notes: str = "",
    audio_bytes: bytes | None = None,
) -> None:
    """Render the 'Save to text library' expander with folder selection.

    Saves text to the `texts` table. If `audio_bytes` is provided, also inserts
    a linked row in `audio_files` using the returned text UUID.

    Args:
        content: Original source text.
        source_language: ISO language code, e.g. 'de'.
        user_id: Current user's ID.
        default_title: Pre-filled title value.
        key_prefix: Unique prefix for Streamlit widget keys (must differ per page).
        decoded_text: Word-by-word Birkenbihl decoded text (optional).
        translated_text: Natural/contextual translation (optional).
        target_language: ISO code of the target language (optional).
        notes: LLM notes/comments from the decoder (optional).
        audio_bytes: MP3 audio bytes to save linked to this text (optional).
    """
    from services.db_service import DBService

    with st.expander("Save to text library", expanded=False):
        db = DBService()
        title = st.text_input("Title", value=default_title, key=f"{key_prefix}_title")

        folders = db.execute(
            "SELECT id, name FROM folders WHERE user_id = %s ORDER BY name",
            (user_id,),
        )
        folder_options = {"(No folder)": None, **{f["name"]: str(f["id"]) for f in folders}}

        col_folder, col_new = st.columns([3, 1])
        with col_folder:
            folder_label = st.selectbox("Folder", list(folder_options.keys()), key=f"{key_prefix}_folder")
        with col_new:
            st.markdown("&nbsp;", unsafe_allow_html=True)
            show_new_folder = st.toggle("New folder", key=f"{key_prefix}_show_new_folder")

        if show_new_folder:
            new_folder_col, new_folder_btn_col = st.columns([3, 1])
            with new_folder_col:
                new_folder_name = st.text_input(
                    "Folder name", placeholder="e.g. Portuguese texts",
                    key=f"{key_prefix}_new_folder_name", label_visibility="collapsed",
                )
            with new_folder_btn_col:
                if st.button("Create", key=f"{key_prefix}_create_folder_btn"):
                    if new_folder_name.strip():
                        try:
                            db.execute_write(
                                "INSERT INTO folders (user_id, name) VALUES (%s, %s)",
                                (user_id, new_folder_name.strip()),
                            )
                            st.success(f"Folder '{new_folder_name}' created.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed: {e}")
                    else:
                        st.warning("Enter a folder name.")

        if st.button("Save text", type="primary", key=f"{key_prefix}_btn"):
            if title.strip():
                try:
                    row = db.execute_returning(
                        "INSERT INTO texts"
                        " (user_id, folder_id, title, content, source_language,"
                        "  target_language, decoded_text, translated_text, notes)"
                        " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
                        " RETURNING id",
                        (
                            user_id,
                            folder_options[folder_label],
                            title.strip(),
                            content,
                            source_language,
                            target_language or None,
                            decoded_text or None,
                            translated_text or None,
                            notes or None,
                        ),
                    )
                    if audio_bytes and row:
                        from services.audio_storage_service import AudioStorageService
                        AudioStorageService(db).save(
                            user_id=user_id,
                            data=audio_bytes,
                            language=source_language,
                            tts_service="gtts",
                            text_id=str(row["id"]),
                        )
                    st.success(f"Saved as '{title}'.")
                except Exception as e:
                    st.error(f"Failed: {e}")
