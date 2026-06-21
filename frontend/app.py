"""
NFL & NBA Roster Grader + Trade Simulator — Streamlit frontend.

Per sport: grade every team's roster by position from advanced stats, compare
players, browse stats, and (NFL) run cap-legal trades that show the grade impact.

Run with:
    streamlit run frontend/app.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st

from config.settings import DEFAULT_SPORT
from grading.pipeline import build_nfl_graded, build_nba_graded
from grading.team_report import position_grades, overall_grade, to_letter
from summary.llm_summary import summarize
from frontend.components.grade_view import render_overall, render_position_grades, render_roster
from frontend.components.views import render_compare, render_stats
from frontend.components.trade_view import render_trades

st.set_page_config(page_title="Roster Grader", page_icon="🏟️", layout="wide")

_TTL = 60 * 60 * 6

NFL_STATS = [
    ("passing_yards", "Pass Yds"), ("passing_tds", "Pass TD"), ("interceptions", "INT"),
    ("rushing_yards", "Rush Yds"), ("rushing_tds", "Rush TD"),
    ("receptions", "Rec"), ("receiving_yards", "Rec Yds"), ("receiving_tds", "Rec TD"),
    ("def_sacks", "Sacks"), ("def_tackles", "Tkl"),
]
NBA_STATS = [
    ("PTS", "PPG"), ("REB", "RPG"), ("AST", "APG"), ("STL", "SPG"), ("BLK", "BPG"),
    ("TS_PCT", "TS%"), ("USG_PCT", "USG%"), ("PLUS_MINUS", "+/-"), ("NET_RATING", "NetRtg"), ("PIE", "PIE"),
]


# ── Cached loaders ───────────────────────────────────────────────────

@st.cache_data(ttl=_TTL, show_spinner=False)
def load_nfl():
    return build_nfl_graded()


@st.cache_data(ttl=_TTL, show_spinner=False)
def load_nba():
    return build_nba_graded()


def nfl_names(teams):
    if teams is None or teams.empty or "team_abbr" not in teams.columns:
        return {}
    col = "team_name" if "team_name" in teams.columns else "team_abbr"
    return dict(zip(teams["team_abbr"], teams[col]))


def nba_names(teams):
    if teams is None or teams.empty:
        return {}
    return dict(zip(teams["abbreviation"], teams["full_name"]))


# ── Team-grades view ─────────────────────────────────────────────────

def render_nfl_grades(graded, names):
    abbrs = sorted(graded["team"].dropna().unique()) if "team" in graded.columns else []
    pick = st.selectbox("Team", abbrs, format_func=lambda a: names.get(a, a), key="nfl_grade_team")
    team_df = graded[graded["team"] == pick].copy()
    if "age" not in team_df.columns:
        team_df["age"] = pd.NA
    pos = position_grades(team_df, "group", "_wt")
    ov = overall_grade(pos, "nfl")

    left, right = st.columns(2)
    with left:
        render_overall(names.get(pick, pick), ov, to_letter(ov))
        render_position_grades(pos)
    with right:
        st.markdown("#### Improvement summary")
        st.write(summarize(names.get(pick, pick), pos, "nfl"))
        st.caption("Rookies (R) graded from college production, draft capital, and combine testing.")

    render_roster(team_df, [
        ("player_name", "Player"), ("position", "Pos"), ("age", "Age"),
        ("years_exp", "Exp"), ("group", "Unit"), ("grade", "Grade"),
        ("letter", "Letter"), ("graded_as", "Basis"),
    ])


def render_nba_grades(graded, names):
    abbrs = sorted(graded["team_abbr"].dropna().unique())
    pick = st.selectbox("Team", abbrs, format_func=lambda a: names.get(a, a), key="nba_grade_team")
    team_df = graded[graded["team_abbr"] == pick].copy()
    pos = position_grades(team_df, "bucket", "_wt")
    ov = overall_grade(pos, "nba")

    left, right = st.columns(2)
    with left:
        render_overall(names.get(pick, pick), ov, to_letter(ov))
        render_position_grades(pos)
    with right:
        st.markdown("#### Improvement summary")
        st.write(summarize(names.get(pick, pick), pos, "nba"))
        st.caption("Grades are relative to position peers across the league.")

    name_col = "PLAYER_NAME" if "PLAYER_NAME" in team_df.columns else "PLAYER"
    render_roster(team_df, [
        (name_col, "Player"), ("position", "Pos"), ("AGE", "Age"),
        ("EXP", "Exp"), ("bucket", "Group"), ("grade", "Grade"), ("letter", "Letter"),
    ])


# ── Sport sections (view selector) ───────────────────────────────────

def nfl_section(graded, teams):
    if graded.empty:
        st.error("No NFL data loaded. The first run fetches live data; check your network and reload.")
        return
    names = nfl_names(teams)
    view = st.radio("View", ["Team grades", "Compare", "Stats", "Trades"], horizontal=True, key="nfl_view")
    if view == "Team grades":
        render_nfl_grades(graded, names)
    elif view == "Compare":
        render_compare(graded, "player_name", "group", NFL_STATS, key="nfl")
    elif view == "Stats":
        render_stats(graded, "player_name", "group", "team", NFL_STATS, names, key="nfl")
    else:
        render_trades(graded, names)


def nba_section(graded, teams):
    if graded.empty:
        st.error("No NBA data loaded. The first run fetches live data; check your network and reload.")
        return
    names = nba_names(teams)
    view = st.radio("View", ["Team grades", "Compare", "Stats"], horizontal=True, key="nba_view")
    if view == "Team grades":
        render_nba_grades(graded, names)
    elif view == "Compare":
        render_compare(graded, "PLAYER_NAME", "bucket", NBA_STATS, key="nba")
    else:
        render_stats(graded, "PLAYER_NAME", "bucket", "team_abbr", NBA_STATS, names, key="nba")


# ── Main ─────────────────────────────────────────────────────────────

st.title("🏟️ Roster Grader + Trade Simulator")
st.caption("Every team graded by position from advanced stats. NFL and NBA.")

if DEFAULT_SPORT == "nfl":
    tab_nfl, tab_nba = st.tabs(["🏈 NFL", "🏀 NBA"])
else:
    tab_nba, tab_nfl = st.tabs(["🏀 NBA", "🏈 NFL"])

with tab_nfl:
    with st.spinner("Loading NFL data and grading rosters..."):
        nfl_graded, nfl_teams = load_nfl()
    nfl_section(nfl_graded, nfl_teams)

with tab_nba:
    with st.spinner("Loading NBA data and grading rosters (first run pulls all 30 rosters)..."):
        nba_graded, nba_teams = load_nba()
    nba_section(nba_graded, nba_teams)
