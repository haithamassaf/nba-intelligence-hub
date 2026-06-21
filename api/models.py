"""Pydantic response schemas for the grading API."""

from pydantic import BaseModel


class TeamRef(BaseModel):
    code: str
    name: str


class TeamsResponse(BaseModel):
    sport: str
    count: int
    teams: list[TeamRef]


class PositionGrade(BaseModel):
    group: str
    grade: float
    letter: str
    n_players: int
    top: list


class TeamGradesResponse(BaseModel):
    sport: str
    team: str
    overall: float
    letter: str
    positions: list[PositionGrade]
    needs: list
    summary: str
