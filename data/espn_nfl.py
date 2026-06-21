"""
NFL roster and team data from ESPN's public API.

No API key required. Rosters are live (what ESPN shows today), so there are no
stale-season problems. We loop all 32 team IDs to build a league-wide table.

ESPN team IDs are stable integers 1-34 (with gaps). We use the /teams endpoint
to get the authoritative list rather than hardcoding IDs.

Salary/contract data still comes from nflverse OverTheCap, keyed by player name
since ESPN does not expose salary figures.
"""

import time
import requests
import pandas as pd

_BASE = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"
_TIMEOUT = 10
_DELAY = 0.25   # seconds between team roster calls to be polite

# ESPN position groups in the roster response
_POS_GROUPS = ("quarterback", "runningBack", "wideReceiver", "tightEnd",
               "offensiveLine", "defensiveLine", "linebacker",
               "defensiveBack", "specialTeams")


def _get(url: str) -> dict:
    r = requests.get(url, timeout=_TIMEOUT, headers={"User-Agent": "nfl-roster-app/1.0"})
    r.raise_for_status()
    return r.json()


def get_teams() -> pd.DataFrame:
    """All 32 NFL teams with ESPN id, abbreviation, and full name."""
    data = _get(f"{_BASE}/teams?limit=32")
    rows = []
    for item in data.get("sports", [{}])[0].get("leagues", [{}])[0].get("teams", []):
        t = item.get("team", {})
        rows.append({
            "espn_id": t.get("id"),
            "team_abbr": t.get("abbreviation"),
            "team_name": t.get("displayName"),
            "short_name": t.get("shortDisplayName"),
            "location": t.get("location"),
        })
    return pd.DataFrame(rows)


def _parse_athlete(athlete: dict, team_abbr: str, team_name: str) -> dict:
    """Flatten one ESPN athlete dict into a roster row."""
    pos = athlete.get("position", {})
    stats = {}
    for s in athlete.get("statistics", {}).get("splits", {}).get("categories", []):
        for stat in s.get("stats", []):
            stats[stat.get("abbreviation", "")] = stat.get("value")

    return {
        "player_name": athlete.get("fullName", ""),
        "first_name": athlete.get("firstName", ""),
        "last_name": athlete.get("lastName", ""),
        "espn_id": athlete.get("id"),
        "team": team_abbr,
        "team_name": team_name,
        "position": pos.get("abbreviation", ""),
        "position_name": pos.get("displayName", ""),
        "jersey": athlete.get("jersey"),
        "age": athlete.get("age"),
        "experience": athlete.get("experience", {}).get("years"),
        "status": athlete.get("status", {}).get("name", "Active"),
        "height": athlete.get("displayHeight"),
        "weight": athlete.get("displayWeight"),
        "college": athlete.get("college", {}).get("name"),
    }


def get_team_roster(espn_id: str | int, team_abbr: str, team_name: str) -> list[dict]:
    """Roster rows for one team from ESPN."""
    try:
        data = _get(f"{_BASE}/teams/{espn_id}/roster")
    except Exception:
        return []
    rows = []
    for group in data.get("athletes", []):
        for athlete in group.get("items", []):
            rows.append(_parse_athlete(athlete, team_abbr, team_name))
    return rows


def get_all_rosters(teams_df: pd.DataFrame | None = None) -> pd.DataFrame:
    """
    League-wide roster table from ESPN. Pulls all 32 teams sequentially.
    Each row is one player with name, team, position, age, experience, status.
    """
    if teams_df is None or teams_df.empty:
        teams_df = get_teams()

    all_rows = []
    for _, t in teams_df.iterrows():
        rows = get_team_roster(t["espn_id"], t["team_abbr"], t["team_name"])
        all_rows.extend(rows)
        time.sleep(_DELAY)

    df = pd.DataFrame(all_rows)
    if df.empty:
        return df

    # Keep only active players (drop PUP, injured reserve listed as non-active etc.)
    if "status" in df.columns:
        df = df[~df["status"].str.lower().isin(["non football injury", "physically unable"])]

    return df.reset_index(drop=True)
