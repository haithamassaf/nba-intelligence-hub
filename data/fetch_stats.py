"""
Fetch NBA data from stats.nba.com via nba_api.

All functions return pandas DataFrames. A small delay between calls respects
the stats.nba.com rate limit. Grading uses the most recent completed season.
"""

import time
import pandas as pd
from nba_api.stats.endpoints import (
    CommonTeamRoster,
    PlayerCareerStats,
    LeagueDashPlayerStats,
    LeagueDashTeamStats,
    LeagueStandings,
)
from nba_api.stats.static import teams as _static_teams

from config.settings import NBA_STATS_SEASON, NBA_API_TIMEOUT

_DELAY = 0.6


def _pause():
    time.sleep(_DELAY)


# ── Team directory (no network) ──────────────────────────────────────

def get_teams() -> pd.DataFrame:
    """All 30 teams with id, abbreviation, full name, city. Static, no call."""
    return pd.DataFrame(_static_teams.get_teams())


# ── Players: base + advanced ─────────────────────────────────────────

def get_player_base_stats(season: str | None = None, per_mode: str = "PerGame") -> pd.DataFrame:
    """Traditional per-game stats: PTS/REB/AST/STL/BLK/TOV, shooting %, +/-, AGE."""
    season = season or NBA_STATS_SEASON
    data = LeagueDashPlayerStats(
        season=season,
        per_mode_detailed=per_mode,
        measure_type_detailed_defense="Base",
        season_type_all_star="Regular Season",
        timeout=NBA_API_TIMEOUT,
    )
    _pause()
    return data.league_dash_player_stats.get_data_frame()


def get_player_advanced_stats(season: str | None = None) -> pd.DataFrame:
    """Advanced stats: TS%, USG%, AST%, REB%, OFF/DEF/NET rating, PIE, PACE."""
    season = season or NBA_STATS_SEASON
    data = LeagueDashPlayerStats(
        season=season,
        per_mode_detailed="PerGame",
        measure_type_detailed_defense="Advanced",
        season_type_all_star="Regular Season",
        timeout=NBA_API_TIMEOUT,
    )
    _pause()
    return data.league_dash_player_stats.get_data_frame()


def get_team_roster(team_id: int, season: str | None = None) -> pd.DataFrame:
    """Current roster for one team: player, position, height, weight, age, exp."""
    season = season or NBA_STATS_SEASON
    data = CommonTeamRoster(team_id=team_id, season=season, timeout=NBA_API_TIMEOUT)
    _pause()
    return data.common_team_roster.get_data_frame()


# ── Teams ────────────────────────────────────────────────────────────

def get_team_standings(season: str | None = None) -> pd.DataFrame:
    season = season or NBA_STATS_SEASON
    data = LeagueStandings(season=season, season_type="Regular Season", timeout=NBA_API_TIMEOUT)
    _pause()
    return data.standings.get_data_frame()


def get_team_stats_advanced(season: str | None = None) -> pd.DataFrame:
    """Advanced team stats: OFF/DEF/NET rating, PACE (used for context + SOS)."""
    season = season or NBA_STATS_SEASON
    data = LeagueDashTeamStats(
        season=season,
        measure_type_detailed_defense="Advanced",
        season_type_all_star="Regular Season",
        timeout=NBA_API_TIMEOUT,
    )
    _pause()
    return data.league_dash_team_stats.get_data_frame()


# ── Career stats (for player compare) ────────────────────────────────

def get_player_career(player_id: int):
    """Per-game season splits + career totals for one player (regular season)."""
    data = PlayerCareerStats(player_id=player_id, per_mode36="PerGame", timeout=NBA_API_TIMEOUT)
    _pause()
    return (data.season_totals_regular_season.get_data_frame(),
            data.career_totals_regular_season.get_data_frame())


# ── Convenience ──────────────────────────────────────────────────────

def fetch_league_players(season: str | None = None) -> pd.DataFrame:
    """
    Base + advanced merged on PLAYER_ID into one league-wide player table.
    Position is not included here; it is attached per-team from the roster.
    """
    base = get_player_base_stats(season)
    adv = get_player_advanced_stats(season)

    adv_cols = [c for c in adv.columns if c not in base.columns or c == "PLAYER_ID"]
    merged = base.merge(adv[adv_cols], on="PLAYER_ID", how="left", suffixes=("", "_adv"))
    return merged


if __name__ == "__main__":
    print("Teams:", len(get_teams()))
    players = fetch_league_players()
    print("League players:", len(players))
    print(players.head(3).to_string(index=False))
