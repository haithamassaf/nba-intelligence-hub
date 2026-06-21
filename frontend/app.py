"""
NFL & NBA Roster Grader — Streamlit frontend.

Pick a sport, pick a team, and see every position graded 0-100 against league
peers from advanced stats, a roster table, and an improvement summary. NFL
rookies are graded from their college production plus draft capital and combine.

Run with:
    streamlit run frontend/app.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st

from config.settings import DEFAULT_SPORT
from frontend.components.grade_view import render_overall, render_position_grades, render_roster

from grading.pipeline import build_nfl_graded, build_nba_graded
from grading.team_report import position_grades, overall_grade, to_letter
from summary.llm_summary import summarize

st.set_page_config(page_title="Roster Grader", page_icon="🏟️", layout="wide")

SPORTS = {
    "nfl": {"label": "🏈 NFL", "accent": "#013369"},
    "nba": {"label": "🏀 NBA", "accent": "#C8102E"},
}

_TTL = 60 * 60 * 6  # 6h cache; first load seeds live data


# ── Cached data loaders ──────────────────────────────────────────────

@st.cache_data(ttl=_TTL, show_spinner=False)
def load_nfl():
    return build_nfl_graded()


@st.cache_data(ttl=_TTL, show_spinner=False)
def load_nba():
    return build_nba_graded()


# ── Sport renderers ──────────────────────────────────────────────────

def render_nfl(graded: pd.DataFrame, teams: pd.DataFrame):
    if graded.empty:
        st.error("No NFL data loaded. First run fetches live data; check your network and reload.")
        return

    abbrs = sorted(graded["team"].dropna().unique()) if "team" in graded.columns else []
    name_map = {}
    if not teams.empty and "team_abbr" in teams.columns:
        label_col = "team_name" if "team_name" in teams.columns else "team_abbr"
        name_map = dict(zip(teams["team_abbr"], teams[label_col]))
    labels = {a: name_map.get(a, a) for a in abbrs}

    pick = st.selectbox("Team", abbrs, format_func=lambda a: labels.get(a, a))
    team_df = graded[graded["team"] == pick].copy()

    if "age" not in team_df.columns:
        team_df["age"] = pd.NA
    pos = position_grades(team_df, "group", "_wt")
    ov = overall_grade(pos, "nfl")

    left, right = st.columns([1, 1])
    with left:
        render_overall(labels.get(pick, pick), ov, to_letter(ov))
        render_position_grades(pos)
    with right:
        st.markdown("#### Improvement summary")
        st.write(summarize(labels.get(pick, pick), pos, "nfl"))
        st.caption("Rookies (R) graded from college production, draft capital, and combine testing.")

    render_roster(team_df, [
        ("player_name", "Player"), ("position", "Pos"), ("age", "Age"),
        ("years_exp", "Exp"), ("group", "Unit"), ("grade", "Grade"),
        ("letter", "Letter"), ("graded_as", "Basis"),
    ])


def render_nba(graded: pd.DataFrame, teams: pd.DataFrame):
    if graded.empty:
        st.error("No NBA data loaded. First run fetches live data; check your network and reload.")
        return

    abbrs = sorted(graded["team_abbr"].dropna().unique())
    full = {}
    if not teams.empty:
        full = dict(zip(teams["abbreviation"], teams["full_name"]))
    pick = st.selectbox("Team", abbrs, format_func=lambda a: full.get(a, a))
    team_df = graded[graded["team_abbr"] == pick].copy()

    pos = position_grades(team_df, "bucket", "_wt")
    ov = overall_grade(pos, "nba")

    left, right = st.columns([1, 1])
    with left:
        render_overall(full.get(pick, pick), ov, to_letter(ov))
        render_position_grades(pos)
    with right:
        st.markdown("#### Improvement summary")
        st.write(summarize(full.get(pick, pick), pos, "nba"))
        st.caption("Grades are relative to position peers across the league.")

    name_col = "PLAYER_NAME" if "PLAYER_NAME" in team_df.columns else "PLAYER"
    render_roster(team_df, [
        (name_col, "Player"), ("position", "Pos"), ("AGE", "Age"),
        ("EXP", "Exp"), ("bucket", "Group"), ("grade", "Grade"), ("letter", "Letter"),
    ])


# ── Main ─────────────────────────────────────────────────────────────

st.title("🏟️ Roster Grader")
st.caption("Every team graded by position from advanced stats. NFL and NBA.")

if DEFAULT_SPORT == "nfl":
    tab_nfl, tab_nba = st.tabs([SPORTS["nfl"]["label"], SPORTS["nba"]["label"]])
else:
    tab_nba, tab_nfl = st.tabs([SPORTS["nba"]["label"], SPORTS["nfl"]["label"]])

with tab_nfl:
    with st.spinner("Loading NFL data and grading rosters..."):
        nfl_graded, nfl_teams = load_nfl()
    render_nfl(nfl_graded, nfl_teams)

with tab_nba:
    with st.spinner("Loading NBA data and grading rosters (first run pulls all 30 rosters)..."):
        nba_graded, nba_teams = load_nba()
    render_nba(nba_graded, nba_teams)
