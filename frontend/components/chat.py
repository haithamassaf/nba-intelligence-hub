"""Chat message rendering with styled bubbles."""

import streamlit as st


def render_message(role: str, content: str):
    """Render a single chat message."""
    with st.chat_message(role, avatar="🏀" if role == "assistant" else None):
        st.markdown(content)


def render_chat_history():
    """Render all messages in session state."""
    for msg in st.session_state.get("messages", []):
        render_message(msg["role"], msg["content"])


def add_message(role: str, content: str):
    """Append a message to chat history."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    st.session_state.messages.append({"role": role, "content": content})
