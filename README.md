# NBA Intelligence Hub

A conversational AI web app where users ask natural language questions about the current NBA season and get answers grounded in real, up-to-date player and team stats using Retrieval-Augmented Generation (RAG).

**Example questions you can ask:**
- "Who's playing the best basketball right now?"
- "Compare Luka and Shai's stats this season"
- "Who should win MVP based on the numbers?"
- "Which teams have the best defense this month?"
- "How has Jayson Tatum been playing lately?"

## Screenshots

### Chat Interface
Ask any NBA question and get a stat-grounded answer powered by Claude AI.

![Chat](screenshots/chat.png)

### Player Stats Browser
Browse, search, and filter player season averages with stat cards.

![Players](screenshots/players.png)

### Team Standings
Full conference standings with offensive/defensive ratings and team cards.

![Standings](screenshots/standings.png)

### Player Comparison
Head-to-head stat breakdowns with visual comparison bars.

![Compare](screenshots/compare.png)

## Tech Stack

| Layer | Tech | Why |
|-------|------|-----|
| **LLM** | Claude API (claude-sonnet-4-20250514) | Cost-effective, strong reasoning |
| **Embeddings** | ChromaDB built-in ONNX MiniLM | Local, no API key needed |
| **Vector Store** | ChromaDB (persistent) | Lightweight, no infra overhead |
| **Data Source** | `nba_api` (stats.nba.com) | Free, comprehensive, real NBA data |
| **Backend** | FastAPI | Clean API layer, async support |
| **Frontend** | Streamlit | Rapid UI development, built-in chat |
| **Language** | Python 3.11+ | End-to-end |

## Architecture

```
User Question
     |
     v
[Streamlit Frontend]  or  [FastAPI /ask endpoint]
     |
     v
[RAG Chain]
     |
     +-- 1. Query Classification (Claude API)
     |       - Intent: player_stats, comparison, team_stats, rankings, award_race
     |       - Entity extraction: player names, teams, stat categories
     |       - Time range detection
     |
     +-- 2. Dual-Path Retrieval
     |       |
     |       +-- Path A: Targeted search by extracted entities
     |       |     (player name lookups, team filters, leader queries)
     |       |
     |       +-- Path B: Broad semantic search over vector store
     |       |     (478 embedded stat summaries via cosine similarity)
     |       |
     |       +-- Merged + deduplicated context
     |
     +-- 3. Response Generation (Claude API)
             - NBA analyst persona
             - Stat-grounded, conversational answers
             - Tables and structured comparisons
```

## Project Structure

```
nba-intelligence-hub/
+-- config/
|   +-- settings.py           # API keys, model config, season settings
+-- data/
|   +-- fetch_stats.py        # nba_api data fetching (players, teams, leaders)
|   +-- transform.py          # Data cleaning + natural language summaries
|   +-- build_embeddings.py   # Fetch -> transform -> embed pipeline
+-- rag/
|   +-- vector_store.py       # ChromaDB init, add, query, reset
|   +-- retriever.py          # Dual-path retrieval (structured + semantic)
|   +-- prompts.py            # System prompts and templates
|   +-- chain.py              # Full RAG chain + interactive terminal chat
+-- api/
|   +-- main.py               # FastAPI app entry point
|   +-- routes.py             # /ask, /players, /teams, /refresh endpoints
|   +-- models.py             # Pydantic request/response schemas
+-- frontend/
|   +-- app.py                # Streamlit app (4 pages)
|   +-- components/
|       +-- chat.py           # Chat message rendering
|       +-- stats_card.py     # Player/team stat cards
|       +-- player_compare.py # Side-by-side comparison UI
+-- .env.example
+-- requirements.txt
+-- pyproject.toml
```

## Setup

### 1. Clone and install

```bash
git clone https://github.com/YOUR_USERNAME/nba-intelligence-hub.git
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

### 3. Seed the vector store

This fetches live NBA data and embeds 478 stat summaries into ChromaDB:

```bash
python -m data.build_embeddings
```

### 4. Run the app

**Option A: Streamlit frontend (recommended)**
```bash
streamlit run frontend/app.py
# Opens at http://localhost:8501
```

**Option B: FastAPI backend only**
```bash
python -m api.main
# API at http://localhost:8000
# Docs at http://localhost:8000/docs
```

**Option C: Terminal chat**
```bash
python -m rag.chain
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/ask` | Ask a natural language NBA question |
| `GET` | `/players` | Browse player stats (`?search=`, `?team=`, `?limit=`) |
| `GET` | `/teams` | Team standings + advanced stats (`?conference=`) |
| `POST` | `/refresh` | Re-fetch all data and rebuild vector store |

### Example request

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Who should win MVP this season?"}'
```

## Data Pipeline

The app ingests five categories of live NBA data:

1. **Player Season Averages** -- PTS, REB, AST, STL, BLK, FG%, 3P%, FT%, MIN, GP
2. **Team Standings** -- W-L, conference rank, streak
3. **Advanced Team Stats** -- Offensive/defensive ratings, pace, net rating
4. **League Leaders** -- Top 20 in scoring, assists, rebounds

Each data point is transformed into a natural language summary and embedded into ChromaDB for semantic retrieval. The vector store can be refreshed on demand via the UI refresh button or the `/refresh` API endpoint.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Your Anthropic API key |
| `CHROMA_PERSIST_DIR` | No | ChromaDB storage path (default: `./data/chroma`) |
| `NBA_API_TIMEOUT` | No | NBA API request timeout in seconds (default: `30`) |

## Built With

- [Anthropic Claude API](https://docs.anthropic.com/) -- LLM for query classification and response generation
- [ChromaDB](https://www.trychroma.com/) -- Vector database for semantic search
- [nba_api](https://github.com/swar/nba_api) -- Python client for stats.nba.com
- [FastAPI](https://fastapi.tiangolo.com/) -- Backend API framework
- [Streamlit](https://streamlit.io/) -- Frontend UI framework
