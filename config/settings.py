"""Configuration for the roster viewer + NFL trade simulator."""

import os
from pathlib import Path
from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env", override=True)

# Optional: Claude writes the trade opinion. The app runs without it (falls back
# to a plain summary). Claude never sources a stat, only the written assessment.
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

SPORTS = ("nfl", "nba")
DEFAULT_SPORT = "nfl"

# NBA: most recent completed season drives rosters and stats.
NBA_STATS_SEASON = os.getenv("NBA_STATS_SEASON", "2025-26")
NBA_API_TIMEOUT = int(os.getenv("NBA_API_TIMEOUT", "30"))

# NFL: stats from the last completed season, rosters from the current league year.
NFL_STATS_SEASON = os.getenv("NFL_STATS_SEASON")     # None -> latest completed
NFL_ROSTER_SEASON = os.getenv("NFL_ROSTER_SEASON")   # None -> current league year

# NFL salary cap (in $M) for the trade simulator. Set to the current cap for exact
# room; net cap change between teams is exact regardless.
NFL_SALARY_CAP = float(os.getenv("NFL_SALARY_CAP", "300.0"))
