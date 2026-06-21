"""
AI opinion on a proposed NFL trade.

If an Anthropic key is set, Claude evaluates the deal like a front-office exec,
using only the assets and cap figures provided. Without a key, a plain factual
summary is returned. Claude never sources a stat, only the written judgment.
"""

import json

try:
    from config.settings import ANTHROPIC_API_KEY, CLAUDE_MODEL
except ImportError:  # tolerate an older settings.py
    import os
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

_SYSTEM = (
    "You are an experienced NFL front office executive evaluating a proposed trade. "
    "Using only the players (name, position, age, average salary in $M), draft picks, "
    "and cap impact provided, give a realistic assessment: whether the value is balanced, "
    "which side comes out ahead and why, how it fits each team, and whether a deal like this "
    "would plausibly happen. Be specific and grounded in the assets given. Do not invent "
    "statistics or details not provided. Write 4 to 6 sentences. Do not use em dashes."
)


def _assets_str(players, picks):
    parts = []
    for p in players:
        apy = f" (${p['apy']}M)" if p.get("apy") is not None else ""
        age = f", {p['age']}yo" if p.get("age") is not None else ""
        parts.append(f"{p['name']} [{p.get('pos','')}{age}]{apy}")
    parts.extend(picks)
    return ", ".join(parts) if parts else "nothing"


def _fallback(summary: dict) -> str:
    a, b = summary["team_a"], summary["team_b"]
    cap = summary["cap"]
    legal = "Cap-legal for both teams." if summary["legal"] else "Not cap-legal as built."
    return (
        f"{legal} {a} sends {_assets_str(summary['a_sends'], summary['a_picks'])}. "
        f"{b} sends {_assets_str(summary['b_sends'], summary['b_picks'])}. "
        f"{a} cap space after: ${cap[a]['space_after']}M; {b}: ${cap[b]['space_after']}M. "
        f"Pick value sent: {a} {summary['a_pick_value']}, {b} {summary['b_pick_value']} "
        f"(Jimmy Johnson scale). Set an Anthropic key for a written scouting opinion."
    )


def analyze_trade(summary: dict) -> str:
    if not ANTHROPIC_API_KEY:
        return _fallback(summary)
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        msg = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=500,
            system=_SYSTEM,
            messages=[{"role": "user", "content": json.dumps(summary, default=str)}],
        )
        text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
        return text or _fallback(summary)
    except Exception:
        return _fallback(summary)
