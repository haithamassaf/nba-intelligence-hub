"""Player comparison (with season/career dropdown + charts) and roster comparison."""

import pandas as pd
import streamlit as st

from frontend.components.charts import radar, grouped_bars
from frontend.components.tables import render_roster_table


def _fmt(v):
    try:
        f = float(v)
        return round(f, 2)
    except (TypeError, ValueError):
        return v if (v is not None and not (isinstance(v, float) and pd.isna(v))) else "—"


def _name_to_id(df, name_col, id_col):
    d = df.dropna(subset=[name_col, id_col]).drop_duplicates(name_col)
    return dict(zip(d[name_col].astype(str), d[id_col]))


def render_player_compare(table, name_col, id_col, get_splits, radar_keys, stat_labels, key, no_data_hint=""):
    """
    get_splits(player_id) -> {season_label: {stat: value}}, incl. a "Career" entry.
    radar_keys / stat_labels: list of (stat_key, display_label).
    """
    from data.compare_data import season_options
    st.markdown("#### Compare players")
    names = sorted(table[name_col].dropna().astype(str).unique())
    if len(names) < 2:
        st.info("Not enough players loaded to compare.")
        return
    name_id = _name_to_id(table, name_col, id_col)

    c1, c2 = st.columns(2)
    with c1:
        p1 = st.selectbox("Player 1", names, key=f"{key}_c1")
    with c2:
        p2 = st.selectbox("Player 2", names, index=1, key=f"{key}_c2")

    with st.spinner("Loading career stats..."):
        sa = get_splits(name_id.get(p1))
        sb = get_splits(name_id.get(p2))

    opts = season_options(sa, sb)
    if not opts:
        msg = "No season stats available for these two players."
        if no_data_hint:
            msg += " " + no_data_hint
        st.warning(msg)
        return
    season = st.selectbox("Season", opts, key=f"{key}_season")

    da = sa.get(season, {})
    db = sb.get(season, {})

    # Chart: radar if 3+ higher-is-better axes have data, else grouped bars
    axes = [(lbl, da.get(k), db.get(k)) for k, lbl in radar_keys]
    axes = [a for a in axes if (pd.notna(a[1]) and a[1]) or (pd.notna(a[2]) and a[2])]
    if len(axes) >= 3:
        st.plotly_chart(radar(p1, p2, axes), use_container_width=True)
        st.caption("Radar shows relative strength: on each axis the higher player fills to the edge.")
    elif axes:
        st.plotly_chart(grouped_bars(p1, p2, axes), use_container_width=True)

    rows = [{"Stat": lbl, p1: _fmt(da.get(k)), p2: _fmt(db.get(k))} for k, lbl in stat_labels]
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)


def render_roster_compare(table, team_col, name_for, summary_fn, roster_cols, key):
    st.markdown("#### Compare rosters")
    codes = sorted(table[team_col].dropna().astype(str).unique())
    c1, c2 = st.columns(2)
    with c1:
        ta = st.selectbox("Team A", codes, format_func=lambda c: name_for.get(c, c), key=f"{key}_ra")
    with c2:
        tb = st.selectbox("Team B", [c for c in codes if c != ta], format_func=lambda c: name_for.get(c, c), key=f"{key}_rb")

    a = table[table[team_col].astype(str) == ta]
    b = table[table[team_col].astype(str) == tb]
    na, nb = name_for.get(ta, ta), name_for.get(tb, tb)

    sa, sb = summary_fn(a), summary_fn(b)
    summary = pd.DataFrame([{"Metric": m, na: sa.get(m), nb: sb.get(m)} for m in sa])
    st.dataframe(summary, hide_index=True, use_container_width=True)

    left, right = st.columns(2)
    with left:
        st.markdown(f"**{na}**")
        render_roster_table(a, roster_cols)
    with right:
        st.markdown(f"**{nb}**")
        render_roster_table(b, roster_cols)
