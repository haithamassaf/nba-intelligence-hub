"""
Transform raw NFL DataFrames into clean stats and natural-language summaries
ready for embedding in the vector store.

Football stats are position-dependent, so player summaries are written
per position group (QB / RB / WR / TE). Team standings are computed from
the season schedule.
"""

import pandas as pd

# Doc "type" values are kept identical to the NBA pipeline
# (player_season / team_season / league_leaders) so the shared vector
# store and retriever treat both sports uniformly.


# ── Helpers ──────────────────────────────────────────────────────────

def _num(df: pd.DataFrame, col: str) -> pd.Series:
    """Return a numeric column, or a zero-filled series if it's missing."""
    if col in df.columns:
        return pd.to_numeric(df[col], errors="coerce").fillna(0)
    return pd.Series([0] * len(df), index=df.index)


def _norm_pos(p) -> str:
    """Bucket a raw position/position_group into QB/RB/WR/TE/OTHER."""
    if not isinstance(p, str):
        return "OTHER"
    p = p.upper()
    if p == "QB":
        return "QB"
    if p in ("RB", "FB", "HB"):
        return "RB"
    if p == "WR":
        return "WR"
    if p == "TE":
        return "TE"
    return "OTHER"


# ── Player Transforms ────────────────────────────────────────────────

def clean_player_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize season-aggregated player stats into a guaranteed schema."""
    if df.empty:
        return df

    name = df["player_display_name"] if "player_display_name" in df.columns else df.get("player_name")
    team = df["team"] if "team" in df.columns else df.get("recent_team")
    posg = df["position_group"] if "position_group" in df.columns else df.get("position")

    out = pd.DataFrame({
        "player_id": df.get("player_id"),
        "player_name": name,
        "team": team,
        "position": df.get("position"),
        "position_group": posg,
        "games": _num(df, "games"),
        "completions": _num(df, "completions"),
        "attempts": _num(df, "attempts"),
        "passing_yards": _num(df, "passing_yards"),
        "passing_tds": _num(df, "passing_tds"),
        "interceptions": _num(df, "interceptions"),
        "sacks": _num(df, "sacks"),
        "carries": _num(df, "carries"),
        "rushing_yards": _num(df, "rushing_yards"),
        "rushing_tds": _num(df, "rushing_tds"),
        "receptions": _num(df, "receptions"),
        "targets": _num(df, "targets"),
        "receiving_yards": _num(df, "receiving_yards"),
        "receiving_tds": _num(df, "receiving_tds"),
        "fantasy_points": _num(df, "fantasy_points"),
        "fantasy_points_ppr": _num(df, "fantasy_points_ppr"),
    })

    out["player_name"] = out["player_name"].fillna("Unknown")
    out["team"] = out["team"].fillna("FA")
    out["scrimmage_yards"] = out["rushing_yards"] + out["receiving_yards"]
    out["total_tds"] = out["passing_tds"] + out["rushing_tds"] + out["receiving_tds"]
    out["pos_group"] = out["position_group"].map(_norm_pos)
    return out.reset_index(drop=True)


def _fantasy_line(row: pd.Series) -> str:
    fp = row["fantasy_points"]
    if fp <= 0:
        return ""
    return f" Fantasy: {fp:.1f} pts ({row['fantasy_points_ppr']:.1f} PPR)."


def player_summary(row: pd.Series) -> str:
    """Position-aware natural-language stat summary for one player."""
    name = row["player_name"]
    team = row["team"]
    pos = row["pos_group"]
    g = int(row["games"]) if row["games"] else None
    gp = f" over {g} games" if g else ""

    if pos == "QB":
        att = row["attempts"]
        cmp_pct = (row["completions"] / att * 100) if att else 0.0
        text = (
            f"{name} ({team}, QB) has thrown for {int(row['passing_yards']):,} yards, "
            f"{int(row['passing_tds'])} TD, {int(row['interceptions'])} INT on "
            f"{int(row['completions'])}/{int(att)} passing ({cmp_pct:.1f}%){gp}."
        )
        if row["rushing_yards"] >= 50:
            text += f" Added {int(row['rushing_yards']):,} rushing yards and {int(row['rushing_tds'])} rushing TD."
        return text + _fantasy_line(row)

    if pos == "RB":
        car = row["carries"]
        ypc = (row["rushing_yards"] / car) if car else 0.0
        text = (
            f"{name} ({team}, RB) has {int(row['rushing_yards']):,} rushing yards and "
            f"{int(row['rushing_tds'])} rushing TD on {int(car)} carries ({ypc:.1f} YPC){gp}."
        )
        if row["receptions"] >= 10:
            text += (
                f" Also caught {int(row['receptions'])} passes for "
                f"{int(row['receiving_yards']):,} yards and {int(row['receiving_tds'])} TD."
            )
        return text + _fantasy_line(row)

    if pos in ("WR", "TE"):
        text = (
            f"{name} ({team}, {pos}) has {int(row['receptions'])} receptions for "
            f"{int(row['receiving_yards']):,} yards and {int(row['receiving_tds'])} TD on "
            f"{int(row['targets'])} targets{gp}."
        )
        if row["rushing_yards"] >= 50:
            text += f" Added {int(row['rushing_yards']):,} rushing yards and {int(row['rushing_tds'])} rushing TD."
        return text + _fantasy_line(row)

    # OTHER: assemble whatever is non-zero
    parts = []
    if row["passing_yards"] > 0:
        parts.append(f"{int(row['passing_yards']):,} pass yds, {int(row['passing_tds'])} pass TD")
    if row["rushing_yards"] > 0:
        parts.append(f"{int(row['rushing_yards']):,} rush yds, {int(row['rushing_tds'])} rush TD")
    if row["receiving_yards"] > 0:
        parts.append(f"{int(row['receptions'])} rec for {int(row['receiving_yards']):,} yds, {int(row['receiving_tds'])} rec TD")
    body = "; ".join(parts) if parts else "limited offensive production"
    return f"{name} ({team}): {body}{gp}." + _fantasy_line(row)


def _player_summaries(cleaned: pd.DataFrame) -> list[dict]:
    keep = cleaned[
        (cleaned["passing_yards"] >= 200)
        | (cleaned["rushing_yards"] >= 100)
        | (cleaned["receiving_yards"] >= 100)
        | (cleaned["fantasy_points"] >= 20)
    ].sort_values("fantasy_points", ascending=False)

    summaries = []
    for _, row in keep.iterrows():
        summaries.append({
            "player_id": str(row["player_id"]),
            "player_name": row["player_name"],
            "team": row["team"],
            "position": row["pos_group"],
            "summary": player_summary(row),
            "type": "player_season",
        })
    return summaries


def build_player_summaries(df: pd.DataFrame) -> list[dict]:
    """Public entry: clean then summarize meaningful players."""
    cleaned = clean_player_stats(df)
    if cleaned.empty:
        return []
    return _player_summaries(cleaned)


# ── League Leaders ───────────────────────────────────────────────────

def _leader_block(df: pd.DataFrame, col: str, label: str, unit: str, qualifier: str | None = None) -> str:
    pool = df
    if qualifier and qualifier in df.columns:
        pool = df[df[qualifier] > 0]
    top = pool.sort_values(col, ascending=False).head(5)
    top = top[top[col] > 0]
    if top.empty:
        return ""
    entries = [
        f"{i}. {r['player_name']} ({r['team']}, {int(r[col]):,} {unit})"
        for i, (_, r) in enumerate(top.iterrows(), 1)
    ]
    return f"Top {label} leaders this season: " + ", ".join(entries) + "."


def _leader_summaries(cleaned: pd.DataFrame) -> list[dict]:
    blocks = [
        ("passing_yards", "passing yards", "yds", "attempts"),
        ("rushing_yards", "rushing yards", "yds", "carries"),
        ("receiving_yards", "receiving yards", "yds", "targets"),
        ("total_tds", "touchdown", "TD", None),
    ]
    out = []
    for col, label, unit, qualifier in blocks:
        text = _leader_block(cleaned, col, label, unit, qualifier)
        if text:
            out.append({
                "summary": text,
                "type": "league_leaders",
                "category": label.split()[0],  # passing / rushing / receiving / touchdown
            })
    return out


def build_leader_summaries(df: pd.DataFrame) -> list[dict]:
    cleaned = clean_player_stats(df)
    if cleaned.empty:
        return []
    return _leader_summaries(cleaned)


# ── Team Standings (computed from the schedule) ──────────────────────

def _team_meta_lookup(teams: pd.DataFrame) -> dict:
    meta = {}
    if teams is None or teams.empty or "team_abbr" not in teams.columns:
        return meta
    for _, r in teams.iterrows():
        meta[r["team_abbr"]] = {
            "name": r.get("team_name", r["team_abbr"]),
            "conference": r.get("team_conf", ""),
            "division": r.get("team_division", ""),
            "color": r.get("team_color", "#444444"),
        }
    return meta


def compute_standings(schedules: pd.DataFrame, teams: pd.DataFrame | None = None) -> list[dict]:
    """Compute W-L-T, points for/against, and division rank from the schedule."""
    if schedules is None or schedules.empty:
        return []

    reg = schedules
    if "game_type" in reg.columns:
        reg = reg[reg["game_type"] == "REG"]
    reg = reg.dropna(subset=["home_score", "away_score"])
    if reg.empty:
        return []

    rec: dict[str, dict] = {}

    def ensure(t):
        rec.setdefault(t, {"w": 0, "l": 0, "t": 0, "pf": 0, "pa": 0, "g": 0})

    for _, g in reg.iterrows():
        h, a = g["home_team"], g["away_team"]
        hs, as_ = float(g["home_score"]), float(g["away_score"])
        ensure(h); ensure(a)
        rec[h]["pf"] += hs; rec[h]["pa"] += as_; rec[h]["g"] += 1
        rec[a]["pf"] += as_; rec[a]["pa"] += hs; rec[a]["g"] += 1
        if hs > as_:
            rec[h]["w"] += 1; rec[a]["l"] += 1
        elif hs < as_:
            rec[h]["l"] += 1; rec[a]["w"] += 1
        else:
            rec[h]["t"] += 1; rec[a]["t"] += 1

    meta = _team_meta_lookup(teams)

    rows = []
    for abbr, d in rec.items():
        m = meta.get(abbr, {})
        g = d["g"]
        win_pct = (d["w"] + 0.5 * d["t"]) / g if g else 0.0
        rows.append({
            "team": abbr,
            "team_id": abbr,
            "name": m.get("name", abbr),
            "conference": m.get("conference", ""),
            "division": m.get("division", ""),
            "color": m.get("color", "#444444"),
            "wins": d["w"],
            "losses": d["l"],
            "ties": d["t"],
            "win_pct": round(win_pct, 3),
            "points_for": int(d["pf"]),
            "points_against": int(d["pa"]),
            "point_diff": int(d["pf"] - d["pa"]),
            "games": g,
        })

    # Division rank
    by_div: dict[str, list] = {}
    for r in rows:
        by_div.setdefault(r["division"], []).append(r)
    for div_rows in by_div.values():
        div_rows.sort(key=lambda r: (r["win_pct"], r["point_diff"]), reverse=True)
        for i, r in enumerate(div_rows, 1):
            r["div_rank"] = i

    rows.sort(key=lambda r: (r["win_pct"], r["point_diff"]), reverse=True)
    return rows


def team_standings_summary(row: dict) -> str:
    rec = f"{row['wins']}-{row['losses']}"
    if row["ties"]:
        rec += f"-{row['ties']}"
    g = row["games"] or 1
    ppg = row["points_for"] / g
    pa_pg = row["points_against"] / g
    div = row["division"] or row["conference"] or "the league"
    rank = row.get("div_rank")
    rank_txt = f", ranked #{rank} in the {row['division']}" if rank and row["division"] else ""
    return (
        f"The {row['name']} ({row['team']}) are {rec} ({row['win_pct']:.3f}) in the {div}{rank_txt}. "
        f"They have scored {row['points_for']} points ({ppg:.1f}/game) and allowed "
        f"{row['points_against']} ({pa_pg:.1f}/game), a point differential of "
        f"{row['point_diff']:+d} over {row['games']} games."
    )


def build_team_summaries(schedules: pd.DataFrame, teams: pd.DataFrame | None = None) -> list[dict]:
    standings = compute_standings(schedules, teams)
    summaries = []
    for row in standings:
        summaries.append({
            "team_id": row["team"],
            "team": row["team"],
            "name": row["name"],
            "summary": team_standings_summary(row),
            "type": "team_season",
        })
    return summaries


# ── Master Pipeline ──────────────────────────────────────────────────

def build_all_summaries(datasets: dict) -> list[dict]:
    """Take the output of nfl_fetch.fetch_all() and produce every summary doc."""
    all_summaries: list[dict] = []

    ps = datasets.get("player_stats")
    if ps is not None and not ps.empty:
        cleaned = clean_player_stats(ps)
        all_summaries.extend(_player_summaries(cleaned))
        all_summaries.extend(_leader_summaries(cleaned))

    sched = datasets.get("schedules")
    teams = datasets.get("teams")
    if sched is not None and not sched.empty:
        all_summaries.extend(build_team_summaries(sched, teams))

    print(f"Generated {len(all_summaries)} total NFL summaries:")
    types: dict[str, int] = {}
    for s in all_summaries:
        types[s["type"]] = types.get(s["type"], 0) + 1
    for t, c in types.items():
        print(f"  {t}: {c}")

    return all_summaries


if __name__ == "__main__":
    from data.nfl_fetch import fetch_all

    datasets = fetch_all()
    summaries = build_all_summaries(datasets)

    seen = set()
    for s in summaries:
        if s["type"] not in seen:
            seen.add(s["type"])
            print(f"\n--- {s['type']} ---")
            print(s["summary"])
