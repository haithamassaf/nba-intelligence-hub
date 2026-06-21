import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root regardless of cwd
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env", override=True)

# API Keys
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Model
# Env-overridable so a future model retirement is a config change, not a code edit.
# (claude-sonnet-4-20250514 was retired from the Claude API on 2026-06-15.)
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

# ChromaDB
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma")

# Supported sports
SPORTS = ("nba", "nfl")
DEFAULT_SPORT = "nba"

# NBA
CURRENT_SEASON = "2025-26"          # NBA season (kept for backwards compatibility)
NBA_SEASON = CURRENT_SEASON
LAST_N_GAMES = 10
NBA_API_TIMEOUT = int(os.getenv("NBA_API_TIMEOUT", "30"))

# NFL
# If unset, the data layer falls back to nflreadpy's current-season helper,
# so this advances automatically when the next season kicks off.
NFL_SEASON = os.getenv("NFL_SEASON")  # e.g. "2025"; None -> auto-detect
