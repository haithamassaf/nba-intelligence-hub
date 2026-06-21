"""
NFL & NBA Rosters — Streamlit frontend.

Browse rosters and stats, compare players (with a season/career dropdown and
charts) and rosters, and run cap-legal NFL trades. No grading.

Run with:
    streamlit run frontend/app.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st

from config.settings import DEFAULT_SPORT
from data.assemble import build_nfl_roster, build_nba_roster
from data.compare_data import nba_splits, nfl_splits
from data import fetch_stats as nba_data
from data import nfl_fetch as nfl_data
from frontend.components.tables import render_roster_table
from frontend.components.compare_view import render_player_compare, render_roster_compare
from frontend.components.trade_view import render_trades
from frontend.components.assistant_view import render_assistant

st.set_page_config(page_title="NFL & NBA Rosters", page_icon="🏟️", layout="wide")

_TTL = 60 * 60 * 6

NFL_COLS = [
    ("player_name", "Player"), ("position", "Pos"), ("age", "Age"), ("years_exp", "Exp"),
    ("passing_yards", "Pass Yds"), ("passing_tds", "Pass TD"), ("interceptions", "INT"),
    ("rushing_yards", "Rush Yds"), ("rushing_tds", "Rush TD"),
    ("receptions", "Rec"), ("receiving_yards", "Rec Yds"), ("receiving_tds", "Rec TD"),
    ("def_sacks", "Sacks"), ("def_tackles", "Tkl"), ("cap_hit", "Cap Hit ($M)"), ("apy", "APY ($M)"),
]
NFL_RADAR = [
    ("passing_yards", "Pass Yds"), ("passing_tds", "Pass TD"), ("rushing_yards", "Rush Yds"),
    ("rushing_tds", "Rush TD"), ("receptions", "Rec"), ("receiving_yards", "Rec Yds"),
    ("receiving_tds", "Rec TD"), ("def_sacks", "Sacks"), ("def_tackles", "Tkl"),
]
NFL_COMPARE_STATS = [
    ("passing_yards", "Pass Yds"), ("passing_tds", "Pass TD"), ("interceptions", "INT"),
    ("rushing_yards", "Rush Yds"), ("rushing_tds", "Rush TD"), ("receptions", "Rec"),
    ("receiving_yards", "Rec Yds"), ("receiving_tds", "Rec TD"), ("def_sacks", "Sacks"), ("def_tackles", "Tkl"),
]

NBA_COLS = [
    ("PLAYER_NAME", "Player"), ("position", "Pos"), ("AGE", "Age"), ("EXP", "Exp"),
    ("GP", "GP"), ("MIN", "MIN"), ("PTS", "PPG"), ("REB", "RPG"), ("AST", "APG"),
    ("STL", "SPG"), ("BLK", "BPG"), ("TS_PCT", "TS%"), ("USG_PCT", "USG%"),
    ("PLUS_MINUS", "+/-"), ("NET_RATING", "NetRtg"), ("PIE", "PIE"),
]
NBA_RADAR = [("PTS", "PTS"), ("REB", "REB"), ("AST", "AST"), ("STL", "STL"), ("BLK", "BLK"), ("FG_PCT", "FG%")]
NBA_COMPARE_STATS = [
    ("PTS", "PPG"), ("REB", "RPG"), ("AST", "APG"), ("STL", "SPG"), ("BLK", "BPG"),
    ("FG_PCT", "FG%"), ("FG3_PCT", "3P%"), ("FT_PCT", "FT%"), ("MIN", "MIN"), ("GP", "GP"),
]


# ── Cached loaders ───────────────────────────────────────────────────

@st.cache_data(ttl=_TTL, show_spinner=False)
def load_nfl():
    return build_nfl_roster()


@st.cache_data(ttl=_TTL, show_spinner=False)
def load_nba():
    return build_nba_roster()


@st.cache_data(ttl=_TTL, show_spinner=False)
def nfl_history():
    end = nfl_data.stats_season()
    return nfl_data.get_player_history(end - 15, end)   # ~15 seasons for career splits


@st.cache_data(ttl=_TTL, show_spinner=False)
def nba_career(player_id):
    return nba_data.get_player_career(int(player_id))


def nfl_get_splits(gsis_id):
    if gsis_id is None:
        return {}
    try:
        return nfl_splits(nfl_history(), gsis_id)
    except Exception:
        return {}


def nba_get_splits(player_id):
    if player_id is None:
        return {}
    try:
        season_df, career_df = nba_career(player_id)
        return nba_splits(season_df, career_df)
    except Exception:
        return {}


def nfl_names(teams):
    if teams is None or teams.empty or "team_abbr" not in teams.columns:
        return {}
    col = "team_name" if "team_name" in teams.columns else "team_abbr"
    return dict(zip(teams["team_abbr"], teams[col]))


def nba_names(teams):
    if teams is None or teams.empty:
        return {}
    return dict(zip(teams["abbreviation"], teams["full_name"]))


def _col_mean(df, col, nd=1):
    if col not in df.columns:
        return None
    s = pd.to_numeric(df[col], errors="coerce")
    return round(float(s.mean()), nd) if s.notna().any() else None


def _col_sum(df, col, nd=1):
    if col not in df.columns:
        return None
    s = pd.to_numeric(df[col], errors="coerce")
    return round(float(s.fillna(0).sum()), nd)


def nfl_summary(df):
    return {"Players": int(len(df)),
            "Avg age": _col_mean(df, "age"),
            "Total APY ($M)": _col_sum(df, "apy")}


def nba_summary(df):
    return {"Players": int(len(df)),
            "Avg age": _col_mean(df, "AGE"),
            "Total PPG": _col_sum(df, "PTS"),
            "Avg +/-": _col_mean(df, "PLUS_MINUS", nd=2)}


def render_roster_view(table, team_col, name_for, cols, key):
    codes = sorted(table[team_col].dropna().astype(str).unique())
    pick = st.selectbox("Team", codes, format_func=lambda c: name_for.get(c, c), key=f"{key}_team")
    team_df = table[table[team_col].astype(str) == pick]
    st.markdown(f"#### {name_for.get(pick, pick)} — {len(team_df)} players")
    render_roster_table(team_df, cols)


# ── Sport sections ───────────────────────────────────────────────────

def nfl_section(table, teams):
    if table.empty:
        st.error("No NFL data loaded. The first run fetches live data; check your network and reload.")
        return
    names = nfl_names(teams)
    view = st.radio("View", ["Rosters", "Compare players", "Compare rosters", "Trades", "Ask AI"], horizontal=True, key="nfl_view")
    if view == "Rosters":
        render_roster_view(table, "team", names, NFL_COLS, "nfl")
    elif view == "Compare players":
        render_player_compare(
            table, "player_name", "gsis_id", nfl_get_splits, NFL_RADAR, NFL_COMPARE_STATS, "nfl",
            no_data_hint="The free NFL data covers passing, rushing, receiving, and kicking, so offensive and defensive linemen have no stats here. Try skill-position players or kickers.",
        )
    elif view == "Compare rosters":
        render_roster_compare(table, "team", names, nfl_summary, NFL_COLS, "nfl")
    elif view == "Trades":
        render_trades(table, names)
    else:
        render_assistant(table, teams)


def nba_section(table, teams):
    if table.empty:
        st.error("No NBA data loaded. The first run fetches live data; check your network and reload.")
        return
    names = nba_names(teams)
    view = st.radio("View", ["Rosters", "Compare players", "Compare rosters"], horizontal=True, key="nba_view")
    if view == "Rosters":
        render_roster_view(table, "team_abbr", names, NBA_COLS, "nba")
    elif view == "Compare players":
        render_player_compare(table, "PLAYER_NAME", "PLAYER_ID", nba_get_splits, NBA_RADAR, NBA_COMPARE_STATS, "nba")
    else:
        render_roster_compare(table, "team_abbr", names, nba_summary, NBA_COLS, "nba")


st.title("🏟️ NFL & NBA Rosters")
st.caption("Browse rosters and stats, compare players and rosters, and run cap-legal NFL trades.")

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
