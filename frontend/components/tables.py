"""Roster table and player-compare rendering."""

import pandas as pd
import streamlit as st


def _num(s):
    return pd.to_numeric(s, errors="coerce")


def render_roster_table(df: pd.DataFrame, columns: list[tuple[str, str]]):
    avail = [(c, l) for c, l in columns if c in df.columns]
    show = df[[c for c, _ in avail]].copy()
    show.columns = [l for _, l in avail]
    if "APY" in show.columns:
        show["APY"] = _num(show["APY"]).round(1)
        show = show.sort_values("APY", ascending=False, na_position="last")
    st.dataframe(show, hide_index=True, use_container_width=True)


def _fmt(v):
    try:
        return round(float(v), 2)
    except (TypeError, ValueError):
        return v if (v is not None and not (isinstance(v, float) and pd.isna(v))) else "—"


def render_compare(df: pd.DataFrame, name_col: str, stat_cols: list[tuple[str, str]], key: str,
                   radar_axes: list[tuple[str, str]] | None = None):
    from frontend.components.charts import radar, grouped_bars
    st.markdown("#### Compare players")
    names = sorted(df[name_col].dropna().astype(str).unique())
    if len(names) < 2:
        st.info("Not enough players loaded to compare.")
        return
    c1, c2 = st.columns(2)
    with c1:
        p1 = st.selectbox("Player 1", names, key=f"{key}_c1")
    with c2:
        p2 = st.selectbox("Player 2", names, index=1, key=f"{key}_c2")

    r1 = df[df[name_col].astype(str) == p1].iloc[0]
    r2 = df[df[name_col].astype(str) == p2].iloc[0]

    if radar_axes:
        axes = [(lbl, r1.get(src), r2.get(src)) for src, lbl in radar_axes if src in df.columns]
        if axes:
            st.plotly_chart(radar(p1, p2, axes), use_container_width=True)
            st.caption("Radar shows relative strength: on each axis the higher player fills to the edge.")
    else:
        items = [(lbl, _num(pd.Series([r1.get(src)]))[0], _num(pd.Series([r2.get(src)]))[0])
                 for src, lbl in stat_cols if src in df.columns]
        items = [it for it in items if (pd.notna(it[1]) and it[1]) or (pd.notna(it[2]) and it[2])]
        if items:
            st.plotly_chart(grouped_bars(p1, p2, items), use_container_width=True)

    rows = [{"Stat": label, p1: _fmt(r1.get(src)), p2: _fmt(r2.get(src))}
            for src, label in stat_cols if src in df.columns]
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
