"""
Assemble per-team roster tables for display and trades. No grading: rosters are
merged with season stats (and, for the NFL, OverTheCap APY) and returned as-is.
"""

import pandas as pd

from data import fetch_stats as nba_data
from data import nfl_fetch as nfl_data
from data.rookie_scale import (
    estimate_rookie_apy,
    MIN_VALID_APY,
    MAX_VALID_APY,
    ROOKIE_APY_CEILING,
)


def _draft_pick(row):
    for c in ("draft_number", "draft_ovr", "draft_pick", "entry_draft_pick"):
        if c in row and pd.notna(row.get(c)):
            return row.get(c)
    return None


def _draft_round(row):
    for c in ("draft_round", "entry_draft_round"):
        if c in row and pd.notna(row.get(c)):
            return row.get(c)
    return None


def _validate_and_fill_apy(rosters: pd.DataFrame) -> pd.DataFrame:
    """
    Validate merged APY and fill rookies with a slotted estimate.

    Any APY outside the sane range, or a rookie APY above the rookie ceiling, is
    cleared so it can never be shown or used in the cap math. Rookies (no accrued
    seasons) left without a valid APY get an estimate from their draft slot. The
    apy_status column records where each value came from: verified, rookie
    estimate, or unavailable.
    """
    if "apy" not in rosters.columns:
        rosters["apy"] = float("nan")

    apy = pd.to_numeric(rosters["apy"], errors="coerce")

    if "years_exp" in rosters.columns:
        exp = pd.to_numeric(rosters["years_exp"], errors="coerce")
    else:
        exp = pd.Series(index=rosters.index, dtype="float64")
    is_rookie = exp.fillna(99) <= 0

    bad = (apy < MIN_VALID_APY) | (apy > MAX_VALID_APY) | (is_rookie & (apy > ROOKIE_APY_CEILING))
    apy = apy.where(~bad)

    status = pd.Series("verified", index=rosters.index)
    status = status.where(apy.notna(), "unavailable")

    need_est = apy.isna() & is_rookie
    if need_est.any():
        est = rosters.loc[need_est].apply(
            lambda r: estimate_rookie_apy(_draft_pick(r), _draft_round(r)), axis=1
        )
        apy.loc[need_est] = pd.to_numeric(est, errors="coerce")
        status.loc[need_est] = "rookie estimate"

    rosters["apy"] = apy.round(2)
    rosters["apy_status"] = status
    return rosters


def build_nfl_roster() -> tuple[pd.DataFrame, pd.DataFrame]:
    rosters = nfl_data.get_rosters()
    if rosters.empty:
        return rosters, pd.DataFrame()

    if "player_name" not in rosters.columns and "full_name" in rosters.columns:
        rosters = rosters.rename(columns={"full_name": "player_name"})

    # nflverse rosters carry a birth date but not age; derive it (column name varies).
    if "age" not in rosters.columns:
        bd_col = next((c for c in ["birth_date", "birthdate", "birth_dt", "dob"] if c in rosters.columns), None)
        if bd_col:
            bd = pd.to_datetime(rosters[bd_col], errors="coerce")
            rosters["age"] = ((pd.Timestamp.today() - bd).dt.days / 365.25).round(1)
        elif "birth_year" in rosters.columns:
            yr = pd.to_numeric(rosters["birth_year"], errors="coerce")
            rosters["age"] = (pd.Timestamp.today().year - yr).round(1)

    stats = nfl_data.get_player_season_stats()
    if not stats.empty and "player_id" in stats.columns and "gsis_id" in rosters.columns:
        stats = stats.rename(columns={"player_id": "gsis_id"})
        cols = [c for c in stats.columns if c not in rosters.columns or c == "gsis_id"]
        rosters = rosters.merge(stats[cols], on="gsis_id", how="left")

    contracts = nfl_data.get_contracts()
    if not contracts.empty and "gsis_id" in contracts.columns and "gsis_id" in rosters.columns and "apy" in contracts.columns:
        rosters = rosters.merge(contracts[["gsis_id", "apy"]].drop_duplicates("gsis_id"), on="gsis_id", how="left")
    else:
        rosters["apy"] = float("nan")

    rosters = _validate_and_fill_apy(rosters)

    return rosters, nfl_data.get_team_meta()


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
