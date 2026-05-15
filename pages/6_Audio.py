"""
Audio page – TTS playback, MP3 save per user, list saved audio.
"""
import streamlit as st
from utils.auth_ui import require_login, render_sidebar
from utils.styles import inject_styles
from utils.ui import LANGUAGES
from services.tts_service import GTTSService
from services.audio_storage_service import AudioStorageService
from services.db_service import DBService

st.set_page_config(page_title="langDec – Audio", layout="wide")

require_login()
render_sidebar()
inject_styles()

user_id = st.session_state.user_id

if "audio_text_input" not in st.session_state:
    st.session_state.audio_text_input = ""
db = DBService()
audio_storage = AudioStorageService(db)
tts = GTTSService()

st.title("Audio")

# --- Generate audio ---
st.subheader("Generate audio")
text_input = st.text_area("Text to synthesize", height=150, placeholder="Paste or type your text here…", key="audio_text_input")
lang_label = st.selectbox("Language", list(LANGUAGES.keys()))
language = LANGUAGES[lang_label]

col1, col2 = st.columns(2)
with col1:
    play_btn = st.button("Play in browser", type="primary", use_container_width=True)
with col2:
    save_btn = st.button("Generate & save MP3", use_container_width=True)

if play_btn and text_input.strip():
    with st.spinner("Synthesizing…"):
        try:
            mp3_bytes = tts.synthesize(text_input.strip(), language)
            st.audio(mp3_bytes, format="audio/mp3")
        except Exception as e:
            st.error(f"TTS failed: {e}")

if save_btn and text_input.strip():
    with st.spinner("Synthesizing and saving…"):
        try:
            mp3_bytes = tts.synthesize(text_input.strip(), language)
            audio_id = audio_storage.save(
                user_id=user_id,
                data=mp3_bytes,
                language=language,
                tts_service=tts.name,
            )
            st.success(f"MP3 saved (ID: {audio_id[:8]}…)")
            st.rerun()
        except Exception as e:
            st.error(f"Failed: {e}")

# --- Saved audio files ---
st.markdown("---")
st.subheader("Saved audio files")

audio_files = audio_storage.list_for_user(user_id)
if not audio_files:
    st.info("No saved audio files yet.")
else:
    for af in audio_files:
        size_kb = (af["file_size_bytes"] or 0) // 1024
        label = f"{str(af['audio_file_id'])[:8]}…  |  {af['language'].upper()}  |  {size_kb} KB  |  {str(af['created_at'])[:19]}"
        with st.expander(label, expanded=False):
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                if st.button("Play", key=f"play_{af['audio_file_id']}"):
                    data = audio_storage.get(str(af["audio_file_id"]), user_id)
                    if data:
                        st.audio(data, format="audio/mp3")
            with col_b:
                data = audio_storage.get(str(af["audio_file_id"]), user_id)
                if data:
                    st.download_button(
                        "Download MP3",
                        data=data,
                        file_name=f"audio_{str(af['audio_file_id'])[:8]}.mp3",
                        mime="audio/mp3",
                        key=f"dl_{af['audio_file_id']}",
                    )
            with col_c:
                if st.session_state.get(f"confirm_del_audio_{af['audio_file_id']}"):
                    st.warning("Are you sure?")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("Yes", key=f"del_confirm_{af['audio_file_id']}", type="primary"):
                            audio_storage.delete(str(af["audio_file_id"]), user_id)
                            st.session_state.pop(f"confirm_del_audio_{af['audio_file_id']}", None)
                            st.rerun()
                    with c2:
                        if st.button("Cancel", key=f"del_cancel_{af['audio_file_id']}"):
                            st.session_state.pop(f"confirm_del_audio_{af['audio_file_id']}", None)
                            st.rerun()
                else:
                    if st.button("Delete", key=f"del_{af['audio_file_id']}"):
                        st.session_state[f"confirm_del_audio_{af['audio_file_id']}"] = True
                        st.rerun()
