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
