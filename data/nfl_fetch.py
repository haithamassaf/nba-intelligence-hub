"""
Fetch live NFL stats from the nflverse data repositories via nflreadpy.

nflreadpy returns Polars DataFrames; we convert to pandas to match the rest
of the codebase. Data is sourced from nflverse GitHub releases (no API key).
"""

import os
import pandas as pd
import nflreadpy as nfl

from config.settings import NFL_SEASON


def _season() -> int:
    """
    Resolve the season to load.

    Uses NFL_SEASON from config/env if set, otherwise nflreadpy's
    current-season helper, which advances automatically once the next
    season kicks off.
    """
    if NFL_SEASON:
        try:
            return int(NFL_SEASON)
        except (TypeError, ValueError):
            pass
    return int(nfl.get_current_season())


def _to_pandas(df) -> pd.DataFrame:
    """nflreadpy returns Polars; normalize to pandas."""
    if isinstance(df, pd.DataFrame):
        return df
    try:
        return df.to_pandas()
    except AttributeError:
        return pd.DataFrame(df)


# ── Players ──────────────────────────────────────────────────────────

def get_player_season_stats(season: int | None = None) -> pd.DataFrame:
    """
    Season-aggregated regular-season player stats (one row per player).

    Includes passing, rushing, and receiving totals plus fantasy points.
    """
    season = season or _season()
    df = nfl.load_player_stats(seasons=[season], summary_level="reg")
    return _to_pandas(df)


# ── Teams / Standings ────────────────────────────────────────────────

def get_team_meta() -> pd.DataFrame:
    """Team metadata: abbreviation, name, conference, division, colors."""
    return _to_pandas(nfl.load_teams())


def get_schedules(season: int | None = None) -> pd.DataFrame:
    """Game schedule + results for the season (used to compute standings)."""
    season = season or _season()
    return _to_pandas(nfl.load_schedules(seasons=[season]))


def get_team_season_stats(season: int | None = None) -> pd.DataFrame:
    """Season-aggregated regular-season team stats (offense/defense)."""
    season = season or _season()
    df = nfl.load_team_stats(seasons=[season], summary_level="reg")
    return _to_pandas(df)


# ── Convenience: fetch everything ────────────────────────────────────

def fetch_all() -> dict[str, pd.DataFrame]:
    """
    Pull all core NFL datasets in one call.

    Returns a dict keyed by dataset name. Any dataset that fails to load
    comes back as an empty DataFrame so the rest of the pipeline still runs.
    """
    season = _season()
    print(f"Fetching NFL data for the {season} season...")

    out: dict[str, pd.DataFrame] = {}

    print("Fetching player season stats...")
    try:
        out["player_stats"] = get_player_season_stats(season)
    except Exception as e:
        print(f"  player stats failed: {e}")
        out["player_stats"] = pd.DataFrame()

    print("Fetching schedules...")
    try:
        out["schedules"] = get_schedules(season)
    except Exception as e:
        print(f"  schedules failed: {e}")
        out["schedules"] = pd.DataFrame()

    print("Fetching team metadata...")
    try:
        out["teams"] = get_team_meta()
    except Exception as e:
        print(f"  team metadata failed: {e}")
        out["teams"] = pd.DataFrame()

    print("Done.")
    return out


if __name__ == "__main__":
    datasets = fetch_all()
    for name, df in datasets.items():
        print(f"\n{'='*60}")
        print(f"  {name}  ({len(df)} rows)")
        print(f"{'='*60}")
        if not df.empty:
            print(df.head(5).to_string(index=False))
