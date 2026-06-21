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


# ── NFL /players ─────────────────────────────────────────────────────

class NflPlayerStats(BaseModel):
    player_id: str
    player_name: str
    team: str
    position: str | None = None
    pos_group: str
    games: int
    completions: int
    attempts: int
    passing_yards: int
    passing_tds: int
    interceptions: int
    carries: int
    rushing_yards: int
    rushing_tds: int
    receptions: int
    targets: int
    receiving_yards: int
    receiving_tds: int
    scrimmage_yards: int
    total_tds: int
    fantasy_points: float
    fantasy_points_ppr: float


class NflPlayersResponse(BaseModel):
    count: int
    players: list[NflPlayerStats]


# ── NFL /teams ───────────────────────────────────────────────────────

class NflTeamInfo(BaseModel):
    team: str
    name: str
    conference: str
    division: str
    wins: int
    losses: int
    ties: int
    win_pct: float
    points_for: int
    points_against: int
    point_diff: int
    games: int
    div_rank: int | None = None


class NflTeamsResponse(BaseModel):
    count: int
    teams: list[NflTeamInfo]
