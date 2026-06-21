"""
Grading API (sport-aware).

    GET /{sport}/teams                     list teams
    GET /{sport}/teams/{team}/grades       position grades + needs + summary

{sport} is one of: nfl, nba. Graded tables are built once per process.
"""

from functools import lru_cache
import pandas as pd
from fastapi import APIRouter, HTTPException, Path

from config.settings import SPORTS
from grading.pipeline import build_nfl_graded, build_nba_graded
from grading.team_report import position_grades, overall_grade, needs as team_needs, to_letter
from summary.llm_summary import summarize
from api.models import TeamRef, TeamsResponse, PositionGrade, TeamGradesResponse

router = APIRouter()

_CFG = {
    "nfl": {"team_col": "team", "group_col": "group", "code": "team_abbr", "name": "team_name"},
    "nba": {"team_col": "team_abbr", "group_col": "bucket", "code": "abbreviation", "name": "full_name"},
}


@lru_cache(maxsize=1)
def _nfl():
    return build_nfl_graded()


@lru_cache(maxsize=1)
def _nba():
    return build_nba_graded()


def _validate(sport: str) -> str:
    s = sport.lower()
    if s not in SPORTS:
        raise HTTPException(status_code=404, detail=f"Unknown sport '{sport}'. Expected {list(SPORTS)}.")
    return s


def _state(sport: str):
    return _nfl() if sport == "nfl" else _nba()


def _names(sport: str, teams: pd.DataFrame) -> dict:
    cfg = _CFG[sport]
    if teams is None or teams.empty or cfg["code"] not in teams.columns:
        return {}
    name_col = cfg["name"] if cfg["name"] in teams.columns else cfg["code"]
    return dict(zip(teams[cfg["code"]], teams[name_col]))


@router.get("/{sport}/teams", response_model=TeamsResponse)
async def list_teams(sport: str = Path(...)):
    sport = _validate(sport)
    graded, teams = _state(sport)
    col = _CFG[sport]["team_col"]
    if graded.empty or col not in graded.columns:
        raise HTTPException(status_code=503, detail="No data loaded yet; check the data source and retry.")
    names = _names(sport, teams)
    codes = sorted(graded[col].dropna().unique())
    return TeamsResponse(
        sport=sport, count=len(codes),
        teams=[TeamRef(code=c, name=names.get(c, c)) for c in codes],
    )


@router.get("/{sport}/teams/{team}/grades", response_model=TeamGradesResponse)
async def team_grades(sport: str = Path(...), team: str = Path(...)):
    sport = _validate(sport)
    graded, teams = _state(sport)
    cfg = _CFG[sport]
    col = cfg["team_col"]
    if graded.empty or col not in graded.columns:
        raise HTTPException(status_code=503, detail="No data loaded yet; check the data source and retry.")

    code = team.upper()
    team_df = graded[graded[col].astype(str).str.upper() == code].copy()
    if team_df.empty:
        raise HTTPException(status_code=404, detail=f"No team '{team}' in {sport}.")

    names = _names(sport, teams)
    label = names.get(code, code)
    pos = position_grades(team_df, cfg["group_col"], "_wt")
    ov = overall_grade(pos, sport)

    return TeamGradesResponse(
        sport=sport, team=label, overall=ov, letter=to_letter(ov),
        positions=[PositionGrade(group=g, **{k: info[k] for k in ("grade", "letter", "n_players", "top")})
                   for g, info in sorted(pos.items(), key=lambda kv: -kv[1]["grade"])],
        needs=team_needs(pos),
        summary=summarize(label, pos, sport),
    )
