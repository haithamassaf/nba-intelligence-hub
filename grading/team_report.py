"""
Roll player grades up to team-by-position grades, an overall team grade, and a
ranked list of roster needs. The deterministic summary here is also the fallback
when no Anthropic key is set.
"""

import math
import pandas as pd

from grading.scale import to_letter

NEED_THRESHOLD = 72.0   # team position grade below this is flagged as a need

# Positional importance for the overall team grade
IMPORTANCE = {
    "nfl": {"QB": .20, "OL": .15, "WR": .12, "DL": .14, "DB": .13, "LB": .09, "RB": .07, "TE": .06, "ST": .04, "OTHER": .0},
    "nba": {"Guard": .34, "Wing": .34, "Big-Wing": .10, "Big": .22},
}

# How many top players define the "starters" shown per group
STARTERS = {
    "QB": 1, "RB": 2, "WR": 3, "TE": 2, "OL": 5, "DL": 4, "LB": 4, "DB": 4, "ST": 1,
    "Guard": 3, "Wing": 4, "Big-Wing": 2, "Big": 2, "OTHER": 2,
}


def _num(s):
    return pd.to_numeric(s, errors="coerce")


def position_grades(df: pd.DataFrame, group_col: str, weight_col: str) -> dict:
    """
    Per position group: a playing-time-weighted team grade, plus the top players.
    Starters dominate the grade via the weight column (snaps or minutes).
    """
    out = {}
    graded = df[df["grade"].notna()]
    name_col = next((c for c in ("player_name", "PLAYER_NAME", "PLAYER", "player") if c in graded.columns), None)
    for grp, sub in graded.groupby(group_col):
        w = _num(sub[weight_col]) if weight_col in sub.columns else pd.Series([float("nan")] * len(sub), index=sub.index)
        if w.notna().sum() == 0 or w.fillna(0).sum() == 0:
            w = pd.Series([1.0] * len(sub), index=sub.index)
        w = w.fillna(0.0)
        if w.sum() == 0:
            w = pd.Series([1.0] * len(sub), index=sub.index)
        grade = float((sub["grade"] * w).sum() / w.sum())

        order = sub.assign(_w=w).sort_values("_w", ascending=False)
        n_top = STARTERS.get(grp, 2)
        top = [(r[name_col] if name_col else "Unknown", round(float(r["grade"]), 1),
                ("R" if bool(r.get("rookie", False)) else ""))
               for _, r in order.head(n_top).iterrows()]
        out[grp] = {
            "grade": round(grade, 1),
            "letter": to_letter(grade),
            "n_players": int(len(sub)),
            "top": top,
        }
    return out


def overall_grade(pos: dict, sport: str) -> float:
    imp = IMPORTANCE.get(sport, {})
    num = wsum = 0.0
    for grp, info in pos.items():
        w = imp.get(grp, 0.05)
        num += info["grade"] * w
        wsum += w
    return round(num / wsum, 1) if wsum else float("nan")


def needs(pos: dict) -> list:
    """Position groups below the need threshold, weakest first."""
    flagged = [(g, info["grade"], info["letter"]) for g, info in pos.items() if info["grade"] < NEED_THRESHOLD]
    return sorted(flagged, key=lambda x: x[1])


def best_unit(pos: dict):
    if not pos:
        return None
    g = max(pos.items(), key=lambda kv: kv[1]["grade"])
    return (g[0], g[1]["grade"], g[1]["letter"])


def deterministic_summary(team_name: str, pos: dict, sport: str) -> str:
    """Plain-language team summary built only from the computed grades."""
    if not pos:
        return f"{team_name}: not enough graded players to assess."

    ov = overall_grade(pos, sport)
    best = best_unit(pos)
    nd = needs(pos)

    parts = [f"{team_name} grades out at {to_letter(ov)} overall ({ov})."]
    if best:
        parts.append(f"Their strongest unit is {best[0]} ({best[2]}, {best[1]}).")
    if nd:
        need_str = ", ".join(f"{g} ({lt}, {sc})" for g, sc, lt in nd[:3])
        parts.append(f"Priority needs: {need_str}.")
        weakest = nd[0]
        parts.append(
            f"{weakest[0]} is the most pressing hole at {weakest[2]} and should be "
            f"the top target this offseason."
        )
    else:
        parts.append("No position group grades below the need line, so this is a deep, balanced roster.")
    return " ".join(parts)
