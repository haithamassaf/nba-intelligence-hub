"""
College football stats from CollegeFootballData.com, used to grade NFL rookies
on their final college season.

Hits the REST API directly with a bearer token (free key from
collegefootballdata.com/key, set as CFBD_API_KEY). One call pulls a whole
season of player stats, cached to disk to stay well under the free tier.

If no key is set, get_player_season_wide() returns an empty frame and rookie
grading falls back to draft capital + combine testing.
"""

import json
import time
from pathlib import Path
import pandas as pd

try:
    import requests
except Exception:  # pragma: no cover
    requests = None

from config.settings import CFBD_API_KEY, COLLEGE_SEASON

_BASE = "https://api.collegefootballdata.com"
_CACHE = Path(__file__).resolve().parent / ".cache"
_CACHE.mkdir(exist_ok=True)


def _get(path: str, params: dict) -> list:
    if not CFBD_API_KEY or requests is None:
        return []
    headers = {"Authorization": f"Bearer {CFBD_API_KEY}", "Accept": "application/json"}
    for attempt in range(3):
        try:
            r = requests.get(f"{_BASE}{path}", headers=headers, params=params, timeout=30)
            if r.status_code == 200:
                return r.json()
            if r.status_code in (429, 500, 502, 503):
                time.sleep(1.5 * (attempt + 1))
                continue
            return []
        except Exception:
            time.sleep(1.0)
    return []


def get_player_season_raw(year: int | None = None, use_cache: bool = True) -> list:
    """Long-format season stat lines for every FBS player in a season."""
    year = year or COLLEGE_SEASON
    cache_file = _CACHE / f"cfb_player_season_{year}.json"
    if use_cache and cache_file.exists():
        try:
            return json.loads(cache_file.read_text())
        except Exception:
            pass
    raw = _get("/stats/player/season", {"year": year})
    if raw:
        try:
            cache_file.write_text(json.dumps(raw))
        except Exception:
            pass
    return raw


# ── Parsing (pure, unit-tested) ──────────────────────────────────────

# CFBD reports stats as (category, statType, stat). Map the ones we grade on
# to flat column names.
_KEEP = {
    ("passing", "YDS"): "pass_yds",
    ("passing", "TD"): "pass_td",
    ("passing", "INT"): "pass_int",
    ("passing", "COMPLETIONS"): "pass_cmp",
    ("passing", "ATT"): "pass_att",
    ("passing", "PCT"): "pass_pct",
    ("rushing", "YDS"): "rush_yds",
    ("rushing", "TD"): "rush_td",
    ("rushing", "CAR"): "rush_att",
    ("rushing", "YPC"): "rush_ypc",
    ("receiving", "YDS"): "rec_yds",
    ("receiving", "TD"): "rec_td",
    ("receiving", "REC"): "rec",
    ("receiving", "YPR"): "rec_ypr",
    ("defensive", "TOT"): "tackles",
    ("defensive", "SOLO"): "solo",
    ("defensive", "TFL"): "tfl",
    ("defensive", "SACKS"): "sacks",
    ("defensive", "QB HUR"): "qb_hur",
    ("defensive", "PD"): "pass_def",
    ("interceptions", "INT"): "def_int",
}


def to_wide(raw: list) -> pd.DataFrame:
    """Pivot CFBD long-format lines into one row per player with flat columns."""
    if not raw:
        return pd.DataFrame()

    rows: dict[str, dict] = {}
    for r in raw:
        pid = str(r.get("playerId") or r.get("player"))
        rec = rows.setdefault(pid, {
            "player_id": pid,
            "player": r.get("player"),
            "college": r.get("team"),
            "conference": r.get("conference"),
        })
        key = (r.get("category"), r.get("statType"))
        col = _KEEP.get(key)
        if col is not None:
            try:
                rec[col] = float(r.get("stat"))
            except (TypeError, ValueError):
                pass

    df = pd.DataFrame(list(rows.values()))
    if df.empty:
        return df
    stat_cols = [c for c in _KEEP.values() if c in df.columns]
    df[stat_cols] = df[stat_cols].fillna(0.0)
    return df.reset_index(drop=True)


def get_player_season_wide(year: int | None = None) -> pd.DataFrame:
    """Per-player wide college stats for the season. Empty if no CFBD key."""
    return to_wide(get_player_season_raw(year))


if __name__ == "__main__":
    df = get_player_season_wide()
    print(f"college players: {len(df)}")
    if not df.empty:
        print(df.head(5).to_string(index=False))
    else:
        print("(no CFBD_API_KEY set, or no data)")
