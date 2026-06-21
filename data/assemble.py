"""
Assemble per-team roster tables for display.

NFL: ESPN live rosters (current, no stale-season issues) merged with
     OverTheCap contract data by player name for salary context.
NBA: nba_api rosters merged with league-wide player stats.
"""

import pandas as pd

from data import fetch_stats as nba_data
from data import nfl_fetch as nfl_data
from data import espn_nfl


def _merge_contracts_by_name(rosters: pd.DataFrame) -> pd.DataFrame:
    """
    Attach OverTheCap APY to the ESPN roster by matching player names.

    gsis_id is not available from ESPN, so we join on normalised full name.
    The match is case-insensitive and strips whitespace. Where a name
    appears more than once in contracts we keep the highest APY (most
    recent/biggest deal).
    """
    try:
        contracts = nfl_data.get_contracts()
    except Exception:
        rosters["apy"] = float("nan")
        return rosters

    if contracts.empty or "apy" not in contracts.columns:
        rosters["apy"] = float("nan")
        return rosters

    name_col = next((c for c in ("player", "player_name") if c in contracts.columns), None)
    if name_col is None:
        rosters["apy"] = float("nan")
        return rosters

    ctdf = contracts[[name_col, "apy"]].copy()
    ctdf["_key"] = ctdf[name_col].astype(str).str.strip().str.lower()
    ctdf = ctdf.sort_values("apy", ascending=False).drop_duplicates("_key", keep="first")

    rosters["_key"] = rosters["player_name"].astype(str).str.strip().str.lower()
    rosters = rosters.merge(ctdf[["_key", "apy"]], on="_key", how="left")
    rosters = rosters.drop(columns=["_key"])
    return rosters


def build_nfl_roster() -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Live NFL roster from ESPN merged with OverTheCap salary by name.
    Returns (roster_df, teams_df).
    """
    teams_df = espn_nfl.get_teams()
    rosters = espn_nfl.get_all_rosters(teams_df)

    if rosters.empty:
        return rosters, teams_df

    rosters = _merge_contracts_by_name(rosters)
    return rosters, teams_df


def build_nba_roster() -> tuple[pd.DataFrame, pd.DataFrame]:
    teams = nba_data.get_teams()
    players = nba_data.fetch_league_players()
    rows = []
    for _, t in teams.iterrows():
        try:
            roster = nba_data.get_team_roster(int(t["id"]))
        except Exception:
            continue
        for _, r in roster.iterrows():
            rows.append({
                "PLAYER_ID": r.get("PLAYER_ID"),
                "position": r.get("POSITION"),
                "team_abbr": t["abbreviation"],
                "NUM": r.get("NUM"),
                "EXP": r.get("EXP"),
            })
    posdf = pd.DataFrame(rows)
    if posdf.empty or players.empty:
        return pd.DataFrame(), teams
    merged = players.merge(posdf, on="PLAYER_ID", how="inner")
    return merged, teams
