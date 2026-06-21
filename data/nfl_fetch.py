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
from data.rookie_scale import MIN_VALID_APY, MAX_VALID_APY


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


def _clean_apy(series) -> pd.Series:
    """APY in $M with out-of-range values (feed errors) set to NaN."""
    apy = pd.to_numeric(series, errors="coerce")
    return apy.where((apy >= MIN_VALID_APY) & (apy <= MAX_VALID_APY))


def get_contracts() -> pd.DataFrame:
    """
    Active player contracts from OverTheCap (apy in $M, keyed by gsis_id).

    APY values outside the sane range are treated as feed errors and dropped, so
    a bad number can never reach the roster. For each player we keep the most
    recent still-valid contract, which prevents a stale or restructured row from
    overriding the current one. Rows without a gsis_id are dropped because they
    cannot be joined reliably.
    """
    df = _pd(nfl.load_contracts())
    if df.empty:
        return df
    if "is_active" in df.columns:
        df = df[df["is_active"] == True]  # noqa: E712
    keep = [c for c in ("player", "position", "team", "gsis_id", "apy", "guaranteed",
                        "value", "years", "year_signed") if c in df.columns]
    df = df[keep].copy()

    if "apy" in df.columns:
        df["apy"] = _clean_apy(df["apy"])
        df = df[df["apy"].notna()]          # drop rows whose APY failed validation

    if "gsis_id" in df.columns:
        df = df[df["gsis_id"].notna()]      # a null id cannot be joined reliably
        sort_cols = [c for c in ("year_signed", "apy") if c in df.columns]
        if sort_cols:
            df = df.sort_values(sort_cols, ascending=False)
        df = df.drop_duplicates("gsis_id", keep="first")

    return df.reset_index(drop=True)


def get_team_meta() -> pd.DataFrame:
    return _pd(nfl.load_teams())


def get_player_history(start_year: int, end_year: int) -> pd.DataFrame:
    """Season-aggregated player stats across a range of seasons (for compare)."""
    years = list(range(int(start_year), int(end_year) + 1))
    return _pd(nfl.load_player_stats(seasons=years, summary_level="reg"))


if __name__ == "__main__":
    print("stats season:", stats_season(), "| roster season:", roster_season())
    r = get_rosters()
    print("rosters:", len(r), list(r.columns)[:8])
