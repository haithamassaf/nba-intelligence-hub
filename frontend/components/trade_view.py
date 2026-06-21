"""NFL trade simulator view: build a trade, see cap legality."""

import pandas as pd
import streamlit as st

from trade.nfl_trade import evaluate_trade, NFL_SALARY_CAP


def _label(df: pd.DataFrame) -> dict:
    out = {}
    d = df.sort_values("apy", ascending=False, na_position="last") if "apy" in df.columns else df
    for _, r in d.iterrows():
        apy = f", ${round(float(r['apy']),1)}M" if pd.notna(r.get("apy")) else ""
        out[f"{r['player_name']} ({r.get('position','')}{apy})"] = r["gsis_id"]
    return out


def render_trades(table: pd.DataFrame, team_names: dict):
    st.markdown("#### Trade simulator")
    st.caption(
        f"NFL trades are cap-driven, no salary matching. Legality uses OverTheCap APY and the "
        f"top-51 rule against a ${NFL_SALARY_CAP:.0f}M cap (set NFL_SALARY_CAP to the current cap). "
        f"Net cap change between teams is exact."
    )
    if table.empty or "team" not in table.columns:
        st.error("No NFL data loaded.")
        return

    codes = sorted(table["team"].dropna().astype(str).unique())
    c1, c2 = st.columns(2)
    with c1:
        ta = st.selectbox("Team A", codes, format_func=lambda c: team_names.get(c, c), key="trade_a")
    with c2:
        tb = st.selectbox("Team B", [c for c in codes if c != ta], format_func=lambda c: team_names.get(c, c), key="trade_b")

    a = table[table["team"] == ta]
    b = table[table["team"] == tb]
    a_opts, b_opts = _label(a), _label(b)

    s1, s2 = st.columns(2)
    with s1:
        sa = st.multiselect(f"{team_names.get(ta, ta)} sends", list(a_opts.keys()), key="trade_sa")
    with s2:
        sb = st.multiselect(f"{team_names.get(tb, tb)} sends", list(b_opts.keys()), key="trade_sb")

    if st.button("Evaluate trade", type="primary"):
        send_a = [a_opts[x] for x in sa]
        send_b = [b_opts[x] for x in sb]
        if not send_a and not send_b:
            st.warning("Add at least one player.")
        else:
            _render_result(evaluate_trade(table, ta, tb, send_a, send_b), team_names)


def _render_result(res: dict, names: dict):
    st.markdown("---")
    if res["legal"]:
        st.success("Cap-legal for both teams")
    else:
        st.error("Not cap-legal as built")

    for team in (res["team_a"], res["team_b"]):
        cap = res["cap"][team]
        sends = res["a_sends"] if team == res["team_a"] else res["b_sends"]
        gets = res["b_sends"] if team == res["team_a"] else res["a_sends"]
        net = round(cap["apy_in"] - cap["apy_out"], 2)
        st.markdown(f"**{names.get(team, team)}**")
        st.caption(
            f"Cap space after ${cap['space_after']}M ({'legal' if cap['legal'] else 'OVER CAP'}) "
            f"&nbsp;|&nbsp; APY out ${cap['apy_out']}M, in ${cap['apy_in']}M "
            f"&nbsp;|&nbsp; net {'+' if net >= 0 else ''}{net}M"
        )

        def _names(rows):
            return ", ".join(f"{p['name']}" + (f" (${p['apy']}M)" if p["apy"] is not None else "") for p in rows)
        if sends:
            st.caption("Sends: " + _names(sends))
        if gets:
            st.caption("Gets: " + _names(gets))
