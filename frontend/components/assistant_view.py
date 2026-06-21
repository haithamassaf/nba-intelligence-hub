"""NFL AI assistant chat view."""

import streamlit as st
from assistant import nfl_agent

_EXAMPLES = [
    "Would trading Brandon Aiyuk to the Cowboys for a 2026 1st and Dak Prescott be cap legal?",
    "How much cap space do the 49ers have?",
    "Who has the biggest cap hit on the Chiefs?",
    "Break down the 49ers defense scheme and their biggest weakness",
    "Who should the Cowboys target in free agency to fix their offensive line?",
    "Is Brock Purdy elite or a product of the system?",
    "Who are the top 5 quarterbacks in the NFL right now?",
]


def render_assistant(roster_df, teams_df):
    st.markdown("#### NFL AI")
    st.caption(
        "Ask anything NFL. Trades, cap space, rosters, strategy, history, draft, fantasy. "
        "Contract details and cap legality are pulled from live data."
    )

    with st.expander("Example questions"):
        for ex in _EXAMPLES:
            st.markdown(f"- {ex}")

    if "nfl_chat" not in st.session_state:
        st.session_state.nfl_chat = []

    # Render history
    for msg in st.session_state.nfl_chat:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Clear button
    if st.session_state.nfl_chat:
        if st.button("Clear conversation", key="clear_chat"):
            st.session_state.nfl_chat = []
            st.rerun()

    prompt = st.chat_input("Ask anything about the NFL...")
    if not prompt:
        return

    st.session_state.nfl_chat.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            history = [
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.nfl_chat[:-1]
            ]
            try:
                answer, _ = nfl_agent.ask(prompt, roster_df, teams_df, history=history)
            except Exception as e:
                answer = f"Something went wrong: {e}"
        st.markdown(answer)

    st.session_state.nfl_chat.append({"role": "assistant", "content": answer})
