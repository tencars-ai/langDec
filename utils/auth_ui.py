"""
Shared sidebar UI – call render_sidebar() at the top of every page.
"""
import streamlit as st


def render_sidebar() -> None:
    """Render the sidebar with user info and logout button."""
    with st.sidebar:
        username = st.session_state.get("username", "")
        if username:
            st.markdown(f"**{username}**")
        if st.button("Logout", use_container_width=True):
            st.session_state.clear()
            st.switch_page("app.py")
