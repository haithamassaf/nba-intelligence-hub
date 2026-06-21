"""
Shared grading math.

Grades are 0-100 and relative to a player's position peers: each input stat is
converted to a percentile rank within the position group, then a weighted blend
of those percentiles forms the composite. This means a grade answers "where does
this player rank at his position", not an arbitrary absolute cutoff.
"""

import math
import pandas as pd

from config.settings import GRADE_BANDS


def to_letter(score: float) -> str:
    if score is None or (isinstance(score, float) and math.isnan(score)):
        return "NR"
    for threshold, letter in GRADE_BANDS:
        if score >= threshold:
            return letter
    return "F"


def clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def percentile_scores(series: pd.Series, higher_is_better: bool = True) -> pd.Series:
    """
    Map a numeric series to 0-100 percentile ranks within itself.
    NaNs stay NaN. If lower is better (e.g. INT, sacks allowed), invert.
    """
    s = pd.to_numeric(series, errors="coerce")
    valid = s.dropna()
    if valid.empty:
        return pd.Series([float("nan")] * len(s), index=s.index)
    if valid.nunique() == 1:
        # Everyone equal -> neutral 50
        out = pd.Series([float("nan")] * len(s), index=s.index)
        out[s.notna()] = 50.0
        return out
    ranks = s.rank(pct=True, na_option="keep") * 100.0
    if not higher_is_better:
        ranks = 100.0 - ranks
    return ranks


def weighted_blend(components: dict[str, float], weights: dict[str, float]) -> float:
    """
    Weighted average of component scores (each 0-100). Components that are NaN
    or missing are dropped and the remaining weights renormalize, so a missing
    stat never silently counts as zero.
    """
    num = 0.0
    wsum = 0.0
    for name, w in weights.items():
        v = components.get(name)
        if v is None or (isinstance(v, float) and math.isnan(v)):
            continue
        num += v * w
        wsum += w
    if wsum == 0:
        return float("nan")
    return clamp(num / wsum)


def pick_curve(pick: float, last_pick: int = 262) -> float:
    """
    Convert an NFL draft pick number to a 0-100 capital score.
    Pick 1 ~ 99, end of draft ~ 40, undrafted handled by caller (lower).
    Uses a smooth decay so early picks separate sharply.
    """
    if pick is None or (isinstance(pick, float) and math.isnan(pick)) or pick <= 0:
        return float("nan")
    # Exponential-ish decay anchored at 1 and last_pick.
    frac = (pick - 1) / max(1, last_pick - 1)
    score = 99.0 * (1.0 - frac) ** 1.6 + 40.0 * frac
    return clamp(score, 30.0, 99.0)
