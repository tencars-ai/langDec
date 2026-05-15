"""
Shared sidebar UI – call render_sidebar() at the top of every page.
"""
import streamlit as st


def require_login() -> None:
    """Show login prompt with navigation button and stop if user is not logged in."""
    if "user_id" not in st.session_state:
        st.warning("Please log in first.")
        if st.button("Go to Login", type="primary"):
            st.rerun()
        st.stop()


def render_sidebar() -> None:
    """Render the sidebar with user info and logout button."""
    with st.sidebar:
        username = st.session_state.get("username", "")
        if username:
            st.markdown(f"**{username}**")
        if st.button("Logout", use_container_width=True):
            st.session_state.clear()
            st.rerun()
