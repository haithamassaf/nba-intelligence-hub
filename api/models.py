"""Pydantic request/response schemas for the API."""

from pydantic import BaseModel


# ── /ask ─────────────────────────────────────────────────────────────

class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    question: str
    answer: str
    classification: dict


# ── /players ─────────────────────────────────────────────────────────

class PlayerStats(BaseModel):
    player_id: int
    player_name: str
    team: str
    age: float
    games_played: int
    minutes: float
    pts: float
    reb: float
    ast: float
    stl: float
    blk: float
    tov: float
    fg_pct: float
    fg3_pct: float
    ft_pct: float
    plus_minus: float


class PlayersResponse(BaseModel):
    count: int
    players: list[PlayerStats]


# ── /teams ───────────────────────────────────────────────────────────

class TeamInfo(BaseModel):
    team_id: int
    team: str
    name: str
    conference: str
    seed: int
    wins: int
    losses: int
    win_pct: float
    streak: str
    off_rating: float | None = None
    def_rating: float | None = None
    net_rating: float | None = None
    pace: float | None = None


class TeamsResponse(BaseModel):
    count: int
    teams: list[TeamInfo]


# ── /refresh ─────────────────────────────────────────────────────────

class RefreshResponse(BaseModel):
    status: str
    documents_loaded: int
