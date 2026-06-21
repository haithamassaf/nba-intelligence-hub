"""
NFL trade simulator.

Legality is cap-based (NFL has no salary matching). Each player's cap charge is
his OverTheCap APY, and a team's commitment is the sum of its top-51 APYs, which
mirrors the offseason top-51 rule. Net cap change between teams is exact; the
absolute cap-space number depends on NFL_SALARY_CAP, which should be set to the
current league-year cap. Beyond legality, every trade is scored by how it moves
each team's position grades and needs, using the grading engine.
"""

import pandas as pd

try:
    from config.settings import NFL_SALARY_CAP
except ImportError:  # tolerate an older settings.py that predates this constant
    import os
    NFL_SALARY_CAP = float(os.getenv("NFL_SALARY_CAP", "300.0"))
from grading.team_report import position_grades, overall_grade, needs as team_needs, to_letter

TOP_N = 51
UPGRADE_MARGIN = 4.0   # a target must beat the team's current group grade by this


def attach_cap(graded: pd.DataFrame, contracts: pd.DataFrame) -> pd.DataFrame:
    """Add an `apy` column to the graded table by matching on gsis_id."""
    g = graded.copy()
    if contracts is None or contracts.empty or "gsis_id" not in contracts.columns or "gsis_id" not in g.columns:
        g["apy"] = float("nan")
        return g
    c = contracts[["gsis_id", "apy"]].drop_duplicates("gsis_id")
    g = g.merge(c, on="gsis_id", how="left")
    return g


def _committed(df: pd.DataFrame, top_n: int = TOP_N) -> float:
    apy = pd.to_numeric(df.get("apy"), errors="coerce").dropna().sort_values(ascending=False)
    return float(apy.head(top_n).sum())


def _apy_sum(df: pd.DataFrame) -> float:
    return float(pd.to_numeric(df.get("apy"), errors="coerce").fillna(0).sum())


def team_cap_space(graded: pd.DataFrame, team: str, cap: float = NFL_SALARY_CAP) -> float:
    return round(cap - _committed(graded[graded["team"] == team]), 2)


def _team_snapshot(roster: pd.DataFrame, sport: str = "nfl") -> dict:
    pos = position_grades(roster, "group", "_wt")
    return {
        "overall": overall_grade(pos, sport),
        "positions": pos,
        "needs": team_needs(pos),
    }


def evaluate_trade(graded: pd.DataFrame, team_a: str, team_b: str,
                   send_a: list[str], send_b: list[str], cap: float = NFL_SALARY_CAP) -> dict:
    """
    send_a / send_b are gsis_id lists leaving team_a / team_b respectively.
    Returns cap legality and the grade/needs impact for both teams.
    """
    a = graded[graded["team"] == team_a].copy()
    b = graded[graded["team"] == team_b].copy()
    out_a = a[a["gsis_id"].isin(send_a)]
    out_b = b[b["gsis_id"].isin(send_b)]

    new_a = pd.concat([a[~a["gsis_id"].isin(send_a)], out_b], ignore_index=True)
    new_b = pd.concat([b[~b["gsis_id"].isin(send_b)], out_a], ignore_index=True)

    cap_a_before, cap_a_after = _committed(a), _committed(new_a)
    cap_b_before, cap_b_after = _committed(b), _committed(new_b)

    def _player_rows(df):
        return [{"name": r.get("player_name"), "pos": r.get("position"),
                 "group": r.get("group"), "grade": round(float(r["grade"]), 1) if pd.notna(r.get("grade")) else None,
                 "apy": round(float(r["apy"]), 2) if pd.notna(r.get("apy")) else None}
                for _, r in df.iterrows()]

    return {
        "team_a": team_a, "team_b": team_b,
        "a_sends": _player_rows(out_a), "b_sends": _player_rows(out_b),
        "cap": {
            team_a: {"committed_before": round(cap_a_before, 2), "committed_after": round(cap_a_after, 2),
                     "space_after": round(cap - cap_a_after, 2), "legal": cap_a_after <= cap,
                     "apy_out": round(_apy_sum(out_a), 2), "apy_in": round(_apy_sum(out_b), 2)},
            team_b: {"committed_before": round(cap_b_before, 2), "committed_after": round(cap_b_after, 2),
                     "space_after": round(cap - cap_b_after, 2), "legal": cap_b_after <= cap,
                     "apy_out": round(_apy_sum(out_b), 2), "apy_in": round(_apy_sum(out_a), 2)},
        },
        "legal": (cap_a_after <= cap) and (cap_b_after <= cap),
        "impact": {
            team_a: {"before": _team_snapshot(a), "after": _team_snapshot(new_a)},
            team_b: {"before": _team_snapshot(b), "after": _team_snapshot(new_b)},
        },
    }


def suggest_trades(graded: pd.DataFrame, team_a: str, cap: float = NFL_SALARY_CAP,
                   max_per_need: int = 3) -> list[dict]:
    """
    For team_a's biggest needs, find upgrade targets leaguewide and, where a
    cap-legal one-for-one return exists from team_a's surplus, attach it.
    """
    a = graded[graded["team"] == team_a].copy()
    snap = _team_snapshot(a)
    suggestions = []

    # team_a's surplus pieces to offer back, by APY (mid-tier, tradeable depth)
    a_offerable = a[pd.notna(a["grade"])].copy()
    a_offerable = a_offerable.sort_values("apy", ascending=False) if "apy" in a_offerable.columns else a_offerable

    for grp, grade, letter in snap["needs"]:
        targets = graded[(graded["group"] == grp) & (graded["team"] != team_a) & pd.notna(graded["grade"])]
        targets = targets[targets["grade"] >= grade + UPGRADE_MARGIN].sort_values("grade", ascending=False)
        count = 0
        for _, t in targets.iterrows():
            if count >= max_per_need:
                break
            t_apy = float(t["apy"]) if pd.notna(t.get("apy")) else None
            # find a comparable-APY return from team_a (not at the need position)
            ret = None
            if t_apy is not None and "apy" in a_offerable.columns:
                cand = a_offerable[(a_offerable["group"] != grp) & pd.notna(a_offerable["apy"])].copy()
                cand["d"] = (pd.to_numeric(cand["apy"], errors="coerce") - t_apy).abs()
                cand = cand.sort_values("d")
                if not cand.empty:
                    r = cand.iloc[0]
                    res = evaluate_trade(graded, team_a, t["team"], [r["gsis_id"]], [t["gsis_id"]], cap)
                    if res["legal"]:
                        ret = {"name": r.get("player_name"), "group": r.get("group"),
                               "apy": round(float(r["apy"]), 2), "grade": round(float(r["grade"]), 1)}
            suggestions.append({
                "need": grp, "current_grade": grade, "current_letter": letter,
                "target": t.get("player_name"), "target_team": t.get("team"),
                "target_grade": round(float(t["grade"]), 1), "target_letter": to_letter(float(t["grade"])),
                "target_apy": round(t_apy, 2) if t_apy is not None else None,
                "legal_return": ret,
            })
            count += 1
    return suggestions
