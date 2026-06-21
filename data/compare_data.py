"""
Build per-season (and career) stat splits for player comparison.

Pure transforms over already-fetched data, kept separate so they can be tested
without hitting the network:
  - nba_splits: from nba_api PlayerCareerStats result frames.
  - nfl_splits: from a multi-season nflverse player_stats frame.
"""

import pandas as pd

NBA_KEYS = ["PTS", "REB", "AST", "STL", "BLK", "TOV", "FG_PCT", "FG3_PCT", "FT_PCT", "MIN", "GP"]
NFL_KEYS = ["passing_yards", "passing_tds", "interceptions", "rushing_yards", "rushing_tds",
            "receptions", "receiving_yards", "receiving_tds", "def_sacks", "def_tackles"]


def nba_splits(season_df: pd.DataFrame, career_df: pd.DataFrame) -> dict:
    """season_df: SeasonTotalsRegularSeason (PerGame). career_df: CareerTotals."""
    out = {}
    if season_df is not None and not season_df.empty:
        for _, row in season_df.iterrows():
            season = str(row.get("SEASON_ID"))
            out[season] = {k: row.get(k) for k in NBA_KEYS}
    if career_df is not None and not career_df.empty:
        crow = career_df.iloc[0]
        out["Career"] = {k: crow.get(k) for k in NBA_KEYS}
    return out


def nfl_splits(history_df: pd.DataFrame, gsis_id: str, id_col: str = "player_id") -> dict:
    """One entry per season the player appears in, plus a summed Career entry."""
    out = {}
    if history_df is None or history_df.empty or id_col not in history_df.columns:
        return out
    p = history_df[history_df[id_col].astype(str) == str(gsis_id)]
    if p.empty:
        return out
    keys = [k for k in NFL_KEYS if k in p.columns]
    for _, row in p.sort_values("season").iterrows():
        if pd.isna(row.get("season")):
            continue
        out[str(int(row["season"]))] = {k: row.get(k) for k in keys}
    out["Career"] = {k: float(pd.to_numeric(p[k], errors="coerce").fillna(0).sum()) for k in keys}
    return out


def season_options(splits_a: dict, splits_b: dict) -> list[str]:
    """Union of seasons from both players (Career first, then newest seasons)."""
    seasons = {s for s in list(splits_a) + list(splits_b) if s != "Career"}
    ordered = sorted(seasons, reverse=True)
    return (["Career"] if ("Career" in splits_a or "Career" in splits_b) else []) + ordered
