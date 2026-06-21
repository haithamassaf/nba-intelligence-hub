"""NFL trade simulator view: build a trade, see cap legality and grade impact."""

import pandas as pd
import streamlit as st

from frontend.components.grade_view import chip
from grading.team_report import to_letter
from trade.nfl_trade import evaluate_trade, suggest_trades
from config.settings import NFL_SALARY_CAP


def _label(df):
    out = {}
    for _, r in df.sort_values("grade", ascending=False).iterrows():
        apy = f", ${round(float(r['apy']),1)}M" if pd.notna(r.get("apy")) else ""
        out[f"{r['player_name']} ({r.get('group','')}, {r.get('letter','')}{apy})"] = r["gsis_id"]
    return out


def render_trades(graded, team_names):
    st.markdown("#### Trade simulator")
    st.caption(
        f"NFL trades are cap-driven, no salary matching. Legality uses OverTheCap APY and the "
        f"top-51 rule against a ${NFL_SALARY_CAP:.0f}M cap (set NFL_SALARY_CAP to the current cap). "
        f"Net cap change between teams is exact."
    )
    if graded.empty or "team" not in graded.columns:
        st.error("No NFL data loaded.")
        return

    codes = sorted(graded["team"].dropna().astype(str).unique())
    c1, c2 = st.columns(2)
    with c1:
        ta = st.selectbox("Team A", codes, format_func=lambda c: team_names.get(c, c), key="trade_a")
    with c2:
        tb = st.selectbox("Team B", [c for c in codes if c != ta], format_func=lambda c: team_names.get(c, c), key="trade_b")

    a = graded[graded["team"] == ta]
    b = graded[graded["team"] == tb]
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
            _render_result(evaluate_trade(graded, ta, tb, send_a, send_b), team_names)

    st.divider()
    if st.button(f"Suggest upgrades for {team_names.get(ta, ta)}"):
        sugg = suggest_trades(graded, ta)
        if not sugg:
            st.write("No upgrade targets grade clearly above the current groups.")
        for s in sugg:
            ret = s["legal_return"]
            apy = f", ${s['target_apy']}M" if s["target_apy"] is not None else ""
            line = (f"- **{s['need']}** ({s['current_letter']}, {s['current_grade']}): target "
                    f"**{s['target']}** ({s['target_letter']}, {team_names.get(s['target_team'], s['target_team'])}{apy})")
            line += (f" — send {ret['name']} (${ret['apy']}M) for a cap-legal one-for-one"
                     if ret else " — would need a matching-salary return")
            st.markdown(line)


def _render_result(res, names):
    st.markdown("---")
    if res["legal"]:
        st.success("Cap-legal for both teams")
    else:
        st.error("Not cap-legal as built")

    for team in (res["team_a"], res["team_b"]):
        cap = res["cap"][team]
        imp = res["impact"][team]
        bovr, aovr = imp["before"]["overall"], imp["after"]["overall"]
        delta = round(aovr - bovr, 1)
        arrow = f"+{delta}" if delta >= 0 else f"{delta}"
        st.markdown(f"**{names.get(team, team)}** &nbsp; {chip(to_letter(aovr), aovr)}", unsafe_allow_html=True)
        st.caption(
            f"Overall {bovr} → {aovr} ({arrow}) &nbsp;|&nbsp; cap space after ${cap['space_after']}M "
            f"({'legal' if cap['legal'] else 'OVER CAP'}) &nbsp;|&nbsp; APY out ${cap['apy_out']}M, in ${cap['apy_in']}M"
        )
        # position groups that changed
        before_pos = imp["before"]["positions"]
        after_pos = imp["after"]["positions"]
        changed = []
        for grp in sorted(set(before_pos) | set(after_pos)):
            bg = before_pos.get(grp, {}).get("grade")
            ag = after_pos.get(grp, {}).get("grade")
            if bg is not None and ag is not None and abs(ag - bg) >= 0.1:
                changed.append(f"{grp} {bg}→{ag}")
            elif bg is None and ag is not None:
                changed.append(f"{grp} new {ag}")
        if changed:
            st.caption("Position shifts: " + ", ".join(changed))
        after_needs = [n[0] for n in imp["after"]["needs"]]
        st.caption("Needs after: " + (", ".join(after_needs) if after_needs else "none"))
