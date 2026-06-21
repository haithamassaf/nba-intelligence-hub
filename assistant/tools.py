"""
Tools for the NFL assistant.

The LLM never computes cap math or invents salaries. It calls these functions,
which read the live roster table and run the same cap-legality and pick-value
logic the trade simulator uses, then answers from what they return.

Salary shown per player is the current-season cap hit when available, otherwise
the contract APY (both in $M).
"""

import pandas as pd

from config.settings import NFL_SALARY_CAP
from trade.nfl_trade import evaluate_trade as _evaluate_trade, team_cap_space
from trade.picks import picks_value


def _salary(row) -> float | None:
    for c in ("cap_hit", "apy"):
        if c in row and pd.notna(row.get(c)):
            return round(float(row.get(c)), 2)
    return None


# ── Tool schemas advertised to the model ─────────────────────────────
TOOL_SCHEMAS = [
    {
        "name": "list_teams",
        "description": "List every NFL team with its abbreviation and full name. Use this to map a team name or nickname to the abbreviation other tools expect.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_player",
        "description": "Look up one player's team, position, age, current-season salary cap figure ($M), and key stats. Use for any question about a specific player.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Player name, full or partial."},
                "team": {"type": "string", "description": "Optional team abbreviation to disambiguate."},
            },
            "required": ["name"],
        },
    },
    {
        "name": "get_team_cap",
        "description": "Get a team's salary cap picture: cap used (top-51), cap space remaining ($M), and its largest cap figures. Use for cap-space questions.",
        "input_schema": {
            "type": "object",
            "properties": {"team": {"type": "string", "description": "Team abbreviation or name."}},
            "required": ["team"],
        },
    },
    {
        "name": "get_team_roster",
        "description": "List a team's players with position, age, and salary ($M). Use to see who is on a team.",
        "input_schema": {
            "type": "object",
            "properties": {"team": {"type": "string", "description": "Team abbreviation or name."}},
            "required": ["team"],
        },
    },
    {
        "name": "evaluate_trade",
        "description": "Check whether a proposed NFL trade is salary-cap legal under the top-51 rule and report each team's cap space after, plus draft-pick value (Jimmy Johnson scale). Always use this for any 'is this trade legal / fair' question. Players are named; picks are labels like '2027 1st'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "team_a": {"type": "string", "description": "First team, abbreviation or name."},
                "team_b": {"type": "string", "description": "Second team, abbreviation or name."},
                "players_from_a": {"type": "array", "items": {"type": "string"}, "description": "Players team A sends."},
                "players_from_b": {"type": "array", "items": {"type": "string"}, "description": "Players team B sends."},
                "picks_from_a": {"type": "array", "items": {"type": "string"}, "description": "Draft picks team A sends, e.g. ['2027 1st']."},
                "picks_from_b": {"type": "array", "items": {"type": "string"}, "description": "Draft picks team B sends."},
            },
            "required": ["team_a", "team_b"],
        },
    },
]


class NFLTools:
    """Executes the tools above against a live roster + team table."""

    def __init__(self, roster_df: pd.DataFrame, teams_df: pd.DataFrame):
        self.roster = roster_df if roster_df is not None else pd.DataFrame()
        self.teams = teams_df if teams_df is not None else pd.DataFrame()

    # -- resolution helpers --
    def _team_codes(self):
        if "team" in self.roster.columns:
            return sorted(self.roster["team"].dropna().astype(str).unique())
        return []

    def resolve_team(self, q: str):
        if not q:
            return None
        q = str(q).strip()
        codes = self._team_codes()
        for c in codes:
            if c.upper() == q.upper():
                return c
        # match against full team names
        if not self.teams.empty and "team_abbr" in self.teams.columns:
            name_col = "team_name" if "team_name" in self.teams.columns else "team_abbr"
            for _, t in self.teams.iterrows():
                if q.lower() in str(t.get(name_col, "")).lower():
                    abbr = str(t.get("team_abbr"))
                    if abbr in codes:
                        return abbr
        for c in codes:
            if q.upper() in c.upper():
                return c
        return None

    def _find_players(self, name: str, team_abbr: str | None):
        df = self.roster
        if "player_name" not in df.columns:
            return df.iloc[0:0]
        if team_abbr and "team" in df.columns:
            df = df[df["team"].astype(str) == team_abbr]
        nm = str(name).strip().lower()
        exact = df[df["player_name"].astype(str).str.lower() == nm]
        if not exact.empty:
            return exact
        return df[df["player_name"].astype(str).str.lower().str.contains(nm, na=False)]

    def _player_payload(self, row) -> dict:
        stat_cols = ("passing_yards", "passing_tds", "rushing_yards", "rushing_tds",
                     "receptions", "receiving_yards", "receiving_tds", "def_sacks", "def_tackles")
        stats = {c: row.get(c) for c in stat_cols if c in row and pd.notna(row.get(c))}
        return {
            "name": row.get("player_name"),
            "team": row.get("team"),
            "position": row.get("position"),
            "age": row.get("age"),
            "salary_cap_m": _salary(row),
            "salary_basis": "cap_hit" if pd.notna(row.get("cap_hit")) else ("apy" if "apy" in row and pd.notna(row.get("apy")) else "unknown"),
            "stats": stats,
        }

    # -- tools --
    def list_teams(self) -> dict:
        out = []
        codes = self._team_codes()
        names = {}
        if not self.teams.empty and "team_abbr" in self.teams.columns:
            ncol = "team_name" if "team_name" in self.teams.columns else "team_abbr"
            names = dict(zip(self.teams["team_abbr"].astype(str), self.teams[ncol].astype(str)))
        for c in codes:
            out.append({"abbr": c, "name": names.get(c, c)})
        return {"teams": out}

    def get_player(self, name: str, team: str | None = None) -> dict:
        abbr = self.resolve_team(team) if team else None
        hits = self._find_players(name, abbr)
        if hits.empty:
            return {"error": f"No player matching '{name}'" + (f" on {abbr}" if abbr else "")}
        if len(hits) > 1:
            opts = [{"name": r.get("player_name"), "team": r.get("team"), "position": r.get("position")}
                    for _, r in hits.head(8).iterrows()]
            return {"multiple_matches": opts}
        return self._player_payload(hits.iloc[0])

    def get_team_cap(self, team: str) -> dict:
        abbr = self.resolve_team(team)
        if not abbr:
            return {"error": f"No team matching '{team}'"}
        df = self.roster[self.roster["team"].astype(str) == abbr] if "team" in self.roster.columns else self.roster.iloc[0:0]
        space = team_cap_space(self.roster, abbr)
        top = []
        if "apy" in df.columns:
            for _, r in df.sort_values("apy", ascending=False, na_position="last").head(8).iterrows():
                top.append({"name": r.get("player_name"), "position": r.get("position"), "salary_cap_m": _salary(r)})
        return {
            "team": abbr,
            "salary_cap_m": NFL_SALARY_CAP,
            "cap_space_m": space,
            "cap_used_m": round(NFL_SALARY_CAP - space, 2),
            "top_contracts": top,
        }

    def get_team_roster(self, team: str) -> dict:
        abbr = self.resolve_team(team)
        if not abbr:
            return {"error": f"No team matching '{team}'"}
        df = self.roster[self.roster["team"].astype(str) == abbr] if "team" in self.roster.columns else self.roster.iloc[0:0]
        players = [{"name": r.get("player_name"), "position": r.get("position"),
                    "age": r.get("age"), "salary_cap_m": _salary(r)}
                   for _, r in df.iterrows()]
        return {"team": abbr, "count": len(players), "players": players}

    def evaluate_trade(self, team_a, team_b, players_from_a=None, players_from_b=None,
                       picks_from_a=None, picks_from_b=None) -> dict:
        a = self.resolve_team(team_a)
        b = self.resolve_team(team_b)
        if not a or not b:
            return {"error": f"Could not resolve teams: {team_a!r}, {team_b!r}"}

        def ids(team_abbr, names):
            out, missing = [], []
            for n in (names or []):
                hits = self._find_players(n, team_abbr)
                if hits.empty:
                    missing.append(n)
                else:
                    out.append(hits.iloc[0]["gsis_id"])
            return out, missing

        send_a, miss_a = ids(a, players_from_a)
        send_b, miss_b = ids(b, players_from_b)
        if miss_a or miss_b:
            return {"error": "Players not found", "missing": {a: miss_a, b: miss_b}}

        result = _evaluate_trade(self.roster, a, b, send_a, send_b)
        va = picks_value(picks_from_a or [])
        vb = picks_value(picks_from_b or [])
        result["pick_value"] = {a: va, b: vb}
        result["picks_sent"] = {a: picks_from_a or [], b: picks_from_b or []}
        result["pick_scale"] = "Jimmy Johnson"
        return result

    # -- dispatch --
    def run(self, name: str, args: dict) -> dict:
        args = args or {}
        try:
            if name == "list_teams":
                return self.list_teams()
            if name == "get_player":
                return self.get_player(**args)
            if name == "get_team_cap":
                return self.get_team_cap(**args)
            if name == "get_team_roster":
                return self.get_team_roster(**args)
            if name == "evaluate_trade":
                return self.evaluate_trade(**args)
            return {"error": f"Unknown tool {name}"}
        except Exception as e:  # never crash the chat on a bad tool call
            return {"error": f"{type(e).__name__}: {e}"}
