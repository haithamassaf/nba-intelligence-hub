"""Compare-players and player-stats views (shared by both sports)."""

import pandas as pd
import streamlit as st

from frontend.components.grade_view import chip


def _num(s):
    return pd.to_numeric(s, errors="coerce")


def _fmt(v):
    try:
        return round(float(v), 2)
    except (TypeError, ValueError):
        return v if v is not None and not (isinstance(v, float) and pd.isna(v)) else "—"


def render_compare(graded, name_col, group_col, stat_cols, key):
    st.markdown("#### Compare players")
    names = sorted(graded[name_col].dropna().astype(str).unique())
    if len(names) < 2:
        st.info("Not enough players loaded to compare.")
        return
    c1, c2 = st.columns(2)
    with c1:
        p1 = st.selectbox("Player 1", names, key=f"{key}_cmp1")
    with c2:
        p2 = st.selectbox("Player 2", names, index=1, key=f"{key}_cmp2")

    r1 = graded[graded[name_col].astype(str) == p1].iloc[0]
    r2 = graded[graded[name_col].astype(str) == p2].iloc[0]

    h1, h2 = st.columns(2)
    for col, r in [(h1, r1), (h2, r2)]:
        with col:
            g = r.get("grade")
            st.markdown(f"**{r[name_col]}** &nbsp; {r.get(group_col, '')}")
            st.markdown(chip(r.get("letter", "NR"), g if pd.notna(g) else float("nan")), unsafe_allow_html=True)

    rows = [{"Stat": "Grade", p1: _fmt(r1.get("grade")), p2: _fmt(r2.get("grade"))}]
    for src, label in stat_cols:
        if src in graded.columns:
            rows.append({"Stat": label, p1: _fmt(r1.get(src)), p2: _fmt(r2.get(src))})
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)


def render_stats(graded, name_col, group_col, team_col, stat_cols, team_names, key):
    st.markdown("#### Player stats")
    codes = sorted(graded[team_col].dropna().astype(str).unique())
    pick = st.selectbox(
        "Team", ["All teams"] + codes,
        format_func=lambda c: team_names.get(c, c) if c != "All teams" else c,
        key=f"{key}_stats_team",
    )
    df = graded if pick == "All teams" else graded[graded[team_col].astype(str) == pick]

    cols = [(name_col, "Player"), (group_col, "Unit"), ("grade", "Grade"), ("letter", "Letter")]
    cols += [(s, l) for s, l in stat_cols if s in df.columns]
    avail = [(c, l) for c, l in cols if c in df.columns]
    show = df[[c for c, _ in avail]].copy()
    show.columns = [l for _, l in avail]
    if "Grade" in show.columns:
        show["Grade"] = _num(show["Grade"]).round(1)
        show = show.sort_values("Grade", ascending=False)
    st.dataframe(show, hide_index=True, use_container_width=True)
