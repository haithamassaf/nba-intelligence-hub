"""NFL assistant chat view."""

import streamlit as st

from assistant import nfl_agent

_EXAMPLES = (
    "Would trading Brandon Aiyuk to the Jets for a 2027 1st be cap legal?",
    "How much cap space do the 49ers have?",
    "Who has the highest cap hit on the Cowboys?",
)


def render_assistant(roster_df, teams_df):
    st.markdown("#### Ask the NFL AI")
    st.caption("Ask about player salaries, team cap space, or whether a trade is legal. "
               "Cap math comes from the live data, not a guess.")
    st.caption("Try: " + "  •  ".join(f"\u201c{e}\u201d" for e in _EXAMPLES))

    if "nfl_chat" not in st.session_state:
        st.session_state.nfl_chat = []

    for msg in st.session_state.nfl_chat:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    prompt = st.chat_input("Ask anything about NFL rosters, cap, or trades...")
    if not prompt:
        return

    st.session_state.nfl_chat.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Checking the data..."):
            history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.nfl_chat[:-1]]
            try:
                answer, _ = nfl_agent.ask(prompt, roster_df, teams_df, history=history)
            except Exception as e:
                answer = f"Something went wrong: {e}"
        st.markdown(answer)

    st.session_state.nfl_chat.append({"role": "assistant", "content": answer})
