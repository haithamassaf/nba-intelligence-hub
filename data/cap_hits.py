"""
Current-season cap hit per player from OverTheCap (via nflverse contracts).

APY is a contract-wide average: total value divided by years, so it reads the
same in every season of a deal. The number a team actually carries in a given
season is the cap hit, which lives in the contract's year-by-year breakdown
(the nested `cols` field on the contracts table). This module pulls the cap hit
for one league year and returns it keyed by gsis_id, in $M to match the rest of
the app.

The exact field names in the nested breakdown vary by nflverse version, so the
extractor tries the common ones and, if the value looks like raw dollars, scales
it to millions. If nothing matches, callers fall back to APY.
"""

import pandas as pd

try:
    import nflreadpy as nfl
except Exception:  # pragma: no cover - import guarded so tests can stub it
    nfl = None

# Candidate field names inside each year row of the OTC breakdown.
_YEAR_KEYS = ("year", "season", "league_year", "yr")
_CAP_KEYS = ("cap_number", "cap_hit", "cap_charge", "cap_total", "team_cap_hit",
             "cap_figure", "cap")


def _to_pd(df) -> pd.DataFrame:
    if isinstance(df, pd.DataFrame):
        return df
    try:
        return df.to_pandas()
    except AttributeError:
        return pd.DataFrame(df)


def _as_rows(cell):
    """Normalize a nested `cols` cell into a list of dict-like year rows."""
    if cell is None:
        return []
    # list / array / tuple of dicts
    if isinstance(cell, (list, tuple)):
        return [r for r in cell if isinstance(r, dict)]
    try:
        import numpy as np
        if isinstance(cell, np.ndarray):
            return [r for r in cell.tolist() if isinstance(r, dict)]
    except Exception:
        pass
    # a DataFrame of year rows
    if isinstance(cell, pd.DataFrame):
        return cell.to_dict("records")
    return []


def _pick(d: dict, keys) -> object:
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    # case-insensitive fallback
    low = {str(k).lower(): v for k, v in d.items()}
    for k in keys:
        if k in low and low[k] is not None:
            return low[k]
    return None


def _scale_to_millions(val) -> float | None:
    try:
        v = float(val)
    except (TypeError, ValueError):
        return None
    if v <= 0:
        return None
    # APY-style figures are already in $M (e.g. 27.0); raw OTC dollars are large.
    return round(v / 1_000_000, 2) if v > 1000 else round(v, 2)


def _year_cap(cell, season: int) -> float | None:
    for row in _as_rows(cell):
        yr = _pick(row, _YEAR_KEYS)
        try:
            if yr is not None and int(yr) == int(season):
                return _scale_to_millions(_pick(row, _CAP_KEYS))
        except (TypeError, ValueError):
            continue
    return None


def get_current_cap_hits(season: int) -> pd.DataFrame:
    """
    Return DataFrame[gsis_id, cap_hit, cap_year] for the given league year.

    Empty if the contracts feed has no usable year-by-year breakdown, in which
    case callers should fall back to APY.
    """
    if nfl is None:
        return pd.DataFrame(columns=["gsis_id", "cap_hit", "cap_year"])
    df = _to_pd(nfl.load_contracts())
    if df.empty or "gsis_id" not in df.columns:
        return pd.DataFrame(columns=["gsis_id", "cap_hit", "cap_year"])

    nested_col = next((c for c in ("cols", "yearly", "years_detail", "cap_table")
                       if c in df.columns), None)
    if nested_col is None:
        return pd.DataFrame(columns=["gsis_id", "cap_hit", "cap_year"])

    rows = []
    for _, r in df.iterrows():
        gid = r.get("gsis_id")
        if gid is None or pd.isna(gid):
            continue
        hit = _year_cap(r.get(nested_col), season)
        if hit is not None:
            rows.append({"gsis_id": gid, "cap_hit": hit, "cap_year": int(season)})

    out = pd.DataFrame(rows, columns=["gsis_id", "cap_hit", "cap_year"])
    if not out.empty:
        out = out.sort_values("cap_hit", ascending=False).drop_duplicates("gsis_id", keep="first")
    return out.reset_index(drop=True)
