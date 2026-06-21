"""Chat message rendering with styled bubbles."""

import streamlit as st

SPORT_AVATAR = {"nba": "🏀", "nfl": "🏈"}


def render_message(role: str, content: str, sport: str = "nba"):
    """Render a single chat message with a sport-aware assistant avatar."""
    avatar = SPORT_AVATAR.get(sport, "🏀") if role == "assistant" else None
    with st.chat_message(role, avatar=avatar):
        st.markdown(content)


def render_chat_history(messages: list | None = None, sport: str = "nba"):
    """Render all messages. Falls back to session_state['messages'] if none given."""
    if messages is None:
        messages = st.session_state.get("messages", [])
    for msg in messages:
        render_message(msg["role"], msg["content"], sport)


def add_message(messages: list, role: str, content: str):
    """Append a message to a provided history list."""
    messages.append({"role": role, "content": content})
