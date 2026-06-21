"""
Fetch NFL data from the nflverse repositories via nflreadpy (no API key).

Two seasons matter:
  - stats season: the most recent completed season, for grading veterans.
  - roster season: the current league year, whose rosters include rookies.

nflreadpy returns Polars; everything is converted to pandas.
"""

import datetime
import pandas as pd
import nflreadpy as nfl

from config.settings import NFL_STATS_SEASON, NFL_ROSTER_SEASON, NFL_DRAFT_YEAR


# ── Season resolvers ─────────────────────────────────────────────────

def stats_season() -> int:
    """Most recent completed season (for player stats / veteran grading)."""
    if NFL_STATS_SEASON:
        return int(NFL_STATS_SEASON)
    try:
        return int(nfl.get_current_season())
    except Exception:
        t = datetime.date.today()
        return t.year if t.month >= 9 else t.year - 1


def roster_season() -> int:
    """Current league year (rosters include the latest rookie class)."""
    if NFL_ROSTER_SEASON:
        return int(NFL_ROSTER_SEASON)
    t = datetime.date.today()
    # NFL league year opens mid-March; before then the prior year is current.
    return t.year if t.month >= 3 else t.year - 1


def draft_year() -> int:
    if NFL_DRAFT_YEAR:
        return int(NFL_DRAFT_YEAR)
    return roster_season()


def _pd(df) -> pd.DataFrame:
    if isinstance(df, pd.DataFrame):
        return df
    try:
        return df.to_pandas()
    except AttributeError:
        return pd.DataFrame(df)


# ── Production (completed season) ────────────────────────────────────

def get_player_season_stats(season: int | None = None) -> pd.DataFrame:
    """Season-aggregated regular-season player stats (one row per player)."""
    season = season or stats_season()
    return _pd(nfl.load_player_stats(seasons=[season], summary_level="reg"))


# ── Advanced / efficiency layers (completed season) ──────────────────

def get_nextgen(stat_type: str, season: int | None = None) -> pd.DataFrame:
    """Next Gen Stats. stat_type: passing | receiving | rushing. week 0 = season."""
    season = season or stats_season()
    return _pd(nfl.load_nextgen_stats(seasons=[season], stat_type=stat_type))


def get_pfr_advstats(stat_type: str, season: int | None = None) -> pd.DataFrame:
    """Pro Football Reference advanced stats. stat_type: pass | rush | rec | def."""
    season = season or stats_season()
    return _pd(nfl.load_pfr_advstats(seasons=[season], stat_type=stat_type))


def get_qbr(season: int | None = None) -> pd.DataFrame:
    """ESPN QBR for quarterbacks."""
    season = season or stats_season()
    return _pd(nfl.load_espn_qbr(seasons=[season]))


def get_snap_counts(season: int | None = None) -> pd.DataFrame:
    """Snap counts (role / usage), sourced from PFR."""
    season = season or stats_season()
    return _pd(nfl.load_snap_counts(seasons=[season]))


# ── Rosters, bios, depth charts (current league year) ────────────────

def get_rosters(season: int | None = None) -> pd.DataFrame:
    """Current rosters incl. rookies: player, position, age, exp, college, status."""
    season = season or roster_season()
    return _pd(nfl.load_rosters(seasons=[season]))


def get_depth_charts(season: int | None = None) -> pd.DataFrame:
    season = season or roster_season()
    return _pd(nfl.load_depth_charts(seasons=[season]))


def get_players() -> pd.DataFrame:
    """Player bios: height, weight, birthdate, college, draft info, headshot."""
    return _pd(nfl.load_players())


# ── Rookie inputs (draft capital + athletic testing) ─────────────────

def get_draft_picks(year: int | None = None) -> pd.DataFrame:
    year = year or draft_year()
    return _pd(nfl.load_draft_picks(seasons=[year]))


def get_combine(year: int | None = None) -> pd.DataFrame:
    year = year or draft_year()
    return _pd(nfl.load_combine(seasons=[year]))


# ── Team meta / schedule ─────────────────────────────────────────────

def get_team_meta() -> pd.DataFrame:
    return _pd(nfl.load_teams())


def get_schedules(season: int | None = None) -> pd.DataFrame:
    season = season or stats_season()
    return _pd(nfl.load_schedules(seasons=[season]))


# ── Convenience ──────────────────────────────────────────────────────

def _safe(label, fn):
    try:
        return fn()
    except Exception as e:
        print(f"  {label} failed: {e}")
        return pd.DataFrame()


def fetch_grading_inputs() -> dict[str, pd.DataFrame]:
    """Everything the grading engine needs. Failures degrade to empty frames."""
    s, r, d = stats_season(), roster_season(), draft_year()
    print(f"NFL: stats={s}, rosters={r}, draft={d}")

    return {
        "rosters": _safe("rosters", lambda: get_rosters(r)),
        "players": _safe("players", get_players),
        "depth_charts": _safe("depth_charts", lambda: get_depth_charts(r)),
        "player_stats": _safe("player_stats", lambda: get_player_season_stats(s)),
        "ngs_passing": _safe("ngs_passing", lambda: get_nextgen("passing", s)),
        "ngs_receiving": _safe("ngs_receiving", lambda: get_nextgen("receiving", s)),
        "ngs_rushing": _safe("ngs_rushing", lambda: get_nextgen("rushing", s)),
        "pfr_pass": _safe("pfr_pass", lambda: get_pfr_advstats("pass", s)),
        "pfr_rush": _safe("pfr_rush", lambda: get_pfr_advstats("rush", s)),
        "pfr_rec": _safe("pfr_rec", lambda: get_pfr_advstats("rec", s)),
        "pfr_def": _safe("pfr_def", lambda: get_pfr_advstats("def", s)),
        "qbr": _safe("qbr", lambda: get_qbr(s)),
        "snaps": _safe("snaps", lambda: get_snap_counts(s)),
        "draft": _safe("draft", lambda: get_draft_picks(d)),
        "combine": _safe("combine", lambda: get_combine(d)),
        "teams": _safe("teams", get_team_meta),
        "schedules": _safe("schedules", lambda: get_schedules(s)),
    }


if __name__ == "__main__":
    data = fetch_grading_inputs()
    for k, v in data.items():
        print(f"{k:16s} {len(v):>5} rows  {list(v.columns)[:6]}")
