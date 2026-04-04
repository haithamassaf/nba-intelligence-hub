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
CLAUDE_MODEL = "claude-sonnet-4-20250514"

# ChromaDB
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma")

# NBA API
NBA_API_TIMEOUT = int(os.getenv("NBA_API_TIMEOUT", "30"))

# Data
CURRENT_SEASON = "2025-26"
LAST_N_GAMES = 10
