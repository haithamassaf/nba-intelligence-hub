"""
Transform raw NBA DataFrames into clean stats and natural-language
summaries ready for embedding in the vector store.
"""

import pandas as pd
from nba_api.stats.static import teams as static_teams

# Build team_id -> abbreviation lookup from static data
_TEAM_ABBREV = {t["id"]: t["abbreviation"] for t in static_teams.get_teams()}


# ── Player Transforms ────────────────────────────────────────────────

def clean_player_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Select and rename the columns we care about from LeagueDashPlayerStats."""
    cols = {
        "PLAYER_ID": "player_id",
        "PLAYER_NAME": "player_name",
        "TEAM_ABBREVIATION": "team",
        "AGE": "age",
        "GP": "games_played",
        "MIN": "minutes",
        "PTS": "pts",
        "REB": "reb",
        "AST": "ast",
        "STL": "stl",
        "BLK": "blk",
        "TOV": "tov",
        "FG_PCT": "fg_pct",
        "FG3_PCT": "fg3_pct",
        "FT_PCT": "ft_pct",
        "PLUS_MINUS": "plus_minus",
    }
    available = {k: v for k, v in cols.items() if k in df.columns}
    out = df[list(available.keys())].rename(columns=available)
    return out.sort_values("pts", ascending=False).reset_index(drop=True)



def player_summary(row: pd.Series) -> str:
    """
    Generate a natural-language stat summary for one player.

    Example output:
      "Shai Gilgeous-Alexander (OKC) is averaging 31.4 PPG, 5.5 RPG,
       6.2 APG, 2.0 SPG on 53.5% FG and 35.1% 3PT through 68 games."
    """
    fg = f"{row['fg_pct'] * 100:.1f}" if row["fg_pct"] < 1 else f"{row['fg_pct']:.1f}"
    fg3 = f"{row['fg3_pct'] * 100:.1f}" if row["fg3_pct"] < 1 else f"{row['fg3_pct']:.1f}"
    ft = f"{row['ft_pct'] * 100:.1f}" if row["ft_pct"] < 1 else f"{row['ft_pct']:.1f}"

    return (
        f"{row['player_name']} ({row['team']}) is averaging "
        f"{row['pts']:.1f} PPG, {row['reb']:.1f} RPG, {row['ast']:.1f} APG, "
        f"{row['stl']:.1f} SPG, {row['blk']:.1f} BPG "
        f"on {fg}% FG, {fg3}% 3PT, and {ft}% FT "
        f"through {int(row['games_played'])} games."
    )


def build_player_summaries(df: pd.DataFrame, min_games: int = 20) -> list[dict]:
    """
    Return a list of dicts with player_id, player_name, team, and summary text.

    Filters out players with fewer than `min_games` games played.
    """
    cleaned = clean_player_stats(df)
    cleaned = cleaned[cleaned["games_played"] >= min_games]

    summaries = []
    for _, row in cleaned.iterrows():
        summaries.append({
            "player_id": int(row["player_id"]),
            "player_name": row["player_name"],
            "team": row["team"],
            "summary": player_summary(row),
            "type": "player_season",
        })
    return summaries


# ── Team Transforms ──────────────────────────────────────────────────

def clean_standings(df: pd.DataFrame) -> pd.DataFrame:
    """Select key columns from LeagueStandings."""
    cols = {
        "TeamID": "team_id",
        "TeamCity": "city",
        "TeamName": "name",
        "Conference": "conference",
        "PlayoffRank": "seed",
        "WINS": "wins",
        "LOSSES": "losses",
        "WinPCT": "win_pct",
        "strCurrentStreak": "streak",
    }
    available = {k: v for k, v in cols.items() if k in df.columns}
    out = df[list(available.keys())].rename(columns=available)
    out["team"] = out["team_id"].map(_TEAM_ABBREV)
    return out.sort_values("win_pct", ascending=False).reset_index(drop=True)


def team_standings_summary(row: pd.Series) -> str:
    """Natural-language standings summary for one team."""
    return (
        f"The {row['city']} {row['name']} ({row['team']}) are "
        f"{int(row['wins'])}-{int(row['losses'])} "
        f"({row['win_pct']:.3f}), "
        f"ranked #{int(row['seed'])} in the {row['conference']}. "
        f"Current streak: {row['streak']}."
    )


def clean_team_advanced(df: pd.DataFrame) -> pd.DataFrame:
    """Select advanced columns from LeagueDashTeamStats (Advanced measure)."""
    cols = {
        "TEAM_ID": "team_id",
        "TEAM_NAME": "name",
        "OFF_RATING": "off_rating",
        "DEF_RATING": "def_rating",
        "NET_RATING": "net_rating",
        "PACE": "pace",
    }
    available = {k: v for k, v in cols.items() if k in df.columns}
    out = df[list(available.keys())].rename(columns=available)
    return out.sort_values("net_rating", ascending=False).reset_index(drop=True)


def team_advanced_summary(row: pd.Series) -> str:
    """Natural-language advanced stats summary for one team."""
    return (
        f"They have an offensive rating of "
        f"{row['off_rating']:.1f}, defensive rating of {row['def_rating']:.1f} "
        f"(net: {row['net_rating']:+.1f}), and play at a pace of "
        f"{row['pace']:.1f} possessions per game."
    )


def build_team_summaries(
    standings_df: pd.DataFrame,
    advanced_df: pd.DataFrame,
) -> list[dict]:
    """Combine standings + advanced stats into team summary dicts."""
    standings = clean_standings(standings_df)
    advanced = clean_team_advanced(advanced_df)

    summaries = []
    for _, row in standings.iterrows():
        text = team_standings_summary(row)

        # Merge advanced stats by team_id
        adv = advanced[advanced["team_id"] == row["team_id"]]
        if not adv.empty:
            text += " " + team_advanced_summary(adv.iloc[0])

        summaries.append({
            "team_id": int(row["team_id"]),
            "team": row["team"],
            "name": f"{row['city']} {row['name']}",
            "summary": text,
            "type": "team_season",
        })
    return summaries


# ── League Leaders Transforms ────────────────────────────────────────

_LEADER_STAT_COL = {
    "scoring": "PTS",
    "assists": "AST",
    "rebounding": "REB",
}


def leader_summary(df: pd.DataFrame, stat_label: str) -> str:
    """
    One-paragraph summary of the top 5 leaders in a stat category.

    Example: "The top scorers this season: 1. Shai Gilgeous-Alexander (31.4),
    2. Luka Doncic (28.9), ..."
    """
    stat_col = _LEADER_STAT_COL.get(stat_label)
    if stat_col is None or stat_col not in df.columns:
        return ""

    top5 = df.head(5)
    entries = []
    for i, (_, row) in enumerate(top5.iterrows(), 1):
        entries.append(f"{i}. {row['PLAYER']} ({row[stat_col]:.1f})")

    return f"Top {stat_label} leaders this season: {', '.join(entries)}."


def build_leader_summaries(datasets: dict) -> list[dict]:
    """Build summary dicts from the leaders DataFrames in the fetch_all output."""
    summaries = []
    mapping = {
        "leaders_pts": "scoring",
        "leaders_ast": "assists",
        "leaders_reb": "rebounding",
    }
    for key, label in mapping.items():
        if key in datasets and not datasets[key].empty:
            text = leader_summary(datasets[key], label)
            if text:
                summaries.append({
                    "summary": text,
                    "type": "league_leaders",
                    "category": label,
                })
    return summaries


# ── Master Pipeline ──────────────────────────────────────────────────

def build_all_summaries(datasets: dict) -> list[dict]:
    """
    Take the output of fetch_all() and produce every summary document
    for the vector store.
    """
    all_summaries = []

    # Player summaries
    if "player_stats" in datasets:
        all_summaries.extend(build_player_summaries(datasets["player_stats"]))

    # Team summaries
    if "standings" in datasets and "team_advanced" in datasets:
        all_summaries.extend(
            build_team_summaries(datasets["standings"], datasets["team_advanced"])
        )

    # League leaders
    all_summaries.extend(build_leader_summaries(datasets))

    print(f"Generated {len(all_summaries)} total summaries:")
    types = {}
    for s in all_summaries:
        types[s["type"]] = types.get(s["type"], 0) + 1
    for t, count in types.items():
        print(f"  {t}: {count}")

    return all_summaries


if __name__ == "__main__":
    from data.fetch_stats import fetch_all

    datasets = fetch_all()
    summaries = build_all_summaries(datasets)

    # Print a sample of each type
    seen = set()
    for s in summaries:
        if s["type"] not in seen:
            seen.add(s["type"])
            print(f"\n--- {s['type']} ---")
            print(s["summary"])
