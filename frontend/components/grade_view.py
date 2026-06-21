"""Rendering helpers for grades, position breakdowns, and roster tables."""

import pandas as pd
import streamlit as st


def color_for(letter: str) -> str:
    if not letter:
        return "#9e9e9e"
    if letter.startswith("A"):
        return "#1a9850"
    if letter.startswith("B"):
        return "#66bd63"
    if letter.startswith("C"):
        return "#f6c344"
    if letter.startswith("D"):
        return "#fb9a3c"
    return "#d73027"  # F / NR


def chip(letter: str, score) -> str:
    c = color_for(letter)
    try:
        s = f"{float(score):.0f}"
    except (TypeError, ValueError):
        s = "--"
    return (f"<span style='background:{c};color:#111;padding:2px 9px;border-radius:6px;"
            f"font-weight:700;font-size:0.95em'>{letter} · {s}</span>")


def render_overall(team_name: str, overall: float, letter: str):
    st.markdown(f"### {team_name}")
    st.markdown(f"Overall roster grade &nbsp; {chip(letter, overall)}", unsafe_allow_html=True)


def render_position_grades(pos: dict):
    st.markdown("#### Position grades")
    for grp, info in sorted(pos.items(), key=lambda kv: -kv[1]["grade"]):
        c1, c2 = st.columns([1, 4], vertical_alignment="center")
        with c1:
            st.markdown(chip(info["letter"], info["grade"]), unsafe_allow_html=True)
            st.caption(f"{grp} · {info['n_players']}")
        with c2:
            st.progress(min(1.0, max(0.0, info["grade"] / 100)))
            tops = ", ".join(
                f"{n} ({g:.0f}{'·R' if r else ''})" for n, g, r in info["top"]
            )
            st.caption(tops if tops else "—")


def render_roster(df: pd.DataFrame, columns: list[tuple[str, str]]):
    """columns: list of (source_col, display_label)."""
    st.markdown("#### Roster")
    avail = [(c, lbl) for c, lbl in columns if c in df.columns for lbl in [lbl]]
    show = df[[c for c, _ in avail]].copy()
    show.columns = [lbl for _, lbl in avail]
    if "Grade" in show.columns:
        show = show.sort_values("Grade", ascending=False)
        show["Grade"] = pd.to_numeric(show["Grade"], errors="coerce").round(1)
    st.dataframe(show, use_container_width=True, hide_index=True)
