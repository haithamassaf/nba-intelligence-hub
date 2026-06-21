"""
NFL data from nflverse via nflreadpy (no API key).

Rosters come from the current league year (so rookies are included); production
stats come from the most recent completed season; contracts (APY) come from
OverTheCap and power the trade simulator. nflreadpy returns Polars; everything
is converted to pandas.
"""

import datetime
import pandas as pd
import nflreadpy as nfl

from config.settings import NFL_STATS_SEASON, NFL_ROSTER_SEASON


def stats_season() -> int:
    if NFL_STATS_SEASON:
        return int(NFL_STATS_SEASON)
    try:
        return int(nfl.get_current_season())
    except Exception:
        t = datetime.date.today()
        return t.year if t.month >= 9 else t.year - 1


def roster_season() -> int:
    if NFL_ROSTER_SEASON:
        return int(NFL_ROSTER_SEASON)
    t = datetime.date.today()
    return t.year if t.month >= 3 else t.year - 1   # league year opens mid-March


def _pd(df) -> pd.DataFrame:
    if isinstance(df, pd.DataFrame):
        return df
    try:
        return df.to_pandas()
    except AttributeError:
        return pd.DataFrame(df)


def get_rosters(season: int | None = None) -> pd.DataFrame:
    """Current rosters incl. rookies: player, position, age, exp, college, status."""
    return _pd(nfl.load_rosters(seasons=[season or roster_season()]))


def get_player_season_stats(season: int | None = None) -> pd.DataFrame:
    """Season-aggregated regular-season player stats (one row per player)."""
    return _pd(nfl.load_player_stats(seasons=[season or stats_season()], summary_level="reg"))


def get_contracts() -> pd.DataFrame:
    """Active player contracts from OverTheCap (apy, guaranteed, gsis_id)."""
    df = _pd(nfl.load_contracts())
    if df.empty:
        return df
    if "is_active" in df.columns:
        df = df[df["is_active"] == True]  # noqa: E712
    keep = [c for c in ("player", "position", "team", "gsis_id", "apy", "guaranteed",
                        "value", "years", "year_signed") if c in df.columns]
    df = df[keep]
    if "gsis_id" in df.columns:
        sort_col = "year_signed" if "year_signed" in df.columns else "apy"
        df = df.sort_values(sort_col, ascending=False).drop_duplicates("gsis_id", keep="first")
    return df.reset_index(drop=True)


def get_team_meta() -> pd.DataFrame:
    return _pd(nfl.load_teams())


if __name__ == "__main__":
    print("stats season:", stats_season(), "| roster season:", roster_season())
    r = get_rosters()
    print("rosters:", len(r), list(r.columns)[:8])
