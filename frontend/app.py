"""
NFL & NBA Rosters — Streamlit frontend.

Browse every team's roster and stats, compare any two players, and run cap-legal
NFL trades. No grading.

Run with:
    streamlit run frontend/app.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from config.settings import DEFAULT_SPORT
from data.assemble import build_nfl_roster, build_nba_roster
from frontend.components.tables import render_roster_table, render_compare
from frontend.components.trade_view import render_trades

st.set_page_config(page_title="NFL & NBA Rosters", page_icon="🏟️", layout="wide")

_TTL = 60 * 60 * 6

NFL_COLS = [
    ("player_name", "Player"), ("position", "Pos"), ("age", "Age"), ("years_exp", "Exp"),
    ("passing_yards", "Pass Yds"), ("passing_tds", "Pass TD"), ("interceptions", "INT"),
    ("rushing_yards", "Rush Yds"), ("rushing_tds", "Rush TD"),
    ("receptions", "Rec"), ("receiving_yards", "Rec Yds"), ("receiving_tds", "Rec TD"),
    ("def_sacks", "Sacks"), ("def_tackles", "Tkl"), ("apy", "APY"),
]
NFL_STATS = NFL_COLS[4:]

NBA_COLS = [
    ("PLAYER_NAME", "Player"), ("position", "Pos"), ("AGE", "Age"), ("EXP", "Exp"),
    ("GP", "GP"), ("MIN", "MIN"), ("PTS", "PPG"), ("REB", "RPG"), ("AST", "APG"),
    ("STL", "SPG"), ("BLK", "BPG"), ("TS_PCT", "TS%"), ("USG_PCT", "USG%"),
    ("PLUS_MINUS", "+/-"), ("NET_RATING", "NetRtg"), ("PIE", "PIE"),
]
NBA_STATS = NBA_COLS[4:]


@st.cache_data(ttl=_TTL, show_spinner=False)
def load_nfl():
    return build_nfl_roster()


@st.cache_data(ttl=_TTL, show_spinner=False)
def load_nba():
    return build_nba_roster()


def nfl_names(teams):
    if teams is None or teams.empty or "team_abbr" not in teams.columns:
        return {}
    col = "team_name" if "team_name" in teams.columns else "team_abbr"
    return dict(zip(teams["team_abbr"], teams[col]))


def nba_names(teams):
    if teams is None or teams.empty:
        return {}
    return dict(zip(teams["abbreviation"], teams["full_name"]))


def render_roster_view(table, team_col, name_for, cols, key):
    codes = sorted(table[team_col].dropna().astype(str).unique())
    pick = st.selectbox("Team", codes, format_func=lambda c: name_for.get(c, c), key=f"{key}_team")
    team_df = table[table[team_col].astype(str) == pick]
    st.markdown(f"#### {name_for.get(pick, pick)} — {len(team_df)} players")
    render_roster_table(team_df, cols)


def nfl_section(table, teams):
    if table.empty:
        st.error("No NFL data loaded. The first run fetches live data; check your network and reload.")
        return
    names = nfl_names(teams)
    view = st.radio("View", ["Rosters", "Compare", "Trades"], horizontal=True, key="nfl_view")
    if view == "Rosters":
        render_roster_view(table, "team", names, NFL_COLS, "nfl")
    elif view == "Compare":
        render_compare(table, "player_name", NFL_STATS, "nfl")
    else:
        render_trades(table, names)


def nba_section(table, teams):
    if table.empty:
        st.error("No NBA data loaded. The first run fetches live data; check your network and reload.")
        return
    names = nba_names(teams)
    view = st.radio("View", ["Rosters", "Compare"], horizontal=True, key="nba_view")
    if view == "Rosters":
        render_roster_view(table, "team_abbr", names, NBA_COLS, "nba")
    else:
        radar_axes = [("PTS", "PTS"), ("REB", "REB"), ("AST", "AST"),
                      ("STL", "STL"), ("BLK", "BLK"), ("TS_PCT", "TS%")]
        render_compare(table, "PLAYER_NAME", NBA_STATS, "nba", radar_axes=radar_axes)


st.title("🏟️ NFL & NBA Rosters")
st.caption("Browse every team's roster and stats, compare players, and run cap-legal NFL trades.")

if DEFAULT_SPORT == "nfl":
    tab_nfl, tab_nba = st.tabs(["🏈 NFL", "🏀 NBA"])
else:
    tab_nba, tab_nfl = st.tabs(["🏀 NBA", "🏈 NFL"])

with tab_nfl:
    with st.spinner("Loading NFL rosters..."):
        nfl_table, nfl_teams = load_nfl()
    nfl_section(nfl_table, nfl_teams)

with tab_nba:
    with st.spinner("Loading NBA rosters (first run pulls all 30)..."):
        nba_table, nba_teams = load_nba()
    nba_section(nba_table, nba_teams)
