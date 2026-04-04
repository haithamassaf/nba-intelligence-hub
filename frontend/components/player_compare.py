"""Player comparison mode — side-by-side stat breakdown."""

import streamlit as st
import pandas as pd

from data.fetch_stats import get_player_season_stats
from data.transform import clean_player_stats
from frontend.components.stats_card import TEAM_COLORS


@st.cache_data(ttl=300)
def _get_all_players() -> pd.DataFrame:
    """Cached fetch of all player stats."""
    raw = get_player_season_stats()
    df = clean_player_stats(raw)
    return df[df["games_played"] >= 20].reset_index(drop=True)


def _stat_row(label: str, val1: float, val2: float, color1: str, color2: str, higher_is_better: bool = True):
    """Render one stat comparison row using Streamlit columns."""
    max_val = max(val1, val2, 0.01)

    if higher_is_better:
        winner = 1 if val1 >= val2 else 2
    else:
        winner = 1 if val1 <= val2 else 2

    left, center, right = st.columns([2, 1, 2])

    with left:
        w = "700" if winner == 1 else "400"
        bar_pct = val1 / max_val * 100
        st.markdown(
            f"""<div style="display:flex;align-items:center;justify-content:flex-end;gap:10px;height:32px">
                <span style="color:{color1};font-weight:{w};font-size:16px;min-width:45px;text-align:right">{val1:.1f}</span>
                <div style="width:60%;height:10px;background:#2a2a2a;border-radius:5px;overflow:hidden;direction:rtl">
                    <div style="width:{bar_pct:.0f}%;height:100%;background:{color1};border-radius:5px;opacity:{'1.0' if winner==1 else '0.35'}"></div>
                </div>
            </div>""",
            unsafe_allow_html=True,
        )

    with center:
        st.markdown(
            f"""<div style="text-align:center;height:32px;line-height:32px;color:#8b949e;font-weight:600;font-size:13px">
                {label}
            </div>""",
            unsafe_allow_html=True,
        )

    with right:
        w = "700" if winner == 2 else "400"
        bar_pct = val2 / max_val * 100
        st.markdown(
            f"""<div style="display:flex;align-items:center;gap:10px;height:32px">
                <div style="width:60%;height:10px;background:#2a2a2a;border-radius:5px;overflow:hidden">
                    <div style="width:{bar_pct:.0f}%;height:100%;background:{color2};border-radius:5px;opacity:{'1.0' if winner==2 else '0.35'}"></div>
                </div>
                <span style="color:{color2};font-weight:{w};font-size:16px;min-width:45px">{val2:.1f}</span>
            </div>""",
            unsafe_allow_html=True,
        )


def render_comparison():
    """Full comparison mode UI."""
    df = _get_all_players()
    player_names = df["player_name"].tolist()

    col1, col2 = st.columns(2)
    with col1:
        p1_name = st.selectbox("Player 1", player_names, index=0, key="cmp_p1")
    with col2:
        default_idx = min(1, len(player_names) - 1)
        p2_name = st.selectbox("Player 2", player_names, index=default_idx, key="cmp_p2")

    if p1_name == p2_name:
        st.warning("Select two different players to compare.")
        return

    p1 = df[df["player_name"] == p1_name].iloc[0]
    p2 = df[df["player_name"] == p2_name].iloc[0]

    color1 = TEAM_COLORS.get(p1["team"], "#007AC1")
    color2 = TEAM_COLORS.get(p2["team"], "#E03A3E")

    # Header
    h1, h2 = st.columns(2)
    h1.markdown(
        f"<div style='text-align:center;padding:16px 0'>"
        f"<div style='font-size:22px;font-weight:700;color:{color1}'>{p1_name}</div>"
        f"<div style='color:#8b949e;font-size:14px;margin-top:4px'>{p1['team']} | {int(p1['games_played'])} GP | Age {p1['age']:.0f}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )
    h2.markdown(
        f"<div style='text-align:center;padding:16px 0'>"
        f"<div style='font-size:22px;font-weight:700;color:{color2}'>{p2_name}</div>"
        f"<div style='color:#8b949e;font-size:14px;margin-top:4px'>{p2['team']} | {int(p2['games_played'])} GP | Age {p2['age']:.0f}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # Stat bars
    comparisons = [
        ("PTS", "pts", True),
        ("REB", "reb", True),
        ("AST", "ast", True),
        ("STL", "stl", True),
        ("BLK", "blk", True),
        ("FG%", "fg_pct", True),
        ("3PT%", "fg3_pct", True),
        ("FT%", "ft_pct", True),
        ("MIN", "minutes", True),
        ("TOV", "tov", False),
    ]

    for label, col, higher_better in comparisons:
        v1 = p1[col]
        v2 = p2[col]
        if col in ("fg_pct", "fg3_pct", "ft_pct"):
            v1 = v1 * 100
            v2 = v2 * 100
        _stat_row(label, v1, v2, color1, color2, higher_better)

    # Summary table
    st.markdown("---")
    st.markdown("#### Full Stat Sheet")

    stat_cols = ["pts", "reb", "ast", "stl", "blk", "tov", "fg_pct", "fg3_pct", "ft_pct", "minutes", "games_played", "plus_minus"]
    labels = ["PTS", "REB", "AST", "STL", "BLK", "TOV", "FG%", "3PT%", "FT%", "MIN", "GP", "+/-"]

    rows = []
    for label, col in zip(labels, stat_cols):
        v1 = p1[col]
        v2 = p2[col]
        if col in ("fg_pct", "fg3_pct", "ft_pct"):
            rows.append({"Stat": label, p1_name: f"{v1*100:.1f}%", p2_name: f"{v2*100:.1f}%"})
        else:
            rows.append({"Stat": label, p1_name: f"{v1:.1f}", p2_name: f"{v2:.1f}"})

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
