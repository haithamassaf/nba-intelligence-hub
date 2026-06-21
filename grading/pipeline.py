"""
Shared grading pipeline used by both the Streamlit app and the API.

These functions do the live fetch + grade and return a graded player table plus
a team-meta frame. Callers add their own caching (st.cache_data / lru_cache).
"""

import pandas as pd

from data import fetch_stats as nba_data
from data import nfl_fetch as nfl_data
from data import cfbd_fetch
from grading.nba_grades import grade_players as nba_grade, bucket_for
from grading.nfl_grades import grade_all as nfl_grade_all


def build_nfl_graded() -> tuple[pd.DataFrame, pd.DataFrame]:
    inputs = nfl_data.fetch_grading_inputs()
    graded = nfl_grade_all(inputs, cfbd_fetch.get_player_season_wide())
    if not graded.empty:
        present = [c for c in ("offense_snaps", "defense_snaps", "st_snaps") if c in graded.columns]
        if present:
            wt = pd.Series(0.0, index=graded.index)
            for c in present:
                wt = wt + pd.to_numeric(graded[c], errors="coerce").fillna(0)
            graded["_wt"] = wt
        else:
            graded["_wt"] = 0.0
        # Attach OverTheCap APY (for the trade simulator) by gsis_id.
        contracts = inputs.get("contracts", pd.DataFrame())
        if not contracts.empty and "gsis_id" in contracts.columns and "gsis_id" in graded.columns and "apy" in contracts.columns:
            graded = graded.merge(contracts[["gsis_id", "apy"]].drop_duplicates("gsis_id"), on="gsis_id", how="left")
        else:
            graded["apy"] = float("nan")
    return graded, inputs.get("teams", pd.DataFrame())


def build_nba_graded() -> tuple[pd.DataFrame, pd.DataFrame]:
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
    posdf["bucket"] = posdf["position"].map(bucket_for)
    merged = players.merge(posdf, on="PLAYER_ID", how="inner")
    graded = nba_grade(merged)
    gp = pd.to_numeric(graded.get("GP"), errors="coerce").fillna(0)
    mn = pd.to_numeric(graded.get("MIN"), errors="coerce").fillna(0)
    graded["_wt"] = gp * mn
    return graded, teams
