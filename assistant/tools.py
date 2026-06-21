"""
Tools for the NFL AI assistant.

The LLM uses these to pull live data instead of guessing. The roster comes
from ESPN (current, live). Contract/cap details for trade questions are fetched
from OverTheCap via nflverse. General NFL knowledge comes from Claude itself.
"""

import json
import requests
import pandas as pd

from config.settings import NFL_SALARY_CAP
from trade.picks import picks_value

_OTC_BASE = "https://overthecap.com"
_ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"

TOOL_SCHEMAS = [
    {
        "name": "list_teams",
        "description": "List all 32 NFL teams with abbreviation and full name.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_player_info",
        "description": "Look up a player's current team, position, age, experience, and college from the live ESPN roster. Use this for any question about a specific player's current status.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Player full name or partial name."},
            },
            "required": ["name"],
        },
    },
    {
        "name": "get_team_roster",
        "description": "Get a team's full current roster from ESPN. Returns all players with position, age, and experience.",
        "input_schema": {
            "type": "object",
            "properties": {
                "team": {"type": "string", "description": "Team abbreviation (e.g. SF, DAL) or city/nickname."},
            },
            "required": ["team"],
        },
    },
    {
        "name": "get_contract_info",
        "description": "Get a player's contract details including total value, APY, and guaranteed money from OverTheCap. Use this for ANY trade question to get accurate salary figures before evaluating cap legality.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Player full name."},
            },
            "required": ["name"],
        },
    },
    {
        "name": "get_team_cap_space",
        "description": "Get a team's current salary cap space and top contracts from OverTheCap data. Use this before evaluating trade cap legality.",
        "input_schema": {
            "type": "object",
            "properties": {
                "team": {"type": "string", "description": "Team abbreviation or name."},
            },
            "required": ["team"],
        },
    },
    {
        "name": "evaluate_trade_cap",
        "description": "Check if a proposed trade is cap legal under the NFL top-51 rule. Provide player names and their APYs (from get_contract_info), plus any draft picks. Returns cap legality and space remaining for both teams after the trade.",
        "input_schema": {
            "type": "object",
            "properties": {
                "team_a": {"type": "string"},
                "team_b": {"type": "string"},
                "players_from_a": {
                    "type": "array",
                    "items": {"type": "object", "properties": {"name": {"type": "string"}, "apy": {"type": "number"}}, "required": ["name", "apy"]},
                    "description": "Players team A sends with their APY in $M.",
                },
                "players_from_b": {
                    "type": "array",
                    "items": {"type": "object", "properties": {"name": {"type": "string"}, "apy": {"type": "number"}}, "required": ["name", "apy"]},
                    "description": "Players team B sends with their APY in $M.",
                },
                "picks_from_a": {"type": "array", "items": {"type": "string"}, "description": "Draft picks team A sends e.g. ['2027 1st']."},
                "picks_from_b": {"type": "array", "items": {"type": "string"}, "description": "Draft picks team B sends."},
            },
            "required": ["team_a", "team_b"],
        },
    },
]


class NFLTools:
    def __init__(self, roster_df: pd.DataFrame, teams_df: pd.DataFrame):
        self.roster = roster_df if roster_df is not None else pd.DataFrame()
        self.teams = teams_df if teams_df is not None else pd.DataFrame()
        self._contracts_cache = None

    def _contracts(self) -> pd.DataFrame:
        if self._contracts_cache is not None:
            return self._contracts_cache
        try:
            from data import nfl_fetch as nfl_data
            self._contracts_cache = nfl_data.get_contracts()
        except Exception:
            self._contracts_cache = pd.DataFrame()
        return self._contracts_cache

    def _resolve_team(self, q: str) -> str | None:
        q = str(q).strip()
        abbr_col = "team_abbr" if "team_abbr" in self.teams.columns else None
        name_col = "team_name" if "team_name" in self.teams.columns else None
        if not abbr_col:
            if "team" in self.roster.columns:
                codes = self.roster["team"].dropna().unique()
                for c in codes:
                    if q.upper() == str(c).upper():
                        return str(c)
            return None
        for _, t in self.teams.iterrows():
            if q.upper() == str(t[abbr_col]).upper():
                return str(t[abbr_col])
        for _, t in self.teams.iterrows():
            if q.lower() in str(t.get(name_col, "")).lower():
                return str(t[abbr_col])
            if q.lower() in str(t.get("short_name", "")).lower():
                return str(t[abbr_col])
            if q.lower() in str(t.get("location", "")).lower():
                return str(t[abbr_col])
        return None

    def _find_player(self, name: str) -> list[dict]:
        if self.roster.empty or "player_name" not in self.roster.columns:
            return []
        nm = name.strip().lower()
        exact = self.roster[self.roster["player_name"].str.lower() == nm]
        if not exact.empty:
            return exact.to_dict("records")
        partial = self.roster[self.roster["player_name"].str.lower().str.contains(nm, na=False)]
        return partial.head(5).to_dict("records")

    def list_teams(self) -> dict:
        if self.teams.empty:
            return {"error": "Teams data not loaded."}
        abbr_col = "team_abbr" if "team_abbr" in self.teams.columns else "team"
        name_col = "team_name" if "team_name" in self.teams.columns else abbr_col
        return {"teams": [{"abbr": str(r[abbr_col]), "name": str(r[name_col])} for _, r in self.teams.iterrows()]}

    def get_player_info(self, name: str) -> dict:
        hits = self._find_player(name)
        if not hits:
            return {"error": f"No player matching '{name}' found on any current roster."}
        if len(hits) > 1:
            return {"multiple_matches": [{"name": h.get("player_name"), "team": h.get("team"), "position": h.get("position")} for h in hits]}
        p = hits[0]
        return {
            "name": p.get("player_name"),
            "team": p.get("team"),
            "team_name": p.get("team_name"),
            "position": p.get("position"),
            "age": p.get("age"),
            "experience_years": p.get("experience"),
            "height": p.get("height"),
            "weight": p.get("weight"),
            "college": p.get("college"),
            "status": p.get("status"),
        }

    def get_team_roster(self, team: str) -> dict:
        abbr = self._resolve_team(team)
        if not abbr:
            return {"error": f"No team matching '{team}'."}
        if self.roster.empty or "team" not in self.roster.columns:
            return {"error": "Roster data not loaded."}
        df = self.roster[self.roster["team"] == abbr]
        players = [{"name": r.get("player_name"), "position": r.get("position"),
                    "age": r.get("age"), "experience": r.get("experience")}
                   for _, r in df.iterrows()]
        return {"team": abbr, "count": len(players), "players": players}

    def get_contract_info(self, name: str) -> dict:
        contracts = self._contracts()
        if contracts.empty:
            return {"error": "Contract data unavailable."}
        name_col = next((c for c in ("player", "player_name") if c in contracts.columns), None)
        if not name_col:
            return {"error": "Contract data has no name column."}
        nm = name.strip().lower()
        exact = contracts[contracts[name_col].astype(str).str.lower() == nm]
        if exact.empty:
            exact = contracts[contracts[name_col].astype(str).str.lower().str.contains(nm, na=False)]
        if exact.empty:
            return {"error": f"No contract found for '{name}'. Player may be on a rookie deal or unsigned."}
        row = exact.sort_values("apy", ascending=False).iloc[0]
        result = {"player": row.get(name_col), "apy_m": row.get("apy"), "salary_cap_figure_m": row.get("apy")}
        for col in ("value", "guaranteed", "years", "year_signed", "team"):
            if col in row and pd.notna(row.get(col)):
                result[col] = row.get(col)
        return result

    def get_team_cap_space(self, team: str) -> dict:
        abbr = self._resolve_team(team)
        if not abbr:
            return {"error": f"No team matching '{team}'."}
        contracts = self._contracts()
        if contracts.empty or "apy" not in contracts.columns:
            return {"error": "Contract data unavailable.", "team": abbr}
        team_col = next((c for c in ("team",) if c in contracts.columns), None)
        if team_col:
            team_contracts = contracts[contracts[team_col].astype(str).str.upper() == abbr.upper()]
        else:
            team_contracts = pd.DataFrame()
        if team_contracts.empty:
            return {"team": abbr, "note": "No contract data for this team. Cap figures may be unavailable.", "salary_cap_m": NFL_SALARY_CAP}
        apy_vals = pd.to_numeric(team_contracts["apy"], errors="coerce").dropna().sort_values(ascending=False)
        committed = float(apy_vals.head(51).sum())
        space = round(NFL_SALARY_CAP - committed, 2)
        name_col = next((c for c in ("player", "player_name") if c in team_contracts.columns), None)
        top = []
        if name_col:
            for _, r in team_contracts.sort_values("apy", ascending=False).head(10).iterrows():
                top.append({"player": r.get(name_col), "apy_m": r.get("apy")})
        return {
            "team": abbr,
            "salary_cap_m": NFL_SALARY_CAP,
            "cap_committed_m": round(committed, 2),
            "cap_space_m": space,
            "top_contracts": top,
        }

    def evaluate_trade_cap(self, team_a: str, team_b: str,
                           players_from_a=None, players_from_b=None,
                           picks_from_a=None, picks_from_b=None) -> dict:
        a = self._resolve_team(team_a)
        b = self._resolve_team(team_b)
        if not a or not b:
            return {"error": f"Could not resolve teams: '{team_a}', '{team_b}'"}

        cap_a = self.get_team_cap_space(a)
        cap_b = self.get_team_cap_space(b)

        apy_out_a = sum(p.get("apy", 0) for p in (players_from_a or []))
        apy_in_a = sum(p.get("apy", 0) for p in (players_from_b or []))
        apy_out_b = sum(p.get("apy", 0) for p in (players_from_b or []))
        apy_in_b = sum(p.get("apy", 0) for p in (players_from_a or []))

        space_a = cap_a.get("cap_space_m", 0)
        space_b = cap_b.get("cap_space_m", 0)

        new_space_a = round(space_a + apy_out_a - apy_in_a, 2)
        new_space_b = round(space_b + apy_out_b - apy_in_b, 2)

        legal_a = new_space_a >= 0
        legal_b = new_space_b >= 0

        va = picks_value(picks_from_a or [])
        vb = picks_value(picks_from_b or [])

        return {
            "trade_legal": legal_a and legal_b,
            team_a: {
                "sends": [p.get("name") for p in (players_from_a or [])] + (picks_from_a or []),
                "receives": [p.get("name") for p in (players_from_b or [])] + (picks_from_b or []),
                "apy_out_m": round(apy_out_a, 2),
                "apy_in_m": round(apy_in_a, 2),
                "cap_space_before_m": space_a,
                "cap_space_after_m": new_space_a,
                "cap_legal": legal_a,
                "pick_value_sent": va,
            },
            team_b: {
                "sends": [p.get("name") for p in (players_from_b or [])] + (picks_from_b or []),
                "receives": [p.get("name") for p in (players_from_a or [])] + (picks_from_a or []),
                "apy_out_m": round(apy_out_b, 2),
                "apy_in_m": round(apy_in_b, 2),
                "cap_space_before_m": space_b,
                "cap_space_after_m": new_space_b,
                "cap_legal": legal_b,
                "pick_value_sent": vb,
            },
            "pick_value_scale": "Jimmy Johnson",
            "note": "Cap check uses top-51 APY rule (NFL offseason standard).",
        }

    def run(self, name: str, args: dict) -> dict:
        args = args or {}
        try:
            if name == "list_teams":
                return self.list_teams()
            if name == "get_player_info":
                return self.get_player_info(**args)
            if name == "get_team_roster":
                return self.get_team_roster(**args)
            if name == "get_contract_info":
                return self.get_contract_info(**args)
            if name == "get_team_cap_space":
                return self.get_team_cap_space(**args)
            if name == "evaluate_trade_cap":
                return self.evaluate_trade_cap(**args)
            return {"error": f"Unknown tool: {name}"}
        except Exception as e:
            return {"error": f"{type(e).__name__}: {e}"}
