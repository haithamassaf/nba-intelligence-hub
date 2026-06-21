# NFL & NBA Roster Grader + Trade Simulator

Pick a team in either league and see every position graded 0-100 against league
peers from advanced stats, a full roster table, and an offseason improvement
summary. Compare any two players, browse stats, and (NFL) run cap-legal trades
that show how each side's grades move. Built for evaluating roster construction
the way a front office would.

No faked numbers. Where a metric is paywalled or not publicly available, it is
dropped rather than estimated, and the grade renormalizes around what is real.

## What it does

- **Per-position grades.** Each player is scored relative to position peers
  (NFL: QB, RB, WR, TE, OL, DL, LB, DB, ST; NBA: Guard, Wing, Big) using a
  weighted blend of advanced stats, expressed as a percentile within the
  position. A grade means "where this player ranks at his spot," not an
  arbitrary cutoff.
- **Team rollup and needs.** Player grades roll up to a playing-time-weighted
  team grade per position and an overall grade, with the weakest groups flagged
  as offseason needs.
- **Improvement summary.** A plain-language summary of strengths and the top
  needs. Written by Claude when an API key is present, otherwise from a
  deterministic template. Claude only phrases the computed grades; it is never
  the source of a number.
- **NFL rookies included.** Rookies have no NFL snaps, so they are graded from
  their final college season (CollegeFootballData) plus draft capital and
  combine testing.
- **Compare and stats.** Side-by-side player comparison and a sortable stat
  table per team, in both leagues.
- **NFL trade simulator.** Build a trade between any two teams and get cap
  legality plus the grade and needs impact for both sides. A suggester finds
  cap-legal upgrades for a team's biggest needs.

## Grading inputs

- **NBA** (`nba_api`): true shooting, usage, assist and rebound rates, offensive
  and defensive rating, net rating, plus-minus, PIE, steals, blocks.
- **NFL** (`nflreadpy` / nflverse): EPA, Next Gen Stats (CPOE, separation, YAC
  over expected, rush yards over expected), ESPN QBR, PFR advanced stats, snap
  counts, production totals.
- **Offensive line and specialists** are graded on role and availability (snap
  share and continuity). Public pass-block and run-block win rates are ESPN
  proprietary and not in any free feed, so they are not used or approximated.
- **NFL rookies** (`cfbd`): college production, draft pick, combine testing.

## Trade simulator (NFL)

NFL trades are cap-driven with no salary matching. Each player's cap charge is
his OverTheCap APY, and a team's commitment is the sum of its top-51 APYs, which
mirrors the offseason top-51 rule. A trade is legal when both teams stay under
the cap. The net cap change between teams is exact; the absolute cap-space number
depends on `NFL_SALARY_CAP`, which you set to the current league-year cap.

Beyond legality, every trade is re-graded: the tool swaps the rosters and
recomputes each team's position grades, overall grade, and needs, so you see
exactly what the deal does on the field.

NBA trades are intentionally not included. Validating NBA legality requires
player salaries and apron math, and `nba_api` carries no contract data, so doing
it honestly is not possible from free sources.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env        # then fill in optional keys
streamlit run frontend/app.py
```

The first load fetches live data and grades every roster, then caches for six
hours. The NBA tab pulls all 30 rosters on first load, so give it a moment.

### Optional keys

Both are optional. The app runs without either.

- `ANTHROPIC_API_KEY` - turns the team summaries into Claude-written prose.
  Without it, summaries use a deterministic template.
- `CFBD_API_KEY` - free key from https://collegefootballdata.com/key (email
  request). Powers rookie grading from college production. Without it, rookies
  grade on draft capital and combine only.

### Season behavior

Stats and grading use the most recent completed season; rosters use the current
league year, so the latest rookie class is included. All seasons can be pinned
with the env vars in `.env.example`.

## Structure

```
config/      settings, grade bands
data/        fetch_stats (NBA), nfl_fetch (NFL), cfbd_fetch (college)
grading/     scale (percentile math), nba_grades, nfl_grades, team_report, pipeline
trade/       nfl_trade (cap legality + grade impact + suggester)
summary/     llm_summary (Claude prose + deterministic fallback)
frontend/    Streamlit app + grade-display components
api/         FastAPI grading endpoints (optional)
```

## API (optional)

```bash
uvicorn api.main:app --reload
# GET /{sport}/teams
# GET /{sport}/teams/{team}/grades
```

## Roadmap

- **Award and champion projections** for the upcoming seasons (2026-27 NBA,
  2026 NFL), built on the grading layer: MVP, DPOY, ROY, All-NBA, All-Defense,
  All-Star and champion for the NBA; MVP, OPOY, DPOY, both Rookies of the Year,
  All-Pro, Pro Bowl and Super Bowl for the NFL. Each respects the league's real
  eligibility rules and factors age and strength of schedule.
