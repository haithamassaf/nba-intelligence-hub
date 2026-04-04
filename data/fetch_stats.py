"""
Fetch live NBA stats from stats.nba.com via the nba_api package.

All functions return pandas DataFrames. A small delay is added between
API calls to respect the NBA stats rate limit.
"""

import time
import pandas as pd
from nba_api.stats.endpoints import (
    CommonAllPlayers,
    LeagueDashPlayerStats,
    LeagueDashTeamStats,
    LeagueLeaders,
    LeagueStandings,
    PlayerGameLog,
)

from config.settings import CURRENT_SEASON, LAST_N_GAMES, NBA_API_TIMEOUT

_DELAY = 0.6  # seconds between API calls


def _pause():
    time.sleep(_DELAY)


# ── Players ──────────────────────────────────────────────────────────

def get_active_players() -> pd.DataFrame:
    """Return a DataFrame of all players active in the current season."""
    data = CommonAllPlayers(
        is_only_current_season=1,
        season=CURRENT_SEASON,
        timeout=NBA_API_TIMEOUT,
    )
    _pause()
    return data.common_all_players.get_data_frame()


def get_player_season_stats(per_mode: str = "PerGame") -> pd.DataFrame:
    """
    Bulk fetch season averages for every player.

    per_mode: "PerGame", "Totals", "Per36", "Per48", etc.
    """
    data = LeagueDashPlayerStats(
        season=CURRENT_SEASON,
        per_mode_detailed=per_mode,
        season_type_all_star="Regular Season",
        timeout=NBA_API_TIMEOUT,
    )
    _pause()
    return data.league_dash_player_stats.get_data_frame()


def get_player_game_log(player_id: int, last_n: int = LAST_N_GAMES) -> pd.DataFrame:
    """
    Fetch a single player's game log for the current season.

    Returns *all* games, then slices to the most recent `last_n`.
    """
    data = PlayerGameLog(
        player_id=player_id,
        season=CURRENT_SEASON,
        season_type_all_star="Regular Season",
        timeout=NBA_API_TIMEOUT,
    )
    _pause()
    df = data.player_game_log.get_data_frame()
    return df.head(last_n)  # game log comes newest-first


# ── Teams ────────────────────────────────────────────────────────────

def get_team_standings() -> pd.DataFrame:
    """Conference standings with W-L, PCT, streak, etc."""
    data = LeagueStandings(
        season=CURRENT_SEASON,
        season_type="Regular Season",
        timeout=NBA_API_TIMEOUT,
    )
    _pause()
    return data.standings.get_data_frame()


def get_team_stats(per_mode: str = "PerGame") -> pd.DataFrame:
    """League-wide team stats (offensive numbers)."""
    data = LeagueDashTeamStats(
        season=CURRENT_SEASON,
        per_mode_detailed=per_mode,
        season_type_all_star="Regular Season",
        timeout=NBA_API_TIMEOUT,
    )
    _pause()
    return data.league_dash_team_stats.get_data_frame()


def get_team_stats_advanced() -> pd.DataFrame:
    """Advanced team stats — OFF_RATING, DEF_RATING, NET_RATING, PACE."""
    data = LeagueDashTeamStats(
        season=CURRENT_SEASON,
        measure_type_detailed_defense="Advanced",
        season_type_all_star="Regular Season",
        timeout=NBA_API_TIMEOUT,
    )
    _pause()
    return data.league_dash_team_stats.get_data_frame()


# ── League Leaders ───────────────────────────────────────────────────

def get_league_leaders(stat: str = "PTS", top_n: int = 20) -> pd.DataFrame:
    """
    Top players by a stat category.

    stat: PTS, AST, REB, STL, BLK, FG_PCT, FG3_PCT, etc.
    """
    data = LeagueLeaders(
        season=CURRENT_SEASON,
        per_mode48="PerGame",
        stat_category_abbreviation=stat,
        season_type_all_star="Regular Season",
        timeout=NBA_API_TIMEOUT,
    )
    _pause()
    return data.league_leaders.get_data_frame().head(top_n)


# ── Convenience: fetch everything ────────────────────────────────────

def fetch_all() -> dict[str, pd.DataFrame]:
    """
    Pull all core datasets in one call.

    Returns a dict keyed by dataset name.
    """
    print("Fetching player season stats...")
    player_stats = get_player_season_stats()

    print("Fetching team standings...")
    standings = get_team_standings()

    print("Fetching team stats...")
    team_stats = get_team_stats()

    print("Fetching advanced team stats...")
    team_advanced = get_team_stats_advanced()

    print("Fetching league leaders (PTS)...")
    leaders_pts = get_league_leaders("PTS")

    print("Fetching league leaders (AST)...")
    leaders_ast = get_league_leaders("AST")

    print("Fetching league leaders (REB)...")
    leaders_reb = get_league_leaders("REB")

    print("Done.")
    return {
        "player_stats": player_stats,
        "standings": standings,
        "team_stats": team_stats,
        "team_advanced": team_advanced,
        "leaders_pts": leaders_pts,
        "leaders_ast": leaders_ast,
        "leaders_reb": leaders_reb,
    }


if __name__ == "__main__":
    datasets = fetch_all()
    for name, df in datasets.items():
        print(f"\n{'='*60}")
        print(f"  {name}  ({len(df)} rows)")
        print(f"{'='*60}")
        print(df.head(5).to_string(index=False))
