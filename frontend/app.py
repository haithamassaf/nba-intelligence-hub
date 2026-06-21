"""
NFL & NBA Intelligence Hub — Streamlit Frontend

Two sections (NFL and NBA) backed by a shared RAG pipeline. Each sport has
its own ChromaDB collection, live data source, and accent theme.

Run with:
    streamlit run frontend/app.py
"""

import streamlit as st
from datetime import datetime

from rag.chain import ask, classify_query
from rag.vector_store import count as vector_count
from data.build_embeddings import build as rebuild_data

from frontend.components.chat import render_chat_history, add_message, render_message
from frontend.components.stats_card import (
    render_player_card, render_team_card, render_standings_table,
    render_nfl_player_card, render_nfl_team_card, render_nfl_standings_table,
)
from frontend.components.player_compare import render_comparison, render_nfl_comparison


# ── Sport Config ─────────────────────────────────────────────────────

SPORTS = {
    "nfl": {
        "label": "🏈 NFL",
        "icon": "🏈",
        "title": "NFL Intelligence Hub",
        "tagline": "AI-powered NFL analytics",
        "gradient": "linear-gradient(135deg, #013369, #D50A0A)",
        "seed_msg": "First launch — fetching live NFL data and building the vector store...",
        "refresh_msg": "Fetching fresh NFL data...",
        "ask_header": "Ask anything about the NFL",
        "ask_placeholder": "Ask about players, teams, stats, MVP race...",
        "quick": [
            "Who's the MVP frontrunner right now?",
            "Compare Josh Allen and Lamar Jackson",
            "Which teams have the best record?",
            "Who leads the league in rushing?",
            "How are the 49ers looking this season?",
        ],
    },
    "nba": {
        "label": "🏀 NBA",
        "icon": "🏀",
        "title": "NBA Intelligence Hub",
        "tagline": "AI-powered NBA analytics",
        "gradient": "linear-gradient(135deg, #007AC1, #F58426)",
        "seed_msg": "First launch — fetching live NBA data and building the vector store...",
        "refresh_msg": "Fetching fresh NBA data...",
        "ask_header": "Ask anything about the NBA",
        "ask_placeholder": "Ask about players, teams, stats, MVP race...",
        "quick": [
            "Who's playing the best basketball right now?",
            "Compare Luka and Shai's stats",
            "Who should win MVP?",
            "Which teams have the best defense?",
            "How has Jayson Tatum been playing?",
        ],
    },
}
SPORT_ORDER = ["nfl", "nba"]


# ── Page Config ──────────────────────────────────────────────────────

st.set_page_config(
    page_title="NFL & NBA Intelligence Hub",
    page_icon="🏟️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ───────────────────────────────────────────────────────

st.markdown("""
<style>
    .stApp { background-color: #0e1117; }
    section[data-testid="stSidebar"] { background-color: #161b22; }
    .stChatInput { border-color: #30363d !important; }

    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 8px;
        padding: 12px 16px;
        border: 1px solid #30363d;
    }
    [data-testid="stMetricValue"] { font-size: 24px; font-weight: 700; }
    [data-testid="stMetricLabel"] {
        font-size: 11px; text-transform: uppercase;
        letter-spacing: 1px; color: #8b949e;
    }

    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { border-radius: 6px; padding: 8px 16px; }

    .hub-header { text-align: center; padding: 20px 0 10px 0; }
    .hub-header h1 {
        font-size: 26px; font-weight: 800;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 4px;
    }
    .hub-header p { color: #8b949e; font-size: 14px; }

    .stDataFrame { border-radius: 8px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)


# ── Session State Init ───────────────────────────────────────────────

if "sport" not in st.session_state:
    st.session_state.sport = "nfl"
if "messages" not in st.session_state:
    st.session_state.messages = {"nfl": [], "nba": []}
if "last_refreshed" not in st.session_state:
    st.session_state.last_refreshed = {"nfl": None, "nba": None}
if "last_classification" not in st.session_state:
    st.session_state.last_classification = None


# ── Sidebar: Sport Toggle (top) ──────────────────────────────────────

with st.sidebar:
    choice = st.radio(
        "Sport",
        SPORT_ORDER,
        format_func=lambda s: SPORTS[s]["label"],
        horizontal=True,
        label_visibility="collapsed",
        index=SPORT_ORDER.index(st.session_state.sport),
        key="sport_toggle",
    )
    if choice != st.session_state.sport:
        st.session_state.sport = choice
        st.session_state.last_classification = None
        st.rerun()

sport = st.session_state.sport
cfg = SPORTS[sport]


# ── Auto-seed active sport's vector store on first run ───────────────

if vector_count(sport) == 0:
    with st.spinner(cfg["seed_msg"]):
        rebuild_data(sport, fresh=True)
    st.session_state.last_refreshed[sport] = datetime.now().strftime("%b %d, %I:%M %p")
    st.rerun()


# ── Sidebar: rest ────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        '<div class="hub-header">'
        f'<h1 style="background:{cfg["gradient"]};-webkit-background-clip:text;background-clip:text">'
        f'{cfg["icon"]} {cfg["title"]}</h1>'
        f'<p>{cfg["tagline"]}</p>'
        '<p style="color:#555;font-size:12px;margin-top:8px">Built by Haitham Assaf</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown("---")

    page = st.radio(
        "Navigate",
        ["💬 Ask", "📊 Players", "🏆 Standings", "⚔️ Compare"],
        label_visibility="collapsed",
        key=f"nav_{sport}",
    )

    st.markdown("---")

    st.markdown("##### Data Status")
    st.caption(f"📄 {vector_count(sport)} {sport.upper()} documents indexed")
    refreshed = st.session_state.last_refreshed[sport]
    st.caption(f"🕐 Last updated: {refreshed}" if refreshed else "🕐 Last updated: this session")

    if st.button("🔄 Refresh Data", use_container_width=True):
        with st.spinner(cfg["refresh_msg"]):
            rebuild_data(sport, fresh=True)
            st.session_state.last_refreshed[sport] = datetime.now().strftime("%b %d, %I:%M %p")
        st.success("Data refreshed!")
        st.rerun()

    st.markdown("---")

    st.markdown("##### Quick Questions")
    for p in cfg["quick"]:
        if st.button(p, use_container_width=True, key=f"qp_{sport}_{p[:20]}"):
            st.session_state.pending_question = p
            st.session_state._nav_to_chat = True
            st.rerun()


messages = st.session_state.messages[sport]


# ── Page: Ask (Chat) ────────────────────────────────────────────────

if page == "💬 Ask" or getattr(st.session_state, "_nav_to_chat", False):
    if getattr(st.session_state, "_nav_to_chat", False):
        st.session_state._nav_to_chat = False

    st.markdown(f"### 💬 {cfg['ask_header']}")
    st.caption("Powered by real-time stats and Claude AI")

    render_chat_history(messages, sport)

    pending = st.session_state.pop("pending_question", None)
    user_input = st.chat_input(cfg["ask_placeholder"])
    question = pending or user_input

    if question:
        add_message(messages, "user", question)
        render_message("user", question, sport)

        with st.chat_message("assistant", avatar=cfg["icon"]):
            with st.spinner("Analyzing stats..."):
                classification = classify_query(question, sport)
                st.session_state.last_classification = classification
                answer = ask(question, sport)

            st.markdown(answer)
            add_message(messages, "assistant", answer)

            with st.expander("🔍 Query details"):
                st.json(classification)


# ── Page: Players ────────────────────────────────────────────────────

elif page == "📊 Players":
    st.markdown(f"### 📊 {cfg['icon']} Player Stats")

    if sport == "nba":
        from data.fetch_stats import get_player_season_stats
        from data.transform import clean_player_stats

        col_search, col_team, col_limit = st.columns([3, 1, 1])
        with col_search:
            search = st.text_input("Search player", placeholder="e.g. LeBron", label_visibility="collapsed")
        with col_team:
            team_filter = st.text_input("Team", placeholder="e.g. OKC", label_visibility="collapsed")
        with col_limit:
            limit = st.selectbox("Show", [25, 50, 100, 200], index=1, label_visibility="collapsed")

        with st.spinner("Loading players..."):
            df = clean_player_stats(get_player_season_stats())
            if search:
                df = df[df["player_name"].str.contains(search, case=False, na=False)]
            if team_filter:
                df = df[df["team"].str.upper() == team_filter.upper()]
            df = df.head(limit)

        if not df.empty:
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Players", len(df))
            m2.metric("Top Scorer", f"{df.iloc[0]['pts']:.1f} PPG")
            m3.metric("Avg PPG", f"{df['pts'].mean():.1f}")
            m4.metric("Avg FG%", f"{df['fg_pct'].mean()*100:.1f}%")

        st.markdown("#### Top Players")
        card_cols = st.columns(min(3, max(1, len(df))))
        for i, col in enumerate(card_cols):
            if i < len(df):
                with col:
                    render_player_card(df.iloc[i].to_dict())

        st.markdown("#### All Players")
        display_df = df[["player_name", "team", "games_played", "pts", "reb", "ast", "stl", "blk", "fg_pct", "fg3_pct", "ft_pct", "plus_minus"]].copy()
        display_df.columns = ["Player", "Team", "GP", "PTS", "REB", "AST", "STL", "BLK", "FG%", "3PT%", "FT%", "+/-"]
        for col in ["FG%", "3PT%", "FT%"]:
            display_df[col] = (display_df[col] * 100).round(1)
        st.dataframe(display_df, use_container_width=True, hide_index=True, height=500)

    else:  # NFL
        from data.nfl_fetch import get_player_season_stats as nfl_players
        from data.nfl_transform import clean_player_stats as clean_nfl

        col_search, col_pos, col_limit = st.columns([3, 1, 1])
        with col_search:
            search = st.text_input("Search player", placeholder="e.g. Mahomes", label_visibility="collapsed")
        with col_pos:
            pos_filter = st.selectbox("Position", ["All", "QB", "RB", "WR", "TE"], label_visibility="collapsed")
        with col_limit:
            limit = st.selectbox("Show", [25, 50, 100, 200], index=1, label_visibility="collapsed")

        with st.spinner("Loading players..."):
            df = clean_nfl(nfl_players())
            if not df.empty:
                if search:
                    df = df[df["player_name"].str.contains(search, case=False, na=False)]
                if pos_filter != "All":
                    df = df[df["pos_group"] == pos_filter]
                df = df.sort_values("fantasy_points", ascending=False).head(limit)

        if df.empty:
            st.info("No NFL players match your filters. Try widening the search or refreshing the data.")
        else:
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Players", len(df))
            m2.metric("Top Passer", f"{int(df['passing_yards'].max()):,} yds")
            m3.metric("Top Rusher", f"{int(df['rushing_yards'].max()):,} yds")
            m4.metric("Top Receiver", f"{int(df['receiving_yards'].max()):,} yds")

            st.markdown("#### Top Players")
            card_cols = st.columns(min(3, len(df)))
            for i, col in enumerate(card_cols):
                if i < len(df):
                    with col:
                        render_nfl_player_card(df.iloc[i].to_dict())

            st.markdown("#### All Players")
            display_df = df[["player_name", "team", "pos_group", "games", "passing_yards", "passing_tds", "rushing_yards", "rushing_tds", "receptions", "receiving_yards", "receiving_tds", "fantasy_points"]].copy()
            display_df.columns = ["Player", "Team", "Pos", "G", "Pass Yds", "Pass TD", "Rush Yds", "Rush TD", "Rec", "Rec Yds", "Rec TD", "Fantasy"]
            for c in ["Pass Yds", "Pass TD", "Rush Yds", "Rush TD", "Rec", "Rec Yds", "Rec TD"]:
                display_df[c] = display_df[c].astype(int)
            display_df["Fantasy"] = display_df["Fantasy"].round(1)
            st.dataframe(display_df, use_container_width=True, hide_index=True, height=500)


# ── Page: Standings ──────────────────────────────────────────────────

elif page == "🏆 Standings":
    st.markdown(f"### 🏆 {cfg['icon']} Team Standings")

    if sport == "nba":
        from data.fetch_stats import get_team_standings, get_team_stats_advanced
        from data.transform import clean_standings, clean_team_advanced

        with st.spinner("Loading standings..."):
            standings = clean_standings(get_team_standings())
            advanced = clean_team_advanced(get_team_stats_advanced())

            teams_data = []
            for _, row in standings.iterrows():
                adv = advanced[advanced["team_id"] == row["team_id"]]
                teams_data.append({
                    "team_id": int(row["team_id"]),
                    "team": row["team"],
                    "name": f"{row['city']} {row['name']}",
                    "conference": row["conference"],
                    "seed": int(row["seed"]),
                    "wins": int(row["wins"]),
                    "losses": int(row["losses"]),
                    "win_pct": row["win_pct"],
                    "streak": row["streak"],
                    "off_rating": round(adv.iloc[0]["off_rating"], 1) if not adv.empty else None,
                    "def_rating": round(adv.iloc[0]["def_rating"], 1) if not adv.empty else None,
                    "net_rating": round(adv.iloc[0]["net_rating"], 1) if not adv.empty else None,
                    "pace": round(adv.iloc[0]["pace"], 1) if not adv.empty else None,
                })

        m1, m2, m3 = st.columns(3)
        best = max(teams_data, key=lambda t: t["win_pct"])
        best_off = max(teams_data, key=lambda t: t["off_rating"] or 0)
        best_def = min(teams_data, key=lambda t: t["def_rating"] or 999)
        m1.metric("Best Record", best["name"], f"{best['wins']}-{best['losses']}")
        m2.metric("Best Offense", best_off["name"], f"{best_off['off_rating']} ORTG")
        m3.metric("Best Defense", best_def["name"], f"{best_def['def_rating']} DRTG")

        tab_east, tab_west = st.tabs(["Eastern Conference", "Western Conference"])
        east = sorted([t for t in teams_data if t["conference"] == "East"], key=lambda t: t["seed"])
        west = sorted([t for t in teams_data if t["conference"] == "West"], key=lambda t: t["seed"])
        with tab_east:
            render_standings_table(east, "Eastern Conference")
        with tab_west:
            render_standings_table(west, "Western Conference")

        st.markdown("#### Top Teams")
        top3 = sorted(teams_data, key=lambda t: t["win_pct"], reverse=True)[:3]
        for col, team in zip(st.columns(3), top3):
            with col:
                render_team_card(team)

    else:  # NFL
        from data.nfl_fetch import get_schedules, get_team_meta
        from data.nfl_transform import compute_standings

        with st.spinner("Computing standings..."):
            teams_data = compute_standings(get_schedules(), get_team_meta())

        if not teams_data:
            st.info("NFL standings are not available yet. This is expected in the offseason before games are played. Refresh once the season begins.")
        else:
            def _ppg(t):
                return t["points_for"] / t["games"] if t["games"] else 0

            def _pa_pg(t):
                return t["points_against"] / t["games"] if t["games"] else 999

            m1, m2, m3 = st.columns(3)
            best = max(teams_data, key=lambda t: (t["win_pct"], t["point_diff"]))
            best_off = max(teams_data, key=_ppg)
            best_def = min(teams_data, key=_pa_pg)
            rec = f"{best['wins']}-{best['losses']}" + (f"-{best['ties']}" if best["ties"] else "")
            m1.metric("Best Record", best["name"], rec)
            m2.metric("Best Offense", best_off["name"], f"{_ppg(best_off):.1f} PPG")
            m3.metric("Best Defense", best_def["name"], f"{_pa_pg(best_def):.1f} PA/G")

            tab_afc, tab_nfc = st.tabs(["AFC", "NFC"])
            afc = [t for t in teams_data if t["conference"] == "AFC"]
            nfc = [t for t in teams_data if t["conference"] == "NFC"]
            with tab_afc:
                render_nfl_standings_table(afc, "AFC")
            with tab_nfc:
                render_nfl_standings_table(nfc, "NFC")

            st.markdown("#### Top Teams")
            top3 = sorted(teams_data, key=lambda t: (t["win_pct"], t["point_diff"]), reverse=True)[:3]
            for col, team in zip(st.columns(3), top3):
                with col:
                    render_nfl_team_card(team)


# ── Page: Compare ────────────────────────────────────────────────────

elif page == "⚔️ Compare":
    st.markdown(f"### ⚔️ {cfg['icon']} Player Comparison")
    st.caption("Select two players for a head-to-head stat breakdown")

    if sport == "nba":
        render_comparison()
    else:
        render_nfl_comparison()
