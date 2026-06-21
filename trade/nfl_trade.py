"""
NFL trade simulator (cap-only).

NFL trades are cap-driven with no salary matching. Each player's cap charge is
his OverTheCap APY, and a team's commitment is the sum of its top-51 APYs, which
mirrors the offseason top-51 rule. A trade is legal when both teams stay under
the cap. The net cap change between teams is exact; the absolute cap-space number
depends on NFL_SALARY_CAP, which should be set to the current league-year cap.
"""

import pandas as pd

try:
    from config.settings import NFL_SALARY_CAP
except ImportError:  # tolerate an older settings.py that predates this constant
    import os
    NFL_SALARY_CAP = float(os.getenv("NFL_SALARY_CAP", "300.0"))

TOP_N = 51


def _committed(df: pd.DataFrame, top_n: int = TOP_N) -> float:
    apy = pd.to_numeric(df.get("apy"), errors="coerce").dropna().sort_values(ascending=False)
    return float(apy.head(top_n).sum())


def _apy_sum(df: pd.DataFrame) -> float:
    return float(pd.to_numeric(df.get("apy"), errors="coerce").fillna(0).sum())


def team_cap_space(table: pd.DataFrame, team: str, cap: float = NFL_SALARY_CAP) -> float:
    return round(cap - _committed(table[table["team"] == team]), 2)


def _player_rows(df: pd.DataFrame) -> list[dict]:
    return [{"name": r.get("player_name"), "pos": r.get("position"),
             "apy": round(float(r["apy"]), 2) if pd.notna(r.get("apy")) else None}
            for _, r in df.iterrows()]


def evaluate_trade(table: pd.DataFrame, team_a: str, team_b: str,
                   send_a: list[str], send_b: list[str], cap: float = NFL_SALARY_CAP) -> dict:
    """
    send_a / send_b are gsis_id lists leaving team_a / team_b respectively.
    Returns cap legality and the players moving for both teams.
    """
    a = table[table["team"] == team_a]
    b = table[table["team"] == team_b]
    out_a = a[a["gsis_id"].isin(send_a)]
    out_b = b[b["gsis_id"].isin(send_b)]

    new_a = pd.concat([a[~a["gsis_id"].isin(send_a)], out_b], ignore_index=True)
    new_b = pd.concat([b[~b["gsis_id"].isin(send_b)], out_a], ignore_index=True)

    cap_a_after = _committed(new_a)
    cap_b_after = _committed(new_b)

    return {
        "team_a": team_a, "team_b": team_b,
        "a_sends": _player_rows(out_a), "b_sends": _player_rows(out_b),
        "legal": (cap_a_after <= cap) and (cap_b_after <= cap),
        "cap": {
            team_a: {"committed_before": round(_committed(a), 2), "committed_after": round(cap_a_after, 2),
                     "space_after": round(cap - cap_a_after, 2), "legal": cap_a_after <= cap,
                     "apy_out": round(_apy_sum(out_a), 2), "apy_in": round(_apy_sum(out_b), 2)},
            team_b: {"committed_before": round(_committed(b), 2), "committed_after": round(cap_b_after, 2),
                     "space_after": round(cap - cap_b_after, 2), "legal": cap_b_after <= cap,
                     "apy_out": round(_apy_sum(out_b), 2), "apy_in": round(_apy_sum(out_a), 2)},
        },
    }
