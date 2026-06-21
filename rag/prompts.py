"""
System prompts and prompt templates for the RAG chain.

Prompts are keyed by sport so the same pipeline can serve NBA and NFL.
"""

# ── System prompts (response generation) ─────────────────────────────

_NBA_SYSTEM = """\
You are an elite NBA analyst with deep statistical knowledge. You answer
questions about the current NBA season using ONLY the stats and context
provided below. Be conversational but precise. Always cite specific
numbers. If the data doesn't contain enough info to answer, say so
honestly rather than guessing.

When comparing players, use tables or structured formats. When discussing
award races (MVP, DPOY, Sixth Man), explain your reasoning with stats. Keep
answers concise but insightful, like a knowledgeable friend who watches
every game."""

_NFL_SYSTEM = """\
You are an elite NFL analyst with deep statistical knowledge. You answer
questions about the current NFL season using ONLY the stats and context
provided below. Be conversational but precise. Always cite specific
numbers. If the data doesn't contain enough info to answer, say so
honestly rather than guessing.

Football stats are position-dependent: judge QBs on passing efficiency,
yards, touchdowns, and interceptions; running backs on rushing yards,
yards per carry, and total touches; receivers and tight ends on receptions,
targets, and receiving yards. When comparing players, use tables or
structured formats. When discussing award races (MVP, OPOY, DPOY) or
playoff seeding, explain your reasoning with stats. Keep answers concise
but insightful, like a knowledgeable friend who watches every game."""

SYSTEM_PROMPTS = {
    "nba": _NBA_SYSTEM,
    "nfl": _NFL_SYSTEM,
}


# ── Classification prompts (intent + entity extraction) ──────────────

_NBA_CLASSIFY = """\
Given this user question about the NBA, extract:
1. intent: one of [player_stats, player_comparison, team_stats, rankings, award_race, general]
2. entities: list of player names, team names, or stat categories mentioned
3. time_range: one of [season, last_10, last_month, career, not_specified]

Respond in JSON only. No markdown fences, just raw JSON.

Question: {question}"""

_NFL_CLASSIFY = """\
Given this user question about the NFL, extract:
1. intent: one of [player_stats, player_comparison, team_stats, rankings, award_race, general]
2. entities: list of player names (QB/RB/WR/TE), team names, or stat categories mentioned
3. time_range: one of [season, last_5, last_month, career, not_specified]

Respond in JSON only. No markdown fences, just raw JSON.

Question: {question}"""

CLASSIFY_PROMPTS = {
    "nba": _NBA_CLASSIFY,
    "nfl": _NFL_CLASSIFY,
}


# ── Shared context template ──────────────────────────────────────────

CONTEXT_TEMPLATE = """\
Here are the relevant stats and context for this question:

{context}

---
User question: {question}"""


# ── Helpers ──────────────────────────────────────────────────────────

def system_prompt(sport: str) -> str:
    return SYSTEM_PROMPTS.get(sport, _NBA_SYSTEM)


def classify_prompt(sport: str) -> str:
    return CLASSIFY_PROMPTS.get(sport, _NBA_CLASSIFY)
