"""
Team summary. If an Anthropic key is set, Claude phrases the computed grades into
a scouting-style paragraph. Claude is given only the grades and needs and is told
not to invent numbers. With no key (or on any error), the deterministic template
from team_report is used instead. Claude is never the source of a grade or stat.
"""

import json

from config.settings import ANTHROPIC_API_KEY, CLAUDE_MODEL
from grading.team_report import deterministic_summary, overall_grade, needs, best_unit

_SYSTEM = (
    "You are a pro sports roster analyst. Write a tight, plain scouting summary of "
    "a team's roster using ONLY the position grades and needs provided in the user "
    "message. Do not invent any statistics, players, or numbers beyond what is given. "
    "Reference the grades that are given. 4 to 6 sentences. Do not use em dashes."
)


def _payload(team_name: str, pos: dict, sport: str) -> str:
    return json.dumps({
        "team": team_name,
        "sport": sport,
        "overall_grade": overall_grade(pos, sport),
        "position_grades": {g: {"grade": i["grade"], "letter": i["letter"]} for g, i in pos.items()},
        "best_unit": best_unit(pos),
        "needs": needs(pos),
    }, default=str)


def summarize(team_name: str, pos: dict, sport: str) -> str:
    if not pos:
        return deterministic_summary(team_name, pos, sport)
    if not ANTHROPIC_API_KEY:
        return deterministic_summary(team_name, pos, sport)

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        msg = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=400,
            system=_SYSTEM,
            messages=[{"role": "user", "content": _payload(team_name, pos, sport)}],
        )
        text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
        return text or deterministic_summary(team_name, pos, sport)
    except Exception:
        return deterministic_summary(team_name, pos, sport)
