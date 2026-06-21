# NFL & NBA Intelligence Hub

A conversational AI web app with two sections, NFL and NBA, where users ask natural language questions about the current season and get answers grounded in real, up-to-date player and team stats using Retrieval-Augmented Generation (RAG).

Switch sports from the toggle at the top of the sidebar. Each sport has its own live data source, its own ChromaDB collection, and its own accent theme.

**NFL questions you can ask:**
- "Who's the MVP frontrunner right now?"
- "Compare Josh Allen and Lamar Jackson"
- "Which teams have the best record?"
- "Who leads the league in rushing?"
- "How are the 49ers looking this season?"

**NBA questions you can ask:**
- "Who's playing the best basketball right now?"
- "Compare Luka and Shai's stats this season"
- "Who should win MVP based on the numbers?"
- "Which teams have the best defense this month?"
- "How has Jayson Tatum been playing lately?"

## Screenshots

### Chat Interface
Ask any NFL or NBA question and get a stat-grounded answer powered by Claude AI.

![Chat](screenshots/chat.png)

### Player Stats Browser
Browse, search, and filter player stats with stat cards. NFL adds a position filter (QB / RB / WR / TE).

![Players](screenshots/players.png)

### Team Standings
Conference standings with team cards. NBA shows offensive/defensive ratings, NFL shows points for/against and division rank computed from the live schedule.

![Standings](screenshots/standings.png)

### Player Comparison
Head-to-head stat breakdowns with visual comparison bars, with position-appropriate stat rows for the NFL.

![Compare](screenshots/compare.png)

## Tech Stack

| Layer | Tech | Why |
|-------|------|-----|
| **LLM** | Claude API (claude-sonnet-4-6) | Strong reasoning, fast, cost-effective |
| **Embeddings** | ChromaDB built-in ONNX MiniLM | Local, no API key needed |
| **Vector Store** | ChromaDB (one collection per sport) | Lightweight, no infra overhead |
| **NFL Data** | `nflreadpy` (nflverse) | Free, maintained, season-aggregated stats |
| **NBA Data** | `nba_api` (stats.nba.com) | Free, comprehensive, real NBA data |
| **Backend** | FastAPI | Clean API layer, async support |
| **Frontend** | Streamlit | Rapid UI development, built-in chat |
| **Language** | Python 3.11+ | End-to-end |

## Architecture

The RAG layer is sport-aware. A `sport` parameter ("nfl" or "nba") flows through classification, retrieval, and generation, and selects the matching ChromaDB collection (`nfl_summaries` or `nba_summaries`). Both sports reuse the same document types (player_season, team_season, league_leaders) so the retriever and vector store stay uniform.

```
User Question (+ active sport)
     |
     v
[Streamlit Frontend]  or  [FastAPI /{sport}/ask endpoint]
     |
     v
[RAG Chain]
     |
     +-- 1. Query Classification (Claude API, sport-specific prompt)
     |       - Intent and entity extraction
     |
     +-- 2. Dual-Path Retrieval (scoped to the sport's collection)
     |       - Path A: targeted search by extracted entities
     |       - Path B: broad semantic search over the vector store
     |       - Merged + deduplicated context
     |
     +-- 3. Response Generation (Claude API, sport-specific persona)
             - Stat-grounded, conversational answers
```

## Project Structure

```
nba-intelligence-hub/
+-- config/
|   +-- settings.py           # Model, season, and sport settings
+-- data/
|   +-- fetch_stats.py        # NBA: nba_api data fetching
|   +-- transform.py          # NBA: cleaning + summaries
|   +-- nfl_fetch.py          # NFL: nflreadpy data fetching
|   +-- nfl_transform.py      # NFL: cleaning, summaries, computed standings
|   +-- build_embeddings.py   # Sport-aware fetch -> transform -> embed pipeline
+-- rag/
|   +-- vector_store.py       # ChromaDB, one collection per sport
|   +-- retriever.py          # Dual-path retrieval (structured + semantic)
|   +-- prompts.py            # Per-sport system and classification prompts
|   +-- chain.py              # Full RAG chain + interactive terminal chat
+-- api/
|   +-- main.py               # FastAPI app entry point
|   +-- routes.py             # /{sport}/ask, /players, /teams, /refresh
|   +-- models.py             # Pydantic schemas (NBA + NFL)
+-- frontend/
|   +-- app.py                # Streamlit app, two sections, 4 pages each
|   +-- components/
|       +-- chat.py           # Sport-aware chat rendering
|       +-- stats_card.py     # NBA + NFL player/team cards
|       +-- player_compare.py # NBA + NFL side-by-side comparison
+-- .env.example
+-- requirements.txt
+-- pyproject.toml
```

## Setup

### 1. Clone and install

```bash
git clone https://github.com/haithamassaf/nba-intelligence-hub.git
cd nba-intelligence-hub
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and add your Anthropic API key:
# ANTHROPIC_API_KEY=sk-ant-...
```

### 3. Seed the vector stores

This fetches live data and embeds stat summaries into ChromaDB. Seed one sport or both:

```bash
python -m data.build_embeddings nfl    # NFL only
python -m data.build_embeddings nba    # NBA only
python -m data.build_embeddings all    # both
```

The app also seeds the active sport automatically on first launch if its collection is empty.

### 4. Run the app

**Option A: Streamlit frontend (recommended)**
```bash
streamlit run frontend/app.py
# Opens at http://localhost:8501
```

**Option B: FastAPI backend only**
```bash
pip install fastapi uvicorn
python -m api.main
# API at http://localhost:8000
# Docs at http://localhost:8000/docs
```

**Option C: Terminal chat**
```bash
python -m rag.chain nfl     # or: python -m rag.chain nba
```

## API Endpoints

Routes are sport-prefixed, where `{sport}` is `nfl` or `nba`.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/{sport}/ask` | Ask a natural language question |
| `GET` | `/{sport}/players` | Browse player stats (`?search=`, `?team=`, `?position=` for NFL, `?limit=`) |
| `GET` | `/{sport}/teams` | Team standings (`?conference=`) |
| `POST` | `/{sport}/refresh` | Re-fetch the sport's data and rebuild its vector store |

### Example request

```bash
curl -X POST http://localhost:8000/nfl/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Who leads the league in rushing?"}'
```

## Data Pipeline

**NFL** (via `nflreadpy`): season-aggregated player stats (passing, rushing, receiving, fantasy), the season schedule, and team metadata. Standings (W-L-T, points for/against, point differential, division rank) are computed from completed regular-season games in the schedule.

**NBA** (via `nba_api`): player season averages, team standings, advanced team ratings (offense, defense, pace, net), and league leaders.

For each sport, every data point is transformed into a natural language summary and embedded into its ChromaDB collection for semantic retrieval. Either store can be refreshed on demand via the UI refresh button or the `/{sport}/refresh` API endpoint.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Your Anthropic API key |
| `CLAUDE_MODEL` | No | Model override (default: `claude-sonnet-4-6`) |
| `CHROMA_PERSIST_DIR` | No | ChromaDB storage path (default: `./data/chroma`) |
| `NBA_API_TIMEOUT` | No | NBA API request timeout in seconds (default: `30`) |
| `NBA_SEASON` | No | Pin the NBA season (default: auto-detect) |
| `NFL_SEASON` | No | Pin the NFL season (default: auto-detect) |

## Built With

- [Anthropic Claude API](https://docs.anthropic.com/) - LLM for query classification and response generation
- [ChromaDB](https://www.trychroma.com/) - Vector database for semantic search
- [nflreadpy](https://github.com/nflverse/nflreadpy) - Python client for nflverse data
- [nba_api](https://github.com/swar/nba_api) - Python client for stats.nba.com
- [FastAPI](https://fastapi.tiangolo.com/) - Backend API framework
- [Streamlit](https://streamlit.io/) - Frontend UI framework
