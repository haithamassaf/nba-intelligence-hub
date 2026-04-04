"""Stat cards displayed alongside chat answers."""

import streamlit as st
import pandas as pd


# ── Team color palette ───────────────────────────────────────────────

TEAM_COLORS = {
    "ATL": "#E03A3E", "BOS": "#007A33", "BKN": "#000000", "CHA": "#1D1160",
    "CHI": "#CE1141", "CLE": "#860038", "DAL": "#00538C", "DEN": "#0E2240",
    "DET": "#C8102E", "GSW": "#1D428A", "HOU": "#CE1141", "IND": "#002D62",
    "LAC": "#C8102E", "LAL": "#552583", "MEM": "#5D76A9", "MIA": "#98002E",
    "MIL": "#00471B", "MIN": "#0C2340", "NOP": "#0C2340", "NYK": "#F58426",
    "OKC": "#007AC1", "ORL": "#0077C0", "PHI": "#006BB6", "PHX": "#1D1160",
    "POR": "#E03A3E", "SAC": "#5A2D81", "SAS": "#C4CED4", "TOR": "#CE1141",
    "UTA": "#002B5C", "WAS": "#002B5C",
}


def _color_bar(pct: float, color: str = "#007AC1") -> str:
    """Return HTML for a thin progress bar."""
    width = max(0, min(100, pct * 100))
    return (
        f'<div style="background:#2a2a2a;border-radius:4px;height:6px;width:100%">'
        f'<div style="background:{color};border-radius:4px;height:6px;width:{width:.0f}%"></div>'
        f'</div>'
    )


def render_player_card(player: dict):
    """Render a compact player stat card."""
    team = player.get("team", "")
    color = TEAM_COLORS.get(team, "#007AC1")
    name = player.get("player_name", "Unknown")

    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            border-left: 4px solid {color};
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 8px;
        ">
            <div style="font-size:16px;font-weight:700;color:#fff;margin-bottom:8px">
                {name}
                <span style="color:{color};font-size:13px;margin-left:6px">{team}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    cols = st.columns(4)
    stats = [
        ("PTS", player.get("pts", 0)),
        ("REB", player.get("reb", 0)),
        ("AST", player.get("ast", 0)),
        ("FG%", f"{player.get('fg_pct', 0) * 100:.1f}"),
    ]
    for col, (label, val) in zip(cols, stats):
        col.metric(label, val)



def render_team_card(team: dict):
    """Render a team standings card."""
    abbr = team.get("team", "")
    color = TEAM_COLORS.get(abbr, "#007AC1")
    name = team.get("name", "Unknown")
    record = f"{team.get('wins', 0)}-{team.get('losses', 0)}"

    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            border-left: 4px solid {color};
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 8px;
        ">
            <div style="font-size:16px;font-weight:700;color:#fff;margin-bottom:4px">
                #{team.get('seed', '-')} {name}
                <span style="color:{color};font-size:13px;margin-left:6px">{record}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    cols = st.columns(4)
    metrics = [
        ("OFF RTG", team.get("off_rating")),
        ("DEF RTG", team.get("def_rating")),
        ("NET RTG", team.get("net_rating")),
        ("PACE", team.get("pace")),
    ]
    for col, (label, val) in zip(cols, metrics):
        display = f"{val:.1f}" if val is not None else "—"
        col.metric(label, display)


def render_standings_table(teams: list[dict], title: str = "Standings"):
    """Render a full standings table."""
    if not teams:
        return

    rows = []
    for t in teams:
        rows.append({
            "Seed": t.get("seed", ""),
            "Team": t.get("name", ""),
            "W": t.get("wins", 0),
            "L": t.get("losses", 0),
            "PCT": f"{t.get('win_pct', 0):.3f}",
            "OFF": t.get("off_rating") or "—",
            "DEF": t.get("def_rating") or "—",
            "NET": t.get("net_rating") or "—",
            "Streak": t.get("streak", ""),
        })

    st.markdown(f"#### {title}")
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
