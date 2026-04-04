"""
NBA Intelligence Hub — Streamlit Frontend

Run with:
    streamlit run frontend/app.py
"""

import streamlit as st
from datetime import datetime

from rag.chain import ask, classify_query
from rag.vector_store import count as vector_count
from data.fetch_stats import get_player_season_stats, get_team_standings, get_team_stats_advanced
from data.transform import clean_player_stats, clean_standings, clean_team_advanced
from data.build_embeddings import build as rebuild_data

from frontend.components.chat import render_chat_history, add_message, render_message
from frontend.components.stats_card import render_player_card, render_team_card, render_standings_table
from frontend.components.player_compare import render_comparison


# ── Page Config ──────────────────────────────────────────────────────

st.set_page_config(
    page_title="NBA Intelligence Hub",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ───────────────────────────────────────────────────────

st.markdown("""
<style>
    /* Dark theme refinements */
    .stApp {
        background-color: #0e1117;
    }

    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #161b22;
    }

    /* Chat input styling */
    .stChatInput {
        border-color: #30363d !important;
    }

    /* Metric cards */
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 8px;
        padding: 12px 16px;
        border: 1px solid #30363d;
    }
    [data-testid="stMetricValue"] {
        font-size: 24px;
        font-weight: 700;
    }
    [data-testid="stMetricLabel"] {
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: #8b949e;
    }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 6px;
        padding: 8px 16px;
    }

    /* Header */
    .hub-header {
        text-align: center;
        padding: 20px 0 10px 0;
    }
    .hub-header h1 {
        font-size: 28px;
        font-weight: 800;
        background: linear-gradient(135deg, #007AC1, #F58426);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 4px;
    }
    .hub-header p {
        color: #8b949e;
        font-size: 14px;
    }

    /* Dataframe styling */
    .stDataFrame {
        border-radius: 8px;
        overflow: hidden;
    }
</style>
""", unsafe_allow_html=True)


# ── Session State Init ───────────────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_refreshed" not in st.session_state:
    st.session_state.last_refreshed = None
if "last_classification" not in st.session_state:
    st.session_state.last_classification = None


# ── Sidebar ──────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        '<div class="hub-header">'
        '<h1>🏀 NBA Intelligence Hub</h1>'
        '<p>AI-powered NBA analytics</p>'
        '<p style="color:#555;font-size:12px;margin-top:8px">Built by Haitham Assaf</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # Navigation
    page = st.radio(
        "Navigate",
        ["💬 Ask", "📊 Players", "🏆 Standings", "⚔️ Compare"],
        label_visibility="collapsed",
    )

    st.markdown("---")

    # Data status
    st.markdown("##### Data Status")
    doc_count = vector_count()
    st.caption(f"📄 {doc_count} documents indexed")

    if st.session_state.last_refreshed:
        st.caption(f"🕐 Last updated: {st.session_state.last_refreshed}")
    else:
        st.caption("🕐 Last updated: this session")

    # Refresh button
    if st.button("🔄 Refresh Data", use_container_width=True):
        with st.spinner("Fetching fresh NBA data..."):
            rebuild_data(fresh=True)
            st.session_state.last_refreshed = datetime.now().strftime("%b %d, %I:%M %p")
        st.success("Data refreshed!")
        st.rerun()

    st.markdown("---")

    # Quick prompts
    st.markdown("##### Quick Questions")
    prompts = [
        "Who's playing the best basketball right now?",
        "Compare Luka and Shai's stats",
        "Who should win MVP?",
        "Which teams have the best defense?",
        "How has Jayson Tatum been playing?",
    ]
    for p in prompts:
        if st.button(p, use_container_width=True, key=f"qp_{p[:20]}"):
            st.session_state.pending_question = p
            st.session_state._nav_to_chat = True
            st.rerun()


# ── Page: Ask (Chat) ────────────────────────────────────────────────

if page == "💬 Ask" or getattr(st.session_state, "_nav_to_chat", False):
    if getattr(st.session_state, "_nav_to_chat", False):
        st.session_state._nav_to_chat = False

    st.markdown("### 💬 Ask anything about the NBA")
    st.caption("Powered by real-time stats and Claude AI")

    # Render chat history
    render_chat_history()

    # Handle pending question from sidebar
    pending = st.session_state.pop("pending_question", None)

    # Chat input
    user_input = st.chat_input("Ask about players, teams, stats, MVP race...")

    question = pending or user_input

    if question:
        # Show user message
        add_message("user", question)
        render_message("user", question)

        # Generate answer
        with st.chat_message("assistant", avatar="🏀"):
            with st.spinner("Analyzing stats..."):
                classification = classify_query(question)
                st.session_state.last_classification = classification
                answer = ask(question)

            st.markdown(answer)
            add_message("assistant", answer)

            # Show classification as an expander
            with st.expander("🔍 Query details"):
                st.json(classification)


# ── Page: Players ────────────────────────────────────────────────────

elif page == "📊 Players":
    st.markdown("### 📊 Player Stats")

    col_search, col_team, col_limit = st.columns([3, 1, 1])
    with col_search:
        search = st.text_input("Search player", placeholder="e.g. LeBron", label_visibility="collapsed")
    with col_team:
        team_filter = st.text_input("Team", placeholder="e.g. OKC", label_visibility="collapsed")
    with col_limit:
        limit = st.selectbox("Show", [25, 50, 100, 200], index=1, label_visibility="collapsed")

    with st.spinner("Loading players..."):
        raw = get_player_season_stats()
        df = clean_player_stats(raw)

        if search:
            df = df[df["player_name"].str.contains(search, case=False, na=False)]
        if team_filter:
            df = df[df["team"].str.upper() == team_filter.upper()]

        df = df.head(limit)

    # Summary metrics
    if not df.empty:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Players", len(df))
        m2.metric("Top Scorer", f"{df.iloc[0]['pts']:.1f} PPG")
        m3.metric("Avg PPG", f"{df['pts'].mean():.1f}")
        m4.metric("Avg FG%", f"{df['fg_pct'].mean()*100:.1f}%")

    # Top 3 player cards
    st.markdown("#### Top Players")
    card_cols = st.columns(min(3, len(df)))
    for i, col in enumerate(card_cols):
        if i < len(df):
            with col:
                row = df.iloc[i]
                render_player_card(row.to_dict())

    # Full table
    st.markdown("#### All Players")
    display_df = df[["player_name", "team", "games_played", "pts", "reb", "ast", "stl", "blk", "fg_pct", "fg3_pct", "ft_pct", "plus_minus"]].copy()
    display_df.columns = ["Player", "Team", "GP", "PTS", "REB", "AST", "STL", "BLK", "FG%", "3PT%", "FT%", "+/-"]
    # Format percentages
    for col in ["FG%", "3PT%", "FT%"]:
        display_df[col] = (display_df[col] * 100).round(1)

    st.dataframe(display_df, use_container_width=True, hide_index=True, height=500)


# ── Page: Standings ──────────────────────────────────────────────────

elif page == "🏆 Standings":
    st.markdown("### 🏆 Team Standings")

    with st.spinner("Loading standings..."):
        standings_raw = get_team_standings()
        advanced_raw = get_team_stats_advanced()
        standings = clean_standings(standings_raw)
        advanced = clean_team_advanced(advanced_raw)

        # Merge advanced into standings
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

    # League-wide metrics
    m1, m2, m3 = st.columns(3)
    best = max(teams_data, key=lambda t: t["win_pct"])
    best_off = max(teams_data, key=lambda t: t["off_rating"] or 0)
    best_def = min(teams_data, key=lambda t: t["def_rating"] or 999)
    m1.metric("Best Record", f"{best['name']}", f"{best['wins']}-{best['losses']}")
    m2.metric("Best Offense", f"{best_off['name']}", f"{best_off['off_rating']} ORTG")
    m3.metric("Best Defense", f"{best_def['name']}", f"{best_def['def_rating']} DRTG")

    # Conference tabs
    tab_east, tab_west = st.tabs(["Eastern Conference", "Western Conference"])

    east = [t for t in teams_data if t["conference"] == "East"]
    west = [t for t in teams_data if t["conference"] == "West"]
    east.sort(key=lambda t: t["seed"])
    west.sort(key=lambda t: t["seed"])

    with tab_east:
        render_standings_table(east, "Eastern Conference")
    with tab_west:
        render_standings_table(west, "Western Conference")

    # Top team cards
    st.markdown("#### Top Teams")
    top3 = sorted(teams_data, key=lambda t: t["win_pct"], reverse=True)[:3]
    card_cols = st.columns(3)
    for col, team in zip(card_cols, top3):
        with col:
            render_team_card(team)


# ── Page: Compare ────────────────────────────────────────────────────

elif page == "⚔️ Compare":
    st.markdown("### ⚔️ Player Comparison")
    st.caption("Select two players for a head-to-head stat breakdown")

    render_comparison()
