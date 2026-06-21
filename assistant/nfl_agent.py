"""
NFL assistant: a Claude agent with tools.

Claude reads the question, calls the tools in assistant.tools to pull live roster,
cap, and trade data, and answers from what comes back. Cap legality and salaries
always come from the tools, never from the model's memory. General football rules
or history can be answered from Claude's own knowledge, flagged as such.

Entry point:
    answer, transcript = ask(question, roster_df, teams_df, history=[...])
`history` is a list of {"role": "user"|"assistant", "content": "<text>"} for
multi-turn context; tool calls live only inside a single ask().
"""

import json

try:
    from config.settings import ANTHROPIC_API_KEY, CLAUDE_MODEL
except ImportError:  # pragma: no cover
    import os
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

from assistant.tools import TOOL_SCHEMAS, NFLTools

_SYSTEM = (
    "You are an NFL front-office analyst assistant built into a roster and trade app. "
    "You can answer questions about current players, teams, salary cap space, and whether "
    "a proposed trade is cap-legal. "
    "Use the tools for anything involving current rosters, salaries, cap space, or trade "
    "legality: never state a salary, cap number, or legality result from memory, since the "
    "tools hold the live, validated data. For any 'is this trade legal or fair' question, "
    "call evaluate_trade and report the cap-legality result and each team's cap space after, "
    "then give a brief view on the value using the pick values returned. "
    "If a player or team is not found, say so and ask for a clarification rather than guessing. "
    "You may answer general football rules, history, or strategy from your own knowledge, but "
    "make clear when an answer is general knowledge rather than the app's live data. "
    "Salaries are in millions of dollars. Be concise and specific. Do not use em dashes."
)

_MAX_STEPS = 6


def _text_of(content) -> str:
    return "".join(getattr(b, "text", "") for b in content if getattr(b, "type", "") == "text").strip()


def ask(question: str, roster_df, teams_df, history=None, max_steps: int = _MAX_STEPS):
    """Return (answer_text, transcript). transcript is the running message list."""
    if not ANTHROPIC_API_KEY:
        return ("The assistant needs an Anthropic API key. Set ANTHROPIC_API_KEY in your .env to enable it.", [])

    import anthropic
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    tools = NFLTools(roster_df, teams_df)

    messages = []
    for turn in (history or []):
        role = turn.get("role")
        text = turn.get("content")
        if role in ("user", "assistant") and text:
            messages.append({"role": role, "content": text})
    messages.append({"role": "user", "content": question})

    for _ in range(max_steps):
        resp = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1200,
            system=_SYSTEM,
            tools=TOOL_SCHEMAS,
            messages=messages,
        )

        if resp.stop_reason != "tool_use":
            messages.append({"role": "assistant", "content": resp.content})
            return _text_of(resp.content) or "I could not produce an answer.", messages

        messages.append({"role": "assistant", "content": resp.content})
        results = []
        for block in resp.content:
            if getattr(block, "type", "") == "tool_use":
                output = tools.run(block.name, block.input or {})
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(output, default=str),
                })
        messages.append({"role": "user", "content": results})

    return ("That took too many steps to resolve. Try narrowing the question.", messages)
