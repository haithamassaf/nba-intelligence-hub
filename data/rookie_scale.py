"""
APY validation bounds and an approximate NFL rookie wage scale.

Two jobs:

1. Sanity bounds. Any single-player APY outside MIN_VALID_APY..MAX_VALID_APY is
   treated as a feed error. A rookie APY above ROOKIE_APY_CEILING is impossible
   under the rookie wage scale and is also treated as bad. Bad values are never
   shown or used in cap math.

2. Rookie estimate. Rookie deals are slotted by draft position, so a first
   contract APY is predictable from the overall pick even before OverTheCap
   lists the signed deal. The estimate anchors the No. 1 pick near the top of
   the rookie scale and falls toward the rookie minimum for late and undrafted
   players. These are estimates, used only when verified data is missing or
   fails validation, and they are labeled as estimates in the app.

All figures are in millions of dollars to match the OverTheCap APY field.
"""

import math

# ── Validation bounds ($M) ───────────────────────────────────────────
MIN_VALID_APY = 0.4      # below the league minimum; treat as a feed error
MAX_VALID_APY = 75.0     # above the top of the QB market; treat as a feed error
ROOKIE_APY_CEILING = 11.5  # no rookie deal exceeds this; catches misjoins like a vet salary on a rookie

# ── Rookie scale anchors ($M) ────────────────────────────────────────
TOP_ROOKIE_APY = 11.0    # approx No. 1 overall pick APY
END_R1_APY = 3.0         # approx pick 32 APY
MIN_ROOKIE_APY = 0.84    # approx rookie minimum

# Approx APY at each round's midpoint, used when only the round is known.
_ROUND_APY = {1: 4.6, 2: 2.2, 3: 1.4, 4: 1.15, 5: 1.0, 6: 0.95, 7: 0.9}


def _round_from_pick(pick: int) -> int:
    return min(7, (pick - 1) // 32 + 1)


def rookie_apy_from_pick(overall_pick) -> float:
    """Estimated rookie APY ($M) from an overall draft slot (1 = first pick)."""
    pick = int(overall_pick)  # raises on NaN/None/non-numeric
    if pick < 1:
        return MIN_ROOKIE_APY
    if pick <= 32:
        # Round one falls steeply, so weight the early picks (convex curve).
        frac = ((pick - 1) / 31.0) ** 0.6
        return round(TOP_ROOKIE_APY + frac * (END_R1_APY - TOP_ROOKIE_APY), 2)
    return _ROUND_APY.get(_round_from_pick(pick), MIN_ROOKIE_APY)


def rookie_apy_from_round(rnd) -> float:
    """Estimated rookie APY ($M) from draft round when the slot is unknown."""
    return _ROUND_APY.get(int(rnd), MIN_ROOKIE_APY)


def estimate_rookie_apy(overall_pick=None, rnd=None) -> float:
    """Best rookie APY estimate ($M) from whatever draft info is available."""
    for fn, val in ((rookie_apy_from_pick, overall_pick), (rookie_apy_from_round, rnd)):
        if val is None:
            continue
        try:
            return fn(val)
        except (TypeError, ValueError):
            continue
    return MIN_ROOKIE_APY
