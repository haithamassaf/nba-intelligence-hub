"""
NBA player grading.

Each player is scored 0-100 against position peers (Guard / Wing / Big) on a
weighted blend of advanced stats. Inputs come from fetch_stats.fetch_league_players
(base + advanced merged) with a `bucket` and `position` attached from rosters.
Plus-minus and net rating feed the impact component directly.
"""

import math
import pandas as pd

from grading.scale import percentile_scores, weighted_blend, to_letter

MIN_GP_FULL = 20      # below this, the grade is flagged as a limited sample

# Roster position string -> grading bucket
BUCKETS = {
    "G": "Guard", "PG": "Guard", "SG": "Guard",
    "G-F": "Wing", "F-G": "Wing", "SF": "Wing", "GF": "Wing",
    "F": "Wing", "PF": "Big-Wing", "F-C": "Big", "C-F": "Big",
    "C": "Big",
}


def bucket_for(position: str) -> str:
    if not isinstance(position, str):
        return "Wing"
    p = position.upper().strip()
    if p in BUCKETS:
        return BUCKETS[p]
    # PF reads as a forward; group with Wing for offense, Big for defense purposes
    if "C" in p:
        return "Big"
    if "G" in p:
        return "Guard"
    return "Wing"


# Overall component weights per bucket
WEIGHTS = {
    "Guard":     {"eff": .16, "vol": .18, "play": .22, "reb": .06, "defense": .16, "impact": .22},
    "Wing":      {"eff": .18, "vol": .20, "play": .12, "reb": .10, "defense": .18, "impact": .22},
    "Big-Wing":  {"eff": .18, "vol": .18, "play": .10, "reb": .16, "defense": .20, "impact": .18},
    "Big":       {"eff": .16, "vol": .14, "play": .08, "reb": .22, "defense": .22, "impact": .18},
}
# Defense sub-blend per bucket (steals, blocks, defensive rating inverted)
DEF_WEIGHTS = {
    "Guard":    {"stl": .50, "blk": .10, "def_rtg": .40},
    "Wing":     {"stl": .35, "blk": .20, "def_rtg": .45},
    "Big-Wing": {"stl": .25, "blk": .35, "def_rtg": .40},
    "Big":      {"stl": .15, "blk": .45, "def_rtg": .40},
}


def _col(df, name):
    return pd.to_numeric(df[name], errors="coerce") if name in df.columns else pd.Series([float("nan")] * len(df), index=df.index)


def grade_players(df: pd.DataFrame) -> pd.DataFrame:
    """Grade a league-wide player table that already has a `bucket` column."""
    if df.empty:
        return df.assign(grade=[], letter=[])

    out = df.copy()
    out["grade"] = float("nan")
    for c in ("eff", "vol", "play", "reb", "defense", "impact"):
        out[c + "_s"] = float("nan")

    for bucket, idx in out.groupby("bucket").groups.items():
        sub = out.loc[idx]
        # Component percentiles within this bucket
        p_eff = percentile_scores(_col(sub, "TS_PCT"))
        p_vol = percentile_scores(_col(sub, "PTS"))
        p_play = percentile_scores(_col(sub, "AST_PCT"))
        p_reb = percentile_scores(_col(sub, "REB_PCT"))
        p_stl = percentile_scores(_col(sub, "STL"))
        p_blk = percentile_scores(_col(sub, "BLK"))
        p_defrtg = percentile_scores(_col(sub, "DEF_RATING"), higher_is_better=False)
        p_net = percentile_scores(_col(sub, "NET_RATING"))
        p_pm = percentile_scores(_col(sub, "PLUS_MINUS"))
        p_pie = percentile_scores(_col(sub, "PIE"))

        dw = DEF_WEIGHTS[bucket]
        w = WEIGHTS[bucket]
        for i in sub.index:
            defense = weighted_blend(
                {"stl": p_stl[i], "blk": p_blk[i], "def_rtg": p_defrtg[i]}, dw
            )
            impact = weighted_blend(
                {"net": p_net[i], "pm": p_pm[i], "pie": p_pie[i]},
                {"net": .34, "pm": .33, "pie": .33},
            )
            comps = {
                "eff": p_eff[i], "vol": p_vol[i], "play": p_play[i],
                "reb": p_reb[i], "defense": defense, "impact": impact,
            }
            grade = weighted_blend(comps, w)
            out.at[i, "grade"] = grade
            out.at[i, "eff_s"] = p_eff[i]
            out.at[i, "vol_s"] = p_vol[i]
            out.at[i, "play_s"] = p_play[i]
            out.at[i, "reb_s"] = p_reb[i]
            out.at[i, "defense_s"] = defense
            out.at[i, "impact_s"] = impact

    gp = _col(out, "GP")
    out["limited_sample"] = gp < MIN_GP_FULL
    out["letter"] = out["grade"].map(to_letter)
    return out
