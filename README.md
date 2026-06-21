# NFL & NBA Rosters

Browse every team's roster and stats in both leagues, compare any two players,
and run cap-legal NFL trades.

## What it does

- **Rosters.** Pick any team and see its full roster with stats, pulled fresh.
- **Compare.** Put any two players side by side on their stats.
- **NFL trade simulator.** Build a trade between any two teams and get cap
  legality plus the cap impact for both sides.

## Trade simulator (NFL)

NFL trades are cap-driven with no salary matching. Each player's cap charge is
his OverTheCap APY, and a team's commitment is the sum of its top-51 APYs, which
mirrors the offseason top-51 rule. A trade is legal when both teams stay under
the cap. The net cap change between teams is exact; the absolute cap-space number
depends on `NFL_SALARY_CAP`, which you set to the current league-year cap.

NBA trades are not included: validating NBA legality needs player salaries and
apron math, and `nba_api` carries no contract data, so it cannot be done honestly
from free sources.

## Setup

```bash
pip install -r requirements.txt
streamlit run frontend/app.py
```

The first load fetches live data and caches for six hours. The NBA tab pulls all
30 rosters on first load, so give it a moment. No API keys required.

Season behavior: stats use the most recent completed season; NFL rosters use the
current league year, so the latest rookie class is included. Pin any season with
the env vars in `.env.example`.

## Data sources

- **NBA** (`nba_api`): rosters and player stats (traditional + advanced).
- **NFL** (`nflreadpy` / nflverse): rosters, season stats, and OverTheCap
  contracts for the trade simulator.

## Structure

```
config/      settings
data/        fetch_stats (NBA), nfl_fetch (NFL), assemble (roster tables)
trade/       nfl_trade (cap legality)
frontend/    Streamlit app + table/compare/trade components
```
