"""API endpoints — /ask, /players, /teams, /refresh."""

from fastapi import APIRouter, Query

from api.models import (
    AskRequest, AskResponse,
    PlayerStats, PlayersResponse,
    TeamInfo, TeamsResponse,
    RefreshResponse,
)
from rag.chain import ask, classify_query
from data.fetch_stats import get_player_season_stats, get_team_standings, get_team_stats_advanced
from data.transform import clean_player_stats, clean_standings, clean_team_advanced
from data.build_embeddings import build

router = APIRouter()


# ── POST /ask ────────────────────────────────────────────────────────

@router.post("/ask", response_model=AskResponse)
async def ask_question(req: AskRequest):
    """Ask a natural-language NBA question and get a grounded answer."""
    classification = classify_query(req.question)
    answer = ask(req.question)
    return AskResponse(
        question=req.question,
        answer=answer,
        classification=classification,
    )


# ── GET /players ─────────────────────────────────────────────────────

@router.get("/players", response_model=PlayersResponse)
async def list_players(
    search: str = Query(default=None, description="Filter by player name"),
    team: str = Query(default=None, description="Filter by team abbreviation (e.g. OKC)"),
    limit: int = Query(default=50, ge=1, le=500, description="Max results"),
):
    """Browse player season stats with optional filters."""
    raw = get_player_season_stats()
    df = clean_player_stats(raw)

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


# ── GET /teams ───────────────────────────────────────────────────────

@router.get("/teams", response_model=TeamsResponse)
async def list_teams(
    conference: str = Query(default=None, description="Filter: East or West"),
):
    """Browse team standings with advanced stats."""
    standings_raw = get_team_standings()
    advanced_raw = get_team_stats_advanced()

    standings = clean_standings(standings_raw)
    advanced = clean_team_advanced(advanced_raw)

    if conference:
        standings = standings[standings["conference"].str.lower() == conference.lower()]

    teams = []
    for _, row in standings.iterrows():
        adv = advanced[advanced["team_id"] == row["team_id"]]
        teams.append(
            TeamInfo(
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
            )
        )
    return TeamsResponse(count=len(teams), teams=teams)


# ── POST /refresh ────────────────────────────────────────────────────

@router.post("/refresh", response_model=RefreshResponse)
async def refresh_data():
    """Re-fetch all NBA data and rebuild the vector store."""
    total = build(fresh=True)
    return RefreshResponse(status="ok", documents_loaded=total)
