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

    st.markdown("#### 💾 Save to text library")
    with st.container():
        db = DBService()
        title = st.text_input("Title", value=default_title, key=f"{key_prefix}_title")

        folders = db.execute(
            "SELECT folder_id, name FROM folders WHERE user_id = %s ORDER BY name",
            (user_id,),
        )
        _NEW_FOLDER_SENTINEL = "__new_folder__"
        folder_options = {
            "(No folder)": None,
            **{f["name"]: str(f["folder_id"]) for f in folders},
            "<Create New Folder>": _NEW_FOLDER_SENTINEL,
        }

        folder_label = st.selectbox(
            "Folder", list(folder_options.keys()), key=f"{key_prefix}_folder",
        )
        is_new_folder = folder_options[folder_label] == _NEW_FOLDER_SENTINEL

        new_folder_name = ""
        if is_new_folder:
            new_folder_name = st.text_input(
                "New folder name", placeholder="e.g. Portuguese texts",
                key=f"{key_prefix}_new_folder_name",
            )

        save_label = "Save Text to New Folder" if is_new_folder else "Save Text"
        if st.button(save_label, type="primary", key=f"{key_prefix}_btn"):
            if not title.strip():
                st.warning("Please enter a title.")
            elif is_new_folder and not new_folder_name.strip():
                st.warning("Please enter a name for the new folder.")
            else:
                try:
                    if is_new_folder:
                        new_folder = db.execute_returning(
                            "INSERT INTO folders (user_id, name) VALUES (%s, %s) RETURNING folder_id",
                            (user_id, new_folder_name.strip()),
                        )
                        folder_id = str(new_folder["folder_id"])
                    else:
                        folder_id = folder_options[folder_label]

                    row = db.execute_returning(
                        "INSERT INTO texts"
                        " (user_id, folder_id, title, content, source_language,"
                        "  target_language, decoded_text, translated_text, notes)"
                        " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
                        " RETURNING text_id",
                        (
                            user_id,
                            folder_id,
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
                            text_id=str(row["text_id"]),
                        )
                    if is_new_folder:
                        st.success(f"Saved as '{title}' in new folder '{new_folder_name}'.")
                    else:
                        st.success(f"Saved as '{title}'.")
                except Exception as e:
                    st.error(f"Failed: {e}")
