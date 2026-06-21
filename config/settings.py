"""Central configuration. Seasons default to the most recent completed season
for stats/grading, and the current year for rosters (which include rookies)."""

import os
from pathlib import Path
from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env", override=True)

# ── API keys ─────────────────────────────────────────────────────────
# ANTHROPIC_API_KEY is optional: used only to write team summaries in prose.
# Without it, summaries fall back to a deterministic template. No key is ever
# the source of a stat or grade.
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
# CFBD_API_KEY (free, from collegefootballdata.com/key) powers rookie grading
# from college production. Without it, rookies grade on draft capital + combine.
CFBD_API_KEY = os.getenv("CFBD_API_KEY")

# Model used only for prose summaries (never for numbers).
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

# ── Sports ───────────────────────────────────────────────────────────
SPORTS = ("nfl", "nba")
DEFAULT_SPORT = "nfl"

# ── NBA ──────────────────────────────────────────────────────────────
# Most recent completed season drives player stats and grading.
NBA_STATS_SEASON = os.getenv("NBA_STATS_SEASON", "2025-26")
NBA_API_TIMEOUT = int(os.getenv("NBA_API_TIMEOUT", "30"))

# ── NFL ──────────────────────────────────────────────────────────────
# Stats/grading use the last completed season; rosters (with rookies) use the
# current league year. None -> auto-detect from nflreadpy.
NFL_STATS_SEASON = os.getenv("NFL_STATS_SEASON")     # e.g. "2025"; None -> latest completed
NFL_ROSTER_SEASON = os.getenv("NFL_ROSTER_SEASON")   # e.g. "2026"; None -> current
NFL_DRAFT_YEAR = os.getenv("NFL_DRAFT_YEAR")         # e.g. "2026"; None -> current roster year

# NFL salary cap for the current league year (in $M), used by the trade simulator.
# Set this to the current cap for exact room; net cap change between teams is
# exact regardless of this value. OverTheCap APY is the per-player charge basis.
NFL_SALARY_CAP = float(os.getenv("NFL_SALARY_CAP", "300.0"))

# College season the current rookie class last played (for rookie grading).
COLLEGE_SEASON = int(os.getenv("COLLEGE_SEASON", "2025"))

# ── Grading scale ────────────────────────────────────────────────────
# Grades are 0-100, mapped to letters. Anchored to league percentiles so a
# grade means "where this player ranks at his position", not an absolute.
GRADE_BANDS = [
    (97, "A+"), (93, "A"), (90, "A-"),
    (87, "B+"), (83, "B"), (80, "B-"),
    (77, "C+"), (73, "C"), (70, "C-"),
    (67, "D+"), (63, "D"), (60, "D-"),
    (0,  "F"),
]
