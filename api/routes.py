"""
API endpoints — sport-aware.

Routes are prefixed with the sport:
    POST /{sport}/ask
    GET  /{sport}/players
    GET  /{sport}/teams
    POST /{sport}/refresh

where {sport} is one of: nfl, nba.
"""

from fastapi import APIRouter, Query, HTTPException, Path

from api.models import (
    AskRequest, AskResponse,
    PlayerStats, PlayersResponse,
    TeamInfo, TeamsResponse,
    NflPlayerStats, NflPlayersResponse,
    NflTeamInfo, NflTeamsResponse,
    RefreshResponse,
)
from config.settings import SPORTS
from rag.chain import ask, classify_query
from data.build_embeddings import build

router = APIRouter()


def _validate(sport: str) -> str:
    sport = sport.lower()
    if sport not in SPORTS:
        raise HTTPException(status_code=404, detail=f"Unknown sport '{sport}'. Expected one of {list(SPORTS)}.")
    return sport


# ── POST /{sport}/ask ────────────────────────────────────────────────

@router.post("/{sport}/ask", response_model=AskResponse)
async def ask_question(req: AskRequest, sport: str = Path(...)):
    """Ask a natural-language question and get a grounded answer."""
    sport = _validate(sport)
    classification = classify_query(req.question, sport)
    answer = ask(req.question, sport)
    return AskResponse(question=req.question, answer=answer, classification=classification)


# ── GET /{sport}/players ─────────────────────────────────────────────

@router.get("/{sport}/players", response_model=PlayersResponse | NflPlayersResponse)
async def list_players(
    sport: str = Path(...),
    search: str = Query(default=None, description="Filter by player name"),
    team: str = Query(default=None, description="Filter by team abbreviation"),
    position: str = Query(default=None, description="NFL only: QB/RB/WR/TE"),
    limit: int = Query(default=50, ge=1, le=500, description="Max results"),
):
    """Browse player season stats with optional filters."""
    sport = _validate(sport)

    if sport == "nba":
        from data.fetch_stats import get_player_season_stats
        from data.transform import clean_player_stats

        df = clean_player_stats(get_player_season_stats())
        if search:
            df = df[df["player_name"].str.contains(search, case=False, na=False)]
        if team:
            df = df[df["team"].str.upper() == team.upper()]
        df = df.head(limit)

        players = [
            PlayerStats(
                player_id=int(row["player_id"]),
                player_name=row["player_name"],
                team=row["team"],
                age=row["age"],
                games_played=int(row["games_played"]),
                minutes=round(row["minutes"], 1),
                pts=round(row["pts"], 1),
                reb=round(row["reb"], 1),
                ast=round(row["ast"], 1),
                stl=round(row["stl"], 1),
                blk=round(row["blk"], 1),
                tov=round(row["tov"], 1),
                fg_pct=round(row["fg_pct"], 3),
                fg3_pct=round(row["fg3_pct"], 3),
                ft_pct=round(row["ft_pct"], 3),
                plus_minus=round(row["plus_minus"], 1),
            )
            for _, row in df.iterrows()
        ]
        return PlayersResponse(count=len(players), players=players)

    # NFL
    from data.nfl_fetch import get_player_season_stats as nfl_players
    from data.nfl_transform import clean_player_stats as clean_nfl

    df = clean_nfl(nfl_players())
    if not df.empty:
        if search:
            df = df[df["player_name"].str.contains(search, case=False, na=False)]
        if team:
            df = df[df["team"].str.upper() == team.upper()]
        if position:
            df = df[df["pos_group"] == position.upper()]
        df = df.sort_values("fantasy_points", ascending=False).head(limit)

    players = [
        NflPlayerStats(
            player_id=str(row["player_id"]),
            player_name=row["player_name"],
            team=row["team"],
            position=row.get("position"),
            pos_group=row["pos_group"],
            games=int(row["games"]),
            completions=int(row["completions"]),
            attempts=int(row["attempts"]),
            passing_yards=int(row["passing_yards"]),
            passing_tds=int(row["passing_tds"]),
            interceptions=int(row["interceptions"]),
            carries=int(row["carries"]),
            rushing_yards=int(row["rushing_yards"]),
            rushing_tds=int(row["rushing_tds"]),
            receptions=int(row["receptions"]),
            targets=int(row["targets"]),
            receiving_yards=int(row["receiving_yards"]),
            receiving_tds=int(row["receiving_tds"]),
            scrimmage_yards=int(row["scrimmage_yards"]),
            total_tds=int(row["total_tds"]),
            fantasy_points=round(float(row["fantasy_points"]), 1),
            fantasy_points_ppr=round(float(row["fantasy_points_ppr"]), 1),
        )
        for _, row in df.iterrows()
    ]
    return NflPlayersResponse(count=len(players), players=players)


# ── GET /{sport}/teams ───────────────────────────────────────────────

@router.get("/{sport}/teams", response_model=TeamsResponse | NflTeamsResponse)
async def list_teams(
    sport: str = Path(...),
    conference: str = Query(default=None, description="NBA: East/West. NFL: AFC/NFC"),
):
    """Browse team standings."""
    sport = _validate(sport)

    if sport == "nba":
        from data.fetch_stats import get_team_standings, get_team_stats_advanced
        from data.transform import clean_standings, clean_team_advanced

        standings = clean_standings(get_team_standings())
        advanced = clean_team_advanced(get_team_stats_advanced())
        if conference:
            standings = standings[standings["conference"].str.lower() == conference.lower()]

        teams = []
        for _, row in standings.iterrows():
            adv = advanced[advanced["team_id"] == row["team_id"]]
            teams.append(TeamInfo(
                team_id=int(row["team_id"]),
                team=row["team"],
                name=f"{row['city']} {row['name']}",
                conference=row["conference"],
                seed=int(row["seed"]),
                wins=int(row["wins"]),
                losses=int(row["losses"]),
                win_pct=round(row["win_pct"], 3),
                streak=row["streak"],
                off_rating=round(adv.iloc[0]["off_rating"], 1) if not adv.empty else None,
                def_rating=round(adv.iloc[0]["def_rating"], 1) if not adv.empty else None,
                net_rating=round(adv.iloc[0]["net_rating"], 1) if not adv.empty else None,
                pace=round(adv.iloc[0]["pace"], 1) if not adv.empty else None,
            ))
        return TeamsResponse(count=len(teams), teams=teams)

    # NFL
    from data.nfl_fetch import get_schedules, get_team_meta
    from data.nfl_transform import compute_standings

    standings = compute_standings(get_schedules(), get_team_meta())
    if conference:
        standings = [t for t in standings if t["conference"].lower() == conference.lower()]

    teams = [
        NflTeamInfo(
            team=t["team"],
            name=t["name"],
            conference=t["conference"],
            division=t["division"],
            wins=t["wins"],
            losses=t["losses"],
            ties=t["ties"],
            win_pct=t["win_pct"],
            points_for=t["points_for"],
            points_against=t["points_against"],
            point_diff=t["point_diff"],
            games=t["games"],
            div_rank=t.get("div_rank"),
        )
        for t in standings
    ]
    return NflTeamsResponse(count=len(teams), teams=teams)


# ── POST /{sport}/refresh ────────────────────────────────────────────

@router.post("/{sport}/refresh", response_model=RefreshResponse)
async def refresh_data(sport: str = Path(...)):
    """Re-fetch a sport's data and rebuild its vector store."""
    sport = _validate(sport)
    total = build(sport, fresh=True)
    return RefreshResponse(status="ok", documents_loaded=total)
