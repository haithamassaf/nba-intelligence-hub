"""NFL trade simulator view: players + picks, cap legality, cap chart, AI opinion."""

import pandas as pd
import streamlit as st

from trade.nfl_trade import evaluate_trade
from trade.picks import team_pick_options, picks_value, next_draft_year
from trade.analysis import analyze_trade
from frontend.components.charts import cap_space_chart


def _label(df: pd.DataFrame) -> dict:
    out = {}
    d = df.sort_values("apy", ascending=False, na_position="last") if "apy" in df.columns else df
    for _, r in d.iterrows():
        apy = f", ${round(float(r['apy']),1)}M" if pd.notna(r.get("apy")) else ""
        out[f"{r['player_name']} ({r.get('position','')}{apy})"] = r["gsis_id"]
    return out


def render_trades(table: pd.DataFrame, team_names: dict):
    st.markdown("#### Trade simulator")
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
    base_year = next_draft_year()
    pick_opts = team_pick_options(base_year)

    left, right = st.columns(2)
    with left:
        st.markdown(f"**{team_names.get(ta, ta)} sends**")
        sa = st.multiselect("Players", list(a_opts.keys()), key="t_pa")
        pa = st.multiselect("Draft picks", pick_opts, key="t_picka")
    with right:
        st.markdown(f"**{team_names.get(tb, tb)} sends**")
        sb = st.multiselect("Players", list(b_opts.keys()), key="t_pb")
        pb = st.multiselect("Draft picks", pick_opts, key="t_pickb")

    if st.button("Evaluate trade", type="primary"):
        send_a = [a_opts[x] for x in sa]
        send_b = [b_opts[x] for x in sb]
        if not (send_a or send_b or pa or pb):
            st.warning("Add at least one player or pick.")
        else:
            res = evaluate_trade(table, ta, tb, send_a, send_b)
            _render(res, team_names, ta, tb, pa, pb, base_year)


def _render(res, team_names, ta, tb, pa, pb, base_year):
    st.markdown("---")
    if res["legal"]:
        st.success("Cap-legal for both teams")
    else:
        st.error("Not cap-legal as built")

    cap = res["cap"]
    na, nb = team_names.get(ta, ta), team_names.get(tb, tb)

    def _space_before(c):
        return round(c["space_after"] + c["committed_after"] - c["committed_before"], 2)

    st.plotly_chart(
        cap_space_chart([
            (na, _space_before(cap[ta]), cap[ta]["space_after"]),
            (nb, _space_before(cap[tb]), cap[tb]["space_after"]),
        ]),
        use_container_width=True,
    )

    for code, sends, picks_sent in [(ta, res["a_sends"], pa), (tb, res["b_sends"], pb)]:
        c = cap[code]
        st.markdown(f"**{team_names.get(code, code)}**")
        st.caption(
            f"Cap space after ${c['space_after']}M ({'legal' if c['legal'] else 'OVER CAP'}) "
            f"&nbsp;|&nbsp; APY out ${c['apy_out']}M, in ${c['apy_in']}M"
        )
        assets = [f"{p['name']}" + (f" (${p['apy']}M)" if p["apy"] is not None else "") for p in sends] + list(picks_sent)
        st.caption("Sends: " + (", ".join(assets) if assets else "nothing"))

    summary = {
        "team_a": na, "team_b": nb,
        "a_sends": res["a_sends"], "b_sends": res["b_sends"],
        "a_picks": list(pa), "b_picks": list(pb),
        "a_pick_value": picks_value(list(pa), base_year),
        "b_pick_value": picks_value(list(pb), base_year),
        "cap": {na: cap[ta], nb: cap[tb]},
        "legal": res["legal"],
    }
    st.markdown("**Trade analysis**")
    with st.spinner("Analyzing the trade..."):
        st.write(analyze_trade(summary))
