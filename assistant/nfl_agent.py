"""
NFL AI assistant: Claude with live data tools.

Handles any NFL question: player info, team rosters, cap space, trade legality,
draft analysis, game strategy, history, rules, fantasy, and more.

For trade questions: Claude first fetches contract details for all players
involved, then runs the cap check, then gives a full evaluation.

For general NFL questions: Claude answers from its own knowledge.
"""

import json

try:
    from config.settings import ANTHROPIC_API_KEY, CLAUDE_MODEL
except ImportError:
    import os
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

from assistant.tools import TOOL_SCHEMAS, NFLTools

_SYSTEM = """You are an expert NFL analyst assistant embedded in a roster and analytics app. You have deep knowledge of the NFL including:
- Rules, strategy, and scheme
- Player evaluation and scouting
- Salary cap and contract structures
- Draft analysis and prospect evaluation
- Historical context and records
- Fantasy football implications
- Trade evaluation and roster construction

You have access to tools that give you live data:
- Current ESPN rosters (who is actually on each team right now)
- OverTheCap contract data (real salary figures)
- Cap space calculations using the top-51 rule

IMPORTANT RULES:
1. For trade questions: ALWAYS use get_contract_info for every player involved before evaluating the trade. Never guess at salary figures. Then use evaluate_trade_cap with the real numbers.
2. For player status or team questions: use get_player_info or get_team_roster to get current data.
3. For cap space questions: use get_team_cap_space.
4. For general NFL questions (rules, history, strategy, draft, fantasy): answer from your own knowledge without needing tools.
5. Be specific and direct. Give a real opinion on trades, not just a summary.
6. Salary figures are in millions of dollars.
7. Do not use em dashes."""

_MAX_STEPS = 10


def _text_of(content) -> str:
    return "".join(getattr(b, "text", "") for b in content if getattr(b, "type", "") == "text").strip()


def ask(question: str, roster_df, teams_df, history=None, max_steps: int = _MAX_STEPS):
    if not ANTHROPIC_API_KEY:
        return ("Set ANTHROPIC_API_KEY in your .env file to enable the NFL AI assistant.", [])

    import anthropic
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    tools_handler = NFLTools(roster_df, teams_df)

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
            max_tokens=2000,
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
                output = tools_handler.run(block.name, block.input or {})
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(output, default=str),
                })
        messages.append({"role": "user", "content": results})

    return ("That question required too many steps. Try breaking it into smaller questions.", messages)
